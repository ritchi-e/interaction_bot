from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings

IST = ZoneInfo("Asia/Kolkata")


def now_ist():
    return datetime.now(IST)


def next_open(local, start_hour):
    opening = local.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    if local < opening:
        return opening
    return opening + timedelta(days=1)


def calling_window(moment=None):
    """TRAI-style window: dial only between 09:00 and 21:00 IST.

    Returns (allowed, next_allowed_datetime). next_allowed_datetime is None when allowed.
    """
    start_hour = settings.CALLING_WINDOW_START_HOUR
    end_hour = settings.CALLING_WINDOW_END_HOUR
    moment = moment or now_ist()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=IST)
    local = moment.astimezone(IST)
    opening = local.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    closing = local.replace(hour=end_hour, minute=0, second=0, microsecond=0)
    if opening <= local < closing:
        return True, None
    return False, next_open(local, start_hour)
