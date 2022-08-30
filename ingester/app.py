import re

from dateutil.parser import parse
from influxdb import InfluxDBClient
import xml.etree.cElementTree as etree
import time 


PREFIX_RE = re.compile('HK.*Identifier(.+)$')
input_path = '/export.xml'

def try_to_float(v):
    try:
        return float(v)
    except ValueError:
        try:
            return int(v)
        except:
            return 1

def format_record(record):
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

client = InfluxDBClient('influx', 8086, database='health')
while True:
    try:
        client.ping()
        break
    except:
        print("waiting on influx to be ready..")
        time.sleep(1)

client.drop_database("health")
client.create_database("health")


formatted_records = []
total_count = 0
for _, elem in etree.iterparse("/export.xml"):
    if elem.tag == "Record":
        f = format_record(elem)
        formatted_records.append(f)
        del elem

        # batch push every 10000
        if len(formatted_records) == 10000:
            total_count += 10000
            client.write_points(formatted_records,time_precision="s")
            formatted_records.clear()
            print("inserted",total_count,"records")

# push the rest
client.write_points(formatted_records,time_precision="s")
print("Total number of records:",total_count+len(formatted_records))
print('All done ! You can now check grafana.')