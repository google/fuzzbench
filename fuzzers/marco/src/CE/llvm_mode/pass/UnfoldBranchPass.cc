/*
  Make optimization fail for branches
  e.g
  if (x == 1 & y == 1) {}
  =>
  if (x==1) {
    if (y == 1) {}
  }
 */

#include "debug.h"
#include "./version.h"

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include "llvm/ADT/SmallSet.h"
#include "llvm/ADT/Statistic.h"
#include "llvm/IR/DebugInfo.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/IntrinsicInst.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/IR/Module.h"
#include "llvm/Support/Debug.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"
using namespace llvm;

namespace {

class UnfoldBranch : public FunctionPass {
private:
  Type *VoidTy;
  IntegerType *Int8Ty;
  IntegerType *Int32Ty;

  Constant *UnfoldBranchFn;

public:
  static char ID;

  UnfoldBranch() : FunctionPass(ID) {}

  bool doInitialization(Module &M) override;
  bool doFinalization(Module &M) override;
  bool runOnFunction(Function &F) override;
};

} // namespace

char UnfoldBranch::ID = 0;

bool UnfoldBranch::doInitialization(Module &M) {

  LLVMContext &C = M.getContext();

  Int8Ty = IntegerType::getInt8Ty(C);
  Int32Ty = IntegerType::getInt32Ty(C);
  VoidTy = Type::getVoidTy(C);

  srandom(1851655);

  Type *FnArgs[1] = {Int32Ty};
  FunctionType *FnTy = FunctionType::get(VoidTy, FnArgs, /*isVarArg=*/false);
  UnfoldBranchFn = M.getOrInsertFunction("__unfold_branch_fn", FnTy);

  if (Function *F = dyn_cast<Function>(UnfoldBranchFn)) {
    F->addAttribute(LLVM_ATTRIBUTE_LIST::FunctionIndex, Attribute::NoUnwind);
  }
  return true;
}

bool UnfoldBranch::doFinalization(Module &M) { return true; }

bool UnfoldBranch::runOnFunction(Function &F) {

  // if the function is declaration, ignore
  if (F.isDeclaration())
    return false;

#ifndef ENABLE_UNFOLD_BRANCH
  return false;
#endif

  SmallSet<BasicBlock *, 20> VisitedBB;
  LLVMContext &C = F.getContext();
  for (auto &BB : F) {

    Instruction *Inst = BB.getTerminator();
    if (isa<BranchInst>(Inst)) {

      BranchInst *BI = dyn_cast<BranchInst>(Inst);

      if (BI->isUnconditional() || BI->getNumSuccessors() < 2)
        continue;

      Value *Cond = BI->getCondition();
      if (!Cond)
        continue;

      for (unsigned int i = 0; i < BI->getNumSuccessors(); i++) {
        BasicBlock *B0 = BI->getSuccessor(i);
        if (B0 && VisitedBB.count(B0) == 0) {
          VisitedBB.insert(B0);
          BasicBlock::iterator IP = B0->getFirstInsertionPt();
          IRBuilder<> IRB(&(*IP));
          unsigned int cur_loc = RRR(1048576);
          CallInst *Call = IRB.CreateCall(UnfoldBranchFn,
                                          {ConstantInt::get(Int32Ty, cur_loc)});
          Call->setMetadata(C.getMDKindID("unfold"), MDNode::get(C, None));
        }
      }
    }
  }

  return true;
}

static void registerUnfoldBranchPass(const PassManagerBuilder &,
                                     legacy::PassManagerBase &PM) {

  PM.add(new UnfoldBranch());
}

static RegisterPass<UnfoldBranch> X("unfold_branch_pass", "Unfold Branch Pass");

static RegisterStandardPasses
    RegisterAFLPass(PassManagerBuilder::EP_EarlyAsPossible,
                    registerUnfoldBranchPass);

/*
static RegisterStandardPasses RegisterAFLPass0(
    PassManagerBuilder::EP_EnabledOnOptLevel0, registerAFLPass);
*/
