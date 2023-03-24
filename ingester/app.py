"""
Ingester module that converts Apple Health export zip file
into influx db datapoints
"""
import os
import re
import time
import xml.etree.ElementTree as etree
from shutil import unpack_archive

import gpxpy
from dateutil.parser import parse
from gpxpy.gpx import GPXTrackPoint
from influxdb import InfluxDBClient

client = InfluxDBClient('influx', 8086, database='health')
PREFIX_RE = re.compile('HK.*Identifier(.+)$')
zip_path = '/export.zip'
unzip_path = "/export"
routes_path = "/export/apple_health_export/workout-routes/"
export_path = "/export/apple_health_export/export.xml"

def try_to_float(v):
    """convert v to float or 0"""
    try:
        return float(v)
    except ValueError:
        try:
            return int(v)
        except:
            return 0


def format_route_point(name,point: GPXTrackPoint,next_point=None)-> dict:
    """for a given `point`, creates an influxdb point
    and computes speed and distance if `next_point` exists
    """
    slug_name = name.replace(" ","-").replace(":","-").lower()
    datapoint = {
        "measurement":'workout-routes',
        "tags":{
            "workout":slug_name
        },
        "time":point.time,
        "fields":{
            "latitude":point.latitude,
            "longitude": point.longitude,
            "elevation": point.elevation,
            
        }}
    if next_point:
        datapoint['fields']['speed'] = point.speed_between(next_point) if next_point else 0
        datapoint['fields']['distance'] = point.distance_3d(next_point)
    return datapoint

def format_record(record):
    """format a export health xml record for influx"""
    m = re.match(PREFIX_RE, record.get("type"))
    measurement =  m.group(1) if m else record.get("type")
    value = try_to_float(record.get("value",1))
    unit = record.get("unit","unit")
    date = int(parse(record.get("startDate")).timestamp())

    return {
        "measurement":measurement,
        "tags":{
            "unit":unit
        },
        "time":date,
        "fields":{
            "value":value
        }
    }



def parse_workout_route(route_xml_file):
    with open(route_xml_file, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        for track in gpx.tracks:
            track_points=[]
            print("opening",track.name)
            for segment in track.segments:
                num_points = len(segment.points)
                for i in range(num_points):
                    track_points.append(format_route_point(track.name,segment.points[i],segment.points[i+1] if i +1 < num_points else None))
            client.write_points(track_points,time_precision="s")


def process_workout_routes():
    if os.path.exists(routes_path) and os.path.isdir(routes_path):
        print('loading workout routes')
        for file in os.listdir(routes_path):
            if file.endswith(".gpx"):
                route_file = os.path.join(routes_path, file)
                parse_workout_route(route_file)
    else:
        print('no workout routes found, skipping..')


def process_health_data():
    if not os.path.exists(export_path):
        print("no export.xml file found, skipping")
        return
    formatted_records = []
    total_count = 0
    for _, elem in etree.iterparse(export_path):
        if elem.tag == "Record":
            f = format_record(elem)
            formatted_records.append(f)
            elem.clear()

            # batch push every 10000
            if len(formatted_records) == 10000:
                total_count += 10000
                client.write_points(formatted_records,time_precision="s")
                del formatted_records
                formatted_records = []
                print("inserted",total_count,"records")

    # push the rest
    client.write_points(formatted_records,time_precision="s")
    print("Total number of records:",total_count+len(formatted_records))

if __name__ == "__main__":
    print('unzipping the export file..')
    try:
        unpack_archive(zip_path, unzip_path)
    except Exception as unzip_err:
        print("Unable to open export zip: ",unzip_err)
        exit(1)
    print('export file unzipped')


    while True:
        try:
            client.ping()
            client.drop_database("health")
            client.create_database("health")
            print('influx is ready')
            break
        except:
            print("waiting on influx to be ready..")
            time.sleep(1)

    process_workout_routes()
    process_health_data()
    print('All done ! You can now check grafana.')
