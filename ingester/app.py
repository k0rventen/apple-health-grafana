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
    return datapoint


def format_record(record: dict[str, Any]) -> dict[str, Any]:
    }]


def format_workout(record: dict[str, Any]) -> dict[str, Any]:
    }


def parse_workout_route(client: InfluxDBClient, route_xml_file: str) -> None:
            client.write_points(track_points, time_precision="s")


def process_workout_routes(client: InfluxDBClient) -> None:
        print("No workout routes found, skipping ...")


def process_health_data(client: InfluxDBClient) -> None:
    print("Total number of records:", total_count + len(records))

def push_sources(client: InfluxDBClient):
    client.write_points(sources_points,time_precision="s")

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

    process_workout_routes(client)
    process_health_data(client)
    push_sources(client)
    print("All done! You can now check grafana.")
