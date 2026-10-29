/* FXM-HIDDEN-CANARY-t11: hidden test driver for t11. Never shown to the model. */
#include <stdio.h>
#include <stddef.h>
#include "bq.h"
#include "vectors.h"

#define BLK_MAX 64U
#define NOT_SET 777U

static int run_case(const fxm_case_t *cs)
{
    bq_t f;
    int ok = 1;
    for (unsigned i = 0; i < cs->len; i++) {
        const fxm_step_t *s = &FXM_STEPS[cs->start + i];
        int16_t in[BLK_MAX], out[BLK_MAX];
        long got = 0, got2 = 0;
        switch (s->op) {
        case 0: {
            bq_coeffs_t c = {FXM_COEFFS[s->a][0], FXM_COEFFS[s->a][1], FXM_COEFFS[s->a][2],
                             FXM_COEFFS[s->a][3], FXM_COEFFS[s->a][4]};
            got = bq_init(&f, &c, (uint8_t)s->b) ? 1 : 0;
            break;
        }
        case 1: {
            int16_t y = (int16_t)FXM_SENTINEL;
            if (bq_step(&f, (int16_t)s->a, &y)) {
                got = y;
            } else {
                got = FXM_NONE;
                ok &= y == (int16_t)FXM_SENTINEL; /* B7: *y is not written */
            }
            break;
        }
        case 2:
        case 3: {
            size_t made = NOT_SET;
            int16_t *dst = s->op == 3 ? in : out;
            for (unsigned k = 0; k < BLK_MAX; k++) {
                in[k] = k < (unsigned)s->b ? FXM_BLK_IN[s->a + k] : 0;
                out[k] = (int16_t)FXM_SENTINEL;
            }
            got = (long)bq_process(&f, in, (size_t)s->b, dst, (size_t)s->c, &made);
            got2 = (long)made;
            /* the outputs, then (in place) the untouched input or (separate) the untouched sentinel */
            for (unsigned k = 0; k < (unsigned)s->b && k < BLK_MAX; k++) {
                ok &= dst[k] == FXM_BLK_OUT[s->a + k];
            }
            if (s->op == 2) {
                for (unsigned k = (unsigned)s->want2; k < BLK_MAX; k++) {
                    ok &= out[k] == (int16_t)FXM_SENTINEL;
                }
            }
            break;
        }
        case 4: bq_reset(&f); got = s->want; break;
        case 5: got = bq_sat_count(&f); break;
        default: {
            for (long k = 0; k < s->b; k++) {
                int16_t y = 0;
                if (bq_step(&f, (int16_t)s->a, &y)) {
                    got++;
                    got2 = y;
                }
            }
            break;
        }
        }
        if (got != s->want || ((s->op == 2 || s->op == 3 || s->op == 6) && got2 != s->want2)) {
            ok = 0;
        }
    }
    return ok;
}

/* B11 (C only): null pointers. */
static int null_pointers(void)
{
    bq_t f;
    const bq_coeffs_t c = {16384, 0, 0, 0, 0};
    int16_t buf[2] = {7, 8};
    int16_t y = 1;
    size_t made = NOT_SET;
    int ok = 1;
    ok &= bq_init(NULL, &c, 1U) == false;
    ok &= bq_init(&f, &c, 1U) == true;
    ok &= bq_step(&f, 5, &y) == true && y == 5;
    ok &= bq_init(&f, NULL, 1U) == false;   /* changes nothing: x1 is still 5 */
    ok &= bq_step(NULL, 3, &y) == false;
    ok &= bq_step(&f, 3, NULL) == false;
    bq_reset(NULL);
    ok &= bq_process(NULL, buf, 2U, buf, 2U, &made) == 0U;
    ok &= bq_process(&f, NULL, 2U, buf, 2U, &made) == 0U;
    ok &= bq_process(&f, buf, 2U, NULL, 2U, &made) == 0U;
    ok &= bq_process(&f, buf, 2U, buf, 2U, NULL) == 0U;
    ok &= made == NOT_SET && buf[0] == 7 && buf[1] == 8;
    ok &= bq_sat_count(NULL) == 0U;
    {
        /* the state survived every null call: with b1 = 1.0 the next output is x1 = 5 */
        const bq_coeffs_t d = {0, 16384, 0, 0, 0};
        f.c = d;
        ok &= bq_step(&f, 0, &y) == true && y == 5;
    }
    return ok;
}

int main(void)
{
    unsigned passed = 0, total = 0;
    for (unsigned k = 0; k < FXM_N_CASES; k++) {
        total++;
        if (run_case(&FXM_CASES[k])) {
            passed++;
        } else {
            printf("FXM-FAIL %s [%s]\n", FXM_CASES[k].name, FXM_CASES[k].req);
        }
    }
    total++;
    if (null_pointers()) {
        passed++;
    } else {
        printf("FXM-FAIL null_pointers [B11]\n");
    }
    printf("FXM-RESULT passed=%u total=%u\n", passed, total);
    return passed == total ? 0 : 1;
}
