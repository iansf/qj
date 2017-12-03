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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import re
import sys

import unittest
import mock

from qj import qj
from qj.tests import qj_test_helper

DEBUG_TESTS = True


# pylint: disable=line-too-long
class RegExp(object):

  def __init__(self, pattern, flags=0):
    self._p = pattern
    self._f = flags

  def __eq__(self, o):
    if DEBUG_TESTS:
      print('%s: %s: \'%s\'' % ('pass' if bool(re.search(self._p, o, self._f)) else 'FAIL', str(self), str(o)))
    return bool(re.search(self._p, o, self._f))

  def __ne__(self, o):
    return not self.__eq__(o)

  def __repr__(self):
    return '<RegExp:(%s)>' % self._p


@unittest.skipIf(sys.version_info[0] < 3, 'Python 3+ required')
class QjTest(unittest.TestCase):

  def setUp(self):
    qj.LOG = True
    qj.LOG_FN = logging.info
    qj.MAX_FRAME_LOGS = 100
    qj.PREFIX = 'qj: '
    qj.COLOR = False
    qj._DEBUG_QJ = False

  def test_logs_no_s_with_splat_as_well(self):
    def with_splat_as_well():
      x = 2
      a = [None, False]
      aa = (False, False)
      qj(x, '', *a, *aa)

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      # qj._DEBUG_QJ = 1
      with_splat_as_well()
      mock_log_fn.assert_called_once_with(RegExp(
          r"qj: <qj_test> with_splat_as_well: x, '', \*a, \*aa <\d+>: 2"))


# pylint: enable=line-too-long
if __name__ == '__main__':
  unittest.main()
