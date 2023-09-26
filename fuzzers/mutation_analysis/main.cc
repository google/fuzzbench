#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <errno.h>
#include <sys/mman.h>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size);

int main(int argc, char** argv) {
    FILE *fp;
    int fd;
    size_t size;

    if (argc < 1) {
        fprintf(stderr, "Not enough arguments");
        exit(EXIT_FAILURE);
    }

    fp = fopen(argv[1], "r");
    if (fp == NULL) {
        perror("Could not open file\n.");
        exit(EXIT_FAILURE);
    }

    fseek(fp, 0L, SEEK_END);
    size = ftell(fp);


    fd = fileno(fp);
    if (size == 0) {
        printf("zero size: %zu\n", size);
        const uint8_t data[1] = {0};
        LLVMFuzzerTestOneInput(data, 0);
        return 0;
    }
    auto data = static_cast<const uint8_t*>(mmap(NULL, size, PROT_READ, MAP_PRIVATE, fd, 0));
    if (data == (uint8_t*)-1) {
        perror("Could not mmap file\n.");
        exit(EXIT_FAILURE);
    }

    /* Call function to be fuzzed, e.g.: */
    LLVMFuzzerTestOneInput(data, size);

    return 0;
}
