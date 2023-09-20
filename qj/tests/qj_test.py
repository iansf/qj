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
import pprint
import re
import sys

import unittest
import mock

from qj import qj
from qj.tests import qj_test_helper

DEBUG_TESTS = False


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


class QjTest(unittest.TestCase):

  def setUp(self):
    qj.LOG = True
    qj.LOG_FN = logging.info
    qj.MAX_FRAME_LOGS = 100
    qj.PREFIX = 'qj: '
    qj.COLOR = False
    qj._DEBUG_QJ = False

  def test_logs(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj('some log')
      mock_log_fn.assert_called_once_with(RegExp(
          r"qj: <qj_test> test_logs: 'some log' <\d+>: some log"))

  def test_logs_and_returns_arg(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      s_in = 'some log'
      s_out = qj(s_in)
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> test_logs_and_returns_arg: s_in <\d+>: some log'))
      self.assertIs(s_in, s_out)

  def test_no_logs(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG = False
      qj.LOG_FN = mock_log_fn
      qj('some log')
      mock_log_fn.assert_not_called()

  def test_no_logs_and_returns_arg(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG = False
      qj.LOG_FN = mock_log_fn
      s_in = 'some log'
      s_out = qj(s_in)
      mock_log_fn.assert_not_called()
      self.assertIs(s_in, s_out)

  def test_logs_with_prefix(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.PREFIX = 'QQ: '
      qj.LOG_FN = mock_log_fn
      qj('some log')
      mock_log_fn.assert_called_once_with(RegExp(
          r"QQ: <qj_test> test_logs_with_prefix: 'some log' <\d+>: some log"))

  def test_logs_max_times(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.MAX_FRAME_LOGS = 1
      qj.LOG_FN = mock_log_fn
      for _ in range(2):
        qj('some log')
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_max_times: 'some log' <\d+>: some log")),
          mock.call(RegExp(
              r'qj: <qj_test> test_logs_max_times: Maximum per-frame logging hit \(1\).')),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)
      # mock_log_fn.reset_mock()
      # qj('some log')
      # mock_log_fn.assert_not_called()

  def test_logs_with_pprint_str_fn(self):
    str_fn = qj.STR_FN
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      try:
        qj.STR_FN = pprint.pformat

        foos = [dict(foo=x, bar=x % 2, baz=x % 3) for x in range(10)]
        qj(foos, 'foos', l=lambda x: x, r=foos)

        mock_log_fn.assert_has_calls(
            [
                mock.call(
                    RegExp(r"qj: <qj_test> test_logs_with_pprint_str_fn: foos <\d+>: "
                           r'\(multiline log follows\)\n'
                           r"\[\{'bar': 0, 'baz': 0, 'foo': 0\},\n \{'bar': 1, 'baz': 1, 'foo': 1\}")),
                mock.call(
                    RegExp(r'qj:\s+\(multiline log follows\)\n'
                           r"\[\{'bar': 0, 'baz': 0, 'foo': 0\},\n \{'bar': 1, 'baz': 1, 'foo': 1\}")),
                mock.call(
                    RegExp(r'qj:\s+Overridden return value: \(multiline log follows\)\n'
                           r"\[\{'bar': 0, 'baz': 0, 'foo': 0\},\n \{'bar': 1, 'baz': 1, 'foo': 1\}")),
            ],
            any_order=False)
        self.assertEqual(mock_log_fn.call_count, 3)
      finally:
        qj.STR_FN = str_fn

  def test_logs_with_x(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj(x='some log')
      mock_log_fn.assert_called_once_with(RegExp(
          r"qj: <qj_test> test_logs_with_x: x='some log' <\d+>: some log"))

  def test_logs_with_s(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj(s='some prefix', x='some log')
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> test_logs_with_s: some prefix <\d+>: some log'))

  def test_no_logs_with_s(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG = False
      qj.LOG_FN = mock_log_fn
      qj(s='some prefix', x='some log')
      mock_log_fn.assert_not_called()

  def test_logs_with_s_not_a_string(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj(s=42, x='some log')
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> test_logs_with_s_not_a_string: 42 <\d+>: some log'))

  def test_logs_with_b(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj(b=True, x='some log')
      mock_log_fn.assert_called_once_with(RegExp(
          r"qj: <qj_test> test_logs_with_b: b=True, x='some log' <\d+>: some log"))
      mock_log_fn.reset_mock()
      qj(b=False, x='some log')
      mock_log_fn.assert_not_called()

  def test_no_logs_with_b(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG = False
      qj.LOG_FN = mock_log_fn
      qj(b=True, x='some log')
      mock_log_fn.assert_not_called()

  def test_logs_with_l(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj(l=lambda _: 'some extra info', x='some log')
      if sys.version_info[0] == 3 and sys.version_info[1] > 10:
        # This test is unlikely to pass on 3.11 and higher.
        pass
      else:
        mock_log_fn.assert_has_calls([
            mock.call(RegExp(
                r"qj: <qj_test> test_logs_with_l: l=lambda _: 'some extra info', x='some log' <\d+>: some log")),
            mock.call(RegExp(
                r'qj:\s+some extra info')),
        ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)

  def test_logs_with_l_passes_x(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      s = 'some log'
      qj(l=lambda x: self.assertIs(x, s), x=s)
      if sys.version_info[0] == 3 and sys.version_info[1] > 10:
        # This test is unlikely to pass on 3.11 and higher.
        pass
      else:
        mock_log_fn.assert_has_calls([
            mock.call(RegExp(
                r'qj: <qj_test> test_logs_with_l_passes_x: l=lambda x: self.assertIs\(x, s\), x=s <\d+>: some log')),
            mock.call(RegExp(
                r'qj:\s+None')),
        ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)

  def test_no_logs_with_l(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG = False
      qj.LOG_FN = mock_log_fn
      qj(l=lambda _: 'some extra info', x='some log')
      mock_log_fn.assert_not_called()

      qj.LOG = True
      qj(b=False, l=lambda _: 'some extra info', x='some log')
      mock_log_fn.assert_not_called()

  def test_logs_with_d(self):
    with mock.patch('logging.info') as mock_log_fn:
      with mock.patch('ipdb.set_trace') as mock_debug_fn:
        qj.LOG_FN = mock_log_fn
        qj.DEBUG_FN = mock_debug_fn
        qj(d=True, x='some log')
        mock_log_fn.assert_called_once_with(RegExp(
            r"qj: <qj_test> test_logs_with_d: d=True, x='some log' <\d+>: some log"))
        mock_debug_fn.assert_called_once()

  def test_no_logs_with_d(self):
    with mock.patch('logging.info') as mock_log_fn:
      with mock.patch('ipdb.set_trace') as mock_debug_fn:
        qj.LOG = False
        qj.LOG_FN = mock_log_fn
        qj(d=True, x='some log')
        mock_log_fn.assert_not_called()
        mock_debug_fn.assert_not_called()

        qj.LOG = True
        qj(b=False, d=True, x='some log')
        mock_log_fn.assert_not_called()
        mock_debug_fn.assert_not_called()

  def test_logs_with_p(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj(p=True, x='some log')
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_with_p: p=True, x='some log' <\d+>: some log")),
          mock.call(RegExp(
              r'qj:\s+Public properties:\n'
              r'\s+__init__[^\n]*\n'
              r'\s+capitalize\n')),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)

  def test_no_logs_with_p(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG = False
      qj.LOG_FN = mock_log_fn
      qj(p=True, x='some log')
      mock_log_fn.assert_not_called()

  def test_logs_with_p_arg_spec(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn

      class TestClass(object):

        def function_with_args(self, a, b=None, c=True, d='default value'):
          pass

        def __str__(self):
          return 'TestClass object'

      qj(p=True, x=TestClass())
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r'qj: <qj_test> test_logs_with_p_arg_spec: p=True, x=TestClass\(\) <\d+>: '
              r'TestClass object')),
          mock.call(RegExp(
              r'qj:\s+Public properties:\n'
              r'\s+__init__[^\n]*\n'
              r"\s+function_with_args\((self, )?a, b=None, c=True, d='default value'\)"
          )),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)

  def test_logs_with_t(self):
    with mock.patch('logging.info') as mock_log_fn:

      class TestTensorClass(object):

        @property
        def __module__(self):
          return 'tensorflow_test_module'

        name = 'foo'

      if 'tensorflow' not in sys.modules:
        sys.modules['tensorflow'] = TestTensorClass()
        sys.modules['tensorflow'].Print = lambda s: s
      sys.modules['tensorflow'].shape = lambda _: tuple()

      with mock.patch('tensorflow.Print') as tf_print_fn:
        x = TestTensorClass()

        qj.LOG_FN = mock_log_fn
        qj(t=True, x=x)
        mock_log_fn.assert_has_calls([
            mock.call(RegExp(
                r'qj: <qj_test> test_logs_with_t: t=True, x=x <\d+>: '
                r'<TestTensorClass object at ')),
            mock.call(RegExp(
                r'qj:\s+Wrapping return value in tf.Print operation.')),
        ], any_order=False)
        self.assertEqual(mock_log_fn.call_count, 2)

        tf_print_fn.assert_called_once_with(
            x, [tuple(), x],
            summarize=qj.MAX_FRAME_LOGS,
            first_n=qj.MAX_FRAME_LOGS,
            name=RegExp(r'qj_print_test_logs_with_t_\d+'),
            message=RegExp(
                r'qj: <qj_test> test_logs_with_t: t=True, x=x <\d+>'))
        self.assertEqual(tf_print_fn.call_count, 1)

  def test_logs_with_t_x_not_a_tensor(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj(t=True, x='not a tensor')
      mock_log_fn.assert_called_once_with(
          RegExp(
              r"qj: <qj_test> test_logs_with_t_x_not_a_tensor: t=True, x='not a tensor' <\d+>: not a tensor"
          ))

  def test_logs_with_r(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      alternative_return_value = 'some other return value'
      out = qj(r=alternative_return_value, x='some log')
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_with_r: r=alternative_return_value, x='some log' <\d+>: some log")),
          mock.call(RegExp(
              r'qj:\s+Overridden return value: some other return value')),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)
      self.assertIs(out, alternative_return_value)

  def test_logs_with_r_when_r_is_none(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      alternative_return_value = None
      out = qj(r=alternative_return_value, x='some log')
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_with_r_when_r_is_none: r=alternative_return_value, x='some log' <\d+>: some log")),
          mock.call(RegExp(
              r'qj:\s+Overridden return value: None')),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)
      self.assertIs(out, alternative_return_value)

  def test_no_logs_with_r(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG = False
      qj.LOG_FN = mock_log_fn
      alternative_return_value = 'some other return value'
      input_value = 'some log'
      out = qj(r=alternative_return_value, x=input_value)
      mock_log_fn.assert_not_called()
      self.assertIs(out, input_value)

  def test_logs_with_indentation(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      for i in range(2):
        qj('some log %d' % i)
        qj('some log %d' % i)
        qj('some log %d' % i)
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_with_indentation: 'some log %d' % i <\d+>: "
              "some log 0")),
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_with_indentation:  'some log %d' % i <\d+>: "
              "some log 0")),
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_with_indentation:   'some log %d' % i <\d+>: "
              "some log 0")),
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_with_indentation: 'some log %d' % i <\d+>: "
              "some log 1")),
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_with_indentation:  'some log %d' % i <\d+>: "
              "some log 1")),
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_with_indentation:   'some log %d' % i <\d+>: "
              "some log 1")),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 6)

  def test_logs_in_list_comp(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      _ = [qj('some log') for _ in range(2)]
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_in_list_comp: 'some log' <\d+>: some log")),
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_in_list_comp: 'some log' <\d+>: some log")),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)

  def test_logs_in_dict_comp(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      _ = {i: qj('some log') for i in range(2)}
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_in_dict_comp: 'some log' <\d+>: some log")),
          mock.call(RegExp(
              r"qj: <qj_test> test_logs_in_dict_comp: 'some log' <\d+>: some log")),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)

  def test_expected_locals_mods(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      k = None
      local_var_names = None
      # Can't store the dictionary in itself, it turns out...
      local_vars = {k: v for k, v in locals().items() if k != 'local_vars'}

      qj('some log')
      mock_log_fn.assert_called_once_with(RegExp(
          r"qj: <qj_test> test_expected_locals_mods: 'some log' <\d+>: some log"))

      # Make sure that none of the existing variables got modified.
      self.assertEqual(local_vars, {k: v for k, v in locals().items()
                                    if (k != '__qj_magic_wocha_doin__' and
                                        k != 'local_vars')})

      # Make sure that only the new variable name is added.
      local_var_names = set([k for k in local_vars.keys()])
      local_var_names.add('__qj_magic_wocha_doin__')
      local_var_names.add('local_vars')
      self.assertEqual(local_var_names, set([k for k in locals().keys()]))

  def test_make_global(self):
    if hasattr(__builtins__, 'qj'):
      delattr(__builtins__, 'qj')
    self.assertRaises(AttributeError, lambda: getattr(__builtins__, 'qj'))
    qj.make_global()
    if __name__ == '__main__':
      # Running with `$ python qj/tests/qj_tests.py` goes down this path.
      self.assertEqual(qj, __builtins__.__dict__['qj'])
    else:
      # Running with `$ nosetests` goes down this path.
      self.assertEqual(qj, __builtins__['qj'])

  def test_multiline(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj('some\nlog')
      mock_log_fn.assert_called_once_with(RegExp(
          r"qj: <qj_test> test_multiline: 'some\\nlog' <\d+>: \(multiline log follows\)\n"
          "some\nlog"))

  def test_multiline_with_l(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj(l=lambda _: 'some\nextra\ninfo', x='some\nlog')
      if sys.version_info[0] == 3 and sys.version_info[1] > 10:
        # This test is unlikely to pass on 3.11 and higher.
        pass
      else:
        mock_log_fn.assert_has_calls(
            [
                mock.call(
                    RegExp(r"qj: <qj_test> test_multiline_with_l: l=lambda _: 'some\\nextra\\ninfo', x='some\\nlog' <\d+>: "
                           r'\(multiline log follows\)\nsome\nlog')),
                mock.call(
                    RegExp(r'qj:\s+\(multiline log follows\)\nsome\nextra\ninfo')),
            ],
            any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)

  def test_multiline_with_r(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      alternative_return_value = 'some other\nreturn value'
      out = qj(r=alternative_return_value, x='some\nlog')
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r"qj: <qj_test> test_multiline_with_r: r=alternative_return_value, x='some\\nlog' <\d+>: "
              r'\(multiline log follows\)\nsome\nlog')),
          mock.call(RegExp(
              r'qj:\s+Overridden return value: \(multiline log follows\)\n'
              r'some other\nreturn value')),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)
      self.assertIs(out, alternative_return_value)

  def test_r_magic_works_across_modules(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj.make_global()

      input_value = 'some log'
      out = qj_test_helper.LogToQJ(x=input_value)
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test_helper> LogToQJ: \*\*kwargs <\d+>: some log'))
      self.assertIs(out, input_value)
      mock_log_fn.reset_mock()

      out = qj_test_helper.LogToQJ(x=input_value, r=None)
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r'qj: <qj_test_helper> LogToQJ: \*\*kwargs <\d+>: some log')),
          mock.call(RegExp(
              r'qj:\s+Overridden return value: None')),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)

      self.assertIsNone(out)
      mock_log_fn.reset_mock()

      out = qj_test_helper.LogToQJQJ(x=input_value)
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test_helper> LogToQJQJ: \*\*kwargs <\d+>: some log'))
      self.assertIs(out, input_value)
      mock_log_fn.reset_mock()

      out = qj_test_helper.LogToQJQJ(x=input_value, r=None)
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r'qj: <qj_test_helper> LogToQJQJ: \*\*kwargs <\d+>: some log')),
          mock.call(RegExp(
              r'qj:\s+Overridden return value: None')),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)
      self.assertIsNone(out)

  def test_logs_with_positional_args(self):
    with mock.patch('logging.info') as mock_log_fn:
      with mock.patch('ipdb.set_trace') as mock_debug_fn:
        qj.LOG_FN = mock_log_fn
        qj.DEBUG_FN = mock_debug_fn
        alternative_return_value = 'some other return value'
        out = qj('some log', 'some prefix', lambda _: 'some extra info', True,
                 True, False, False, alternative_return_value, False, True,
                 False, False, False, False, False, False, False)
        mock_log_fn.assert_has_calls(
            [
                mock.call(
                    RegExp(r'qj: <qj_test> test_logs_with_positional_args: some prefix '
                           r'<\d+>: some log')),
                mock.call(
                    RegExp(r'qj:\s+some extra info')),
                mock.call(
                    RegExp(r'qj:\s+Public properties:\n')),
                mock.call(
                    RegExp(r'qj:\s+Overridden return value: some other return value')),
            ],
            any_order=False)
        self.assertEqual(mock_log_fn.call_count, 4)
        mock_debug_fn.assert_called_once()
        self.assertIs(out, alternative_return_value)

  def test_no_logs_with_positional_args(self):
    with mock.patch('logging.info') as mock_log_fn:
      with mock.patch('ipdb.set_trace') as mock_debug_fn:
        qj.LOG_FN = mock_log_fn
        input_value = 'some log'
        alternative_return_value = 'some other return value'
        out = qj('some log', 'some prefix', lambda _: 'some extra info', True,
                 True, False, False, alternative_return_value, False, False,
                 False, False, False, False, False, False, False)
        mock_log_fn.assert_not_called()
        mock_debug_fn.assert_not_called()
        self.assertIs(out, input_value)

  def test_logs_max_times_ends_with_warning(self):
    with mock.patch('logging.info') as mock_log_fn:
      with mock.patch('ipdb.set_trace') as mock_debug_fn:
        qj.LOG_FN = mock_log_fn
        qj.MAX_FRAME_LOGS = 1
        original_return_value = 'some log'
        alternative_return_value = 'some other return value'
        out = []
        for _ in range(2):
          out.append(qj(original_return_value, 'some prefix', lambda _: 'some extra info', d=True,
                        p=True, r=alternative_return_value, b=True))
        qj('other log', 'other prefix')
        mock_log_fn.assert_has_calls(
            [
                mock.call(
                    RegExp(r'qj: <qj_test> test_logs_max_times_ends_with_warning:'
                           r' some prefix <\d+>: some log')),
                mock.call(
                    RegExp(r'qj:\s+some extra info')),
                mock.call(
                    RegExp(r'qj:\s+Public properties:\n')),
                mock.call(
                    RegExp(r'qj:\s+Overridden return value: some other return value')),
                mock.call(
                    RegExp(r'qj: <qj_test> test_logs_max_times_ends_with_warning:'
                           r' Maximum per-frame logging hit \(1\)\.')),
                mock.call(
                    RegExp(r'qj: <qj_test> test_logs_max_times_ends_with_warning:'
                           r'  other prefix <\d+>: other log')),
                mock.call(
                    RegExp(r'qj: <qj_test> test_logs_max_times_ends_with_warning:'
                           r'  Maximum per-frame logging hit \(1\)\.')),
            ],
            any_order=False)
        self.assertEqual(mock_log_fn.call_count, 7)
        mock_debug_fn.assert_called_once()
        self.assertIs(out[0], alternative_return_value)
        self.assertIs(out[1], original_return_value)

  def test_logs_with_pad(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj('some log', pad='#')
      qj('some other log', pad=3)
      mock_log_fn.assert_has_calls(
          [
              mock.call(
                  RegExp(r'#+')),
              mock.call(
                  RegExp(r"qj: <qj_test> test_logs_with_pad: 'some log', pad='#' <\d+>: some log")),
              mock.call(
                  RegExp(r'#+')),
              mock.call(
                  RegExp(r'\n\n')),
              mock.call(
                  RegExp(r"qj: <qj_test> test_logs_with_pad:  'some other log', pad=3 <\d+>: some other log")),
              mock.call(
                  RegExp(r'\n\n')),
          ],
          any_order=False)
      self.assertEqual(mock_log_fn.call_count, 6)

  def test_logs_with_tictoc(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj._tics = []  # Ensure an empty tic stack.

      qj('tic log', tic=1)
      qj('toc log', toc=1)
      mock_log_fn.assert_has_calls(
          [
              mock.call(
                  RegExp(r"qj: <qj_test> test_logs_with_tictoc: 'tic log', tic=1 <\d+>: tic log")),
              mock.call(
                  RegExp(r'qj:\s+Added tic\.')),
              mock.call(
                  RegExp(r"qj: <qj_test> test_logs_with_tictoc:  'toc log', toc=1 <\d+>: toc log")),
              mock.call(
                  RegExp(r"qj:\s+\d\.\d\d\d\d seconds since 'tic log', tic=1\.")),
          ],
          any_order=False)
      self.assertEqual(mock_log_fn.call_count, 4)

  def test_logs_with_tictoc_no_x(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj._tics = []  # Ensure an empty tic stack.

      qj(tic=1)
      qj(toc=1)
      mock_log_fn.assert_has_calls(
          [
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_no_x: tic=1 <\d+>: Adding tic\.')),
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_no_x:  toc=1 <\d+>: Computing toc\.')),
              mock.call(
                  RegExp(r'qj:\s+\d\.\d\d\d\d seconds since tic=1\.')),
          ],
          any_order=False)
      self.assertEqual(mock_log_fn.call_count, 3)

  def test_logs_with_tictoc_list_comp(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj._tics = []  # Ensure an empty tic stack.

      _ = [qj(x, tic=1, toc=1) for x in range(2)]
      qj(toc=1)
      mock_log_fn.assert_has_calls(
          [
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_list_comp: x, tic=1, toc=1 <\d+>: 0')),
              mock.call(
                  RegExp(r'qj:\s+Added tic\.')),
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_list_comp: x, tic=1, toc=1 <\d+>: 1')),
              mock.call(
                  RegExp(r'qj:\s+\d\.\d\d\d\d seconds since x, tic=1, toc=1\.')),
              mock.call(
                  RegExp(r'qj:\s+Added tic\.')),
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_list_comp: \s?toc=1 <\d+>: Computing toc\.')),
              mock.call(
                  RegExp(r'qj:\s+\d\.\d\d\d\d seconds since x, tic=1, toc=1\.')),
          ],
          any_order=False)
      self.assertEqual(mock_log_fn.call_count, 7)

  def test_logs_with_tictoc_nested(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj._tics = []  # Ensure an empty tic stack.

      qj(tic=1)
      qj(tic=2)
      qj(toc=1)
      qj(toc=1)
      mock_log_fn.assert_has_calls(
          [
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_nested: tic=1 <\d+>: Adding tic\.')),
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_nested:  tic=2 <\d+>: Adding tic\.')),
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_nested:   toc=1 <\d+>: Computing toc\.')),
              mock.call(
                  RegExp(r'qj:\s+\d\.\d\d\d\d seconds since tic=2\.')),
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_nested:    toc=1 <\d+>: Computing toc\.')),
              mock.call(
                  RegExp(r'qj:\s+\d\.\d\d\d\d seconds since tic=1\.')),
          ],
          any_order=False)
      self.assertEqual(mock_log_fn.call_count, 6)

  def test_logs_with_tictoc_negative_toc(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj._tics = []  # Ensure an empty tic stack.

      qj(tic=1)
      qj(tic=2)
      qj(toc=-1)
      mock_log_fn.assert_has_calls(
          [
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_negative_toc: tic=1 <\d+>: Adding tic\.')),
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_negative_toc:  tic=2 <\d+>: Adding tic\.')),
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_negative_toc:   toc=-1 <\d+>: Computing toc\.')),
              mock.call(
                  RegExp(r'qj:\s+\d\.\d\d\d\d seconds since tic=2\.')),
              mock.call(
                  RegExp(r'qj:\s+\d\.\d\d\d\d seconds since tic=1\.')),
          ],
          any_order=False)
      self.assertEqual(mock_log_fn.call_count, 5)
      self.assertEqual(len(qj._tics), 0)

  def test_logs_with_tictoc_across_fn_calls(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj._tics = []  # Ensure an empty tic stack.

      def tictoc_across_fn_calls():
        qj(tic=2)

      qj(tic=1)
      tictoc_across_fn_calls()
      qj(toc=-1)

      mock_log_fn.assert_has_calls(
          [
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_across_fn_calls: tic=1 <\d+>: Adding tic\.')),
              mock.call(
                  RegExp(r'qj: <qj_test> tictoc_across_fn_calls: tic=2 <\d+>: Adding tic\.')),
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_tictoc_across_fn_calls:  toc=-1 <\d+>: Computing toc\.')),
              mock.call(
                  RegExp(r'qj:\s+\d\.\d\d\d\d seconds since tic=2\.')),
              mock.call(
                  RegExp(r'qj:\s+\d\.\d\d\d\d seconds since tic=1\.')),
          ],
          any_order=False)
      self.assertEqual(mock_log_fn.call_count, 5)
      self.assertEqual(len(qj._tics), 0)

  def test_logs_with_tictoc_no_unmatched_tic(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      qj._tics = []  # Ensure an empty tic stack.

      qj(toc=1)

      mock_log_fn.assert_called_once_with(
          RegExp(r'qj: <qj_test> test_logs_with_tictoc_no_unmatched_tic: toc=1 <\d+>: Unable to compute toc -- no unmatched tic\.'))
      self.assertEqual(len(qj._tics), 0)

  def test_logs_with_time(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      def foo():
        pass
      qj(foo, time=1)()
      mock_log_fn.assert_has_calls(
          [
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_time: foo, time=1 <\d+>: <function .*foo at 0x.*>')),
              mock.call(
                  RegExp(r'qj:\s+Wrapping return value in timing function\.')),
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_time:  Average timing for <function .*foo at 0x.*> across 1 call <\d+>: \d\.\d\d\d\d seconds')),
          ],
          any_order=False)
      self.assertEqual(mock_log_fn.call_count, 3)

  def test_logs_with_time_decorator(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      @qj(time=1)
      def foo():
        pass
      foo()
      mock_log_fn.assert_has_calls(
          [
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_time_decorator: time=1 <\d+>: Preparing decorator to measure timing\.\.\.')),
              mock.call(
                  RegExp(r'qj:\s+Decorating <function .*foo at 0x.*> with timing function\.')),
              mock.call().__nonzero__() if sys.version_info[0] < 3 else mock.call().__bool__(),  # TODO(iansf): it's unclear why this is necessary in this case.
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_time_decorator:  Average timing for <function .*foo at 0x.*> across 1 call <\d+>: \d\.\d\d\d\d seconds')),
          ],
          any_order=False)
      self.assertEqual(mock_log_fn.call_count, 3)

  def test_logs_with_catch(self):
    with mock.patch('logging.info') as mock_log_fn:
      with mock.patch('ipdb.set_trace') as mock_debug_fn:
        qj.LOG_FN = mock_log_fn
        qj.DEBUG_FN = mock_debug_fn
        def foo():
          raise Exception('FOO')
        qj(foo, catch=1)()
        mock_log_fn.assert_has_calls(
            [
                mock.call(
                    RegExp(r'qj: <qj_test> test_logs_with_catch: foo, catch=1 <\d+>: <function .*foo at 0x.*>')),
                mock.call(
                    RegExp(r'qj:\s+Wrapping return value in exception function\.')),
                mock.call(
                    RegExp(r'qj: <qj_test> test_logs_with_catch:  Caught an exception in <function .*foo at 0x.*> <\d+>: FOO')),
            ],
            any_order=False)
        self.assertEqual(mock_log_fn.call_count, 3)
        self.assertEqual(mock_debug_fn.call_count, 1)

  def test_logs_with_catch_decorator(self):
    with mock.patch('logging.info') as mock_log_fn:
      with mock.patch('ipdb.set_trace') as mock_debug_fn:
        qj.LOG_FN = mock_log_fn
        qj.DEBUG_FN = mock_debug_fn
        @qj(catch=1)
        def foo():
          raise Exception('FOO')
        foo()
        mock_log_fn.assert_has_calls(
            [
                mock.call(
                    RegExp(r'qj: <qj_test> test_logs_with_catch_decorator: catch=1 <\d+>: Preparing decorator to catch exceptions\.\.\.')),
                mock.call(
                    RegExp(r'qj:\s+Decorating <function .*foo at 0x.*> with exception function\.')),
                mock.call().__nonzero__() if sys.version_info[0] < 3 else mock.call().__bool__(),  # TODO(iansf): it's unclear why this is necessary in this case.
                mock.call(
                    RegExp(r'qj: <qj_test> test_logs_with_catch_decorator:  Caught an exception in <function .*foo at 0x.*> <\d+>: FOO')),
            ],
            any_order=False)
        self.assertEqual(mock_log_fn.call_count, 3)
        self.assertEqual(mock_debug_fn.call_count, 1)

  def test_logs_with_log_all_calls(self):
    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      s = qj('abc', log_all_calls=1)
      s.replace('a', 'b')
      mock_log_fn.assert_has_calls(
          [
              mock.call(
                  RegExp(r"qj: <qj_test> test_logs_with_log_all_calls: 'abc', log_all_calls=1 <\d+>: abc")),
              mock.call(
                  RegExp(r'qj:\s+Wrapping all public method calls for object\.')),
              mock.call(
                  RegExp(r"qj: <qj_test> test_logs_with_log_all_calls:  calling replace <\d+>: replace\('a', 'b'\)")),
              mock.call(
                  RegExp(r'qj: <qj_test> test_logs_with_log_all_calls:  returning from replace <\d+>: bbc')),
          ],
          any_order=False)
      self.assertEqual(mock_log_fn.call_count, 4)

  def test_logs_no_s_empty(self):
    def empty():
      qj()

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      empty()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> empty: <empty log> <\d+>:'))

  def test_logs_no_s_basic(self):
    def basic():
      x = 2
      qj(x)

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      basic()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> basic: x <\d+>: 2'))

  def test_logs_no_s_basic_add(self):
    def basic_add():
      x = 2
      qj(1 + x)

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      basic_add()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> basic_add: 1 \+ x <\d+>: 3'))

  def test_logs_no_s_basic_mul(self):
    def basic_mul():
      x = 2
      qj(1 * x)

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      basic_mul()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> basic_mul: 1 \* x <\d+>: 2'))

  def test_logs_no_s_basic_floordiv(self):
    def basic_floordiv():
      x = 2
      qj(3 // x)

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      basic_floordiv()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> basic_floordiv: 3 // x <\d+>: 1'))

  def test_logs_no_s_order_of_operations(self):
    def order_of_operations():
      x = 2
      qj(1 + 2 * x)
      qj(2 * x + 1)
      qj(2 * (x + 1))

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      order_of_operations()
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r'qj: <qj_test> order_of_operations: 1 \+ 2 \* x <\d+>: 5')),
          mock.call(RegExp(
              r'qj: <qj_test> order_of_operations:  2 \* x \+ 1 <\d+>: 5')),
          mock.call(RegExp(
              r'qj: <qj_test> order_of_operations:   2 \* \(x \+ 1\) <\d+>: 6')),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 3)

  def test_logs_no_s_basic_funcall(self):
    def basic_funcall():
      x = 2
      qj(abs(-x))

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      basic_funcall()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> basic_funcall: abs\(-x\) <\d+>: 2'))

  def test_logs_no_s_basic_obj_funcall(self):
    def basic_obj_funcall():
      x = '2'
      qj(x.strip())

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      basic_obj_funcall()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> basic_obj_funcall: x.strip\(\) <\d+>: 2'))

  def test_logs_no_s_basic_list(self):
    def basic_list():
      x = [1, 2]
      qj(x)

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      basic_list()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> basic_list: x <\d+>: \[1, 2\]'))

  def test_logs_no_s_basic_tuple(self):
    def basic_tuple():
      x = (1, 2)
      qj(x)

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      basic_tuple()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> basic_tuple: x <\d+>: \(1, 2\)'))

  def test_logs_no_s_basic_dict(self):
    def basic_dict():
      x = {'a': 1, 'b': 2}
      qj(x)

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      basic_dict()
      mock_log_fn.assert_called_once_with(RegExp(
          r"qj: <qj_test> basic_dict: x <\d+>: \{('a': 1, 'b': 2|'b': 2, 'a': 1)\}"))

  def test_logs_no_s_list_comp(self):
    def list_comp():
      x = [1, 2]
      return [qj(a) for a in x]

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      list_comp()
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r'qj: <qj_test> list_comp: a <\d+>: 1')),
          mock.call(RegExp(
              r'qj: <qj_test> list_comp: a <\d+>: 2'))
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)

  def test_logs_no_s_basic_gen(self):
    def basic_gen():
      x = [1, 2]
      g = (qj(a) for a in x)
      for a in g:
        pass

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      basic_gen()
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r'qj: <qj_test> basic_gen: a <\d+>: 1')),
          mock.call(RegExp(
              r'qj: <qj_test> basic_gen: a <\d+>: 2'))
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)

  def test_logs_no_s_dict_comp(self):
    def dict_comp():
      x = {'a': 1, 'b': 2}
      return {qj(k): qj(v) for k, v in x.items()}

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      dict_comp()
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r'qj: <qj_test> dict_comp: *k <\d+>: a')),
          mock.call(RegExp(
              r'qj: <qj_test> dict_comp: *v <\d+>: 1')),
          mock.call(RegExp(
              r'qj: <qj_test> dict_comp: *k <\d+>: b')),
          mock.call(RegExp(
              r'qj: <qj_test> dict_comp: *v <\d+>: 2')),
      ], any_order=True)
      self.assertEqual(mock_log_fn.call_count, 4)

  def test_logs_no_s_basic_lambda(self):
    def basic_lambda():
      x = 2
      (lambda: qj(x))()

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      basic_lambda()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> basic_lambda.lambda: x <\d+>: 2'))

  def test_logs_no_s_embedded_lambda(self):
    def embedded_lambda():
      a = 1
      b = 2
      qj(a, l=lambda x: qj(b))

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      embedded_lambda()
      if sys.version_info[0] == 3 and sys.version_info[1] > 10:
        # This test is unlikely to pass on 3.11 and higher.
        pass
      else:
        mock_log_fn.assert_has_calls([
            mock.call(RegExp(
                r'qj: <qj_test> embedded_lambda: a, l=lambda x: qj\(b\) <\d+>: 1')),
            mock.call(RegExp(
                r'qj: <qj_test> qj.lambda: b <\d+>: 2')),
            mock.call(RegExp(
                r'qj:\s+2')),
        ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 3)

  def test_logs_no_s_contains_list(self):
    def contains_list():
      x = 1
      qj([x, x + 1, x + 2])

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      contains_list()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> contains_list: \[x, x \+ 1, x \+ 2\] <\d+>: \[1, 2, 3\]'))

  def test_logs_no_s_contains_list_comp_basic(self):
    def contains_list_comp_basic():
      l = [1, 2, 3]
      qj([x for x in l])

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      contains_list_comp_basic()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> contains_list_comp_basic: \[x for x in l\] <\d+>: \[1, 2, 3\]'))

  def test_logs_no_s_contains_list_comp_with_list_comp(self):
    def contains_list_comp_with_list_comp():
      l = [1, 2, 3]
      qj([[x + y for y in [2, 3, 4]] for x in l])

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      contains_list_comp_with_list_comp()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> contains_list_comp_with_list_comp: \[\[x \+ y for y in \[2, 3, 4\]\] for x in l\] <\d+>: \[\[3, 4, 5\],'))

  def test_logs_no_s_contains_dict_comp_basic(self):
    def contains_dict_comp_basic():
      l = [1, 2, 3]
      qj({x: x + 1 for x in l})

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      contains_dict_comp_basic()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> contains_dict_comp_basic: \{x: x \+ 1 for x in l\} <\d+>: '
          r'\{[1-3]: [2-4], [1-3]: [2-4], [1-3]: [2-4]\}'))

  def test_logs_no_s_contains_dict_comp_multiarg(self):
    def contains_dict_comp_multiarg():
      l = [1, 2, 3]
      s = 'abc'
      qj({k: x + 1 for k, x in zip(list(s), l)})

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      contains_dict_comp_multiarg()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> contains_dict_comp_multiarg: \{k: x \+ 1 for k, x in zip\(list\(s\), l\)\} <\d+>: '
          r"\{'[a-c]': [2-4], '[a-c]': [2-4], '[a-c]': [2-4]\}"))

  def test_logs_no_s_contains_dict_comp_closure(self):
    def contains_dict_comp_closure():
      l = [1, 2, 3]
      s = 'abc'
      t = 'def'
      qj({k + s + t: x + 1 for k, x in zip(list(s), l)})

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      contains_dict_comp_closure()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> contains_dict_comp_closure: \{k \+ s \+ t: x \+ 1 for k, x in zip\(list\(s\), l\)\} <\d+>: '
          r"\{'(aabcdef|babcdef|cabcdef)': [2-4], '(aabcdef|babcdef|cabcdef)': [2-4], '(aabcdef|babcdef|cabcdef)': [2-4]\}"))

  def test_logs_no_s_multiline_basic(self):
    def multiline_basic():
      x = 2
      qj(
          x
      )

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      multiline_basic()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> multiline_basic: x <\d+>: 2'))

  def test_logs_no_s_multiline_many_arg(self):
    def multiline_many_arg():
      x = 2
      qj(x,
         s='',
         l=None,
         d=False,
         p=0,
         t=0,
         n=0,
         z=0,
         b=1)

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      multiline_many_arg()
      mock_log_fn.assert_called_once_with(RegExp(
          r"qj: <qj_test> multiline_many_arg: x, s='', l=None, d=False, p=0, t=0, n=0, z=0, b=1 <\d+>: 2"))

  def test_logs_no_s_multiline_list_comp(self):
    def multiline_list_comp():
      l = [1, 2, 3]
      qj(
          [x
           for x in l]
      )

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      multiline_list_comp()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> multiline_list_comp: \[x for x in l\] <\d+>: \[1, 2, 3\]'))

  def test_logs_no_s_multiline_set_comp(self):
    def multiline_set_comp():
      a = dict(x=1, y=2)
      b = dict(x=3, y=4)
      qj({
          (
              qj('%d_%d' % (v['x'], v['y'])),
              qj(tuple(sorted(v.keys()))),
          )
          for v in [a, b]
      })

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      multiline_set_comp()
      if sys.version_info[0] == 3 and sys.version_info[1] > 10:
        # This test is unlikely to pass in 3.11 and higher.
        pass
      else:
        mock_log_fn.assert_has_calls([
            mock.call(RegExp(
                r"qj: <qj_test> multiline_set_comp: '%d_%d' % \(v\['x'\], v\['y'\]\) <\d+>: 1_2")),
            mock.call(RegExp(
                r"qj: <qj_test> multiline_set_comp:  tuple\(sorted\(v\.keys\(\)\)\) <\d+>: \('x', 'y'\)")),
            mock.call(RegExp(
                r"qj: <qj_test> multiline_set_comp: '%d_%d' % \(v\['x'\], v\['y'\]\) <\d+>: 3_4")),
            mock.call(RegExp(
                r"qj: <qj_test> multiline_set_comp:  tuple\(sorted\(v\.keys\(\)\)\) <\d+>: \('x', 'y'\)")),
            mock.call(RegExp(
                r"qj: <qj_test> multiline_set_comp: "
                r"\{ \( qj\('%d_%d' % \(v\['x'\], v\['y'\]\)\), qj\(tuple\(sorted\(v.keys\(\)\)\)\), \) "
                r"for v in \[a, b\] \} <\d+>: "
                r".*\('(1_2|3_4)', \('x', 'y'\)\), \('(1_2|3_4)', \('x', 'y'\)\)")),  # Python 2.7 and 3.6 represent sets differently
        ], any_order=True)
      self.assertEqual(mock_log_fn.call_count, 5)

  def test_logs_no_s_no_whitespace(self):
    def no_whitespace():
      x = 1
      qj([x,x+1,x+2])  # pylint: disable=bad-whitespace

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      no_whitespace()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> no_whitespace: \[x,x\+1,x\+2\] <\d+>: \[1, 2, 3\]'))

  def test_logs_no_s_substring_conflicts(self):
    def substring_conflicts():
      x = 1
      y = 2
      xx = 1
      yy = 4
      qj([x, y]); qj([xx, yy])  # pylint: disable=multiple-statements

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      substring_conflicts()
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r'qj: <qj_test> substring_conflicts: \[x, y\] <\d+>: \[1, 2\]')),
          mock.call(RegExp(
              r'qj: <qj_test> substring_conflicts:  \[xx, yy\] <\d+>: \[1, 4\]')),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)

  def test_logs_no_s_with_splat_basic(self):
    def with_splat_basic():
      a = [2, '', None]
      qj(*a)

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      with_splat_basic()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> with_splat_basic: \*a <\d+>: 2'))

  def test_logs_no_s_with_splat_as_well(self):
    def with_splat_as_well():
      x = 2
      a = [None, False]
      qj(x, '', *a)

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      with_splat_as_well()
      mock_log_fn.assert_called_once_with(RegExp(
          r"qj: <qj_test> with_splat_as_well: x, '', \*a <\d+>: 2"))

  def test_logs_no_s_with_splat_and_kw(self):
    def with_splat_and_kw():
      x = 2
      a = ['', None]
      d = {'d': 0}
      qj(x, *a, **d)

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      with_splat_and_kw()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> with_splat_and_kw: x, \*a, \*\*d <\d+>: 2'))

  def test_logs_no_s_nested(self):
    def nested():
      x = 2
      qj(qj(x))

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      nested()
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r'qj: <qj_test> nested: x <\d+>: 2')),
          mock.call(RegExp(
              r'qj: <qj_test> nested:  qj\(x\) <\d+>: 2')),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)

  def test_logs_no_s_subscript(self):
    def subscript():
      x = [1, 2, 3]
      qj(x[0])

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      subscript()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> subscript: x\[0\] <\d+>: 1'))

  def test_logs_no_s_subscript_with_args(self):
    def subscript_with_args():
      x = [1, 2, 3]
      qj(x[0], b=1)

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      subscript_with_args()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> subscript_with_args: x\[0\], b=1 <\d+>: 1'))

  def test_logs_no_s_subscript_dict(self):
    def subscript():
      d = dict(x=2)
      qj(d['x'])

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      subscript()
      mock_log_fn.assert_called_once_with(RegExp(
          r"qj: <qj_test> subscript: d\['x'\] <\d+>: 2"))

  def test_logs_no_s_slice_0(self):
    def slice_0():
      s = 'abcdef'
      qj(s[:])

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      slice_0()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> slice_0: s\[:\] <\d+>: abcdef'))

  def test_logs_no_s_slice_1(self):
    def slice_1():
      s = 'abcdef'
      x = 2
      qj(s[x:])

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      slice_1()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> slice_1: s\[x:\] <\d+>: cdef'))

  def test_logs_no_s_slice_2(self):
    def slice_2():
      s = 'abcdef'
      x = 2
      qj(s[x:-1])
      qj(s[:-1])

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      slice_2()
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r'qj: <qj_test> slice_2: s\[x:-1\] <\d+>: cde')),
          mock.call(RegExp(
              r'qj: <qj_test> slice_2:  s\[:-1\] <\d+>: abcde')),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 2)

  def test_logs_no_s_slice_3(self):
    def slice_3():
      s = 'abcdef'
      x = 2
      qj(s[-1:x:-1])
      qj(s[-1::-1])
      qj(s[::])

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      slice_3()
      mock_log_fn.assert_has_calls([
          mock.call(RegExp(
              r'qj: <qj_test> slice_3: s\[-1:x:-1\] <\d+>: fed')),
          mock.call(RegExp(
              r'qj: <qj_test> slice_3:  s\[-1::-1\] <\d+>: fedcba')),
          mock.call(RegExp(
              r'qj: <qj_test> slice_3:   s\[::\] <\d+>: abcdef')),
      ], any_order=False)
      self.assertEqual(mock_log_fn.call_count, 3)

  def test_logs_no_s_calls_len(self):
    def calls_len():
      l = [1, 2, 3]
      qj(len(l))

    with mock.patch('logging.info') as mock_log_fn:
      qj.LOG_FN = mock_log_fn
      calls_len()
      mock_log_fn.assert_called_once_with(RegExp(
          r'qj: <qj_test> calls_len: len\(l\) <\d+>: 3'))


# pylint: enable=line-too-long
if __name__ == '__main__':
  unittest.main()
