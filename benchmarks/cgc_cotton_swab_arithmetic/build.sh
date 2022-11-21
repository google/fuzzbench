#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/cotton_swab_arithmetic/cotton_swab_arithmetic $OUT/
cp -r /opt/seeds $OUT/