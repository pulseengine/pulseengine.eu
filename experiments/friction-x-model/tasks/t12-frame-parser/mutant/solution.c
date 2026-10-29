#include "fr.h"

#include <stddef.h>
#include <stdint.h>

#define FR_HUNTING 0U
#define FR_IN_FRAME 1U
#define FR_AFTER_ESC 2U
#define FR_UNESCAPE 0x20U
#define FR_COUNT_MAX 65535U

static void fr_bump(uint16_t *count)
{
    if (*count < FR_COUNT_MAX) {
        *count = (uint16_t)(*count + 1U);
    }
}

uint16_t fr_crc16(const uint8_t *data, size_t n)
{
    uint16_t crc = 0xFFFFU;
    if (data != NULL) {
        size_t k;
        for (k = 0U; k < n; k++) {
            uint32_t bit;
            crc = (uint16_t)(crc ^ (uint16_t)((uint16_t)data[k] << 8U));
            for (bit = 0U; bit < 8U; bit++) {
                if ((crc & 0x8000U) != 0U) {
                    crc = (uint16_t)((uint16_t)(crc << 1U) ^ 0x1021U);
                } else {
                    crc = (uint16_t)(crc << 1U);
                }
            }
        }
    }
    return crc;
}

void fr_rx_init(fr_rx_t *rx, uint8_t addr)
{
    if (rx != NULL) {
        rx->addr = addr;
        rx->state = FR_HUNTING;
        rx->n = 0U;
        rx->frame_len = 0U;
        rx->counts.frames = 0U;
        rx->counts.runts = 0U;
        rx->counts.crc_errors = 0U;
        rx->counts.filtered = 0U;
        rx->counts.aborts = 0U;
        rx->counts.overruns = 0U;
    }
}

/* H3 and H4: one content byte. */
static fr_event_t fr_content(fr_rx_t *rx, uint8_t byte)
{
    fr_event_t ev = FR_EV_NOTHING;
    if (rx->n < FR_MAX_CONTENT) {
        rx->buf[rx->n] = byte;
        rx->n = (uint8_t)(rx->n + 1U);
        rx->state = FR_IN_FRAME;
    } else {
        rx->state = FR_HUNTING;
        rx->n = 0U;
        fr_bump(&rx->counts.overruns);
        ev = FR_EV_OVERRUN;
    }
    return ev;
}

/* H5: the closing flag decides the event of the frame it ends. */
static fr_event_t fr_close(fr_rx_t *rx)
{
    fr_event_t ev = FR_EV_NOTHING;
    size_t n = (size_t)rx->n;
    if (n == 0U) {
        /* repeated flag */
    } else if (n < 3U) {
        fr_bump(&rx->counts.runts);
        ev = FR_EV_RUNT;
    } else {
        size_t body = n - 2U;
        uint16_t want = (uint16_t)(((uint16_t)rx->buf[body] << 8U) | (uint16_t)rx->buf[body + 1U]);
        if (fr_crc16(rx->buf, body) != want) {
            fr_bump(&rx->counts.crc_errors);
            ev = FR_EV_BAD_CRC;
        } else if ((rx->buf[0] != rx->addr) && (rx->buf[0] != FR_BROADCAST)) {
            fr_bump(&rx->counts.filtered);
            ev = FR_EV_FILTERED;
        } else {
            size_t k;
            size_t len = body - 1U;
            for (k = 0U; k < len; k++) {
                rx->frame[k] = rx->buf[k + 1U];
            }
            rx->frame_len = (uint8_t)len;
            fr_bump(&rx->counts.frames);
            ev = FR_EV_FRAME;
        }
    }
    return ev;
}

fr_event_t fr_rx_push(fr_rx_t *rx, uint8_t byte)
{
    fr_event_t ev = FR_EV_NOTHING;
    if (rx != NULL) {
        if (rx->state == FR_HUNTING) {
            if (byte == FR_FLAG) {
                rx->state = FR_IN_FRAME;
                rx->n = 0U;
            }
        } else if (byte == FR_FLAG) {
            if (rx->state == FR_AFTER_ESC) {
                fr_bump(&rx->counts.aborts);
                ev = FR_EV_ABORT;
                /* MUTANT: an abort makes the receiver hunt instead of opening a new frame (violates H6) */
                rx->state = FR_HUNTING;
            } else {
                ev = fr_close(rx);
                rx->state = FR_IN_FRAME;
            }
            rx->n = 0U;
        } else if (rx->state == FR_AFTER_ESC) {
            ev = fr_content(rx, (uint8_t)(byte ^ FR_UNESCAPE));
        } else if (byte == FR_ESC) {
            rx->state = FR_AFTER_ESC;
        } else {
            ev = fr_content(rx, byte);
        }
    }
    return ev;
}

const uint8_t *fr_rx_frame(const fr_rx_t *rx, size_t *len)
{
    const uint8_t *p = NULL;
    if (len != NULL) {
        *len = 0U;
        if (rx != NULL) {
            *len = (size_t)rx->frame_len;
            p = rx->frame;
        }
    }
    return p;
}

fr_counts_t fr_rx_counts(const fr_rx_t *rx)
{
    fr_counts_t c = {0U, 0U, 0U, 0U, 0U, 0U};
    if (rx != NULL) {
        c = rx->counts;
    }
    return c;
}

static size_t fr_wire_len(uint8_t byte)
{
    size_t n = 1U;
    if ((byte == FR_FLAG) || (byte == FR_ESC)) {
        n = 2U;
    }
    return n;
}

static size_t fr_put(uint8_t *out, size_t at, uint8_t byte)
{
    size_t k = at;
    if ((byte == FR_FLAG) || (byte == FR_ESC)) {
        out[k] = (uint8_t)FR_ESC;
        k++;
        out[k] = (uint8_t)(byte ^ FR_UNESCAPE);
    } else {
        out[k] = byte;
    }
    return k + 1U;
}

size_t fr_encode(uint8_t addr, const uint8_t *payload, size_t len, uint8_t *out, size_t cap)
{
    size_t total = 0U;
    if ((out != NULL) && ((payload != NULL) || (len == 0U)) && (len <= FR_MAX_PAYLOAD)) {
        uint8_t whole[FR_MAX_PAYLOAD + 1U];
        uint16_t crc;
        uint8_t hi;
        uint8_t lo;
        size_t need;
        size_t k;
        whole[0] = addr;
        for (k = 0U; k < len; k++) {
            whole[k + 1U] = payload[k];
        }
        crc = fr_crc16(whole, len + 1U);
        hi = (uint8_t)(crc >> 8U);
        lo = (uint8_t)(crc & 0xFFU);
        need = 2U + fr_wire_len(hi) + fr_wire_len(lo);
        for (k = 0U; k <= len; k++) {
            need += fr_wire_len(whole[k]);
        }
        if (cap >= need) {
            size_t at = 0U;
            out[at] = (uint8_t)FR_FLAG;
            at++;
            for (k = 0U; k <= len; k++) {
                at = fr_put(out, at, whole[k]);
            }
            at = fr_put(out, at, hi);
            at = fr_put(out, at, lo);
            out[at] = (uint8_t)FR_FLAG;
            total = need;
        }
    }
    return total;
}
