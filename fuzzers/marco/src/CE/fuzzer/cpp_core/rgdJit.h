#ifndef GRAD_JIT_H
#define GRAD_JIT_H

#include "llvm/ADT/STLExtras.h"
#include "llvm/ExecutionEngine/ExecutionEngine.h"
#include "llvm/ExecutionEngine/JITSymbol.h"
#include "llvm/ExecutionEngine/Orc/CompileOnDemandLayer.h"
#include "llvm/ExecutionEngine/Orc/Core.h"
#include "llvm/ExecutionEngine/Orc/CompileUtils.h"
#include "llvm/ExecutionEngine/Orc/ExecutionUtils.h"
#include "llvm/ExecutionEngine/Orc/IRCompileLayer.h"
#include "llvm/ExecutionEngine/Orc/IRTransformLayer.h"
#include "llvm/ExecutionEngine/Orc/LambdaResolver.h"
#include "llvm/ExecutionEngine/Orc/JITTargetMachineBuilder.h"
#include "llvm/ExecutionEngine/Orc/RTDyldObjectLinkingLayer.h"
#include "llvm/ExecutionEngine/RTDyldMemoryManager.h"
#include "llvm/ExecutionEngine/RuntimeDyld.h"
#include "llvm/ExecutionEngine/SectionMemoryManager.h"
#include "llvm/IR/DataLayout.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/IR/Mangler.h"
#include "llvm/Support/DynamicLibrary.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Target/TargetMachine.h"
#include "llvm/Transforms/InstCombine/InstCombine.h"
#include "llvm/Transforms/Scalar.h"
#include "llvm/Transforms/Scalar/GVN.h"
#include <algorithm>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <vector>

namespace rgd {

	class GradJit {
		private:
			llvm::orc::ExecutionSession ES;
			llvm::orc::RTDyldObjectLinkingLayer ObjectLayer;
			llvm::orc::IRCompileLayer CompileLayer;
			llvm::orc::IRTransformLayer OptimizeLayer;
			//std::unique_ptr<llvm::TargetMachine> TM;

			llvm::DataLayout DL;
			llvm::orc::MangleAndInterner Mangle;
//			llvm::orc::ThreadSafeContext Ctx;
		//	std::unique_ptr<llvm::orc::JITCompileCallbackManager> CompileCallbackManager;
	//		llvm::orc::CompileOnDemandLayer CODLayer;

		public:
			GradJit(llvm::orc::JITTargetMachineBuilder JTMB, llvm::DataLayout DL)
				: ObjectLayer(ES,
						[]() { return llvm::make_unique<llvm::SectionMemoryManager>(); }), 
			//		TM(llvm::EngineBuilder().selectTarget()),
				CompileLayer(ES, ObjectLayer, llvm::orc::ConcurrentIRCompiler(std::move(JTMB))),
				OptimizeLayer(ES, CompileLayer, optimizeModule),
				DL(std::move(DL)), Mangle(ES, this->DL)
			//	CompileCallbackManager(
       //   llvm::orc::createLocalCompileCallbackManager(TM->getTargetTriple(), ES, 0)),
     // CODLayer(ES, OptimizeLayer,
               //[this](llvm::Function &F) { return std::set<llvm::Function*>({&F}); },
      //         *CompileCallbackManager,
       //        llvm::orc::createLocalIndirectStubsManagerBuilder(
        //         TM->getTargetTriple()))
		//		Ctx(llvm::make_unique<llvm::LLVMContext>()) 
				{
					ES.getMainJITDylib().setGenerator(
							cantFail(llvm::orc::DynamicLibrarySearchGenerator::GetForCurrentProcess(
									DL.getGlobalPrefix())));
				}

			const llvm::DataLayout &getDataLayout() const { return DL; }
		//	llvm::LLVMContext &getContext() { return *Ctx.getContext(); }
	//		llvm::orc::ThreadSafeContext &getTSC() {return Ctx;}

			static llvm::Expected<std::unique_ptr<GradJit>> Create() {
				auto JTMB = llvm::orc::JITTargetMachineBuilder::detectHost();

				if (!JTMB)
					return JTMB.takeError();

				auto DL = JTMB->getDefaultDataLayoutForTarget();
				if (!DL)
					return DL.takeError();

				return llvm::make_unique<GradJit>(std::move(*JTMB), std::move(*DL));
			}


			llvm::Error addModule(std::unique_ptr<llvm::Module> M,
														std::unique_ptr<llvm::LLVMContext> ctx) {
				return OptimizeLayer.add(ES.getMainJITDylib(),
						llvm::orc::ThreadSafeModule(std::move(M), std::move(ctx)));
			}

			llvm::Expected<llvm::JITEvaluatedSymbol> lookup(llvm::StringRef Name) {
				return ES.lookup({&ES.getMainJITDylib()}, Mangle(Name.str()));
			}	
		private:
			static llvm::orc::ThreadSafeModule
				optimizeModule(llvm::orc::ThreadSafeModule TSM, const llvm::orc::MaterializationResponsibility &R) {
					// Create a function pass manager.
					auto FPM = llvm::make_unique<llvm::legacy::FunctionPassManager>(TSM.getModule());

					// Add some optimizations.
					FPM->add(llvm::createInstructionCombiningPass());
					FPM->add(llvm::createReassociatePass());
					FPM->add(llvm::createGVNPass());
					FPM->add(llvm::createCFGSimplificationPass());
					FPM->doInitialization();

					// Run the optimizations over all functions in the module being added to
					// the JIT.
					for (auto &F : *TSM.getModule())
						FPM->run(F);

					return TSM;
				}				
	};
}

#endif // LLVM_EXECUTIONENGINE_ORC_KALEIDOSCOPEJIT_H

