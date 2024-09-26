ARG parent_image
FROM $parent_image
COPY --from=whexy/bandfuzz:sbft_v1 /fuzzers /tmp/fuzzers
COPY --from=whexy/bandfuzz:sbft_v1 /bf /bf
ENV PATH="/bf/llvm/llvm-12/bin:${PATH}"
RUN echo "/bf/llvm/llvm-12/lib" >> /etc/ld.so.conf.d/bandfuzz.conf && ldconfig