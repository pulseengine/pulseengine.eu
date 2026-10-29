/* Calls every function declared in rb.h, and nothing else. Not a test. */
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
