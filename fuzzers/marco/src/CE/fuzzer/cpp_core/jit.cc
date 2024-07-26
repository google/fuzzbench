#include "llvm/ADT/APFloat.h"
#include "llvm/ADT/STLExtras.h"
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/DerivedTypes.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Type.h"
#include "llvm/IR/Verifier.h"
#include "llvm/Support/TargetSelect.h"
#include "llvm/Target/TargetMachine.h" 
#include "llvm/Transforms/InstCombine/InstCombine.h" 
#include "llvm/Transforms/Scalar.h"
#include "llvm/Transforms/Scalar/GVN.h"
#include "rgd.pb.h"
#include "rgd_op.h"
#include "util.h"
#include "rgdJit.h"
#include "task.h"
#include <iostream>
#include <unordered_map>

using namespace llvm;
using namespace rgd;

extern std::unique_ptr<GradJit> JIT;// = make_unique<GradJit>();
const int RET_OFFSET = 2; //the first two slots of the arguments for reseved for the left and right operands

//Generate code for a AST node.
//There should be no relational (Equal, Distinct, Ult, Ule, Ugt, Uge, Sle, Sle, Sgt, Sge) operators in the node
//Builder: LLVM IR builder
//localmap:  for each Constant/Read node (leaf node), find its position in the argument
llvm::Value* codegen(llvm::IRBuilder<> &Builder,
		const AstNode* node,
		std::unordered_map<uint32_t,uint32_t> &local_map, llvm::Value* arg,
		std::unordered_map<uint32_t, llvm::Value*> &value_cache) {

	llvm::Value* ret = nullptr;

	auto itr = value_cache.find(node->label());
	if (node->label() != 0
			&& itr != value_cache.end()) {
		return itr->second;
	}

	switch (node->kind()) {
		case rgd::Bool: {
			// getTrue is actually 1 bit integer 1
			if(node->boolvalue())
				ret = llvm::ConstantInt::getTrue(Builder.getContext());
			else
				ret = llvm::ConstantInt::getFalse(Builder.getContext());
			break;
		}
		case rgd::Constant: {
			uint32_t start = node->index();
			uint32_t length = node->bits()/8;

			llvm::Value* idx[1];
			idx[0] = llvm::ConstantInt::get(Builder.getInt32Ty(),start+RET_OFFSET);
			ret = Builder.CreateLoad(Builder.CreateGEP(arg,idx));
			ret = Builder.CreateTrunc(ret, llvm::Type::getIntNTy(Builder.getContext(),node->bits()));
			break;
		}

		case rgd::Read: {
			uint32_t start = local_map[node->index()];
			size_t length = node->bits()/8;
			llvm::Value* idx[1];
			idx[0] = llvm::ConstantInt::get(Builder.getInt32Ty(),start+RET_OFFSET);
			ret = Builder.CreateLoad(Builder.CreateGEP(arg,idx));
			for(uint32_t k = 1; k < length; k++) {
				idx[0] = llvm::ConstantInt::get(Builder.getInt32Ty(),start+k+RET_OFFSET);
				llvm::Value* tmp = Builder.CreateLoad(Builder.CreateGEP(arg,idx));
				tmp = Builder.CreateShl(tmp, 8 * k);
				ret =Builder.CreateOr(ret,tmp);
			}
			ret = Builder.CreateTrunc(ret, llvm::Type::getIntNTy(Builder.getContext(),node->bits()));
			break;
		}
		case rgd::Concat: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			uint32_t bits =  rc1->bits() + rc2->bits(); 
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			ret = Builder.CreateOr(
					Builder.CreateShl(
						Builder.CreateZExt(c2,llvm::Type::getIntNTy(Builder.getContext(),bits)),
						rc1->bits()),
					Builder.CreateZExt(c1, llvm::Type::getIntNTy(Builder.getContext(), bits)));
			break;
		}
		case rgd::Extract: {
			const AstNode* rc = &node->children(0);
			llvm::Value* c = codegen(Builder,rc, local_map, arg, value_cache);
			ret = Builder.CreateTrunc(
					Builder.CreateLShr(c, node->index()),
					llvm::Type::getIntNTy(Builder.getContext(), node->bits()));
			break;
		}
		case rgd::ZExt: {
			const AstNode* rc = &node->children(0);
			llvm::Value* c = codegen(Builder,rc, local_map, arg, value_cache);
			ret = Builder.CreateZExtOrTrunc(c, llvm::Type::getIntNTy(Builder.getContext(), node->bits()));
			break;
		}
		case rgd::SExt: {
			const AstNode* rc = &node->children(0);
			llvm::Value* c = codegen(Builder,rc,local_map, arg, value_cache);
			ret = Builder.CreateSExt(c, llvm::Type::getIntNTy(Builder.getContext(), node->bits()));
			break;
		}
		case rgd::Add: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			ret = Builder.CreateAdd(c1, c2);
			break;
		}
		case rgd::Sub: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			ret = Builder.CreateSub(c1, c2);
			break;
		}
		case rgd::Mul: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			ret = Builder.CreateMul(c1, c2);
			break;
		}
		case rgd::UDiv: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			llvm::Value* VA0 = llvm::ConstantInt::get(llvm::Type::getIntNTy(Builder.getContext(), node->bits()), 0);
			llvm::Value* VA1 = llvm::ConstantInt::get(llvm::Type::getIntNTy(Builder.getContext(), node->bits()), 1);
			llvm::Value* cond = Builder.CreateICmpEQ(c2,VA0);
			llvm::Value* divisor = Builder.CreateSelect(cond,VA1,c2);
			ret = Builder.CreateUDiv(c1, divisor);
			break;
		}
		case rgd::SDiv: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			llvm::Value* VA0 = llvm::ConstantInt::get(llvm::Type::getIntNTy(Builder.getContext(), node->bits()), 0);
			llvm::Value* VA1 = llvm::ConstantInt::get(llvm::Type::getIntNTy(Builder.getContext(), node->bits()), 1);
			llvm::Value* cond = Builder.CreateICmpEQ(c2,VA0);
			llvm::Value* divisor = Builder.CreateSelect(cond,VA1,c2);
			ret = Builder.CreateSDiv(c1, divisor);
			break;
		}
		case rgd::URem: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			llvm::Value* VA0 = llvm::ConstantInt::get(llvm::Type::getIntNTy(Builder.getContext(), node->bits()), 0);
			llvm::Value* VA1 = llvm::ConstantInt::get(llvm::Type::getIntNTy(Builder.getContext(), node->bits()), 1);
			llvm::Value* cond = Builder.CreateICmpEQ(c2,VA0);
			llvm::Value* divisor = Builder.CreateSelect(cond,VA1,c2);
			ret = Builder.CreateURem(c1, divisor);
			break;
		}
		case rgd::SRem: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			llvm::Value* VA0 = llvm::ConstantInt::get(llvm::Type::getIntNTy(Builder.getContext(), node->bits()), 0);
			llvm::Value* VA1 = llvm::ConstantInt::get(llvm::Type::getIntNTy(Builder.getContext(), node->bits()), 1);
			llvm::Value* cond = Builder.CreateICmpEQ(c2,VA0);
			llvm::Value* divisor = Builder.CreateSelect(cond,VA1,c2);
			ret = Builder.CreateSRem(c1, divisor);
			break;
		}
		case rgd::Neg: {
			const AstNode* rc = &node->children(0);
			llvm::Value* c = codegen(Builder,rc, local_map, arg, value_cache);
			ret = Builder.CreateNeg(c);
			break;
		}
		case rgd::Not: {
			const AstNode* rc = &node->children(0);
			llvm::Value* c = codegen(Builder,rc, local_map, arg, value_cache);
			ret = Builder.CreateNot(c);
			break;
		}
		case rgd::And: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			ret = Builder.CreateAnd(c1, c2);
			break;
		}
		case rgd::Or: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			ret = Builder.CreateOr(c1, c2);
			break;
		}
		case rgd::Xor: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			ret = Builder.CreateXor(c1, c2);
			break;
		}
		case rgd::Shl: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			ret = Builder.CreateShl(c1, c2);
			break;
		}
		case rgd::LShr: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			ret = Builder.CreateLShr(c1, c2);
			break;
		}
		case rgd::AShr: {
			const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			ret = Builder.CreateAShr(c1, c2);
			break;
		}
		// all the following ICmp expressions should be top level
		case rgd::Equal: {
      const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			llvm::Value* c1e = Builder.CreateZExt(c1,llvm::Type::getIntNTy(Builder.getContext(),64));
			llvm::Value* c2e = Builder.CreateZExt(c2,llvm::Type::getIntNTy(Builder.getContext(),64));

			llvm::Value* idx[1];
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),0);
			Builder.CreateStore(c1e, Builder.CreateGEP(arg,idx));
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),1);
			Builder.CreateStore(c2e, Builder.CreateGEP(arg,idx));
			llvm::Value* cond = Builder.CreateICmpUGE(c1e,c2e);
			//(int64_t) 0
			llvm::Value* tv = Builder.CreateSub(c1e,c2e,"equal");
			llvm::Value* fv = Builder.CreateSub(c2e,c1e,"equal");
			ret = Builder.CreateSelect(cond, tv, fv);
			break;
		}
		case rgd::Distinct: {
      const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			llvm::Value* c1e = Builder.CreateZExt(c1,llvm::Type::getIntNTy(Builder.getContext(),64));
			llvm::Value* c2e = Builder.CreateZExt(c2,llvm::Type::getIntNTy(Builder.getContext(),64));

			llvm::Value* idx[1];
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),0);
			Builder.CreateStore(c1e, Builder.CreateGEP(arg,idx));
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),1);
			Builder.CreateStore(c2e, Builder.CreateGEP(arg,idx));

			llvm::Value* cond = Builder.CreateICmpEQ(c1e,c2e);
      llvm::APInt value1(64, 1, false);
      llvm::APInt value0(64, 0, false);
			//(int64_t) 0
      llvm::Value* tv = llvm::ConstantInt::get(Builder.getContext(),value1);
      llvm::Value* fv = llvm::ConstantInt::get(Builder.getContext(),value0);
			ret = Builder.CreateSelect(cond, tv, fv);
			break;
		}
		//for all relation comparison, we extend to 64-bit
		case rgd::Ult: {
      const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			//assert(rc1->bits() != 64 && "64-bit comparison");
			//extend to 64bit
			llvm::Value* c1e = Builder.CreateZExt(c1,llvm::Type::getIntNTy(Builder.getContext(),64));
			llvm::Value* c2e = Builder.CreateZExt(c2,llvm::Type::getIntNTy(Builder.getContext(),64));

			llvm::Value* idx[1];
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),0);
			Builder.CreateStore(c1e, Builder.CreateGEP(arg,idx));
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),1);
			Builder.CreateStore(c2e, Builder.CreateGEP(arg,idx));

			llvm::Value* cond = Builder.CreateICmpULT(c1e,c2e);
			//(int64_t) 0
			llvm::APInt value(64, 0, true);
			llvm::APInt value1(64, 1, true);
			llvm::Value* tv = llvm::ConstantInt::get(Builder.getContext(), value);
			llvm::Value* fv = Builder.CreateAdd(Builder.CreateSub(c1e, c2e, "Ult"), 
					llvm::ConstantInt::get(Builder.getContext(),value1));
			ret = Builder.CreateSelect(cond, tv, fv);
			break;
		}
		case rgd::Ule: {
      const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);

			llvm::Value* c1e = Builder.CreateZExt(c1,llvm::Type::getIntNTy(Builder.getContext(),64));
			llvm::Value* c2e = Builder.CreateZExt(c2,llvm::Type::getIntNTy(Builder.getContext(),64));
			llvm::Value* cond = Builder.CreateICmpULE(c1e,c2e);

			llvm::Value* idx[1];
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),0);
			Builder.CreateStore(c1e, Builder.CreateGEP(arg,idx));
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),1);
			Builder.CreateStore(c2e, Builder.CreateGEP(arg,idx));

			llvm::APInt value(64, 0, true);
			llvm::Value* tv = llvm::ConstantInt::get(Builder.getContext(), value);
			llvm::Value* fv = Builder.CreateSub(c1e, c2e, "Ule");
			ret = Builder.CreateSelect(cond, tv, fv);
			break;
		}
		case rgd::Ugt: {
      const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);

			llvm::Value* c1e = Builder.CreateZExt(c1,llvm::Type::getIntNTy(Builder.getContext(),64));
			llvm::Value* c2e = Builder.CreateZExt(c2,llvm::Type::getIntNTy(Builder.getContext(),64));
			llvm::Value* cond = Builder.CreateICmpUGT(c1e,c2e);

			llvm::Value* idx[1];
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),0);
			Builder.CreateStore(c1e, Builder.CreateGEP(arg,idx));
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),1);
			Builder.CreateStore(c2e, Builder.CreateGEP(arg,idx));

			llvm::APInt value(64, 0, true);
			llvm::APInt value1(64, 1, true);
			llvm::Value* tv = llvm::ConstantInt::get(Builder.getContext(), value);
			llvm::Value* fv = Builder.CreateAdd(Builder.CreateSub(c2e, c1e, "Ugt"), 
					llvm::ConstantInt::get(Builder.getContext(),value1));
			ret = Builder.CreateSelect(cond, tv, fv);
			break;
		}
		case rgd::Uge: {
      const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);

			llvm::Value* c1e = Builder.CreateZExt(c1,llvm::Type::getIntNTy(Builder.getContext(),64));
			llvm::Value* c2e = Builder.CreateZExt(c2,llvm::Type::getIntNTy(Builder.getContext(),64));

			llvm::Value* idx[1];
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),0);
			Builder.CreateStore(c1e, Builder.CreateGEP(arg,idx));
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),1);
			Builder.CreateStore(c2e, Builder.CreateGEP(arg,idx));
			llvm::Value* cond = Builder.CreateICmpUGE(c1e,c2e);

			llvm::APInt value(64, 0, true);
			llvm::Value* tv = llvm::ConstantInt::get(Builder.getContext(), value);
			llvm::Value* fv = Builder.CreateSub(c2e, c1e, "Uge");
			ret = Builder.CreateSelect(cond, tv, fv);
			break;
		}
		case rgd::Slt: {
      const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);

			llvm::Value* c1e = Builder.CreateSExt(c1,llvm::Type::getIntNTy(Builder.getContext(),64));
			llvm::Value* c2e = Builder.CreateSExt(c2,llvm::Type::getIntNTy(Builder.getContext(),64));

			llvm::Value* idx[1];
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),0);
			Builder.CreateStore(c1e, Builder.CreateGEP(arg,idx));
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),1);
			Builder.CreateStore(c2e, Builder.CreateGEP(arg,idx));

			llvm::Value* cond = Builder.CreateICmpSLT(c1e,c2e);
			//(int64_t) 0
			llvm::APInt value(64, 0, true);
			llvm::APInt value1(64, 1, true);
			llvm::Value* tv = llvm::ConstantInt::get(Builder.getContext(), value);
			llvm::Value* fv = Builder.CreateAdd(Builder.CreateSub(c1e, c2e, "Slt"), 
					llvm::ConstantInt::get(Builder.getContext(),value1));
			ret = Builder.CreateSelect(cond, tv, fv);
			break;
		}
		case rgd::Sle: {
      const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			//assert(rc1->bits() != 64 && "64-bit comparison");
			//extend to 64bit
			llvm::Value* c1e = Builder.CreateSExt(c1,llvm::Type::getIntNTy(Builder.getContext(),64));
			llvm::Value* c2e = Builder.CreateSExt(c2,llvm::Type::getIntNTy(Builder.getContext(),64));

			llvm::Value* idx[1];
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),0);
			Builder.CreateStore(c1e, Builder.CreateGEP(arg,idx));
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),1);
			Builder.CreateStore(c2e, Builder.CreateGEP(arg,idx));

			llvm::Value* cond = Builder.CreateICmpSLE(c1e,c2e);
			//(int64_t) 0
			llvm::APInt value(64, 0, true);
			llvm::Value* tv = llvm::ConstantInt::get(Builder.getContext(), value);
			llvm::Value* fv = Builder.CreateSub(c1e, c2e, "Sle");
			ret = Builder.CreateSelect(cond, tv, fv);
			break;
		}
		case rgd::Sgt: {
      const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);

			llvm::Value* c1e = Builder.CreateSExt(c1,llvm::Type::getIntNTy(Builder.getContext(),64));
			llvm::Value* c2e = Builder.CreateSExt(c2,llvm::Type::getIntNTy(Builder.getContext(),64));

			llvm::Value* idx[1];
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),0);
			Builder.CreateStore(c1e, Builder.CreateGEP(arg,idx));
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),1);
			Builder.CreateStore(c2e, Builder.CreateGEP(arg,idx));
			llvm::Value* cond = Builder.CreateICmpSGT(c1e,c2e);
			//(int64_t) 0
			llvm::APInt value(64, 0, true);
			llvm::APInt value1(64, 1, true);
			llvm::Value* tv = llvm::ConstantInt::get(Builder.getContext(), value);
			llvm::Value* fv = Builder.CreateAdd(Builder.CreateSub(c2e, c1e, "Sgt"), 
					llvm::ConstantInt::get(Builder.getContext(),value1));
			ret = Builder.CreateSelect(cond, tv, fv);
			break;
		}
		case rgd::Sge: {
      const AstNode* rc1 = &node->children(0);
			const AstNode* rc2 = &node->children(1);
			llvm::Value* c1 = codegen(Builder,rc1, local_map, arg, value_cache);
			llvm::Value* c2 = codegen(Builder,rc2, local_map, arg, value_cache);
			llvm::Value* c1e = Builder.CreateSExt(c1,llvm::Type::getIntNTy(Builder.getContext(),64));
			llvm::Value* c2e = Builder.CreateSExt(c2,llvm::Type::getIntNTy(Builder.getContext(),64));

			llvm::Value* idx[1];
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),0);
			Builder.CreateStore(c1e, Builder.CreateGEP(arg,idx));
			idx[0]= llvm::ConstantInt::get(Builder.getInt32Ty(),1);
			Builder.CreateStore(c2e, Builder.CreateGEP(arg,idx));

			llvm::Value* cond = Builder.CreateICmpSGE(c1e,c2e);
			llvm::APInt value(64, 0, true);
			llvm::Value* tv = llvm::ConstantInt::get(Builder.getContext(), value);
			llvm::Value* fv = Builder.CreateSub(c2e, c1e, "Sge");
			ret = Builder.CreateSelect(cond, tv, fv);
			break;
		}
		// this should never happen!
		case rgd::LOr: {
			assert(false && "LOr expression");
			break;
		}
		case rgd::LAnd: {
			assert(false && "LAnd expression");
			break;
		}
		case rgd::LNot: {
			assert(false && "LNot expression");
			break;
		}
		case rgd::Ite: {
			assert(false && "ITE expression");
			break;
			// don't handle ITE for now, doesn't work with GD
#if DEUBG
			std::cerr << "ITE expr codegen" << std::endl;
#endif
#if 0
			const AstNode* rcond = &node->children(0);
			const AstNode* rtv = &node->children(1);
			const AstNode* rfv = &node->children(2);
			llvm::Value* cond = codegen(rcond, local_map, arg, value_cache);
			llvm::Value* tv = codegen(rtv, local_map, arg, value_cache);
			llvm::Value* fv = codegen(rfv, local_map, arg, value_cache);
			ret = Builder.CreateSelect(cond, tv, fv);
#endif
			break;}
		default:
			std::cerr << "WARNING: unhandled expr: ";
			printNode(node);
			break;
	}

	if (ret && node->label()!=0) {
		value_cache.insert({node->label(), ret});
	}

	return ret; 
}

int addFunction(const AstNode* request,
		std::unordered_map<uint32_t,uint32_t> &local_map,
    uint64_t id ) {

	// Open a new module.
	std::string moduleName = "rgdjit_m" + std::to_string(id);
  std::string funcName = "rgdjit" + std::to_string(id);


	auto TheCtx = llvm::make_unique<llvm::LLVMContext>();
	auto TheModule = llvm::make_unique<Module>(moduleName, *TheCtx);
	TheModule->setDataLayout(JIT->getDataLayout());
	llvm::IRBuilder<> Builder(*TheCtx);


	std::vector<llvm::Type*> input_type(1,
			llvm::PointerType::getUnqual(Builder.getInt64Ty()));
	llvm::FunctionType *funcType;
	funcType = llvm::FunctionType::get(Builder.getInt64Ty(), input_type, false);
	auto *fooFunc = llvm::Function::Create(funcType, llvm::Function::ExternalLinkage,
			funcName, TheModule.get());
	auto *po = llvm::BasicBlock::Create(Builder.getContext(), "entry", fooFunc);
	Builder.SetInsertPoint(po);
	uint32_t idx = 0;

	auto args = fooFunc->arg_begin();
	llvm::Value* var = &(*args);
	std::unordered_map<uint32_t, llvm::Value*> value_cache;
	auto *body = codegen(Builder, request, local_map, var, value_cache);
	Builder.CreateRet(body);


	llvm::raw_ostream *stream = &llvm::outs();
	llvm::verifyFunction(*fooFunc, stream);
#if 1
	//	TheModule->print(llvm::errs(),nullptr);
#endif

	JIT->addModule(std::move(TheModule),std::move(TheCtx));

	return 0;
}


test_fn_type performJit(uint64_t id) {
  std::string funcName = "rgdjit" + std::to_string(id);
  auto ExprSymbol = JIT->lookup(funcName).get();
  auto func = (uint64_t(*)(uint64_t*))ExprSymbol.getAddress();
  return func;
}

