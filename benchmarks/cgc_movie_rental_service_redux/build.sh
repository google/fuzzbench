#!/bin/bash -ex
cd cgc_programs
pip3 install xlsxwriter pycrypto
bash ./build_fuzzbench.sh
cp build_afl1/challenges/Movie_Rental_Service_Redux/Movie_Rental_Service_Redux $OUT/
cp -r /opt/seeds $OUT/