from datetime import datetime as dt
from typing import Any, Union


def parse_float_with_try(v: Any) -> Union[float, int]:
    """convert v to float or 0"""
    try:
        return float(v)
    except ValueError:
        try:
            return int(v)
        except Exception:
            return 0


def parse_date_as_timestamp(v: Any) -> int:
    return int(dt.fromisoformat(v).timestamp())


def AppleStandHourFormatter(record: dict) -> dict:
    date = parse_date_as_timestamp(record.get("startDate", 0))
    unit = record.get("unit", "unit")
    device = record.get("sourceName", "unknown")
    value = 1 if record.get("value") == "HKCategoryValueAppleStandHourStood" else 0

    return {
        "measurement": "AppleStandHour",
        "time": date,
        "fields": {"value": value},
        "tags": {"unit": unit, "device": device},
    }