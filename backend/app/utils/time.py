from datetime import date, datetime
from zoneinfo import ZoneInfo


DHAKA_TIMEZONE = ZoneInfo("Asia/Dhaka")


def dhaka_today() -> date:
    return datetime.now(DHAKA_TIMEZONE).date()
