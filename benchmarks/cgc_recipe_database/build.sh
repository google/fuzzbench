#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/Recipe_Database/Recipe_Database $OUT/
cp -r /opt/seeds $OUT/