# Bounty Plaza #1509 / Tenstorrent tt-metal #56290

Independent fix for uint8 lower-bound saturation in `ttnn.quantize` and `ttnn.requantize`.

## Root cause

Both Wormhole B0 and Blackhole use the SFPU `FP32_TO_UINT8` conversion for uint8 outputs. For negative floating-point lanes, that conversion can preserve the magnitude while dropping the sign instead of producing the required lower saturation value `0`.

## Fix

The upstream-oriented fix:

1. clamps negative SFPU lanes with a single `TTI_SFPSWAP(..., mode 9)` before `FP32_TO_UINT8`;
2. updates uint8 and int8 replay-buffer lengths to match the shorter one-instruction clamp;
3. adds compile-time output-format guards to the new quant/requant calculate templates;
4. gives uint8 quantize/requantize dedicated tile entry points so record and replay use the same uint8 body length;
5. avoids unnecessary Blackhole sign-representation conversion after uint8 rounding;
6. routes composite uint8 narrowing through `ttnn::quantize` instead of wrapping `typecast`;
7. adds exact-output regressions for lower/upper saturation, zero points, ties-to-even, float32/bfloat16, and int8-input requantization.

## Apply to tt-metal

```bash
python apply_tt_metal_56290.py /path/to/tt-metal
```

The application script is anchored to `tenstorrent/tt-metal` main commit `86b46910d8bd13ca6ec8144048d9323b474ee68a` from 2026-09-16 and aborts if an expected source fragment is no longer present.

See `UPSTREAM_MANIFEST.md` for the exact base blob SHAs and `tt-metal-56290-review.diff` for review-oriented C++ diff snippets.

The upstream-style regression file is also included directly at:

`upstream/tests/ttnn/nightly/unit_tests/operations/eltwise/test_quantization_uint8_lower_saturation.py`

## Bounty Plaza semantic verification

`reference_model.py` is a hardware-independent executable model of the formulas specified by issue #56290.

```bash
python -m pytest -q test_reference_model.py
python ../../../scripts/score.py --code reference_model.py --tests .
```

Local semantic result: **29 tests passed**.

The reference suite covers negative lower saturation, upper saturation at 255, in-range values, nearest-even ties, non-zero zero points, negative zero, int8 regression behavior, int8-input requantization values and invalid zero scales.

## Scope and verification status

This submission does not modify Bounty Plaza scoring, payout, winner-selection, or platform test infrastructure.

The original Tenstorrent issue requires execution coverage on Wormhole B0 and Blackhole. This submission includes the code and upstream regression tests for those paths, but does **not** claim that Tenstorrent hardware execution was performed locally.
