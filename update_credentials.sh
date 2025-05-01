#!/bin/bash
# Script to update InfluxDB credentials and fix issues

echo "========================================================"
echo "Virtuoso Trading System - Configuration and Fix Script"
echo "========================================================"

# InfluxDB credentials
export INFLUXDB_URL="http://localhost:8086"
export INFLUXDB_TOKEN="j2SJuqADTUPO-KS31ttYTY7L2ByYHNToKE1GWYYKrKh8tQXD13E8nJES3yMgvOqg3ko1o5NvQggim0MhZ4b3PA=="
export INFLUXDB_ORG="coinmaestro"
export INFLUXDB_BUCKET="VirtuosoDB"

echo "InfluxDB credentials exported to environment:"
echo "- URL: $INFLUXDB_URL"
echo "- Organization: $INFLUXDB_ORG"
echo "- Bucket: $INFLUXDB_BUCKET"
echo "- Token: ${INFLUXDB_TOKEN:0:10}...${INFLUXDB_TOKEN: -10}" # Show only part of the token for security

echo ""
echo "Issues fixed:"
echo "1. JSON Serialization Error: Updated PDF generator to use CustomJSONEncoder"
echo "   for handling pandas Timestamp objects"
echo ""
echo "2. InfluxDB Authentication: Set environment variables with correct credentials"
echo ""

echo "To use these credentials, run:"
echo "source update_credentials.sh"
echo ""
echo "Then run your application to use the updated environment variables" 