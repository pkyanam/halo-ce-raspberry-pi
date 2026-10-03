#include <SDL3/SDL.h>
#include <GLES3/gl3.h>
#include <stdio.h>
int main(void) {
 if(!SDL_Init(SDL_INIT_VIDEO)){fprintf(stderr,"%s\n",SDL_GetError());return 1;}
 SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);
 SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,3);
 SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,1);
 SDL_Window *w=SDL_CreateWindow("Pi probe",640,480,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);
 if(!w){fprintf(stderr,"%s\n",SDL_GetError());return 2;}
 SDL_GLContext ctx=SDL_GL_CreateContext(w);
 if(!ctx){fprintf(stderr,"%s\n",SDL_GetError());return 3;}
 printf("SDL driver: %s\nGPU: %s\nVersion: %s\n",SDL_GetCurrentVideoDriver(),glGetString(GL_RENDERER),glGetString(GL_VERSION));
 glClearColor(0.25,0.5,0.75,1);glClear(GL_COLOR_BUFFER_BIT);
 unsigned char pixel[4]={0};glReadPixels(0,0,1,1,GL_RGBA,GL_UNSIGNED_BYTE,pixel);
 printf("Rendered pixel: %u %u %u %u\n",pixel[0],pixel[1],pixel[2],pixel[3]);
 int okay=pixel[0]>=63&&pixel[0]<=65&&pixel[1]>=127&&pixel[1]<=129&&pixel[2]>=190&&pixel[2]<=192;
 SDL_GL_DestroyContext(ctx);SDL_DestroyWindow(w);SDL_Quit();return okay?0:4;
}
