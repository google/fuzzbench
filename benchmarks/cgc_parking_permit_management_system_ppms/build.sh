#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/Parking_Permit_Management_System_PPMS/Parking_Permit_Management_System_PPMS $OUT/
cp -r /opt/seeds $OUT/