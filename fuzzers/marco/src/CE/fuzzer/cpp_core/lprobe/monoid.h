#pragma once
#include <limits>
#include <tuple>
#include <array>

// Definition of various monoids
// each consists of:
//   T : type of the values
//   static T identity() : returns identity for the monoid
//   static T add(T, T) : adds two elements, must be associative

namespace pbbs {

  template <class F, class TT>
  struct monoid {
    using T = TT;
    F f;
    TT identity;
    monoid(F f, TT id) : f(f), identity(id) {}
  };

  template <class F, class T>
  monoid<F,T> make_monoid (F f, T id) {
    return monoid<F,T>(f, id);
  }

  template <class M1, class M2>
  auto pair_monoid (M1 m1, M2 m2) {
    using P = std::pair<typename M1::T, typename M2::T>;
    auto f = [&] (P a, P b) {
      return P(m1.f(a.first, b.first), m2.f(a.second, b.second));};
    return make_monoid(f, P(m1.identity, m2.identity));
  }

  template <class M, size_t n>
  auto array_monoid (M m) {
    using Ar = std::array<typename M::T, n>;
    auto f = [&] (Ar a, Ar b) {
      Ar r;
      for (size_t i=0; i < n; i++)
	r[i] = m.f(a[i], b[i]);
      return r;
    };
    Ar id;
    for (size_t i=0; i < n; i++) id[i] = m.identity;
    return make_monoid(f, id);
  }
  
  template <class TT>
  struct addm {
    using T = TT;
    addm() : identity(0) {}
    T identity;
    static T f(T a, T b) {return a + b;}
  };

  template <class T>
  T lowest() {return std::numeric_limits<T>::lowest();}

  template <class T>
  T highest() {return std::numeric_limits<T>::max();}

  template <class TT>
  struct maxm{
    using T = TT;
    maxm() : identity(lowest<T>()) {}
    T identity;
    static T f(T a, T b) {return std::max(a,b);}
  };

  template <class T1, class T2>
  struct maxm<std::pair<T1,T2>> {
    using T = std::pair<T1,T2>;
    maxm() : identity(std::make_pair(lowest<T1>(), lowest<T2>())) {}
    T identity;
    static T f(T a, T b) {return std::max(a,b);}
  };

  template <class TT>
  struct minm {
    using T = TT;
    minm() : identity(highest<T>()) {}
    T identity;
    static T f(T a, T b) {return std::min(a,b);}
  };

  template <class T1, class T2>
  struct minm<std::pair<T1,T2>> {
    using T = std::pair<T1,T2>;
    minm() : identity(std::make_pair(highest<T1>(), highest<T2>())) {}
    T identity;
    static T f(T a, T b) {return std::max(a,b);}
  };

  template <class TT>
  struct xorm {
    using T = TT;
    xorm() : identity(0) {}
    T identity;
    static T f(T a, T b) {return a ^ b;}
  };

  template <class TT>
  struct minmaxm {
    using T = std::pair<TT,TT>;
    minmaxm() : identity(T(highest<T>(), lowest<T>())) {}
    T identity;
    static T f(T a, T b) {return T(std::min(a.first,b.first),
				   std::max(a.second,b.second));}
  };

  template <class TT>
  struct Add {
    using T = TT;
    static T identity() {return (T) 0;}
    static T add(T a, T b) {return a + b;}
  };

  template <class TT>
  struct Max {
    using T = TT;
    static T identity() {
      return (T) std::numeric_limits<T>::min();}
    static T add(T a, T b) {return std::max(a,b);}
  };

  template <class TT>
  struct Min {
    using T = TT;
    static T identity() {
      return (T) std::numeric_limits<T>::max();}
    static T add(T a, T b) {return std::min(a,b);}
  };

  template <class A1, class A2>
  struct Add_Pair {
    using T = std::pair<typename A1::T, typename A2::T>;
    static T identity() {return T(A1::identity(), A2::identity());}
    static T add(T a, T b) {
      return T(A1::add(a.first,b.first), A2::add(a.second,b.second));}
  };

  template <class AT>
  struct Add_Array {
    using S = std::tuple_size<AT>;
    using T = std::array<typename AT::value_type, S::value>;
    static T identity() {
      T r;
      for (size_t i=0; i < S::value; i++)
	r[i] = 0;
      return r;
    }
    static T add(T a, T b) {
      T r;
      for (size_t i=0; i < S::value; i++)
	r[i] = a[i] + b[i];
      return r;
    }
  };

  template <class AT>
  struct Add_Nested_Array {
    using T = AT;
    using S = std::tuple_size<T>;
    using SS = std::tuple_size<typename AT::value_type>;
    static T identity() {
      T r;
      for (size_t i=0; i < S::value; i++)
	for (size_t j=0; j < SS::value; j++) r[i][j] = 0;
      return r;
    }
    static T add(T a, T b) {
      T r;
      for (size_t i=0; i < S::value; i++)
	for (size_t j=0; j < SS::value; j++)
	  r[i][j] = a[i][j] + b[i][j];
      return r;
    }
  };

}
