#!/bin/bash
# Run the FastMCP server

set -e

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values
TRANSPORT=${TRANSPORT:-http}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

echo "=================================="
echo "Starting FastMCP Server"
echo "=================================="
echo "Transport: $TRANSPORT"
echo "Host: $HOST"
echo "Port: $PORT"
echo "Environment: ${ENVIRONMENT:-development}"
echo "=================================="
echo ""

# Run the server
python -m fastmcp run src/server.py --transport "$TRANSPORT" --host "$HOST" --port "$PORT"
