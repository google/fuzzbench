//===- Taint.cpp - dynamic taint analysis --------------------------------===//
//
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
//
//===----------------------------------------------------------------------===//
//
/// \file
/// This file is a part of Taint, a specialized taint analysis for symbolic
/// execution.
//
//===----------------------------------------------------------------------===//

#include "defs.h"
#include "version.h"

#include "llvm/ADT/DenseMap.h"
#include "llvm/ADT/DenseSet.h"
#include "llvm/ADT/DepthFirstIterator.h"
#include "llvm/ADT/None.h"
#include "llvm/ADT/SmallPtrSet.h"
#include "llvm/ADT/SmallVector.h"
#include "llvm/ADT/StringExtras.h"
#include "llvm/ADT/StringRef.h"
#include "llvm/ADT/Triple.h"
#include "llvm/Analysis/ValueTracking.h"
#include "llvm/IR/Argument.h"
#include "llvm/IR/Attributes.h"
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/CallSite.h"
#include "llvm/IR/Constant.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/DataLayout.h"
#include "llvm/IR/DerivedTypes.h"
#include "llvm/IR/Dominators.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/GlobalAlias.h"
#include "llvm/IR/GlobalValue.h"
#include "llvm/IR/GlobalVariable.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/InlineAsm.h"
#include "llvm/IR/InstVisitor.h"
#include "llvm/IR/InstrTypes.h"
#include "llvm/IR/Instruction.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/IntrinsicInst.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/IR/MDBuilder.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Type.h"
#include "llvm/IR/User.h"
#include "llvm/IR/Value.h"
#include "llvm/Pass.h"
#include "llvm/Support/Casting.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/ErrorHandling.h"
#include "llvm/Support/SpecialCaseList.h"
#include "llvm/Transforms/Instrumentation.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include "llvm/Transforms/Utils/Local.h"
#include "llvm/Transforms/Utils/ModuleUtils.h"
#include <algorithm>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <iterator>
#include <memory>
#include <set>
#include <string>
#include <utility>
#include <vector>
#include <functional>

using namespace llvm;

// External symbol to be used when generating the shadow address for
// architectures with multiple VMAs. Instead of using a constant integer
// the runtime will set the external mask based on the VMA range.
static const char *const kTaintExternShadowPtrMask = "__dfsan_shadow_ptr_mask";

// The -taint-preserve-alignment flag controls whether this pass assumes that
// alignment requirements provided by the input IR are correct.  For example,
// if the input IR contains a load with alignment 8, this flag will cause
// the shadow load to have alignment 16.  This flag is disabled by default as
// we have unfortunately encountered too much code (including Clang itself;
// see PR14291) which performs misaligned access.

static cl::opt<bool> ClPreserveAlignment(
    "taint-preserve-alignment",
    cl::desc("respect alignment requirements provided by input IR"), cl::Hidden,
    cl::init(false));

// The ABI list files control how shadow parameters are passed. The pass treats
// every function labelled "uninstrumented" in the ABI list file as conforming
// to the "native" (i.e. unsanitized) ABI.  Unless the ABI list contains
// additional annotations for those functions, a call to one of those functions
// will produce a warning message, as the labelling behaviour of the function is
// unknown.  The other supported annotations are "functional" and "discard",
// which are described below under Taint::WrapperKind.
static cl::list<std::string> ClABIListFiles(
    "taint-abilist",
    cl::desc("File listing native ABI functions and how the pass treats them"),
    cl::Hidden);

// Controls whether the pass uses IA_Args or IA_TLS as the ABI for instrumented
// functions (see Taint::InstrumentedABI below).
static cl::opt<bool> ClArgsABI(
    "taint-args-abi",
    cl::desc("Use the argument ABI rather than the TLS ABI"),
    cl::Hidden);

// Controls whether the pass includes or ignores the labels of pointers in load
// instructions.
static cl::opt<bool> ClCombinePointerLabelsOnLoad(
    "taint-combine-pointer-labels-on-load",
    cl::desc("Combine the label of the pointer with the label of the data when "
      "loading from memory."),
    cl::Hidden, cl::init(false));

// Controls whether the pass includes or ignores the labels of pointers in
// stores instructions.
static cl::opt<bool> ClCombinePointerLabelsOnStore(
    "taint-combine-pointer-labels-on-store",
    cl::desc("Combine the label of the pointer with the label of the data when "
      "storing in memory."),
    cl::Hidden, cl::init(false));

static cl::opt<bool> ClDebugNonzeroLabels(
    "taint-debug-nonzero-labels",
    cl::desc("Insert calls to __dfsan_nonzero_label on observing a parameter, "
      "load or return with a nonzero label"),
    cl::Hidden);

static cl::opt<bool> ClTraceGEPOffset(
    "taint-trace-gep",
    cl::desc("Trace GEP offset for solving."),
    cl::Hidden, cl::init(true));

static cl::opt<bool> ClTraceFP(
    "taint-trace-float-pointer",
    cl::desc("Propagate taint for floating pointer instructions."),
    cl::Hidden, cl::init(false));

static StringRef GetGlobalTypeString(const GlobalValue &G) {
  // Types of GlobalVariables are always pointer types.
  Type *GType = G.getValueType();
  // For now we support blacklisting struct types only.
  if (StructType *SGType = dyn_cast<StructType>(GType)) {
    if (!SGType->isLiteral())
      return SGType->getName();
  }
  return "<unknown type>";
}

namespace {

  class TaintABIList {
    std::unique_ptr<SpecialCaseList> SCL;

    public:
    TaintABIList() = default;

    void set(std::unique_ptr<SpecialCaseList> List) { SCL = std::move(List); }

    /// Returns whether either this function or its source file are listed in the
    /// given category.
    bool isIn(const Function &F, StringRef Category) const {
      return isIn(*F.getParent(), Category) ||
        SCL->inSection("taint", "fun", F.getName(), Category);
    }

    /// Returns whether this global alias is listed in the given category.
    ///
    /// If GA aliases a function, the alias's name is matched as a function name
    /// would be.  Similarly, aliases of globals are matched like globals.
    bool isIn(const GlobalAlias &GA, StringRef Category) const {
      if (isIn(*GA.getParent(), Category))
        return true;

      if (isa<FunctionType>(GA.getValueType()))
        return SCL->inSection("taint", "fun", GA.getName(), Category);

      return SCL->inSection("taint", "global", GA.getName(), Category) ||
        SCL->inSection("dataflow", "type", GetGlobalTypeString(GA),
            Category);
    }

    /// Returns whether this module is listed in the given category.
    bool isIn(const Module &M, StringRef Category) const {
      return SCL->inSection("taint", "src", M.getModuleIdentifier(), Category);
    }
  };

  /// TransformedFunction is used to express the result of transforming one
  /// function type into another.  This struct is immutable.  It holds metadata
  /// useful for updating calls of the old function to the new type.
  struct TransformedFunction {
    TransformedFunction(FunctionType *OriginalType, FunctionType *TransformedType,
        std::vector<unsigned> ArgumentIndexMapping)
      : OriginalType(OriginalType), TransformedType(TransformedType),
      ArgumentIndexMapping(ArgumentIndexMapping) {}

    // Disallow copies.
    TransformedFunction(const TransformedFunction &) = delete;
    TransformedFunction &operator=(const TransformedFunction &) = delete;

    // Allow moves.
    TransformedFunction(TransformedFunction &&) = default;
    TransformedFunction &operator=(TransformedFunction &&) = default;

    /// Type of the function before the transformation.
    FunctionType *OriginalType;

    /// Type of the function after the transformation.
    FunctionType *TransformedType;

    /// Transforming a function may change the position of arguments.  This
    /// member records the mapping from each argument's old position to its new
    /// position.  Argument positions are zero-indexed.  If the transformation
    /// from F to F' made the first argument of F into the third argument of F',
    /// then ArgumentIndexMapping[0] will equal 2.
    std::vector<unsigned> ArgumentIndexMapping;
  };

#if LLVM_VERSION_CODE >= LLVM_VERSION(6, 0)
  /// Given function attributes from a call site for the original function,
  /// return function attributes appropriate for a call to the transformed
  /// function.
  AttributeList TransformFunctionAttributes(
      const TransformedFunction &TransformedFunction,
      LLVMContext &Ctx, AttributeList CallSiteAttrs) {

    // Construct a vector of AttributeSet for each function argument.
    std::vector<llvm::AttributeSet> ArgumentAttributes(
        TransformedFunction.TransformedType->getNumParams());

    // Copy attributes from the parameter of the original function to the
    // transformed version.  'ArgumentIndexMapping' holds the mapping from
    // old argument position to new.
    for (unsigned i = 0, ie = TransformedFunction.ArgumentIndexMapping.size();
        i < ie; ++i) {
      unsigned TransformedIndex = TransformedFunction.ArgumentIndexMapping[i];
      ArgumentAttributes[TransformedIndex] = CallSiteAttrs.getParamAttributes(i);
    }

    // Copy annotations on varargs arguments.
    for (unsigned i = TransformedFunction.OriginalType->getNumParams(),
        ie = CallSiteAttrs.getNumAttrSets();
        i < ie; ++i) {
      ArgumentAttributes.push_back(CallSiteAttrs.getParamAttributes(i));
    }

    return AttributeList::get(Ctx, CallSiteAttrs.getFnAttributes(),
        CallSiteAttrs.getRetAttributes(),
        llvm::makeArrayRef(ArgumentAttributes));
  }
#endif

  class Taint : public ModulePass {
    friend struct TaintFunction;
    friend class TaintVisitor;

    enum {
      ShadowWidth = 32
    };

    /// Which ABI should be used for instrumented functions?
    enum InstrumentedABI {
      /// Argument and return value labels are passed through additional
      /// arguments and by modifying the return type.
      IA_Args,

      /// Argument and return value labels are passed through TLS variables
      /// __dfsan_arg_tls and __dfsan_retval_tls.
      IA_TLS
    };

    /// How should calls to uninstrumented functions be handled?
    enum WrapperKind {
      /// This function is present in an uninstrumented form but we don't know
      /// how it should be handled.  Print a warning and call the function anyway.
      /// Don't label the return value.
      WK_Warning,

      /// This function does not write to (user-accessible) memory, and its return
      /// value is unlabelled.
      WK_Discard,

      /// This function does not write to (user-accessible) memory, and the label
      /// of its return value is the union of the label of its arguments.
      WK_Functional,

      /// Instead of calling the function, a custom wrapper __dfsw_F is called,
      /// where F is the name of the function.  This function may wrap the
      /// original function or provide its own implementation.  This is similar to
      /// the IA_Args ABI, except that IA_Args uses a struct return type to
      /// pass the return value shadow in a register, while WK_Custom uses an
      /// extra pointer argument to return the shadow.  This allows the wrapped
      /// form of the function type to be expressed in C.
      WK_Custom
    };

    Module *Mod;
    LLVMContext *Ctx;
    IntegerType *ShadowTy;
    IntegerType *Int8Ty;
    IntegerType *Int16Ty;
    IntegerType *Int32Ty;
    IntegerType *Int64Ty;
    PointerType *ShadowPtrTy;
    IntegerType *IntptrTy;
    ConstantInt *ZeroShadow;
    ConstantInt *ShadowPtrMask;
    ConstantInt *ShadowPtrMul;
    Constant *ArgTLS;
    Constant *RetvalTLS;
    void *(*GetArgTLSPtr)();
    void *(*GetRetvalTLSPtr)();
    Constant *GetArgTLS;
    Constant *GetRetvalTLS;
    Constant *ExternalShadowMask;
    FunctionType *TaintUnionFnTy;
    FunctionType *TaintUnionLoadFnTy;
    FunctionType *TaintUnionStoreFnTy;
    FunctionType *TaintUnimplementedFnTy;
    FunctionType *TaintSetLabelFnTy;
    FunctionType *TaintNonzeroLabelFnTy;
    FunctionType *TaintVarargWrapperFnTy;
    FunctionType *TaintTraceCmpFnTy;
    FunctionType *TaintTraceCondFnTy;
    FunctionType *TaintTraceIndirectCallFnTy;
    FunctionType *TaintTraceGEPFnTy;
    FunctionType *TaintDebugFnTy;
    Constant *TaintUnionFn;
    Constant *TaintCheckedUnionFn;
    Constant *TaintUnionLoadFn;
    Constant *TaintUnionStoreFn;
    Constant *TaintUnimplementedFn;
    Constant *TaintSetLabelFn;
    Constant *TaintNonzeroLabelFn;
    Constant *TaintVarargWrapperFn;
    Constant *TaintTraceCmpFn;
    Constant *TaintTraceCondFn;
    Constant *TaintTraceIndirectCallFn;
    Constant *TaintTraceGEPFn;
    Constant *TaintDebugFn;
    //Constant *CallStack;
    GlobalVariable *CallStack;
    GlobalVariable *AngoraMapPtr;
    GlobalVariable *AngoraPrevLoc;
    MDNode *ColdCallWeights;
    TaintABIList ABIList;
    DenseMap<Value *, Function *> UnwrappedFnMap;
    AttrBuilder ReadOnlyNoneAttrs;
    bool TaintRuntimeShadowMask = false;

    Value *getShadowAddress(Value *Addr, Instruction *Pos);
    bool isInstrumented(const Function *F);
    bool isInstrumented(const GlobalAlias *GA);
    FunctionType *getArgsFunctionType(FunctionType *T);
    FunctionType *getTrampolineFunctionType(FunctionType *T);
    TransformedFunction getCustomFunctionType(FunctionType *T);
    InstrumentedABI getInstrumentedABI();
    WrapperKind getWrapperKind(Function *F);
    void addGlobalNamePrefix(GlobalValue *GV);
    Function *buildWrapperFunction(Function *F, StringRef NewFName,
        GlobalValue::LinkageTypes NewFLink,
        FunctionType *NewFT);
    Constant *getOrBuildTrampolineFunction(FunctionType *FT, StringRef FName);

    void addContextRecording(Function &F);

    public:
    static char ID;

    Taint(
        const std::vector<std::string> &ABIListFiles = std::vector<std::string>(),
        void *(*getArgTLS)() = nullptr, void *(*getRetValTLS)() = nullptr);

    bool doInitialization(Module &M) override;
    bool runOnModule(Module &M) override;
    //void countEdge(Module &M, BasicBlock &BB);
    void setValueNonSan(Value *v);
    void setInsNonSan(Instruction *v);
  };

  struct TaintFunction {
    Taint &TT;
    Function *F;
    DominatorTree DT;
    Taint::InstrumentedABI IA;
    bool IsNativeABI;
    Value *ArgTLSPtr = nullptr;
    Value *RetvalTLSPtr = nullptr;
    AllocaInst *LabelReturnAlloca = nullptr;
    DenseMap<Value *, Value *> ValShadowMap;
    DenseMap<AllocaInst *, AllocaInst *> AllocaShadowMap;
    std::vector<std::pair<PHINode *, PHINode *>> PHIFixups;
    DenseSet<Instruction *> SkipInsts;
    DenseSet<Instruction *> StoreInsts;
    std::vector<Value *> NonZeroChecks;
    bool AvoidNewBlocks;
    std::hash<std::string> HashFn;

    struct CachedCombinedShadow {
      BasicBlock *Block;
      Value *Shadow;
    };
    DenseMap<std::pair<Value *, Value *>, CachedCombinedShadow>
      CachedCombinedShadows;
    DenseMap<Value *, std::set<Value *>> ShadowElements;

    TaintFunction(Taint &TT, Function *F, bool IsNativeABI)
      : TT(TT), F(F), IA(TT.getInstrumentedABI()), IsNativeABI(IsNativeABI) {
        DT.recalculate(*F);
        // FIXME: Need to track down the register allocator issue which causes poor
        // performance in pathological cases with large numbers of basic blocks.
        AvoidNewBlocks = F->size() > 1000;
        srandom(std::hash<std::string>{}(F->getName().str()));
      }

    Value *getArgTLSPtr();
    Value *getArgTLS(unsigned Index, Instruction *Pos);
    Value *getRetvalTLS();
    Value *getShadow(Value *V);
    void setShadow(Instruction *I, Value *Shadow);
    // Op Shadow
    Value *combineShadows(Value *V1, Value *V2,
        uint16_t op, Instruction *Pos);
    Value *combineBinaryOperatorShadows(BinaryOperator *BO, uint8_t op);
    Value *combineCastInstShadows(CastInst *CI, uint8_t op);
    Value *combineCmpInstShadows(CmpInst *CI, uint8_t op);
    Value *loadShadow(Value *ShadowAddr, uint64_t Size, uint64_t Align,
        Instruction *Pos);
    void storeShadow(Value *Addr, uint64_t Size, uint64_t Align, Value *Shadow,
        Instruction *Pos);
    void visitCmpInst(CmpInst *I);
    void visitSwitchInst(SwitchInst *I);
    void visitCondition(Value *Cond, Instruction *I);
    void visitGEPInst(GetElementPtrInst *I);
  };

  class TaintVisitor : public InstVisitor<TaintVisitor> {
    public:
      TaintFunction &TF;

      TaintVisitor(TaintFunction &TF) : TF(TF) {}

      const DataLayout &getDataLayout() const {
        return TF.F->getParent()->getDataLayout();
      }

      void visitBinaryOperator(BinaryOperator &BO);
      void visitBranchInst(BranchInst &BR);
      void visitCastInst(CastInst &CI);
      void visitCmpInst(CmpInst &CI);
      void visitSwitchInst(SwitchInst &SWI);
      void visitGetElementPtrInst(GetElementPtrInst &GEPI);
      void visitLoadInst(LoadInst &LI);
      void visitStoreInst(StoreInst &SI);
      void visitReturnInst(ReturnInst &RI);
      void visitCallSite(CallSite CS);
      void visitPHINode(PHINode &PN);
      void visitExtractElementInst(ExtractElementInst &I);
      void visitInsertElementInst(InsertElementInst &I);
      void visitShuffleVectorInst(ShuffleVectorInst &I);
      void visitExtractValueInst(ExtractValueInst &I);
      void visitInsertValueInst(InsertValueInst &I);
      void visitAllocaInst(AllocaInst &I);
      void visitSelectInst(SelectInst &I);
      void visitMemSetInst(MemSetInst &I);
      void visitMemTransferInst(MemTransferInst &I);
  };

} // end anonymous namespace

char Taint::ID;

#if 0
INITIALIZE_PASS(Taint, "taint",
    "Taint: dynamic taint analysis.", false, false)

ModulePass *
llvm::createTaintPass(const std::vector<std::string> &ABIListFiles,
    void *(*getArgTLS)(),
    void *(*getRetValTLS)()) {
  // remove default one to support FTS build
  std::vector<std::string> Files =
    const_cast<std::vector<std::string> &>(ABIListFiles);
  if (Files.size() > 1)
    Files.erase(Files.begin());
  return new Taint(Files, getArgTLS, getRetValTLS);
}
#endif

  Taint::Taint(
      const std::vector<std::string> &ABIListFiles, void *(*getArgTLS)(),
      void *(*getRetValTLS)())
  : ModulePass(ID), GetArgTLSPtr(getArgTLS), GetRetvalTLSPtr(getRetValTLS) {
    std::vector<std::string> AllABIListFiles(std::move(ABIListFiles));
    AllABIListFiles.insert(AllABIListFiles.end(), ClABIListFiles.begin(),
        ClABIListFiles.end());
    ABIList.set(SpecialCaseList::createOrDie(AllABIListFiles));
  }

FunctionType *Taint::getArgsFunctionType(FunctionType *T) {
  SmallVector<Type *, 4> ArgTypes(T->param_begin(), T->param_end());
  ArgTypes.append(T->getNumParams(), ShadowTy);
  if (T->isVarArg())
    ArgTypes.push_back(ShadowPtrTy);
  Type *RetType = T->getReturnType();
  if (!RetType->isVoidTy()) {
#if LLVM_VERSION_CODE >= LLVM_VERSION(5, 0)
    RetType = StructType::get(RetType, ShadowTy);
#else
    RetType = StructType::get(RetType, ShadowTy, (Type *)nullptr);
#endif
  }
  return FunctionType::get(RetType, ArgTypes, T->isVarArg());
}

FunctionType *Taint::getTrampolineFunctionType(FunctionType *T) {
  assert(!T->isVarArg());
  SmallVector<Type *, 4> ArgTypes;
  ArgTypes.push_back(T->getPointerTo());
  ArgTypes.append(T->param_begin(), T->param_end());
  ArgTypes.append(T->getNumParams(), ShadowTy);
  Type *RetType = T->getReturnType();
  if (!RetType->isVoidTy())
    ArgTypes.push_back(ShadowPtrTy);
  return FunctionType::get(T->getReturnType(), ArgTypes, false);
}

TransformedFunction Taint::getCustomFunctionType(FunctionType *T) {
  SmallVector<Type *, 4> ArgTypes;

  // Some parameters of the custom function being constructed are
  // parameters of T.  Record the mapping from parameters of T to
  // parameters of the custom function, so that parameter attributes
  // at call sites can be updated.
  std::vector<unsigned> ArgumentIndexMapping;
  for (unsigned i = 0, ie = T->getNumParams(); i != ie; ++i) {
    Type *param_type = T->getParamType(i);
    FunctionType *FT;
    if (isa<PointerType>(param_type) &&
        (FT = dyn_cast<FunctionType>(
                                     cast<PointerType>(param_type)->getElementType()))) {
      ArgumentIndexMapping.push_back(ArgTypes.size());
      ArgTypes.push_back(getTrampolineFunctionType(FT)->getPointerTo());
      ArgTypes.push_back(Type::getInt8PtrTy(*Ctx));
    } else {
      ArgumentIndexMapping.push_back(ArgTypes.size());
      ArgTypes.push_back(param_type);
    }
  }
  for (unsigned i = 0, e = T->getNumParams(); i != e; ++i)
    ArgTypes.push_back(ShadowTy);
  if (T->isVarArg())
    ArgTypes.push_back(ShadowPtrTy);
  Type *RetType = T->getReturnType();
  if (!RetType->isVoidTy())
    ArgTypes.push_back(ShadowPtrTy);
  return TransformedFunction(
      T, FunctionType::get(T->getReturnType(), ArgTypes, T->isVarArg()),
      ArgumentIndexMapping);
}

void Taint::addContextRecording(Function &F) {
  // Most code from Angora
  BasicBlock *BB = &F.getEntryBlock();
  assert(pred_begin(BB) == pred_end(BB) &&
      "Assume that entry block has no predecessors");

  // Add ctx ^ random_index at the beginning of a function
  IRBuilder<> IRB(&*(BB->getFirstInsertionPt()));
  ConstantInt *CID = ConstantInt::get(Int32Ty, (uint32_t)random());
  LoadInst *LCS = IRB.CreateLoad(CallStack);
  LCS->setMetadata(Mod->getMDKindID("nosanitize"), MDNode::get(*Ctx, None));
  Value *NCS = IRB.CreateXor(LCS, CID);
  StoreInst *SCS = IRB.CreateStore(NCS, CallStack);
  SCS->setMetadata(Mod->getMDKindID("nosanitize"), MDNode::get(*Ctx, None));

  // Recover ctx at the end of a function
  for (auto FI = F.begin(), FE = F.end(); FI != FE; FI++) {
    BasicBlock *BB = &*FI;
    Instruction *Inst = BB->getTerminator();
    if (isa<ReturnInst>(Inst) || isa<ResumeInst>(Inst)) {
      IRB.SetInsertPoint(Inst);
      SCS = IRB.CreateStore(LCS, CallStack);
      SCS->setMetadata(Mod->getMDKindID("nosanitize"), MDNode::get(*Ctx, None));
    }
  }
}

bool Taint::doInitialization(Module &M) {
  Triple TargetTriple(M.getTargetTriple());
  bool IsX86_64 = TargetTriple.getArch() == Triple::x86_64;
  // bool IsMIPS64 argetTriple.isMIPS64();
  bool IsMIPS64 = TargetTriple.getArch() == llvm::Triple::mips64 ||
    TargetTriple.getArch() == llvm::Triple::mips64el;
  bool IsAArch64 = TargetTriple.getArch() == Triple::aarch64 ||
    TargetTriple.getArch() == Triple::aarch64_be;

  const DataLayout &DL = M.getDataLayout();

  Mod = &M;
  Ctx = &M.getContext();
  ShadowTy = IntegerType::get(*Ctx, ShadowWidth);
  Int8Ty = IntegerType::get(*Ctx, 8);
  Int16Ty = IntegerType::get(*Ctx, 16);
  Int32Ty = IntegerType::get(*Ctx, 32);
  Int64Ty = IntegerType::get(*Ctx, 64);
  ShadowPtrTy = PointerType::getUnqual(ShadowTy);
  IntptrTy = DL.getIntPtrType(*Ctx);
  ZeroShadow = ConstantInt::getSigned(ShadowTy, 0);
  ShadowPtrMul = ConstantInt::getSigned(IntptrTy, ShadowWidth / 8);
  if (IsX86_64)
    ShadowPtrMask = ConstantInt::getSigned(IntptrTy, ~0x700000000000LL);
  else if (IsMIPS64)
    ShadowPtrMask = ConstantInt::getSigned(IntptrTy, ~0xF000000000LL);
  // AArch64 supports multiple VMAs and the shadow mask is set at runtime.
  else if (IsAArch64)
    TaintRuntimeShadowMask = true;
  else
    report_fatal_error("unsupported triple");

  Type *TaintUnionArgs[6] = { ShadowTy, ShadowTy, Int16Ty, Int16Ty, Int64Ty, Int64Ty};
  TaintUnionFnTy = FunctionType::get(
      ShadowTy, TaintUnionArgs, /*isVarArg=*/ false);
  Type *TaintUnionLoadArgs[2] = { ShadowPtrTy, IntptrTy };
  TaintUnionLoadFnTy = FunctionType::get(
      ShadowTy, TaintUnionLoadArgs, /*isVarArg=*/ false);
  Type *TaintUnionStoreArgs[3] = { ShadowTy, ShadowPtrTy, IntptrTy };
  TaintUnionStoreFnTy = FunctionType::get(
      Type::getVoidTy(*Ctx), TaintUnionStoreArgs, /*isVarArg=*/ false);
  TaintUnimplementedFnTy = FunctionType::get(
      Type::getVoidTy(*Ctx), Type::getInt8PtrTy(*Ctx), /*isVarArg=*/false);
  Type *TaintSetLabelArgs[3] = { ShadowTy, Type::getInt8PtrTy(*Ctx), IntptrTy };
  TaintSetLabelFnTy = FunctionType::get(Type::getVoidTy(*Ctx),
      TaintSetLabelArgs, /*isVarArg=*/false);
  TaintNonzeroLabelFnTy = FunctionType::get(
      Type::getVoidTy(*Ctx), None, /*isVarArg=*/false);
  TaintVarargWrapperFnTy = FunctionType::get(
      Type::getVoidTy(*Ctx), Type::getInt8PtrTy(*Ctx), /*isVarArg=*/false);
  Type *TaintTraceCmpArgs[6] = { ShadowTy, ShadowTy, ShadowTy, ShadowTy,
    Int64Ty, Int64Ty };
  TaintTraceCmpFnTy = FunctionType::get(
      Type::getVoidTy(*Ctx), TaintTraceCmpArgs, false);
  Type *TaintTraceCondArgs[2] = { ShadowTy, Int8Ty };
  TaintTraceCondFnTy = FunctionType::get(
      Type::getVoidTy(*Ctx), TaintTraceCondArgs, false);
  TaintTraceIndirectCallFnTy = FunctionType::get(
      Type::getVoidTy(*Ctx), { ShadowTy }, false);
  TaintTraceGEPFnTy = FunctionType::get(
      Type::getVoidTy(*Ctx), { ShadowTy, Int64Ty }, false);

  TaintDebugFnTy = FunctionType::get(Type::getVoidTy(*Ctx),
      {ShadowTy, ShadowTy, ShadowTy, ShadowTy, ShadowTy}, false);

  if (GetArgTLSPtr) {
    Type *ArgTLSTy = ArrayType::get(ShadowTy, 64);
    ArgTLS = nullptr;
    GetArgTLS = ConstantExpr::getIntToPtr(
        ConstantInt::get(IntptrTy, uintptr_t(GetArgTLSPtr)),
        PointerType::getUnqual(
          FunctionType::get(PointerType::getUnqual(ArgTLSTy), false)));
  }
  if (GetRetvalTLSPtr) {
    RetvalTLS = nullptr;
    GetRetvalTLS = ConstantExpr::getIntToPtr(
        ConstantInt::get(IntptrTy, uintptr_t(GetRetvalTLSPtr)),
        PointerType::getUnqual(
          FunctionType::get(PointerType::getUnqual(ShadowTy), false)));
  }

  ColdCallWeights = MDBuilder(*Ctx).createBranchWeights(1, 1000);

  return true;
}

bool Taint::isInstrumented(const Function *F) {
  return !ABIList.isIn(*F, "uninstrumented");
}

bool Taint::isInstrumented(const GlobalAlias *GA) {
  return !ABIList.isIn(*GA, "uninstrumented");
}

Taint::InstrumentedABI Taint::getInstrumentedABI() {
  return ClArgsABI ? IA_Args : IA_TLS;
}

Taint::WrapperKind Taint::getWrapperKind(Function *F) {
  // priority custom
  if (ABIList.isIn(*F, "custom"))
    return WK_Custom;
  if (ABIList.isIn(*F, "functional"))
    return WK_Functional;
  if (ABIList.isIn(*F, "discard"))
    return WK_Discard;

  return WK_Warning;
}

void Taint::addGlobalNamePrefix(GlobalValue *GV) {
  std::string GVName = GV->getName(), Prefix = "dfs$";
  GV->setName(Prefix + GVName);

  // Try to change the name of the function in module inline asm.  We only do
  // this for specific asm directives, currently only ".symver", to try to avoid
  // corrupting asm which happens to contain the symbol name as a substring.
  // Note that the substitution for .symver assumes that the versioned symbol
  // also has an instrumented name.
  std::string Asm = GV->getParent()->getModuleInlineAsm();
  std::string SearchStr = ".symver " + GVName + ",";
  size_t Pos = Asm.find(SearchStr);
  if (Pos != std::string::npos) {
    Asm.replace(Pos, SearchStr.size(),
        ".symver " + Prefix + GVName + "," + Prefix);
    GV->getParent()->setModuleInlineAsm(Asm);
  }
}

Function *
Taint::buildWrapperFunction(Function *F, StringRef NewFName,
    GlobalValue::LinkageTypes NewFLink,
    FunctionType *NewFT) {
  FunctionType *FT = F->getFunctionType();
  Function *NewF = Function::Create(NewFT, NewFLink, NewFName,
      F->getParent());
  NewF->copyAttributesFrom(F);
  NewF->removeAttributes(
      AttributeList::ReturnIndex,
      AttributeFuncs::typeIncompatible(NewFT->getReturnType()));

  BasicBlock *BB = BasicBlock::Create(*Ctx, "entry", NewF);
  if (F->isVarArg() && getWrapperKind(F) != WK_Discard) {
    NewF->removeAttributes(AttributeList::FunctionIndex,
        AttrBuilder().addAttribute("split-stack"));
    CallInst::Create(TaintVarargWrapperFn,
        IRBuilder<>(BB).CreateGlobalStringPtr(F->getName()), "",
        BB);
    new UnreachableInst(*Ctx, BB);
  } else {
    std::vector<Value *> Args;
    unsigned n = FT->getNumParams();
    for (Function::arg_iterator ai = NewF->arg_begin(); n != 0; ++ai, --n)
      Args.push_back(&*ai);
    CallInst *CI = CallInst::Create(F, Args, "", BB);
    if (FT->getReturnType()->isVoidTy())
      ReturnInst::Create(*Ctx, BB);
    else
      ReturnInst::Create(*Ctx, CI, BB);
  }

  return NewF;
}

Constant *Taint::getOrBuildTrampolineFunction(FunctionType *FT,
    StringRef FName) {
  FunctionType *FTT = getTrampolineFunctionType(FT);
  Constant *C = Mod->getOrInsertFunction(FName, FTT);
  Function *F = dyn_cast<Function>(C);
  if (F && F->isDeclaration()) {
    F->setLinkage(GlobalValue::LinkOnceODRLinkage);
    BasicBlock *BB = BasicBlock::Create(*Ctx, "entry", F);
    std::vector<Value *> Args;
    Function::arg_iterator AI = F->arg_begin(); ++AI;
    for (unsigned N = FT->getNumParams(); N != 0; ++AI, --N)
      Args.push_back(&*AI);
    CallInst *CI = CallInst::Create(&*F->arg_begin(), Args, "", BB);
    ReturnInst *RI;
    if (FT->getReturnType()->isVoidTy())
      RI = ReturnInst::Create(*Ctx, BB);
    else
      RI = ReturnInst::Create(*Ctx, CI, BB);

    TaintFunction TF(*this, F, /*IsNativeABI=*/true);
    Function::arg_iterator ValAI = F->arg_begin(), ShadowAI = AI; ++ValAI;
    for (unsigned N = FT->getNumParams(); N != 0; ++ValAI, ++ShadowAI, --N)
      TF.ValShadowMap[&*ValAI] = &*ShadowAI;
    TaintVisitor(TF).visitCallInst(*CI);
    if (!FT->getReturnType()->isVoidTy())
      new StoreInst(TF.getShadow(RI->getReturnValue()),
          &*std::prev(F->arg_end()), RI);
  }

  return C;
}

void Taint::setValueNonSan(Value *v) {
  if (Instruction *ins = dyn_cast<Instruction>(v))
    setInsNonSan(ins);
}

void Taint::setInsNonSan(Instruction *ins) {
  if (ins)
    ins->setMetadata(Mod->getMDKindID("nosanitize"), MDNode::get(*Ctx, None));
}



bool Taint::runOnModule(Module &M) {
  if (ABIList.isIn(M, "skip"))
    return false;

  if (!GetArgTLSPtr) {
    Type *ArgTLSTy = ArrayType::get(ShadowTy, 64);
    ArgTLS = Mod->getOrInsertGlobal("__dfsan_arg_tls", ArgTLSTy);
    if (GlobalVariable *G = dyn_cast<GlobalVariable>(ArgTLS))
      G->setThreadLocalMode(GlobalVariable::InitialExecTLSModel);
  }
  if (!GetRetvalTLSPtr) {
    RetvalTLS = Mod->getOrInsertGlobal("__dfsan_retval_tls", ShadowTy);
    if (GlobalVariable *G = dyn_cast<GlobalVariable>(RetvalTLS))
      G->setThreadLocalMode(GlobalVariable::InitialExecTLSModel);
  }

  ExternalShadowMask =
    Mod->getOrInsertGlobal(kTaintExternShadowPtrMask, IntptrTy);

  TaintUnionFn = Mod->getOrInsertFunction("__taint_union", TaintUnionFnTy);
  if (Function *F = dyn_cast<Function>(TaintUnionFn)) {
    F->addAttribute(AttributeList::FunctionIndex, Attribute::NoUnwind);
    F->addAttribute(AttributeList::FunctionIndex, Attribute::ReadNone);
    F->addAttribute(AttributeList::ReturnIndex, Attribute::ZExt);
    F->addParamAttr(0, Attribute::ZExt);
    F->addParamAttr(1, Attribute::ZExt);
  }

  TaintCheckedUnionFn = Mod->getOrInsertFunction("taint_union", TaintUnionFnTy);
  if (Function *F = dyn_cast<Function>(TaintCheckedUnionFn)) {
    F->addAttribute(AttributeList::FunctionIndex, Attribute::NoUnwind);
    F->addAttribute(AttributeList::FunctionIndex, Attribute::ReadNone);
    F->addAttribute(AttributeList::ReturnIndex, Attribute::ZExt);
    F->addParamAttr(0, Attribute::ZExt);
    F->addParamAttr(1, Attribute::ZExt);
  }

  TaintUnionLoadFn =
    Mod->getOrInsertFunction("__taint_union_load", TaintUnionLoadFnTy);
  if (Function *F = dyn_cast<Function>(TaintUnionLoadFn)) {
    F->addAttribute(AttributeList::FunctionIndex, Attribute::NoUnwind);
    F->addAttribute(AttributeList::FunctionIndex, Attribute::ReadOnly);
    F->addAttribute(AttributeList::ReturnIndex, Attribute::ZExt);
  }

  TaintUnionStoreFn =
    Mod->getOrInsertFunction("__taint_union_store", TaintUnionStoreFnTy);
  if (Function *F = dyn_cast<Function>(TaintUnionStoreFn)) {
    F->addAttribute(AttributeList::FunctionIndex, Attribute::NoUnwind);
    F->addParamAttr(0, Attribute::ZExt);
  }

  TaintUnimplementedFn =
    Mod->getOrInsertFunction("__dfsan_unimplemented", TaintUnimplementedFnTy);
  TaintSetLabelFn =
    Mod->getOrInsertFunction("__dfsan_set_label", TaintSetLabelFnTy);
  if (Function *F = dyn_cast<Function>(TaintSetLabelFn)) {
    F->addParamAttr(0, Attribute::ZExt);
  }
  TaintNonzeroLabelFn =
    Mod->getOrInsertFunction("__dfsan_nonzero_label", TaintNonzeroLabelFnTy);
  TaintVarargWrapperFn = Mod->getOrInsertFunction("__dfsan_vararg_wrapper",
      TaintVarargWrapperFnTy);

  TaintTraceCmpFn =
    Mod->getOrInsertFunction("__taint_trace_cmp", TaintTraceCmpFnTy);
  TaintTraceCondFn =
    Mod->getOrInsertFunction("__taint_trace_cond", TaintTraceCondFnTy);
  TaintTraceIndirectCallFn =
    Mod->getOrInsertFunction("__taint_trace_indcall", TaintTraceIndirectCallFnTy);
  TaintTraceGEPFn =
    Mod->getOrInsertFunction("__taint_trace_gep", TaintTraceGEPFnTy);

  TaintDebugFn =
    Mod->getOrInsertFunction("__taint_debug", TaintDebugFnTy);

  /*
     CallStack = Mod->getOrInsertGlobal("__taint_trace_callstack", Int32Ty);
     if (GlobalVariable *G = dyn_cast<GlobalVariable>(CallStack))
     G->setThreadLocalMode(GlobalVariable::InitialExecTLSModel);
   */
  CallStack = Mod->getGlobalVariable("__taint_trace_callstack");
  if (!CallStack) {
    CallStack =
      new GlobalVariable(*Mod, PointerType::get(Int32Ty, 0), false,
          GlobalValue::CommonLinkage,
          ConstantInt::get(Int32Ty, 0),
          "__taint_trace_callstack",
          nullptr,
          GlobalValue::GeneralDynamicTLSModel);
  }
  

  std::vector<Function *> FnsToInstrument;
  SmallPtrSet<Function *, 2> FnsWithNativeABI;
  for (Function &i : M) {
    if (!i.isIntrinsic() &&
        &i != TaintUnionFn &&
        &i != TaintCheckedUnionFn &&
        &i != TaintUnionLoadFn &&
        &i != TaintUnionStoreFn &&
        &i != TaintUnimplementedFn &&
        &i != TaintSetLabelFn &&
        &i != TaintNonzeroLabelFn &&
        &i != TaintVarargWrapperFn &&
        &i != TaintTraceCmpFn &&
        &i != TaintTraceCondFn &&
        &i != TaintTraceIndirectCallFn &&
        &i != TaintTraceGEPFn &&
        &i != TaintDebugFn &&
        &i != TaintUnionStoreFn) {
      FnsToInstrument.push_back(&i);
    }
  }

  // Give function aliases prefixes when necessary, and build wrappers where the
  // instrumentedness is inconsistent.
  for (Module::alias_iterator i = M.alias_begin(), e = M.alias_end(); i != e;) {
    GlobalAlias *GA = &*i;
    ++i;
    // Don't stop on weak.  We assume people aren't playing games with the
    // instrumentedness of overridden weak aliases.
    if (auto F = dyn_cast<Function>(GA->getBaseObject())) {
      bool GAInst = isInstrumented(GA), FInst = isInstrumented(F);
      if (GAInst && FInst) {
        addGlobalNamePrefix(GA);
      } else if (GAInst != FInst) {
        // Non-instrumented alias of an instrumented function, or vice versa.
        // Replace the alias with a native-ABI wrapper of the aliasee.  The pass
        // below will take care of instrumenting it.
        Function *NewF =
          buildWrapperFunction(F, "", GA->getLinkage(), F->getFunctionType());
        GA->replaceAllUsesWith(ConstantExpr::getBitCast(NewF, GA->getType()));
        NewF->takeName(GA);
        GA->eraseFromParent();
        FnsToInstrument.push_back(NewF);
      }
    }
  }

  ReadOnlyNoneAttrs.addAttribute(Attribute::ReadOnly)
    .addAttribute(Attribute::ReadNone);

  // First, change the ABI of every function in the module.  ABI-listed
  // functions keep their original ABI and get a wrapper function.
  for (std::vector<Function *>::iterator i = FnsToInstrument.begin(),
      e = FnsToInstrument.end();
      i != e; ++i) {
    Function &F = **i;
    FunctionType *FT = F.getFunctionType();

    bool IsZeroArgsVoidRet = (FT->getNumParams() == 0 && !FT->isVarArg() &&
        FT->getReturnType()->isVoidTy());
    if (isInstrumented(&F)) {
      // Instrumented functions get a 'dfs$' prefix.  This allows us to more
      // easily identify cases of mismatching ABIs.
      if (getInstrumentedABI() == IA_Args && !IsZeroArgsVoidRet) {
        FunctionType *NewFT = getArgsFunctionType(FT);
        Function *NewF = Function::Create(NewFT, F.getLinkage(), "", &M);
        NewF->copyAttributesFrom(&F);
        NewF->removeAttributes(
            AttributeList::ReturnIndex,
            AttributeFuncs::typeIncompatible(NewFT->getReturnType()));
        for (Function::arg_iterator FArg = F.arg_begin(),
            NewFArg = NewF->arg_begin(),
            FArgEnd = F.arg_end();
            FArg != FArgEnd; ++FArg, ++NewFArg) {
          FArg->replaceAllUsesWith(&*NewFArg);
        }
        NewF->getBasicBlockList().splice(NewF->begin(), F.getBasicBlockList());

        for (Function::user_iterator UI = F.user_begin(), UE = F.user_end();
            UI != UE;) {
          BlockAddress *BA = dyn_cast<BlockAddress>(*UI);
          ++UI;
          if (BA) {
            BA->replaceAllUsesWith(
                BlockAddress::get(NewF, BA->getBasicBlock()));
            delete BA;
          }
        }
        F.replaceAllUsesWith(
            ConstantExpr::getBitCast(NewF, PointerType::getUnqual(FT)));
        NewF->takeName(&F);
        F.eraseFromParent();
        *i = NewF;
        addGlobalNamePrefix(NewF);
      } else {
        addGlobalNamePrefix(&F);
      }
    } else if (!IsZeroArgsVoidRet || getWrapperKind(&F) == WK_Custom) {
      // Build a wrapper function for F.  The wrapper simply calls F, and is
      // added to FnsToInstrument so that any instrumentation according to its
      // WrapperKind is done in the second pass below.
      FunctionType *NewFT = getInstrumentedABI() == IA_Args
        ? getArgsFunctionType(FT)
        : FT;
      // If the function being wrapped has local linkage, then preserve the
      // function's linkage in the wrapper function.
      GlobalValue::LinkageTypes wrapperLinkage =
        F.hasLocalLinkage() ? F.getLinkage()
        : GlobalValue::LinkOnceODRLinkage;
      Function *NewF = buildWrapperFunction(
          &F, std::string("dfsw$") + std::string(F.getName()), wrapperLinkage,
          NewFT);
      if (getInstrumentedABI() == IA_TLS)
        NewF->removeAttributes(AttributeList::FunctionIndex, ReadOnlyNoneAttrs);

      Value *WrappedFnCst =
        ConstantExpr::getBitCast(NewF, PointerType::getUnqual(FT));
      F.replaceAllUsesWith(WrappedFnCst);

      UnwrappedFnMap[WrappedFnCst] = &F;
      *i = NewF;

      if (!F.isDeclaration()) {
        // This function is probably defining an interposition of an
        // uninstrumented function and hence needs to keep the original ABI.
        // But any functions it may call need to use the instrumented ABI, so
        // we instrument it in a mode which preserves the original ABI.
        FnsWithNativeABI.insert(&F);

        // This code needs to rebuild the iterators, as they may be invalidated
        // by the push_back, taking care that the new range does not include
        // any functions added by this code.
        size_t N = i - FnsToInstrument.begin(),
               Count = e - FnsToInstrument.begin();
        FnsToInstrument.push_back(&F);
        i = FnsToInstrument.begin() + N;
        e = FnsToInstrument.begin() + Count;
      }
      // Hopefully, nobody will try to indirectly call a vararg
      // function... yet.
    } else if (FT->isVarArg()) {
      UnwrappedFnMap[&F] = &F;
      *i = nullptr;
    }
  }

  for (Function *i : FnsToInstrument) {
    if (!i || i->isDeclaration())
      continue;

    addContextRecording(*i);
    removeUnreachableBlocks(*i);

    TaintFunction TF(*this, i, FnsWithNativeABI.count(i));

    // TaintVisitor may create new basic blocks, which confuses df_iterator.
    // Build a copy of the list before iterating over it.
    SmallVector<BasicBlock *, 4> BBList(depth_first(&i->getEntryBlock()));

    for (BasicBlock *i : BBList) {
      //countEdge(M, *i);
      Instruction *Inst = &i->front();
      while (true) {
        // TaintVisitor may split the current basic block, changing the current
        // instruction's next pointer and moving the next instruction to the
        // tail block from which we should continue.
        Instruction *Next = Inst->getNextNode();
        // TaintVisitor may delete Inst, so keep track of whether it was a
        // terminator.
        bool IsTerminator = Inst->isTerminator();
        if (!TF.SkipInsts.count(Inst))
          TaintVisitor(TF).visit(Inst);
        if (IsTerminator)
          break;
        Inst = Next;
      }
    }

    // We will not necessarily be able to compute the shadow for every phi node
    // until we have visited every block.  Therefore, the code that handles phi
    // nodes adds them to the PHIFixups list so that they can be properly
    // handled here.
    for (std::vector<std::pair<PHINode *, PHINode *>>::iterator
        i = TF.PHIFixups.begin(),
        e = TF.PHIFixups.end();
        i != e; ++i) {
      for (unsigned val = 0, n = i->first->getNumIncomingValues(); val != n;
          ++val) {
        i->second->setIncomingValue(
            val, TF.getShadow(i->first->getIncomingValue(val)));
      }
    }

    // -dfsan-debug-nonzero-labels will split the CFG in all kinds of crazy
    // places (i.e. instructions in basic blocks we haven't even begun visiting
    // yet).  To make our life easier, do this work in a pass after the main
    // instrumentation.
    if (ClDebugNonzeroLabels) {
      for (Value *V : TF.NonZeroChecks) {
        Instruction *Pos;
        if (Instruction *I = dyn_cast<Instruction>(V))
          Pos = I->getNextNode();
        else
          Pos = &TF.F->getEntryBlock().front();
        while (isa<PHINode>(Pos) || isa<AllocaInst>(Pos))
          Pos = Pos->getNextNode();
        IRBuilder<> IRB(Pos);
        Value *Ne = IRB.CreateICmpNE(V, TF.TT.ZeroShadow);
        BranchInst *BI = cast<BranchInst>(SplitBlockAndInsertIfThen(
              Ne, Pos, /*Unreachable=*/false, ColdCallWeights));
        IRBuilder<> ThenIRB(BI);
        ThenIRB.CreateCall(TF.TT.TaintNonzeroLabelFn, {});
      }
    }
  }

  return false;
}

Value *TaintFunction::getArgTLSPtr() {
  if (ArgTLSPtr)
    return ArgTLSPtr;
  if (TT.ArgTLS)
    return ArgTLSPtr = TT.ArgTLS;

  IRBuilder<> IRB(&F->getEntryBlock().front());
  return ArgTLSPtr = IRB.CreateCall(TT.GetArgTLS, {});
}

Value *TaintFunction::getRetvalTLS() {
  if (RetvalTLSPtr)
    return RetvalTLSPtr;
  if (TT.RetvalTLS)
    return RetvalTLSPtr = TT.RetvalTLS;

  IRBuilder<> IRB(&F->getEntryBlock().front());
  return RetvalTLSPtr = IRB.CreateCall(TT.GetRetvalTLS, {});
}

Value *TaintFunction::getArgTLS(unsigned Idx, Instruction *Pos) {
  IRBuilder<> IRB(Pos);
  return IRB.CreateConstGEP2_64(getArgTLSPtr(), 0, Idx);
}

Value *TaintFunction::getShadow(Value *V) {
  if (!isa<Argument>(V) && !isa<Instruction>(V))
    return TT.ZeroShadow;
  Value *&Shadow = ValShadowMap[V];
  if (!Shadow) {
    if (Argument *A = dyn_cast<Argument>(V)) {
      if (IsNativeABI)
        return TT.ZeroShadow;
      switch (IA) {
        case Taint::IA_TLS: {
                              Value *ArgTLSPtr = getArgTLSPtr();
                              Instruction *ArgTLSPos =
                                TT.ArgTLS ? &*F->getEntryBlock().begin()
                                : cast<Instruction>(ArgTLSPtr)->getNextNode();
                              IRBuilder<> IRB(ArgTLSPos);
                              Shadow = IRB.CreateLoad(getArgTLS(A->getArgNo(), ArgTLSPos));
                              break;
                            }
        case Taint::IA_Args: {
                               unsigned ArgIdx = A->getArgNo() + F->arg_size() / 2;
                               Function::arg_iterator i = F->arg_begin();
                               while (ArgIdx--)
                                 ++i;
                               Shadow = &*i;
                               assert(Shadow->getType() == TT.ShadowTy);
                               break;
                             }
      }
      NonZeroChecks.push_back(Shadow);
    } else {
      Shadow = TT.ZeroShadow;
    }
  }
  return Shadow;
}

void TaintFunction::setShadow(Instruction *I, Value *Shadow) {
  assert(!ValShadowMap.count(I));
  assert(Shadow->getType() == TT.ShadowTy);
  ValShadowMap[I] = Shadow;
}

Value *Taint::getShadowAddress(Value *Addr, Instruction *Pos) {
  assert(Addr != RetvalTLS && "Reinstrumenting?");
  IRBuilder<> IRB(Pos);
  Value *ShadowPtrMaskValue;
  if (TaintRuntimeShadowMask)
    ShadowPtrMaskValue = IRB.CreateLoad(IntptrTy, ExternalShadowMask);
  else
    ShadowPtrMaskValue = ShadowPtrMask;
  return IRB.CreateIntToPtr(
      IRB.CreateMul(
        IRB.CreateAnd(IRB.CreatePtrToInt(Addr, IntptrTy),
          IRB.CreatePtrToInt(ShadowPtrMaskValue, IntptrTy)),
        ShadowPtrMul),
      ShadowPtrTy);
}

static inline bool isConstantOne(const Value *V) {
  if (const ConstantInt *CI = dyn_cast<ConstantInt>(V))
    return CI->isOne();
  return false;
}

Value *TaintFunction::combineBinaryOperatorShadows(BinaryOperator *BO,
    uint8_t op) {
  if (BO->getType()->isIntegerTy(1) &&
      BO->getOpcode() == Instruction::Xor &&
      (isConstantOne(BO->getOperand(1)) ||
       isConstantOne(BO->getOperand(0)))) {
    op = 1;
  }
  // else if (BinaryOperator::isNeg(BO))
  //   op = 2;
  Value *Shadow1 = getShadow(BO->getOperand(0));
  Value *Shadow2 = getShadow(BO->getOperand(1));
  Value *Shadow = combineShadows(Shadow1, Shadow2, op, BO);
  return Shadow;
}

Value *TaintFunction::combineShadows(Value *V1, Value *V2,
    uint16_t op,
    Instruction *Pos) {
  if (V1 == TT.ZeroShadow && V2 == TT.ZeroShadow) return V1;

  // filter types
  Type *Ty = Pos->getOperand(0)->getType();
  if (Ty->isFloatingPointTy()) {
    // check for FP
    if (!ClTraceFP)
      return TT.ZeroShadow;
  } else if (Ty->isVectorTy()) {
    // FIXME: vector type
    return TT.ZeroShadow;
  } else if (!Ty->isIntegerTy() && !Ty->isPointerTy()) {
    // not FP and not vector and not int and not ptr?
    errs() << "Unknown type: " << *Pos << "\n";
    return TT.ZeroShadow;
  }

  // filter size
  auto &DL = Pos->getModule()->getDataLayout();
  uint64_t size = DL.getTypeSizeInBits(Pos->getType());
  // FIXME: do not handle type larger than 64-bit
  if (size > 64) return TT.ZeroShadow;

  IRBuilder<> IRB(Pos);
  if (CmpInst *CI = dyn_cast<CmpInst>(Pos)) { // for both icmp and fcmp
    size = DL.getTypeSizeInBits(CI->getOperand(0)->getType());
    // op should be predicate
    op |= (CI->getPredicate() << 8);
  }
  Value *Op = ConstantInt::get(TT.Int16Ty, op);
  Value *Size = ConstantInt::get(TT.Int8Ty, size);
  Value *Op1 = Pos->getOperand(0);
  Ty = Op1->getType();
  // bitcast to integer before extending
  if (Ty->isHalfTy())
    Op1 = IRB.CreateBitCast(Op1, TT.Int16Ty);
  else if (Ty->isFloatTy())
    Op1 = IRB.CreateBitCast(Op1, TT.Int32Ty);
  else if (Ty->isDoubleTy())
    Op1 = IRB.CreateBitCast(Op1, TT.Int64Ty);
  else if (Ty->isPointerTy())
    Op1 = IRB.CreatePtrToInt(Op1, TT.Int64Ty);
  Op1 = IRB.CreateZExtOrTrunc(Op1, TT.Int64Ty);
  Value *Op2 = ConstantInt::get(TT.Int64Ty, 0);
  if (Pos->getNumOperands() > 1) {
    Op2 = Pos->getOperand(1);
    Ty = Op2->getType();
    // bitcast to integer before extending
    if (Ty->isHalfTy())
      Op2 = IRB.CreateBitCast(Op2, TT.Int16Ty);
    else if (Ty->isFloatTy())
      Op2 = IRB.CreateBitCast(Op2, TT.Int32Ty);
    else if (Ty->isDoubleTy())
      Op2 = IRB.CreateBitCast(Op2, TT.Int64Ty);
    else if (Ty->isPointerTy())
      Op2 = IRB.CreatePtrToInt(Op2, TT.Int64Ty);
    Op2 = IRB.CreateZExtOrTrunc(Op2, TT.Int64Ty);
  }
  CallInst *Call = IRB.CreateCall(TT.TaintUnionFn, {V1, V2, Op, Size, Op1, Op2});
  Call->addAttribute(AttributeList::ReturnIndex, Attribute::ZExt);
  Call->addParamAttr(0, Attribute::ZExt);
  Call->addParamAttr(1, Attribute::ZExt);
  return Call;
}

Value *TaintFunction::combineCastInstShadows(CastInst *CI,
    uint8_t op) {
  Value *Shadow1 = getShadow(CI->getOperand(0));
  Value *Shadow2 = TT.ZeroShadow;
  Value *Shadow = combineShadows(Shadow1, Shadow2, op, CI);
  return Shadow;
}

Value *TaintFunction::combineCmpInstShadows(CmpInst *CI,
    uint8_t op) {
  Value *Shadow1 = getShadow(CI->getOperand(0));
  Value *Shadow2 = getShadow(CI->getOperand(1));
  Value *Shadow = combineShadows(Shadow1, Shadow2, op, CI);
  return Shadow;
}

// Generates IR to load shadow corresponding to bytes [Addr, Addr+Size), where
// Addr has alignment Align, and take the union of each of those shadows.
Value *TaintFunction::loadShadow(Value *Addr, uint64_t Size, uint64_t Align,
    Instruction *Pos) {
  if (AllocaInst *AI = dyn_cast<AllocaInst>(Addr)) {
    const auto i = AllocaShadowMap.find(AI);
    if (i != AllocaShadowMap.end()) {
      IRBuilder<> IRB(Pos);
      return IRB.CreateLoad(i->second);
    }
  }

  SmallVector<Value *, 2> Objs;
  GetUnderlyingObjects(Addr, Objs, Pos->getModule()->getDataLayout());
  bool AllConstants = true;
  for (Value *Obj : Objs) {
    if (isa<Function>(Obj) || isa<BlockAddress>(Obj))
      continue;
    if (isa<GlobalVariable>(Obj) && cast<GlobalVariable>(Obj)->isConstant())
      continue;

    AllConstants = false;
    break;
  }
  if (AllConstants)
    return TT.ZeroShadow;

  Value *ShadowAddr = TT.getShadowAddress(Addr, Pos);
  if (Size == 0)
    return TT.ZeroShadow;

  IRBuilder<> IRB(Pos);
  CallInst *FallbackCall = IRB.CreateCall(
      TT.TaintUnionLoadFn, {ShadowAddr, ConstantInt::get(TT.IntptrTy, Size)});
  FallbackCall->addAttribute(AttributeList::ReturnIndex, Attribute::ZExt);
  return FallbackCall;
}

void TaintVisitor::visitLoadInst(LoadInst &LI) {
  if (LI.getMetadata("nosanitize")) return;
  auto &DL = LI.getModule()->getDataLayout();
  uint64_t Size = DL.getTypeStoreSize(LI.getType());
  if (Size == 0) {
    TF.setShadow(&LI, TF.TT.ZeroShadow);
    return;
  }

  uint64_t Align;
  if (ClPreserveAlignment) {
    Align = LI.getAlignment();
    if (Align == 0)
      Align = DL.getABITypeAlignment(LI.getType());
  } else {
    Align = 1;
  }
  IRBuilder<> IRB(&LI);
  Value *Shadow = TF.loadShadow(LI.getPointerOperand(), Size, Align, &LI);
#if 0
  //FIXME: tainted pointer
  if (ClCombinePointerLabelsOnLoad) {
    Value *PtrShadow = TF.getShadow(LI.getPointerOperand());
    Shadow = TF.combineShadows(Shadow, PtrShadow, &LI);
  }
#endif
  if (Shadow != TF.TT.ZeroShadow)
    TF.NonZeroChecks.push_back(Shadow);

  TF.setShadow(&LI, Shadow);
}

void TaintFunction::storeShadow(Value *Addr, uint64_t Size, uint64_t Align,
    Value *Shadow, Instruction *Pos) {
  if (AllocaInst *AI = dyn_cast<AllocaInst>(Addr)) {
    const auto i = AllocaShadowMap.find(AI);
    if (i != AllocaShadowMap.end()) {
      IRBuilder<> IRB(Pos);
      IRB.CreateStore(Shadow, i->second);
      return;
    }
  }

  uint64_t ShadowAlign = Align * TT.ShadowWidth / 8;
  IRBuilder<> IRB(Pos);
  Value *ShadowAddr = TT.getShadowAddress(Addr, Pos);
  if (Shadow == TT.ZeroShadow) {
    IntegerType *ShadowTy = IntegerType::get(*TT.Ctx, Size * TT.ShadowWidth);
    Value *ExtZeroShadow = ConstantInt::get(ShadowTy, 0);
    Value *ExtShadowAddr =
      IRB.CreateBitCast(ShadowAddr, PointerType::getUnqual(ShadowTy));
    IRB.CreateAlignedStore(ExtZeroShadow, ExtShadowAddr, ShadowAlign);
    return;
  }

  IRB.CreateCall(TT.TaintUnionStoreFn,
      {Shadow, ShadowAddr, ConstantInt::get(TT.IntptrTy, Size)});
}

void TaintVisitor::visitStoreInst(StoreInst &SI) {
  if (SI.getMetadata("nosanitize")) return;
  if (TF.StoreInsts.count(&SI)) return;
  auto &DL = SI.getModule()->getDataLayout();
  uint64_t Size = DL.getTypeStoreSize(SI.getValueOperand()->getType());
  if (Size == 0)
    return;

  uint64_t Align;
  if (ClPreserveAlignment) {
    Align = SI.getAlignment();
    if (Align == 0)
      Align = DL.getABITypeAlignment(SI.getValueOperand()->getType());
  } else {
    Align = 1;
  }

  Value* Shadow = TF.getShadow(SI.getValueOperand());
#if 0
  //FIXME: tainted pointer
  if (ClCombinePointerLabelsOnStore) {
    Value *PtrShadow = TF.getShadow(SI.getPointerOperand());
    Shadow = TF.combineShadows(Shadow, PtrShadow, &SI);
  }
#endif
  TF.storeShadow(SI.getPointerOperand(), Size, Align, Shadow, &SI);
}

void TaintVisitor::visitBinaryOperator(BinaryOperator &BO) {
  if (BO.getMetadata("nosanitize")) return;
  if (BO.getType()->isFloatingPointTy()) return;
  Value *CombinedShadow =
    TF.combineBinaryOperatorShadows(&BO, BO.getOpcode());
  TF.setShadow(&BO, CombinedShadow);
}

void TaintVisitor::visitCastInst(CastInst &CI) {
  if (CI.getMetadata("nosanitize")) return;
  Value *CombinedShadow =
    TF.combineCastInstShadows(&CI, CI.getOpcode());
  TF.setShadow(&CI, CombinedShadow);
}

void TaintFunction::visitCmpInst(CmpInst *I) {
  Module *M = F->getParent();
  auto &DL = M->getDataLayout();
  IRBuilder<> IRB(I);
  // get operand
  Value *Op1 = I->getOperand(0);
  unsigned size = DL.getTypeSizeInBits(Op1->getType());
  ConstantInt *Size = ConstantInt::get(TT.ShadowTy, size);
  Value *Op2 = I->getOperand(1);
  Value *Op1Shadow = getShadow(Op1);
  Value *Op2Shadow = getShadow(Op2);
  Op1 = IRB.CreateZExtOrTrunc(Op1, TT.Int64Ty);
  Op2 = IRB.CreateZExtOrTrunc(Op2, TT.Int64Ty);
  // get predicate
  int predicate = I->getPredicate();
  ConstantInt *Predicate = ConstantInt::get(TT.ShadowTy, predicate);

  IRB.CreateCall(TT.TaintTraceCmpFn, {Op1Shadow, Op2Shadow, Size, Predicate,
      Op1, Op2});
}

void TaintVisitor::visitCmpInst(CmpInst &CI) {
  if (CI.getMetadata("nosanitize")) return;
  // FIXME: integer only now
  if (!ClTraceFP && !isa<ICmpInst>(CI)) return;
#if 0 //TODO make an option
  TF.visitCmpInst(&CI);
#endif
  Value *CombinedShadow =
    TF.combineCmpInstShadows(&CI, CI.getOpcode());
  TF.setShadow(&CI, CombinedShadow);
}

void TaintFunction::visitSwitchInst(SwitchInst *I) {
  Module *M = F->getParent();
  auto &DL = M->getDataLayout();
  // get operand
  Value *Cond = I->getCondition();
  Value *CondShadow = getShadow(Cond);
  if (CondShadow == TT.ZeroShadow)
    return;
  unsigned size = DL.getTypeSizeInBits(Cond->getType());
  ConstantInt *Size = ConstantInt::get(TT.ShadowTy, size);
  ConstantInt *Predicate = ConstantInt::get(TT.ShadowTy, 32); // EQ, ==

  for (auto C : I->cases()) {
    Value *CV = C.getCaseValue();

    IRBuilder<> IRB(I);
    Cond = IRB.CreateZExtOrTrunc(Cond, TT.Int64Ty);
    CV = IRB.CreateZExtOrTrunc(CV, TT.Int64Ty);
    IRB.CreateCall(TT.TaintTraceCmpFn, {CondShadow, TT.ZeroShadow, Size, Predicate,
        Cond, CV});
  }
}

void TaintVisitor::visitSwitchInst(SwitchInst &SWI) {
  if (SWI.getMetadata("nosanitize")) return;
  TF.visitSwitchInst(&SWI);
}

void TaintFunction::visitGEPInst(GetElementPtrInst *I) {
  IRBuilder<> IRB(I);
  Type *ET = I->getPointerOperandType();
  for (auto &idx: I->indices()) {
    Value *Index = &*idx;
    CompositeType *CT = dyn_cast<CompositeType>(ET);
    if (!CT) {
      // at least pointer type?
      if (PointerType *PT = dyn_cast<PointerType>(ET)) {
        ET = PT->getElementType();
        continue;
      } else {
        break;
      }
    }
    ET = CT->getTypeAtIndex(Index);
    if (isa<Constant>(Index)) continue;
    if (!CT->isArrayTy()) continue; // only care about array?

    Value *Shadow = getShadow(Index);
    if (Shadow != TT.ZeroShadow) {
      Index = IRB.CreateZExtOrTrunc(Index, TT.Int64Ty);
      IRB.CreateCall(TT.TaintTraceGEPFn, {Shadow, Index});
    }
  }
}

void TaintVisitor::visitGetElementPtrInst(GetElementPtrInst &GEPI) {
  if (!ClTraceGEPOffset) return;
  if (GEPI.getMetadata("nosanitize")) return;
  TF.visitGEPInst(&GEPI);
}

void TaintVisitor::visitExtractElementInst(ExtractElementInst &I) {
  //FIXME:
}

void TaintVisitor::visitInsertElementInst(InsertElementInst &I) {
  //FIXME:
}

void TaintVisitor::visitShuffleVectorInst(ShuffleVectorInst &I) {
  //FIXME:
}

void TaintVisitor::visitExtractValueInst(ExtractValueInst &I) {
  //FIXME:
}

void TaintVisitor::visitInsertValueInst(InsertValueInst &I) {
  //FIXME:
}

void TaintVisitor::visitAllocaInst(AllocaInst &I) {
  bool AllLoadsStores = true;
  for (User *U : I.users()) {
    if (isa<LoadInst>(U)) {
      continue;
    }
    if (StoreInst *SI = dyn_cast<StoreInst>(U)) {
      if (SI->getPointerOperand() == &I) {
        continue;
      }
    }

    AllLoadsStores = false;
    break;
  }
  if (AllLoadsStores) {
    IRBuilder<> IRB(&I);
    AllocaInst *AI = IRB.CreateAlloca(TF.TT.ShadowTy);
    TF.AllocaShadowMap[&I] = AI;
  }
  TF.setShadow(&I, TF.TT.ZeroShadow);
}

void TaintVisitor::visitSelectInst(SelectInst &I) {
  Value *Condition = I.getCondition();
  Value *TrueShadow = TF.getShadow(I.getTrueValue());
  Value *FalseShadow = TF.getShadow(I.getFalseValue());

  if (isa<VectorType>(Condition->getType())) {
    //FIXME:
    TF.setShadow(&I, TF.TT.ZeroShadow);
  } else {
    Value *ShadowSel;
    if (TrueShadow == FalseShadow) {
      ShadowSel = TrueShadow;
    } else {
      ShadowSel =
        SelectInst::Create(Condition, TrueShadow, FalseShadow, "", &I);
    }
    TF.visitCondition(Condition, &I);
    TF.setShadow(&I, ShadowSel);
  }
}

void TaintVisitor::visitMemSetInst(MemSetInst &I) {
  IRBuilder<> IRB(&I);
  Value *ValShadow = TF.getShadow(I.getValue());
  IRB.CreateCall(TF.TT.TaintSetLabelFn,
      {ValShadow, IRB.CreateBitCast(I.getDest(), Type::getInt8PtrTy(
            *TF.TT.Ctx)),
      IRB.CreateZExtOrTrunc(I.getLength(), TF.TT.IntptrTy)});
}

void TaintVisitor::visitMemTransferInst(MemTransferInst &I) {
  IRBuilder<> IRB(&I);
  Value *DestShadow = TF.TT.getShadowAddress(I.getDest(), &I);
  Value *SrcShadow = TF.TT.getShadowAddress(I.getSource(), &I);
  Value *LenShadow = IRB.CreateMul(
      I.getLength(),
      ConstantInt::get(I.getLength()->getType(), TF.TT.ShadowWidth / 8));
#if LLVM_VERSION_CODE < LLVM_VERSION(7, 0)
  Value *AlignShadow;
  if (ClPreserveAlignment) {
    AlignShadow = IRB.CreateMul(I.getAlignmentCst(),
        ConstantInt::get(I.getAlignmentCst()->getType(),
          TF.TT.ShadowWidth / 8));
  } else {
    AlignShadow = ConstantInt::get(I.getAlignmentCst()->getType(),
        TF.TT.ShadowWidth / 8);
  }
  Type *Int8Ptr = Type::getInt8PtrTy(*TF.TT.Ctx);
  DestShadow = IRB.CreateBitCast(DestShadow, Int8Ptr);
  SrcShadow = IRB.CreateBitCast(SrcShadow, Int8Ptr);
  IRB.CreateCall(I.getCalledValue(), {DestShadow, SrcShadow, LenShadow,
      AlignShadow, I.getVolatileCst()});
#else
  Type *Int8Ptr = Type::getInt8PtrTy(*TF.TT.Ctx);
  DestShadow = IRB.CreateBitCast(DestShadow, Int8Ptr);
  SrcShadow = IRB.CreateBitCast(SrcShadow, Int8Ptr);
  auto *MTI = cast<MemTransferInst>(
      IRB.CreateCall(I.getCalledValue(),
        {DestShadow, SrcShadow, LenShadow, I.getVolatileCst()}));
  if (ClPreserveAlignment) {
    MTI->setDestAlignment(I.getDestAlignment() * (TF.TT.ShadowWidth / 8));
    MTI->setSourceAlignment(I.getSourceAlignment() *
        (TF.TT.ShadowWidth / 8));
  } else {
    MTI->setDestAlignment(TF.TT.ShadowWidth / 8);
    MTI->setSourceAlignment(TF.TT.ShadowWidth / 8);
  }
#endif
}

void TaintVisitor::visitReturnInst(ReturnInst &RI) {
  if (!TF.IsNativeABI && RI.getReturnValue()) {
    switch (TF.IA) {
      case Taint::IA_TLS: {
                            Value *S = TF.getShadow(RI.getReturnValue());
                            IRBuilder<> IRB(&RI);
                            IRB.CreateStore(S, TF.getRetvalTLS());
                            break;
                          }
      case Taint::IA_Args: {
                             IRBuilder<> IRB(&RI);
                             Type *RT = TF.F->getFunctionType()->getReturnType();
                             Value *InsVal =
                               IRB.CreateInsertValue(UndefValue::get(RT), RI.getReturnValue(), 0);
                             Value *InsShadow =
                               IRB.CreateInsertValue(InsVal, TF.getShadow(RI.getReturnValue()), 1);
                             RI.setOperand(0, InsShadow);
                             break;
                           }
    }
  }
}

void TaintVisitor::visitCallSite(CallSite CS) {
  Function *F = CS.getCalledFunction();
  if ((F && F->isIntrinsic()) || isa<InlineAsm>(CS.getCalledValue())) {
    //visitOperandShadowInst(*CS.getInstruction());
    //llvm::errs() << *(CS.getCalledValue()) << "\n";
    return;
  }

  // Calls to this function are synthesized in wrappers, and we shouldn't
  // instrument them.
  if (F == TF.TT.TaintVarargWrapperFn)
    return;

  IRBuilder<> IRB(CS.getInstruction());

  // trace indirect call
  if (CS.getCalledFunction() == nullptr) {
    Value *Shadow = TF.getShadow(CS.getCalledValue());
    if (Shadow != TF.TT.ZeroShadow)
      IRB.CreateCall(TF.TT.TaintTraceIndirectCallFn, {Shadow});
  }

  // reset IRB
  IRB.SetInsertPoint(CS.getInstruction());

  DenseMap<Value *, Function *>::iterator i =
    TF.TT.UnwrappedFnMap.find(CS.getCalledValue());
  if (i != TF.TT.UnwrappedFnMap.end()) {
    Function *F = i->second;
    switch (TF.TT.getWrapperKind(F)) {
      case Taint::WK_Warning:
        CS.setCalledFunction(F);
        IRB.CreateCall(TF.TT.TaintUnimplementedFn,
            IRB.CreateGlobalStringPtr(F->getName()));
        TF.setShadow(CS.getInstruction(), TF.TT.ZeroShadow);
        return;
      case Taint::WK_Discard:
        CS.setCalledFunction(F);
        TF.setShadow(CS.getInstruction(), TF.TT.ZeroShadow);
        return;
      case Taint::WK_Functional:
        CS.setCalledFunction(F);
        //FIXME:
        // visitOperandShadowInst(*CS.getInstruction());
        return;
      case Taint::WK_Custom:
        // Don't try to handle invokes of custom functions, it's too complicated.
        // Instead, invoke the dfsw$ wrapper, which will in turn call the __dfsw_
        // wrapper.
        if (CallInst *CI = dyn_cast<CallInst>(CS.getInstruction())) {
          FunctionType *FT = F->getFunctionType();
          TransformedFunction CustomFn = TF.TT.getCustomFunctionType(FT);
          std::string CustomFName = "__dfsw_";
          CustomFName += F->getName();
          Constant *CustomF =
            TF.TT.Mod->getOrInsertFunction(CustomFName, CustomFn.TransformedType);
          if (Function *CustomFn = dyn_cast<Function>(CustomF)) {
            CustomFn->copyAttributesFrom(F);

            // Custom functions returning non-void will write to the return label.
            if (!FT->getReturnType()->isVoidTy()) {
              CustomFn->removeAttributes(AttributeList::FunctionIndex,
                  TF.TT.ReadOnlyNoneAttrs);
            }
          }

          std::vector<Value *> Args;

          CallSite::arg_iterator i = CS.arg_begin();
          for (unsigned n = FT->getNumParams(); n != 0; ++i, --n) {
            Type *T = (*i)->getType();
            FunctionType *ParamFT;
            if (isa<PointerType>(T) &&
                (ParamFT = dyn_cast<FunctionType>(
                                                  cast<PointerType>(T)->getElementType()))) {
              std::string TName = "dfst";
              TName += utostr(FT->getNumParams() - n);
              TName += "$";
              TName += F->getName();
              Constant *T = TF.TT.getOrBuildTrampolineFunction(ParamFT, TName);
              Args.push_back(T);
              Args.push_back(
                  IRB.CreateBitCast(*i, Type::getInt8PtrTy(*TF.TT.Ctx)));
            } else {
              Args.push_back(*i);
            }
          }

          i = CS.arg_begin();
          const unsigned ShadowArgStart = Args.size();
          for (unsigned n = FT->getNumParams(); n != 0; ++i, --n)
            Args.push_back(TF.getShadow(*i));

          if (FT->isVarArg()) {
            auto *LabelVATy = ArrayType::get(TF.TT.ShadowTy,
                CS.arg_size() - FT->getNumParams());
            auto *LabelVAAlloca = new AllocaInst(
                LabelVATy, getDataLayout().getAllocaAddrSpace(),
                "labelva", &TF.F->getEntryBlock().front());

            for (unsigned n = 0; i != CS.arg_end(); ++i, ++n) {
              auto LabelVAPtr = IRB.CreateStructGEP(LabelVATy, LabelVAAlloca, n);
              IRB.CreateStore(TF.getShadow(*i), LabelVAPtr);
            }

            Args.push_back(IRB.CreateStructGEP(LabelVATy, LabelVAAlloca, 0));
          }

          if (!FT->getReturnType()->isVoidTy()) {
            if (!TF.LabelReturnAlloca) {
              TF.LabelReturnAlloca =
                new AllocaInst(TF.TT.ShadowTy,
                    getDataLayout().getAllocaAddrSpace(),
                    "labelreturn", &TF.F->getEntryBlock().front());
            }
            Args.push_back(TF.LabelReturnAlloca);
          }

          for (i = CS.arg_begin() + FT->getNumParams(); i != CS.arg_end(); ++i)
            Args.push_back(*i);

          CallInst *CustomCI = IRB.CreateCall(CustomF, Args);
          CustomCI->setCallingConv(CI->getCallingConv());
#if LLVM_VERSION_CODE <= LLVM_VERSION(5, 0)
          CustomCI->setAttributes(CI->getAttributes());
#else
          CustomCI->setAttributes(TransformFunctionAttributes(
                CustomFn, CI->getContext(), CI->getAttributes()));

          // Update the parameter attributes of the custom call instruction to
          // zero extend the shadow parameters. This is required for targets
          // which consider ShadowTy an illegal type.
          for (unsigned n = 0; n < FT->getNumParams(); n++) {
            const unsigned ArgNo = ShadowArgStart + n;
            if (CustomCI->getArgOperand(ArgNo)->getType() == TF.TT.ShadowTy) {
              CustomCI->addParamAttr(ArgNo, Attribute::ZExt);
              CustomCI->removeParamAttr(ArgNo, Attribute::NonNull);
            }
          }
#endif
          if (!FT->getReturnType()->isVoidTy()) {
            LoadInst *LabelLoad = IRB.CreateLoad(TF.LabelReturnAlloca);
            TF.setShadow(CustomCI, LabelLoad);
          }
          CI->replaceAllUsesWith(CustomCI);
          CI->eraseFromParent();
          return;
        }
        break;
    }
  }

  FunctionType *FT = cast<FunctionType>(
      CS.getCalledValue()->getType()->getPointerElementType());
  if (TF.TT.getInstrumentedABI() == Taint::IA_TLS) {
    for (unsigned i = 0, n = FT->getNumParams(); i != n; ++i) {
      IRB.CreateStore(TF.getShadow(CS.getArgument(i)),
          TF.getArgTLS(i, CS.getInstruction()));
    }
  }

  Instruction *Next = nullptr;
  if (!CS.getType()->isVoidTy()) {
    if (InvokeInst *II = dyn_cast<InvokeInst>(CS.getInstruction())) {
      if (II->getNormalDest()->getSinglePredecessor()) {
        Next = &II->getNormalDest()->front();
      } else {
        BasicBlock *NewBB =
          SplitEdge(II->getParent(), II->getNormalDest(), &TF.DT);
        Next = &NewBB->front();
      }
    } else {
      assert(CS->getIterator() != CS->getParent()->end());
      Next = CS->getNextNode();
    }

    if (TF.TT.getInstrumentedABI() == Taint::IA_TLS) {
      IRBuilder<> NextIRB(Next);
      LoadInst *LI = NextIRB.CreateLoad(TF.getRetvalTLS());
      TF.SkipInsts.insert(LI);
      TF.setShadow(CS.getInstruction(), LI);
      TF.NonZeroChecks.push_back(LI);
    }
  }

  // Do all instrumentation for IA_Args down here to defer tampering with the
  // CFG in a way that SplitEdge may be able to detect.
  if (TF.TT.getInstrumentedABI() == Taint::IA_Args) {
    FunctionType *NewFT = TF.TT.getArgsFunctionType(FT);
    Value *Func =
      IRB.CreateBitCast(CS.getCalledValue(), PointerType::getUnqual(NewFT));
    std::vector<Value *> Args;

    CallSite::arg_iterator i = CS.arg_begin(), e = CS.arg_end();
    for (unsigned n = FT->getNumParams(); n != 0; ++i, --n)
      Args.push_back(*i);

    i = CS.arg_begin();
    for (unsigned n = FT->getNumParams(); n != 0; ++i, --n)
      Args.push_back(TF.getShadow(*i));

    if (FT->isVarArg()) {
      unsigned VarArgSize = CS.arg_size() - FT->getNumParams();
      ArrayType *VarArgArrayTy = ArrayType::get(TF.TT.ShadowTy, VarArgSize);
      AllocaInst *VarArgShadow =
        new AllocaInst(VarArgArrayTy, getDataLayout().getAllocaAddrSpace(),
            "", &TF.F->getEntryBlock().front());
      Args.push_back(IRB.CreateConstGEP2_32(VarArgArrayTy, VarArgShadow, 0, 0));
      for (unsigned n = 0; i != e; ++i, ++n) {
        IRB.CreateStore(
            TF.getShadow(*i),
            IRB.CreateConstGEP2_32(VarArgArrayTy, VarArgShadow, 0, n));
        Args.push_back(*i);
      }
    }

    CallSite NewCS;
    if (InvokeInst *II = dyn_cast<InvokeInst>(CS.getInstruction())) {
      NewCS = IRB.CreateInvoke(Func, II->getNormalDest(), II->getUnwindDest(),
          Args);
    } else {
      NewCS = IRB.CreateCall(Func, Args);
    }
    NewCS.setCallingConv(CS.getCallingConv());
    NewCS.setAttributes(CS.getAttributes().removeAttributes(
          *TF.TT.Ctx, AttributeList::ReturnIndex,
          AttributeFuncs::typeIncompatible(NewCS.getInstruction()->getType())));

    if (Next) {
      ExtractValueInst *ExVal =
        ExtractValueInst::Create(NewCS.getInstruction(), 0, "", Next);
      TF.SkipInsts.insert(ExVal);
      ExtractValueInst *ExShadow =
        ExtractValueInst::Create(NewCS.getInstruction(), 1, "", Next);
      TF.SkipInsts.insert(ExShadow);
      TF.setShadow(ExVal, ExShadow);
      TF.NonZeroChecks.push_back(ExShadow);

      CS.getInstruction()->replaceAllUsesWith(ExVal);
    }

    CS.getInstruction()->eraseFromParent();
  }
}

void TaintVisitor::visitPHINode(PHINode &PN) {
  PHINode *ShadowPN =
    PHINode::Create(TF.TT.ShadowTy, PN.getNumIncomingValues(), "", &PN);

  // Give the shadow phi node valid predecessors to fool SplitEdge into working.
  Value *UndefShadow = UndefValue::get(TF.TT.ShadowTy);
  for (PHINode::block_iterator i = PN.block_begin(), e = PN.block_end(); i != e;
      ++i) {
    ShadowPN->addIncoming(UndefShadow, *i);
  }

  TF.PHIFixups.push_back(std::make_pair(&PN, ShadowPN));
  TF.setShadow(&PN, ShadowPN);
}

void TaintFunction::visitCondition(Value *Condition, Instruction *I) {
  IRBuilder<> IRB(I);
  // get operand
  Value *Shadow = getShadow(Condition);
  if (Shadow == TT.ZeroShadow)
    return;
  IRB.CreateCall(TT.TaintTraceCondFn, {Shadow, Condition});
}

void TaintVisitor::visitBranchInst(BranchInst &BR) {
  if (BR.getMetadata("nosanitize")) return;
  if (BR.isUnconditional()) return;
  TF.visitCondition(BR.getCondition(), &BR);
}

static RegisterPass<Taint> X("taint_pass", "Taint Pass");

static void registerTaintPass(const PassManagerBuilder &,
    legacy::PassManagerBase &PM) {

  PM.add(new Taint());
}

static RegisterStandardPasses
RegisterTaintPass(PassManagerBuilder::EP_OptimizerLast,
    registerTaintPass);

static RegisterStandardPasses
RegisterTaintPass0(PassManagerBuilder::EP_EnabledOnOptLevel0,
    registerTaintPass);
