#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/online_job_application/online_job_application $OUT/
cp -r /opt/seeds $OUT/