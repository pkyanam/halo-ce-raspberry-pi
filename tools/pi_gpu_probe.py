#!/usr/bin/env python3
import ctypes as c
E=c.CDLL('libEGL.so.1'); G=c.CDLL('libGLESv2.so.2')
def bind(lib,n,rest,args):
 f=getattr(lib,n); f.restype=rest; f.argtypes=args; return f
ptr=c.c_void_p; I=c.c_int; U=c.c_uint
get=bind(E,'eglGetProcAddress',ptr,[c.c_char_p])
platform=c.CFUNCTYPE(ptr,U,ptr,c.POINTER(I))(get(b'eglGetPlatformDisplayEXT'))
d=platform(0x31DD,None,None)
major=I();minor=I()
assert bind(E,'eglInitialize',U,[ptr,c.POINTER(I),c.POINTER(I)])(d,c.byref(major),c.byref(minor)), 'EGL initialize failed'
assert bind(E,'eglBindAPI',U,[U])(0x30A0)
attrs=(I*7)(0x3040,0x40,0x3033,1,0x3024,8,0x3038)
config=ptr();count=I()
assert bind(E,'eglChooseConfig',U,[ptr,c.POINTER(I),c.POINTER(ptr),I,c.POINTER(I)])(d,attrs,c.byref(config),1,c.byref(count)) and count.value
context=bind(E,'eglCreateContext',ptr,[ptr,ptr,ptr,c.POINTER(I)])(d,config,None,(I*3)(0x3098,3,0x3038))
assert context, 'ES3 context failed'
assert bind(E,'eglMakeCurrent',U,[ptr,ptr,ptr,ptr])(d,None,None,context)
string=bind(G,'glGetString',c.c_char_p,[U])
for name,enum in [('vendor',0x1F00),('renderer',0x1F01),('version',0x1F02),('glsl',0x8B8C)]: print(name+':',string(enum).decode())
print('EGL:',major.value,minor.value)
