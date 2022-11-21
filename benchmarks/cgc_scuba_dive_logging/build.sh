#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/SCUBA_Dive_Logging/SCUBA_Dive_Logging $OUT/
cp -r /opt/seeds $OUT/