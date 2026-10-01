#!/bin/sh
set -eu

cd "$(dirname "$0")"
exec npm run dev -- --host 0.0.0.0 --port 5174
