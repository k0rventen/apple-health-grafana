"""
Ingester module that converts Apple Health export zip file
into influx db datapoints
"""
import os
import re
import time
import xml.etree.ElementTree as etree
from shutil import unpack_archive
from typing import Any, Union

import gpxpy
from dateutil.parser import parse
from gpxpy.gpx import GPXTrackPoint
from influxdb import InfluxDBClient

CLIENT = InfluxDBClient("influx", 8086, database="health")
PREFIX_RE = re.compile("HK.*Identifier(.+)$")
ZIP_PATH = "/export.zip"
UNZIP_PATH = "/export"
ROUTES_PATH = "/export/apple_health_export/workout-routes/"
EXPORT_PATH = "/export/apple_health_export/export.xml"


def try_to_float(v: Any) -> Union[float, int]:
    """convert v to float or 0"""
    try:
        return float(v)
    except ValueError:
        try:
            return int(v)
        except Exception:
            return 0


def format_route_point(name, point: GPXTrackPoint, next_point=None) -> dict[str, Any]:
    """for a given `point`, creates an influxdb point
    and computes speed and distance if `next_point` exists
    """
    slug_name = name.replace(" ", "-").replace(":", "-").lower()
    datapoint = {
        "measurement": "workout-routes",
        "tags": {"workout": slug_name},
        "time": point.time,
        "fields": {
            "latitude": point.latitude,
            "longitude": point.longitude,
            "elevation": point.elevation,
        },
    }
    if next_point:
        datapoint["fields"]["speed"] = (
            point.speed_between(next_point) if next_point else 0
        )
        datapoint["fields"]["distance"] = point.distance_3d(next_point)
    return datapoint


def format_record(record: dict[str, Any]) -> dict[str, Any]:
    """format a export health xml record for influx"""
    m = re.match(PREFIX_RE, record.get("type"))
    measurement = m.group(1) if m else record.get("type")
    value = try_to_float(record.get("value", 1))
    unit = record.get("unit", "unit")
    date = int(parse(record.get("startDate")).timestamp())
    device = record.get("sourceName", "unknown")

    return {
        "measurement": measurement,
        "tags": {"unit": unit, "device": device},
        "time": date,
        "fields": {"value": value},
    }


def parse_workout_route(route_xml_file: str) -> None:
    with open(route_xml_file, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        for track in gpx.tracks:
            track_points = []
            print("Opening", track.name)
            for segment in track.segments:
                num_points = len(segment.points)
                for i in range(num_points):
                    track_points.append(
                        format_route_point(
                            track.name,
                            segment.points[i],
                            segment.points[i + 1] if i + 1 < num_points else None,
                        )
                    )
            CLIENT.write_points(track_points, time_precision="s")


def process_workout_routes() -> None:
    if os.path.exists(ROUTES_PATH) and os.path.isdir(ROUTES_PATH):
        print("Loading workout routes ...")
        for file in os.listdir(ROUTES_PATH):
            if file.endswith(".gpx"):
                route_file = os.path.join(ROUTES_PATH, file)
                parse_workout_route(route_file)
    else:
        print("No workout routes found, skipping ...")


def process_health_data() -> None:
    if not os.path.exists(EXPORT_PATH):
        print("No export.xml file found, skipping ...")
        return
    formatted_records = []
    total_count = 0
    for _, elem in etree.iterparse(EXPORT_PATH):
        if elem.tag == "Record":
            f = format_record(elem)
            formatted_records.append(f)
            elem.clear()

            # batch push every 10000
            if len(formatted_records) == 10000:
                total_count += 10000
                CLIENT.write_points(formatted_records, time_precision="s")
                del formatted_records
                formatted_records = []
                print("Inserted", total_count, "records")

    # push the rest
    CLIENT.write_points(formatted_records, time_precision="s")
    print("Total number of records:", total_count + len(formatted_records))


if __name__ == "__main__":
    print("Unzipping the export file ...")
    try:
        unpack_archive(ZIP_PATH, UNZIP_PATH)
    except Exception as unzip_err:
        print("Unable to open export zip:", unzip_err)
        exit(1)
    print("Export file unzipped!")

    while True:
        try:
            CLIENT.ping()
            CLIENT.drop_database("health")
            CLIENT.create_database("health")
            print("Influx is ready.")
            break
        except Exception:
            print("Waiting on influx to be ready..")
            time.sleep(1)

    process_workout_routes()
    process_health_data()
    print("All done! You can now check grafana.")
