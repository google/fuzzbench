#! /usr/bin/env bash

SRC_DIR=$1

tar xf libpastis.tar.gz
cd libpastis
pip3 install .
cd ..

tar xf klockwork.tar.gz
cd klockwork
pip3 install .
cd ..

tar xf pastis-aflpp.tar.gz
cd pastis-aflpp
pip3 install .
cd broker-addon/
pip3 install .
cd ../..

tar xf pastis-hf.tar.gz
cd pastis-hf
pip3 install .
cd broker-addon/
pip3 install .
cd ../..

tar xf tritondse.tar.gz
cd tritondse
pip3 install .
cd ..

tar xf pastis-triton.tar.gz
cd pastis-triton
pip3 install .
cd broker-addon/
pip3 install .
cd ../..

tar xf pastis-broker.tar.gz
cd pastis-broker
pip3 install .
cd ..

tar xf pastisd.tar.gz
cd pastisd/
pip3 install .
cd ..

tar xf pastis-benchmarks.tar.gz
cd pastis-benchmarks/
pip3 install .
cd ..
