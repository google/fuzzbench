#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/Loud_Square_Instant_Messaging_Protocol_LSIMP/Loud_Square_Instant_Messaging_Protocol_LSIMP $OUT/
cp -r /opt/seeds $OUT/