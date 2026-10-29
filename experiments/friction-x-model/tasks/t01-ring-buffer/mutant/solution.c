#include "rb.h"

#include <stddef.h>

void rb_init(rb_t *rb)
{
    if (rb != NULL) {
        rb->head = 0U;
        rb->count = 0U;
    }
}

bool rb_push(rb_t *rb, uint8_t value)
{
    bool stored = false;
    if (rb != NULL) {
        uint32_t tail = ((uint32_t)rb->head + (uint32_t)rb->count) % RB_CAPACITY;
        rb->data[tail] = value; /* MUTANT: overwrites the oldest byte when full (violates R3) */
        if (rb->count < (uint8_t)RB_CAPACITY) {
            rb->count = (uint8_t)(rb->count + 1U);
        } else {
            rb->head = (uint8_t)(((uint32_t)rb->head + 1U) % RB_CAPACITY);
        }
        stored = true;
    }
    return stored;
}

bool rb_pop(rb_t *rb, uint8_t *out)
{
    bool taken = false;
    if ((rb != NULL) && (out != NULL)) {
        if (rb->count > 0U) {
            *out = rb->data[rb->head];
            rb->head = (uint8_t)(((uint32_t)rb->head + 1U) % RB_CAPACITY);
            rb->count = (uint8_t)(rb->count - 1U);
            taken = true;
        }
    }
    return taken;
}

bool rb_peek(const rb_t *rb, uint8_t *out)
{
    bool seen = false;
    if ((rb != NULL) && (out != NULL)) {
        if (rb->count > 0U) {
            *out = rb->data[rb->head];
            seen = true;
        }
    }
    return seen;
}

uint8_t rb_len(const rb_t *rb)
{
    uint8_t n = 0U;
    if (rb != NULL) {
        n = rb->count;
    }
    return n;
}
