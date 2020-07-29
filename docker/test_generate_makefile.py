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
"""Generate Makefile test."""

import io
import sys

from docker import generate_makefile


def test_print_makefile_build():
    """Tests result of a makefile generation for an image."""

    name = 'afl-zlib-builder-intermediate'
    image = {
        'tag': 'builders/afl/zlib-intermediate',
        'context': 'fuzzers/afl',
        'dockerfile': 'fuzzers/afl/builder.Dockerfile',
        'depends_on': ['zlib-project-builder'],
        'build_arg': ['parent_image=gcr.io/fuzzbench/builders/benchmark/zlib']
    }

    generated_makefile_truth = """\
.afl-zlib-builder-intermediate: .zlib-project-builder
\tdocker build \\
\t--tag gcr.io/fuzzbench/builders/afl/zlib-intermediate \\
\t--build-arg BUILDKIT_INLINE_CACHE=1 \\
\t--cache-from gcr.io/fuzzbench/builders/afl/zlib-intermediate \\
\t--build-arg parent_image=gcr.io/fuzzbench/builders/benchmark/zlib \\
\t--file fuzzers/afl/builder.Dockerfile \\
\tfuzzers/afl

"""

    stdout = sys.stdout
    print_output = io.StringIO()
    sys.stdout = print_output

    generate_makefile.print_makefile(name, image)
    result = print_output.getvalue()
    sys.stdout = stdout

    assert result == generated_makefile_truth
