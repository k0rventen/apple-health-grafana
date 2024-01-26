from datetime import datetime as dt
from datetime import timedelta

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


sleep_states_lookup={
    "HKCategoryValueSleepAnalysisAsleepDeep":0,
    "HKCategoryValueSleepAnalysisAsleepCore":1,
    "HKCategoryValueSleepAnalysisAsleepREM":2,
    #"HKCategoryValueSleepAnalysisAsleepUnspecified":3,
    "HKCategoryValueSleepAnalysisInBed": 3,
    "HKCategoryValueSleepAnalysisAwake":4,
}

sleep_states_short_lookup={
    "HKCategoryValueSleepAnalysisAsleepDeep":"Deep",
    "HKCategoryValueSleepAnalysisAsleepCore":"Core",
    "HKCategoryValueSleepAnalysisAsleepREM":"REM",
    #"HKCategoryValueSleepAnalysisAsleepUnspecified":"Asleep",
    "HKCategoryValueSleepAnalysisInBed": "Asleep",
    "HKCategoryValueSleepAnalysisAwake":"Awake",
}

def SleepAnalysisFormatter(record: dict) -> dict:
    start_date = dt.fromisoformat(record.get("startDate"))
    start_date.replace(second=0)
    end_date = dt.fromisoformat(record.get("endDate"))
    device = record.get("sourceName", "unknown")
    state = sleep_states_lookup.get(record.get("value"),5)
    if "Apple Watch" in device:
        print(start_date,end_date,device,state)

    minutes_in_bed = []
    while start_date <= end_date:
        minutes_in_bed.append({
            'measurement':"SleepAnalysisTimes-{}".format(device),
            "time":int(start_date.timestamp()),
            "fields": {"value":state},
            "tags": {}
        })
        start_date += timedelta(minutes=1)

    minutes_in_bed.append({
            'measurement':'SleepAnalysis',
            "time":start_date,
            "fields": {"start": int(dt.fromisoformat(record.get("startDate")).timestamp()),"stop":int(dt.fromisoformat(record.get("endDate")).timestamp())},
            "tags": {"unit": 'seconds', "device": device,'state':sleep_states_short_lookup.get(record.get("value"),"Unspecified")}
        })
    return minutes_in_bed
