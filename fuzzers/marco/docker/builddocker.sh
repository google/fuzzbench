#!/bin/bash
NUM=${1}
NCACHE=${2}
if [ -z "$NCACHE" ]; then
    echo "docker build --network=host -f ./Dockerfile.${NUM} -t coco_design${NUM} . "
    docker build --network=host -f ./Dockerfile.${NUM} -t coco_design${NUM} .
else
    echo "docker build --network=host --no-cache -f ./Dockerfile.${NUM} -t coco_design${NUM} . "
    docker build --network=host --no-cache -f ./Dockerfile.${NUM} -t coco_design${NUM} .
fi

# gcc init_sem.c -lpthread -o init_sem
# gcc emul_sem.c -lpthread -o emul_sem
# gcc printsem.c -lpthread -o printsem