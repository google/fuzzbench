#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/String_Storage_and_Retrieval/String_Storage_and_Retrieval $OUT/
cp -r /opt/seeds $OUT/