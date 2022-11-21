#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/Vector_Graphics_2/Vector_Graphics_2 $OUT/
cp -r /opt/seeds $OUT/