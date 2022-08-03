#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/Carbonate/Carbonate $OUT/
cp -r /opt/seeds $OUT/