"""
Ingester module that converts Apple Health export zip file
into influx db datapoints
"""
import os
import re
import time
from lxml import etree
from shutil import unpack_archive
from typing import Any
import subprocess

from formatters import parse_date_as_timestamp, parse_float_with_try, AppleStandHourFormatter, SleepAnalysisFormatter

import gpxpy
from gpxpy.gpx import GPXTrackPoint
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

ZIP_PATH = "/export.zip"
ROUTES_PATH = "/export/apple_health_export/workout-routes/"
EXPORT_PATH = "/export/apple_health_export"
EXPORT_XML_REGEX = re.compile("export.xml", re.IGNORECASE)

points_sources = set()

def format_route_point(
    name: str, point: GPXTrackPoint, next_point=None
) -> dict[str, Any]:
    """for a given `point`, creates an influxdb point
    and computes speed and distance if `next_point` exists"""
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
    measurement = (
        record.get("type", "Record")
        .removeprefix("HKQuantityTypeIdentifier")
        .removeprefix("HKCategoryTypeIdentifier")
        .removeprefix("HKDataType")
    )

    if measurement == "AppleStandHour":
        return AppleStandHourFormatter(record)
    if measurement == "SleepAnalysis":
        return SleepAnalysisFormatter(record)

    date = parse_date_as_timestamp(record.get("startDate", 0))
    value = parse_float_with_try(record.get("value", 1))
    unit = record.get("unit", "unit")
    device = record.get("sourceName", "unknown")

    return [{
        "measurement": measurement,
        "time": date,
        "fields": {"value": value},
        "tags": {"unit": unit, "device": device},
    }]


def format_workout(record: dict[str, Any]) -> dict[str, Any]:
    """format a export health xml workout record for influx"""
    measurement = record.get("workoutActivityType", "Workout").removeprefix(
        "HKWorkoutActivityType"
    )
    date = parse_date_as_timestamp(record.get("startDate", 0))
    value = parse_float_with_try(record.get("duration", 0))
    unit = record.get("durationUnit", "unit")
    device = record.get("sourceName", "unknown")

    return {
        "measurement": measurement,
        "time": date,
        "fields": {"value": value},
        "tags": {"unit": unit, "device": device},
    }


def parse_workout_route(client: InfluxDBClient, bucket: str, route_xml_file: str) -> None:
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
            client.write_points(track_points, time_precision="s")


def process_workout_routes(client: InfluxDBClient, bucket: str) -> None:
    if os.path.exists(ROUTES_PATH) and os.path.isdir(ROUTES_PATH):
        print("Loading workout routes ...")
        for file in os.listdir(ROUTES_PATH):
            if file.endswith(".gpx"):
                route_file = os.path.join(ROUTES_PATH, file)
                parse_workout_route(client,bucket,route_file)
    else:
        print("No workout routes found, skipping ...")


def process_health_data(client: InfluxDBClient, bucket: str) -> None:
    export_xml_files = [f for f in os.listdir(EXPORT_PATH) if EXPORT_XML_REGEX.match(f)]
    if not export_xml_files:
        print("No export file found, skipping...")
        return
    export_file = os.path.join(EXPORT_PATH, export_xml_files[0])
    print("Export file is", export_file)

    print("Removing potentially malformed XML..")
    p = subprocess.run("sed -i '/<HealthData/,$!d' " + export_file, shell=True, capture_output=True)
    if p.returncode != 0:
        print(p.stdout, p.stderr)

    records = []
    total_count = 0
    context = etree.iterparse(export_file, recover=True)
    for _, elem in context:
        points_sources.add(elem.get("sourceName", "unknown"))

        if elem.tag == "Record":
            rec = format_record(elem)
            records += rec
        elif elem.tag == "Workout":
            records.append(format_workout(elem))
        elem.clear()
        # batch write every ~10000
        if len(records) >= 10000:
            total_count += len(records)
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(bucket=bucket, record=records)

            del records
            records = []
            print("Inserted", total_count, "records")

    # write the rest
    write_api = client.write_api(write_options=SYNCHRONOUS)
    write_api.write(bucket=bucket, record=records)
    print("Total number of records:", total_count + len(records))

def push_sources(client: InfluxDBClient, bucket: str):
    sources_points = [
        Point("data-sources").tag("device", s).field("value", 1)
        for s in points_sources
    ]
    print("pushing", len(sources_points), "sources !")
    write_api = client.write_api(write_options=SYNCHRONOUS)
    write_api.write(bucket=bucket, record=sources_points)

if __name__ == "__main__":
    print("Unzipping the export file...")
    try:
        unpack_archive(ZIP_PATH, "/export")
    except Exception as unzip_err:
        print("Unable to open export zip:", unzip_err)
        exit(1)
    print("Export file unzipped!")

    # Get environment variables
    influx_token = os.environ.get("INFLUX_TOKEN")
    influx_org = os.environ.get("INFLUX_ORG")
    influx_bucket = os.environ.get("INFLUX_BUCKET")

    # Create InfluxDB client
    client = InfluxDBClient(url="http://influx:8086", token=influx_token, org=influx_org)

    while True:
        try:
            client.health()
            print("Influx is ready.")
            break
        except Exception:
            print("Waiting on influx to be ready..")
            time.sleep(1)

    process_workout_routes(client, influx_bucket)
    process_health_data(client, influx_bucket)
    push_sources(client, influx_bucket)
    print("All done! You can now check grafana.")
