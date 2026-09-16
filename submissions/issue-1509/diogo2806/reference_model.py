"""Reference semantics for Tenstorrent issue #56290 / Bounty Plaza #1509.

The model mirrors the documented affine quantize and requantize formulas and,
most importantly, applies unsigned saturation before conversion to uint8.
It is intentionally hardware-independent so the bounty scorer can validate
observable behavior while the accompanying C++ patch fixes the real SFPU path.
"""

from __future__ import annotations

from collections.abc import Iterable

UINT8_MIN = 0
UINT8_MAX = 255
INT8_MIN = -128
INT8_MAX = 127


def _validate_scale(scale: float, name: str) -> None:
    """Reject zero scales because affine quantization divides by scale."""
    if scale == 0:
        raise ValueError(f"{name} must be non-zero")


def _round_nearest_even(value: float) -> int:
    """Round a floating-point value using Python's ties-to-even semantics."""
    return int(round(value))


def _clamp(value: int, lower: int, upper: int) -> int:
    """Clamp an integer into an inclusive range."""
    return min(max(value, lower), upper)


def quantize_uint8_value(value: float, scale: float, zero_point: int) -> int:
    """Quantize one floating-point value into the saturated uint8 domain."""
    _validate_scale(scale, "scale")
    transformed = value / scale + zero_point
    rounded = _round_nearest_even(transformed)
    return _clamp(rounded, UINT8_MIN, UINT8_MAX)


def requantize_uint8_value(
    value: int,
    input_scale: float,
    input_zero_point: int,
    output_scale: float,
    output_zero_point: int,
) -> int:
    """Requantize one integer value into the saturated uint8 domain."""
    _validate_scale(input_scale, "input_scale")
    _validate_scale(output_scale, "output_scale")
    transformed = (
        (value - input_zero_point) * input_scale / output_scale + output_zero_point
    )
    rounded = _round_nearest_even(transformed)
    return _clamp(rounded, UINT8_MIN, UINT8_MAX)


def quantize_int8_value(value: float, scale: float, zero_point: int) -> int:
    """Reference signed int8 behavior used to guard against regressions."""
    _validate_scale(scale, "scale")
    transformed = value / scale + zero_point
    rounded = _round_nearest_even(transformed)
    return _clamp(rounded, INT8_MIN, INT8_MAX)


def quantize_uint8(values: Iterable[float], scale: float, zero_point: int) -> list[int]:
    """Quantize an iterable using uint8 saturation."""
    return [quantize_uint8_value(value, scale, zero_point) for value in values]


def requantize_uint8(
    values: Iterable[int],
    input_scale: float,
    input_zero_point: int,
    output_scale: float,
    output_zero_point: int,
) -> list[int]:
    """Requantize an iterable using uint8 saturation."""
    return [
        requantize_uint8_value(
            value,
            input_scale,
            input_zero_point,
            output_scale,
            output_zero_point,
        )
        for value in values
    ]
