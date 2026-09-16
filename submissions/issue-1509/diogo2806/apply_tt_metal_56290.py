"""Apply the tt-metal #56290 uint8 lower-saturation fix.

The replacements are anchored to tt-metal main commit
86b46910d8bd13ca6ec8144048d9323b474ee68a (2026-09-16).
Each edit must match the expected source exactly; otherwise the script aborts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

Replacement = tuple[str, str] | tuple[str, str, int]


def _replace(text: str, old: str, new: str, path: Path, occurrences: int = 1) -> str:
    count = text.count(old)
    if count < occurrences:
        raise RuntimeError(f"expected {occurrences} match(es) in {path}, found {count}")
    return text.replace(old, new, occurrences)


def _apply(path: Path, replacements: list[Replacement]) -> None:
    text = path.read_text(encoding="utf-8")
    for replacement in replacements:
        old, new = replacement[:2]
        occurrences = replacement[2] if len(replacement) == 3 else 1
        text = _replace(text, old, new, path, occurrences)
    path.write_text(text, encoding="utf-8")


def _wormhole_replacements() -> list[Replacement]:
    return [
        (
            """constexpr std::uint32_t QUANT_REPLAY_LEN = 3;
constexpr std::uint32_t QUANT_REPLAY_LEN_INT8_OUT = 7;
constexpr std::uint32_t QUANT_REPLAY_LEN_MAX = QUANT_REPLAY_LEN_INT8_OUT;
""",
            """constexpr std::uint32_t QUANT_REPLAY_LEN = 3;
constexpr std::uint32_t QUANT_REPLAY_LEN_UINT8_OUT = 4;
constexpr std::uint32_t QUANT_REPLAY_LEN_INT8_OUT = 5;
constexpr std::uint32_t QUANT_REPLAY_LEN_MAX = QUANT_REPLAY_LEN_INT8_OUT;
""",
        ),
        (
            """constexpr std::uint32_t REQUANT_REPLAY_LEN = 4;
constexpr std::uint32_t REQUANT_REPLAY_LEN_INT8_OUT = 8;
constexpr std::uint32_t REQUANT_REPLAY_LEN_MAX = REQUANT_REPLAY_LEN_INT8_OUT;
""",
            """constexpr std::uint32_t REQUANT_REPLAY_LEN = 4;
constexpr std::uint32_t REQUANT_REPLAY_LEN_UINT8_OUT = 5;
constexpr std::uint32_t REQUANT_REPLAY_LEN_INT8_OUT = 6;
constexpr std::uint32_t REQUANT_REPLAY_LEN_MAX = REQUANT_REPLAY_LEN_INT8_OUT;
""",
        ),
        (
            """inline void _int8_input_unbias_() { TTI_SFPXOR(0, p_sfpu::LREG4, p_sfpu::LREG0, 0); }
""",
            """inline void _int8_input_unbias_() { TTI_SFPXOR(0, p_sfpu::LREG4, p_sfpu::LREG0, 0); }

inline void _uint8_clamp_negatives_() {
    // SFPSWAP mode 9 writes max(LCONST_0, LREG0) back to LREG0.
    TTI_SFPSWAP(0, p_sfpu::LCONST_0, p_sfpu::LREG0, 9);
}
""",
        ),
        (
            """    TTI_SFPSETCC(0, p_sfpu::LREG0, 0, sfpi::SFPSETCC_MOD1_LREG_LT0);
    TTI_SFPMOV(0, p_sfpu::LCONST_0, p_sfpu::LREG0, 0);
    TTI_SFPENCC(0, 0, 0, 0);
    TTI_SFP_STOCH_RND(
""",
            """    _uint8_clamp_negatives_();
    TTI_SFP_STOCH_RND(
""",
        ),
        (
            """template <bool APPROXIMATION_MODE, int ITERATIONS = 8, bool SIGN_MAGNITUDE_FORMAT = false>
inline void calculate_quant_int32(""",
            """template <
    bool APPROXIMATION_MODE,
    int ITERATIONS = 8,
    bool SIGN_MAGNITUDE_FORMAT = false,
    DataFormat OUTPUT_FORMAT = DataFormat::Int32>
inline void calculate_quant_int32(""",
        ),
        (
            """    constexpr InstrModLoadStore out_mode =
        SIGN_MAGNITUDE_FORMAT ? InstrModLoadStore::INT32 : InstrModLoadStore::INT32_2S_COMP;
""",
            """    static_assert(
        OUTPUT_FORMAT == DataFormat::Int32 || OUTPUT_FORMAT == DataFormat::UInt8,
        "calculate_quant_int32 OUTPUT_FORMAT must be Int32 or UInt8");
    constexpr InstrModLoadStore out_mode =
        SIGN_MAGNITUDE_FORMAT ? InstrModLoadStore::INT32 : InstrModLoadStore::INT32_2S_COMP;
""",
        ),
        (
            """        lltt::replay(QUANT_REPLAY_SLOT, QUANT_REPLAY_LEN);                        // MAD + SFPNOP + STOCH_RND
""",
            """        constexpr std::uint32_t replay_len =
            OUTPUT_FORMAT == DataFormat::UInt8 ? QUANT_REPLAY_LEN_UINT8_OUT : QUANT_REPLAY_LEN;
        lltt::replay(QUANT_REPLAY_SLOT, replay_len);
""",
        ),
        (
            """template <bool APPROXIMATION_MODE, int ITERATIONS = 8, bool SIGN_MAGNITUDE_FORMAT = false, bool INT8_INPUT = false>
inline void calculate_requant_int32(""",
            """template <
    bool APPROXIMATION_MODE,
    int ITERATIONS = 8,
    bool SIGN_MAGNITUDE_FORMAT = false,
    bool INT8_INPUT = false,
    DataFormat OUTPUT_FORMAT = DataFormat::Int32>
inline void calculate_requant_int32(""",
        ),
        (
            """    constexpr InstrModLoadStore int_mode =
        (SIGN_MAGNITUDE_FORMAT && !INT8_INPUT) ? InstrModLoadStore::INT32 : InstrModLoadStore::INT32_2S_COMP;
""",
            """    static_assert(
        OUTPUT_FORMAT == DataFormat::Int32 || OUTPUT_FORMAT == DataFormat::UInt8,
        "calculate_requant_int32 OUTPUT_FORMAT must be Int32 or UInt8");
    constexpr InstrModLoadStore int_mode =
        (SIGN_MAGNITUDE_FORMAT && !INT8_INPUT) ? InstrModLoadStore::INT32 : InstrModLoadStore::INT32_2S_COMP;
""",
        ),
        (
            """        lltt::replay(REQUANT_REPLAY_SLOT, REQUANT_REPLAY_LEN);      // CAST + MAD + SFPNOP + STOCH_RND
""",
            """        constexpr std::uint32_t replay_len =
            OUTPUT_FORMAT == DataFormat::UInt8 ? REQUANT_REPLAY_LEN_UINT8_OUT : REQUANT_REPLAY_LEN;
        lltt::replay(REQUANT_REPLAY_SLOT, replay_len);
""",
        ),
        (
            """    lltt::record<lltt::NoExec>(QUANT_REPLAY_SLOT, QUANT_REPLAY_LEN);
    {
""",
            """    constexpr std::uint32_t replay_len =
        OUTPUT_FORMAT == DataFormat::UInt8 ? QUANT_REPLAY_LEN_UINT8_OUT : QUANT_REPLAY_LEN;
    lltt::record<lltt::NoExec>(QUANT_REPLAY_SLOT, replay_len);
    {
""",
        ),
        (
            """        if constexpr (OUTPUT_FORMAT == DataFormat::UInt8) {
            TTI_SFP_STOCH_RND(
""",
            """        if constexpr (OUTPUT_FORMAT == DataFormat::UInt8) {
            _uint8_clamp_negatives_();
            TTI_SFP_STOCH_RND(
""",
            2,
        ),
        (
            """    lltt::record<lltt::NoExec>(REQUANT_REPLAY_SLOT, REQUANT_REPLAY_LEN);
    {
""",
            """    constexpr std::uint32_t replay_len =
        OUTPUT_FORMAT == DataFormat::UInt8 ? REQUANT_REPLAY_LEN_UINT8_OUT : REQUANT_REPLAY_LEN;
    lltt::record<lltt::NoExec>(REQUANT_REPLAY_SLOT, replay_len);
    {
""",
        ),
    ]


def _blackhole_replacements() -> list[Replacement]:
    return [
        (
            """constexpr std::uint32_t QUANT_REPLAY_LEN_2S_COMP = 4;
constexpr std::uint32_t QUANT_REPLAY_LEN_SIGN_MAGN = 2;
constexpr std::uint32_t QUANT_REPLAY_LEN_INT8_OUT = 6;
constexpr std::uint32_t QUANT_REPLAY_LEN_MAX = QUANT_REPLAY_LEN_INT8_OUT;
""",
            """constexpr std::uint32_t QUANT_REPLAY_LEN_2S_COMP = 4;
constexpr std::uint32_t QUANT_REPLAY_LEN_SIGN_MAGN = 2;
constexpr std::uint32_t QUANT_REPLAY_LEN_UINT8_OUT = 3;
constexpr std::uint32_t QUANT_REPLAY_LEN_INT8_OUT = 4;
constexpr std::uint32_t QUANT_REPLAY_LEN_MAX = QUANT_REPLAY_LEN_2S_COMP;
""",
        ),
        (
            """constexpr std::uint32_t REQUANT_REPLAY_LEN_2S_COMP = 7;
constexpr std::uint32_t REQUANT_REPLAY_LEN_SIGN_MAGN = 3;
constexpr std::uint32_t REQUANT_REPLAY_LEN_INT8_IN = 5;
constexpr std::uint32_t REQUANT_REPLAY_LEN_INT8_OUT = 7;
constexpr std::uint32_t REQUANT_REPLAY_LEN_INT8_OUT_INT32_IN = 9;
constexpr std::uint32_t REQUANT_REPLAY_LEN_MAX = REQUANT_REPLAY_LEN_INT8_OUT_INT32_IN;
""",
            """constexpr std::uint32_t REQUANT_REPLAY_LEN_2S_COMP = 7;
constexpr std::uint32_t REQUANT_REPLAY_LEN_SIGN_MAGN = 3;
constexpr std::uint32_t REQUANT_REPLAY_LEN_UINT8_SIGN_MAGN = 4;
constexpr std::uint32_t REQUANT_REPLAY_LEN_UINT8_2S_COMP = 6;
constexpr std::uint32_t REQUANT_REPLAY_LEN_INT8_IN = 5;
constexpr std::uint32_t REQUANT_REPLAY_LEN_INT8_OUT = 5;
constexpr std::uint32_t REQUANT_REPLAY_LEN_INT8_OUT_INT32_IN = 7;
constexpr std::uint32_t REQUANT_REPLAY_LEN_MAX = REQUANT_REPLAY_LEN_2S_COMP;
""",
        ),
        (
            """inline void _int8_input_unbias_() { TTI_SFPXOR(0, p_sfpu::LREG3, p_sfpu::LREG0, 0); }
""",
            """inline void _int8_input_unbias_() { TTI_SFPXOR(0, p_sfpu::LREG3, p_sfpu::LREG0, 0); }

inline void _uint8_clamp_negatives_() {
    TTI_SFPSWAP(0, p_sfpu::LCONST_0, p_sfpu::LREG0, 9);
}
""",
        ),
        (
            """    TTI_SFPSETCC(0, p_sfpu::LREG0, 0, sfpi::SFPSETCC_MOD1_LREG_LT0);
    TTI_SFPMOV(0, p_sfpu::LCONST_0, p_sfpu::LREG0, 0);
    TTI_SFPENCC(0, 0, 0, 0);
    TTI_SFP_STOCH_RND(
""",
            """    _uint8_clamp_negatives_();
    TTI_SFP_STOCH_RND(
""",
        ),
        (
            """    constexpr std::uint32_t REPLAY_LEN = SIGN_MAGNITUDE_FORMAT ? QUANT_REPLAY_LEN_SIGN_MAGN : QUANT_REPLAY_LEN_2S_COMP;
""",
            """    constexpr std::uint32_t REPLAY_LEN =
        OUTPUT_FORMAT == DataFormat::UInt8
            ? QUANT_REPLAY_LEN_UINT8_OUT
            : (SIGN_MAGNITUDE_FORMAT ? QUANT_REPLAY_LEN_SIGN_MAGN : QUANT_REPLAY_LEN_2S_COMP);
""",
            2,
        ),
        (
            """        if constexpr (OUTPUT_FORMAT == DataFormat::UInt8) {
            TTI_SFP_STOCH_RND(
""",
            """        if constexpr (OUTPUT_FORMAT == DataFormat::UInt8) {
            _uint8_clamp_negatives_();
            TTI_SFP_STOCH_RND(
""",
            2,
        ),
        (
            """        if constexpr (!SIGN_MAGNITUDE_FORMAT) {
""",
            """        if constexpr (!SIGN_MAGNITUDE_FORMAT && OUTPUT_FORMAT != DataFormat::UInt8) {
""",
            2,
        ),
        (
            """    constexpr std::uint32_t REPLAY_LEN =
        INT8_INPUT ? REQUANT_REPLAY_LEN_INT8_IN
                   : (SIGN_MAGNITUDE_FORMAT ? REQUANT_REPLAY_LEN_SIGN_MAGN : REQUANT_REPLAY_LEN_2S_COMP);
""",
            """    constexpr std::uint32_t REPLAY_LEN =
        OUTPUT_FORMAT == DataFormat::UInt8
            ? ((SIGN_MAGNITUDE_FORMAT || INT8_INPUT) ? REQUANT_REPLAY_LEN_UINT8_SIGN_MAGN
                                                     : REQUANT_REPLAY_LEN_UINT8_2S_COMP)
            : (INT8_INPUT ? REQUANT_REPLAY_LEN_INT8_IN
                          : (SIGN_MAGNITUDE_FORMAT ? REQUANT_REPLAY_LEN_SIGN_MAGN : REQUANT_REPLAY_LEN_2S_COMP));
""",
            2,
        ),
        (
            """template <bool APPROXIMATION_MODE, int ITERATIONS = 8, bool SIGN_MAGNITUDE_FORMAT = false>
inline void calculate_quant_int32(""",
            """template <
    bool APPROXIMATION_MODE,
    int ITERATIONS = 8,
    bool SIGN_MAGNITUDE_FORMAT = false,
    DataFormat OUTPUT_FORMAT = DataFormat::Int32>
inline void calculate_quant_int32(""",
        ),
        (
            """template <bool APPROXIMATION_MODE, int ITERATIONS = 8, bool SIGN_MAGNITUDE_FORMAT = false, bool INT8_INPUT = false>
inline void calculate_requant_int32(""",
            """template <
    bool APPROXIMATION_MODE,
    int ITERATIONS = 8,
    bool SIGN_MAGNITUDE_FORMAT = false,
    bool INT8_INPUT = false,
    DataFormat OUTPUT_FORMAT = DataFormat::Int32>
inline void calculate_requant_int32(""",
        ),
        (
            """    constexpr std::uint32_t dst_tile_size = 64;

    constexpr std::uint32_t REPLAY_LEN =
        OUTPUT_FORMAT == DataFormat::UInt8
""",
            """    constexpr std::uint32_t dst_tile_size = 64;
    static_assert(
        OUTPUT_FORMAT == DataFormat::Int32 || OUTPUT_FORMAT == DataFormat::UInt8,
        "calculate quant/requant OUTPUT_FORMAT must be Int32 or UInt8");

    constexpr std::uint32_t REPLAY_LEN =
        OUTPUT_FORMAT == DataFormat::UInt8
""",
            2,
        ),
    ]


def _quantization_api_replacements() -> list[Replacement]:
    return [
        (
            """ALWI void quant_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((SFPU_BINARY_CALL(
        DST_SYNC_MODE, DST_ACCUM_MODE, calculate_quant_int32, (APPROX), idst0, idst1, odst, VectorMode::RC)));
}
""",
            """ALWI void quant_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((SFPU_BINARY_CALL(
        DST_SYNC_MODE, DST_ACCUM_MODE, calculate_quant_int32, (APPROX), idst0, idst1, odst, VectorMode::RC)));
}

ALWI void quant_uint8_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((SFPU_BINARY_CALL(
        DST_SYNC_MODE,
        DST_ACCUM_MODE,
        calculate_quant_int32,
        (APPROX, 8 /*ITERATIONS*/, false /*SIGN_MAGNITUDE_FORMAT*/, DataFormat::UInt8),
        idst0,
        idst1,
        odst,
        VectorMode::RC)));
}
""",
        ),
        (
            """ALWI void requant_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((SFPU_BINARY_CALL(
        DST_SYNC_MODE, DST_ACCUM_MODE, calculate_requant_int32, (APPROX), idst0, idst1, odst, VectorMode::RC)));
}
""",
            """ALWI void requant_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((SFPU_BINARY_CALL(
        DST_SYNC_MODE, DST_ACCUM_MODE, calculate_requant_int32, (APPROX), idst0, idst1, odst, VectorMode::RC)));
}

ALWI void requant_uint8_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((SFPU_BINARY_CALL(
        DST_SYNC_MODE,
        DST_ACCUM_MODE,
        calculate_requant_int32,
        (APPROX, 8 /*ITERATIONS*/, false /*SIGN_MAGNITUDE_FORMAT*/, false /*INT8_INPUT*/, DataFormat::UInt8),
        idst0,
        idst1,
        odst,
        VectorMode::RC)));
}
""",
        ),
        (
            """ALWI void requant_int8_in_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((SFPU_BINARY_CALL(
        DST_SYNC_MODE,
        DST_ACCUM_MODE,
        calculate_requant_int32,
        (APPROX, 8, false, true),
        idst0,
        idst1,
        odst,
        VectorMode::RC)));
}
""",
            """ALWI void requant_int8_in_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((SFPU_BINARY_CALL(
        DST_SYNC_MODE,
        DST_ACCUM_MODE,
        calculate_requant_int32,
        (APPROX, 8, false, true),
        idst0,
        idst1,
        odst,
        VectorMode::RC)));
}

ALWI void requant_int8_in_uint8_out_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {
    MATH((SFPU_BINARY_CALL(
        DST_SYNC_MODE,
        DST_ACCUM_MODE,
        calculate_requant_int32,
        (APPROX, 8 /*ITERATIONS*/, false /*SIGN_MAGNITUDE_FORMAT*/, true /*INT8_INPUT*/, DataFormat::UInt8),
        idst0,
        idst1,
        odst,
        VectorMode::RC)));
}
""",
        ),
    ]


def _program_factory_replacements() -> list[Replacement]:
    return [
        (
            """        if (c_dtype == DataType::UINT8) {
            compute_kernel_defines["BINARY_SFPU_INIT"] = std::string("quant_uint8_tile_init") + quant_zp_arg;
        } else if (c_dtype == DataType::INT8) {
""",
            """        if (c_dtype == DataType::UINT8) {
            set_sfpu_op("quant_uint8_tile_init", "quant_uint8_tile");
        } else if (c_dtype == DataType::INT8) {
""",
        ),
        (
            """        } else if (c_dtype == DataType::UINT8) {
            // uint8 output uses the standard packer narrowing (int32 SFPU result -> uint8), so it reuses
            // the int32-output op body; only the init differs, to select FP32_TO_UINT8 rounding.
            set_sfpu_op(
                int8_in ? "requant_int8_in_uint8_out_tile_init" : "requant_uint8_tile_init",
                int8_in ? "requant_int8_in_tile" : "requant_tile");
""",
            """        } else if (c_dtype == DataType::UINT8) {
            set_sfpu_op(
                int8_in ? "requant_int8_in_uint8_out_tile_init" : "requant_uint8_tile_init",
                int8_in ? "requant_int8_in_uint8_out_tile" : "requant_uint8_tile");
""",
        ),
    ]


def _composite_replacements() -> list[Replacement]:
    return [
        (
            """// Narrow composite's fp result to the output dtype. Use quantize as the narrowing step
// for int8 until typecast(int32 -> int8) is enabled (#50401).
""",
            """// Narrow composite fp results with saturating quantization for int8/uint8.
// Direct narrow typecasts can wrap instead of respecting quantization bounds.
""",
        ),
        (
            """    if (c_dtype != ttnn::DataType::INT8) {
        return ttnn::typecast(shifted, c_dtype, memory_config, optional_output_tensor);
    }
""",
            """    if (!is_narrow_quantized_dtype(c_dtype)) {
        return ttnn::typecast(shifted, c_dtype, memory_config, optional_output_tensor);
    }
""",
        ),
        (
            """        ttnn::DataType::INT8,
        memory_config,
""",
            """        c_dtype,
        memory_config,
""",
        ),
    ]


def _write_upstream_regression_test(root: Path) -> None:
    path = root / "tests/ttnn/nightly/unit_tests/operations/eltwise/test_quantization_uint8_lower_saturation.py"
    if path.exists():
        raise FileExistsError(path)
    path.write_text(
        """# SPDX-FileCopyrightText: © 2026 Tenstorrent USA, Inc.
# SPDX-License-Identifier: Apache-2.0

import pytest
import torch
import ttnn


@pytest.mark.parametrize("input_dtype", [ttnn.float32, ttnn.bfloat16])
def test_quantize_uint8_lower_and_upper_saturation(device, input_dtype):
    values = [-1000.0, -300.0, -17.0, -2.5, -0.0, 0.0, 2.5, 17.0, 255.0, 300.0, 1000.0]
    input_tr = torch.tensor([values], dtype=torch.float32)
    expected = torch.clamp(torch.round(input_tr), 0, 255).to(torch.uint8)
    input_tt = ttnn.from_torch(input_tr, dtype=input_dtype, layout=ttnn.TILE_LAYOUT, device=device)
    result = ttnn.to_torch(ttnn.quantize(input_tt, 1.0, 0, dtype=ttnn.uint8))
    assert torch.equal(result, expected), f"got {result.tolist()} expected {expected.tolist()}"


def test_quantize_uint8_nonzero_zero_point(device):
    input_tr = torch.tensor([[-100.0, -10.0, -1.0, 0.0, 1.0, 10.0, 100.0]], dtype=torch.float32)
    scale, zero_point = 2.0, 20
    expected = torch.clamp(torch.round(input_tr / scale + zero_point), 0, 255).to(torch.uint8)
    input_tt = ttnn.from_torch(input_tr, dtype=ttnn.float32, layout=ttnn.TILE_LAYOUT, device=device)
    result = ttnn.to_torch(ttnn.quantize(input_tt, scale, zero_point, dtype=ttnn.uint8))
    assert torch.equal(result, expected)


@pytest.mark.parametrize(
    "in_dtype,q_values,in_scale,in_zp",
    [
        (ttnn.int32, [-1000, -300, -50, -1, 0, 1, 50, 255, 1000], 1.0, 0),
        (ttnn.int32, [-100, -10, 0, 10, 100], 2.0, 10),
        (ttnn.int8, [-128, -100, -32, -1, 0, 1, 32, 100, 127], 1.0, 0),
    ],
)
def test_requantize_uint8_exact_saturation(device, in_dtype, q_values, in_scale, in_zp):
    torch_dtype = torch.int32 if in_dtype == ttnn.int32 else torch.int8
    q_in = torch.tensor([q_values], dtype=torch_dtype)
    expected = torch.clamp(torch.round((q_in.to(torch.float32) - in_zp) * in_scale), 0, 255).to(torch.uint8)
    q_in_tt = ttnn.from_torch(q_in, dtype=in_dtype, layout=ttnn.TILE_LAYOUT, device=device)
    result = ttnn.to_torch(ttnn.requantize(q_in_tt, in_scale, in_zp, 1.0, 0, dtype=ttnn.uint8))
    assert torch.equal(result, expected), f"got {result.tolist()} expected {expected.tolist()}"


def test_quantize_uint8_rounding_ties(device):
    input_tr = torch.tensor([[0.5, 1.5, 2.5, 3.5, 254.5, 255.5]], dtype=torch.float32)
    expected = torch.clamp(torch.round(input_tr), 0, 255).to(torch.uint8)
    input_tt = ttnn.from_torch(input_tr, dtype=ttnn.float32, layout=ttnn.TILE_LAYOUT, device=device)
    result = ttnn.to_torch(ttnn.quantize(input_tt, 1.0, 0, dtype=ttnn.uint8))
    assert torch.equal(result, expected)
""",
        encoding="utf-8",
    )


def apply_fix(root: Path) -> None:
    """Apply all issue #56290 changes to a tt-metal checkout."""
    files = {
        "tt_metal/hw/ckernels/wormhole_b0/metal/llk_api/llk_sfpu/ckernel_sfpu_quant.h": _wormhole_replacements(),
        "tt_metal/hw/ckernels/blackhole/metal/llk_api/llk_sfpu/ckernel_sfpu_quant.h": _blackhole_replacements(),
        "tt_metal/hw/inc/api/compute/quantization.h": _quantization_api_replacements(),
        "ttnn/cpp/ttnn/operations/eltwise/binary_ng/device/binary_ng_program_factory.cpp": _program_factory_replacements(),
        "ttnn/cpp/ttnn/operations/eltwise/quantization/quantization.cpp": _composite_replacements(),
    }
    for relative, replacements in files.items():
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        _apply(path, replacements)
    _write_upstream_regression_test(root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply tt-metal #56290 fix")
    parser.add_argument("checkout", type=Path, help="Path to a tt-metal checkout")
    args = parser.parse_args()
    apply_fix(args.checkout.resolve())


if __name__ == "__main__":
    main()
