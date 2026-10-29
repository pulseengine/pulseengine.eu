/* Calls every function declared in bq.h, and nothing else. Not a test. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "bq.h"

int main(void)
{
    bq_t fxm_f;
    const bq_coeffs_t fxm_c = {16384, 0, 0, 0, 0};
    int16_t fxm_buf[2] = {1, 2};
    int16_t fxm_y = 0;
    size_t fxm_made = 0U;
    size_t fxm_took;
    bool fxm_ok;
    int fxm_rc = 0;

    fxm_ok = bq_init(&fxm_f, &fxm_c, 1U);
    if (!bq_step(&fxm_f, 3, &fxm_y)) {
        fxm_ok = false;
    }
    fxm_took = bq_process(&fxm_f, fxm_buf, 2U, fxm_buf, 2U, &fxm_made);
    bq_reset(&fxm_f);
    if ((!fxm_ok) || (fxm_y != 3) || (fxm_took != 2U) || (fxm_made != 2U) || (bq_sat_count(&fxm_f) != 0U)) {
        fxm_rc = 1;
    }
    return fxm_rc;
}
