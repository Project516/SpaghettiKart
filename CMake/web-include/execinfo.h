#pragma once
// Emscripten has no execinfo.h. libultraship's crash handler only uses these to
// print a backtrace, so on the web it prints an empty one.
#include <stddef.h>

static inline int backtrace(void** buffer, int size) {
    (void)buffer;
    (void)size;
    return 0;
}

static inline char** backtrace_symbols(void* const* buffer, int size) {
    (void)buffer;
    (void)size;
    return NULL;
}
