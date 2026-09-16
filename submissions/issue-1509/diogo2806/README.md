# Bounty Plaza #1509 / Tenstorrent tt-metal #56290

Independent fix for uint8 lower-bound saturation in `ttnn.quantize` and `ttnn.requantize`.

## Root cause

Both Wormhole B0 and Blackhole use the SFPU `FP32_TO_UINT8` conversion for uint8 outputs. For negative floating-point lanes, that instruction can preserve the magnitude while dropping the sign instead of producing the required lower saturation value 0.

## Fix

The upstream fix:

1. clamps negative SFPU lanes to `0.0f` before `FP32_TO_UINT8`;
2. updates replay-buffer lengths for the extra three clamp instructions;
3. gives uint8 quantize/requantize dedicated tile entry points so replay uses the uint8 body length;
4. avoids unnecessary Blackhole sign-representation conversion after uint8 rounding;
5. routes composite uint8 narrowing through `ttnn::quantize` instead of wrapping `typecast`;
6. adds exact-output lower-bound regression coverage while preserving the existing upper-bound tests.

## Apply to tt-metal

```bash
python apply_tt_metal_56290.py /path/to/tt-metal
```

The application script is based on `tenstorrent/tt-metal` main at commit `af70ea1a75418af1d0c018ee0acedc3422cf387c` (2026-09-16).

## Bounty Plaza scorer reference

`reference_model.py` is a hardware-independent executable model of the documented formulas. It exists so Bounty Plaza can score the semantics without requiring Tenstorrent hardware.

```bash
python -m pytest -q test_reference_model.py
python ../../../scripts/score.py --code reference_model.py --tests .
```

Local functional result: 18 tests passed.

No Bounty Plaza scoring, payout, or test infrastructure files are modified by this submission.
