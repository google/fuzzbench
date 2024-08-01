// This code is part of the Problem Based Benchmark Suite (PBBS)
// Copyright (c) 2016 Guy Blelloch, Daniel Ferizovic, and the PBBS team
//
// Permission is hereby granted, free of charge, to any person obtaining a
// copy of this software and associated documentation files (the
// "Software"), to deal in the Software without restriction, including
// without limitation the rights (to use, copy, modify, merge, publish,
// distribute, sublicense, and/or sell copies of the Software, and to
// permit persons to whom the Software is furnished to do so, subject to
// the following conditions:
//
// The above copyright notice and this permission notice shall be included
// in all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
// OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
// MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
// NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
// LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
// OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
// WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

// Lock free, linearizable implementation of a concurrent stack
// supporting:
//    push
//    pop
//    size
// Works for elements of any type T
// It requires memory proportional to the largest it has been
// This can be cleared, but only when noone else is using it.
// Requires 128-bit-compare-and-swap
// Counter could overflow "in theory", but would require over 500 years even
// if updated every nanosecond (and must be updated sequentially)

#pragma once
#include <cstdio>
#include <cstdint>
#include <iostream>
#include "utilities.h"

template<typename T>
class concurrent_stack {

  struct Node {
    T value;
    Node* next;
    size_t length;
  };

  class alignas(64) prim_concurrent_stack {
    struct nodeAndCounter {
      Node* node;
      uint64_t counter;
    };

    union CAS_t {
      __uint128_t x;
      nodeAndCounter NC;
    };
    CAS_t head;

    size_t length(Node* n) {
      if (n == NULL) return 0;
      else return n->length;
    }

  public:
    prim_concurrent_stack() {
      head.NC.node = NULL;
      head.NC.counter = 0;
      std::atomic_thread_fence(std::memory_order_seq_cst);
    }

    size_t size() {
      return length(head.NC.node);}

    void push(Node* newNode){
      CAS_t oldHead, newHead;
      do {
	oldHead = head;
	newNode->next = oldHead.NC.node;
	newNode->length = length(oldHead.NC.node) + 1;
	//std::atomic_thread_fence(std::memory_order_release);
	std::atomic_thread_fence(std::memory_order_seq_cst);
	newHead.NC.node = newNode;
	newHead.NC.counter = oldHead.NC.counter + 1;
      } while (!__sync_bool_compare_and_swap_16(&head.x,oldHead.x, newHead.x));
    }
    Node* pop() {
      Node* result;
      CAS_t oldHead, newHead;
      do {
	oldHead = head;
	result = oldHead.NC.node;
	if (result == NULL) return result;
	newHead.NC.node = result->next;
	newHead.NC.counter = oldHead.NC.counter + 1;
      } while (!__sync_bool_compare_and_swap_16(&head.x,oldHead.x, newHead.x));

      return result;
    }
  };// __attribute__((aligned(16)));

  prim_concurrent_stack a;
  prim_concurrent_stack b;

 public:

  size_t size() { return a.size();}

  void push(T v) {
    Node* x = b.pop();
    if (!x) x = (Node*) malloc(sizeof(Node));
    x->value = v;
    a.push(x);
  }

  maybe<T> pop() {
    Node* x = a.pop();
    if (!x) return maybe<T>();
    T r = x->value;
    b.push(x);
    return maybe<T>(r);
  }

  // assumes no push or pop in progress
  void clear() {
    Node* x;
    while ((x = a.pop())) free(x);
    while ((x = b.pop())) free(x);
  }

  concurrent_stack() {}
  ~concurrent_stack() { clear();}
};
