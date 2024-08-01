//#include "help.h"
#include <google/protobuf/io/zero_copy_stream_impl.h>
#include <google/protobuf/io/coded_stream.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include "rgd.pb.h"
#include "util.h"
#include "parser.h"
#include "task.h"
#include "interface.h"
#include "gd.h"
#include "ctpl.h"


using namespace google::protobuf::io;

using namespace rgd;
extern ctpl::thread_pool* pool;
bool handle_task(int tid, std::shared_ptr<SearchTask> task);
bool handle_task_v2(int tid, std::shared_ptr<SearchTask> task);
extern std::vector<std::future<bool>> gresults;

int main() {
  init(false, true);
  int fd = open("../switch.data",O_RDONLY);
  ZeroCopyInputStream* rawInput = new google::protobuf::io::FileInputStream(fd);
  bool suc = false;
  int fid = 1;
  int finished = 0;
  std::shared_ptr<SearchTask>  task = std::make_shared<SearchTask>();
  suc = readDelimitedFrom(rawInput,task.get());
  //printTask(task.get());
  if (suc) {
    for (int i=0 ;i<100; i++) {
      printf("#%d search\n", i);
      handle_task(0,task);
    }
  }
  delete rawInput;
  fini();
}

