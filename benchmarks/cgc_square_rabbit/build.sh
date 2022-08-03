#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/Square_Rabbit/Square_Rabbit $OUT/
cp -r /opt/seeds $OUT/