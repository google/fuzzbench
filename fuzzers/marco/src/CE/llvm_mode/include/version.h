
#ifndef _ANGORA_LLVM_VERSION_H
#define _ANGORA_LLVM_VERSION_H

#define LLVM_VERSION(major, minor) ((major)*100 + (minor))
#define LLVM_VERSION_CODE LLVM_VERSION(LLVM_VERSION_MAJOR, LLVM_VERSION_MINOR)

#if LLVM_VERSION_CODE >= LLVM_VERSION(5, 0)
#define LLVM_ATTRIBUTE_LIST AttributeList

#define LLVM_NEW_ALLOCINST(ty, name, insertp)                                  \
  (new AllocaInst(ty, getDataLayout().getAllocaAddrSpace(), name, insertp))

#define LLVM_REMOVE_ATTRIBUTE(func, attr, attrbuilder)                         \
  func->removeAttributes(attr, attrbuilder)

#else

#define LLVM_ATTRIBUTE_LIST AttributeSet

#define LLVM_NEW_ALLOCINST(ty, name, insertp)                                  \
  (new AllocaInst(ty, name, insertp))

#define LLVM_REMOVE_ATTRIBUTE(func, attr, attrbuilder)                         \
  func->removeAttributes(                                                      \
      attr, LLVM_ATTRIBUTE_LIST::get(func->getContext(), attr, attrbuilder))

#endif

#if LLVM_VERSION_CODE >= LLVM_VERSION(6, 0)

#define SCL_INSECTION(scl, section, prefix, query, category)                   \
  scl->inSection(section, prefix, query, category)

#define LLVM_ADD_PARAM_ATTR(func, argno, attr) func->addParamAttr(argno, attr)

#else

#define SCL_INSECTION(scl, section, prefix, query, category)                   \
  scl->inSection(prefix, query, category)

#define LLVM_ADD_PARAM_ATTR(func, argno, attr)                                 \
  func->addAttribute(argno + 1, attr)

#endif

#endif
