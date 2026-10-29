"""Hidden test vectors for t12, from one Python reference model.

Writes vectors.h (C) and vectors.rs (Rust) from the same cases, so both
languages are judged against the same behaviour. Every case names the spec
sentences (H1..H10) it checks. `fxm.py self-test` regenerates these in memory and
fails if the committed files differ.

FXM-HIDDEN-CANARY-t12 (this marker must never reach a model prompt)
"""
import pathlib
import random
import sys

CANARY = "FXM-HIDDEN-CANARY-t12"
SEED = 20261031
FLAG, ESC, BROADCAST, MAX_PAYLOAD, MAX_CONTENT = 0x7E, 0x7D, 0xFF, 32, 35
NOTHING, FRAME, RUNT, BAD_CRC, FILTERED, ABORT, OVERRUN = range(7)
COUNT_OF = {FRAME: 0, RUNT: 1, BAD_CRC: 2, FILTERED: 3, ABORT: 4, OVERRUN: 5}
CNT_MAX = 65535
# Step ops (op, a, b, c, d, want, want2):
# INIT: a = address. PUSH: a = byte, want = event. FRAME_Q: (want, want2) = the payload in OUTS.
# COUNTS_Q: want = row of COUNTS. REPEAT: push BLK[a .. a + b] c times, events unchecked; want = row
# of COUNTS after it. CRC: BLK[a .. a + b]; want = the crc. ENCODE: payload BLK[a .. a + b], c = output
# capacity, d = address; want = returned length, want2 = start of the expected output in OUTS.
INIT, PUSH, FRAME_Q, COUNTS_Q, REPEAT, CRC, ENCODE = range(7)


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def content(addr, payload, crc=None):
    c = crc16([addr, *payload]) if crc is None else crc
    return [addr, *payload, c >> 8, c & 0xFF]


def stuff(cont):
    out = []
    for b in cont:
        out += [ESC, b ^ 0x20] if b in (FLAG, ESC) else [b]
    return out


def wire(addr, payload, crc=None):
    return [FLAG, *stuff(content(addr, payload, crc)), FLAG]


def encode(addr, payload, cap):
    if len(payload) > MAX_PAYLOAD:
        return 0, []
    w = wire(addr, payload)
    return (len(w), w) if cap >= len(w) else (0, [])


class Rx:
    def __init__(self, addr):
        self.addr, self.hunting, self.esc, self.buf = addr, True, False, []
        self.frame, self.counts = [], [0] * 6

    def count(self, ev):
        k = COUNT_OF[ev]
        self.counts[k] = min(self.counts[k] + 1, CNT_MAX)
        return ev

    def push(self, b):
        if self.hunting:
            if b == FLAG:
                self.hunting, self.esc, self.buf = False, False, []
            return NOTHING
        if b == FLAG:
            if self.esc:
                self.esc, self.buf = False, []
                return self.count(ABORT)
            cont, self.buf = self.buf, []
            if not cont:
                return NOTHING
            if len(cont) < 3:
                return self.count(RUNT)
            if crc16(cont[:-2]) != (cont[-2] << 8 | cont[-1]):
                return self.count(BAD_CRC)
            if cont[0] not in (self.addr, BROADCAST):
                return self.count(FILTERED)
            self.frame = cont[1:-2]
            return self.count(FRAME)
        if b == ESC and not self.esc:
            self.esc = True
            return NOTHING
        if self.esc:
            b ^= 0x20
            self.esc = False
        if len(self.buf) == MAX_CONTENT:
            self.hunting, self.buf = True, []
            return self.count(OVERRUN)
        self.buf.append(b)
        return NOTHING


def cases():
    blk, outs, counts_tab, steps, table = [], [], [], [], []

    def put(seq, data):
        start = len(seq)
        seq.extend(data)
        return start

    def counts_index(c):
        c = tuple(c)
        if c not in counts_tab:
            counts_tab.append(c)
        return counts_tab.index(c)

    class Case:
        def __init__(self, name, req, addr):
            self.name, self.req, self.rx, self.start = name, req, Rx(addr), len(steps)
            steps.append((INIT, addr, 0, 0, 0, 0, 0))

        def push(self, data, check_frame=True):
            for b in data:
                ev = self.rx.push(b)
                steps.append((PUSH, b, 0, 0, 0, ev, 0))
                if ev == FRAME and check_frame:
                    self.frame()
            return self

        def frame(self):
            steps.append((FRAME_Q, 0, 0, 0, 0, put(outs, self.rx.frame), len(self.rx.frame)))
            return self

        def counts(self):
            steps.append((COUNTS_Q, 0, 0, 0, 0, counts_index(self.rx.counts), 0))
            return self

        def repeat(self, data, k):
            for _ in range(k):
                for b in data:
                    self.rx.push(b)
            steps.append((REPEAT, put(blk, data), len(data), k, 0, counts_index(self.rx.counts), 0))
            return self

        def done(self):
            table.append((self.name, self.req, self.start, len(steps) - self.start))

    def case(name, req, addr=0x05):
        return Case(name, req, addr)

    me, other = 0x05, 0x06
    good = wire(me, [1, 2, 3])
    case("new_receiver", "H1 H7 H8").frame().counts().done()
    case("one_frame", "H3 H5").push(good).counts().done()
    case("empty_payload_frame", "H5").push(wire(me, [])).counts().done()
    case("max_payload_frame", "H4 H5").push(wire(me, list(range(0x40, 0x60)))).counts().done()
    case("broadcast_accepted", "H5").push(wire(BROADCAST, [9])).counts().done()
    case("other_address_filtered", "H5").push(wire(other, [9])).frame().counts().done()
    case("receiver_at_broadcast_address", "H5", addr=BROADCAST).push(wire(0xFF, [1])) \
        .push(wire(0x00, [2])).counts().done()
    case("hunting_ignores_bytes_before_first_flag", "H2").push([1, 2, 3, ESC, 0x5E] + good).counts().done()
    case("hunting_ignores_esc_before_flag", "H2 H6").push([ESC, FLAG] + good[1:]).counts().done()
    case("repeated_flags_between_frames", "H5").push([FLAG] * 4 + good + [FLAG] * 3 + good).counts().done()
    case("shared_flag_between_frames", "H5").push(good + good[1:] + wire(me, [7])[1:]).counts().done()
    case("runt_one_byte", "H5").push([FLAG, me, FLAG]).frame().counts().done()
    case("runt_two_bytes", "H5").push([FLAG, me, 0x00, FLAG]).counts().push(good).counts().done()
    case("three_bytes_is_a_frame_not_a_runt", "H5").push([FLAG, *stuff(content(me, [])), FLAG]).counts().done()
    case("bad_crc", "H5").push(wire(me, [1, 2, 3], crc=0x1234)).frame().counts().done()
    case("bad_crc_before_filter", "H5").push(wire(other, [1], crc=0)).counts().done()
    swapped = content(me, [1])
    case("crc_byte_order", "H5").push([FLAG, *stuff([me, 1, swapped[3], swapped[2]]), FLAG]).counts().done()
    case("escaped_flag_in_payload", "H3 H5").push(wire(me, [FLAG, ESC, FLAG])).counts().done()
    case("escaped_crc_bytes", "H3 H5").push(wire(me, [0x2F])).push(wire(me, [0x01, 0xC3])).counts().done()
    case("esc_esc_gives_0x5d", "H3", addr=0x5D).push([FLAG, ESC, ESC, *stuff(content(0x5D, [])[1:]), FLAG]) \
        .counts().done()
    case("esc_unescapes_any_byte", "H3").push([FLAG, ESC, me ^ 0x20, *stuff(content(me, [0x41])[1:]), FLAG]) \
        .counts().done()
    case("unnecessary_escape_of_payload_byte", "H3").push(
        [FLAG, me, ESC, 0x41 ^ 0x20, *stuff(content(me, [0x41])[2:]), FLAG]).counts().done()
    case("abort_mid_frame", "H6").push([FLAG, me, 1, 2, ESC, FLAG]).counts().push(good[1:]).counts().done()
    case("abort_with_no_content", "H6").push([FLAG, ESC, FLAG]).counts().done()
    case("abort_opens_new_frame", "H6").push([FLAG, 1, ESC, FLAG, *good[1:]]).frame().counts().done()
    case("double_abort", "H6").push([FLAG, ESC, FLAG, ESC, FLAG]).counts().done()
    case("esc_esc_then_flag_is_close_not_abort", "H3 H5 H6").push([FLAG, me, ESC, ESC, FLAG]).counts().done()
    case("overrun_on_36th_content_byte", "H4").push([FLAG] + [0x11] * 36).counts().push([0x22, FLAG]) \
        .push(good[1:]).counts().done()
    case("overrun_hunts_through_esc", "H2 H4").push([FLAG] + [0x11] * 36 + [ESC, FLAG]).counts() \
        .push(good[1:]).counts().done()
    case("exactly_35_content_bytes_is_not_overrun", "H4").push(
        [FLAG, *stuff(content(me, [0x33] * 32)), FLAG]).counts().done()
    case("overrun_counted_on_escaped_byte", "H3 H4").push([FLAG] + [0x11] * 35 + [ESC, 0x5D]).counts().done()
    case("esc_does_not_count_as_content", "H3 H4").push([FLAG] + [ESC, 0x31] * 35 + [FLAG]).counts().done()
    keep = wire(me, [0xA1, 0xA2, 0xA3, 0xA4])
    case("accepted_frame_survives_later_bytes", "H7").push(keep).push([me, 9, 9, 9]).frame() \
        .push([ESC, FLAG]).frame().push(wire(other, [7, 7])).frame().push([0x11] * 40).frame().counts().done()
    case("accepted_frame_survives_bad_crc_and_runts", "H7").push(keep).push(wire(me, [5, 5, 5, 5, 5], crc=1)) \
        .frame().push([FLAG, me, FLAG]).frame().push(wire(me, [6])).counts().done()
    case("accepted_frame_shorter_replaces_longer", "H7").push(keep).push(wire(me, [0xB1])).push(wire(me, [])) \
        .counts().done()
    case("counts_stop_at_65535", "H8").repeat([FLAG, me, FLAG], 70000).counts().repeat([FLAG, ESC, FLAG], 65534) \
        .counts().repeat([FLAG, ESC, FLAG], 3).counts().push(good).counts().done()

    rng = random.Random(SEED)
    for s in range(30):
        c = case(f"random_stream_{s:02d}", "H2 H3 H4 H5 H6 H7 H8", addr=rng.choice([me, 0x00, 0x7E, 0x7D, 0xFF]))
        for _ in range(rng.randint(3, 9)):
            r = rng.random()
            pl = [rng.choice([FLAG, ESC, 0x5E, 0x5D, rng.randrange(256)]) for _ in range(rng.randint(0, 33))]
            addr = rng.choice([c.rx.addr, c.rx.addr, BROADCAST, rng.randrange(256)])
            w = wire(addr, pl)
            if r < 0.4:
                c.push(w)
            elif r < 0.55:
                c.push([rng.choice([FLAG, ESC, rng.randrange(256)]) for _ in range(rng.randint(1, 8))])
            elif r < 0.7:
                k = rng.randrange(1, len(w) - 1)
                w[k] ^= 1 << rng.randrange(8)
                c.push(w)
            elif r < 0.8:
                c.push(w[:rng.randrange(1, len(w))])
            elif r < 0.9:
                k = rng.randrange(1, len(w) - 1)
                c.push(w[:k] + [ESC, FLAG] + w[k:])
            else:
                c.push([FLAG] + [rng.randrange(256) for _ in range(rng.randint(30, 45))])
            if rng.random() < 0.4:
                c.frame()
        c.counts().frame().done()

    def row(name, req, op, data, cap=0, addr=0):
        start = len(steps)
        if op == CRC:
            steps.append((CRC, put(blk, data), len(data), 0, 0, crc16(data), 0))
        else:
            n, w = encode(addr, data, cap)
            steps.append((ENCODE, put(blk, data), len(data), cap, addr, n, put(outs, w)))
        table.append((name, req, start, 1))

    row("crc_check_value", "H9", CRC, [ord(ch) for ch in "123456789"])
    row("crc_empty", "H9", CRC, [])
    row("crc_zero_byte", "H9", CRC, [0])
    row("crc_all_ones", "H9", CRC, [0xFF] * 4)
    for s in range(10):
        row(f"random_crc_{s:02d}", "H9", CRC, [rng.randrange(256) for _ in range(rng.randint(1, 40))])
    row("encode_plain", "H10", ENCODE, [1, 2, 3], 16, me)
    row("encode_empty_payload", "H10", ENCODE, [], 8, me)
    row("encode_stuffs_flag_and_esc", "H10", ENCODE, [FLAG, ESC, 0x5E, 0x5D], 20, FLAG)
    row("encode_stuffs_address_and_crc", "H10", ENCODE, [0x2F], 20, ESC)
    row("encode_max_payload", "H10", ENCODE, [FLAG] * 32, 80, me)
    row("encode_payload_33_rejected", "H10", ENCODE, [0] * 33, 80, me)
    row("encode_exact_room", "H10", ENCODE, [1, 2, 3], len(wire(me, [1, 2, 3])), me)
    row("encode_one_short", "H10", ENCODE, [1, 2, FLAG], len(wire(me, [1, 2, FLAG])) - 1, me)
    row("encode_room_counts_stuffing", "H10", ENCODE, [FLAG, FLAG], 7, me)
    row("encode_output_empty", "H10", ENCODE, [], 0, me)
    for s in range(8):
        pl = [rng.choice([FLAG, ESC, rng.randrange(256)]) for _ in range(rng.randint(0, 32))]
        a = rng.randrange(256)
        row(f"random_encode_{s:02d}", "H10", ENCODE, pl, len(wire(a, pl)) + rng.randint(-2, 2), a)
    return steps, table, blk, outs, counts_tab


def generate():
    steps, table, blk, outs, counts_tab = cases()
    head = f"/* {CANARY}: generated by gen_vectors.py; do not edit. Hidden from the model. */\n"
    c = [head, "#ifndef FXM_VECTORS_H\n#define FXM_VECTORS_H\n#include <stdint.h>\n",
         "typedef struct { uint8_t op; uint32_t a; uint32_t b; uint32_t c; uint32_t d; uint32_t want; "
         "uint32_t want2; } fxm_step_t;\n",
         "typedef struct { const char *name; const char *req; uint32_t start; uint32_t len; } fxm_case_t;\n",
         "static const uint8_t FXM_BLK[] = {\n"]
    c += [f"    {v}U,\n" for v in blk]
    c += ["};\nstatic const uint8_t FXM_OUTS[] = {\n"]
    c += [f"    {v}U,\n" for v in outs]
    c += ["};\nstatic const uint16_t FXM_COUNTS[][6] = {\n"]
    c += ["    {" + ", ".join(f"{v}U" for v in k) + "},\n" for k in counts_tab]
    c += ["};\nstatic const fxm_step_t FXM_STEPS[] = {\n"]
    c += ["    {%dU, %dU, %dU, %dU, %dU, %dU, %dU},\n" % s for s in steps]
    c += ["};\nstatic const fxm_case_t FXM_CASES[] = {\n"]
    c += [f'    {{"{n}", "{r}", {s}U, {ln}U}},\n' for n, r, s, ln in table]
    c += [f"}};\n#define FXM_N_CASES {len(table)}U\n#endif\n"]
    rs = [f"// {CANARY}: generated by gen_vectors.py; do not edit. Hidden from the model.\n",
          "#[rustfmt::skip]\npub const BLK: &[u8] = &[\n"]
    rs += [f"    {v},\n" for v in blk]
    rs += ["];\n#[rustfmt::skip]\npub const OUTS: &[u8] = &[\n"]
    rs += [f"    {v},\n" for v in outs]
    rs += ["];\n#[rustfmt::skip]\npub const COUNTS: &[[u16; 6]] = &[\n"]
    rs += ["    [" + ", ".join(str(v) for v in k) + "],\n" for k in counts_tab]
    rs += ["];\n#[rustfmt::skip]\npub const STEPS: &[(u8, u32, u32, u32, u32, u32, u32)] = &[\n"]
    rs += ["    (%d, %d, %d, %d, %d, %d, %d),\n" % s for s in steps]
    rs += ["];\n#[rustfmt::skip]\npub const CASES: &[(&str, &str, usize, usize)] = &[\n"]
    rs += [f'    ("{n}", "{r}", {s}, {ln}),\n' for n, r, s, ln in table]
    rs += ["];\n"]
    return {"vectors.h": "".join(c), "vectors.rs": "".join(rs)}


if __name__ == "__main__":
    here = pathlib.Path(__file__).parent
    for name, text in generate().items():
        (here / name).write_text(text)
    print(f"wrote {len(generate())} files", file=sys.stderr)
