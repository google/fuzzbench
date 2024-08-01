#pragma once

namespace pbbs {
  void* my_alloc(size_t);
  void my_free(void*);
}

#include <atomic>
#include <vector>
#include <new>
#include "utilities.h"
#include "concurrent_stack.h"
#include "utilities.h"
#include "block_allocator.h"
#include "memory_size.h"
#include "get_time.h"

namespace pbbs {

#if defined(__APPLE__) // a little behind the times
  void* aligned_alloc(size_t, size_t n) {return malloc(n);}
#endif


  // ****************************************
  //    pool_allocator
  // ****************************************

  // Allocates headerless blocks from pools of different sizes.
  // A vector of pool sizes is given to the constructor.
  // Sizes must be at least 8, and must increase.
  // For pools of small blocks (below large_threshold) each thread keeps a
  //   thread local list of elements from each pool using the
  //   block_allocator.
  // For pools of large blocks there is only one shared pool for each.
  struct pool_allocator {

  private:
    static const size_t large_align = 64;
    static const size_t large_threshold = (1 << 20);
    size_t num_buckets;
    size_t num_small;
    size_t max_small;
    size_t max_size;
    std::atomic<long> large_allocated{0};
  
    concurrent_stack<void*>* large_buckets;
    struct block_allocator *small_allocators;
    std::vector<size_t> sizes;

    void* allocate_large(size_t n) {

      size_t bucket = num_small;
      size_t alloc_size;

      if (n <= max_size) {
	while (n > sizes[bucket]) bucket++;
	maybe<void*> r = large_buckets[bucket-num_small].pop();
	if (r) return *r;
	alloc_size = sizes[bucket];
      } else alloc_size = n;

      void* a = (void*) aligned_alloc(large_align, alloc_size);
      if (a == NULL) throw std::bad_alloc();
      
      large_allocated += n;
      return a;
    }

    void deallocate_large(void* ptr, size_t n) {
      if (n > max_size) { 
	free(ptr);
	large_allocated -= n;
      } else {
	size_t bucket = num_small;
	while (n > sizes[bucket]) bucket++;
	large_buckets[bucket-num_small].push(ptr);
      }
    }

    const size_t small_alloc_block_size = (1 << 20);

  public:
    ~pool_allocator() {
      for (size_t i=0; i < num_small; i++)
	small_allocators[i].~block_allocator();
      free(small_allocators);
      clear();
      delete[] large_buckets;
    }

    pool_allocator() {}
  
    pool_allocator(std::vector<size_t> const &sizes) : sizes(sizes) {
      timer t;
      num_buckets = sizes.size();
      max_size = sizes[num_buckets-1];
      num_small = 0;
      while (sizes[num_small] < large_threshold && num_small < num_buckets)
	num_small++;
      max_small = (num_small > 0) ? sizes[num_small - 1] : 0;

      large_buckets = new concurrent_stack<void*>[num_buckets-num_small];

      small_allocators = (struct block_allocator*)
	malloc(num_buckets * sizeof(struct block_allocator));
      size_t prev_bucket_size = 0;
    
      for (size_t i = 0; i < num_small; i++) {
	size_t bucket_size = sizes[i];
	if (bucket_size < 8)
	  throw std::invalid_argument("for small_allocator, bucket sizes must be at least 8");
	if (!(bucket_size > prev_bucket_size))
	  throw std::invalid_argument("for small_allocator, bucket sizes must increase");
	prev_bucket_size = bucket_size;
	new (static_cast<void*>(std::addressof(small_allocators[i]))) 
	  block_allocator(bucket_size, 0, small_alloc_block_size - 64); 
      }
    }

    void* allocate(size_t n) {
      if (n > max_small) return allocate_large(n);
      size_t bucket = 0;
      while (n > sizes[bucket]) bucket++;
      return small_allocators[bucket].alloc();
    }

    void deallocate(void* ptr, size_t n) {
      if (n > max_small) deallocate_large(ptr, n);
      else {
	size_t bucket = 0;
	while (n > sizes[bucket]) bucket++;
	small_allocators[bucket].free(ptr);
      }
    }

    // allocate, touch, and free to make sure space for small blocks is paged in
    void reserve(size_t bytes) {
      size_t bc = bytes/small_alloc_block_size;
      std::vector<void*> h(bc);
      parallel_for(0, bc, [&] (size_t i) {
	  h[i] = allocate(small_alloc_block_size);
	}, 1);
      parallel_for(0, bc, [&] (size_t i) {
	  for (size_t j=0; j < small_alloc_block_size; j += (1 << 12))
	    ((char*) h[i])[j] = 0;
	}, 1);
      for (size_t i=0; i < bc; i++)
      	deallocate(h[i], small_alloc_block_size);
    }

    void print_stats() {
      size_t total_a = 0;
      size_t total_u = 0;
      for (size_t i = 0; i < num_small; i++) {
	size_t bucket_size = sizes[i];
	size_t allocated = small_allocators[i].num_allocated_blocks();
	size_t used = small_allocators[i].num_used_blocks();
	total_a += allocated * bucket_size;
	total_u += used * bucket_size;
	cout << "size = " << bucket_size << ", allocated = " << allocated
	     << ", used = " << used << endl;
      }
      cout << "Large allocated = " << large_allocated << endl;
      cout << "Total bytes allocated = " << total_a + large_allocated << endl;
      cout << "Total bytes used = " << total_u << endl;
    }

    void clear() {
      for (size_t i = num_small; i < num_buckets; i++) {
	maybe<void*> r = large_buckets[i-num_small].pop();
	while (r) {
	  large_allocated -= sizes[i];
	  free(*r);
	  r = large_buckets[i-num_small].pop();
	}
      }
    }
  };

  // ****************************************
  //    default_allocator (uses powers of two as pool sizes)
  // ****************************************

  // these are bucket sizes used by the default allocator.
  std::vector<size_t> default_sizes() {
    size_t log_min_size = 4;
    size_t log_max_size = pbbs::log2_up(getMemorySize()/64);

    std::vector<size_t> sizes;
    for (size_t i = log_min_size; i <= log_max_size; i++)
      sizes.push_back(1 << i);
    return sizes;
  }

  pool_allocator default_allocator(default_sizes());

  // ****************************************
  // Following Matches the c++ Allocator specification (minimally)
  // https://en.cppreference.com/w/cpp/named_req/Allocator
  // Can therefore be used for containers, e.g.:
  //    std::vector<int, pbbs::allocator<int>>
  // ****************************************

  template <typename T>
  struct allocator {
    using value_type = T;
    T* allocate(size_t n) {
      return (T*) default_allocator.allocate(n * sizeof(T));
    }
    void deallocate(T* ptr, size_t n) {
      default_allocator.deallocate((void*) ptr, n * sizeof(T));
    }

    allocator() = default;
    template <class U> constexpr allocator(const allocator<U>&) {}
  };

  template <class T, class U>
  bool operator==(const allocator<T>&, const allocator<U>&) { return true; }
  template <class T, class U>
  bool operator!=(const allocator<T>&, const allocator<U>&) { return false; }

  // ****************************************
  // Static allocator for single items of a given type, e.g.
  //   using long_allocator = type_allocator<long>;
  //   long* foo = long_allocator::alloc();
  //   *foo = (long) 23;
  //   long_allocator::free(foo);
  // Uses block allocator, and is headerless  
  // ****************************************

  template <typename T>
  class type_allocator {
  public:
    static constexpr size_t default_alloc_size = 0;
    static block_allocator allocator;
    static const bool initialized{true};
    static T* alloc() { return (T*) allocator.alloc();}
    static void free(T* ptr) {allocator.free((void*) ptr);}

    // for backward compatibility
    //static void init(size_t _alloc_size = 0, size_t _list_size=0) {};
    static void init(size_t, size_t) {};
    static void init() {};
    static void reserve(size_t n = default_alloc_size) {
      allocator.reserve(n);
    }
    static void finish() {allocator.clear();
    }
    static size_t block_size () {return allocator.block_size();}
    static size_t num_allocated_blocks() {return allocator.num_allocated_blocks();}
    static size_t num_used_blocks() {return allocator.num_used_blocks();}
    static size_t num_used_bytes() {return num_used_blocks() * block_size();}
    static void print_stats() {allocator.print_stats();}
  };

  template<typename T>
  block_allocator type_allocator<T>::allocator = block_allocator(sizeof(T));
  
  // ****************************************
  //    my_alloc and my_free (add size tags)
  // ****************************************
  //    ifdefed to either use malloc or the pbbs allocator
  // ****************************************

#ifdef USEMALLOC

#include <malloc.h>

  struct __mallopt {
    __mallopt() {
      mallopt(M_MMAP_MAX,0);
      mallopt(M_TRIM_THRESHOLD,-1);
    }
  };

  __mallopt __mallopt_var;
  
  inline void* my_alloc(size_t i) {return malloc(i);}
  inline void my_free(void* p) {free(p);}
  void allocator_clear() {}
  void allocator_reserve(size_t bytes) {}

#else

  constexpr size_t size_offset = 1; // in size_t sized words

  // needs to be at least size_offset * size_offset(size_t)
  inline size_t header_size(size_t n) { // in bytes
    return (n >= 1024) ? 64 : (n & 15) ? 8 : (n & 63) ? 16 : 64;
  }

  // allocates and tags with a header (8, 16 or 64 bytes) that contains the size
  void* my_alloc(size_t n) {
    size_t hsize = header_size(n);
    void* ptr;
    ptr = default_allocator.allocate(n + hsize);
    void* r = (void*) (((char*) ptr) + hsize);
    *(((size_t*) r)-size_offset) = n; // puts size in header
    return r;
  }

  // reads the size, offsets the header and frees
  void my_free(void *ptr) {
    size_t n = *(((size_t*) ptr)-size_offset);
    size_t hsize = header_size(n);
    if (hsize > (1ul << 48)) {
      cout << "corrupted header in my_free" << endl;
      throw std::bad_alloc(); 
    }
    default_allocator.deallocate((void*) (((char*) ptr) - hsize), n + hsize);
  }

  void allocator_clear() {
    default_allocator.clear();
  }

  void allocator_reserve(size_t bytes) {
    default_allocator.reserve(bytes);
  }
#endif

  // ****************************************
  //    common across allocators (key routines used by sequences)
  // ****************************************

  // Does not initialize the array
  template<typename E>
  E* new_array_no_init(size_t n) {
    return (E*) my_alloc(n * sizeof(E));
  }

  // Initializes in parallel
  template<typename E>
  E* new_array(size_t n) {
    E* r = new_array_no_init<E>(n);
    if (!std::is_trivially_default_constructible<E>::value) 
      parallel_for(0, n, [&] (size_t i) {
	  new ((void*) (r+i)) E;});
    return r;
  }

  inline void free_array(void* a) {
    my_free(a);
  }

  // Destructs in parallel
  template<typename E>
  void delete_array(E* A, size_t n) {
    // C++14 -- supported by gnu C++11
    if (!std::is_trivially_destructible<E>::value)
      parallel_for(0, n, [&] (size_t i) {
	  A[i].~E();});
    my_free(A);
  }
}
