/* A fixed caller of every function declared in q15.h, and nothing else.
 * cppcheck analyses it together with q15.c, so its whole-program MISRA check
 * sees that the API is called from another translation unit (rule 8.7).
 * It is not a test: it is never compiled or run, and checks no behaviour. */
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
