# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Sanitizer helpers."""

# Matches ClusterFuzz configuration.
# See https://github.com/google/clusterfuzz/blob/master/src/python/system/environment.py.
SANITIZER_OPTIONS = {
    'handle_abort': 2,
    'handle_sigbus': 2,
    'handle_sigfpe': 2,
    'handle_segv': 2,
    'handle_sigill': 2,
    'symbolize': 1,
    'symbolize_inline_frames': 0,
}
ADDITIONAL_ASAN_OPTIONS = {
    'alloc_dealloc_mismatch': 0,
    'allocator_may_return_null': 1,
    'allocator_release_to_os_interval_ms': 500,
    'allow_user_segv_handler': 0,
    'check_malloc_usable_size': 0,
    'detect_odr_violation': 0,
    'detect_leaks': 1,
    'detect_stack_use_after_return': 1,
    'fast_unwind_on_fatal': 0,
    'max_uar_stack_size_log': 16,
    'quarantine_size_mb': 64,
    'strict_memcmp': 1,
}
ADDITIONAL_UBSAN_OPTIONS = {
    'allocator_release_to_os_interval_ms': 500,
    'print_stacktrace': 1,
}


def _join_memory_tool_options(options):
    """Joins a dict holding memory tool options into a string that can be set in
  the environment."""
    return ':'.join(
        '%s=%s' % (key, str(value)) for key, value in sorted(options.items()))


def set_sanitizer_options(env, is_fuzz_run=False):
    """Sets sanitizer options in |env|."""
    sanitizer_options_filtered = dict(SANITIZER_OPTIONS)
    additional_ubsan_options_filtered = dict(ADDITIONAL_UBSAN_OPTIONS)
    if is_fuzz_run:
        # This is needed for fuzzing speed, also a requirement for AFL.
        sanitizer_options_filtered['symbolize'] = 0
        sanitizer_options_filtered['abort_on_error'] = 1

        additional_ubsan_options_filtered['print_stacktrace'] = 0

    env['ASAN_OPTIONS'] = _join_memory_tool_options({
        **sanitizer_options_filtered,
        **ADDITIONAL_ASAN_OPTIONS
    })
    env['UBSAN_OPTIONS'] = _join_memory_tool_options({
        **sanitizer_options_filtered,
        **additional_ubsan_options_filtered
    })
