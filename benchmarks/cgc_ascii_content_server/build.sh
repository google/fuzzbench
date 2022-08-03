#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/ASCII_Content_Server/ASCII_Content_Server $OUT/
cp -r /opt/seeds $OUT/