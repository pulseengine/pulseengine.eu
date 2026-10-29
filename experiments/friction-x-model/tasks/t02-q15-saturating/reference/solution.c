#include "q15.h"

#define Q15_MAX_I32 ((int32_t)32767)
#define Q15_MIN_I32 ((int32_t)-32768)

static q15_t q15_clamp(int32_t x)
{
    int32_t r = x;
    if (r > Q15_MAX_I32) {
        r = Q15_MAX_I32;
    } else if (r < Q15_MIN_I32) {
        r = Q15_MIN_I32;
    } else {
        /* in range */
    }
    return (q15_t)r;
}

q15_t q15_add(q15_t a, q15_t b)
{
    return q15_clamp((int32_t)a + (int32_t)b);
}

q15_t q15_sub(q15_t a, q15_t b)
{
    return q15_clamp((int32_t)a - (int32_t)b);
}

q15_t q15_mul(q15_t a, q15_t b)
{
    int32_t r = ((int32_t)a * (int32_t)b) + (int32_t)16384;
    int32_t q = r / (int32_t)32768;
    if (((r % (int32_t)32768) != 0) && (r < 0)) {
        q = q - 1;
    }
    return q15_clamp(q);
}

q15_t q15_neg(q15_t a)
{
    return q15_clamp(-(int32_t)a);
}

q15_t q15_abs(q15_t a)
{
    int32_t x = (int32_t)a;
    if (x < 0) {
        x = -x;
    }
    return q15_clamp(x);
}
