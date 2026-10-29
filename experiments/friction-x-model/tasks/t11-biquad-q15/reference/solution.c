#include "bq.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define BQ_ONE ((int64_t)16384)
#define BQ_HALF ((int64_t)8192)
#define BQ_MAX ((int64_t)32767)
#define BQ_MIN ((int64_t)-32768)

bool bq_init(bq_t *f, const bq_coeffs_t *c, uint8_t m)
{
    bool ok = false;
    if ((f != NULL) && (c != NULL) && (m >= 1U) && (m <= BQ_MAX_DECIMATION)) {
        f->c = *c;
        f->m = m;
        f->phase = 0U;
        f->x1 = 0;
        f->x2 = 0;
        f->y1 = 0;
        f->y2 = 0;
        f->sat = 0U;
        ok = true;
    }
    return ok;
}

/* B3: acc / 16384, rounded to nearest, ties to even. */
static int64_t bq_round(int64_t acc)
{
    int64_t q = acc / BQ_ONE;
    int64_t r = acc % BQ_ONE;
    if (r < 0) {
        /* C division truncates; make q the floor and r the non-negative remainder. */
        q = q - 1;
        r = r + BQ_ONE;
    }
    if ((r > BQ_HALF) || ((r == BQ_HALF) && ((q % 2) != 0))) {
        q = q + 1;
    }
    return q;
}

static void bq_count_saturation(bq_t *f)
{
    if (f->sat < UINT16_MAX) {
        f->sat = (uint16_t)(f->sat + 1U);
    }
}

/* B2 to B5 on one sample; f is not null. */
static int16_t bq_filter(bq_t *f, int16_t x)
{
    int64_t acc = ((int64_t)f->c.b0 * (int64_t)x)
                  + ((int64_t)f->c.b1 * (int64_t)f->x1)
                  + ((int64_t)f->c.b2 * (int64_t)f->x2)
                  - ((int64_t)f->c.a1 * (int64_t)f->y1)
                  - ((int64_t)f->c.a2 * (int64_t)f->y2);
    int64_t y = bq_round(acc);
    int16_t out;
    if (y > BQ_MAX) {
        y = BQ_MAX;
        bq_count_saturation(f);
    } else if (y < BQ_MIN) {
        y = BQ_MIN;
        bq_count_saturation(f);
    } else {
        /* in range */
    }
    out = (int16_t)y;
    f->x2 = f->x1;
    f->x1 = x;
    f->y2 = f->y1;
    f->y1 = out;
    return out;
}

static bool bq_emits_next(const bq_t *f)
{
    return ((uint32_t)f->phase + 1U) == (uint32_t)f->m;
}

/* B6 and B7 on one sample; f and y are not null. */
static bool bq_take(bq_t *f, int16_t x, int16_t *y)
{
    bool emit = bq_emits_next(f);
    int16_t v = bq_filter(f, x);
    if (emit) {
        f->phase = 0U;
        *y = v;
    } else {
        f->phase = (uint8_t)(f->phase + 1U);
    }
    return emit;
}

bool bq_step(bq_t *f, int16_t x, int16_t *y)
{
    bool emitted = false;
    if ((f != NULL) && (y != NULL)) {
        emitted = bq_take(f, x, y);
    }
    return emitted;
}

size_t bq_process(bq_t *f, const int16_t *in, size_t n_in, int16_t *out, size_t cap, size_t *produced)
{
    size_t taken = 0U;
    if ((f != NULL) && (in != NULL) && (out != NULL) && (produced != NULL)) {
        size_t written = 0U;
        bool stop = false;
        while ((taken < n_in) && (!stop)) {
            if (bq_emits_next(f) && (written == cap)) {
                stop = true;
            } else {
                int16_t x = in[taken];
                int16_t y = 0;
                taken++;
                if (bq_take(f, x, &y)) {
                    out[written] = y;
                    written++;
                }
            }
        }
        *produced = written;
    }
    return taken;
}

void bq_reset(bq_t *f)
{
    if (f != NULL) {
        f->x1 = 0;
        f->x2 = 0;
        f->y1 = 0;
        f->y2 = 0;
        f->phase = 0U;
    }
}

uint16_t bq_sat_count(const bq_t *f)
{
    uint16_t n = 0U;
    if (f != NULL) {
        n = f->sat;
    }
    return n;
}
