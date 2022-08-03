#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/CGC_File_System/CGC_File_System $OUT/
cp -r /opt/seeds $OUT/