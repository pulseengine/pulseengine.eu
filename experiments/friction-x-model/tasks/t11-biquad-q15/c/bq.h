#ifndef BQ_H
#define BQ_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define BQ_MAX_DECIMATION 8U

typedef struct {
    int16_t b0;
    int16_t b1;
    int16_t b2;
    int16_t a1;
    int16_t a2;
} bq_coeffs_t;

typedef struct {
    bq_coeffs_t c; /* Q14 coefficients */
    uint8_t m;     /* decimation factor, 1 to BQ_MAX_DECIMATION */
    uint8_t phase; /* 0 to m - 1 */
    int16_t x1;    /* previous input */
    int16_t x2;    /* input before x1 */
    int16_t y1;    /* previous filter output */
    int16_t y2;    /* filter output before y1 */
    uint16_t sat;  /* saturation count, stops at 65535 */
} bq_t;

bool bq_init(bq_t *f, const bq_coeffs_t *c, uint8_t m);
bool bq_step(bq_t *f, int16_t x, int16_t *y);
size_t bq_process(bq_t *f, const int16_t *in, size_t n_in, int16_t *out, size_t cap, size_t *produced);
void bq_reset(bq_t *f);
uint16_t bq_sat_count(const bq_t *f);

#endif /* BQ_H */
