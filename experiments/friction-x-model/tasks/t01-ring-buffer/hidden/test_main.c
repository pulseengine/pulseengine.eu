/* FXM-HIDDEN-CANARY-t01: hidden test driver for t01. Never shown to the model. */
#include <stdio.h>
#include <stddef.h>
#include "rb.h"
#include "vectors.h"

#define SENTINEL 0xA5U

static int run_case(const fxm_case_t *c)
{
    rb_t rb;
    int ok = 1;
    for (unsigned i = 0; i < c->len; i++) {
        const fxm_step_t *s = &FXM_STEPS[c->start + i];
        uint8_t out = SENTINEL;
        int got_ok = 1;
        unsigned got_val = 0;
        switch (s->op) {
        case 0: rb_init(&rb); break;
        case 1: got_ok = rb_push(&rb, s->arg) ? 1 : 0; break;
        case 2: got_ok = rb_pop(&rb, &out) ? 1 : 0; got_val = got_ok ? out : 0; break;
        case 3: got_ok = rb_peek(&rb, &out) ? 1 : 0; got_val = got_ok ? out : 0; break;
        default: got_val = rb_len(&rb); break;
        }
        if ((s->op == 2 || s->op == 3) && !got_ok && out != SENTINEL) {
            ok = 0; /* R4/R8: *out must not be written on a false return */
        }
        if (got_ok != (int)s->ok || got_val != s->val) {
            ok = 0;
        }
    }
    return ok;
}

/* R8 (C only): null pointers. */
static int null_pointers(void)
{
    rb_t rb;
    uint8_t out = SENTINEL;
    int ok = 1;
    rb_init(NULL);
    rb_init(&rb);
    ok &= rb_push(NULL, 1U) == false;
    ok &= rb_pop(NULL, &out) == false;
    ok &= rb_peek(NULL, &out) == false;
    ok &= rb_len(NULL) == 0U;
    ok &= rb_push(&rb, 1U) == true;
    ok &= rb_pop(&rb, NULL) == false;
    ok &= rb_peek(&rb, NULL) == false;
    ok &= rb_len(&rb) == 1U;
    ok &= out == SENTINEL;
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
        printf("FXM-FAIL null_pointers [R8]\n");
    }
    printf("FXM-RESULT passed=%u total=%u\n", passed, total);
    return passed == total ? 0 : 1;
}
