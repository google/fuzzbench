#ifndef UNION_UTIL_H
#define UNION_UTIL_H

#include "sanitizer_common/sanitizer_internal_defs.h"
#include "dfsan.h"

using __sanitizer::uptr;
using __sanitizer::u32;

namespace __taint {

class option {
  bool isa;
  dfsan_label content;
public:
  option(bool, dfsan_label);
  bool operator==(option rhs);
  bool operator!=(option rhs);
  dfsan_label operator*();
};

option some_dfsan_label(dfsan_label x);
option none();

bool operator==(const dfsan_label_info& lhs, 
    const dfsan_label_info& rhs);

} // namespace

#endif // UNION_UTIL_H
