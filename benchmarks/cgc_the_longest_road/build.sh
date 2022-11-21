#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/The_Longest_Road/The_Longest_Road $OUT/
cp -r /opt/seeds $OUT/