#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/Sad_Face_Template_Engine_SFTE/Sad_Face_Template_Engine_SFTE $OUT/
cp -r /opt/seeds $OUT/