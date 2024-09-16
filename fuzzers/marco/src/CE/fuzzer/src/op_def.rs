use num_derive::FromPrimitive;    

#[derive(FromPrimitive)]
pub enum RGD {
  Bool = 0,
  Constant,
  Read,
  Concat,
  Extract,
  ZExt,
  SExt,

  //Arithmetic
  Add,
  Sub,
  Mul,
  UDiv,
  SDiv,
  URem,
  SRem,
  Neg,

  //Bitwise
  Not,
  And,
  Or,
  Xor,
  Shl, LShr,
  AShr,

  // Relational
  Equal,
  Distinct,
  Ult,
  Ule,
  Ugt,
  Uge,
  Slt,
  Sle,
  Sgt,
  Sge,
  
  //Logical
  LOr,
  LAnd,
  LNot,

  //Special
  Ite,
  Load,
  Memcmp,
}

//Derived from llvm-6.0/llvm/IR/Instruction.def 
//and dfsan.h
pub const CONST_OFFSET: u32 = 1;
pub const DFSAN_READ: u32 = 0;
pub const DFSAN_NOT: u32 = 1;
pub const DFSAN_NEG: u32 = 2;
pub const DFSAN_ADD: u32 = 11;
pub const DFSAN_SUB: u32 = 13;
pub const DFSAN_MUL: u32 = 15;
pub const DFSAN_UDIV: u32 = 17;
pub const DFSAN_SDIV: u32 = 18;
pub const DFSAN_UREM: u32 = 20;
pub const DFSAN_SREM: u32 = 21;
pub const DFSAN_SHL: u32 = 23;
pub const DFSAN_LSHR: u32 = 24;
pub const DFSAN_ASHR: u32 = 25;
pub const DFSAN_AND: u32 = 26;
pub const DFSAN_OR: u32 = 27;
pub const DFSAN_XOR: u32 = 28;
pub const DFSAN_TRUNC: u32 = 36;
pub const DFSAN_ZEXT: u32 = 37;
pub const DFSAN_SEXT: u32 = 38;
pub const DFSAN_LOAD: u32 = 67;
pub const DFSAN_EXTRACT: u32 = 68;
pub const DFSAN_CONCAT: u32 = 69;
//relational
pub const DFSAN_BVEQ: u32 = 32;
pub const DFSAN_BVNEQ: u32 = 33;
pub const DFSAN_BVUGT: u32 = 34;
pub const DFSAN_BVUGE: u32 = 35;
pub const DFSAN_BVULT: u32 = 36;
pub const DFSAN_BVULE: u32 = 37;
pub const DFSAN_BVSGT: u32 = 38;
pub const DFSAN_BVSGE: u32 = 39;
pub const DFSAN_BVSLT: u32 = 40;
pub const DFSAN_BVSLE: u32 = 41;

