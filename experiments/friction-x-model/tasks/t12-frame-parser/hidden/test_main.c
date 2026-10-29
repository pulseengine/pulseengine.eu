/* FXM-HIDDEN-CANARY-t12: hidden test driver for t12. Never shown to the model. */
#include <stdio.h>
#include <stddef.h>
#include "fr.h"
#include "vectors.h"

#define OUT_MAX 96U
#define SENTINEL 0xA5U

static int counts_are(const fr_rx_t *rx, uint32_t row)
{
    fr_counts_t c = fr_rx_counts(rx);
    const uint16_t *w = FXM_COUNTS[row];
    return c.frames == w[0] && c.runts == w[1] && c.crc_errors == w[2] && c.filtered == w[3]
           && c.aborts == w[4] && c.overruns == w[5];
}

static int run_case(const fxm_case_t *cs)
{
    fr_rx_t rx;
    int ok = 1;
    for (unsigned i = 0; i < cs->len; i++) {
        const fxm_step_t *s = &FXM_STEPS[cs->start + i];
        switch (s->op) {
        case 0: fr_rx_init(&rx, (uint8_t)s->a); break;
        case 1: ok &= (uint32_t)fr_rx_push(&rx, (uint8_t)s->a) == s->want; break;
        case 2: {
            size_t len = 999U;
            const uint8_t *p = fr_rx_frame(&rx, &len);
            ok &= len == s->want2 && (len == 0U || p != NULL);
            for (unsigned k = 0; ok && k < s->want2; k++) {
                ok &= p[k] == FXM_OUTS[s->want + k];
            }
            break;
        }
        case 3: ok &= counts_are(&rx, s->want); break;
        case 4:
            for (uint32_t r = 0; r < s->c; r++) {
                for (uint32_t k = 0; k < s->b; k++) {
                    (void)fr_rx_push(&rx, FXM_BLK[s->a + k]);
                }
            }
            ok &= counts_are(&rx, s->want);
            break;
        case 5: ok &= fr_crc16(&FXM_BLK[s->a], s->b) == s->want; break;
        default: {
            uint8_t out[OUT_MAX];
            for (unsigned k = 0; k < OUT_MAX; k++) {
                out[k] = (uint8_t)SENTINEL;
            }
            ok &= fr_encode((uint8_t)s->d, &FXM_BLK[s->a], s->b, out, s->c) == s->want;
            for (unsigned k = 0; k < OUT_MAX; k++) {
                ok &= out[k] == (k < s->want ? FXM_OUTS[s->want2 + k] : (uint8_t)SENTINEL);
            }
            break;
        }
        }
    }
    return ok;
}

/* H11 (C only): null pointers. */
static int null_pointers(void)
{
    static const uint8_t payload[2] = {1U, 2U};
    fr_rx_t rx;
    uint8_t out[16];
    size_t len = 999U;
    fr_counts_t c;
    int ok = 1;
    for (unsigned k = 0; k < 16U; k++) {
        out[k] = (uint8_t)SENTINEL;
    }
    fr_rx_init(NULL, 5U);
    fr_rx_init(&rx, 5U);
    ok &= fr_rx_push(NULL, 0x7EU) == FR_EV_NOTHING;
    ok &= fr_rx_frame(NULL, &len) == NULL && len == 0U;
    ok &= fr_rx_frame(&rx, NULL) == NULL;
    c = fr_rx_counts(NULL);
    ok &= c.frames == 0U && c.runts == 0U && c.crc_errors == 0U && c.filtered == 0U && c.aborts == 0U
          && c.overruns == 0U;
    ok &= fr_crc16(NULL, 5U) == 0xFFFFU;
    ok &= fr_encode(5U, payload, 2U, NULL, 16U) == 0U;
    ok &= fr_encode(5U, NULL, 2U, out, 16U) == 0U;
    for (unsigned k = 0; k < 16U; k++) {
        ok &= out[k] == (uint8_t)SENTINEL;
    }
    ok &= fr_encode(5U, NULL, 0U, out, 16U) > 0U;
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
        printf("FXM-FAIL null_pointers [H11]\n");
    }
    printf("FXM-RESULT passed=%u total=%u\n", passed, total);
    return passed == total ? 0 : 1;
}
