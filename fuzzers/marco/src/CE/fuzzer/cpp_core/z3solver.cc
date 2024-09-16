#include <set>
#include <byteswap.h>
#include <unistd.h>
#include <sys/syscall.h>
#include "z3solver.h"
#include "rgd_op.h"
#include "rgd.pb.h"

using namespace rgd;
uint64_t getTimeStamp();
z3::context   g_z3_context;
const int kSessionIdLength = 32;
const unsigned kSolverTimeout = 10000; // 10 seconds
Solver *g_solver;
void initZ3Solver() {
  g_solver = new Solver();
}

Solver::Solver() :
  context_(g_z3_context)
  , solver_(z3::solver(context_, "QF_BV"))
  , start_time_(getTimeStamp())
  , solving_time_(0)
  , solving_count_(0)
{
  // Set timeout for solver
  z3::params p(context_);
  p.set(":timeout", kSolverTimeout);
  solver_.set(p);
}

void Solver::add(z3::expr expr) {
  if (!expr.is_const())
    solver_.add(expr.simplify());
}

void Solver::reset() {
  solver_.reset();
}

bool Solver::checkonly() {
  uint64_t before = getTimeStamp();
  z3::check_result res;
  try {
    res = solver_.check();
    if (res != z3::sat) {
      //std::cout << "branch NOT solved in checkonly!" << std::endl;
      return false;
    }
  } catch (z3::exception e) {
    //std::cout << "Z3 alert: " << e.msg() << std::endl;
    return false;
  }
  return true;
}


bool Solver::check(std::unordered_map<uint32_t,uint8_t> &solu) {
  uint64_t before = getTimeStamp();
  z3::check_result res;
  try {
    res = solver_.check();
    if (res==z3::sat) {
      //std::cout << "branch solved!!" << std::endl;
      z3::model m = solver_.get_model();

      unsigned num_constants = m.num_consts();
      for(unsigned i = 0; i< num_constants; i++) {
        z3::func_decl decl = m.get_const_decl(i);
        z3::expr e = m.get_const_interp(decl);
        z3::symbol name = decl.name();
        if(name.kind() == Z3_INT_SYMBOL) {
          uint8_t value = (uint8_t)e.get_numeral_int();
          solu[name.to_int()] = value;
          //std::cout << " generate_input index is " << name.to_int() << " and value is " << (int)value << std::endl;
        }
      }
      return true;
    }	else {
      //std::cout << "branch NOT solved in check()" << std::endl;
      return false;
    }
  } catch (z3::exception e) {
    //std::cout << "Z3 alert: " << e.msg() << std::endl;
  }
}

inline z3::expr Solver::cache_expr(uint32_t label, z3::expr const &e, 
    std::unordered_map<uint32_t,z3::expr> &expr_cache) {	
  if (label!=0)
    expr_cache.insert({label,e});
  return e;
}


z3::expr Solver::serialize(const AstNode* req,
    std::unordered_map<uint32_t,z3::expr> &expr_cache) {

  auto itr = expr_cache.find(req->label());

  if (req->label() != 0 && itr != expr_cache.end())
    return itr->second;

  switch (req->kind()) {
    case rgd::Bool: {
                      // getTrue is actually 1 bit integer 1
                      return cache_expr(req->label(),context_.bool_val(req->boolvalue()),expr_cache);
                    }
    case rgd::Constant: {
                          if (req->bits() == 1) {
                            return cache_expr(req->label(),context_.bool_val(req->value()=="1"),expr_cache);
                          } else {
                            return cache_expr(req->label(),context_.bv_val(req->value().c_str(),req->bits()),expr_cache);
                          }
                        }
    case rgd::Read: {
                      z3::symbol symbol = context_.int_symbol(req->index());
                      z3::sort sort = context_.bv_sort(8);
                      z3::expr out = context_.constant(symbol,sort);
                      for(uint32_t i=1; i<req->bits()/8; i++) {
                        symbol = context_.int_symbol(req->index()+i);
                        out = z3::concat(context_.constant(symbol,sort),out);
                      }
                      return cache_expr(req->label(),out,expr_cache);
                    }
    case rgd::Concat: {
                        z3::expr c1 = serialize(&req->children(0),expr_cache);
                        z3::expr c2 = serialize(&req->children(1),expr_cache);
                        return cache_expr(req->label(),z3::concat(c2,c1),expr_cache);
                      }
    case rgd::Extract: {
                         z3::expr c1 = serialize(&req->children(0),expr_cache);
                         return cache_expr(req->label(),c1.extract(req->index()+req->bits()-1,req->index()),expr_cache);
                       }
    case rgd::ZExt: {
                      z3::expr c1 = serialize(&req->children(0),expr_cache);
                      if (c1.is_bool())
                        c1 = z3::ite(c1,context_.bv_val(1,1),context_.bv_val(0, 1));
                      return cache_expr(req->label(),z3::zext(c1,req->bits()-req->children(0).bits()),expr_cache);
                    }
    case rgd::SExt: {
                      z3::expr c1 = serialize(&req->children(0),expr_cache);
                      return cache_expr(req->label(),z3::sext(c1,req->bits()-req->children(0).bits()),expr_cache);
                    }
    case rgd::Add: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),c1+c2,expr_cache);
                   }
    case rgd::Sub: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),c1-c2,expr_cache);
                   }
    case rgd::Mul: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),c1*c2,expr_cache);
                   }
    case rgd::UDiv: {
                      z3::expr c1 = serialize(&req->children(0),expr_cache);
                      z3::expr c2 = serialize(&req->children(1),expr_cache);
                      return cache_expr(req->label(),z3::udiv(c1,c2),expr_cache);
                    }
    case rgd::SDiv: {
                      z3::expr c1 = serialize(&req->children(0),expr_cache);
                      z3::expr c2 = serialize(&req->children(1),expr_cache);
                      return cache_expr(req->label(),c1/c2,expr_cache); 
                    } 
    case rgd::URem: {
                      z3::expr c1 = serialize(&req->children(0),expr_cache);
                      z3::expr c2 = serialize(&req->children(1),expr_cache);
                      return cache_expr(req->label(),z3::urem(c1,c2),expr_cache);
                    }
    case rgd::SRem: {
                      z3::expr c1 = serialize(&req->children(0),expr_cache);
                      z3::expr c2 = serialize(&req->children(1),expr_cache);
                      return cache_expr(req->label(),z3::srem(c1,c2),expr_cache);
                    }
    case rgd::Neg: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     return cache_expr(req->label(),-c1,expr_cache);
                   }
    case rgd::Not: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     return cache_expr(req->label(),~c1,expr_cache);
                   }
    case rgd::And: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),c1 & c2,expr_cache);
                   }
    case rgd::Or: {
                    z3::expr c1 = serialize(&req->children(0),expr_cache);
                    z3::expr c2 = serialize(&req->children(1),expr_cache);
                    return cache_expr(req->label(),c1 | c2,expr_cache);
                  }
    case rgd::Xor: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),c1^c2,expr_cache);
                   }
    case rgd::Shl: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),z3::shl(c1,c2),expr_cache);
                   }
    case rgd::LShr: {
                      z3::expr c1 = serialize(&req->children(0),expr_cache);
                      z3::expr c2 = serialize(&req->children(1),expr_cache);
                      return cache_expr(req->label(),z3::lshr(c1,c2),expr_cache);
                    }
    case rgd::AShr: {
                      z3::expr c1 = serialize(&req->children(0),expr_cache);
                      z3::expr c2 = serialize(&req->children(1),expr_cache);
                      return cache_expr(req->label(),z3::ashr(c1,c2),expr_cache);
                    }
    case rgd::Equal: {
                       z3::expr c1 = serialize(&req->children(0),expr_cache);
                       z3::expr c2 = serialize(&req->children(1),expr_cache);
                       return cache_expr(req->label(),c1==c2,expr_cache);
                     }
    case rgd::Distinct: {
                          z3::expr c1 = serialize(&req->children(0),expr_cache);
                          z3::expr c2 = serialize(&req->children(1),expr_cache);
                          z3::expr rr = c1!=c2;
                          return cache_expr(req->label(),c1!=c2,expr_cache);
                        }
    case rgd::Ult: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),z3::ult(c1,c2),expr_cache);
                   }
    case rgd::Ule: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),z3::ule(c1,c2),expr_cache);
                   }
    case rgd::Ugt: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),z3::ugt(c1,c2),expr_cache);
                   }
    case rgd::Uge: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),z3::uge(c1,c2),expr_cache);
                   }
    case rgd::Slt: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),c1<c2,expr_cache);
                   }
    case rgd::Sle: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),c1<=c2,expr_cache);
                   }
    case rgd::Sgt: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),c1>c2,expr_cache);
                   }
    case rgd::Sge: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),c1>=c2,expr_cache);
                   }
    case rgd::LOr: {
                     z3::expr c1 = serialize(&req->children(0),expr_cache);
                     z3::expr c2 = serialize(&req->children(1),expr_cache);
                     return cache_expr(req->label(),c1 || c2,expr_cache);
                   }
    case rgd::LAnd: {
                      z3::expr c1 = serialize(&req->children(0),expr_cache);
                      z3::expr c2 = serialize(&req->children(1),expr_cache);
                      return cache_expr(req->label(),c1 && c2,expr_cache);
                    }
    case rgd::LNot: {
                      z3::expr c1 = serialize(&req->children(0),expr_cache);
                      return cache_expr(req->label(),!c1,expr_cache);
                    }
    default:
                    std::cerr << "WARNING: unhandler expr: ";
                    break;
  }
}

std::unordered_map<uint64_t,z3::expr>  session_cache(1000000);
bool sendZ3Solver(bool opti, SearchTask* task, std::unordered_map<uint32_t, uint8_t> &solu) {
  g_solver->reset();
  int num_expr = 0;
  if (opti)
    num_expr = 1;
  else
    num_expr = task->constraints_size();
  for (int i = 0; i < num_expr; i++) {
    std::unordered_map<uint32_t,z3::expr> expr_cache;
    const AstNode *req = &task->constraints(i).node();
    //printExpression(req);
    try {
      auto itr = session_cache.find(task->fid() * 100000 + task->constraints(i).label());
      if (itr != session_cache.end()) {
        //if (0) {
        z3::expr z3expr = itr->second;
        // std::cout << "[debug-if]: z3: " << z3expr.to_string() << std::endl;
        // std::cout << "[debug-if]: z3 simplified: " << z3expr.simplify().to_string() << std::endl;
        if (i != 0)
          g_solver->add(!z3expr);
        else
          g_solver->add(z3expr);
      } else {
        z3::expr z3expr = g_solver->serialize(req,expr_cache);
        // std::cout << "[debug-else]: z3: " << z3expr.to_string() << std::endl;
        // std::cout << "[debug-else]: z3 simplified: " << z3expr.simplify().to_string() << std::endl;
        g_solver->add(z3expr);
        session_cache.insert({task->fid() * 100000 + task->constraints(i).label(),z3expr});
      }
        
    } catch (z3::exception e) {
      std::cout << "[debug]: z3 alert: " << e.msg() << std::endl;
      return false;
    }
  }
    
  bool ret = false;
  if (task->solve()) { 
    ret = g_solver->check(solu);
  }
  return ret;
}

