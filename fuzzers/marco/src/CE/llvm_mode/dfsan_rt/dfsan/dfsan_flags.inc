//===-- dfsan_flags.inc -----------------------------------------*- C++ -*-===//
//
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
//
//===----------------------------------------------------------------------===//
//
// DFSan runtime flags.
//
//===----------------------------------------------------------------------===//
#ifndef DFSAN_FLAG
# error "Define DFSAN_FLAG prior to including this file!"
#endif

// DFSAN_FLAG(Type, Name, DefaultValue, Description)
// See COMMON_FLAG in sanitizer_flags.inc for more details.

DFSAN_FLAG(bool, warn_unimplemented, true,
           "Whether to warn on unimplemented functions.")
DFSAN_FLAG(bool, warn_nonzero_labels, false,
           "Whether to warn on unimplemented functions.")
DFSAN_FLAG(
    bool, strict_data_dependencies, true,
    "Whether to propagate labels only when there is an obvious data dependency"
    "(e.g., when comparing strings, ignore the fact that the output of the"
    "comparison might be data-dependent on the content of the strings). This"
    "applies only to the custom functions defined in 'custom.c'.")
DFSAN_FLAG(const char *, dump_labels_at_exit, "", "The path of the file where "
                                                  "to dump the labels when the "
                                                  "program terminates.")
DFSAN_FLAG(const char *, taint_file, "", "The path of the file which "
                                         "will be tainted.")
DFSAN_FLAG(const char *, union_table, "union.txt", "union table.")
DFSAN_FLAG(const char *, output_dir, ".", "The path for output file.")
DFSAN_FLAG(int, instance_id, 0, "instance id for multi-instance fuzzing.")
DFSAN_FLAG(int, session_id, 0, "session/round id.")
DFSAN_FLAG(int, solver_select, 0, "solver select 1 for rgd 0 for z3.") 
DFSAN_FLAG(int, tid, 0, "taint file id") 
DFSAN_FLAG(int, shmid, 0, "shmid") 
DFSAN_FLAG(int, pipeid, 0, "pipeid") 
DFSAN_FLAG(int, inputid, 0, "input_id") 
