#pragma once
#include <stdio.h>
#include <stdarg.h>
#define ANDROID_LOG_INFO 4
#define ANDROID_LOG_WARN 5
#define ANDROID_LOG_FATAL 7
static inline int __android_log_vprint(int p, const char *tag, const char *fmt, va_list args) { (void)p; fprintf(stderr, "%s: ", tag); int n=vfprintf(stderr,fmt,args); fputc('\n',stderr); return n; }
static inline int __android_log_print(int p, const char *tag, const char *fmt, ...) { va_list args; va_start(args,fmt); int n=__android_log_vprint(p,tag,fmt,args); va_end(args); return n; }
static inline int __android_log_write(int p, const char *tag, const char *s) { return __android_log_print(p,tag,"%s",s); }
