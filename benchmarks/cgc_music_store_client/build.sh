#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/Music_Store_Client/Music_Store_Client $OUT/
cp -r /opt/seeds $OUT/