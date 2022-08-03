#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/Cromulence_All_Service/Cromulence_All_Service $OUT/
cp -r /opt/seeds $OUT/