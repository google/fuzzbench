#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/CGC_Symbol_Viewer_CSV/CGC_Symbol_Viewer_CSV $OUT/
cp -r /opt/seeds $OUT/