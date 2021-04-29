#!/bin/bash

test -z "$1" -o -z "$2" -o '!' -e "$1" && exit 0

file "$1" | grep -q executable && {
  nm "$1" | grep -i "T $2" | awk '{print"0x"$1}'
  exit 0
}

nm "$1" | grep -i "T $2" | '{print$1}' | tr a-f A-F | \
  xargs echo "ibase=16;obase=10;555555554000 + " | bc | tr A-F a-f
exit 0
