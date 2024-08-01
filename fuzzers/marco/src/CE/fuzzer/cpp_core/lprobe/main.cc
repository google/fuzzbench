#include "hash_table.h"
#include "benchmark_lprobe.h"
#include "data.h"
using namespace pbbs;
//#define DEFAULT_OP_COUNT     2000
//#define DEFAULT_THREAD_COUNT 2
//#define DEFAULT_READ_PERCENT 90
//#define DEFAULT_LOAD_FACTOR  40
//#define CAPACITY             8000016
//#define CAPACITY             800000

#define DEFAULT_OP_COUNT     2000000
#define DEFAULT_THREAD_COUNT 24
#define DEFAULT_READ_PERCENT 90
#define DEFAULT_LOAD_FACTOR  40
#define CAPACITY             8000016


int main() {

  int  op_count     = DEFAULT_OP_COUNT; 
  int  num_threads  = DEFAULT_THREAD_COUNT;
  int  read_percent = DEFAULT_READ_PERCENT;
  int  load_factor  = DEFAULT_LOAD_FACTOR;

  int    rweight  = read_percent;
  int    idweight = 100 - read_percent;
/*
	Table<hashKV> T(100000, hashKV(), 1.3);
	T.insert({1,2});
	T.insert({2,45});
	struct KV res  = T.find(2);
	std::cout << "return value is " << res.v << std::endl;
*/

  BenchmarkLockFreeHT benchmark_lockfree_ht(op_count, CAPACITY, rweight, idweight, num_threads, 0.3);
  benchmark_lockfree_ht.run();

	return 0;
}
