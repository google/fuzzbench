#ifndef DATA_ELEMENT_
#define DATA_ELEMENT_
#include "utilities.h"
using namespace pbbs;
struct KV {
	int k;
	int v;
	//bool operator== (struct KV other) { return k == other.k && v == other.v ;}
	//bool operator!= (struct KV other) { return k != other.k || v != other.v ;}
	KV(int ak, int av) {k=ak;v=av;}
};

struct hashKV {
	using eType = struct KV*;
	using kType = int;
	//eType empty() {return new struct KV(-1,-1);}
	eType empty() {return nullptr;}
	kType getKey(eType v) {return v->k;}
	int hash(kType v) {return v * 999029;} //hash64_2(v);}
	//int hash(kType v) {return hash64_2(v);}
	//int cmp(kType v, kType b) {return (v > b) ? 1 : ((v == b) ? 0 : -1);}
	int cmp(kType v, kType b) {return (v == b) ? 0 : -1;}
	bool replaceQ(eType, eType) {return 0;}
	eType update(eType v, eType) {return v;}
	bool cas(eType* p, eType o, eType n) {return
		atomic_compare_and_swap(p, o, n);}
};
#endif
