# Upstream manifest for tt-metal #56290

Base repository: `tenstorrent/tt-metal`

Base commit: `86b46910d8bd13ca6ec8144048d9323b474ee68a` (2026-09-16)

The deterministic applicator `apply_tt_metal_56290.py` is anchored to the following source blobs:

| Upstream path | Base blob SHA |
| --- | --- |
| `tt_metal/hw/ckernels/wormhole_b0/metal/llk_api/llk_sfpu/ckernel_sfpu_quant.h` | `755935fb1c891387195019bccee1e3c01b6e2860` |
| `tt_metal/hw/ckernels/blackhole/metal/llk_api/llk_sfpu/ckernel_sfpu_quant.h` | `cf7b95dcb7d3d7e4cd68f17abd389ac861f4e51f` |
| `tt_metal/hw/inc/api/compute/quantization.h` | `3d770c9c1535cd47f72619019a9203484fed3b6b` |
| `ttnn/cpp/ttnn/operations/eltwise/binary_ng/device/binary_ng_program_factory.cpp` | `37453fbb0ae10023a20659bc2623a4b1c18e785e` |
| `ttnn/cpp/ttnn/operations/eltwise/quantization/quantization.cpp` | `7389f5d307c2856fa6e620b79ef9a24b1d025999` |

## Intended upstream changes

- Replace the three-instruction negative clamp with one `TTI_SFPSWAP(..., mode 9)` clamp before `FP32_TO_UINT8`.
- Keep uint8 record/replay lengths identical on both the init and calculate sides.
- Shrink int8 replay bodies because the shared clamp becomes one instruction.
- Reject unsupported output formats at compile time in the new calculate templates.
- Route uint8 quantize/requantize through dedicated tile functions.
- Route composite uint8 narrowing through saturating `ttnn::quantize` instead of wrapping `typecast`.
- Add exact-output regression coverage for negative, in-range, over-range, zero-point, ties-to-even, float32/bfloat16 and int8-input requantization cases.

## Submission artifacts

- `apply_tt_metal_56290.py`: authoritative deterministic applicator.
- `tt-metal-56290-review.diff`: human-review diff snippets of the C++ changes.
- `upstream/tests/ttnn/nightly/unit_tests/operations/eltwise/test_quantization_uint8_lower_saturation.py`: upstream-style regression test file.
- `reference_model.py`: hardware-independent implementation of the issue formulas.
- `test_reference_model.py`: executable semantic regression suite.

The submission does not modify Bounty Plaza scoring, payout, winner selection, or platform test infrastructure.

Hardware execution on Wormhole B0 and Blackhole is still required by the original Tenstorrent acceptance criteria and is not claimed as locally performed by this submission.
