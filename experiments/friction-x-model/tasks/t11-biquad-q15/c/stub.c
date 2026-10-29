#include "bq.h"

bool bq_init(bq_t *f, const bq_coeffs_t *c, uint8_t m)
{
}

bool bq_step(bq_t *f, int16_t x, int16_t *y)
{
}

size_t bq_process(bq_t *f, const int16_t *in, size_t n_in, int16_t *out, size_t cap, size_t *produced)
{
}

void bq_reset(bq_t *f)
{
}

uint16_t bq_sat_count(const bq_t *f)
{
}
