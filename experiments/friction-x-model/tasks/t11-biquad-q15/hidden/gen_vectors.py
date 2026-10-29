"""Hidden test vectors for t11, from one Python reference model.

Writes vectors.h (C) and vectors.rs (Rust) from the same cases, so both
languages are judged against the same behaviour. Every case names the spec
sentences (B1..B10) it checks. `fxm.py self-test` regenerates these in memory and
fails if the committed files differ.

FXM-HIDDEN-CANARY-t11 (this marker must never reach a model prompt)
"""
import pathlib
import random
import sys

CANARY = "FXM-HIDDEN-CANARY-t11"
SEED = 20261030
LO, HI = -32768, 32767
SAT_MAX = 65535
INIT, STEP, PROCESS, IN_PLACE, RESET, SAT, REPEAT = 0, 1, 2, 3, 4, 5, 6
NONE = 99999      # "no output emitted"
SENTINEL = 23130  # 0x5A5A: an output position the filter must not write

# Coefficient sets (b0, b1, b2, a1, a2), Q14.
BASE_COEFFS = [
    (16384, 0, 0, 0, 0),                      # 0 identity
    (8192, 0, 0, 0, 0),                       # 1 one half: odd inputs are exact ties
    (32767, 32767, 32767, -32768, -32768),    # 2 extreme: the sum leaves 32 bits
    (-32768, -32768, -32768, 32767, 32767),   # 3 extreme, other signs
    (1105, 2210, 1105, -18727, 6763),         # 4 low-pass, about 0.1 fs
    (16384, 0, -16384, -31785, 15729),        # 5 band-pass resonator, r ~ 0.98
    (0, 8192, 8192, 0, 0),                    # 6 delayed halves: ties on the state taps
    (-32768, 0, 0, 0, 0),                     # 7 inverting by -2
    (0, 0, 0, -16384, 0),                     # 8 pure feedback y = y1
    (12288, 0, 0, 0, -8192),                  # 9 three quarters, a2 tie source
]


def clamp(v):
    return max(LO, min(HI, v))


class Model:
    def __init__(self, c, m):
        self.c, self.m = c, m
        self.x1 = self.x2 = self.y1 = self.y2 = self.phase = self.sat = 0

    def filt(self, x):
        b0, b1, b2, a1, a2 = self.c
        acc = b0 * x + b1 * self.x1 + b2 * self.x2 - a1 * self.y1 - a2 * self.y2
        q, r = divmod(acc, 16384)        # Python: floor quotient, non-negative remainder
        if r > 8192 or (r == 8192 and q % 2 == 1):
            q += 1
        y = clamp(q)
        if y != q:
            self.sat = min(self.sat + 1, SAT_MAX)
        self.x2, self.x1, self.y2, self.y1 = self.x1, x, self.y1, y
        return y

    def step(self, x):
        y = self.filt(x)
        if self.phase == self.m - 1:
            self.phase = 0
            return y
        self.phase += 1
        return None

    def process(self, xs, cap):
        taken, outs = 0, []
        for x in xs:
            if self.phase == self.m - 1 and len(outs) == cap:
                break
            y = self.step(x)
            taken += 1
            if y is not None:
                outs.append(y)
        return taken, outs

    def reset(self):
        self.x1 = self.x2 = self.y1 = self.y2 = self.phase = 0


class Case:
    """Builds one case: steps (op, a, b, c, want, want2) and the block data they use."""

    def __init__(self, coeffs, blk_in, blk_out):
        self.steps, self.m, self.coeffs, self.blk_in, self.blk_out = [], None, coeffs, blk_in, blk_out

    def init(self, k, m=1):
        ok = 1 <= m <= 8
        if ok:
            self.m = Model(self.coeffs[k], m)
        self.steps.append((INIT, k, m, 0, int(ok), 0))
        return self

    def step(self, *xs):
        for x in xs:
            y = self.m.step(x)
            self.steps.append((STEP, x, 0, 0, NONE if y is None else y, 0))
        return self

    def _block(self, op, xs, cap):
        start = len(self.blk_in)
        taken, outs = self.m.process(xs, cap)
        self.blk_in += xs
        # in place, the positions after the outputs still hold the input
        pad = xs[len(outs):] if op == IN_PLACE else [SENTINEL] * (len(xs) - len(outs))
        self.blk_out += outs + pad
        self.steps.append((op, start, len(xs), cap, taken, len(outs)))
        return self

    def process(self, xs, cap):
        return self._block(PROCESS, xs, cap)

    def in_place(self, xs, cap=None):
        return self._block(IN_PLACE, xs, len(xs) if cap is None else min(cap, len(xs)))

    def reset(self):
        self.m.reset()
        self.steps.append((RESET, 0, 0, 0, 0, 0))
        return self

    def sat(self):
        self.steps.append((SAT, 0, 0, 0, self.m.sat, 0))
        return self

    def repeat(self, x, k):
        emitted, last = 0, 0
        for _ in range(k):
            y = self.m.step(x)
            if y is not None:
                emitted, last = emitted + 1, y
        self.steps.append((REPEAT, x, k, 0, emitted, last))
        return self


def cases():
    coeffs, blk_in, blk_out, out = list(BASE_COEFFS), [], [], []

    def case(name, req):
        c = Case(coeffs, blk_in, blk_out)
        out.append((name, req, c))
        return c

    case("new_has_zero_state", "B1 B10").init(4).sat().step(0, 0, 0).sat()
    case("decimation_factor_out_of_range", "B1").init(0, 1).step(5, 6).init(0, 0).step(7).init(0, 9).step(8) \
        .init(4, 255).step(9)
    case("decimation_factor_limits", "B1 B6").init(0, 8).step(*range(1, 18)).init(0, 1).step(3, 4)
    case("identity_passes_input", "B2 B3").init(0).step(LO, -1, 0, 1, HI, 12345, -12345)
    case("ties_round_to_even_positive", "B3").init(1).step(1, 3, 5, 7, 9, 11, 32767)
    case("ties_round_to_even_negative", "B3").init(1).step(-1, -3, -5, -7, -9, -11, -32767, -32768)
    case("ties_on_state_taps", "B3 B5").init(6).step(1, 2, 3, -1, -2, -3, 5, -5, 0, 0)
    case("tie_on_feedback_tap", "B3 B5").init(9).step(1, 0, 0, 0, 3, 0, -1, 0, 0, 0)
    case("near_ties_round_to_nearest", "B3").init(4).step(1, 2, 3, 100, -100, 30000, -30000, 7, -7)
    case("exact_sum_beyond_32_bits", "B2 B4").init(2).step(HI, HI, HI, LO, LO, LO, HI, LO).sat()
    case("exact_sum_beyond_32_bits_other_signs", "B2 B4").init(3).step(LO, LO, HI, HI, LO, HI).sat()
    case("inverting_by_minus_two_saturates", "B4").init(7).step(16383, 16384, -16384, -16385, LO, HI, 0).sat()
    case("state_holds_clamped_output", "B4 B5").init(2).step(HI, 0, 0, 0, 0, 0, 0, 0).sat()
    case("saturation_count_stops_at_65535", "B4 B10").init(7).repeat(HI, 70000).sat().step(LO).sat()
    case("saturation_count_exactly_65535", "B4 B10").init(7, 3).repeat(LO, 65535).sat().step(HI).sat()
    case("resonator_rings", "B2 B3 B5").init(5).step(HI, *[0] * 40).sat()
    case("low_pass_step_response", "B2 B3 B5").init(4).step(*[20000] * 40).step(*[-20000] * 20)
    case("decimate_by_3_emits_every_third", "B6 B7").init(4, 3).step(*[20000] * 12)
    case("decimate_state_runs_on_dropped_samples", "B5 B6").init(6, 2).step(1, 3, 5, 7, 9, 11)
    case("decimate_saturation_counted_on_dropped", "B4 B6").init(7, 4).step(HI, HI, HI, 0).sat().step(HI).sat()
    case("reset_clears_state_and_phase", "B9").init(4, 3).step(30000, 30000).reset().step(30000, 30000, 30000)
    case("reset_keeps_count", "B9").init(2, 2).step(HI, HI, HI).sat().reset().sat().step(1, 0, 0, 0).sat()
    case("reset_keeps_coefficients_and_factor", "B9").init(4, 2).step(*[30000] * 5).reset().step(*[30000] * 5)
    case("reset_on_fresh_filter", "B1 B9").init(5).reset().step(HI, 0, 0, 0).sat()
    case("sat_query_changes_nothing", "B10").init(2).step(HI, HI).sat().sat().step(HI).sat()
    case("process_m1_equal_lengths", "B8").init(4).process([30000, -30000, 123, -123, 0, 7, HI, LO], 8)
    case("process_m1_output_short", "B8").init(4).process([1000 * k for k in range(10)], 4).step(0, 0)
    case("process_m1_output_empty", "B8").init(4).process([5, 6, 7], 0).step(9)
    case("process_m3_room_for_all", "B6 B8").init(4, 3).process([20000] * 9, 3)
    case("process_m3_output_full_takes_non_emitting", "B6 B8").init(4, 3).process([20000] * 9, 1).step(1, 2, 3)
    case("process_m3_output_empty_takes_up_to_emit", "B6 B8").init(4, 3).process([20000] * 9, 0) \
        .process([20000] * 9, 0).step(5)
    case("process_phase_carries_over", "B6 B8").init(4, 4).process([1, 2, 3], 5).process([4, 5, 6, 7, 8], 5) \
        .process([9], 5).step(10, 11, 12)
    case("process_mixed_with_step", "B7 B8").init(5, 2).step(HI).process([0] * 7, 2).step(0).process([0] * 5, 9)
    case("process_empty_input", "B8").init(0, 2).process([], 5).process([5], 0).step(9)
    case("process_saturates_and_counts", "B4 B8").init(2, 2).process([HI] * 6 + [LO] * 6, 12).sat()
    case("in_place_m1", "B8").init(5).in_place([HI, 0, 0, 0, -5000, 0, 0, 0, 100, 0]).step(0)
    case("in_place_m2", "B8").init(6, 2).in_place([1, 2, 3, 4, 5, -1, -2, -3]).sat()
    case("in_place_m4_short_output", "B8").init(4, 4).in_place([HI] * 12, 2).step(1)
    case("in_place_extreme", "B2 B4 B8").init(3, 1).in_place([LO, HI, LO, HI, LO, HI]).sat()

    rng = random.Random(SEED)
    edges = [LO, LO + 1, -16384, -8192, -1, 0, 1, 8192, 16384, HI - 1, HI]
    for n in range(24):
        k = len(coeffs)
        coeffs.append(tuple(rng.choice(edges) if rng.random() < 0.4 else rng.randint(LO, HI) for _ in range(5)))
        c = case(f"random_filter_{n:02d}", "B2 B3 B4 B5 B6 B7 B8 B9 B10").init(k, rng.randint(1, 5))
        for _ in range(12):
            r = rng.random()
            if r < 0.45:
                c.step(*[rng.choice(edges) if rng.random() < 0.3 else rng.randint(LO, HI) for _ in range(3)])
            elif r < 0.7:
                xs = [rng.randint(LO, HI) for _ in range(rng.randint(0, 9))]
                c.process(xs, rng.randint(0, 4))
            elif r < 0.8:
                xs = [rng.randint(LO, HI) for _ in range(rng.randint(0, 9))]
                c.in_place(xs, rng.randint(0, 4))
            elif r < 0.88:
                c.reset()
            else:
                c.sat()
    return out, coeffs, blk_in, blk_out


def generate():
    cs, coeffs, blk_in, blk_out = cases()
    steps, table, start = [], [], 0
    for name, req, c in cs:
        steps += c.steps
        table.append((name, req, start, len(c.steps)))
        start += len(c.steps)
    head = f"/* {CANARY}: generated by gen_vectors.py; do not edit. Hidden from the model. */\n"
    c = [head, "#ifndef FXM_VECTORS_H\n#define FXM_VECTORS_H\n#include <stdint.h>\n",
         "typedef struct { uint8_t op; int32_t a; int32_t b; int32_t c; int32_t want; int32_t want2; } fxm_step_t;\n",
         "typedef struct { const char *name; const char *req; uint32_t start; uint32_t len; } fxm_case_t;\n",
         "static const int16_t FXM_COEFFS[][5] = {\n"]
    c += [f"    {{{', '.join(str(v) for v in k)}}},\n" for k in coeffs]
    c += ["};\nstatic const fxm_step_t FXM_STEPS[] = {\n"]
    c += [f"    {{{o}U, {a}, {b}, {cc}, {w}, {w2}}},\n" for o, a, b, cc, w, w2 in steps]
    c += ["};\nstatic const int16_t FXM_BLK_IN[] = {\n"]
    c += [f"    {v},\n" for v in blk_in] or ["    0,\n"]
    c += ["};\nstatic const int16_t FXM_BLK_OUT[] = {\n"]
    c += [f"    {v},\n" for v in blk_out] or ["    0,\n"]
    c += ["};\nstatic const fxm_case_t FXM_CASES[] = {\n"]
    c += [f'    {{"{n}", "{r}", {s}U, {ln}U}},\n' for n, r, s, ln in table]
    c += [f"}};\n#define FXM_N_CASES {len(table)}U\n#define FXM_SENTINEL {SENTINEL}\n#define FXM_NONE {NONE}\n#endif\n"]
    rs = [f"// {CANARY}: generated by gen_vectors.py; do not edit. Hidden from the model.\n",
          f"pub const SENTINEL: i16 = {SENTINEL};\npub const NONE: i32 = {NONE};\n",
          "#[rustfmt::skip]\npub const COEFFS: &[[i16; 5]] = &[\n"]
    rs += [f"    [{', '.join(str(v) for v in k)}],\n" for k in coeffs]
    rs += ["];\n#[rustfmt::skip]\npub const STEPS: &[(u8, i32, i32, i32, i32, i32)] = &[\n"]
    rs += [f"    ({o}, {a}, {b}, {cc}, {w}, {w2}),\n" for o, a, b, cc, w, w2 in steps]
    rs += ["];\n#[rustfmt::skip]\npub const BLK_IN: &[i16] = &[\n"]
    rs += [f"    {v},\n" for v in blk_in]
    rs += ["];\n#[rustfmt::skip]\npub const BLK_OUT: &[i16] = &[\n"]
    rs += [f"    {v},\n" for v in blk_out]
    rs += ["];\n#[rustfmt::skip]\npub const CASES: &[(&str, &str, usize, usize)] = &[\n"]
    rs += [f'    ("{n}", "{r}", {s}, {ln}),\n' for n, r, s, ln in table]
    rs += ["];\n"]
    return {"vectors.h": "".join(c), "vectors.rs": "".join(rs)}


if __name__ == "__main__":
    here = pathlib.Path(__file__).parent
    for name, text in generate().items():
        (here / name).write_text(text)
    print(f"wrote {len(generate())} files", file=sys.stderr)
