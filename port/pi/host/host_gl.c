/*
HOST_GL.C

OpenGL ES for the guest. Its generated entry points (guest_gl.c) import
hostgl_<function>, resolved here to the driver's function; the arguments
already have host types by then. Only strings need copying back.
*/

#include "host.h"

#include <EGL/egl.h>
#include <GLES3/gl32.h>
#include <dlfcn.h>
#include <string.h>
#include <stdlib.h>
#include <GLES2/gl2ext.h>
#include <SDL3/SDL.h>

static GLuint bound_array, bound_element, bound_copy_write;
static void pi_gl_bind_buffer(GLenum target, GLuint name)
{
 glBindBuffer(target,name);
 if(target==GL_ARRAY_BUFFER) bound_array=name;
 else if(target==GL_ELEMENT_ARRAY_BUFFER) bound_element=name;
 else if(target==GL_COPY_WRITE_BUFFER) bound_copy_write=name;
}
struct gl_profile { const char *name; uint64_t count, time; };
static struct gl_profile profile[]={{"draw_elements",0,0},{"draw_arrays",0,0},{"copy_image",0,0},{"buffer_subdata",0,0},{"map_buffer",0,0},{"unmap_buffer",0,0}};
static void pi_gl_draw_elements(GLenum mode, GLsizei count, GLenum type, const void *indices) {
 uint64_t t=SDL_GetTicksNS();glDrawElements(mode,count,type,indices);profile[0].count++;profile[0].time+=SDL_GetTicksNS()-t;
}
static void pi_gl_draw_arrays(GLenum mode, GLint first,GLsizei count) {
 uint64_t t=SDL_GetTicksNS();glDrawArrays(mode,first,count);profile[1].count++;profile[1].time+=SDL_GetTicksNS()-t;
}
static void pi_gl_copy_image(GLuint src, GLenum st,GLint sl,GLint sx,GLint sy,GLint sz,GLuint dst,GLenum dt,GLint dl,GLint dx,GLint dy,GLint dz,GLsizei w,GLsizei h,GLsizei depth) {
 typedef void (*proc)(GLuint,GLenum,GLint,GLint,GLint,GLint,GLuint,GLenum,GLint,GLint,GLint,GLint,GLsizei,GLsizei,GLsizei);
 static proc real;
 if(!real)real=(proc)eglGetProcAddress("glCopyImageSubData");
 uint64_t t=SDL_GetTicksNS();real(src,st,sl,sx,sy,sz,dst,dt,dl,dx,dy,dz,w,h,depth);profile[2].count++;profile[2].time+=SDL_GetTicksNS()-t;
}
static void pi_gl_buffer_subdata(GLenum target,GLintptr offset,GLsizeiptr size,const void *data) {
 uint64_t t=SDL_GetTicksNS();glBufferSubData(target,offset,size,data);profile[3].count++;profile[3].time+=SDL_GetTicksNS()-t;
}
static void *pi_gl_map_buffer(GLenum target,GLintptr offset,GLsizeiptr size,GLbitfield access) {
 uint64_t t=SDL_GetTicksNS();void *r=glMapBufferRange(target,offset,size,access);profile[4].count++;profile[4].time+=SDL_GetTicksNS()-t;return r;
}
static GLboolean pi_gl_unmap_buffer(GLenum target) {
 uint64_t t=SDL_GetTicksNS();GLboolean r=glUnmapBuffer(target);profile[5].count++;profile[5].time+=SDL_GetTicksNS()-t;return r;
}
void host_gl_profile_report(uint64_t frames) {
 if(!getenv("HALO_PI_GL_PROFILE"))return;
 for(unsigned i=0;i<sizeof(profile)/sizeof(*profile);i++) {
  host_logf(HOST_LOG_INFO,"PI_GL_PROFILE %s calls_per_frame=%.1f ms_per_frame=%.3f",profile[i].name,profile[i].count/(double)frames,profile[i].time/1e6/frames);
  profile[i].count=profile[i].time=0;
 }
}

void *host_gl_resolve(const char *name)
{
	if(!strcmp(name,"glBindBuffer"))return (void *)pi_gl_bind_buffer;
	if(getenv("HALO_PI_GL_PROFILE")) {
	 if(!strcmp(name,"glDrawElements"))return (void *)pi_gl_draw_elements;
	 if(!strcmp(name,"glDrawArrays"))return (void *)pi_gl_draw_arrays;
	 if(!strcmp(name,"glCopyImageSubData"))return (void *)pi_gl_copy_image;
	 if(!strcmp(name,"glBufferSubData"))return (void *)pi_gl_buffer_subdata;
	 if(!strcmp(name,"glMapBufferRange"))return (void *)pi_gl_map_buffer;
	 if(!strcmp(name,"glUnmapBuffer"))return (void *)pi_gl_unmap_buffer;
	}
	static void *library;
	void *function = NULL;

	if (!library)
		library = dlopen("libGLESv2.so.2", RTLD_NOW | RTLD_GLOBAL);
	if (library)
		function = dlsym(library, name);
	if (!function)
		function = (void *)eglGetProcAddress(name);
	return function;
}

void host_gl_get_string(uint32_t name, int index, char *buffer, uint32_t size)
{
	const GLubyte *text = index >= 0 ? glGetStringi(name, (GLuint)index) : glGetString(name);

	if (!size)
		return;
	buffer[0] = 0;
	if (text)
	{
		strncpy(buffer, (const char *)text, size - 1);
		buffer[size - 1] = 0;
	}
}

int host_gl_has_extension(const char *name)
{
	GLint count = 0, index;

	glGetIntegerv(GL_NUM_EXTENSIONS, &count);
	for (index = 0; index < count; index++)
	{
		const char *extension = (const char *)glGetStringi(GL_EXTENSIONS, (GLuint)index);

		if (extension && !strcmp(extension, name))
			return 1;
	}
	return 0;
}

/* one 32-bit word of a buffer object (the visibility test counters of
d3d8_gl.c); ES has no glGetBufferSubData, and the mapping it offers
instead is a host pointer */
uint32_t host_gl_read_buffer_word(uint32_t buffer, uint32_t offset)
{
	uint32_t value = 0;
	GLint previous = 0;
	const void *mapping;

	glGetIntegerv(GL_ATOMIC_COUNTER_BUFFER_BINDING, &previous);
	glBindBuffer(GL_ATOMIC_COUNTER_BUFFER, buffer);
	mapping = glMapBufferRange(GL_ATOMIC_COUNTER_BUFFER, offset, sizeof(value), GL_MAP_READ_BIT);
	if (mapping)
	{
		memcpy(&value, mapping, sizeof(value));
		glUnmapBuffer(GL_ATOMIC_COUNTER_BUFFER);
	}
	glBindBuffer(GL_ATOMIC_COUNTER_BUFFER, (GLuint)previous);
	return value;
}

/* The renderer streams each frame's vertices and indices into the next of
a ring of buffers (d3d8_gl.c). A fence marks the end of each frame's work,
and a buffer is written again only once the GPU has passed the fence of the
frame that last used it: drivers queue several frames, and a draw still
waiting to run would otherwise read a later frame's vertices. */
#define FRAME_FENCE_SLOTS 8

static GLsync frame_fences[FRAME_FENCE_SLOTS];

void host_gl_fence_frame(uint32_t slot)
{
	if (slot >= FRAME_FENCE_SLOTS)
		return;
	if (frame_fences[slot])
		glDeleteSync(frame_fences[slot]);
	frame_fences[slot] = glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0);
}

void host_gl_wait_frame(uint32_t slot)
{
	if (slot >= FRAME_FENCE_SLOTS || !frame_fences[slot])
		return;
	/* at most a second: a lost context must not hang the game */
	glClientWaitSync(frame_fences[slot], GL_SYNC_FLUSH_COMMANDS_BIT, 1000000000ull);
	glDeleteSync(frame_fences[slot]);
	frame_fences[slot] = NULL;
}

/* writes data into the buffer bound to target. The renderer streams a
range per draw, so a frame makes hundreds of these, and the cost per call
rather than per byte is what a frame is made of.

GL_MAP_INVALIDATE_RANGE_BIT was what made that cost ruinous. It tells the
driver the range's previous contents are undefined and must be discarded,
which is the very work GL_MAP_UNSYNCHRONIZED_BIT exists to avoid: that one
promises the caller that no queued draw is reading the range. Asked to do
both, Adreno pays for the discard - about 0.85 ms a call on a Galaxy Z
Flip 4, whatever the range written - and with a few hundred calls a frame
that came to 96% of a 550 ms frame at 1.8 fps, with the GPU idle throughout.

Without the invalidation the same call is well under a microsecond and the
same game runs at the display's refresh rate. The promise unsynchronized
makes still holds: the renderer only writes ranges that no queued draw reads,
because host_gl_wait_frame releases the ring slot first. */
#define PERSISTENT_BUFFER_COUNT 32
struct persistent_buffer { GLuint name; unsigned char *mapping; uint32_t size; };
static struct persistent_buffer persistent_buffers[PERSISTENT_BUFFER_COUNT];
static int persistent_count;

static GLuint bound_buffer(GLenum target)
{
 return target==GL_ARRAY_BUFFER?bound_array:
  target==GL_ELEMENT_ARRAY_BUFFER?bound_element:bound_copy_write;
}

void host_gl_buffer_allocate(uint32_t target,uint32_t size)
{
 const char *setting=getenv("HALO_PI_PERSISTENT");
 PFNGLBUFFERSTORAGEEXTPROC storage=(PFNGLBUFFERSTORAGEEXTPROC)eglGetProcAddress("glBufferStorageEXT");
 if ((!setting || strcmp(setting,"0")) && storage &&
  host_gl_has_extension("GL_EXT_buffer_storage") && persistent_count<PERSISTENT_BUFFER_COUNT) {
  GLbitfield flags=GL_MAP_WRITE_BIT|GL_MAP_PERSISTENT_BIT_EXT|GL_MAP_COHERENT_BIT_EXT;
  GLuint name=bound_buffer(target);
  storage(target,size,NULL,flags|GL_DYNAMIC_STORAGE_BIT_EXT);
  void *mapping=glMapBufferRange(target,0,size,flags);
  if(mapping) {
   persistent_buffers[persistent_count++]=(struct persistent_buffer){name,mapping,size};
   host_logf(HOST_LOG_INFO,"Pi persistent stream buffer %u: %u bytes",name,size);
  } else host_log(HOST_LOG_WARN,"persistent buffer mapping unavailable; using subdata");
  return;
 }
 glBufferData(target,size,NULL,GL_STREAM_DRAW);
}

void host_gl_buffer_write(uint32_t target, uint32_t offset, uint32_t size, const void *data)
{
	GLuint name = bound_buffer(target);
	for (int index=0;index<persistent_count;index++) {
		struct persistent_buffer *buffer=&persistent_buffers[index];
		if(buffer->name==name && offset<=buffer->size && size<=buffer->size-offset) {
			memcpy(buffer->mapping+offset,data,size);
			return;
		}
	}
	void *mapping = glMapBufferRange(target, offset, size,
		GL_MAP_WRITE_BIT | GL_MAP_UNSYNCHRONIZED_BIT);

	if (!mapping)
	{
		glBufferSubData(target, offset, size, data);
		return;
	}
	memcpy(mapping, data, size);
	glUnmapBuffer(target);
}
