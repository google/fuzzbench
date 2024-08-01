#ifndef THREAD_SERVICE
#define THREAD_SERVICE

#include <random>
#include <array>
#include "data.h"


std::atomic<int> miss(0);

struct WorkerArgs 
{
  int    num_elems;
  // R/I/D weights, normalized to 100
  int    rweight;
  int    iweight;
  int    dweight; 
  void*  ht_p;

  bool   remove;
  int    tid;
  int    start;
  int*   elems;
};

template<typename T>
void* thread_service(void* threadArgs)
{
  WorkerArgs* args = static_cast<WorkerArgs*>(threadArgs);

  std::random_device                 rd;
  std::mt19937                       mt(rd());
  std::uniform_int_distribution<int> rng;

  std::array<int, 3> weights;
  weights[0] = args->rweight;
  weights[1] = args->iweight;
  weights[2] = args->dweight;

  std::default_random_engine         g;
  std::discrete_distribution<int>    drng(weights.begin(), weights.end());

  int tid       = args->tid;
  int num_elems = args->num_elems;
  T* ht_p = static_cast<T*>(args->ht_p);

  for (int i = 0; i < num_elems; i++)
  {
    // Key, Value pair
    int k = rng(mt);
    int v = rng(mt);
    // Action : 0 -> Search, 1 -> Insert, 2 -> Remove
    int a = drng(g);

    if (a == 0)
      ht_p->find(k);
    else if (a == 1)
      ht_p->insert({k, v});
    else
      ht_p->deleteVal(k);
  }
}

template<typename T>
void* thread_service_low_contention(void* threadArgs)
{
  WorkerArgs* args = static_cast<WorkerArgs*>(threadArgs);

  std::random_device                 rd;
  std::mt19937                       mt(rd());
  std::uniform_int_distribution<int> rng;

  std::array<int, 3> weights;
  weights[0] = args->rweight;
  weights[1] = args->iweight;
  weights[2] = args->dweight;

  std::default_random_engine         g;
  std::discrete_distribution<int>    drng(weights.begin(), weights.end());

  int tid       = args->tid;
  int num_elems = args->num_elems;
  T* ht_p = static_cast<T*>(args->ht_p);

  int *keys = (args->elems + args->start);

  int start = 0;
  int end = 0;
  for (int i = 0; i < num_elems; i++)
  {
    // Action : 0 -> Search, 1 -> Insert, 2 -> Remove
    int a = drng(g);

    if (start == end || a == 1) 
    {
      int k = rng(mt) % num_elems + tid * num_elems; 
      keys[end++] = k;
      ht_p->insert({k, k});
    }
    else if (a == 0)
    {
      int k = rng(mt) % (end - start) + start;
      ht_p->find(k);
    }
    else
    {
      int k = keys[start++];
      ht_p->deleteVal(k);
    }
  }
}

template<typename T>
void* thread_service_high_contention(void* threadArgs)
{
  WorkerArgs* args = static_cast<WorkerArgs*>(threadArgs);

  std::random_device                 rd;
  std::mt19937                       mt(rd());
  std::uniform_int_distribution<int> rng;

  std::array<int, 3> weights;
  weights[0] = args->rweight;
  weights[1] = args->iweight;
  weights[2] = args->dweight;

  std::default_random_engine         g;
  std::discrete_distribution<int>    drng(weights.begin(), weights.end());

  int tid       = args->tid;
  int num_elems = args->num_elems;
  T* ht_p = static_cast<T*>(args->ht_p);

  for (int i = 0; i < num_elems; i++)
  {
    ht_p->find(0);
	}
}

template<typename T>
void* thread_checkmiss(void* threadArgs)
{
  WorkerArgs* args = static_cast<WorkerArgs*>(threadArgs);
  int* elems = args->elems;
  T*   ht_p  = static_cast<T*>(args->ht_p);
  int  start     = args->start;
  int  num_elems = args->num_elems;
  int  tid       = args->tid;

  for (int i = start; i < start + num_elems; i++)
  {
#if 0 
		struct KV res = ht_p->find(elems[i]);
		if (res.k == -1) {
			++miss;
			ht_p->insert({elems[i], elems[i]});
			printf("miss! key is %d\n", elems[i]);
		}
#endif
		bool res = ht_p->insert({elems[i], elems[i]});
		if (res) {
			++miss;
			printf("miss!\n");
		}

  }

}


template<typename T>
void* thread_insert(void* threadArgs)
{
  WorkerArgs* args = static_cast<WorkerArgs*>(threadArgs);
  int* elems = args->elems;
  T*   ht_p  = static_cast<T*>(args->ht_p);
  int  start     = args->start;
  int  num_elems = args->num_elems;
  int  tid       = args->tid;

  for (int i = start; i < start + num_elems; i++)
  {
    ht_p->insert({elems[i], elems[i]});
  }
  
}

template<typename T>
void* thread_remove(void* threadArgs)
{
  WorkerArgs* args = static_cast<WorkerArgs*>(threadArgs);
  int* elems = args->elems;
  T*   ht_p  = static_cast<T*>(args->ht_p);
  int  start     = args->start;
  int  num_elems = args->num_elems;
  int  tid       = args->tid;
  bool remove    = args->remove;
  
  std::random_device                 rd;
  std::mt19937                       mt(rd());
  std::uniform_int_distribution<int> rng(0, 200000 - 1);

  for (int i = start; i < start + num_elems; i++)
  {
    if (remove)
      ht_p->deleteVal(elems[i]);
    else
      ht_p->find(elems[rng(mt)]);
  }

}

#endif
