/*
 * This is heavily based on sfcommands/sfconvert.c which was the 
 * the original target in svrwb set of apps.
 *
 * The delete_file() and buf_to_file() routines were ripped directly from the
 * autofuzz project (see fuzz_utils.cc).
 *
 */


#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <err.h>
#include <linux/limits.h>

#include "config.h"
#include <audiofile.h>

extern "C"
int
delete_file(const char *pathname)
{
	int ret = unlink(pathname);
	if (ret == -1) {
		warn("failed to delete \"%s\"", pathname);
	}
	return ret;
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
 * Below this comment is effectively a copy/paste of the sfconvert.c code
 * in which the bugs were filed on. Any changes are just to make things work
 * in the fuzzbench setting.
 * 
 */

/*
	Audio File Library

	Copyright 1998, 2011, Michael Pruett <michael@68k.org>

	This program is free software; you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation; either version 2 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License along
	with this program; if not, write to the Free Software Foundation, Inc.,
	51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
*/

extern "C" char *copyrightstring (AFfilehandle file)
{
	char	*copyright = NULL;
	int		*miscids;
	int		i, misccount;

	misccount = afGetMiscIDs(file, NULL);
	miscids = (int *) malloc(sizeof (int) * misccount);
	afGetMiscIDs(file, miscids);

	for (i=0; i<misccount; i++)
	{
		if (afGetMiscType(file, miscids[i]) != AF_MISC_COPY)
			continue;

		/*
			If this code executes, the miscellaneous chunk is a
			copyright chunk.
		*/
		int datasize = afGetMiscSize(file, miscids[i]);
		char *data = (char *) malloc(datasize);
		afReadMisc(file, miscids[i], data, datasize);
		copyright = data;
		break;
	}

	free(miscids);

	return copyright;
}

extern "C" bool printfileinfo (const char *filename)
{
	AFfilehandle file = afOpenFile(filename, "r", NULL);
	if (!file)
		return false;

	int fileFormat = afGetFileFormat(file, NULL);
	const char *formatstring =
		(const char *) afQueryPointer(AF_QUERYTYPE_FILEFMT, AF_QUERY_DESC,
			fileFormat, 0, 0);
	const char *labelstring =
		(const char *) afQueryPointer(AF_QUERYTYPE_FILEFMT, AF_QUERY_LABEL,
			fileFormat, 0, 0);

	if (!formatstring || !labelstring)
		return false;

	printf("File Name      %s\n", filename);
	printf("File Format    %s (%s)\n", formatstring, labelstring);

	int sampleFormat, sampleWidth;
	afGetSampleFormat(file, AF_DEFAULT_TRACK, &sampleFormat, &sampleWidth);

	int byteOrder = afGetByteOrder(file, AF_DEFAULT_TRACK);

	printf("Data Format    ");

	int compressionType = afGetCompression(file, AF_DEFAULT_TRACK);
	if (compressionType == AF_COMPRESSION_NONE)
	{
		switch (sampleFormat)
		{
			case AF_SAMPFMT_TWOSCOMP:
				printf("%d-bit integer (2's complement, %s)",
					sampleWidth,
					byteOrder == AF_BYTEORDER_BIGENDIAN ?
						"big endian" : "little endian");
				break;
			case AF_SAMPFMT_UNSIGNED:
				printf("%d-bit integer (unsigned, %s)",
					sampleWidth,
					byteOrder == AF_BYTEORDER_BIGENDIAN ?
						"big endian" : "little endian");
				break;
			case AF_SAMPFMT_FLOAT:
				printf("single-precision (32-bit) floating point, %s",
					byteOrder == AF_BYTEORDER_BIGENDIAN ?
						"big endian" : "little endian");
				break;
			case AF_SAMPFMT_DOUBLE:
				printf("double-precision (64-bit) floating point, %s",
					byteOrder == AF_BYTEORDER_BIGENDIAN ?
						"big endian" : "little endian");
				break;
			default:
				printf("unknown");
				break;
		}
	}
	else
	{
		const char *compressionName =
			(const char *) afQueryPointer(AF_QUERYTYPE_COMPRESSION,
				AF_QUERY_NAME, compressionType, 0, 0);

		if (!compressionName)
			printf("unknown compression");
		else
			printf("%s compression", compressionName);
	}
	printf("\n");

	printf("Audio Data     %jd bytes begins at offset %jd (%jx hex)\n",
		(intmax_t) afGetTrackBytes(file, AF_DEFAULT_TRACK),
		(intmax_t) afGetDataOffset(file, AF_DEFAULT_TRACK),
		(uintmax_t) afGetDataOffset(file, AF_DEFAULT_TRACK));

	printf("               %d channel%s, %jd frames\n",
		afGetChannels(file, AF_DEFAULT_TRACK),
		afGetChannels(file, AF_DEFAULT_TRACK) > 1 ? "s" : "",
		(intmax_t) afGetFrameCount(file, AF_DEFAULT_TRACK));

	printf("Sampling Rate  %.2f Hz\n", afGetRate(file, AF_DEFAULT_TRACK));

	printf("Duration       %.3f seconds\n",
		afGetFrameCount(file, AF_DEFAULT_TRACK) /
		afGetRate(file, AF_DEFAULT_TRACK));

	char *copyright = copyrightstring(file);
	if (copyright)
	{
		printf("Copyright      %s\n", copyright);
		free(copyright);
	}

	afCloseFile(file);

	return true;
}
/*
	Copy audio data from one file to another.  This function
	assumes that the virtual sample formats of the two files
	match.
*/
extern "C"
bool
copyaudiodata (AFfilehandle infile, AFfilehandle outfile, int trackid)
{
	int frameSize = afGetVirtualFrameSize(infile, trackid, 1);

	const int kBufferFrameCount = 65536;
	void *buffer = malloc(kBufferFrameCount * frameSize);

	AFframecount totalFrames = afGetFrameCount(infile, AF_DEFAULT_TRACK);
	AFframecount totalFramesWritten = 0;

	bool success = true;

	while (totalFramesWritten < totalFrames)
	{
		AFframecount framesToRead = totalFrames - totalFramesWritten;
		if (framesToRead > kBufferFrameCount)
			framesToRead = kBufferFrameCount;

		AFframecount framesRead = afReadFrames(infile, trackid, buffer,
			framesToRead);

		if (framesRead < framesToRead)
		{
			fprintf(stderr, "Bad read of audio track data.\n");
			success = false;
			break;
		}

		AFframecount framesWritten = afWriteFrames(outfile, trackid, buffer,
			framesRead);

		if (framesWritten < framesRead)
		{
			fprintf(stderr, "Bad write of audio track data.\n");
			success = false;
			break;
		}

		totalFramesWritten += framesWritten;
	}

	free(buffer);

	return success;
}

// Used to test that we still crash on the known_bugs
#ifdef _HAVE_MAIN
int
main(int argc, char **argv)
{
	const char *inFileName = argv[1];

#else
extern "C"
int
LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
	const char *inFileName = buf_to_file(data, size, "./input_file-XXXXXX");
#endif
	const char *outFileName = "./foo.mp3";

	int outFileFormat = AF_FILE_AIFF;
	int outSampleFormat = -1, outSampleWidth = -1, outChannelCount = -1;
	int outCompression = AF_COMPRESSION_NONE;
	double outMaxAmp = 1.0;

	AFfilehandle inFile = afOpenFile(inFileName, "r", AF_NULL_FILESETUP);
	if (!inFile) {
		printf("Could not open file '%s' for reading.\n", inFileName);
		delete_file(inFileName);
		return EXIT_FAILURE;
	}

	// Get audio format parameters from input file.
	int fileFormat = afGetFileFormat(inFile, NULL);
	int channelCount = afGetChannels(inFile, AF_DEFAULT_TRACK);
	double sampleRate = afGetRate(inFile, AF_DEFAULT_TRACK);
	int sampleFormat, sampleWidth;
	afGetSampleFormat(inFile, AF_DEFAULT_TRACK, &sampleFormat, &sampleWidth);

	// Initialize output audio format parameters.
	AFfilesetup outFileSetup = afNewFileSetup();

	if (outFileFormat == -1)
		outFileFormat = fileFormat;

	if (outSampleFormat == -1 || outSampleWidth == -1)
	{
		outSampleFormat = sampleFormat;
		outSampleWidth = sampleWidth;
	}

	if (outChannelCount == -1)
		outChannelCount = channelCount;

	afInitFileFormat(outFileSetup, outFileFormat);
	afInitCompression(outFileSetup, AF_DEFAULT_TRACK, outCompression);
	afInitSampleFormat(outFileSetup, AF_DEFAULT_TRACK, outSampleFormat,
		outSampleWidth);
	afInitChannels(outFileSetup, AF_DEFAULT_TRACK, outChannelCount);
	afInitRate(outFileSetup, AF_DEFAULT_TRACK, sampleRate);

	AFfilehandle outFile = afOpenFile(outFileName, "w", outFileSetup);
	if (!outFile)
	{
		delete_file(inFileName);
		return EXIT_FAILURE;
	}

	afFreeFileSetup(outFileSetup);

	/*
		Set the output file's virtual audio format parameters
		to match the audio format parameters of the input file.
	*/
	afSetVirtualChannels(outFile, AF_DEFAULT_TRACK, channelCount);
	afSetVirtualSampleFormat(outFile, AF_DEFAULT_TRACK, sampleFormat,
		sampleWidth);

	bool success = copyaudiodata(inFile, outFile, AF_DEFAULT_TRACK);

	afCloseFile(inFile);
	afCloseFile(outFile);

	if (!success)
	{
		unlink(outFileName);
		delete_file(inFileName);
		return EXIT_FAILURE;
	}

	printfileinfo(inFileName);
	putchar('\n');
	printfileinfo(outFileName);

	delete_file(inFileName);

	return EXIT_SUCCESS;
}

