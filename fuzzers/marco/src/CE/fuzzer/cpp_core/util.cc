#include <sys/time.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <cstdint>
#include <string>
#include <string.h>
#include <unordered_map>
#include <linux/limits.h>

const uint64_t kUsToS = 1000000;
uint64_t getTimeStamp() {
	struct timeval tv;
	gettimeofday(&tv, NULL);
	return tv.tv_sec * kUsToS + tv.tv_usec;
}

uint32_t load_input(std::string input_file, unsigned char* input) {
  int fdin;
  struct stat statbuf;
  void *src;
  if ((fdin = open (input_file.c_str(), O_RDONLY)) < 0)
  {
    fprintf(stderr, "[load_input]cannot open input file (%s) %s!\n", input_file.c_str(), strerror(errno));
    return 0;
  }

  if (fstat (fdin,&statbuf) < 0)
  {
    //assert (false && "fstat error");
    fprintf(stderr, "cannot stat file %s!\n", strerror(errno));
    close(fdin);
    return 0;
  }

  if ((src = mmap (0, statbuf.st_size, PROT_READ, MAP_SHARED, fdin, 0))
      == (caddr_t) -1) {
    fprintf(stderr, "cannot map file %s!\n", strerror(errno));
    close(fdin);
    return 0;
  }

	memcpy (input, src, statbuf.st_size);
	munmap(src,statbuf.st_size);
  close(fdin);
  return statbuf.st_size;
}

void generate_input(std::unordered_map<uint32_t,uint8_t> &sol, std::string taint_file, std::string outputDir, uint32_t fid) {
	
	char path[PATH_MAX];
	// std::string old_string = std::to_string(fid);
	// std::string output_file = outputDir + "/" + "id-" + std::string(8-old_string.size(),'0') + old_string;
	std::string old_string = std::to_string(fid % 1000000);
	// std::string output_dir1 = outputDir + std::to_string(fid / 1000000); 
	// std::string output_dir = outputDir + std::to_string(fid / 1000000) + "/queue"; 
	// std::string output_file = outputDir + std::to_string(fid / 1000000) + "/queue/id:" + std::string(6-old_string.size(),'0') + old_string;
	std::string output_dir1 = outputDir; 
	std::string output_dir = outputDir  + "/queue"; 
	std::string output_file = outputDir + "/queue/id:" + std::string(6-old_string.size(),'0') + old_string;
	std::string input_file =  taint_file;
	struct stat statbuf;
	void *src, *dst;
	int fdout, fdin;
	int mode = 0x777;

	if ((mkdir(output_dir1.c_str(), 0777) == -1) && (errno != EEXIST)) {
		fprintf(stderr, "[generate_input]cannot create output dir(%s) %s!\n", output_dir1.c_str(), strerror(errno));
		goto fail;
	}

	if ((mkdir(output_dir.c_str(), 0777) == -1) && (errno != EEXIST)) {
		fprintf(stderr, "[generate_input]cannot create output dir(%s) %s!\n", output_dir.c_str(), strerror(errno));
		goto fail;
	}

	if ((fdin = open (input_file.c_str(), O_RDONLY)) < 0)
	{
		fprintf(stderr, "[generate_input]cannot open input file(%s) %s!\n", input_file.c_str(), strerror(errno));
		goto fail;
	}

	if (fstat (fdin,&statbuf) < 0)
	{
		fprintf(stderr, "cannot stat file %s!\n", strerror(errno));
		goto fail1;
	}	

	if ((src = mmap (0, statbuf.st_size, PROT_READ, MAP_SHARED, fdin, 0))
			== (caddr_t) -1) {
		fprintf(stderr, "cannot map file %s!\n", strerror(errno));
		goto fail1;
	}


	if ((fdout = open (output_file.c_str(), O_RDWR | O_CREAT | O_TRUNC, mode)) < 0)//edited here
	{
		fprintf(stderr, "cannot open outputfile(%s) %s!\n", output_file.c_str(), strerror(errno));
		goto fail2;
	}

	dst = malloc(statbuf.st_size);
  

	/* this copies the input file to the output file */
	memcpy (dst, src, statbuf.st_size);
	//memset(dst,0,sizeof(dst));
  for (auto it=sol.begin();it!=sol.end();it++) {
		((uint8_t*)dst)[it->first] = it->second;
		//printf("generate_input index is %u and value is %x and original value is %x\n", it->first,(uint32_t)it->second, ((uint8_t*)src)[it->first]);
	}
	
	if (write(fdout, dst, statbuf.st_size) < 0) {
		fprintf(stderr, "write output error: %s!\n", strerror(errno));
		goto fail3;
	}
	//printf("[generate_input]: %s\n", output_file.c_str());

fail3:
	close(fdout);
	free(dst);
fail2:
	munmap(src,statbuf.st_size);
fail1:
	close(fdin);
fail:
	return;
}




