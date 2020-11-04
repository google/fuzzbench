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
"""Sanitizer ."""

SANITIZER_OPTIONS = {
    'handle_abort': 2,
    'handle_sigbus': 2,
    'handle_sigfpe': 2,
    'handle_segv': 2,
    'handle_sigill': 2,
    'symbolize': 1,
    'symbolize_inline_frames': 0,
}


def _join_memory_tool_options(options):
    """Joins a dict holding memory tool options into a string that can be set in
  the environment."""
    return ':'.join(
        '%s=%s' % (key, str(value)) for key, value in sorted(options.items()))


def set_sanitizer_options(env):
    """Sets sanitizer options in |env|."""
    env['ASAN_OPTIONS'] = _join_memory_tool_options(SANITIZER_OPTIONS)
    env['UBSAN_OPTIONS'] = _join_memory_tool_options(SANITIZER_OPTIONS)
