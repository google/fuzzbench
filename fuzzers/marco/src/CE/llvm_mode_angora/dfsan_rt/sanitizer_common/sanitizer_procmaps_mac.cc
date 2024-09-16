//===-- sanitizer_procmaps_mac.cc -----------------------------------------===//
//
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
//
//===----------------------------------------------------------------------===//
//
// Information about the process mappings (Mac-specific parts).
//===----------------------------------------------------------------------===//

#include "sanitizer_platform.h"
#if SANITIZER_MAC
#include "sanitizer_common.h"
#include "sanitizer_placement_new.h"
#include "sanitizer_procmaps.h"

#include <mach-o/dyld.h>
#include <mach-o/loader.h>

namespace __sanitizer {

MemoryMappingLayout::MemoryMappingLayout(bool cache_enabled) {
  Reset();
}

MemoryMappingLayout::~MemoryMappingLayout() {
}

// More information about Mach-O headers can be found in mach-o/loader.h
// Each Mach-O image has a header (mach_header or mach_header_64) starting with
// a magic number, and a list of linker load commands directly following the
// header.
// A load command is at least two 32-bit words: the command type and the
// command size in bytes. We're interested only in segment load commands
// (LC_SEGMENT and LC_SEGMENT_64), which tell that a part of the file is mapped
// into the task's address space.
// The |vmaddr|, |vmsize| and |fileoff| fields of segment_command or
// segment_command_64 correspond to the memory address, memory size and the
// file offset of the current memory segment.
// Because these fields are taken from the images as is, one needs to add
// _dyld_get_image_vmaddr_slide() to get the actual addresses at runtime.

void MemoryMappingLayout::Reset() {
  // Count down from the top.
  // TODO(glider): as per man 3 dyld, iterating over the headers with
  // _dyld_image_count is thread-unsafe. We need to register callbacks for
  // adding and removing images which will invalidate the MemoryMappingLayout
  // state.
  current_image_ = _dyld_image_count();
  current_load_cmd_count_ = -1;
  current_load_cmd_addr_ = 0;
  current_magic_ = 0;
  current_filetype_ = 0;
}

// static
void MemoryMappingLayout::CacheMemoryMappings() {
  // No-op on Mac for now.
}

void MemoryMappingLayout::LoadFromCache() {
  // No-op on Mac for now.
}

// Next and NextSegmentLoad were inspired by base/sysinfo.cc in
// Google Perftools, https://github.com/gperftools/gperftools.

// NextSegmentLoad scans the current image for the next segment load command
// and returns the start and end addresses and file offset of the corresponding
// segment.
// Note that the segment addresses are not necessarily sorted.
template<u32 kLCSegment, typename SegmentCommand>
bool MemoryMappingLayout::NextSegmentLoad(
    uptr *start, uptr *end, uptr *offset,
    char filename[], uptr filename_size, uptr *protection) {
  const char* lc = current_load_cmd_addr_;
  current_load_cmd_addr_ += ((const load_command *)lc)->cmdsize;
  if (((const load_command *)lc)->cmd == kLCSegment) {
    const sptr dlloff = _dyld_get_image_vmaddr_slide(current_image_);
    const SegmentCommand* sc = (const SegmentCommand *)lc;
    if (start) *start = sc->vmaddr + dlloff;
    if (protection) {
      // Return the initial protection.
      *protection = sc->initprot;
    }
    if (end) *end = sc->vmaddr + sc->vmsize + dlloff;
    if (offset) {
      if (current_filetype_ == /*MH_EXECUTE*/ 0x2) {
        *offset = sc->vmaddr;
      } else {
        *offset = sc->fileoff;
      }
    }
    if (filename) {
      internal_strncpy(filename, _dyld_get_image_name(current_image_),
                       filename_size);
    }
    return true;
  }
  return false;
}

bool MemoryMappingLayout::Next(uptr *start, uptr *end, uptr *offset,
                               char filename[], uptr filename_size,
                               uptr *protection) {
  for (; current_image_ >= 0; current_image_--) {
    const mach_header* hdr = _dyld_get_image_header(current_image_);
    if (!hdr) continue;
    if (current_load_cmd_count_ < 0) {
      // Set up for this image;
      current_load_cmd_count_ = hdr->ncmds;
      current_magic_ = hdr->magic;
      current_filetype_ = hdr->filetype;
      switch (current_magic_) {
#ifdef MH_MAGIC_64
        case MH_MAGIC_64: {
          current_load_cmd_addr_ = (char*)hdr + sizeof(mach_header_64);
          break;
        }
#endif
        case MH_MAGIC: {
          current_load_cmd_addr_ = (char*)hdr + sizeof(mach_header);
          break;
        }
        default: {
          continue;
        }
      }
    }

    for (; current_load_cmd_count_ >= 0; current_load_cmd_count_--) {
      switch (current_magic_) {
        // current_magic_ may be only one of MH_MAGIC, MH_MAGIC_64.
#ifdef MH_MAGIC_64
        case MH_MAGIC_64: {
          if (NextSegmentLoad<LC_SEGMENT_64, struct segment_command_64>(
                  start, end, offset, filename, filename_size, protection))
            return true;
          break;
        }
#endif
        case MH_MAGIC: {
          if (NextSegmentLoad<LC_SEGMENT, struct segment_command>(
                  start, end, offset, filename, filename_size, protection))
            return true;
          break;
        }
      }
    }
    // If we get here, no more load_cmd's in this image talk about
    // segments.  Go on to the next image.
  }
  return false;
}

void MemoryMappingLayout::DumpListOfModules(
    InternalMmapVector<LoadedModule> *modules) {
  Reset();
  uptr cur_beg, cur_end, prot;
  InternalScopedString module_name(kMaxPathLength);
  for (uptr i = 0; Next(&cur_beg, &cur_end, 0, module_name.data(),
                        module_name.size(), &prot);
       i++) {
    const char *cur_name = module_name.data();
    if (cur_name[0] == '\0')
      continue;
    LoadedModule *cur_module = nullptr;
    if (!modules->empty() &&
        0 == internal_strcmp(cur_name, modules->back().full_name())) {
      cur_module = &modules->back();
    } else {
      modules->push_back(LoadedModule());
      cur_module = &modules->back();
      cur_module->set(cur_name, cur_beg);
    }
    cur_module->addAddressRange(cur_beg, cur_end, prot & kProtectionExecute);
  }
}

}  // namespace __sanitizer

#endif  // SANITIZER_MAC
