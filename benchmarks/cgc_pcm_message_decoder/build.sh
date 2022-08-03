#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/PCM_Message_decoder/PCM_Message_decoder $OUT/
cp -r /opt/seeds $OUT/