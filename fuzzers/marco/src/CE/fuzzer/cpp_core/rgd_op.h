#ifndef __IR__H_
#define __IR__H_

namespace rgd {
	enum Kind {
		Bool, // 0
		Constant, // 1
		Read, // 2
		Concat, // 3
		Extract, // 4

		ZExt, // 5
		SExt, // 6

		// Arithmetic
		Add, // 7
		Sub, // 8
		Mul, // 9
		UDiv, // 10
		SDiv, // 11
		URem, // 12
		SRem, // 13
		Neg,  // 14

		// Bit
		Not, // 15
		And, // 16
		Or, // 17
		Xor, // 18
		Shl, // 19
		LShr, // 20
		AShr, // 21

		// Compare
		Equal, // 22
		Distinct, // 23
		Ult, // 24
		Ule, // 25
		Ugt, // 26
		Uge, // 27
		Slt, // 28
		Sle, // 29
		Sgt, // 30
		Sge, // 31

		// Logical
		LOr, // 32
		LAnd, // 33
		LNot, // 34

		// Special
		Ite, // 35
		Load, // 36    to be worked with TT-Fuzzer
		Memcmp, //37
	};
}


//Derived from llvm-6.0/llvm/IR/Instruction.def
//and dfsan.h

const uint32_t  CONST_OFFSET = 1;
const uint32_t  DFSAN_READ = 0;
const uint32_t  DFSAN_NOT = 1;
const uint32_t  DFSAN_NEG = 2;
const uint32_t  DFSAN_ADD = 11;
const uint32_t  DFSAN_SUB = 13;
const uint32_t  DFSAN_MUL = 15;
const uint32_t  DFSAN_UDIV = 17;
const uint32_t  DFSAN_SDIV = 18;
const uint32_t  DFSAN_UREM = 20;
const uint32_t  DFSAN_SREM = 21;
const uint32_t  DFSAN_SHL = 23;
const uint32_t  DFSAN_LSHR = 24;
const uint32_t  DFSAN_ASHR = 25;
const uint32_t  DFSAN_AND = 26;
const uint32_t  DFSAN_OR = 27;
const uint32_t  DFSAN_XOR = 28;
const uint32_t  DFSAN_TRUNC = 36;
const uint32_t  DFSAN_ZEXT = 37;
const uint32_t  DFSAN_SEXT = 38;
const uint32_t  DFSAN_LOAD = 67;
const uint32_t  DFSAN_EXTRACT = 68;
const uint32_t  DFSAN_CONCAT = 69;
//relational
const uint32_t  DFSAN_BVEQ = 32;
const uint32_t  DFSAN_BVNEQ = 33;
const uint32_t  DFSAN_BVUGT = 34;
const uint32_t  DFSAN_BVUGE = 35;
const uint32_t  DFSAN_BVULT = 36;
const uint32_t  DFSAN_BVULE = 37;
const uint32_t  DFSAN_BVSGT = 38;
const uint32_t  DFSAN_BVSGE = 39;
const uint32_t  DFSAN_BVSLT = 40;
const uint32_t  DFSAN_BVSLE = 41;
const uint32_t  DFSAN_ICMP = 51;

#endif
