/* FXM-HIDDEN-CANARY-t02: hidden test driver for t02. Never shown to the model. */
#include <stdio.h>
#include "q15.h"
#include "vectors.h"

static const char *const REQ[] = {"Q1", "Q2", "Q3", "Q4", "Q5"};

int main(void)
{
    unsigned passed = 0, total = 0, shown = 0;
    for (unsigned k = 0; k < FXM_N_VECS; k++) {
        const fxm_vec_t *v = &FXM_VECS[k];
        q15_t a = (q15_t)v->a, b = (q15_t)v->b, got;
        switch (v->op) {
        case 0: got = q15_add(a, b); break;
        case 1: got = q15_sub(a, b); break;
        case 2: got = q15_mul(a, b); break;
        case 3: got = q15_neg(a); break;
        default: got = q15_abs(a); break;
        }
        total++;
        if ((int32_t)got == v->want) {
            passed++;
        } else if (shown++ < 20) {
            printf("FXM-FAIL vec%u [%s] a=%d b=%d\n", k, REQ[v->op], (int)v->a, (int)v->b);
        }
    }
    printf("FXM-RESULT passed=%u total=%u\n", passed, total);
    return passed == total ? 0 : 1;
}
