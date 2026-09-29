import re

OPT_OUT_PHRASES = {
    "stop",
    "unsubscribe",
    "stopall",
    "stop all",
    "cancel",
    "रुको",
    "रुक जाओ",
    "बंद करो",
    "बंद",
}


def is_opt_out(text):
    cleaned = re.sub(r"[^\w\s\u0900-\u097F]", "", text or "", flags=re.UNICODE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().casefold()
    return cleaned in OPT_OUT_PHRASES
