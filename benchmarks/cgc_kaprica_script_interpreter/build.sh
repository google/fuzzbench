#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/Kaprica_Script_Interpreter/Kaprica_Script_Interpreter $OUT/
cp -r /opt/seeds $OUT/