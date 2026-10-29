#ifndef FR_H
#define FR_H

#include <stddef.h>
#include <stdint.h>

#define FR_FLAG 0x7EU
#define FR_ESC 0x7DU
#define FR_BROADCAST 0xFFU
#define FR_MAX_PAYLOAD 32U
#define FR_MAX_CONTENT 35U /* address + payload + 2 CRC bytes */

typedef enum {
    FR_EV_NOTHING = 0,
    FR_EV_FRAME = 1,
    FR_EV_RUNT = 2,
    FR_EV_BAD_CRC = 3,
    FR_EV_FILTERED = 4,
    FR_EV_ABORT = 5,
    FR_EV_OVERRUN = 6
} fr_event_t;

typedef struct {
    uint16_t frames;
    uint16_t runts;
    uint16_t crc_errors;
    uint16_t filtered;
    uint16_t aborts;
    uint16_t overruns;
} fr_counts_t;

typedef struct {
    uint8_t addr;                    /* the receiver's own address */
    uint8_t state;                   /* yours */
    uint8_t n;                       /* content bytes of the open frame */
    uint8_t buf[FR_MAX_CONTENT];     /* content of the open frame */
    uint8_t frame[FR_MAX_PAYLOAD];   /* payload of the accepted frame */
    uint8_t frame_len;               /* its length */
    fr_counts_t counts;
} fr_rx_t;

void fr_rx_init(fr_rx_t *rx, uint8_t addr);
fr_event_t fr_rx_push(fr_rx_t *rx, uint8_t byte);
const uint8_t *fr_rx_frame(const fr_rx_t *rx, size_t *len);
fr_counts_t fr_rx_counts(const fr_rx_t *rx);
uint16_t fr_crc16(const uint8_t *data, size_t n);
size_t fr_encode(uint8_t addr, const uint8_t *payload, size_t len, uint8_t *out, size_t cap);

#endif /* FR_H */
