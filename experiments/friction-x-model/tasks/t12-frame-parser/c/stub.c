#include "fr.h"

void fr_rx_init(fr_rx_t *rx, uint8_t addr)
{
}

fr_event_t fr_rx_push(fr_rx_t *rx, uint8_t byte)
{
}

const uint8_t *fr_rx_frame(const fr_rx_t *rx, size_t *len)
{
}

fr_counts_t fr_rx_counts(const fr_rx_t *rx)
{
}

uint16_t fr_crc16(const uint8_t *data, size_t n)
{
}

size_t fr_encode(uint8_t addr, const uint8_t *payload, size_t len, uint8_t *out, size_t cap)
{
}
