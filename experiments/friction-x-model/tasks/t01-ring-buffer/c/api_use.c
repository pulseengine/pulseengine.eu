/* A fixed caller of every function declared in rb.h, and nothing else.
 * cppcheck analyses it together with rb.c, so its whole-program MISRA check
 * sees that the API is called from another translation unit (rule 8.7).
 * It is not a test: it is never compiled or run, and checks no behaviour. */
#include <stdbool.h>
#include <stdint.h>
#include "rb.h"

int main(void)
{
    rb_t fxm_rb;
    uint8_t fxm_out = 0U;
    bool fxm_ok = true;
    int fxm_rc = 0;

    rb_init(&fxm_rb);
    if (!rb_push(&fxm_rb, 1U)) {
        fxm_ok = false;
    }
    if (!rb_peek(&fxm_rb, &fxm_out)) {
        fxm_ok = false;
    }
    if (!rb_pop(&fxm_rb, &fxm_out)) {
        fxm_ok = false;
    }
    if (rb_len(&fxm_rb) != 0U) {
        fxm_ok = false;
    }
    if ((!fxm_ok) || (fxm_out != 1U)) {
        fxm_rc = 1;
    }
    return fxm_rc;
}
