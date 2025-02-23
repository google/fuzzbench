FROM gcr.io/oss-fuzz-base/base-builder
RUN apt-get update && apt-get install -y python3-pip
RUN pip3 install boofuzz
COPY build.sh $SRC/
