// Copyright 2020 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/*
 * This is heavily based on jasper(.c).
 *
 * The delete_file() and buf_to_file() routines were ripped directly from the
 * autofuzz project (see fuzz_utils.cc).
 *
 * Implemented by Andrew R. Reiter <areiter@veracode.com> (Veracode Applied
 * Research Group).
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <err.h>

#include <assert.h>
#include <time.h>

#include <jasper/jasper.h>

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
	free((void *)pathname);
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

/*
 * Much of the below is copy/paste of jasper.c with modifications to have it
 * run in the FuzzBench environment.
 * 
 */


/*
 * Copyright (c) 1999-2000 Image Power, Inc. and the University of
 *   British Columbia.
 * Copyright (c) 2001-2003 Michael David Adams.
 * All rights reserved.
 */

/* __START_OF_JASPER_LICENSE__
 * 
 * JasPer License Version 2.0
 * 
 * Copyright (c) 1999-2000 Image Power, Inc.
 * Copyright (c) 1999-2000 The University of British Columbia
 * Copyright (c) 2001-2003 Michael David Adams
 * 
 * All rights reserved.
 * 
 * Permission is hereby granted, free of charge, to any person (the
 * "User") obtaining a copy of this software and associated documentation
 * files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge,
 * publish, distribute, and/or sell copies of the Software, and to permit
 * persons to whom the Software is furnished to do so, subject to the
 * following conditions:
 * 
 * 1.  The above copyright notices and this permission notice (which
 * includes the disclaimer below) shall be included in all copies or
 * substantial portions of the Software.
 * 
 * 2.  The name of a copyright holder shall not be used to endorse or
 * promote products derived from the Software without specific prior
 * written permission.
 * 
 * THIS DISCLAIMER OF WARRANTY CONSTITUTES AN ESSENTIAL PART OF THIS
 * LICENSE.  NO USE OF THE SOFTWARE IS AUTHORIZED HEREUNDER EXCEPT UNDER
 * THIS DISCLAIMER.  THE SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS
 * "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
 * BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
 * PARTICULAR PURPOSE AND NONINFRINGEMENT OF THIRD PARTY RIGHTS.  IN NO
 * EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, OR ANY SPECIAL
 * INDIRECT OR CONSEQUENTIAL DAMAGES, OR ANY DAMAGES WHATSOEVER RESULTING
 * FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
 * NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
 * WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.  NO ASSURANCES ARE
 * PROVIDED BY THE COPYRIGHT HOLDERS THAT THE SOFTWARE DOES NOT INFRINGE
 * THE PATENT OR OTHER INTELLECTUAL PROPERTY RIGHTS OF ANY OTHER ENTITY.
 * EACH COPYRIGHT HOLDER DISCLAIMS ANY LIABILITY TO THE USER FOR CLAIMS
 * BROUGHT BY ANY OTHER ENTITY BASED ON INFRINGEMENT OF INTELLECTUAL
 * PROPERTY RIGHTS OR OTHERWISE.  AS A CONDITION TO EXERCISING THE RIGHTS
 * GRANTED HEREUNDER, EACH USER HEREBY ASSUMES SOLE RESPONSIBILITY TO SECURE
 * ANY OTHER INTELLECTUAL PROPERTY RIGHTS NEEDED, IF ANY.  THE SOFTWARE
 * IS NOT FAULT-TOLERANT AND IS NOT INTENDED FOR USE IN MISSION-CRITICAL
 * SYSTEMS, SUCH AS THOSE USED IN THE OPERATION OF NUCLEAR FACILITIES,
 * AIRCRAFT NAVIGATION OR COMMUNICATION SYSTEMS, AIR TRAFFIC CONTROL
 * SYSTEMS, DIRECT LIFE SUPPORT MACHINES, OR WEAPONS SYSTEMS, IN WHICH
 * THE FAILURE OF THE SOFTWARE OR SYSTEM COULD LEAD DIRECTLY TO DEATH,
 * PERSONAL INJURY, OR SEVERE PHYSICAL OR ENVIRONMENTAL DAMAGE ("HIGH
 * RISK ACTIVITIES").  THE COPYRIGHT HOLDERS SPECIFICALLY DISCLAIM ANY
 * EXPRESS OR IMPLIED WARRANTY OF FITNESS FOR HIGH RISK ACTIVITIES.
 * 
 * __END_OF_JASPER_LICENSE__
 */



#define OPTSMAX	4096
typedef struct {
	char *infile;	/* The input image file. */
	int infmt;	/* The input image file format. */
	char *inopts;
	char inoptsbuf[OPTSMAX + 1];
	char *outfile;	/* The output image file. */
	int outfmt;
	char *outopts;
	char outoptsbuf[OPTSMAX + 1];
	int verbose;	/* Verbose mode. */
	int debug;
	int version;
	int_fast32_t cmptno;
	int srgb;
} cmdopts_t;

char *cmdname = "";

extern
"C"
void cmdopts_destroy(cmdopts_t *cmdopts)
{
	free(cmdopts);
}


extern "C"
#ifdef _HAS_MAIN
int
main(int argc, char **argv)
{
#else
int
LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
#endif
	jas_image_t *image;
	cmdopts_t *cmdopts;
	jas_stream_t *in;
	jas_stream_t *out;
	clock_t startclk;
	clock_t endclk;
	long dectime;
	long enctime;
	int_fast16_t numcmpts;
	int i;

	if (jas_init()) {
		return 0;	
	}

    if (!(cmdopts = (cmdopts_t *)malloc(sizeof(cmdopts_t)))) {
        fprintf(stderr, "error: insufficient memory\n");
       	return 0; 
    }

#ifdef _HAS_MAIN
    cmdopts->infile = argv[1];
#else
    cmdopts->infile = buf_to_file(data, size, "./jasper-input-XXXXXX");
#endif
    cmdopts->infmt = -1;
    cmdopts->inopts = 0;
    cmdopts->inoptsbuf[0] = '\0';
    cmdopts->outfile = 0;
	if ((cmdopts->outfmt = jas_image_strtofmt("mif")) < 0) {
		fprintf(stderr, "error: invalid output format %s\n", jas_optarg);
		delete_file(cmdopts->infile);
	  return 0;	
	} 
    cmdopts->outopts = 0;
    cmdopts->outoptsbuf[0] = '\0';
    cmdopts->verbose = 0;
    cmdopts->version = 0;
    cmdopts->cmptno = -1;
    cmdopts->debug = 0;
    cmdopts->srgb = 0;

	jas_setdbglevel(cmdopts->debug);


	/* Open the input image file. */
	if (cmdopts->infile) {
		/* The input image is to be read from a file. */
		if (!(in = jas_stream_fopen(cmdopts->infile, "rb"))) {
			fprintf(stderr, "error: cannot open input image file %s\n",
			  cmdopts->infile);
			delete_file(cmdopts->infile);
			return 0;	
		}
	} else {
		/* The input image is to be read from standard input. */
		if (!(in = jas_stream_fdopen(0, "rb"))) {
			fprintf(stderr, "error: cannot open standard input\n");
		  return 0;	
		}
	}

	/* Open the output image file. */
	if (cmdopts->outfile) {
		/* The output image is to be written to a file. */
		if (!(out = jas_stream_fopen(cmdopts->outfile, "w+b"))) {
			fprintf(stderr, "error: cannot open output image file %s\n",
			  cmdopts->outfile);
			delete_file(cmdopts->infile);
			return 0;	
		}
	} else {
		/* The output image is to be written to standard output. */
		if (!(out = jas_stream_fdopen(1, "w+b"))) {
			fprintf(stderr, "error: cannot open standard output\n");
			delete_file(cmdopts->infile);
			return 0;	
		}
	}

	if (cmdopts->infmt < 0) {
		if ((cmdopts->infmt = jas_image_getfmt(in)) < 0) {
			fprintf(stderr, "error: input image has unknown format\n");
			delete_file(cmdopts->infile);
			return 0;	
		}
	}

	/* Get the input image data. */
	startclk = clock();
	if (!(image = jas_image_decode(in, cmdopts->infmt, cmdopts->inopts))) {
		fprintf(stderr, "error: cannot load image data\n");
		delete_file(cmdopts->infile);
		return 0;	
	}
	endclk = clock();
	dectime = endclk - startclk;

	/* If requested, throw away all of the components except one.
	  Why might this be desirable?  It is a hack, really.
	  None of the image formats other than the JPEG-2000 ones support
	  images with two, four, five, or more components.  This hack
	  allows such images to be decoded with the non-JPEG-2000 decoders,
	  one component at a time. */
	numcmpts = jas_image_numcmpts(image);
	if (cmdopts->cmptno >= 0 && cmdopts->cmptno < numcmpts) {
		for (i = numcmpts - 1; i >= 0; --i) {
			if (i != cmdopts->cmptno) {
				jas_image_delcmpt(image, i);
			}
		}
	}

	if (cmdopts->srgb) {
		jas_image_t *newimage;
		jas_cmprof_t *outprof;
		jas_eprintf("forcing conversion to sRGB\n");
		if (!(outprof = jas_cmprof_createfromclrspc(JAS_CLRSPC_SRGB))) {
			jas_eprintf("cannot create sRGB profile\n");
			delete_file(cmdopts->infile);
			return 0;	
		}
		if (!(newimage = jas_image_chclrspc(image, outprof, JAS_CMXFORM_INTENT_PER))) {
			jas_eprintf("cannot convert to sRGB\n");
			delete_file(cmdopts->infile);
			return 0;	
		}
		jas_image_destroy(image);
		jas_cmprof_destroy(outprof);
		image = newimage;
	}

	/* Generate the output image data. */
	startclk = clock();
	if (jas_image_encode(image, out, cmdopts->outfmt, cmdopts->outopts)) {
		fprintf(stderr, "error: cannot encode image\n");
		delete_file(cmdopts->infile);
		return 0;
	}
	jas_stream_flush(out);
	endclk = clock();
	enctime = endclk - startclk;

	if (cmdopts->verbose) {
		fprintf(stderr, "decoding time = %f\n", dectime / (double)
		  CLOCKS_PER_SEC);
		fprintf(stderr, "encoding time = %f\n", enctime / (double)
		  CLOCKS_PER_SEC);
	}

	/* If this fails, we don't care. */
	(void) jas_stream_close(in);

	/* Close the output image stream. */
	if (jas_stream_close(out)) {
		fprintf(stderr, "error: cannot close output image file\n");
		delete_file(cmdopts->infile);
		return 0;	
	}

	delete_file(cmdopts->infile);
	cmdopts_destroy(cmdopts);
	jas_image_destroy(image);
	jas_image_clearfmts();

	/* Success at last! :-) */
	return 0; 
}


