/* Copyright 2020 Google Inc.
 
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
 
 http://www.apache.org/licenses/LICENSE-2.0
 
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 */

#include "quickjs-libc.h"

#include <stdint.h>
#include <stdio.h>

static int initialized = 0;
JSRuntime *rt;
JSContext *ctx;
static int nbinterrupts = 0;
static uint8_t *buffer;
static size_t buffer_size;

// handle timeouts from infinite loops
static int interrupt_handler(JSRuntime *rt, void *opaque)
{
    nbinterrupts++;
    return (nbinterrupts > 100);
}

int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {
    if (initialized == 0) {
        rt = JS_NewRuntime();
        // 64 Mo
        JS_SetMemoryLimit(rt, 0x4000000);
        //TODO JS_SetMaxStackSize ?
        ctx = JS_NewContextRaw(rt);
        JS_SetModuleLoaderFunc(rt, NULL, js_module_loader, NULL);
        JS_AddIntrinsicBaseObjects(ctx);
        JS_AddIntrinsicDate(ctx);
        JS_AddIntrinsicEval(ctx);
        JS_AddIntrinsicStringNormalize(ctx);
        JS_AddIntrinsicRegExp(ctx);
        JS_AddIntrinsicJSON(ctx);
        JS_AddIntrinsicProxy(ctx);
        JS_AddIntrinsicMapSet(ctx);
        JS_AddIntrinsicTypedArrays(ctx);
        JS_AddIntrinsicPromise(ctx);
        JS_AddIntrinsicBigInt(ctx);
        JS_SetInterruptHandler(JS_GetRuntime(ctx), interrupt_handler, NULL);
        js_std_add_helpers(ctx, 0, NULL);
        buffer = malloc(Size);
        buffer_size = Size;
        initialized = 1;
    }

    if (Size > 0) {
        const uint8_t * buf;
        size_t buf_size;
        if (Data[Size-1] == 0) {
            buf = Data;
            //the final 0 does not count (as in strlen)
            buf_size = Size-1;
        } else {
            if (buffer_size < Size +1) {
                buffer_size = Size +1;
                buffer = realloc(buffer, buffer_size);
            }
            memcpy(buffer, Data, Size);
            buffer[Size] = 0;
            buf = buffer;
            buf_size = Size;
        }
        nbinterrupts = 0;
        
        JSValue val = JS_Eval(ctx, (const char *)buf, buf_size, "<none>", JS_EVAL_TYPE_GLOBAL);
        //TODO targets with JS_ParseJSON, JS_ReadObject
        if (!JS_IsException(val)) {
            js_std_loop(ctx);
            JS_FreeValue(ctx, val);
        }
    }

    return 0;
}
