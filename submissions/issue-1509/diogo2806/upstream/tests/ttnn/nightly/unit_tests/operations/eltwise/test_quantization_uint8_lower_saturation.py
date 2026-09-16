# SPDX-FileCopyrightText: © 2026 Tenstorrent USA, Inc.
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
