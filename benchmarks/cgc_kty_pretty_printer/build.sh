#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/KTY_Pretty_Printer/KTY_Pretty_Printer $OUT/
cp -r /opt/seeds $OUT/