FROM gcr.io/fuzzbench/base-image

# ! Breaking change: There's something wrong in Google Cloud SDK apt source, so I have to change it back to ubuntu default source.
RUN rm -rf /etc/apt
COPY --from=ubuntu:20.04 /etc/apt/ /etc/apt/
# ! Before submit anything, please change it back to Google Cloud SDK apt source.
RUN apt-get update -y && apt-get install -y libbfd-dev libunwind-dev