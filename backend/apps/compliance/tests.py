from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from apps.compliance.phones import format_indian_caller_id, normalise_indian_mobile
from apps.compliance.window import calling_window

IST = ZoneInfo("Asia/Kolkata")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("9876543210", "+919876543210"),
        ("+91 98765 43210", "+919876543210"),
        ("919876543210", "+919876543210"),
        ("09876543210", "+919876543210"),
        ("5876543210", None),
        ("+14155550100", None),
        ("12345", None),
    ],
)
def test_indian_mobile(raw, expected):
    assert normalise_indian_mobile(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("01141334455", "+911141334455"),
        ("+91 1401234567", "+911401234567"),
        ("9876543210", "+919876543210"),
        ("+1 415 555 0100", None),
    ],
)
def test_caller_id_is_indian(raw, expected):
    assert format_indian_caller_id(raw) == expected


def test_calling_window_blocks_night():
    night = datetime(2026, 9, 28, 22, 30, tzinfo=IST)
    allowed, nxt = calling_window(night)
    assert allowed is False
    assert nxt.hour == 9
    assert nxt.day == 29


def test_calling_window_allows_afternoon():
    noon = datetime(2026, 9, 28, 12, 0, tzinfo=IST)
    allowed, nxt = calling_window(noon)
    assert allowed is True
    assert nxt is None
