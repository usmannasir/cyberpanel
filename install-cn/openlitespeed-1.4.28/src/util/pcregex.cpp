/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2015  LiteSpeed Technologies, Inc.                 *
*                                                                            *
*    This program is free software: you can redistribute it and/or modify    *
*    it under the terms of the GNU General Public License as published by    *
*    the Free Software Foundation, either version 3 of the License, or       *
*    (at your option) any later version.                                     *
*                                                                            *
*    This program is distributed in the hope that it will be useful,         *
*    but WITHOUT ANY WARRANTY; without even the implied warranty of          *
*    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the            *
*    GNU General Public License for more details.                            *
*                                                                            *
*    You should have received a copy of the GNU General Public License       *
*    along with this program. If not, see http://www.gnu.org/licenses/.      *
*****************************************************************************/
#include <util/pcregex.h>
#include <assert.h>
#include <ctype.h>
#include <string.h>
#include <pthread.h>

#ifndef PCRE_STUDY_JIT_COMPILE
#define PCRE_STUDY_JIT_COMPILE 0
#endif

#ifdef _USE_PCRE_JIT_
#if !defined(__sparc__) && !defined(__sparc64__)

static int s_jit_key_inited = 0;
static pthread_key_t s_jit_stack_key;

void Pcregex::initJitStack()
{
    s_jit_key_inited = 1;
    pthread_key_create(&s_jit_stack_key, releaseJitStack);
}

void Pcregex::releaseJitStack(void *pValue)
{
    pcre_jit_stack_free((pcre_jit_stack *) pValue);
}


pcre_jit_stack *Pcregex::getJitStack()
{
    pcre_jit_stack *jit_stack;

    if (!s_jit_key_inited)
        initJitStack();
    jit_stack = (pcre_jit_stack *)pthread_getspecific(s_jit_stack_key);
    if (!jit_stack)
    {
        jit_stack = (pcre_jit_stack *)pcre_jit_stack_alloc(32 * 1024, 512 * 1024);
        pthread_setspecific(s_jit_stack_key, jit_stack);
    }
    return jit_stack;
}
#endif
#endif





