/*
 * This is heavily based on sfcommands/sfconvert.c which was the 
 * the original target in svrwb set of apps.
 *
 * The delete_file and buf_to_file routines are ripped from the autofuzz
 * project (see fuzz_utils.cc)
 *
 */

#include "config.h"

#ifdef __USE_SGI_HEADERS__
#include <dmedia/audiofile.h>
#else
#include <audiofile.h>
#endif

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

//#include "printinfo.h"

bool copyaudiodata(AFfilehandle infile, AFfilehandle outfile, int trackid);

extern "C"
int
delete_file(const char *pathname)
{
	int ret = unlink(pathname);
	if (ret == -1) {
		warn("failed to delete \"%s\"", pathname);
	}
	free((void *)pathname);
	return ret;
}

extern "C"
char *
buf_to_file(const uint8_t *buf, size_t size, char *path)
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

extern "C"
int
LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
	char *inFileName = buf_to_file(data, size, "input_file");
	char *outFileName = "foo.mp3";

	int outFileFormat = AF_FILE_AIFF;
	int outSampleFormat = -1, outSampleWidth = -1, outChannelCount = -1;
	int outCompression = AF_COMPRESSION_NONE;
	double outMaxAmp = 1.0;

	// Here on is the sfconvert code with some modifications for delete_file()

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


/*
	Copy audio data from one file to another.  This function
	assumes that the virtual sample formats of the two files
	match.
*/
bool copyaudiodata (AFfilehandle infile, AFfilehandle outfile, int trackid)
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
