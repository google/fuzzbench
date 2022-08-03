#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/Simple_Stack_Machine/Simple_Stack_Machine $OUT/
cp -r /opt/seeds $OUT/