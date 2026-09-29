import re

_NON_DIGIT = re.compile(r"\D")


def digits_only(raw):
    return _NON_DIGIT.sub("", raw or "")


def normalise_indian_mobile(raw):
    """Return E.164 +91XXXXXXXXXX for an Indian mobile, or None.

    Mobile numbers start with 6, 7, 8, or 9. Landlines and 140-series CLI
    numbers are caller IDs, not customer mobiles, so they are rejected here.
    """
    digits = digits_only(raw)
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("91") and len(digits) == 12:
        national = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        national = digits[1:]
    elif len(digits) == 10:
        national = digits
    else:
        return None
    if len(national) != 10 or national[0] not in "6789":
        return None
    return "+91" + national


def format_indian_caller_id(raw):
    """Format a TRAI-registered Indian CLI as +91.

    Accepts mobiles, landlines (with STD), and virtual numbers such as 140/160
    series. Rejects anything that is not an Indian number.
    """
    digits = digits_only(raw)
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0"):
        digits = digits[1:]
    if digits.startswith("91") and len(digits) in (12, 13):
        national = digits[2:]
    elif len(digits) == 10:
        national = digits
    elif len(digits) == 11 and not digits.startswith("1"):
        national = digits
    else:
        return None
    if len(national) not in (10, 11) or national[0] == "0":
        return None
    return "+91" + national
