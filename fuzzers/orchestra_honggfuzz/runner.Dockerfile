FROM gcr.io/fuzzbench/base-image

#
# Honggfuzz
#

# honggfuzz requires libfd and libunwid
RUN apt-get update -y && apt-get install -y libbfd-dev libunwind-dev

