#include <stdint.h>
#include <assert.h>
#include <iostream>
#include "input.h"
#include "grad.h"
#include "config.h"
#include "task.h"
#include "rgd_op.h"

void dumpResults(MutInput &input, struct FUT* fut) {
  int i = 0;
  for (auto it : fut->inputs) {
    std::cout << "index is " << it.first << " result is " << (int)input.value[i] << std::endl;
    i++;
  }
}

static uint32_t flip(uint32_t op) {
  switch (op) {
    case rgd::Equal: return rgd::Distinct;
    case rgd::Distinct: return rgd::Equal;
    case rgd::Sge: return rgd::Slt;
    case rgd::Sgt:  return rgd::Sle;
    case rgd::Sle:  return rgd::Sgt;
    case rgd::Slt:  return rgd::Sge;
    case rgd::Uge:  return rgd::Ult;
    case rgd::Ugt:  return rgd::Ule;
    case rgd::Ule:  return rgd::Ugt;
    case rgd::Ult:  return rgd::Uge;
    assert(false && "Non-relational op!");
  };
}

void addResults(MutInput &input, struct FUT* fut) {
  int i = 0;
  std::unordered_map<uint32_t, uint8_t> sol;
  for (auto it : fut->inputs) {
    sol[it.first] = input.value[i];
    i++;
  }
  if ((*fut->rgd_solutions).size() < 1)
    (*fut->rgd_solutions).push_back(sol);
}

void addPartialResults(MutInput &input, struct FUT* fut) {
  int i = 0;
  std::unordered_map<uint32_t, uint8_t> sol;
  for (auto it : fut->inputs) {
    sol[it.first] = input.value[i];
    i++;
  }
  if ((*fut->partial_solutions).size() < 50)
    (*fut->partial_solutions).push_back(sol);
}

void addOptiResults(MutInput &input, struct FUT* fut) {
  int i = 0;
  for (auto it : fut->inputs) {
    (*fut->opti_solution)[it.first] = input.value[i];
    i++;
  }
}


inline uint64_t sat_inc(uint64_t base, uint64_t inc) {
  return base+inc < base ? -1 : base+inc;
}

uint64_t getDistance(uint32_t comp, uint64_t a, uint64_t b) {
  uint64_t dis = 0;
  switch (comp) {
    case rgd::Equal:
      if (a>=b) dis = a-b;
      else dis=b-a;
      break;
    case rgd::Distinct:
      if (a==b) dis = 1;
      else dis = 0;
      break;
    case rgd::Ult:
      if (a<b) dis = 0;
      else dis = sat_inc(a-b,1);
      break;
    case rgd::Ule:
      if (a<=b) dis = 0;
      else dis = a-b;
      break;
    case rgd::Ugt:
      if (a>b) dis = 0;
      else dis = sat_inc(b-a,1);
      break;
    case rgd::Uge:
      if (a>=b) dis = 0;
      else dis = b-a;
      break;
    case rgd::Slt:
      if ((int64_t)a < (int64_t)b) return 0;
      else dis = sat_inc(a-b,1);
      break;
    case rgd::Sle:
      if ((int64_t)a <= (int64_t)b) return 0;
      else dis = a-b;
      break;
    case rgd::Sgt:
      if ((int64_t)a > (int64_t)b) return 0;
      else dis = sat_inc(b-a,1);
      break;
    case rgd::Sge:
      if ((int64_t)a >= (int64_t)b) return 0;
      else dis = b-a;
      break;
    default:
      assert(0);
  }
  return dis;
}


//uint64_t distance(MutInput &input, struct FUT* fut, bool* partial_found) {
uint64_t distance(MutInput &input, struct FUT* fut) {
  static int timeout = 0;
  static int solved= 0;
  uint64_t res = 0;
  uint64_t cur = 0;
  bool nested = false;
  if (fut->constraints.size() > 1)
    nested = true;
  for(int i=0; i<fut->constraints.size(); i++) {
    //mapping symbolic args
    int arg_idx = 0;
    std::shared_ptr<Cons> c = fut->constraints[i];
    for (auto arg : c->input_args) {
      if (arg.first) {// symbolic
        fut->scratch_args[2+arg_idx] = (uint64_t)input.value[arg.second];
      }
      else {
        fut->scratch_args[2+arg_idx] = arg.second;
      }
      ++arg_idx;
    }
    cur = (uint64_t)c->fn(fut->scratch_args);
    uint32_t comparison = c->comparison;
    if (i != 0) comparison = flip(comparison);
    uint64_t dis = getDistance(comparison,fut->scratch_args[0],fut->scratch_args[1]);
    fut->ctx->distances[i] = dis;
    // *partial_found = true;
    if (dis>0) {
      res = sat_inc(res,dis);
    }
  }
  //printf("%u %u %u %u => %lu\n", input.value[0], input.value[1], input.value[2], input.value[3], res);
  return res;
}

bool partial_derivative(MutInput &orig_input, size_t index, uint64_t f0, bool *sign, bool* is_linear, uint64_t *val, struct FUT* fut) {

  bool found = false;
  uint8_t orig_val = orig_input.get(index);
  std::vector<uint64_t> plus_distances;
  std::vector<uint64_t> minus_distances;
  orig_input.update(index,true,1);

  uint64_t f_plus = distance(orig_input,fut);
  plus_distances = fut->ctx->distances;

  if (f_plus == 0) {
    addResults(orig_input, fut);
    found = true;
  }

  orig_input.set(index,orig_val);
  orig_input.update(index,false,1);

  uint64_t f_minus = distance(orig_input,fut);
  minus_distances = fut->ctx->distances;
  if (f_minus == 0) {
    addResults(orig_input, fut);
    found = true;
  }
  orig_input.set(index,orig_val);

  if (f_minus < f0) {
    if (f_plus < f0) {
      if (f_minus < f_plus) {
        *sign = false;
        *is_linear = false;
        *val = f0 - f_minus;
      } else {
        *sign = true;
        *is_linear = false;
        *val = f0 - f_plus;
      }
    } else {
      *sign = false;
      *is_linear = ((f_minus != f0) && (f0 - f_minus == f_plus -f0));
      *val = f0 -f_minus;
    }
  } else {
    if (f_plus < f0) {
      *sign = true;
      *is_linear = ((f_minus != f0) && (f_minus - f0 == f0 - f_plus));
      *val = f0 - f_plus;
    }
    else {
      *sign = true;
      *is_linear = false;
      *val = 0;
    }
  }


  if (*val == 0) found; 

  if (sign) {
    for(int i=0; i< fut->ctx->distances.size(); i++) {
      if (plus_distances[i] !=0  && fut->ctx->orig_distances[i] == 0) {
        orig_input.setDisable(index);
        *val = 0;
        return found;
      }
    }
  } else {
    for(int i=0; i< fut->ctx->distances.size(); i++) {
      if (minus_distances[i] != 0  && fut->ctx->orig_distances[i] == 0) {
        orig_input.setDisable(index);
        *val = 0;
        return found;
      }
    }
  }
  

  return found;
}

void compute_delta_all(MutInput &input, Grad &grad, size_t step) {
  double fstep = (double)step;
  int index = 0;
  for(auto &gradu : grad.get_value()) {
    double movement = gradu.pct * step;
    input.update(index,gradu.sign,(uint64_t)movement);
    index++;
  }
}

void cal_gradient(struct FUT *fut) {
  int index = 0;
  for(auto &gradu : fut->ctx->grad.get_value()) {
    bool sign = false;
    bool is_linear = false;
    uint64_t val = 0;
    if (partial_derivative(fut->ctx->min_input, index, fut->ctx->f_last,
          &sign, &is_linear, &val, fut))
      fut->ctx->solved = true;
    gradu.sign = sign;
    gradu.val = val;
    index++;
  }
  fut->ctx->att += fut->ctx->grad.len();
  if (fut->ctx->grad.max_val() == 0) {
    fut->ctx->next_state = 5;  //randomize if there's no grad
  } else {
    fut->ctx->next_state = 2;  //go to guess_descend if grad is nonzero
    fut->ctx->grad.normalize();
  }
}

void guess_descend(struct FUT* fut) {
  MutInput &input_min = fut->ctx->min_input;
  MutInput &input_scratch = fut->ctx->scratch_input;
  input_scratch = input_min;
  uint64_t vsum = fut->ctx->grad.val_sum();
  uint64_t f_last = fut->ctx->f_last;
  if (vsum > 0) {
    auto guess_step = f_last / vsum;
    compute_delta_all(input_scratch,fut->ctx->grad,guess_step);
    uint64_t f_new = distance(input_scratch,fut);
    fut->ctx->att += 1;
    //if f_new && f_last are both zero, we start from the original input before guess step
    if (f_new >= f_last) {
      input_scratch = input_min;
    } else {
      input_min = input_scratch;
      f_last = f_new;
    }
  }

  fut->ctx->f_last = f_last;
  fut->ctx->next_state = 3; //let's go to descend

  if (f_last == 0) {
    fut->ctx->solved = true;
    addResults(input_min, fut);
  }
}


void alldimension_descend(struct FUT* fut) {
  MutInput &input_min = fut->ctx->min_input;
  MutInput &input_scratch = fut->ctx->scratch_input;
  input_scratch = input_min;
  uint64_t f_last = fut->ctx->f_last;
  while (true) {
    compute_delta_all(input_scratch, fut->ctx->grad, fut->ctx->step);
    uint64_t f_new = distance(input_scratch, fut);
    fut->ctx->att += 1;
    if (f_new >= f_last && f_new != 0) {
      //break; let's go to one dimension dimension
      if (fut->ctx->grad.len() == 1)
        fut->ctx->next_state = 5; //go to randomize
      else
        fut->ctx->next_state = 4; //go to onedimension
      fut->ctx->step = 1;
      fut->ctx->f_last = f_last;
      break;
    } else if (f_new == 0) {
      fut->ctx->solved = true;
      addResults(input_scratch, fut);
      fut->ctx->next_state = 3; //continue to descend
      fut->ctx->f_last = f_last;
      f_last = f_new;
      input_min = input_scratch;
      break;
    } else {
      input_min = input_scratch;
      f_last = f_new;
      fut->ctx->step *= 2;
    }
  }
}

void onedimension_descend(struct FUT* fut) {
  MutInput &input_min = fut->ctx->min_input;
  MutInput &input_scratch = fut->ctx->scratch_input;
  input_scratch = input_min;
  size_t step = fut->ctx->step;
  uint64_t f_last = fut->ctx->f_last;
  for (int dimensionIdx=fut->ctx->dimensionIdx; dimensionIdx < fut->ctx->grad.len(); dimensionIdx++) {
    if (fut->ctx->grad.get_value()[dimensionIdx].pct < 0.01)
      continue;
    while (true) {
      double movement = fut->ctx->grad.get_value()[dimensionIdx].pct * (double)fut->ctx->step;
      input_scratch.update(dimensionIdx,fut->ctx->grad.get_value()[dimensionIdx].sign,(uint64_t)movement);
      uint64_t f_new = distance(input_scratch, fut);
      fut->ctx->att += 1;
      if (f_new >= f_last && f_new != 0) {
        fut->ctx->step = 1;
        break;
      } else if (f_new == 0) {
        f_last = f_new;
        fut->ctx->solved = true;
        addResults(input_scratch, fut);
        fut->ctx->next_state = 4; //continue to one dimension descend
        fut->ctx->dimensionIdx = dimensionIdx;
        input_min = input_scratch;
        break;
      } else {
        input_min = input_scratch;
        f_last = f_new;
        fut->ctx->step *= 2;
      }
    }
  }
  fut->ctx->f_last = f_last;
  if (!fut->ctx->solved) {
    fut->ctx->next_state = 1; //go to cal gradient
    fut->ctx->dimensionIdx = 0; //reset dimenionidx
  }
}

void repick_start_point(struct FUT* fut) {
  MutInput &input_min = fut->ctx->min_input;
  input_min.randomize();
  fut->ctx->f_last = distance(input_min,fut);
  fut->ctx->orig_distances = fut->ctx->distances;
  fut->ctx->next_state = 1;
  fut->ctx->grad.clear();
  fut->ctx->att += 1;
  if (fut->ctx->f_last== 0) {
    fut->ctx->solved = true;
    addResults(input_min, fut);
  }
}

void load_input(struct FUT* fut) {
  MutInput &input_min = fut->ctx->min_input;
  input_min.assign(fut->inputs);
/*
  input_min.value[3] = 0xD0;
  input_min.value[2] = 0xCF;
  input_min.value[0] = 0x32;
  input_min.value[6] = 0x00;
*/
  fut->ctx->f_last = distance(input_min,fut);
  fut->ctx->orig_distances = fut->ctx->distances;
  fut->ctx->next_state = 1;
  fut->ctx->grad.clear();
  fut->ctx->att += 1;
  if (fut->ctx->f_last== 0) {
    fut->ctx->solved = true;
    addResults(input_min, fut);
  }
}

bool gd_search(struct FUT* fut) {
  while (true) {
    switch (fut->ctx->next_state) {
      //reload
      case 0:
        load_input(fut);
        break;
      case 1:
        cal_gradient(fut);
        break;
      case 2:
        guess_descend(fut);
        break;
      case 3:
        alldimension_descend(fut);
        break;
      case 4:
        onedimension_descend(fut);
        break;
      case 5:
        repick_start_point(fut);
        break;
      default:
        break;
    }
    if (fut->ctx->solved) {
      fut->ctx->solved = false;
      fut->ctx->att = 0;
      return true;
    }
    if (fut->ctx->att > MAX_EXEC_TIMES) {
      fut->ctx->att = 0;
      return false;
    }
  }
}
