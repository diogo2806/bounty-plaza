"""Apply the tt-metal #56290 uint8 lower-saturation fix to a checkout.

The replacements are intentionally anchored to tt-metal main at
commit af70ea1a75418af1d0c018ee0acedc3422cf387c. Each replacement must match
the expected source shape; otherwise the script stops instead of silently
editing the wrong revision.
"""

from __future__ import annotations

import argparse
from pathlib import Path


Replacement = tuple[str, str] | tuple[str, str, int]


def _replace(text: str, old: str, new: str, path: Path, occurrences: int = 1) -> str:
    count = text.count(old)
    if count < occurrences:
        raise RuntimeError(
            f"expected at least {occurrences} match(es) in {path}, found {count}"
        )
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
            """constexpr std::uint32_t QUANT_REPLAY_SLOT = 0;\nconstexpr std::uint32_t QUANT_REPLAY_LEN = 3;\nconstexpr std::uint32_t QUANT_REPLAY_LEN_INT8_OUT = 7;\n""",
            """constexpr std::uint32_t QUANT_REPLAY_SLOT = 0;\nconstexpr std::uint32_t QUANT_REPLAY_LEN = 3;\nconstexpr std::uint32_t QUANT_REPLAY_LEN_UINT8_OUT = 6;\nconstexpr std::uint32_t QUANT_REPLAY_LEN_INT8_OUT = 7;\n""",
        ),
        (
            """constexpr std::uint32_t REQUANT_REPLAY_SLOT = QUANT_REPLAY_SLOT + QUANT_REPLAY_LEN_MAX;\nconstexpr std::uint32_t REQUANT_REPLAY_LEN = 4;\nconstexpr std::uint32_t REQUANT_REPLAY_LEN_INT8_OUT = 8;\n""",
            """constexpr std::uint32_t REQUANT_REPLAY_SLOT = QUANT_REPLAY_SLOT + QUANT_REPLAY_LEN_MAX;\nconstexpr std::uint32_t REQUANT_REPLAY_LEN = 4;\nconstexpr std::uint32_t REQUANT_REPLAY_LEN_UINT8_OUT = 7;\nconstexpr std::uint32_t REQUANT_REPLAY_LEN_INT8_OUT = 8;\n""",
        ),
        (
            """inline void _int8_input_unbias_() { TTI_SFPXOR(0, p_sfpu::LREG4, p_sfpu::LREG0, 0); }\n\n// Configure the SFPU \"dest += 2\" addr_mod slot.""",
            """inline void _int8_input_unbias_() { TTI_SFPXOR(0, p_sfpu::LREG4, p_sfpu::LREG0, 0); }\n\ninline void _uint8_clamp_negatives_() {\n    TTI_SFPSETCC(0, p_sfpu::LREG0, 0, sfpi::SFPSETCC_MOD1_LREG_LT0);\n    TTI_SFPMOV(0, p_sfpu::LCONST_0, p_sfpu::LREG0, 0);\n    TTI_SFPENCC(0, 0, 0, 0);\n}\n\n// Configure the SFPU \"dest += 2\" addr_mod slot.""",
        ),
        (
            """    TTI_SFPSETCC(0, p_sfpu::LREG0, 0, sfpi::SFPSETCC_MOD1_LREG_LT0);\n    TTI_SFPMOV(0, p_sfpu::LCONST_0, p_sfpu::LREG0, 0);\n    TTI_SFPENCC(0, 0, 0, 0);\n    TTI_SFP_STOCH_RND(""",
            """    _uint8_clamp_negatives_();\n    TTI_SFP_STOCH_RND(""",
        ),
        (
            """template <bool APPROXIMATION_MODE, int ITERATIONS = 8, bool SIGN_MAGNITUDE_FORMAT = false>\ninline void calculate_quant_int32(""",
            """template <\n    bool APPROXIMATION_MODE,\n    int ITERATIONS = 8,\n    bool SIGN_MAGNITUDE_FORMAT = false,\n    DataFormat OUTPUT_FORMAT = DataFormat::Int32>\ninline void calculate_quant_int32(""",
        ),
        (
            """        lltt::replay(QUANT_REPLAY_SLOT, QUANT_REPLAY_LEN);                        // MAD + SFPNOP + STOCH_RND\n""",
            """        constexpr std::uint32_t replay_len =\n            OUTPUT_FORMAT == DataFormat::UInt8 ? QUANT_REPLAY_LEN_UINT8_OUT : QUANT_REPLAY_LEN;\n        lltt::replay(QUANT_REPLAY_SLOT, replay_len);\n""",
        ),
        (
            """template <bool APPROXIMATION_MODE, int ITERATIONS = 8, bool SIGN_MAGNITUDE_FORMAT = false, bool INT8_INPUT = false>\ninline void calculate_requant_int32(""",
            """template <\n    bool APPROXIMATION_MODE,\n    int ITERATIONS = 8,\n    bool SIGN_MAGNITUDE_FORMAT = false,\n    bool INT8_INPUT = false,\n    DataFormat OUTPUT_FORMAT = DataFormat::Int32>\ninline void calculate_requant_int32(""",
        ),
        (
            """        lltt::replay(REQUANT_REPLAY_SLOT, REQUANT_REPLAY_LEN);      // CAST + MAD + SFPNOP + STOCH_RND\n""",
            """        constexpr std::uint32_t replay_len =\n            OUTPUT_FORMAT == DataFormat::UInt8 ? REQUANT_REPLAY_LEN_UINT8_OUT : REQUANT_REPLAY_LEN;\n        lltt::replay(REQUANT_REPLAY_SLOT, replay_len);\n""",
        ),
        (
            """    lltt::record<lltt::NoExec>(QUANT_REPLAY_SLOT, QUANT_REPLAY_LEN);\n    {\n""",
            """    constexpr std::uint32_t replay_len =\n        OUTPUT_FORMAT == DataFormat::UInt8 ? QUANT_REPLAY_LEN_UINT8_OUT : QUANT_REPLAY_LEN;\n    lltt::record<lltt::NoExec>(QUANT_REPLAY_SLOT, replay_len);\n    {\n""",
        ),
        (
            """        if constexpr (OUTPUT_FORMAT == DataFormat::UInt8) {\n            TTI_SFP_STOCH_RND(""",
            """        if constexpr (OUTPUT_FORMAT == DataFormat::UInt8) {\n            _uint8_clamp_negatives_();\n            TTI_SFP_STOCH_RND(""",
            2,
        ),
        (
            """    lltt::record<lltt::NoExec>(REQUANT_REPLAY_SLOT, REQUANT_REPLAY_LEN);\n    {\n""",
            """    constexpr std::uint32_t replay_len =\n        OUTPUT_FORMAT == DataFormat::UInt8 ? REQUANT_REPLAY_LEN_UINT8_OUT : REQUANT_REPLAY_LEN;\n    lltt::record<lltt::NoExec>(REQUANT_REPLAY_SLOT, replay_len);\n    {\n""",
        ),
    ]


def _blackhole_replacements() -> list[Replacement]:
    return [
        (
            """constexpr std::uint32_t QUANT_REPLAY_LEN_2S_COMP = 4;\nconstexpr std::uint32_t QUANT_REPLAY_LEN_SIGN_MAGN = 2;\nconstexpr std::uint32_t QUANT_REPLAY_LEN_INT8_OUT = 6;\n""",
            """constexpr std::uint32_t QUANT_REPLAY_LEN_2S_COMP = 4;\nconstexpr std::uint32_t QUANT_REPLAY_LEN_SIGN_MAGN = 2;\nconstexpr std::uint32_t QUANT_REPLAY_LEN_UINT8_OUT = 5;\nconstexpr std::uint32_t QUANT_REPLAY_LEN_INT8_OUT = 6;\n""",
        ),
        (
            """constexpr std::uint32_t REQUANT_REPLAY_LEN_2S_COMP = 7;\nconstexpr std::uint32_t REQUANT_REPLAY_LEN_SIGN_MAGN = 3;\nconstexpr std::uint32_t REQUANT_REPLAY_LEN_INT8_IN = 5;\n""",
            """constexpr std::uint32_t REQUANT_REPLAY_LEN_2S_COMP = 7;\nconstexpr std::uint32_t REQUANT_REPLAY_LEN_SIGN_MAGN = 3;\nconstexpr std::uint32_t REQUANT_REPLAY_LEN_UINT8_SIGN_MAGN = 6;\nconstexpr std::uint32_t REQUANT_REPLAY_LEN_UINT8_2S_COMP = 8;\nconstexpr std::uint32_t REQUANT_REPLAY_LEN_INT8_IN = 5;\n""",
        ),
        (
            """inline void _int8_input_unbias_() { TTI_SFPXOR(0, p_sfpu::LREG3, p_sfpu::LREG0, 0); }\n\n// Fold +128.0""",
            """inline void _int8_input_unbias_() { TTI_SFPXOR(0, p_sfpu::LREG3, p_sfpu::LREG0, 0); }\n\ninline void _uint8_clamp_negatives_() {\n    TTI_SFPSETCC(0, p_sfpu::LREG0, 0, sfpi::SFPSETCC_MOD1_LREG_LT0);\n    TTI_SFPMOV(0, p_sfpu::LCONST_0, p_sfpu::LREG0, 0);\n    TTI_SFPENCC(0, 0, 0, 0);\n}\n\n// Fold +128.0""",
        ),
        (
            """    TTI_SFPSETCC(0, p_sfpu::LREG0, 0, sfpi::SFPSETCC_MOD1_LREG_LT0);\n    TTI_SFPMOV(0, p_sfpu::LCONST_0, p_sfpu::LREG0, 0);\n    TTI_SFPENCC(0, 0, 0, 0);\n    TTI_SFP_STOCH_RND(""",
            """    _uint8_clamp_negatives_();\n    TTI_SFP_STOCH_RND(""",
        ),
        (
            """    constexpr std::uint32_t REPLAY_LEN = SIGN_MAGNITUDE_FORMAT ? QUANT_REPLAY_LEN_SIGN_MAGN : QUANT_REPLAY_LEN_2S_COMP;\n""",
            """    constexpr std::uint32_t REPLAY_LEN =\n        OUTPUT_FORMAT == DataFormat::UInt8\n            ? QUANT_REPLAY_LEN_UINT8_OUT\n            : (SIGN_MAGNITUDE_FORMAT ? QUANT_REPLAY_LEN_SIGN_MAGN : QUANT_REPLAY_LEN_2S_COMP);\n""",
            2,
        ),
        (
            """        if constexpr (OUTPUT_FORMAT == DataFormat::UInt8) {\n            TTI_SFP_STOCH_RND(""",
            """        if constexpr (OUTPUT_FORMAT == DataFormat::UInt8) {\n            _uint8_clamp_negatives_();\n            TTI_SFP_STOCH_RND(""",
            2,
        ),
        (
            """        if constexpr (!SIGN_MAGNITUDE_FORMAT) {\n""",
            """        if constexpr (!SIGN_MAGNITUDE_FORMAT && OUTPUT_FORMAT != DataFormat::UInt8) {\n""",
            2,
        ),
        (
            """    constexpr std::uint32_t REPLAY_LEN =\n        INT8_INPUT ? REQUANT_REPLAY_LEN_INT8_IN\n                   : (SIGN_MAGNITUDE_FORMAT ? REQUANT_REPLAY_LEN_SIGN_MAGN : REQUANT_REPLAY_LEN_2S_COMP);\n""",
            """    constexpr std::uint32_t REPLAY_LEN = OUTPUT_FORMAT == DataFormat::UInt8\n                                             ? ((SIGN_MAGNITUDE_FORMAT || INT8_INPUT)\n                                                    ? REQUANT_REPLAY_LEN_UINT8_SIGN_MAGN\n                                                    : REQUANT_REPLAY_LEN_UINT8_2S_COMP)\n                                             : (INT8_INPUT ? REQUANT_REPLAY_LEN_INT8_IN\n                                                           : (SIGN_MAGNITUDE_FORMAT ? REQUANT_REPLAY_LEN_SIGN_MAGN\n                                                                                   : REQUANT_REPLAY_LEN_2S_COMP));\n""",
            2,
        ),
        (
            """template <bool APPROXIMATION_MODE, int ITERATIONS = 8, bool SIGN_MAGNITUDE_FORMAT = false>\ninline void calculate_quant_int32(""",
            """template <\n    bool APPROXIMATION_MODE,\n    int ITERATIONS = 8,\n    bool SIGN_MAGNITUDE_FORMAT = false,\n    DataFormat OUTPUT_FORMAT = DataFormat::Int32>\ninline void calculate_quant_int32(""",
        ),
        (
            """template <bool APPROXIMATION_MODE, int ITERATIONS = 8, bool SIGN_MAGNITUDE_FORMAT = false, bool INT8_INPUT = false>\ninline void calculate_requant_int32(""",
            """template <\n    bool APPROXIMATION_MODE,\n    int ITERATIONS = 8,\n    bool SIGN_MAGNITUDE_FORMAT = false,\n    bool INT8_INPUT = false,\n    DataFormat OUTPUT_FORMAT = DataFormat::Int32>\ninline void calculate_requant_int32(""",
        ),
    ]


def _quantization_api_replacements() -> list[Replacement]:
    return [
        (
            """ALWI void quant_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {\n    MATH((SFPU_BINARY_CALL(\n        DST_SYNC_MODE, DST_ACCUM_MODE, calculate_quant_int32, (APPROX), idst0, idst1, odst, VectorMode::RC)));\n}\n""",
            """ALWI void quant_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {\n    MATH((SFPU_BINARY_CALL(\n        DST_SYNC_MODE, DST_ACCUM_MODE, calculate_quant_int32, (APPROX), idst0, idst1, odst, VectorMode::RC)));\n}\n\nALWI void quant_uint8_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {\n    MATH((SFPU_BINARY_CALL(\n        DST_SYNC_MODE,\n        DST_ACCUM_MODE,\n        calculate_quant_int32,\n        (APPROX, 8, false, DataFormat::UInt8),\n        idst0,\n        idst1,\n        odst,\n        VectorMode::RC)));\n}\n""",
        ),
        (
            """ALWI void requant_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {\n    MATH((SFPU_BINARY_CALL(\n        DST_SYNC_MODE, DST_ACCUM_MODE, calculate_requant_int32, (APPROX), idst0, idst1, odst, VectorMode::RC)));\n}\n""",
            """ALWI void requant_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {\n    MATH((SFPU_BINARY_CALL(\n        DST_SYNC_MODE, DST_ACCUM_MODE, calculate_requant_int32, (APPROX), idst0, idst1, odst, VectorMode::RC)));\n}\n\nALWI void requant_uint8_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {\n    MATH((SFPU_BINARY_CALL(\n        DST_SYNC_MODE,\n        DST_ACCUM_MODE,\n        calculate_requant_int32,\n        (APPROX, 8, false, false, DataFormat::UInt8),\n        idst0,\n        idst1,\n        odst,\n        VectorMode::RC)));\n}\n""",
        ),
        (
            """ALWI void requant_int8_in_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {\n    MATH((SFPU_BINARY_CALL(\n        DST_SYNC_MODE,\n        DST_ACCUM_MODE,\n        calculate_requant_int32,\n        (APPROX, 8, false, true),\n        idst0,\n        idst1,\n        odst,\n        VectorMode::RC)));\n}\n""",
            """ALWI void requant_int8_in_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {\n    MATH((SFPU_BINARY_CALL(\n        DST_SYNC_MODE,\n        DST_ACCUM_MODE,\n        calculate_requant_int32,\n        (APPROX, 8, false, true),\n        idst0,\n        idst1,\n        odst,\n        VectorMode::RC)));\n}\n\nALWI void requant_int8_in_uint8_out_tile(uint32_t idst0, uint32_t idst1, uint32_t odst) {\n    MATH((SFPU_BINARY_CALL(\n        DST_SYNC_MODE,\n        DST_ACCUM_MODE,\n        calculate_requant_int32,\n        (APPROX, 8, false, true, DataFormat::UInt8),\n        idst0,\n        idst1,\n        odst,\n        VectorMode::RC)));\n}\n""",
        ),
    ]


def _program_factory_replacements() -> list[Replacement]:
    return [
        (
            """        if (c_dtype == DataType::UINT8) {\n            compute_kernel_defines[\"BINARY_SFPU_INIT\"] = std::string(\"quant_uint8_tile_init\") + quant_zp_arg;\n        } else if (c_dtype == DataType::INT8) {\n""",
            """        if (c_dtype == DataType::UINT8) {\n            set_sfpu_op(\"quant_uint8_tile_init\", \"quant_uint8_tile\");\n        } else if (c_dtype == DataType::INT8) {\n""",
        ),
        (
            """        } else if (c_dtype == DataType::UINT8) {\n            // uint8 output uses the standard packer narrowing (int32 SFPU result -> uint8), so it reuses\n            // the int32-output op body; only the init differs, to select FP32_TO_UINT8 rounding.\n            set_sfpu_op(\n                int8_in ? \"requant_int8_in_uint8_out_tile_init\" : \"requant_uint8_tile_init\",\n                int8_in ? \"requant_int8_in_tile\" : \"requant_tile\");\n""",
            """        } else if (c_dtype == DataType::UINT8) {\n            set_sfpu_op(\n                int8_in ? \"requant_int8_in_uint8_out_tile_init\" : \"requant_uint8_tile_init\",\n                int8_in ? \"requant_int8_in_uint8_out_tile\" : \"requant_uint8_tile\");\n""",
        ),
    ]


def _composite_replacements() -> list[Replacement]:
    return [
        (
            """// Narrow composite's fp result to the output dtype. Use quantize as the narrowing step\n// for int8 until typecast(int32 -> int8) is enabled (#50401).\n""",
            """// Narrow composite's fp result to the output dtype. Narrow integer typecasts wrap,\n// so route int8 and uint8 through quantize to preserve saturating semantics.\n""",
        ),
        (
            """    if (c_dtype != ttnn::DataType::INT8) {\n        return ttnn::typecast(shifted, c_dtype, memory_config, optional_output_tensor);\n    }\n""",
            """    if (!is_narrow_quantized_dtype(c_dtype)) {\n        return ttnn::typecast(shifted, c_dtype, memory_config, optional_output_tensor);\n    }\n""",
        ),
        (
            """        ttnn::DataType::INT8,\n        memory_config,\n""",
            """        c_dtype,\n        memory_config,\n""",
        ),
    ]


def _write_upstream_regression_test(root: Path) -> None:
    path = root / "tests/ttnn/nightly/unit_tests/operations/eltwise/test_quantization_uint8_lower_saturation.py"
    if path.exists():
        raise FileExistsError(path)
    path.write_text(
        """# SPDX-FileCopyrightText: © 2026 Tenstorrent USA, Inc.
# SPDX-License-Identifier: Apache-2.0

import torch
import ttnn


def test_quantize_uint8_lower_saturation(device):
    \"\"\"Negative uint8 quantize results clamp to zero.\"\"\"
    input_tr = torch.tensor([[-300.0, -17.0, -2.0, -1.0, 0.0, 1.0, 17.0, 300.0]], dtype=torch.float32)
    expected = torch.clamp(torch.round(input_tr), 0, 255).to(torch.uint8)
    input_tt = ttnn.from_torch(input_tr, dtype=ttnn.float32, layout=ttnn.TILE_LAYOUT, device=device)
    result = ttnn.to_torch(ttnn.quantize(input_tt, 1.0, 0, dtype=ttnn.uint8))
    assert torch.equal(result, expected), f\"got {result.tolist()} expected {expected.tolist()}\"


def test_requantize_uint8_lower_saturation(device):
    \"\"\"Negative uint8 requantize results clamp to zero.\"\"\"
    q_in = torch.tensor([[-1000, -17, -2, -1, 0, 1, 17, 1000]], dtype=torch.int32)
    expected = torch.clamp(torch.round(q_in.to(torch.float32)), 0, 255).to(torch.uint8)
    q_in_tt = ttnn.from_torch(q_in, dtype=ttnn.int32, layout=ttnn.TILE_LAYOUT, device=device)
    result = ttnn.to_torch(ttnn.requantize(q_in_tt, 1.0, 0, 1.0, 0, dtype=ttnn.uint8))
    assert torch.equal(result, expected), f\"got {result.tolist()} expected {expected.tolist()}\"
""",
        encoding="utf-8",
    )


def apply_fix(root: Path) -> None:
    """Apply all issue #56290 changes to the given tt-metal checkout."""
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
