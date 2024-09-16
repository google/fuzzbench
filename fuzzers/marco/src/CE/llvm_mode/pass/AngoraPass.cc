#include "llvm/ADT/DenseSet.h"
#include "llvm/ADT/SmallPtrSet.h"
#include "llvm/ADT/Statistic.h"
#include "llvm/Analysis/ValueTracking.h"
#include "llvm/IR/DebugInfo.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/IR/MDBuilder.h"
#include "llvm/IR/Module.h"
#include "llvm/Support/Debug.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include <fstream>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include "./abilist.h"
#include "./defs.h"
#include "./debug.h"
#include "./version.h"

using namespace llvm;
// only do taint tracking, used for compile 3rd libraries.
static cl::opt<bool> DFSanMode("DFSanMode", cl::desc("dfsan mode"), cl::Hidden);

static cl::opt<bool> TrackMode("TrackMode", cl::desc("track mode"), cl::Hidden);

static cl::list<std::string> ClABIListFiles(
    "angora-dfsan-abilist",
    cl::desc("file listing native abi functions and how the pass treats them"),
    cl::Hidden);

static cl::list<std::string> ClExploitListFiles(
    "angora-exploitation-list",
    cl::desc("file listing functions and instructions to exploit"), cl::Hidden);

namespace {

#define MAX_EXPLOIT_CATEGORY 5
const char *ExploitCategoryAll = "all";
const char *ExploitCategory[] = {"i0", "i1", "i2", "i3", "i4"};
const char *CompareFuncCat = "cmpfn";

// hash file name and file size
u32 hashName(std::string str) {
  std::ifstream in(str, std::ifstream::ate | std::ifstream::binary);
  u32 fsize = in.tellg();
  u32 hash = 5381 + fsize * 223;
  for (auto c : str)
    hash = ((hash << 5) + hash) + (unsigned char)c; /* hash * 33 + c */
  return hash;
}

class AngoraLLVMPass : public ModulePass {
public:
  static char ID;
  bool FastMode = false;
  std::string ModName;
  u32 ModId;
  u32 CidCounter;
  unsigned long int RandSeed = 1;
  bool is_bc;
  unsigned int inst_ratio = 100;

  // Const Variables
  DenseSet<u32> UniqCidSet;

  // Configurations
  bool gen_id_random;
  bool output_cond_loc;
  int num_fn_ctx;

  MDNode *ColdCallWeights;

  // Types
  Type *VoidTy;
  IntegerType *Int1Ty;
  IntegerType *Int8Ty;
  IntegerType *Int16Ty;
  IntegerType *Int32Ty;
  IntegerType *Int64Ty;
  Type *Int8PtrTy;
  Type *Int64PtrTy;

  // Global vars
  GlobalVariable *AngoraMapPtr;
  GlobalVariable *AngoraPrevLoc;
  GlobalVariable *AngoraContext;
  GlobalVariable *AngoraCondId;
  GlobalVariable *AngoraCallSite;

  Constant *TraceCmp;
  Constant *TraceSw;
  Constant *TraceCmpTT;
  Constant *TraceSwTT;
  Constant *TraceFnTT;
  Constant *TraceExploitTT;

  FunctionType *TraceCmpTy;
  FunctionType *TraceSwTy;
  FunctionType *TraceCmpTtTy;
  FunctionType *TraceSwTtTy;
  FunctionType *TraceFnTtTy;
  FunctionType *TraceExploitTtTy;

  // Custom setting
  AngoraABIList ABIList;
  AngoraABIList ExploitList;

  // Meta
  unsigned NoSanMetaId;
  MDTuple *NoneMetaNode;

  AngoraLLVMPass() : ModulePass(ID) {}
  bool runOnModule(Module &M) override;
  u32 getInstructionId(Instruction *Inst);
  u32 getRandomBasicBlockId();
  bool skipBasicBlock();
  u32 getRandomNum();
  void setRandomNumSeed(u32 seed);
  u32 getRandomContextId();
  u32 getRandomInstructionId();
  void setValueNonSan(Value *v);
  void setInsNonSan(Instruction *v);
  Value *castArgType(IRBuilder<> &IRB, Value *V);
  void initVariables(Module &M);
  void countEdge(Module &M, BasicBlock &BB);
  void visitCallInst(Instruction *Inst);
  void visitInvokeInst(Instruction *Inst);
  void visitCompareFunc(Instruction *Inst);
  void visitBranchInst(Instruction *Inst);
  void visitCmpInst(Instruction *Inst);
  void processCmp(Instruction *Cond, Constant *Cid, Instruction *InsertPoint);
  void processBoolCmp(Value *Cond, Constant *Cid, Instruction *InsertPoint);
  void visitSwitchInst(Module &M, Instruction *Inst);
  void visitExploitation(Instruction *Inst);
  void processCall(Instruction *Inst);
  void addFnWrap(Function &F);
};

} // namespace

char AngoraLLVMPass::ID = 0;

u32 AngoraLLVMPass::getRandomBasicBlockId() { return random() % MAP_SIZE; }

bool AngoraLLVMPass::skipBasicBlock() { return (random() % 100) >= inst_ratio; }

// http://pubs.opengroup.org/onlinepubs/009695399/functions/rand.html
u32 AngoraLLVMPass::getRandomNum() {
  RandSeed = RandSeed * 1103515245 + 12345;
  return (u32)RandSeed;
}

void AngoraLLVMPass::setRandomNumSeed(u32 seed) { RandSeed = seed; }

u32 AngoraLLVMPass::getRandomContextId() {
  u32 context = getRandomNum() % MAP_SIZE;
  if (output_cond_loc) {
    errs() << "[CONTEXT] " << context << "\n";
  }
  return context;
}

u32 AngoraLLVMPass::getRandomInstructionId() { return getRandomNum(); }

u32 AngoraLLVMPass::getInstructionId(Instruction *Inst) {
  u32 h = 0;
  if (is_bc) {
    h = ++CidCounter;
  } else {
    if (gen_id_random) {
      h = getRandomInstructionId();
    } else {
      DILocation *Loc = Inst->getDebugLoc();
      if (Loc) {
        u32 Line = Loc->getLine();
        u32 Col = Loc->getColumn();
        h = (Col * 33 + Line) * 33 + ModId;
      } else {
        h = getRandomInstructionId();
      }
    }

    while (UniqCidSet.count(h) > 0) {
      h = h * 3 + 1;
    }
    UniqCidSet.insert(h);
  }

  if (output_cond_loc) {
    errs() << "[ID] " << h << "\n";
    errs() << "[INS] " << *Inst << "\n";
    if (DILocation *Loc = Inst->getDebugLoc()) {
      errs() << "[LOC] " << cast<DIScope>(Loc->getScope())->getFilename()
             << ", Ln " << Loc->getLine() << ", Col " << Loc->getColumn()
             << "\n";
    }
  }

  return h;
}

void AngoraLLVMPass::setValueNonSan(Value *v) {
  if (Instruction *ins = dyn_cast<Instruction>(v))
    setInsNonSan(ins);
}

void AngoraLLVMPass::setInsNonSan(Instruction *ins) {
  if (ins)
    ins->setMetadata(NoSanMetaId, NoneMetaNode);
}

void AngoraLLVMPass::initVariables(Module &M) {
  // To ensure different version binaries have the same id
  ModName = M.getModuleIdentifier();
  if (ModName.size() == 0)
    FATAL("No ModName!\n");
  ModId = hashName(ModName);
  errs() << "ModName: " << ModName << " -- " << ModId << "\n";
  is_bc = 0 == ModName.compare(ModName.length() - 3, 3, ".bc");
  if (is_bc) {
    errs() << "Input is LLVM bitcode\n";
  }

  char* inst_ratio_str = getenv("ANGORA_INST_RATIO");
  if (inst_ratio_str) {
    if (sscanf(inst_ratio_str, "%u", &inst_ratio) != 1 || !inst_ratio ||
        inst_ratio > 100)
      FATAL("Bad value of ANGORA_INST_RATIO (must be between 1 and 100)");
  }
  errs() << "inst_ratio: " << inst_ratio << "\n";

  // set seed
  srandom(ModId);
  setRandomNumSeed(ModId);
  CidCounter = 0;

  LLVMContext &C = M.getContext();
  VoidTy = Type::getVoidTy(C);
  Int1Ty = IntegerType::getInt1Ty(C);
  Int8Ty = IntegerType::getInt8Ty(C);
  Int32Ty = IntegerType::getInt32Ty(C);
  Int64Ty = IntegerType::getInt64Ty(C);
  Int8PtrTy = PointerType::getUnqual(Int8Ty);
  Int64PtrTy = PointerType::getUnqual(Int64Ty);

  ColdCallWeights = MDBuilder(C).createBranchWeights(1, 1000);

  NoSanMetaId = C.getMDKindID("nosanitize");
  NoneMetaNode = MDNode::get(C, None);

  AngoraContext =
      new GlobalVariable(M, Int32Ty, false, GlobalValue::CommonLinkage,
                         ConstantInt::get(Int32Ty, 0), "__angora_context", 0,
                         GlobalVariable::GeneralDynamicTLSModel, 0, false);

  AngoraCallSite = new GlobalVariable(
      M, Int32Ty, false, GlobalValue::CommonLinkage, 
      ConstantInt::get(Int32Ty, 0), "__angora_call_site", 0, 
      GlobalVariable::GeneralDynamicTLSModel, 0, false);

  if (FastMode) {
    AngoraMapPtr = new GlobalVariable(M, PointerType::get(Int8Ty, 0), false,
                                      GlobalValue::ExternalLinkage, 0,
                                      "__angora_area_ptr");

    AngoraCondId =
        new GlobalVariable(M, Int32Ty, false, GlobalValue::ExternalLinkage, 0,
                           "__angora_cond_cmpid");

    AngoraPrevLoc =
        new GlobalVariable(M, Int32Ty, false, GlobalValue::CommonLinkage,
                           ConstantInt::get(Int32Ty, 0), "__angora_prev_loc", 0,
                           GlobalVariable::GeneralDynamicTLSModel, 0, false);

    Type *TraceCmpArgs[5] = {Int32Ty, Int32Ty, Int32Ty, Int64Ty, Int64Ty};
    TraceCmpTy = FunctionType::get(Int32Ty, TraceCmpArgs, false);
    TraceCmp = M.getOrInsertFunction("__angora_trace_cmp", TraceCmpTy);
    if (Function *F = dyn_cast<Function>(TraceCmp)) {
      F->addAttribute(LLVM_ATTRIBUTE_LIST::FunctionIndex, Attribute::NoUnwind);
      F->addAttribute(LLVM_ATTRIBUTE_LIST::FunctionIndex, Attribute::ReadNone);
      // F->addAttribute(1, Attribute::ZExt);
    }

    Type *TraceSwArgs[3] = {Int32Ty, Int32Ty, Int64Ty};
    TraceSwTy = FunctionType::get(Int64Ty, TraceSwArgs, false);
    TraceSw = M.getOrInsertFunction("__angora_trace_switch", TraceSwTy);
    if (Function *F = dyn_cast<Function>(TraceSw)) {
      F->addAttribute(LLVM_ATTRIBUTE_LIST::FunctionIndex, Attribute::NoUnwind);
      F->addAttribute(LLVM_ATTRIBUTE_LIST::FunctionIndex, Attribute::ReadNone);
      // F->addAttribute(LLVM_ATTRIBUTE_LIST::ReturnIndex, Attribute::ZExt);
      // F->addAttribute(1, Attribute::ZExt);
    }

  } else if (TrackMode) {
    Type *TraceCmpTtArgs[7] = {Int32Ty, Int32Ty, Int32Ty, Int32Ty,
                               Int64Ty, Int64Ty, Int32Ty};
    TraceCmpTtTy = FunctionType::get(VoidTy, TraceCmpTtArgs, false);
    TraceCmpTT = M.getOrInsertFunction("__angora_trace_cmp_tt", TraceCmpTtTy);
    if (Function *F = dyn_cast<Function>(TraceCmpTT)) {
      F->addAttribute(LLVM_ATTRIBUTE_LIST::FunctionIndex, Attribute::NoUnwind);
      F->addAttribute(LLVM_ATTRIBUTE_LIST::FunctionIndex, Attribute::ReadNone);
    }

    Type *TraceSwTtArgs[6] = {Int32Ty, Int32Ty, Int32Ty,
                              Int64Ty, Int32Ty, Int64PtrTy};
    TraceSwTtTy = FunctionType::get(VoidTy, TraceSwTtArgs, false);
    TraceSwTT = M.getOrInsertFunction("__angora_trace_switch_tt", TraceSwTtTy);
    if (Function *F = dyn_cast<Function>(TraceSwTT)) {
      F->addAttribute(LLVM_ATTRIBUTE_LIST::FunctionIndex, Attribute::NoUnwind);
      F->addAttribute(LLVM_ATTRIBUTE_LIST::FunctionIndex, Attribute::ReadNone);
    }

    Type *TraceFnTtArgs[5] = {Int32Ty, Int32Ty, Int32Ty, Int8PtrTy, Int8PtrTy};
    TraceFnTtTy = FunctionType::get(VoidTy, TraceFnTtArgs, false);
    TraceFnTT = M.getOrInsertFunction("__angora_trace_fn_tt", TraceFnTtTy);
    if (Function *F = dyn_cast<Function>(TraceFnTT)) {
      F->addAttribute(LLVM_ATTRIBUTE_LIST::FunctionIndex, Attribute::NoUnwind);
      F->addAttribute(LLVM_ATTRIBUTE_LIST::FunctionIndex, Attribute::ReadOnly);
    }

    Type *TraceExploitTtArgs[5] = {Int32Ty, Int32Ty, Int32Ty, Int32Ty, Int64Ty};
    TraceExploitTtTy = FunctionType::get(VoidTy, TraceExploitTtArgs, false);
    TraceExploitTT = M.getOrInsertFunction("__angora_trace_exploit_val_tt",
                                           TraceExploitTtTy);
    if (Function *F = dyn_cast<Function>(TraceExploitTT)) {
      F->addAttribute(LLVM_ATTRIBUTE_LIST::FunctionIndex, Attribute::NoUnwind);
      F->addAttribute(LLVM_ATTRIBUTE_LIST::FunctionIndex, Attribute::ReadNone);
    }
  }

  std::vector<std::string> AllABIListFiles;
  AllABIListFiles.insert(AllABIListFiles.end(), ClABIListFiles.begin(),
                         ClABIListFiles.end());
  ABIList.set(SpecialCaseList::createOrDie(AllABIListFiles));

  std::vector<std::string> AllExploitListFiles;
  AllExploitListFiles.insert(AllExploitListFiles.end(),
                             ClExploitListFiles.begin(),
                             ClExploitListFiles.end());
  ExploitList.set(SpecialCaseList::createOrDie(AllExploitListFiles));

  gen_id_random = !!getenv(GEN_ID_RANDOM_VAR);
  output_cond_loc = !!getenv(OUTPUT_COND_LOC_VAR);

  num_fn_ctx = -1;
  char* custom_fn_ctx = getenv(CUSTOM_FN_CTX);
  if (custom_fn_ctx) {
    num_fn_ctx = atoi(custom_fn_ctx);
    if (num_fn_ctx < 0 || num_fn_ctx >= 32) {
      errs() << "custom context should be: >= 0 && < 32 \n"; 
      exit(1);
    }
  }

  if (num_fn_ctx == 0) {
    errs() << "disable context\n";
  } 

  if (num_fn_ctx > 0) {
    errs() << "use custom function call context: " << num_fn_ctx << "\n";
  }

  if (gen_id_random) {
    errs() << "generate id randomly\n";
  }

  if (output_cond_loc) {
    errs() << "Output cond log\n";
  }
};

// Coverage statistics: AFL's Branch count
// Angora enable function-call context.
void AngoraLLVMPass::countEdge(Module &M, BasicBlock &BB) {
  if (!FastMode || skipBasicBlock())
    return;
  
  // LLVMContext &C = M.getContext();
  unsigned int cur_loc = getRandomBasicBlockId();
  ConstantInt *CurLoc = ConstantInt::get(Int32Ty, cur_loc);

  BasicBlock::iterator IP = BB.getFirstInsertionPt();
  IRBuilder<> IRB(&(*IP));

  LoadInst *PrevLoc = IRB.CreateLoad(AngoraPrevLoc);
  setInsNonSan(PrevLoc);

  Value *PrevLocCasted = IRB.CreateZExt(PrevLoc, Int32Ty);
  setValueNonSan(PrevLocCasted);

  // Get Map[idx]
  LoadInst *MapPtr = IRB.CreateLoad(AngoraMapPtr);
  setInsNonSan(MapPtr);

  Value *BrId = IRB.CreateXor(PrevLocCasted, CurLoc);
  setValueNonSan(BrId);
  Value *MapPtrIdx = IRB.CreateGEP(MapPtr, BrId);
  setValueNonSan(MapPtrIdx);

  // Increase 1 : IncRet <- Map[idx] + 1
  LoadInst *Counter = IRB.CreateLoad(MapPtrIdx);
  setInsNonSan(Counter);

  // Implementation of saturating counter.
  // Value *CmpOF = IRB.CreateICmpNE(Counter, ConstantInt::get(Int8Ty, -1));
  // setValueNonSan(CmpOF);
  // Value *IncVal = IRB.CreateZExt(CmpOF, Int8Ty);
  // setValueNonSan(IncVal);
  // Value *IncRet = IRB.CreateAdd(Counter, IncVal);
  // setValueNonSan(IncRet);

  // Implementation of Never-zero counter
  // The idea is from Marc and Heiko in AFLPlusPlus
  // Reference: : https://github.com/vanhauser-thc/AFLplusplus/blob/master/llvm_mode/README.neverzero and https://github.com/vanhauser-thc/AFLplusplus/issues/10
    
  Value *IncRet = IRB.CreateAdd(Counter, ConstantInt::get(Int8Ty, 1));
  setValueNonSan(IncRet);
  Value *IsZero = IRB.CreateICmpEQ(IncRet, ConstantInt::get(Int8Ty, 0));
  setValueNonSan(IsZero);
  Value *IncVal = IRB.CreateZExt(IsZero, Int8Ty);
  setValueNonSan(IncVal);
  IncRet = IRB.CreateAdd(IncRet, IncVal);
  setValueNonSan(IncRet);

  // Store Back Map[idx]
  IRB.CreateStore(IncRet, MapPtrIdx)->setMetadata(NoSanMetaId, NoneMetaNode);

  Value *NewPrevLoc = NULL;
  if (num_fn_ctx != 0) { // Call-based context
    // Load ctx
    LoadInst *CtxVal = IRB.CreateLoad(AngoraContext);
    setInsNonSan(CtxVal);

    Value *CtxValCasted = IRB.CreateZExt(CtxVal, Int32Ty);
    setValueNonSan(CtxValCasted);
    // Udate PrevLoc
    NewPrevLoc =
        IRB.CreateXor(CtxValCasted, ConstantInt::get(Int32Ty, cur_loc >> 1));
  } else { // disable context
    NewPrevLoc = ConstantInt::get(Int32Ty, cur_loc >> 1);
  }
  setValueNonSan(NewPrevLoc);

  StoreInst *Store = IRB.CreateStore(NewPrevLoc, AngoraPrevLoc);
  setInsNonSan(Store);
};


void AngoraLLVMPass::addFnWrap(Function &F) {

  if (num_fn_ctx == 0) return;

  // *** Pre Fn ***
  BasicBlock *BB = &F.getEntryBlock();
  Instruction *InsertPoint = &(*(BB->getFirstInsertionPt()));
  IRBuilder<> IRB(InsertPoint);

  Value *CallSite = IRB.CreateLoad(AngoraCallSite);
  setValueNonSan(CallSite);

  Value *OriCtxVal =IRB.CreateLoad(AngoraContext);
  setValueNonSan(OriCtxVal);

  // ***** Add Context *****
  // instrument code before and after each function call to add context
  // We did `xor` simply.
  // This can avoid recursion. The effect of call in recursion will be removed
  // by `xor` with the same value
  // Implementation of function context for AFL by heiko eissfeldt:
  // https://github.com/vanhauser-thc/afl-patches/blob/master/afl-fuzz-context_sensitive.diff
  if (num_fn_ctx > 0) {
    OriCtxVal = IRB.CreateLShr(OriCtxVal, 32 / num_fn_ctx);
    setValueNonSan(OriCtxVal);
  }

  Value *UpdatedCtx = IRB.CreateXor(OriCtxVal, CallSite);
  setValueNonSan(UpdatedCtx);

  StoreInst *SaveCtx = IRB.CreateStore(UpdatedCtx, AngoraContext);
  setInsNonSan(SaveCtx);


  // *** Post Fn ***
  for (auto bb = F.begin(); bb != F.end(); bb++) {
    BasicBlock *BB = &(*bb);
    Instruction *Inst = BB->getTerminator();
    if (isa<ReturnInst>(Inst) || isa<ResumeInst>(Inst)) {
      // ***** Reload Context *****
      IRBuilder<> Post_IRB(Inst);
      Post_IRB.CreateStore(OriCtxVal, AngoraContext)
           ->setMetadata(NoSanMetaId, NoneMetaNode);
    }
  }
}

void AngoraLLVMPass::processCall(Instruction *Inst) {
  
  visitCompareFunc(Inst);
  visitExploitation(Inst);

  //  if (ABIList.isIn(*Callee, "uninstrumented"))
  //  return;
  if (num_fn_ctx != 0) {
    IRBuilder<> IRB(Inst);
    Constant* CallSite = ConstantInt::get(Int32Ty, getRandomContextId());
    IRB.CreateStore(CallSite, AngoraCallSite)->setMetadata(NoSanMetaId, NoneMetaNode);
  }
}

void AngoraLLVMPass::visitCallInst(Instruction *Inst) {

  CallInst *Caller = dyn_cast<CallInst>(Inst);
  Function *Callee = Caller->getCalledFunction();

  if (!Callee || Callee->isIntrinsic() || isa<InlineAsm>(Caller->getCalledValue())) {
    return;
  }

  // remove inserted "unfold" functions
  if (!Callee->getName().compare(StringRef("__unfold_branch_fn"))) {
    if (Caller->use_empty()) {
      Caller->eraseFromParent();
    }
    return;
  }

  processCall(Inst);
};

void AngoraLLVMPass::visitInvokeInst(Instruction *Inst) {

  InvokeInst *Caller = dyn_cast<InvokeInst>(Inst);
  Function *Callee = Caller->getCalledFunction();

  if (!Callee || Callee->isIntrinsic() ||
      isa<InlineAsm>(Caller->getCalledValue())) {
    return;
  }

  processCall(Inst);
}

void AngoraLLVMPass::visitCompareFunc(Instruction *Inst) {
  // configuration file: custom/exploitation_list.txt  fun:xx=cmpfn

  if (!isa<CallInst>(Inst) || !ExploitList.isIn(*Inst, CompareFuncCat)) {
    return;
  }
  ConstantInt *Cid = ConstantInt::get(Int32Ty, getInstructionId(Inst));

  if (!TrackMode)
    return;

  CallInst *Caller = dyn_cast<CallInst>(Inst);
  Value *OpArg[2];
  OpArg[0] = Caller->getArgOperand(0);
  OpArg[1] = Caller->getArgOperand(1);

  if (!OpArg[0]->getType()->isPointerTy() ||
      !OpArg[1]->getType()->isPointerTy()) {
    return;
  }

  Value *ArgSize = nullptr;
  if (Caller->getNumArgOperands() > 2) {
    ArgSize = Caller->getArgOperand(2); // int32ty
  } else {
    ArgSize = ConstantInt::get(Int32Ty, 0);
  }

  IRBuilder<> IRB(Inst);
  LoadInst *CurCtx = IRB.CreateLoad(AngoraContext);
  setInsNonSan(CurCtx);
  CallInst *ProxyCall =
      IRB.CreateCall(TraceFnTT, {Cid, CurCtx, ArgSize, OpArg[0], OpArg[1]});
  setInsNonSan(ProxyCall);
}

Value *AngoraLLVMPass::castArgType(IRBuilder<> &IRB, Value *V) {
  Type *OpType = V->getType();
  Value *NV = V;
  if (OpType->isFloatTy()) {
    NV = IRB.CreateFPToUI(V, Int32Ty);
    setValueNonSan(NV);
    NV = IRB.CreateIntCast(NV, Int64Ty, false);
    setValueNonSan(NV);
  } else if (OpType->isDoubleTy()) {
    NV = IRB.CreateFPToUI(V, Int64Ty);
    setValueNonSan(NV);
  } else if (OpType->isPointerTy()) {
    NV = IRB.CreatePtrToInt(V, Int64Ty);
  } else {
    if (OpType->isIntegerTy() && OpType->getIntegerBitWidth() < 64) {
      NV = IRB.CreateZExt(V, Int64Ty);
    }
  }
  return NV;
}

void AngoraLLVMPass::processCmp(Instruction *Cond, Constant *Cid,
                                Instruction *InsertPoint) {
  CmpInst *Cmp = dyn_cast<CmpInst>(Cond);
  Value *OpArg[2];
  OpArg[0] = Cmp->getOperand(0);
  OpArg[1] = Cmp->getOperand(1);
  Type *OpType = OpArg[0]->getType();
  if (!((OpType->isIntegerTy() && OpType->getIntegerBitWidth() <= 64) ||
        OpType->isFloatTy() || OpType->isDoubleTy() || OpType->isPointerTy())) {
    processBoolCmp(Cond, Cid, InsertPoint);
    return;
  }
  int num_bytes = OpType->getScalarSizeInBits() / 8;
  if (num_bytes == 0) {
    if (OpType->isPointerTy()) {
      num_bytes = 8;
    } else {
      return;
    }
  }

  IRBuilder<> IRB(InsertPoint);

  if (FastMode) {
    /*
    OpArg[0] = castArgType(IRB, OpArg[0]);
    OpArg[1] = castArgType(IRB, OpArg[1]);
    Value *CondExt = IRB.CreateZExt(Cond, Int32Ty);
    setValueNonSan(CondExt);
    LoadInst *CurCtx = IRB.CreateLoad(AngoraContext);
    setInsNonSan(CurCtx);
    CallInst *ProxyCall =
        IRB.CreateCall(TraceCmp, {CondExt, Cid, CurCtx, OpArg[0], OpArg[1]});
    setInsNonSan(ProxyCall);
    */
    LoadInst *CurCid = IRB.CreateLoad(AngoraCondId);
    setInsNonSan(CurCid);
    Value *CmpEq = IRB.CreateICmpEQ(Cid, CurCid);
    setValueNonSan(CmpEq);

    BranchInst *BI = cast<BranchInst>(
        SplitBlockAndInsertIfThen(CmpEq, InsertPoint, false, ColdCallWeights));
    setInsNonSan(BI);

    IRBuilder<> ThenB(BI);
    OpArg[0] = castArgType(ThenB, OpArg[0]);
    OpArg[1] = castArgType(ThenB, OpArg[1]);
    Value *CondExt = ThenB.CreateZExt(Cond, Int32Ty);
    setValueNonSan(CondExt);
    LoadInst *CurCtx = ThenB.CreateLoad(AngoraContext);
    setInsNonSan(CurCtx);
    CallInst *ProxyCall =
        ThenB.CreateCall(TraceCmp, {CondExt, Cid, CurCtx, OpArg[0], OpArg[1]});
    setInsNonSan(ProxyCall);
  } else if (TrackMode) {
    Value *SizeArg = ConstantInt::get(Int32Ty, num_bytes);
    u32 predicate = Cmp->getPredicate();
    if (ConstantInt *CInt = dyn_cast<ConstantInt>(OpArg[1])) {
      if (CInt->isNegative()) {
        predicate |= COND_SIGN_MASK;
      }
    }
    Value *TypeArg = ConstantInt::get(Int32Ty, predicate);
    Value *CondExt = IRB.CreateZExt(Cond, Int32Ty);
    setValueNonSan(CondExt);
    OpArg[0] = castArgType(IRB, OpArg[0]);
    OpArg[1] = castArgType(IRB, OpArg[1]);
    LoadInst *CurCtx = IRB.CreateLoad(AngoraContext);
    setInsNonSan(CurCtx);
    CallInst *ProxyCall =
        IRB.CreateCall(TraceCmpTT, {Cid, CurCtx, SizeArg, TypeArg, OpArg[0],
                                    OpArg[1], CondExt});
    setInsNonSan(ProxyCall);
  }
}

void AngoraLLVMPass::processBoolCmp(Value *Cond, Constant *Cid,
                                    Instruction *InsertPoint) {
  if (!Cond->getType()->isIntegerTy() ||
      Cond->getType()->getIntegerBitWidth() > 32)
    return;
  Value *OpArg[2];
  OpArg[1] = ConstantInt::get(Int64Ty, 1);
  IRBuilder<> IRB(InsertPoint);
  if (FastMode) {
    LoadInst *CurCid = IRB.CreateLoad(AngoraCondId);
    setInsNonSan(CurCid);
    Value *CmpEq = IRB.CreateICmpEQ(Cid, CurCid);
    setValueNonSan(CmpEq);
    BranchInst *BI = cast<BranchInst>(
        SplitBlockAndInsertIfThen(CmpEq, InsertPoint, false, ColdCallWeights));
    setInsNonSan(BI);
    IRBuilder<> ThenB(BI);
    Value *CondExt = ThenB.CreateZExt(Cond, Int32Ty);
    setValueNonSan(CondExt);
    OpArg[0] = ThenB.CreateZExt(CondExt, Int64Ty);
    setValueNonSan(OpArg[0]);
    LoadInst *CurCtx = ThenB.CreateLoad(AngoraContext);
    setInsNonSan(CurCtx);
    CallInst *ProxyCall =
        ThenB.CreateCall(TraceCmp, {CondExt, Cid, CurCtx, OpArg[0], OpArg[1]});
    setInsNonSan(ProxyCall);
  } else if (TrackMode) {
    Value *SizeArg = ConstantInt::get(Int32Ty, 1);
    Value *TypeArg = ConstantInt::get(Int32Ty, COND_EQ_OP | COND_BOOL_MASK);
    Value *CondExt = IRB.CreateZExt(Cond, Int32Ty);
    setValueNonSan(CondExt);
    OpArg[0] = IRB.CreateZExt(CondExt, Int64Ty);
    setValueNonSan(OpArg[0]);
    LoadInst *CurCtx = IRB.CreateLoad(AngoraContext);
    setInsNonSan(CurCtx);
    CallInst *ProxyCall =
        IRB.CreateCall(TraceCmpTT, {Cid, CurCtx, SizeArg, TypeArg, OpArg[0],
                                    OpArg[1], CondExt});
    setInsNonSan(ProxyCall);
  }
}

void AngoraLLVMPass::visitCmpInst(Instruction *Inst) {
  Instruction *InsertPoint = Inst->getNextNode();
  if (!InsertPoint || isa<ConstantInt>(Inst))
    return;
  Constant *Cid = ConstantInt::get(Int32Ty, getInstructionId(Inst));
  processCmp(Inst, Cid, InsertPoint);
}

void AngoraLLVMPass::visitBranchInst(Instruction *Inst) {
  BranchInst *Br = dyn_cast<BranchInst>(Inst);
  if (Br->isConditional()) {
    Value *Cond = Br->getCondition();
    if (Cond && Cond->getType()->isIntegerTy() && !isa<ConstantInt>(Cond)) {
      if (!isa<CmpInst>(Cond)) {
        // From  and, or, call, phi ....
        Constant *Cid = ConstantInt::get(Int32Ty, getInstructionId(Inst));
        processBoolCmp(Cond, Cid, Inst);
      }
    }
  }
}

void AngoraLLVMPass::visitSwitchInst(Module &M, Instruction *Inst) {

  SwitchInst *Sw = dyn_cast<SwitchInst>(Inst);
  Value *Cond = Sw->getCondition();

  if (!(Cond && Cond->getType()->isIntegerTy() && !isa<ConstantInt>(Cond))) {
    return;
  }

  int num_bits = Cond->getType()->getScalarSizeInBits();
  int num_bytes = num_bits / 8;
  if (num_bytes == 0 || num_bits % 8 > 0)
    return;

  Constant *Cid = ConstantInt::get(Int32Ty, getInstructionId(Inst));
  IRBuilder<> IRB(Sw);

  if (FastMode) {
    LoadInst *CurCid = IRB.CreateLoad(AngoraCondId);
    setInsNonSan(CurCid);
    Value *CmpEq = IRB.CreateICmpEQ(Cid, CurCid);
    setValueNonSan(CmpEq);
    BranchInst *BI = cast<BranchInst>(
        SplitBlockAndInsertIfThen(CmpEq, Sw, false, ColdCallWeights));
    setInsNonSan(BI);
    IRBuilder<> ThenB(BI);
    Value *CondExt = ThenB.CreateZExt(Cond, Int64Ty);
    setValueNonSan(CondExt);
    LoadInst *CurCtx = ThenB.CreateLoad(AngoraContext);
    setInsNonSan(CurCtx);
    CallInst *ProxyCall = ThenB.CreateCall(TraceSw, {Cid, CurCtx, CondExt});
    setInsNonSan(ProxyCall);
  } else if (TrackMode) {
    Value *SizeArg = ConstantInt::get(Int32Ty, num_bytes);
    SmallVector<Constant *, 16> ArgList;
    for (auto It : Sw->cases()) {
      Constant *C = It.getCaseValue();
      if (C->getType()->getScalarSizeInBits() > Int64Ty->getScalarSizeInBits())
        continue;
      ArgList.push_back(ConstantExpr::getCast(CastInst::ZExt, C, Int64Ty));
    }

    ArrayType *ArrayOfInt64Ty = ArrayType::get(Int64Ty, ArgList.size());
    GlobalVariable *ArgGV = new GlobalVariable(
        M, ArrayOfInt64Ty, false, GlobalVariable::InternalLinkage,
        ConstantArray::get(ArrayOfInt64Ty, ArgList),
        "__angora_switch_arg_values");
    Value *SwNum = ConstantInt::get(Int32Ty, ArgList.size());
    Value *ArrPtr = IRB.CreatePointerCast(ArgGV, Int64PtrTy);
    setValueNonSan(ArrPtr);
    Value *CondExt = IRB.CreateZExt(Cond, Int64Ty);
    setValueNonSan(CondExt);
    LoadInst *CurCtx = IRB.CreateLoad(AngoraContext);
    setInsNonSan(CurCtx);
    CallInst *ProxyCall = IRB.CreateCall(
        TraceSwTT, {Cid, CurCtx, SizeArg, CondExt, SwNum, ArrPtr});
    setInsNonSan(ProxyCall);
  }
}

void AngoraLLVMPass::visitExploitation(Instruction *Inst) {
  // For each instruction and called function.
  bool exploit_all = ExploitList.isIn(*Inst, ExploitCategoryAll);
  IRBuilder<> IRB(Inst);
  int numParams = Inst->getNumOperands();
  CallInst *Caller = dyn_cast<CallInst>(Inst);

  if (Caller) {
    numParams = Caller->getNumArgOperands();
  }

  Value *TypeArg =
      ConstantInt::get(Int32Ty, COND_EXPLOIT_MASK | Inst->getOpcode());

  for (int i = 0; i < numParams && i < MAX_EXPLOIT_CATEGORY; i++) {
    if (exploit_all || ExploitList.isIn(*Inst, ExploitCategory[i])) {
      Value *ParamVal = NULL;
      if (Caller) {
        ParamVal = Caller->getArgOperand(i);
      } else {
        ParamVal = Inst->getOperand(i);
      }
      Type *ParamType = ParamVal->getType();
      if (ParamType->isIntegerTy() || ParamType->isPointerTy()) {
        if (!isa<ConstantInt>(ParamVal)) {
          ConstantInt *Cid = ConstantInt::get(Int32Ty, getInstructionId(Inst));
          int size = ParamVal->getType()->getScalarSizeInBits() / 8;
          if (ParamType->isPointerTy()) {
            size = 8;
          } else if (!ParamType->isIntegerTy(64)) {
            ParamVal = IRB.CreateZExt(ParamVal, Int64Ty);
          }
          Value *SizeArg = ConstantInt::get(Int32Ty, size);

          if (TrackMode) {
            LoadInst *CurCtx = IRB.CreateLoad(AngoraContext);
            setInsNonSan(CurCtx);
            CallInst *ProxyCall = IRB.CreateCall(
                TraceExploitTT, {Cid, CurCtx, SizeArg, TypeArg, ParamVal});
            setInsNonSan(ProxyCall);
          }
        }
      }
    }
  }
}

bool AngoraLLVMPass::runOnModule(Module &M) {

  SAYF(cCYA "angora-llvm-pass\n");
  if (TrackMode) {
    OKF("Track Mode.");
  } else if (DFSanMode) {
    OKF("DFSan Mode.");
  } else {
    FastMode = true;
    OKF("Fast Mode.");
  }

  initVariables(M);

  if (DFSanMode)
    return true;

  for (auto &F : M) {
    if (F.isDeclaration() || F.getName().startswith(StringRef("asan.module")))
      continue;

    addFnWrap(F);

    std::vector<BasicBlock *> bb_list;
    for (auto bb = F.begin(); bb != F.end(); bb++)
      bb_list.push_back(&(*bb));

    for (auto bi = bb_list.begin(); bi != bb_list.end(); bi++) {
      BasicBlock *BB = *bi;
      std::vector<Instruction *> inst_list;

      for (auto inst = BB->begin(); inst != BB->end(); inst++) {
        Instruction *Inst = &(*inst);
        inst_list.push_back(Inst);
      }

      for (auto inst = inst_list.begin(); inst != inst_list.end(); inst++) {
        Instruction *Inst = *inst;
        if (Inst->getMetadata(NoSanMetaId))
          continue;
        if (Inst == &(*BB->getFirstInsertionPt())) {
          countEdge(M, *BB);
        }
        if (isa<CallInst>(Inst)) {
          visitCallInst(Inst);
        } else if (isa<InvokeInst>(Inst)) {
          visitInvokeInst(Inst);
        } else if (isa<BranchInst>(Inst)) {
          visitBranchInst(Inst);
        } else if (isa<SwitchInst>(Inst)) {
          visitSwitchInst(M, Inst);
        } else if (isa<CmpInst>(Inst)) {
          visitCmpInst(Inst);
        } else {
          visitExploitation(Inst);
        }
      }
    }
  }

  if (is_bc)
    OKF("Max constraint id is %d", CidCounter);
  return true;
}

static void registerAngoraLLVMPass(const PassManagerBuilder &,
                                   legacy::PassManagerBase &PM) {
  PM.add(new AngoraLLVMPass());
}

static RegisterPass<AngoraLLVMPass> X("angora_llvm_pass", "Angora LLVM Pass",
                                      false, false);

static RegisterStandardPasses
    RegisterAngoraLLVMPass(PassManagerBuilder::EP_OptimizerLast,
                           registerAngoraLLVMPass);

static RegisterStandardPasses
    RegisterAngoraLLVMPass0(PassManagerBuilder::EP_EnabledOnOptLevel0,
                            registerAngoraLLVMPass);
