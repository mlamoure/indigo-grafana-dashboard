#!/usr/bin/env bash
# Live InfluxDB matrix: runs tests/live against throwaway influxdb:1.8 (auth on)
# and influxdb:3-core containers, then removes them.  Every release must pass it
# (issue #12); the release notes name the versions it printed.
#
#   tests/live/run_influx_matrix.sh            # from the repo root
#   PYTHON=python3 INFLUX3_IMAGE=influxdb:3-core tests/live/run_influx_matrix.sh -k conflict
set -euo pipefail

cd "$(dirname "$0")/../.."
PYTHON=${PYTHON:-.venv/bin/python}
IMAGE_18=${INFLUX18_IMAGE:-influxdb:1.8}
IMAGE_3=${INFLUX3_IMAGE:-influxdb:3-core}
NAME_18="igd-live-18-$$"
NAME_3="igd-live-3-$$"

cleanup() { docker rm -f "$NAME_18" "$NAME_3" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker run -d --name "$NAME_18" -p 127.0.0.1::8086 \
  -e INFLUXDB_HTTP_AUTH_ENABLED=true -e INFLUXDB_ADMIN_USER=admin -e INFLUXDB_ADMIN_PASSWORD=live-admin-pw \
  "$IMAGE_18" >/dev/null
docker run -d --name "$NAME_3" -p 127.0.0.1::8181 \
  "$IMAGE_3" influxdb3 serve --node-id live --object-store memory >/dev/null

port_of() { docker port "$1" "$2" | head -1 | sed 's/.*://'; }
PORT_18=$(port_of "$NAME_18" 8086)
PORT_3=$(port_of "$NAME_3" 8181)

for _ in $(seq 1 60); do
  if curl -fs "http://127.0.0.1:$PORT_18/ping" >/dev/null 2>&1; then break; fi; sleep 1
done
for _ in $(seq 1 60); do
  # 401 = up (InfluxDB 3 authenticates /ping)
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT_3/ping" || true)
  if [ "$code" = "401" ] || [ "$code" = "200" ]; then break; fi; sleep 1
done

TOKEN_3=$(docker exec "$NAME_3" influxdb3 create token --admin 2>/dev/null | grep -o 'apiv3_[A-Za-z0-9_-]*' | head -1)
if [ -z "$TOKEN_3" ]; then echo "could not create an InfluxDB 3 token" >&2; exit 1; fi

VERSION_18=$(docker exec "$NAME_18" influxd version 2>/dev/null | head -1)
VERSION_3=$(docker exec "$NAME_3" influxdb3 --version 2>/dev/null | head -1)

export INFLUX_LIVE=1 INFLUX18_PORT="$PORT_18" INFLUX18_ADMIN=admin INFLUX18_ADMIN_PASSWORD=live-admin-pw \
       INFLUX3_PORT="$PORT_3" INFLUX3_TOKEN="$TOKEN_3"

status=0
"$PYTHON" -m pytest tests/live -q -p no:cacheprovider "$@" || status=$?

echo
echo "InfluxDB versions tested: $VERSION_18 | $VERSION_3"
exit $status
