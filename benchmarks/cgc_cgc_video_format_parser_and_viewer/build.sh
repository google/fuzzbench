#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/CGC_Video_Format_Parser_and_Viewer/CGC_Video_Format_Parser_and_Viewer $OUT/
cp -r /opt/seeds $OUT/