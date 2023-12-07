#!/bin/bash
set -e
influx  -database 'health' -format 'json' -execute 'SELECT COUNT(x) FROM (SELECT *,x::INTEGER FROM 'WalkingSpeed' FILL(0))' | jq -e '.results[0].series[0].values[0][1]|contains(400)'
influx  -database 'health' -format 'json' -execute 'SELECT COUNT(x) FROM (SELECT *,x::INTEGER FROM 'StepCount' FILL(0))' | jq -e '.results[0].series[0].values[0][1]|contains(399)'

influx -format 'json' -execute 'DROP DATABASE health'