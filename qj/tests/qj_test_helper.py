#
# Copyright 2017 Google Inc.
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

"""Expose a function that allows testing qj's cross-module functionality.

See qj_test.py for usage.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import qj as qj_module


def LogToQJ(**kwargs):
  return qj(**kwargs)  # pylint: disable=undefined-variable


def LogToQJQJ(**kwargs):
  return qj_module.qj(**kwargs)
