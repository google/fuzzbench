#!/bin/bash

set -x

LOG_DIR=$1
shift 1

mkdir -p "$LOG_DIR/stdout" "$LOG_DIR/stderr"

(
    stdbuf -i 0 -o 0 -e 0 "$@"            | multilog t s16777215 n20 '!tai64nlocal' "$LOG_DIR/stdout"
) 2>&1 1>/dev/null  | multilog t s16777215 n10 '!tai64nlocal' "$LOG_DIR/stderr" 2>/dev/null 1>/dev/null

cat "$LOG_DIR"/stdout/current "$LOG_DIR"/stderr/current | sort