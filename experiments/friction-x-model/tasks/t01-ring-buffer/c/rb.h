#ifndef RB_H
#define RB_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define RB_CAPACITY 16U

typedef struct {
    uint8_t data[RB_CAPACITY];
    uint8_t head;  /* index of the oldest stored byte */
    uint8_t count; /* number of stored bytes, 0 to RB_CAPACITY */
} rb_t;

void rb_init(rb_t *rb);
bool rb_push(rb_t *rb, uint8_t value);
bool rb_pop(rb_t *rb, uint8_t *out);
bool rb_peek(const rb_t *rb, uint8_t *out);
uint8_t rb_len(const rb_t *rb);

#endif /* RB_H */
