#ifndef BENCHMARK_LOCKFREE_HT
#define BENCHMARK_LOCKFREE_HT

#include <unordered_map>
#include <iostream>
#include <random>
#include <algorithm>
#include <pthread.h>
#include <array>
#include <unordered_map>
#include "assert.h"

#include "cycle_timer.h"
#include "hash_table.h"
#include "thread_service_ptr.h"

#define NUM_ITERS   3
#define MAX_THREADS 24

#define C_NUM_ELEMS	76800*24
#include "data_ptr.h"
using namespace pbbs;



class BenchmarkLockFreeHT
{
  public:
    BenchmarkLockFreeHT(int op_count, int capacity, 
                        int rweight, int idweight,
                        int thread_count,
                        double load_factor);

    void benchmark_correctness();
    void benchmark_hp();
    void benchmark_all();
    void run();

  private:
    int    m_rweight;
    int    m_idweight;

    int    m_thread_count;
    int    m_op_count;
    int    m_capacity;
    double m_load_factor;
};

BenchmarkLockFreeHT::BenchmarkLockFreeHT(int op_count, int capacity, 
                                         int rweight, int idweight,
                                         int thread_count, double load_factor)
{
  std::cout << "*** BENCHMARKING LockFreeHT ***" << std::endl;
  m_op_count     = op_count;
  m_load_factor  = load_factor; 
  m_capacity     = capacity;
  m_thread_count = thread_count;

  m_rweight      = rweight;
  m_idweight     = idweight;
}

void BenchmarkLockFreeHT::benchmark_correctness()
{
  bool correct = true;

  //Lockfree_hash_table ht(2 * C_NUM_ELEMS, m_thread_count);
	Table<hashKV> ht(2*C_NUM_ELEMS, hashKV(), 1.3);
  std::unordered_map<int, int> map;
  map.reserve(2 * C_NUM_ELEMS);
  
  std::random_device                 rd;
  std::mt19937                       mt(rd());
  std::uniform_int_distribution<int> rng;

  int elems[C_NUM_ELEMS];
  for (int i = 0; i < C_NUM_ELEMS; i++)
  {
    //int k = rng(mt);
		int k = 100;
    elems[i] = k;
    map[k] = k;
  }
	//adding err
	//elems[5*C_NUM_ELEMS/24 + 34]  = elems[6*C_NUM_ELEMS/24 + 49];
	//elems[22*C_NUM_ELEMS/24 + 199]  = elems[9*C_NUM_ELEMS/24 + 347];
	//elems[21*C_NUM_ELEMS/24 + 199]  = elems[9*C_NUM_ELEMS/24 + 347];
	//elems[19*C_NUM_ELEMS/24 + 199]  = elems[9*C_NUM_ELEMS/24 + 347];
	for (int i=0;i<23;i++)
		for (int j=0;j<20;j++)
		elems[i*C_NUM_ELEMS/24 + 34+j]  = 101+i*20+j;
  
  pthread_t  workers[MAX_THREADS];
  WorkerArgs args[MAX_THREADS];

  for (int i = 0; i < 24; i++)
  {
    args[i].num_elems = C_NUM_ELEMS / 24;
    args[i].ht_p      = (void*)&ht;
    args[i].elems     = elems;
    args[i].start     = i * (C_NUM_ELEMS / 24);
    args[i].tid       = i;

    pthread_create(&workers[i], NULL, thread_checkmiss<Table<hashKV>>, (void*)&args[i]);
  }

  for (int i = 0; i < 24; i++)
  {
    pthread_join(workers[i], NULL);
  }


	std::cout << "hash table count is " << ht.count() << std::endl;
	std::cout << "miss is " << miss << std::endl;
	assert(miss==461);
  int count = 0;
  for (std::pair<int, int> e : map)
  {
    //std::pair<int, bool> r = ht.search(e.first, 0);
		struct KV *res  = ht.find(e.first);
		std::pair<int,bool> r;
		if (res==nullptr || res->k == -1)
			r = {-1,false};
		else
			r = {res->v,true};
    if (!r.second || e.second != r.first)
    {

      std::cout << "\t" << "Expected value, Received value, Received result = " << e.second << " " << r.second << " "<< r.first << std::endl;
      correct = false;
      count++;
    }
  }

  std::cout << "\t" << count << "/" << C_NUM_ELEMS << " errors" << std::endl;

  if (correct)
    std::cout << "\t" << "Correctness test passed" << std::endl;
  else
    std::cout << "\t" << "Correctness test failed" << std::endl;

}

void BenchmarkLockFreeHT::benchmark_hp()
{
  //Lockfree_hash_table ht(400000, m_thread_count);
	Table<hashKV> ht(400000, hashKV(), 1.3);

  std::random_device                 rd;
  std::mt19937                       mt(rd());
  std::uniform_int_distribution<int> rng;

  std::array<int, 3> weights;
  weights[0] = m_rweight;
  weights[1] = m_idweight;
  weights[2] = m_idweight;

  std::default_random_engine         g;
  std::discrete_distribution<int>    drng(weights.begin(), weights.end());

  int insert[200000];
  for (int i = 0; i < 200000; i++)
  {
    int k = rng(mt);
    int v = rng(mt);
    insert[i] = k;
    //ht.insert(k, v, 0);
		ht.insert(new struct KV(k,v));
  }
  
  pthread_t  workers[MAX_THREADS];
  WorkerArgs args[MAX_THREADS];

  int num_elems = 200000 / m_thread_count;
  for (int i = 0; i < m_thread_count; i++)
  {
    args[i].num_elems = num_elems;
    args[i].ht_p      = (void*)&ht;
    args[i].elems     = insert;
    args[i].start     = i * num_elems;
    args[i].tid       = i;
    args[i].remove    = i < (m_thread_count / 4);

    pthread_create(&workers[i], NULL, thread_remove<Table<hashKV>>, (void*)&args[i]);
  }
  
  for (int i = 0; i < m_thread_count; i++)
  {
    pthread_join(workers[i], NULL);
  }
   
  std::cout << "\t" << "Hazard Pointer test passed" << std::endl;

}

void BenchmarkLockFreeHT::benchmark_all()
{
   // Lockfree_hash_table ht(m_capacity, m_thread_count);
		Table<hashKV> ht(m_capacity, hashKV(), 1.3);

    std::random_device                 rd;
    std::mt19937                       mt(rd());
    std::uniform_int_distribution<int> rng;

    std::array<int, 3> weights;
    weights[0] = m_rweight;
    weights[1] = m_idweight;
    weights[2] = m_idweight;

    std::default_random_engine         g;
    std::discrete_distribution<int>    drng(weights.begin(), weights.end());

    // Warm-up table to load factor
    int num_warmup = static_cast<int>(static_cast<double>(m_capacity) * m_load_factor);
    for (int i = 0; i < num_warmup; i++)
    {
      int k = rng(mt); 
      int v = rng(mt);

      //ht.insert(k, v, 0);
      ht.insert(new struct KV(k,v));
    }

    // Run benchmark
    std::vector<double> results;
    for (int iter = 0; iter < NUM_ITERS; iter++)
    {
      int num_elems = m_op_count / m_thread_count;
      pthread_t  workers[MAX_THREADS];
      WorkerArgs args[MAX_THREADS];

      double start = CycleTimer::currentSeconds();
      for (int i = 0; i < m_thread_count; i++)
      {
        args[i].num_elems = num_elems;
        args[i].rweight   = m_rweight;
        args[i].iweight   = m_idweight / 2;
        args[i].dweight   = m_idweight / 2;
        args[i].ht_p      = (void*)&ht;
        args[i].tid       = i;
        pthread_create(&workers[i], NULL, thread_service<Table<hashKV>>, (void*)&args[i]);
      }

      for (int i = 0; i < m_thread_count; i++)
      {
        pthread_join(workers[i], NULL);
      }
      double time  = CycleTimer::currentSeconds() - start;
      results.push_back(time);
    }

    // Publish Results
    double best_time = *std::min_element(results.begin(), results.end());
    double avg_time  = std::accumulate(results.begin(), results.end(), 0.0) / static_cast<double>(results.size());
    std::cout << "\t" << "Max Throughput: " << m_op_count / best_time / 1000.0 << " ops/ms" << std::endl;
    std::cout << "\t" << "Avg Throughput: " << m_op_count / avg_time  / 1000.0 << " ops/ms" << std::endl;

    results.clear();

    int* keys = new int[m_op_count];

    for (int iter = 0; iter < NUM_ITERS; iter++)
    {
      int num_elems = m_op_count / m_thread_count;
      pthread_t  workers[MAX_THREADS];
      WorkerArgs args[MAX_THREADS];

      double start = CycleTimer::currentSeconds();
      for (int i = 0; i < m_thread_count; i++)
      {
        args[i].num_elems = num_elems;
        args[i].rweight   = m_rweight;
        args[i].iweight   = m_idweight / 2;
        args[i].dweight   = m_idweight / 2;
        args[i].ht_p      = (void*)&ht;
        args[i].tid       = i;
        args[i].elems     = keys;
        args[i].start     = i * num_elems;
        pthread_create(&workers[i], NULL, thread_service_low_contention<Table<hashKV>>, (void*)&args[i]);
      }

      for (int i = 0; i < m_thread_count; i++)
      {
        pthread_join(workers[i], NULL);
      }
      double time  = CycleTimer::currentSeconds() - start;
      results.push_back(time);
    }

    // Publish Results
    best_time = *std::min_element(results.begin(), results.end());
    avg_time  = std::accumulate(results.begin(), results.end(), 0.0) / static_cast<double>(results.size());
    std::cout << "\t" << "Max Throughput (Low): " << m_op_count / best_time / 1000.0 << " ops/ms" << std::endl;
    std::cout << "\t" << "Avg Throughput (Low): " << m_op_count / avg_time  / 1000.0 << " ops/ms" << std::endl;

    results.clear();

    for (int iter = 0; iter < NUM_ITERS; iter++)
    {
      int num_elems = m_op_count / m_thread_count;
      pthread_t  workers[MAX_THREADS];
      WorkerArgs args[MAX_THREADS];

      double start = CycleTimer::currentSeconds();
      for (int i = 0; i < m_thread_count; i++)
      {
        args[i].num_elems = num_elems;
        args[i].rweight   = m_rweight;
        args[i].iweight   = m_idweight / 2;
        args[i].dweight   = m_idweight / 2;
        args[i].ht_p      = (void*)&ht;
        args[i].tid       = i;
        //ht.insert(0, 0, 0);
        ht.insert(new struct KV(0,0));
        pthread_create(&workers[i], NULL, thread_service_high_contention<Table<hashKV>>, (void*)&args[i]);
      }

      for (int i = 0; i < m_thread_count; i++)
      {
        pthread_join(workers[i], NULL);
      }
      double time  = CycleTimer::currentSeconds() - start;
      results.push_back(time);
    }

    // Publish Results
    best_time = *std::min_element(results.begin(), results.end());
    avg_time  = std::accumulate(results.begin(), results.end(), 0.0) / static_cast<double>(results.size());
    std::cout << "\t" << "Max Throughput (High): " << m_op_count / best_time / 1000.0 << " ops/ms" << std::endl;
    std::cout << "\t" << "Avg Throughput (High): " << m_op_count / avg_time  / 1000.0 << " ops/ms" << std::endl;


}

void BenchmarkLockFreeHT::run()
{
  benchmark_correctness();
//  benchmark_hp();
//  benchmark_all();
}

#endif
