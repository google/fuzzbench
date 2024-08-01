#include "task.h"
#include "rgd.pb.h"
#include "rgd_op.h"
#include "jit.h"
#include "lprobe/hash_table.h"
using namespace rgd;
using namespace pbbs;
#define DEBUG 0
static std::atomic_ullong uuid;
static std::atomic_ullong miss;
static std::atomic_ullong hit;
extern bool USE_CODECACHE;

bool recursive_equal(const AstNode& lhs, const AstNode& rhs) {
  if ((lhs.kind() >= rgd::Ult && lhs.kind() <= rgd::Uge) &&
      (rhs.kind() >= rgd::Ult && rhs.kind() <= rgd::Uge)) {
    const int children_size = lhs.children_size();
    if (children_size != rhs.children_size()) return false;
    for (int i = 0; i < children_size; i++) {
      if (!recursive_equal(lhs.children(i), rhs.children(i)))
        return false;
    }
    return true;
  }
  if ((lhs.kind() >= rgd::Slt && lhs.kind() <= rgd::Sge) &&
      (rhs.kind() >= rgd::Slt && rhs.kind() <= rgd::Sge)) {
    const int children_size = lhs.children_size();
    if (children_size != rhs.children_size()) return false;
    for (int i = 0; i < children_size; i++) {
      if (!recursive_equal(lhs.children(i), rhs.children(i)))
        return false;
    }
    return true;
  }
  if ((lhs.kind() >= rgd::Equal && lhs.kind() <= rgd::Distinct) &&
      (rhs.kind() >= rgd::Equal && rhs.kind() <= rgd::Distinct)) {
    const int children_size = lhs.children_size();
    if (children_size != rhs.children_size()) return false;
    for (int i = 0; i < children_size; i++) {
      if (!recursive_equal(lhs.children(i), rhs.children(i)))
        return false;
    }
    return true;
  }
  if (lhs.hash() != rhs.hash()) return false;
  if (lhs.kind() != rhs.kind()) return false;
  if (lhs.bits() != rhs.bits()) return false;
  const int children_size = lhs.children_size();
  if (children_size != rhs.children_size()) return false;
  for (int i = 0; i < children_size; i++) {
    if (!recursive_equal(lhs.children(i), rhs.children(i)))
      return false;
  }
  return true;
}

bool isEqual(const AstNode& lhs, const AstNode& rhs) {
  return recursive_equal(lhs, rhs);
}

struct myKV {
  std::shared_ptr<AstNode> req;
  test_fn_type fn;
  myKV(std::shared_ptr<AstNode> areq, test_fn_type f) : req(areq), fn(f) {}
};

struct myHash {
  using eType = struct myKV*;
  using kType = std::shared_ptr<AstNode>;
  eType empty() {return nullptr;}
  kType getKey(eType v) {return v->req;}
  int hash(kType v) {return v->hash();} //hash64_2(v);}
  //int hash(kType v) {return hash64_2(v);}
  //int cmp(kType v, kType b) {return (v > b) ? 1 : ((v == b) ? 0 : -1);}
  int cmp(kType v, kType b) {return (isEqual(*v,*b)) ? 0 : -1;}
  bool replaceQ(eType, eType) {return 0;}
  eType update(eType v, eType) {return v;}
  bool cas(eType* p, eType o, eType n) {return atomic_compare_and_swap(p, o, n);}
  };


struct taskKV {
  std::tuple<uint64_t,uint64_t,uint32_t, uint64_t> branch;
  FUT* fut;
  FUT* fut_opt;
  taskKV(std::tuple<uint64_t,uint64_t,uint32_t, uint64_t> abranch,
      FUT* afut,
      FUT* afut_opt)
    : branch(abranch), fut(afut), fut_opt(afut_opt) {}
};

struct taskHash {
  using eType = struct taskKV*;
  using kType = std::tuple<uint64_t, uint64_t, uint32_t, uint64_t>;
  eType empty() {return nullptr;}
  kType getKey(eType v) {return v->branch;}
  int hash(kType v) {return std::get<0>(v)^std::get<1>(v)^std::get<2>(v)^std::get<3>(v);} //hash64_2(v);}
  //int hash(kType v) {return hash64_2(v);}
  //int cmp(kType v, kType b) {return (v > b) ? 1 : ((v == b) ? 0 : -1);}
  int cmp(kType v, kType b) {return (v == b) ? 0 : -1;}
  bool replaceQ(eType, eType) {return 0;}
  eType update(eType v, eType) {return v;}
  bool cas(eType* p, eType o, eType n) {return atomic_compare_and_swap(p, o, n);}
  };

static pbbs::Table<myHash> Expr2Func(8000016, myHash(), 1.3);
pbbs::Table<taskHash> TaskCache(8000016, taskHash(), 1.3);


static void append_meta(std::shared_ptr<Cons> cons, const Constraint* c) {
  for (auto amap : c->meta().map()) {
    cons->local_map.insert({amap.k(), amap.v()});
  }
  for (auto aarg : c->meta().args()) {
    cons->input_args.push_back({aarg.isinput(), aarg.v()});
  }
  for (auto ainput : c->meta().inputs()) {
    cons->inputs.insert({ainput.offset(), ainput.iv()});
  }
  cons->comparison = c->node().kind(); 
  cons->const_num = c->meta().const_num(); 
}

std::unordered_map<uint64_t,std::shared_ptr<Cons>> cons_cache(1000000);


void construct_task(SearchTask* task, struct FUT** fut, struct FUT** fut_opt) {
  int i = 0;
  static uint32_t old_fid = -1;
  for (auto c : task->constraints()) {
    assert(c.node().kind() != rgd::Constant && "kind must be non-constant");
    std::shared_ptr<Cons> cons;
    if (cons_cache.find(task->fid()*100000 + c.label()) != cons_cache.end()) {
      cons = cons_cache[task->fid()*100000 + c.label()];
    } else {
      cons = std::make_shared<Cons>();
      append_meta(cons, &c);
      if (USE_CODECACHE) {
        std::shared_ptr<AstNode> req = std::make_shared<AstNode>();
        req->CopyFrom(c.node());
        struct myKV *res = Expr2Func.find(req);
        //   struct myKV *res = nullptr;

        if ( res == nullptr) {
          ++miss;
          uint64_t id = uuid.fetch_add(1, std::memory_order_relaxed);
          addFunction(&c.node(), cons->local_map, id);
          auto fn = performJit(id);

          res = new struct myKV(req, fn);
          if (!Expr2Func.insert(res)) {
            // if the function has already been inserted during this time
            delete res;
            res = nullptr;
          }
          cons->fn = fn; // fn could be duplicated, but that's fine
        } else {
          ++hit;
#if DEBUG
          if (hit % 1000 == 0) {
            std::cout << "hit/miss is " << hit << "/" << miss << std::endl;
          }
#endif
          cons->fn = res->fn;
        }

      } else {
        uint64_t id = uuid.fetch_add(1, std::memory_order_relaxed);
        addFunction(&c.node(), cons->local_map, id);
        auto fn = performJit(id);
        cons->fn = fn; // fn could be duplicated, but that's fine
      }
      cons_cache.insert({task->fid() * 100000 + c.label(), cons});
    }
    (*fut)->constraints.push_back(cons);
    if ( i == 0)
      (*fut_opt)->constraints.push_back(cons);
    i++;
  }

  (*fut)->finalize();
  (*fut_opt)->finalize();
  //return fut;
  return;
}


void lookup_or_construct(SearchTask* task, struct FUT** fut, struct FUT** fut_opt) {
  static int hit = 0;
  static int miss = 0;


  std::tuple<uint64_t,uint64_t,uint32_t,uint64_t> bid{task->addr(),task->ctx(),task->order(), task->direction()};
  struct taskKV *res = TaskCache.find(bid);

  if (res == nullptr) {
    // printf("miss count %d\n", ++miss);
    *fut = new FUT();
    *fut_opt = new FUT();
    construct_task(task,fut,fut_opt);
    res = new struct taskKV({bid, *fut, *fut_opt});
    if (!TaskCache.insert(res)) {
      delete res;
      delete (*fut);
      delete (*fut_opt);
      res =  TaskCache.find(bid);
      *fut = res->fut;
      *fut_opt = res->fut_opt;
    }
  } else {
    //printf("hit count %d\n", ++hit);
    *fut = res->fut;
    *fut_opt = res->fut_opt;
  }
}
