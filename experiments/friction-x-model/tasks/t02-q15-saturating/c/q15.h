#ifndef Q15_H
#define Q15_H

#include <stdint.h>

typedef int16_t q15_t;

q15_t q15_add(q15_t a, q15_t b);
q15_t q15_sub(q15_t a, q15_t b);
q15_t q15_mul(q15_t a, q15_t b);
q15_t q15_neg(q15_t a);
q15_t q15_abs(q15_t a);

#endif /* Q15_H */
