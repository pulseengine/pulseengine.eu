/* Calls every function declared in fr.h, and nothing else. Not a test. */
#include <stddef.h>
#include <stdint.h>
#include "fr.h"

int main(void)
{
    fr_rx_t fxm_rx;
    const uint8_t fxm_payload[2] = {1U, 2U};
    uint8_t fxm_wire[12] = {0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U};
    size_t fxm_n = fr_encode(5U, fxm_payload, 2U, fxm_wire, 12U);
    size_t fxm_k;
    size_t fxm_len = 0U;
    fr_event_t fxm_last = FR_EV_NOTHING;
    const uint8_t *fxm_got;
    fr_counts_t fxm_counts;
    int fxm_rc = 0;

    fr_rx_init(&fxm_rx, 5U);
    for (fxm_k = 0U; fxm_k < fxm_n; fxm_k++) {
        fxm_last = fr_rx_push(&fxm_rx, fxm_wire[fxm_k]);
    }
    fxm_got = fr_rx_frame(&fxm_rx, &fxm_len);
    fxm_counts = fr_rx_counts(&fxm_rx);
    if ((fxm_last != FR_EV_FRAME) || (fxm_got == NULL) || (fxm_len != 2U) || (fxm_counts.frames != 1U)
        || (fr_crc16(fxm_payload, 2U) == 0U)) {
        fxm_rc = 1;
    }
    return fxm_rc;
}
