#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/CGC_Planet_Markup_Language_Parser/CGC_Planet_Markup_Language_Parser $OUT/
cp -r /opt/seeds $OUT/