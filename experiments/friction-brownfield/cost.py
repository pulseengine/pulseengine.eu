"""Notional cost of friction x model v2 (brownfield), for the pre-registration.

Prints every figure in the Cost section of
docs/experiments/2026-11-friction-brownfield.md. Every constant below is an
assumption stated in that section; calibration measures them. No API is called.

    python3 experiments/friction-brownfield/cost.py
"""

# Live prices per MTok: (input, cache read, output). haiku's are for prompts <= 100K.
PRICES = {
    "haiku": (0.10, 0.01, 0.50),
    "sonnet": (2.0, 0.10, 10.0),
    "opus": (4.0, 0.20, 20.0),
    "fable": (10.0, 0.25, 50.0),
}
HAIKU_OVER_100K = (0.50, 0.05, 2.50)
CACHE_WRITE = 1.25   # x input price; ASSUMED, not in the price list
FIXED = 8_000        # CLI + change request + rules + findings, tokens (assumed)
TOKENS_PER_LINE = 10  # tests included (assumed)
TASKS, REPS = 6, 5
ONESHOT_ROWS, LOOP_ROWS = 2, 5   # C-B0, R-B0 | C-B1, C-B2, R-B1, R-B2, R-B3
ITERATIONS = 3       # mean in the loop rows (assumed); N = 10 at worst
CAL_HAIKU, CAL_OPUS = 10, 3  # B0 runs per task and language per round; smoke: 1 haiku run per loop row
CAL_B1 = 5           # haiku B1 headroom runs per task and language per round


def price(model, prompt):
    if model == "haiku" and prompt > 100_000:
        return HAIKU_OVER_100K
    return PRICES[model]


def call(model, prompt, out, cached=False):
    i, c, o = price(model, prompt)
    if cached:
        return ((prompt - FIXED) * c + FIXED * i + out * o) / 1e6
    return (prompt * i + out * o) / 1e6


def run(model, prompt, out, iters, cache=False):
    if iters == 1 or not cache:
        return iters * call(model, prompt, out)
    i, _, o = price(model, prompt)
    first = ((prompt - FIXED) * i * CACHE_WRITE + FIXED * i + out * o) / 1e6
    return first + (iters - 1) * call(model, prompt, out, True)


def matrix(prompt, out, iters, cache=False):
    n = TASKS * REPS
    return {m: ONESHOT_ROWS * n * call(m, prompt, out)
            + LOOP_ROWS * n * run(m, prompt, out, iters, cache) for m in PRICES}


def main():
    # Anchor: v1's calibration, 22 opus + 38 haiku runs of about one ~5K-token call, $2.00.
    for out in (3_000, 3_500, 4_000):
        v = 22 * call("opus", 5_000, out) + 38 * call("haiku", 5_000, out)
        print(f"v1 calibration back-check, {out} output tokens per call: ${v:.2f}")
    langs = 2
    for kloc in (2, 5):
        prompt = kloc * 1000 * TOKENS_PER_LINE + FIXED
        for out in (4_000, 8_000, 16_000):
            print(f"--- {kloc} kLOC, prompt {prompt // 1000}K, output {out // 1000}K")
            print("  one call: " + " ".join(f"{m}=${call(m, prompt, out):.3f}" for m in PRICES))
            band = langs * TASKS * CAL_HAIKU * call("haiku", prompt, out)
            guard = langs * TASKS * CAL_OPUS * call("opus", prompt, out)
            smoke = TASKS * LOOP_ROWS * run("haiku", prompt, out, ITERATIONS)
            b1 = langs * TASKS * CAL_B1 * run("haiku", prompt, out, ITERATIONS)
            rnd = band + b1 + guard + smoke
            print(f"  calibration round: B0 band ${band:.2f}, B1 headroom ${b1:.2f},"
                  f" all with opus guard and smoke ${rnd:.2f};"
                  f" three rounds ${3 * rnd:.2f}")
            pilot = sum(ONESHOT_ROWS * call(m, prompt, out)
                        + LOOP_ROWS * run(m, prompt, out, ITERATIONS) for m in PRICES)
            print(f"  harness pilot, 1 task x 28 cells x 1 run: ${pilot:.2f}")
            mx = matrix(prompt, out, ITERATIONS)
            total = sum(mx.values())
            cached = sum(matrix(prompt, out, ITERATIONS, True).values())
            worst = sum(matrix(prompt, out, 10).values())
            print(f"  full run, 840 runs: ${total:.0f} ("
                  + " ".join(f"{m}=${v:.0f} {100 * v / total:.0f}%" for m, v in mx.items())
                  + f"); cached ${cached:.0f} (-{100 * (1 - cached / total):.0f}%); every loop run at N=10 ${worst:.0f}")


if __name__ == "__main__":
    main()
