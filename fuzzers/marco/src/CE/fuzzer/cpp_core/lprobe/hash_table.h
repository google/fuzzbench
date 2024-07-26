// This code is part of the Problem Based Benchmark Suite (PBBS)
// Copyright (c) 2010 Guy Blelloch and the PBBS team
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
#include "utilities.h"
#include "sequence_ops.h"

namespace pbbs {

	// A "history independent" hash table that supports insertion, and searching
	// It is described in the paper
	//   Julian Shun and Guy E. Blelloch
	//   Phase-concurrent hash tables for determinism
	//   SPAA 2014: 96-107
	// Insertions can happen in parallel
	// Searches can happen in parallel
	// Deletion can happen in parallel
	// but insertions cannot happen in parallel with searches or deletions
	// and searches cannot happen in parallel with deletions
	// i.e. each of the three types of operations have to happen in phase
	template <class HASH>
		class Table {
			private:
				using eType = typename HASH::eType;
				using kType = typename HASH::kType;
				size_t m;
				eType empty;
				HASH hashStruct;
				eType* TA;
				using index = long;

				static void clear(eType* A, size_t n, eType v) {
					auto f = [&] (size_t i) {
						assign_uninitialized(A[i], v);};
					parallel_for(0, n, f, granularity(n));
				}

				struct notEmptyF {
					eType e; notEmptyF(eType _e) : e(_e) {}
					int operator() (eType a) {return e != a;}};

				index hashToRange(index h) {return (int) h % (uint) m;}
				index firstIndex(kType v) {return hashToRange(hashStruct.hash(v));}
				index incrementIndex(index h) {return (h + 1 == (long) m) ? 0 : h+1;}
				index decrementIndex(index h) {return (h == 0) ? m-1 : h-1;}
				bool lessIndex(index a, index b) {return (a < b) ? (2*(b-a) < m) : (2*(a-b) > m);}
				bool lessEqIndex(index a, index b) {return a==b || lessIndex(a,b);}

			public:
				// Size is the maximum number of values the hash table will hold.
				// Overfilling the table could put it into an infinite loop.
				Table(size_t size, HASH hashF, float load = 1.5) :
					m(((size_t) 100.0 + load * size)),
					empty(hashF.empty()),
					hashStruct(hashF),
					TA(new_array_no_init<eType>(m)) {
						clear(TA, m, empty); }

				~Table() { delete_array(TA, m);};

				// prioritized linear probing
				//   a new key will bump an existing key up if it has a higher priority
				//   an equal key will replace an old key if replaceQ(new,old) is true
				// returns 0 if not inserted (i.e. equal and replaceQ false) and 1 otherwise
				bool insert(eType v) {
					index i = firstIndex(hashStruct.getKey(v));
					while (true) {
						eType c = TA[i];
						if (c == empty) {
							if (hashStruct.cas(&TA[i],c,v)) return true;
						} else {
							int cmp = hashStruct.cmp(hashStruct.getKey(v),hashStruct.getKey(c));
							if (cmp == 0) {
								if (!hashStruct.replaceQ(v,c)) return false;
								else if (hashStruct.cas(&TA[i],c,v)) return true;
							} else if (cmp < 0)
								i = incrementIndex(i);
							else if (hashStruct.cas(&TA[i],c,v)) {
								v = c;
								i = incrementIndex(i);
							}
						}
					}
				}

				// prioritized linear probing
				//   a new key will bump an existing key up if it has a higher priority
				//   an equal key will replace an old key if replaceQ(new,old) is true
				// returns 0 if not inserted (i.e. equal and replaceQ false) and 1 otherwise
				bool update(eType v) {
					index i = firstIndex(hashStruct.getKey(v));
					while (true) {
						eType c = TA[i];
						if (c == empty) {
							if (hashStruct.cas(&TA[i],c,v)) return true;
						} else {
							int cmp = hashStruct.cmp(hashStruct.getKey(v),hashStruct.getKey(c));
							if (cmp == 0) {
								if (!hashStruct.replaceQ(v,c)) return false;
								else {
									eType new_val = hashStruct.update(c,v);
									if (hashStruct.cas(&TA[i],c,new_val)) return true;
								}
							} else if (cmp < 0)
								i = incrementIndex(i);
							else if (hashStruct.cas(&TA[i],c,v)) {
								v = c;
								i = incrementIndex(i);
							}
						}
					}
				}

				bool deleteVal(kType v) {
					index i = firstIndex(v);
					int cmp;

					// find first element less than or equal to v in priority order
					index j = i;
					eType c = TA[j];

					if (c == empty) return true;

					// find first location with priority less or equal to v's priority
					while ((cmp = (c==empty) ? 1 : hashStruct.cmp(v, hashStruct.getKey(c))) < 0) {
						j = incrementIndex(j);
						c = TA[j];
					}
					while (true) {
						// Invariants:
						//   v is the key that needs to be deleted
						//   j is our current index into TA
						//   if v appears in TA, then at least one copy must appear at or before j
						//   c = TA[j] at some previous time (could now be changed)
						//   i = h(v)
						//   cmp = compare v to key of c (positive if greater, 0 equal, negative less)
						if (cmp != 0) {
							// v does not match key of c, need to move down one and exit if
							// moving before h(v)
							if (j == i) return true;
							j = decrementIndex(j);
							c = TA[j];
							cmp = (c == empty) ? 1 : hashStruct.cmp(v, hashStruct.getKey(c));
						} else { // found v at location j (at least at some prior time)

							// Find next available element to fill location j.
							// This is a little tricky since we need to skip over elements for
							// which the hash index is greater than j, and need to account for
							// things being moved downwards by others as we search.
							// Makes use of the fact that values in a cell can only decrease
							// during a delete phase as elements are moved from the right to left.
							index jj = incrementIndex(j);
							eType x = TA[jj];
							while (x != empty && lessIndex(j, firstIndex(hashStruct.getKey(x)))) {
								jj = incrementIndex(jj);
								x = TA[jj];
							}
							index jjj = decrementIndex(jj);
							while (jjj != j) {
								eType y = TA[jjj];
								if (y == empty || !lessIndex(j, firstIndex(hashStruct.getKey(y)))) {
									x = y;
									jj = jjj;
								}
								jjj = decrementIndex(jjj);
							}

							// try to copy the the replacement element into j
							if (hashStruct.cas(&TA[j],c,x)) {
								// swap was successful
								// if the replacement element was empty, we are done
								if (x == empty) return true;

								// Otherwise there are now two copies of the replacement element x
								// delete one copy (probably the original) by starting to look at jj.
								// Note that others can come along in the meantime and delete
								// one or both of them, but that is fine.
								v = hashStruct.getKey(x);
								j = jj;
								i = firstIndex(v);
							}
							c = TA[j];
							cmp = (c == empty) ? 1 : hashStruct.cmp(v, hashStruct.getKey(c));
						}
					}
				}

				// Returns the value if an equal value is found in the table
				// otherwise returns the "empty" element.
				// due to prioritization, can quit early if v is greater than cell
				eType find(kType v) {
					index h = firstIndex(v);
					eType c = TA[h];
					while (true) {
						if (c == empty) {return empty;}
						int cmp = hashStruct.cmp(v,hashStruct.getKey(c));
						if (cmp >= 0) {
							/*Ju we disable >0 case, because the +1 is not defined for our JitRequest*/
							if (cmp > 0) return empty;
							else return c;
							//return c;
						}
						h = incrementIndex(h);
						c = TA[h];
					}
				}

				// returns the number of entries
				size_t count() {
					auto is_full = [&] (size_t i) -> size_t {
						return (TA[i] == empty) ? 0 : 1;};
					return reduce(delayed_seq<size_t>(m, is_full), addm<size_t>());
				}

				// returns all the current entries compacted into a sequence
				sequence<eType> entries() {
					return filter(range<eType*>(TA, TA+m),
							[&] (eType v) {return v != empty;});
				}

				index findIndex(kType v) {
					index h = firstIndex(v);
					eType c = TA[h];
					while (true) {
						if (c == empty) return -1;
						int cmp = hashStruct.cmp(v,hashStruct.getKey(c));
						if (cmp >= 0) {
							if (cmp > 0) return -1;
							else return h;
						}
						h = incrementIndex(h);
						c = TA[h];
					}
				}

				sequence<index> get_index() {
					auto is_full = [&] (const size_t i) -> int {
						if (TA[i] != empty) return 1; else return 0;};
					sequence<index> x(m, is_full);
					scan_inplace(x.slice(), addm<index>());
					return x;
				}

				// prints the current entries along with the index they are stored at
				void print() {
					cout << "vals = ";
					for (size_t i=0; i < m; i++)
						if (TA[i] != empty)
							cout << i << ":" << TA[i] << ",";
					cout << endl;
				}
		};

	template <class ET, class H>
		sequence<ET> remove_duplicates(sequence<ET> const &S, H const &hash, size_t m=0) {
			timer t("remove duplicates", false);
			if (m==0) m = S.size();
			Table<H> T(m, hash, 1.3);
			t.next("build table");
			parallel_for(0, S.size(), [&] (size_t i) { T.insert(S[i]);});
			t.next("insert");
			sequence<ET> result = T.entries();
			t.next("entries");
			return result;
		}

	// T must be some integer type
	template <class T>
		struct hashInt {
			using eType = T;
			using kType = T;
			eType empty() {return -1;}
			kType getKey(eType v) {return v;}
			T hash(kType v) {return v * 999029;} //hash64_2(v);}
	int cmp(kType v, kType b) {return (v > b) ? 1 : ((v == b) ? 0 : -1);}
	bool replaceQ(eType, eType) {return 0;}
	eType update(eType v, eType) {return v;}
	bool cas(eType* p, eType o, eType n) {return
		atomic_compare_and_swap(p, o, n);}
};

// works for non-negative integers (uses -1 to mark cell as empty)
template <class T>
sequence<T> remove_duplicates(sequence<T> const &A) {
	return remove_duplicates(A, hashInt<T>());
}

}
