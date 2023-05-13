#!/bin/bash

# Note that this should be executed within the influx container
# docker compose cp tests.sh influx:/usr/local/bin/
# docker compose exec influx "tests.sh"
measurements=$(influx -database 'health' -execute 'show measurements' | tail -n +4)
for m in $measurements
do 
  influx  -database 'health' -execute 'select(value) from "'$m'" limit 3'
done
