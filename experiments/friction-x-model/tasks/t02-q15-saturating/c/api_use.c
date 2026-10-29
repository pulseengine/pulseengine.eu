/* Calls every function declared in q15.h, and nothing else. Not a test. */
#include <stdint.h>
#include "q15.h"

int main(void)
{
    int fxm_rc = 0;
    q15_t fxm_x = q15_add((q15_t)1, (q15_t)2);

    fxm_x = q15_sub(fxm_x, (q15_t)1);
    fxm_x = q15_mul(fxm_x, (q15_t)16384);
    fxm_x = q15_neg(fxm_x);
    fxm_x = q15_abs(fxm_x);
    if (fxm_x != (q15_t)1) {
        fxm_rc = 1;
    }
    return fxm_rc;
}
