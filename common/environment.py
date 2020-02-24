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
"""Environment functions."""

import ast
import os


def _eval_value(value_string):
    """Returns evaluated value."""
    try:
        return ast.literal_eval(value_string)
    except Exception:  # pylint: disable=broad-except
        # String fallback.
        return value_string


def get(environment_variable, default_value=None):
    """Return the value of |environment_variable| in the environment"""
    value_string = os.getenv(environment_variable)

    # value_string will be None if the variable is not defined.
    if value_string is None:
        return default_value

    # Evaluate the value of the environment variable with string fallback.
    return _eval_value(value_string)


# TODO(metzman): Use get and set everywhere instead of environ[]/setenv/getenv.
def set(environment_variable, value):  # pylint: disable=redefined-builtin
    """Set |environment_variable| to |value| in the environment."""
    value_str = str(value)
    environment_variable_str = str(environment_variable)
    os.environ[environment_variable_str] = value_str
