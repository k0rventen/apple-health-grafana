# prep the test env
set -e

chmod a+x tests.sh
docker compose down
docker compose build

# ingester/influx tests
docker compose up -d influx
docker compose exec influx apt update
docker compose exec influx apt install jq -y
docker compose cp tests.sh influx:/usr/local/bin/

# for each compose service, run it, check for output, then reset influx
for service in test-ingester-std test-ingester-no-routes-uppercase test-ingester-malformed-xml test-ingester-malformed-xml-2
do
  docker compose up --exit-code-from $service $service 
  docker compose exec influx tests.sh
done

# grafana test
docker compose up -d grafana
sleep 10
docker compose exec grafana curl http://127.0.0.1:3000/api/dashboards/home -f -u 'admin:health' 


docker compose down