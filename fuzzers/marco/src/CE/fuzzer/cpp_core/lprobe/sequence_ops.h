// This code is part of the Problem Based Benchmark Suite (PBBS)
// Copyright (c) 2011-2019 Guy Blelloch and the PBBS team
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

#pragma once

#include <iostream>
#include "utilities.h"
#include "seq.h"
#include "monoid.h"

namespace pbbs {

  template <class UnaryFunc>
  auto tabulate(size_t n, UnaryFunc f) -> sequence<decltype(f(0))> {
    return sequence<decltype(f(0))>(n, [&] (size_t i) {return f(i);});}

  template <SEQ Seq, class UnaryFunc>
  auto map(Seq const &A, UnaryFunc f) -> sequence<decltype(f(A[0]))> {
    return tabulate(A.size(), [&] (size_t i) {return f(A[i]);});}

  // delayed version of map
  // requires C++14 or greater, both since return type is not defined (a lambda)
  //   and for support of initialization of the closure lambda capture
  template <SEQ Seq, class UnaryFunc>
  auto dmap(Seq &&A, UnaryFunc&& f) {
    size_t n = A.size();
    return dseq(n, [f=std::forward<UnaryFunc>(f),
		    A=std::forward<Seq>(A)] (size_t i) {
		  return f(A[i]);});}

  template <class T>
  auto singleton(T const &v) -> sequence<T> {
    return sequence<T>(1, v); }

  template <SEQ Seq, RANGE Range>
  auto copy(Seq const &A, Range R, flags) -> void {
    parallel_for(0, A.size(), [&] (size_t i) {R[i] = A[i];});}

  constexpr const size_t _log_block_size = 10;
  constexpr const size_t _block_size = (1 << _log_block_size);

  inline size_t num_blocks(size_t n, size_t block_size) {
    if (n == 0) return 0;
    else return (1 + ((n)-1)/(block_size));}

  template <class F>
  void sliced_for(size_t n, size_t block_size, const F& f, flags fl = no_flag) {
    size_t l = num_blocks(n, block_size);
    auto body = [&] (size_t i) {
      size_t s = i * block_size;
      size_t e = std::min(s + block_size, n);
      f(i, s, e);
    };
    parallel_for(0, l, body, 1, 0 != (fl & fl_conservative));
  }

  template <SEQ Seq, class Monoid>
  auto reduce_serial(Seq const &A, Monoid m) -> typename Seq::value_type {
    using T = typename Seq::value_type;
    T r = A[0];
    for (size_t j=1; j < A.size(); j++) r = m.f(r,A[j]);
    return r;
  }

  template <SEQ Seq, class Monoid>
  auto reduce(Seq const &A, Monoid m, flags fl = no_flag)
    -> typename Seq::value_type
  {
    using T = typename Seq::value_type;
    size_t n = A.size();
    size_t block_size = std::max(_block_size, 4 * (size_t) ceil(sqrt(n)));
    size_t l = num_blocks(n, block_size);
    if (l == 0) return m.identity;
    if (l == 1 || (fl & fl_sequential)) {
      return reduce_serial(A, m); }
    sequence<T> Sums(l);
    sliced_for (n, block_size,
		[&] (size_t i, size_t s, size_t e)
		{ Sums[i] = reduce_serial(A.slice(s,e), m);});
    T r = reduce(Sums, m);
    return r;
  }

  const flags fl_scan_inclusive = (1 << 4);

  template <SEQ In_Seq, RANGE Out_Seq, class Monoid>
  auto scan_serial(In_Seq const &In, Out_Seq Out,
		   Monoid const &m, typename In_Seq::value_type offset,
		   flags fl = no_flag)  -> typename In_Seq::value_type
  {
    using T = typename In_Seq::value_type;
    T r = offset;
    size_t n = In.size();
    bool inclusive = fl & fl_scan_inclusive;
    if (inclusive) {
      for (size_t i = 0; i < n; i++) {
	r = m.f(r,In[i]);
	Out[i] = r;
      }
    } else {
      for (size_t i = 0; i < n; i++) {
	T t = In[i];
	Out[i] = r;
	r = m.f(r,t);
      }
    }
    return r;
  }

  template <SEQ In_Seq, RANGE Out_Range, class Monoid>
  auto scan_(In_Seq const &In, Out_Range Out, Monoid const &m,
	     flags fl = no_flag) -> typename In_Seq::value_type
  {
    using T = typename In_Seq::value_type;
    size_t n = In.size();
    size_t l = num_blocks(n,_block_size);
    if (l <= 2 || fl & fl_sequential)
      return scan_serial(In, Out, m, m.identity, fl);
    sequence<T> Sums(l);
    sliced_for (n, _block_size,
		[&] (size_t i, size_t s, size_t e)
		{ Sums[i] = reduce_serial(In.slice(s,e), m);});
    T total = scan_serial(Sums, Sums.slice(), m, m.identity, 0);
    sliced_for (n, _block_size,
		[&] (size_t i, size_t s, size_t e)
		{ auto O = Out.slice(s,e);
		  scan_serial(In.slice(s,e), O, m, Sums[i], fl);});
    return total;
  }

  template <RANGE Range, class Monoid>
  auto scan_inplace(Range In, Monoid m, flags fl = no_flag)
    -> typename Range::value_type
  { return scan_(In, In, m, fl); }

  template <SEQ In_Seq, class Monoid>
  auto scan(In_Seq const &In, Monoid m, flags fl = no_flag)
    ->  std::pair<sequence<typename In_Seq::value_type>, typename In_Seq::value_type>
  {
    using T = typename In_Seq::value_type;
    sequence<T> Out(In.size());
    return std::make_pair(std::move(Out), scan_(In, Out.slice(), m, fl));
  }

  // do in place if rvalue reference to a sequence<T>
  template <class T, class Monoid>
  auto scan(sequence<T> &&In, Monoid m, flags fl = no_flag)
    ->  std::pair<sequence<T>, T> {
    sequence<T> Out = std::move(In);
    T total = scan_(Out, Out.slice(), m, fl);
    return std::make_pair(std::move(Out), total);
  }

  template <SEQ Seq>
  size_t sum_bools_serial(Seq const &I) {
    size_t r = 0;
    for (size_t j=0; j < I.size(); j++) r += I[j];
    return r;
  }

  template <SEQ In_Seq, class Bool_Seq>
  auto pack_serial(In_Seq const &In, Bool_Seq const &Fl)
      -> sequence<typename In_Seq::value_type> {
    using T = typename In_Seq::value_type;
    size_t n = In.size();
    size_t m = sum_bools_serial(Fl);
    sequence<T> Out = sequence<T>::no_init(m);
    size_t k = 0;
    for (size_t i = 0; i < n; i++)
      if (Fl[i]) assign_uninitialized(Out[k++], In[i]);
    return Out;
  }

  template <class Slice, class Slice2, RANGE Out_Seq>
  size_t pack_serial_at(Slice In, Slice2 Fl, Out_Seq Out) {
    size_t k = 0;
    for (size_t i=0; i < In.size(); i++)
      if (Fl[i]) assign_uninitialized(Out[k++], In[i]);
    return k;
  }

  template <SEQ In_Seq, SEQ Bool_Seq>
  auto pack(In_Seq const &In, Bool_Seq const &Fl, flags fl = no_flag)
      -> sequence<typename In_Seq::value_type> {
    using T = typename In_Seq::value_type;
    size_t n = In.size();
    size_t l = num_blocks(n, _block_size);
    if (l == 1 || fl & fl_sequential)
      return pack_serial(In, Fl);
    sequence<size_t> Sums(l);
    sliced_for(n, _block_size, [&] (size_t i, size_t s, size_t e) {
      Sums[i] = sum_bools_serial(Fl.slice(s, e));
    });
    size_t m = scan_inplace(Sums.slice(), addm<size_t>());
    sequence<T> Out = sequence<T>::no_init(m);
    sliced_for(n, _block_size, [&](size_t i, size_t s, size_t e) {
	pack_serial_at(In.slice(s, e),  Fl.slice(s, e),
		       Out.slice(Sums[i], (i == l-1) ? m : Sums[i+1]));
    });
    return Out;
  }

  // Pack the output to the output range.
  template <SEQ In_Seq, SEQ Bool_Seq, RANGE Out_Seq>
  size_t pack_out(In_Seq const &In, Bool_Seq const &Fl, Out_Seq Out,
		  flags fl = no_flag)
  {
    size_t n = In.size();
    size_t l = num_blocks(n, _block_size);
    if (l <= 1 || fl & fl_sequential) {
      return pack_serial_at(In, Fl.slice(0, In.size()), Out);
    }
    sequence<size_t> Sums(l);
    sliced_for(n, _block_size, [&] (size_t i, size_t s, size_t e) {
      Sums[i] = sum_bools_serial(Fl.slice(s, e));
    });
    size_t m = scan_inplace(Sums.slice(), addm<size_t>());
    sliced_for(n, _block_size, [&](size_t i, size_t s, size_t e) {
      pack_serial_at(In.slice(s, e),  Fl.slice(s, e),
                     Out.slice(Sums[i], (i == l-1) ? m : Sums[i+1]));
    });
    return m;
  }

  template <SEQ In_Seq, class F>
  auto filter(In_Seq const &In, F f)
    -> sequence<typename In_Seq::value_type>
  {
    using T = typename In_Seq::value_type;
    size_t n = In.size();
    size_t l = num_blocks(n,_block_size);
    sequence<size_t> Sums(l);
    sequence<bool> Fl(n);
    sliced_for (n, _block_size,
		[&] (size_t i, size_t s, size_t e)
		{ size_t r = 0;
		  for (size_t j=s; j < e; j++)
		    r += (Fl[j] = f(In[j]));
		  Sums[i] = r;});
    size_t m = scan_inplace(Sums.slice(), addm<size_t>());
    sequence<T> Out = sequence<T>::no_init(m);
    sliced_for (n, _block_size,
		[&] (size_t i, size_t s, size_t e)
		{ pack_serial_at(In.slice(s,e),
				 Fl.slice(s,e),
				 Out.slice(Sums[i], (i == l-1) ? m : Sums[i+1]));});
    return Out;
  }

  template <SEQ In_Seq, class F>
  auto filter(In_Seq const &In, F f, flags)
  { return filter(In, f);}
  
  // Filter and write the output to the output range.
  template <SEQ In_Seq, RANGE Out_Seq, class F>
  size_t filter_out(In_Seq const &In, Out_Seq Out, F f) {
    size_t n = In.size();
    size_t l = pbbs::num_blocks(n,_block_size);
    pbbs::sequence<size_t> Sums(l);
    pbbs::sequence<bool> Fl(n);
    pbbs::sliced_for (n, pbbs::_block_size,
		[&] (size_t i, size_t s, size_t e)
		{ size_t r = 0;
		  for (size_t j=s; j < e; j++)
		    r += (Fl[j] = f(In[j]));
		  Sums[i] = r;});
    size_t m = scan_inplace(Sums.slice(), addm<size_t>());
    pbbs::sliced_for (n, _block_size,
		[&] (size_t i, size_t s, size_t e)
		{ pack_serial_at(In.slice(s,e), Fl.slice(s,e),
                  Out.slice(Sums[i], (i == l-1) ? m : Sums[i+1]));});
    return m;
  }

  template <SEQ In_Seq, RANGE Out_Seq, class F>
  size_t filter_out(In_Seq const &In, Out_Seq Out, F f, flags) {
    return filter_out(In, Out, f);}

  template <class Idx_Type, SEQ Bool_Seq>
  sequence<Idx_Type> pack_index(Bool_Seq const &Fl, flags fl = no_flag) {
    auto identity = [] (size_t i) {return (Idx_Type) i;};
    return pack(delayed_seq<Idx_Type>(Fl.size(),identity), Fl, fl);
  }

  template <SEQ In_Seq, SEQ Char_Seq>
  std::pair<size_t,size_t> split_three(In_Seq const &In,
				       range<typename In_Seq::value_type*> Out,
				       Char_Seq const &Fl,
				       flags fl = no_flag) {
    size_t n = In.size();
    if (slice_eq(In.slice(), Out)) 
      throw std::invalid_argument("In and Out cannot be the same in split_three");
    size_t l = num_blocks(n,_block_size);
    sequence<size_t> Sums0(l);
    sequence<size_t> Sums1(l);
    sliced_for (n, _block_size,
		[&] (size_t i, size_t s, size_t e) {
		  size_t c0 = 0; size_t c1 = 0;
		  for (size_t j=s; j < e; j++) {
		    if (Fl[j] == 0) c0++;
		    else if (Fl[j] == 1) c1++;
		  }
		  Sums0[i] = c0; Sums1[i] = c1;
		}, fl);
    size_t m0 = scan_inplace(Sums0.slice(), addm<size_t>());
    size_t m1 = scan_inplace(Sums1.slice(), addm<size_t>());
    sliced_for (n, _block_size,
		[&] (size_t i, size_t s, size_t e)
		{
		  size_t c0 = Sums0[i];
		  size_t c1 = m0 + Sums1[i];
		  size_t c2 = m0 + m1 + (s - Sums0[i] - Sums1[i]);
		  for (size_t j=s; j < e; j++) {
		    if (Fl[j] == 0) Out[c0++] = In[j];
		    else if (Fl[j] == 1) Out[c1++] = In[j];
		    else Out[c2++] = In[j];
		  }
		}, fl);
    return std::make_pair(m0,m1);
  }

  template <SEQ In_Seq, SEQ Bool_Seq>
  auto split_two(In_Seq const &In,
		 Bool_Seq const &Fl,
		 flags fl = no_flag)
    -> std::pair<sequence<typename In_Seq::value_type>, size_t> {
    using T = typename In_Seq::value_type;
    size_t n = In.size();
    size_t l = num_blocks(n,_block_size);
    sequence<size_t> Sums(l);
    sliced_for (n, _block_size,
		[&] (size_t i, size_t s, size_t e) {
		  size_t c = 0;
		  for (size_t j=s; j < e; j++)
		    c += (Fl[j] == false);
		  Sums[i] = c;
		}, fl);
    size_t m = scan_inplace(Sums.slice(), addm<size_t>());
    sequence<T> Out = sequence<T>::no_init(n);
    sliced_for (n, _block_size,
		[&] (size_t i, size_t s, size_t e) {
		  size_t c0 = Sums[i];
		  size_t c1 = s + (m - c0);
		  for (size_t j=s; j < e; j++) {
		    if (Fl[j] == false) assign_uninitialized(Out[c0++],In[j]);
		    else assign_uninitialized(Out[c1++],In[j]);
		  }
		}, fl);
    return std::make_pair(std::move(Out), m);
  }
}

