"""Regression tests for Bounty Plaza #1509 reference semantics."""

import pytest

from reference_model import (
    INT8_MAX,
    INT8_MIN,
    quantize_int8_value,
    quantize_uint8,
    quantize_uint8_value,
    requantize_uint8,
    requantize_uint8_value,
)


def test_quantize_uint8_negative_values_saturate_to_zero() -> None:
    values = [-1000.0, -255.0, -2.0, -1.0, -0.6]
    assert quantize_uint8(values, 1.0, 0) == [0, 0, 0, 0, 0]


def test_quantize_uint8_negative_and_positive_magnitudes_differ() -> None:
    assert quantize_uint8_value(-17.0, 1.0, 0) == 0
    assert quantize_uint8_value(17.0, 1.0, 0) == 17


def test_quantize_uint8_preserves_in_range_values() -> None:
    values = [0.0, 1.0, 42.0, 127.0, 254.0, 255.0]
    assert quantize_uint8(values, 1.0, 0) == [0, 1, 42, 127, 254, 255]


def test_quantize_uint8_upper_values_saturate_to_255() -> None:
    values = [255.0, 256.0, 300.0, 10000.0]
    assert quantize_uint8(values, 1.0, 0) == [255, 255, 255, 255]


def test_quantize_uint8_applies_zero_point_before_clamp() -> None:
    assert quantize_uint8_value(-10.0, 2.0, 20) == 15
    assert quantize_uint8_value(-100.0, 2.0, 20) == 0


def test_quantize_uint8_uses_nearest_even_rounding() -> None:
    assert quantize_uint8_value(2.5, 1.0, 0) == 2
    assert quantize_uint8_value(3.5, 1.0, 0) == 4


def test_requantize_uint8_negative_result_saturates_to_zero() -> None:
    assert requantize_uint8_value(-12, 1.0, 0, 1.0, 0) == 0


def test_requantize_uint8_exact_formula_and_bounds() -> None:
    values = [-100, -1, 0, 10, 255, 1000]
    assert requantize_uint8(values, 2.0, 10, 1.0, 3) == [0, 0, 0, 3, 255, 255]


def test_requantize_uint8_with_nontrivial_scales() -> None:
    assert requantize_uint8_value(20, 0.5, 4, 0.25, 10) == 42


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-1000.0, INT8_MIN),
        (-128.0, INT8_MIN),
        (-17.0, -17),
        (0.0, 0),
        (17.0, 17),
        (127.0, INT8_MAX),
        (1000.0, INT8_MAX),
    ],
)
def test_int8_behavior_is_preserved(value: float, expected: int) -> None:
    assert quantize_int8_value(value, 1.0, 0) == expected


@pytest.mark.parametrize(
    ("function_name", "args"),
    [
        ("quantize", (1.0, 0.0, 0)),
        ("requantize", (1, 1.0, 0, 0.0, 0)),
    ],
)
def test_zero_scale_is_rejected(function_name: str, args: tuple[object, ...]) -> None:
    function = quantize_uint8_value if function_name == "quantize" else requantize_uint8_value
    with pytest.raises(ValueError):
        function(*args)
