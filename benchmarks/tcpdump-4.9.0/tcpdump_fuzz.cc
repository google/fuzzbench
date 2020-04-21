/*
 * This reduces much of what the tcpdump.c:main and related routines do to just
 * get parsing.
 *
 * The delete_file() and buf_to_file() routines were ripped directly from the
 * autofuzz project (see fuzz_utils.cc), with minor changes.
 *
 *
 *
 */


#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <error.h>
#include <errno.h>
#include <err.h>
extern "C"
{
#include <netdissect-stdinc.h>
#include <netdissect.h>
#include <print.h>
#include <pcap.h>
}

extern "C"
int
delete_file(const char *pathname)
{
#ifdef _HAS_MAIN
	return 0;
#else
	int ret = unlink(pathname);
	if (ret == -1) {
		warn("failed to delete \"%s\"", pathname);
	}
	return ret;
#endif
}

extern "C"
char *
buf_to_file(const uint8_t *buf, size_t size, const char *path)
{
	if (path == nullptr) {
		return nullptr;
	}

	char *pathname = strdup(path);
	if (pathname == nullptr) {
		return nullptr;
	}

	int fd = mkstemp(pathname);
	if (fd == -1) {
		warn("mkstemp(\"%s\")", pathname);
		free(pathname);
		return nullptr;
	}

	size_t pos = 0;
	while (pos < size) {
		int nbytes = write(fd, &buf[pos], size - pos);
		if (nbytes <= 0) {
			if (nbytes == -1 && errno == EINTR) {
				continue;
			}
			warn("write");
			goto err;
		}
		pos += nbytes;
	}

	if (close(fd) == -1) {
		warn("close");
		goto err;
	}

	return pathname;

err:
	delete_file(pathname);
	return nullptr;
}

static void
print_packet(u_char *user, const struct pcap_pkthdr *h, const u_char *sp)
{

    pretty_print_packet((netdissect_options *)user, h, sp, 0);

}

#ifdef _HAS_MAIN
int
main(int argc, char **argv)
{
	const char *in = argv[1];

#else
extern "C"
int
LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
	const char *in = buf_to_file(data, size, "./input_file-XXXXXX");
#endif
	const char *dlt_name;
	char ebuf[PCAP_ERRBUF_SIZE];
	netdissect_options Ndo;
	char *cp;
	pcap_t *pd;
	int dlt;
	int status;
	int cnt;
	pcap_handler callback;
	u_char *pcap_userdata;
	netdissect_options *ndo = &Ndo;

	cnt = -1;

	if (nd_init(ebuf, sizeof ebuf) == -1)
		exit(1);

	memset(ndo, 0, sizeof(*ndo));
	ndo_set_function_pointers(ndo);
	ndo->ndo_snaplen = DEFAULT_SNAPLEN;

	dlt = -1;
	ndo->program_name = in;

	/* pass -n option */
	ndo->ndo_nflag++;

	pd = pcap_open_offline(in, ebuf);
	if (pd == NULL)
		exit(2);

	dlt = pcap_datalink(pd);
	dlt = pcap_datalink(pd);
   	ndo->ndo_if_printer = get_if_printer(ndo, dlt);
	callback = print_packet;
	pcap_userdata = (u_char *)ndo;
	dlt_name = pcap_datalink_val_to_name(dlt);
	if (dlt_name == NULL) {
		fprintf(stderr, "reading from file %s, link-type %u\n", in, dlt);
	} else {
   		fprintf(stderr,
			"reading from file %s, link-type %s (%s)\n",
			in, dlt_name,
			pcap_datalink_val_to_description(dlt));
	}
	status = pcap_loop(pd, 0, callback, pcap_userdata);
    pcap_close(pd);
	return 0;
}

