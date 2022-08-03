#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/matrices_for_sale/matrices_for_sale $OUT/
cp -r /opt/seeds $OUT/