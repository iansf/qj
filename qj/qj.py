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
"""See README.md for usage information.

Import like this:
  from qj import qj
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import dis
import functools
import inspect
import logging
import opcode
import os
import re
import sys
import time as _time
import types


_QJ_R_MAGIC = 0x93218231


# pylint: disable=g-long-lambda, protected-access, expression-not-assigned, line-too-long
def qj(x='',  # pylint: disable=invalid-name
       s='',
       l=None,
       d=False,
       p=False,
       t=False,
       n=False,
       r=_QJ_R_MAGIC,
       z=False,
       b=True,
       pad=False,
       tfc=False,
       tic=False,
       toc=False,
       time=False,
       catch=False,
       log_all_calls=False,
       _depth=1):
  """A combined logging and debugging function.

  Arguments:
    x: The thing to log. x is also the return value. Defaults to '', although
       it's somewhat odd to call this function without passing x.
    s: Optional string to prefix the log message with. Defaults to '', which
       results in the function prefixing the log with the source code at the
       call site, or the type of x if it can't extract the source code.
    l: Optional lambda to be run after logging x. Allows useful things like
       inspecting other variables in the current context when x gets logged. Its
       return value is logged immediately after x is logged. Defaults to None.
    d: Optional bool to drop into the debugger if x is logged. Defaults to
       False.
    p: Optional bool to log the public properties of x, including basic call
       signatures of functions, if x is logged.
    t: Optional bool to wrap x in a tensorflow.Print call. If x is a Tensor,
       its value will be printed at graph execution time. The tensorflow.Print
       calls will be prefixed with the value in s, or qj's default logging
       prefix, just like any other qj log message. It also sets the
       tensorflow.Print call to only print qj.MAX_FRAME_LOGS times, so that
       it isn't too spammy when running the graph. The call attempts to validate
       that tensorflow is available and that x can be passed to tensorflow.Print
       before calling tensorflow.Print.
    n: Optional bool to log the shape, min, mean, and max values of x if numpy
       is available.
    r: Optional alternate return value to use instead of x if x is logged. Any
       value passed to r will be returned (even None). Only the private value
       _QJ_R_MAGIC is ignored.
    z: Optional bool to zero out the frame count in the current frame, so that
       logging continues. Most useful when using qj in colabs at the top
       (module) level, since that stack frame effectively lives forever.
       Defaults to False.
    b: Optional bool to enable or disable the logging of x. Defaults to True (so
       that x is logged, assuming other conditions don't prevent logging).
    pad: Optional bool to add padding blank lines before and after the logs.
       Useful for visually extracting particular logs.
    tfc: Optional bool to wrap x in a tensorflow.check_numerics call if x is a
       Tensor.
    tic: Optional bool to begin recording a duration.
    toc: Optional bool to end recording a duration started with a previous
       `tic`. Logs the corresponding duration if there was a previous `tic`.
       `tic` and `toc` can be set in the same call -- `toc` is handled first,
       which allows you to measure the body of a loop or comprehension with a
       single call to `qj(tic=1, toc=1)`.
    time: Optional bool to turn on timing of a function call. Can be used as a
       decorator.  E.g., `@qj(time=100) def foo()...` will print timing stats
       every 100 calls to foo.
    catch: Optional bool to decorate a function with exception catching that
       drops into the debugger.
    log_all_calls: Optional bool to wrap x in a new object that logs every call
       to x.  Experimental.
    _depth: Private parameter used to specify which stack frame should be used
            for both logging and debugging operations. If you're not wrapping
            qj or adding features to qj, you should leave this at it's default.

  Returns:
    x, which allows you to insert a call to qj just about anywhere.
  """
  if qj.LOG and b:
    try:
      # Compute and collect values needed for logging.
      # We need the caller's stack frame both for logging the function name and
      # line number qj was called from, and to store some state that makes the
      # more magical features work.
      f = inspect.currentframe()
      for _ in range(_depth):
        f = f.f_back

      # This is the magic dictionary where we write state that gives log output
      # that can represent the underlying function's code structure, as well as
      # tracking how many times we logged from the stack frame, which allows us
      # to minimize log spam from logs in loops and comprehensions.
      qj_dict = f.f_locals.get('__qj_magic_wocha_doin__', {})
      qj_dict = {} if z else qj_dict
      log_count_key = 'frame_log_count_%d' % f.f_lasti
      qj_dict[log_count_key] = qj_dict.get(log_count_key, 0) + 1

      if qj_dict[log_count_key] > qj.MAX_FRAME_LOGS:
        return x

      # We're going to log things, so go ahead and collect information about the
      # caller's stack frame.
      func_name = qj_dict.get('func_name')
      if func_name is None:
        func_name = inspect.getframeinfo(f).function
        if func_name == '<dictcomp>':
          func_name = inspect.getframeinfo(f.f_back).function
        if func_name == '<genexpr>':
          func_name = inspect.getframeinfo(f.f_back).function
        if func_name == '<listcomp>':
          func_name = inspect.getframeinfo(f.f_back).function
        elif func_name == '<setcomp>':
          func_name = inspect.getframeinfo(f.f_back).function
        elif func_name == '<lambda>':
          func_name = inspect.getframeinfo(f.f_back).function + '.lambda'
        if func_name.startswith('<module>'):
          func_name = func_name.replace('<module>', 'module_level_code')

        filename = os.path.basename(f.f_code.co_filename)
        # Don't include the filename when logging in ipython contexts.
        if filename[0] != '<':
          filename = filename.replace('.py', '')
          func_name = '<{}> {}'.format(filename, func_name)
        qj_dict['func_name'] = func_name

      # If we are dealing with module-level code, don't limit logging, since
      # large amounts of module-level logs generally means we're running in a
      # colab, and it's annoying to have your logs suddenly stop after k runs.
      if 'module_level_code' in func_name:
        qj_dict[log_count_key] = 1

      # This is the magic that allows us to indent the logs in a sensible
      # manner. f_lasti is the last instruction index executed in the frame
      # (i.e., the instruction that executed the call to qj). We add each
      # instruction index into the dictionary, setting the value to the length
      # of the dictionary after that addition, so the first instruction we see
      # gets a value of 1, the second a value of 2, etc.
      qj_instructions_dict = qj_dict.get('instructions', {})
      qj_dict['instructions'] = qj_instructions_dict
      qj_instructions_dict[f.f_lasti] = qj_instructions_dict.get(
          f.f_lasti, len(qj_instructions_dict) + 1)
      # Here, we use that value to determine how many spaces we need after the
      # log prefix.
      spaces = ' ' * qj_instructions_dict[f.f_lasti]
      # And we store the dictionary back in the caller's frame.
      f.f_locals['__qj_magic_wocha_doin__'] = qj_dict

      # Try to extract the source code of this call if a string wasn't specified.
      if not s:
        try:
          code_key = '%s:%r:%s' % (f.f_code.co_filename, f.f_code.co_firstlineno, f.f_code.co_code)
          fn_calls = qj._FN_MAPS.get(code_key, {})
          if f.f_lasti not in fn_calls:
            qj._DEBUG_QJ and qj._DISASSEMBLE_FN(f.f_code, f.f_lasti)
            fn_calls[f.f_lasti] = _find_current_fn_call(f.f_code, f.f_lasti)
            qj._FN_MAPS[f.f_code.co_code] = fn_calls
          s = fn_calls.setdefault(f.f_lasti, '').strip()
        except IOError:
          # Couldn't get the source code, fall back to showing the type.
          s = ''

      # Now that we've computed the call count and the indentation, we can log.
      prefix = '%s:%s%s <%d>:' % (func_name, spaces, s or type(x), f.f_lineno)
      log = ''

      # First handle parameters that might change how x is logged.
      if n and 'numpy' in sys.modules:
        try:
          np = sys.modules['numpy']
          np_x = np.array(x)
          log = str((np_x.shape, (np.min(np_x),
                                  (np.mean(np_x), np.std(np_x)),
                                  np.max(np_x)),
                     np.histogram(np_x,
                                  bins=max(int(n),
                                           min(np.prod(np_x.shape), 5)))[0]
                    ))
          s = s or str(type(x))
          s += ' (shape (min (mean std) max) hist)'
          prefix = '%s:%s%s <%d>:' % (func_name, spaces, s, f.f_lineno)
        except:  # pylint: disable=bare-except
          pass

      if tic and x is '':
        log = 'Adding tic.'

      # toc needs to be processed after tic here so that the log messages make sense
      # when using tic/toc in a single call in a loop.
      if toc and x is '':
        if len(qj._tics):  # pylint: disable=g-explicit-length-test
          log = 'Computing toc.'
        else:
          log = 'Unable to compute toc -- no unmatched tic.'
          toc = False

      if time and x is '':
        log = 'Preparing decorator to measure timing...' + ('\n%s' % log if log else '')

      if catch and x is '':
        log = 'Preparing decorator to catch exceptions...' + ('\n%s' % log if log else '')

      # Now, either we have set the log message, or we are ready to build it directly from x.
      if not log:
        log = qj.STR_FN(x)
      log = '(multiline log follows)\n%s' % log if '\n' in log else log

      padding_string = ''
      if pad:
        if isinstance(pad, str):
          # Turn pad into a character string with no newlines as long as the
          # log string.
          log_len = (len(qj.PREFIX) + len(prefix.split('\n')[-1]) +
                     len(log.split('\n')[0]) + 1)
          padding_string = (pad.replace('\n', ' ') * log_len)[:log_len]
        else:
          try:
            padding_string = '\n' * (int(pad) - 1) + ' '
          except ValueError:
            padding_string = '\n'

      if padding_string:
        qj.LOG_FN(padding_string)

      # Log the primary log message.
      qj.LOG_FN('%s%s %s%s' % (qj.PREFIX, prefix, qj._COLOR_LOG(), log))

      # If there's a lambda, run it and log it.
      if l:
        log = qj.STR_FN(l(x))
        log = '(multiline log follows)\n%s' % log if '\n' in log else log
        qj.LOG_FN('%s%s %s%s' % (qj.PREFIX, ' ' * len(prefix), qj._COLOR_LOG(),
                                 log))

      # If we requested x's properties, compute them and log them.
      if p:
        try:
          if hasattr(inspect, 'signature'):
            argspec_func = lambda f: str(inspect.signature(f))
          else:
            argspec_func = lambda f: inspect.formatargspec(*inspect.getargspec(f))
          docs = [
              '%s%s' % (n,
                        argspec_func(v)
                        if inspect.isroutine(v) and not inspect.isbuiltin(v)
                        else '')
              for n, v in inspect.getmembers(x)
              if n == '__init__' or not n.startswith('_')
          ]
        except:  # pylint: disable=bare-except
          docs = [n for n in dir(x) if not n.startswith('_')]
        prefix_spaces = ' ' * len(prefix)
        qj.LOG_FN('%s%s %sPublic properties:\n    %s' %
                  (qj.PREFIX, prefix_spaces, qj._COLOR_LOG(), '\n    '.join(docs)))

      # If we requested tensorflow printing, wrap x in a tf.Print.
      if t:
        if (hasattr(x, '__module__') and
            'tensorflow' in x.__module__ and
            'tensorflow' in sys.modules):
          tf = sys.modules['tensorflow']
          prefix_spaces = ' ' * len(prefix)
          if 'session' in x.__module__:
            try:
              # pylint: disable=g-import-not-at-top
              try:
                from tensorflow.python import debug as tf_debug
              except ImportError:
                from google3.third_party.tensorflow.python import debug as tf_debug
              # pylint: enable=g-import-not-at-top
              x = tf_debug.LocalCLIDebugWrapperSession(x)
              x.add_tensor_filter('has_inf_or_nan', tf_debug.has_inf_or_nan)

              qj.LOG_FN('%s%s %sWrapping tf session in tfdbg session.' %
                        (qj.PREFIX, qj._COLOR_LOG(), prefix_spaces))
            except:  # pylint: disable=bare-except
              qj.LOG_FN('%s%s %sUnable to wrap tf session in tfdbg session. '
                        'Make sure your BUILD rule depends on '
                        '//tensorflow/python/debug:debug_py.' %
                        (qj.PREFIX, qj._COLOR_LOG(), prefix_spaces))
          else:
            qj.LOG_FN('%s%s %sWrapping return value in tf.Print operation.' %
                      (qj.PREFIX, qj._COLOR_LOG(), prefix_spaces))
            x = tf.Print(
                x, [tf.shape(x), x],
                message='%s%s%s%s' % (qj._COLOR_PREFIX(), qj.PREFIX, prefix[:-1],
                                      qj._COLOR_END()),
                first_n=qj.MAX_FRAME_LOGS if t is True else int(t),
                summarize=qj.MAX_FRAME_LOGS,
                name='qj_print_%s_%d' % (func_name.split(' ')[-1], f.f_lineno))

      if tfc:
        if (hasattr(x, '__module__') and
            'tensorflow' in x.__module__ and
            'tensorflow' in sys.modules):
          tf = sys.modules['tensorflow']
          prefix_spaces = ' ' * len(prefix)
          qj.LOG_FN('%s%s %sWrapping return value in tf.check_numerics.' %
                    (qj.PREFIX, qj._COLOR_LOG(), prefix_spaces))
          x = tf.check_numerics(
              x,
              message='%s%s%s%s' % (
                  qj._COLOR_PREFIX(), qj.PREFIX, prefix[:-1], qj._COLOR_END()),
              name='qj_check_numerics_%s_%d' % (func_name.split(' ')[-1], f.f_lineno))

      # toc needs to be processed before tic, so that single call tic/toc works in loops.
      if toc:
        if len(qj._tics):  # pylint: disable=g-explicit-length-test
          prefix_spaces = ' ' * len(prefix)
          toc = int(toc)
          if toc < 0:
            toc = len(qj._tics)
          toc = min(toc, len(qj._tics))
          toc_time = _time.time()
          for _ in range(toc):
            tic_ = qj._tics.pop()
            qj.LOG_FN('%s%s %s%.4f seconds since %s.' %
                      (qj.PREFIX, qj._COLOR_LOG(), prefix_spaces, toc_time - tic_[1], tic_[0]))

      if tic:
        tic_ = (s, _time.time())
        qj._tics.append(tic_)
        if x is not '':
          prefix_spaces = ' ' * len(prefix)
          qj.LOG_FN('%s%s %sAdded tic.' %
                    (qj.PREFIX, qj._COLOR_LOG(), prefix_spaces))

      if time:
        prefix_spaces = ' ' * len(prefix)
        if isinstance(x, types.FunctionType):
          qj.LOG_FN('%s%s %sWrapping return value in timing function.' %
                    (qj.PREFIX, qj._COLOR_LOG(), prefix_spaces))
          # pylint: disable=no-value-for-parameter
          x = _timing(logs_every=int(time))(x)
          # pylint: enable=no-value-for-parameter
        elif x is '':
          # x is '', so we'll assume it's the default value and we're decorating
          # a function
          x = lambda f: (
              (qj.LOG_FN('%s%s %sDecorating %s with timing function.' %
                         (qj.PREFIX, qj._COLOR_LOG(), prefix_spaces, str(f)))
               and False)
              # pylint: disable=no-value-for-parameter
              or _timing(logs_every=int(time))(f))
          # pylint: enable=no-value-for-parameter

      if catch:
        prefix_spaces = ' ' * len(prefix)
        if isinstance(x, types.FunctionType):
          qj.LOG_FN('%s%s %sWrapping return value in exception function.' %
                    (qj.PREFIX, qj._COLOR_LOG(), prefix_spaces))
          # pylint: disable=no-value-for-parameter
          x = _catch(exception_type=catch)(x)
          # pylint: enable=no-value-for-parameter
        elif x is '':
          # x is '', so we'll assume it's the default value and we're decorating
          # a function
          x = lambda f: (
              (qj.LOG_FN('%s%s %sDecorating %s with exception function.' %
                         (qj.PREFIX, qj._COLOR_LOG(), prefix_spaces, str(f)))
               and False)
              # pylint: disable=no-value-for-parameter
              or _catch(exception_type=catch)(f))
          # pylint: enable=no-value-for-parameter

      if log_all_calls:
        prefix_spaces = ' ' * len(prefix)
        qj.LOG_FN('%s%s %sWrapping all public method calls for object.' %
                  (qj.PREFIX, qj._COLOR_LOG(), prefix_spaces))

        def wrap(member_name, member_fn):
          """Wrap member_fn in a lambda that logs."""
          wrapped = (lambda *a, **kw:
                     qj('%s(%s)' % (member_name,
                                    ', '.join(['%r' % a_ for a_ in a]
                                              + ['%s=%r' % (k, v) for k, v in kw.items()])),
                        'calling %s' % member_name, _depth=2)
                     and qj(member_fn(*a, **kw),
                            'returning from %s' % member_name, _depth=2))
          if hasattr(member_fn, '__doc__'):
            wrapped.__doc__ = member_fn.__doc__
          return wrapped

        class Wrapper(type(x)):

          def __init__(self, x):
            method_types = (
                types.BuiltinFunctionType, types.BuiltinMethodType,
                types.FunctionType, types.LambdaType, types.MethodType
            )
            for m in inspect.getmembers(x):
              name = m[0]
              if not name.startswith('_'):
                member = m[1]
                if isinstance(member, method_types):
                  wrapped_fn = wrap(name, member)
                  setattr(self, name, wrapped_fn)
                else:
                  # pylint: disable=line-too-long
                  # TODO(iansf): This may be wrong. See
                  #              https://stackoverflow.com/questions/1325673/how-to-add-property-to-a-class-dynamically
                  # pylint: enable=line-too-long
                  setattr(self.__class__, name, member)

        x = Wrapper(x)

      # If we requested an alternative return value, log it.
      if r != _QJ_R_MAGIC:
        prefix = '%s:%s%s <%d>:' % (func_name, spaces, s or type(r), f.f_lineno)
        prefix_spaces = ' ' * len(prefix)
        log = qj.STR_FN(r)
        log = '(multiline log follows)\n%s' % log if '\n' in log else log
        qj.LOG_FN('%s%s %sOverridden return value: %s' % (qj.PREFIX, prefix_spaces,
                                                          qj._COLOR_LOG(), log))

      if padding_string:
        qj.LOG_FN(padding_string)

      # vvvvvvvv NO LOGS PERMITTED AFTER THIS BLOCK vvvvvvvv
      if qj_dict[log_count_key] == qj.MAX_FRAME_LOGS:
        qj.LOG_FN('%s%s:%s%sMaximum per-frame logging hit (%d). '
                  'No more logs will print at this call within this stack frame. '
                  'Set qj.MAX_FRAME_LOGS to change the limit or pass z=1 to this qj call '
                  'to zero out the frame log count.' %
                  (qj.PREFIX, func_name, spaces, qj._COLOR_LOG(),
                   qj.MAX_FRAME_LOGS))
      # ^^^^^^^^ NO LOGS PERMITTED AFTER THIS BLOCK ^^^^^^^^

      # If we requested debugging, drop into the debugger.
      if d:
        if not qj.DEBUG_FN:
          try:
            from colabtools import _debugger  # pylint: disable=g-import-not-at-top
            qj.DEBUG_FN = lambda frame: _debugger.ColabPdb().set_trace(frame=frame)
          except ImportError:
            try:
              # Import ipdb here because importing it at the top slows down execution.
              import ipdb  # pylint: disable=g-import-not-at-top
              qj.DEBUG_FN = ipdb.set_trace
            except ImportError:
              import pdb  # pylint: disable=g-import-not-at-top
              qj.DEBUG_FN = lambda frame: pdb.Pdb().set_trace(frame=frame)
        qj.DEBUG_FN(frame=f)

      # If we requested an alternative return value, return it now that
      # everything else is done.
      if r != _QJ_R_MAGIC:
        return r

    finally:
      # Delete the stack frame to ensure there are no memory leaks, as suggested
      # by https://docs.python.org/2/library/inspect.html#the-interpreter-stack
      del f

  # After everything else is done, return x.
  return x


def _standard_print(*args):
  writer = lambda: ''
  writer.s = ''
  def w(s):
    writer.s += s
  writer.write = w
  print(*args, file=writer, end='')
  return writer.s


# Set up basic logging handler.
logging.basicConfig(
    format='%(asctime)s: %(message)s',
    level=(
        logging.getLogger().getEffectiveLevel()
        if logging.getLogger().getEffectiveLevel() <= logging.INFO
        else logging.INFO))

qj.LOG = True
qj.DEBUG_FN = None

qj.COLOR = True
qj.PREFIX_COLOR = '\033[91m'
qj.LOG_COLOR = '\033[92m'
qj._PREFIX_COLOR_NOTEBOOK = '\033[91m'
qj._LOG_COLOR_NOTEBOOK = '\033[32m'

qj._COLOR_PREFIX = lambda: (qj.COLOR and qj.PREFIX_COLOR) or ''
qj._COLOR_LOG = lambda: (qj.COLOR and qj.LOG_COLOR) or ''
qj._COLOR_END = lambda: (qj.COLOR and '\033[0m') or ''
qj._COLOR_FN = lambda *args: (qj._COLOR_PREFIX() +
                              _standard_print(*args) + qj._COLOR_END())
qj.LOG_FN = lambda *args: logging.info(qj._COLOR_FN(*args))
qj.MAX_FRAME_LOGS = 200
qj.PREFIX = 'qj: '

qj.STR_FN = str

qj._FN_MAPS = {}
qj._DEBUG_QJ = False

qj.__version__ = '0.1.0'

# Stack of tic/toc tuples.
qj._tics = []

# Make qj globally available in any python code you load (not always the case in
# colabs due to the ways modules are loaded) by running qj.make_global(). This is
# robust to modifying qj and reloading, as you might do from a colab, so long as
# you call qj.make_global() again.
# Why the lambda?  This makes it easier to avoid issues when changing qj and
# reloading it -- calling qj.make_global after reloading qj is guaranteed to use
# the latest version and therefore also update the global copy of qj with the
# latest version (so long as you don't break the lambda).  The lambda also
# returns the symbol being made global (qj by default).
_builtin_module_name = '__builtin__' if sys.version_info[0] < 3 else 'builtins'
qj.make_global = lambda sym=qj, name='qj', mod=sys.modules[_builtin_module_name]: (
    (name in dir(mod) and delattr(mod, name) and False) or
    (setattr(mod, name, sym) and False) or sym)  # Return sym

# When running qj interactively (e.g., from a colab), automatically call
# qj.make_global(), and also add a general print function, pr, to the interactive
# module and set it as qj.LOG_FN.
if not hasattr(sys.modules['__main__'], '__file__'):
  try:
    from colabtools import googlelog  # pylint: disable=g-import-not-at-top
    from colabtools import outputformat  # pylint: disable=g-import-not-at-top
    _capture = googlelog.Capture()
    _start_capture = _capture.enter_global_mode
    _end_capture = lambda: _capture.exit_global_mode() or outputformat.word_wrap('1')
  except ImportError:
    _start_capture = lambda: None
    _end_capture = lambda: None
  qj.make_global()
  qj.LOG_FN = qj.make_global(
      lambda *args: _start_capture() or logging.info(qj._COLOR_FN(*args)) or _end_capture(),
      'pr', sys.modules['__main__'])
  qj.PREFIX_COLOR = qj._PREFIX_COLOR_NOTEBOOK
  qj.LOG_COLOR = qj._LOG_COLOR_NOTEBOOK


def _parametrized(decorator):
  @functools.wraps(decorator)
  def layer(*args, **kwargs):
    def repl(f):
      return decorator(f, *args, **kwargs)
    return repl
  return layer


qj._call_counts = collections.Counter()
qj._timings = collections.Counter()


@_parametrized
def _timing(f, logs_every=100):
  """Decorator to time function calls and log the stats."""
  @functools.wraps(f)
  def wrap(*args, **kw):
    """The timer function."""
    ts = _time.time()
    result = f(*args, **kw)
    te = _time.time()
    qj._call_counts[f] += 1
    qj._timings[f] += (te - ts)
    count = qj._call_counts[f]
    if count % logs_every == 0:
      qj(x='%2.4f seconds' % (qj._timings[f] / count),
         s='Average timing for %s across %d call%s' % (f, count, '' if count == 1 else 's'), _depth=2)
    return result
  return wrap


@_parametrized
def _catch(f, exception_type):
  """Decorator to drop into the debugger if a function throws an exception."""
  if not (inspect.isclass(exception_type)
          and issubclass(exception_type, Exception)):
    exception_type = Exception

  @functools.wraps(f)
  def wrap(*args, **kw):
    try:
      return f(*args, **kw)
    except exception_type as e:  # pylint: disable=broad-except
      qj(e, 'Caught an exception in %s' % f, d=1, _depth=2)
  return wrap


###############################################################################
# Code Correlation Code
###############################################################################

#------------------------------------------------------------------------------
# Python 3 Helpers
#------------------------------------------------------------------------------
def _disassemble3(co, lasti):
    """Disassemble a code object."""
    cell_names = co.co_cellvars + co.co_freevars
    linestarts = dict(dis.findlinestarts(co))
    _disassemble_bytes(co.co_code, lasti, co.co_varnames, co.co_names,
                       co.co_consts, cell_names, linestarts)


def _disassemble_bytes(code, lasti=-1, varnames=None, names=None,
                       constants=None, cells=None, linestarts=None,
                       line_offset=0):
    # Omit the line number column entirely if we have no line number info
    show_lineno = linestarts is not None
    lineno_width = 3 if show_lineno else 0
    for instr in dis._get_instructions_bytes(code, varnames, names,
                                             constants, cells, linestarts,
                                             line_offset=line_offset):
        new_source_line = (show_lineno and
                           instr.starts_line is not None and
                           instr.offset > 0)
        if new_source_line:
            qj.LOG_FN('')
        is_current_instr = instr.offset == lasti
        qj.LOG_FN(instr._disassemble(lineno_width, is_current_instr))


def _build_instruction_stack3(co, lasti):
  code = co.co_code

  linestarts = dict(dis.findlinestarts(co))

  stack = []

  num_instr = len(code)

  if qj._DEBUG_QJ:
    assert lasti < num_instr
  if lasti >= num_instr:
    return []

  curr_l = 0
  for instr in dis._get_instructions_bytes(code, co.co_varnames, co.co_names,
                                           co.co_consts, co.co_cellvars + co.co_freevars,
                                           linestarts):

    # instr.{opname opcode arg argval argrepr offset starts_line is_jump_target}
    curr_i = instr.offset
    curr_l = instr.starts_line or curr_l

    op = instr.opcode
    opname = instr.opname
    oparg = instr.arg
    oparg_repr = instr.argval
    if op >= opcode.HAVE_ARGUMENT:

      if opname.startswith('MAKE_') or opname.startswith('BUILD_'):
        oparg_repr = ''

      if isinstance(oparg_repr, str) and oparg_repr.startswith('.'):
        oparg_repr = ''  # Skip unnamed locals like .0
      elif isinstance(oparg_repr, types.CodeType):
        qj._DEBUG_QJ and qj._DISASSEMBLE_FN(oparg_repr, -1)
        if oparg_repr.co_name == '<lambda>':
          oparg_repr = ['lambda', ':']
        elif oparg_repr.co_name == '<dictcomp>' or oparg_repr.co_name == '<setcomp>':
          oparg_repr = ['{', '}']
        elif oparg_repr.co_name == '<genexpr>':
          oparg_repr = ['(', ')']
        elif oparg_repr.co_name == '<listcomp>':
          oparg_repr = ['[', ']']
        else:
          oparg_repr = ''

      if oparg > 0:
        if opname == 'BUILD_LIST':
          oparg_repr = ']'
        elif opname == 'BUILD_TUPLE':
          oparg_repr = ')'
        elif opname == 'BUILD_SET':
          oparg_repr = '}'
        elif opname == 'BUILD_MAP':
          oparg_repr = '{'  # BUILD_MAP happens at the beginning of the map
        elif opname == 'LIST_APPEND':
          oparg_repr = ']'
        elif opname == 'SET_ADD':
          oparg_repr = ''
        elif opname.startswith('CALL_FUNCTION'):
          oparg_repr = ')'
        elif opname == 'MAP_ADD':
          oparg_repr = ''
        elif opname == 'FOR_ITER':
          oparg_repr = ''
      elif oparg == 0:
        if opname == 'BUILD_LIST':
          # BUILD_LIST 0 occurs at the beginning of list comprehensions
          oparg_repr = '['
        elif opname == 'BUILD_TUPLE':
          oparg_repr = '('
        elif opname == 'BUILD_SET':
          oparg_repr = '{'
        elif opname == 'BUILD_MAP':
          oparg_repr = '{'
        elif opname.startswith('CALL_FUNCTION'):
          oparg_repr = ')'
    else:
      # Ops without arguments.
      if opname == 'UNARY_POSITIVE':
        oparg_repr = '+'
      elif opname == 'UNARY_NEGATIVE':
        oparg_repr = '-'
      elif opname == 'UNARY_NOT':
        oparg_repr = ''  # TODO(iansf)
      elif opname == 'UNARY_CONVERT':
        oparg_repr = ''  # TODO(iansf)
      elif opname == 'UNARY_INVERT':
        oparg_repr = '~'
      elif opname == 'BINARY_POWER':
        oparg_repr = '**'
      elif opname == 'BINARY_MULTIPLY':
        oparg_repr = '*'
      elif opname == 'BINARY_DIVIDE':
        oparg_repr = '/'
      elif opname == 'BINARY_MODULO':
        oparg_repr = '%'
      elif opname == 'BINARY_ADD':
        oparg_repr = '+'
      elif opname == 'BINARY_SUBTRACT':
        oparg_repr = '-'
      elif opname == 'BINARY_SUBSCR':
        oparg_repr = ']'
      elif opname == 'BINARY_FLOOR_DIVIDE':
        oparg_repr = '//'
      elif opname == 'BINARY_TRUE_DIVIDE':
        oparg_repr = '/'
      elif opname == 'BINARY_LSHIFT':
        oparg_repr = '<<'
      elif opname == 'BINARY_RSHIFT':
        oparg_repr = '>>'
      elif opname == 'BINARY_AND':
        oparg_repr = '&'
      elif opname == 'BINARY_XOR':
        oparg_repr = '^'
      elif opname == 'BINARY_OR':
        oparg_repr = '|'
      elif opname == 'GET_ITER':
        oparg_repr = ''
      elif opname.startswith('SLICE+'):
        oparg_repr = ':'

    if isinstance(oparg_repr, tuple):
      oparg_repr = list(oparg_repr)

    qj._DEBUG_QJ and qj.LOG_FN('%s\noriginal oparg_repr: %r\n     new oparg_repr: %r' % (opname, instr.argval, oparg_repr))

    stack_entry = _StackEntry(
        _stack_effect3(instr.opname, instr.arg),
        curr_i,
        curr_l,
        instr.opname,
        instr.arg,
        oparg_repr if isinstance(oparg_repr, list) else [str(oparg_repr)],
        [],  # children
    )

    if len(stack) and instr.opname == 'CALL_FUNCTION_EX':
      # CALL_FUNCTION_EX only sets the oparg to 0 or 1. 1 means there are kwargs to expand, as well as possibly tuple args.
      # 0 means there are tuple args to expand only. In that case, we still need CALL_FUNCTION_EX to actually consume a
      # stack entry, which will be the vararg.
      stack_entry.stack_depth = -1

    stack.append(stack_entry)

    if curr_i == lasti:
      break

  qj._DEBUG_QJ and [qj.LOG_FN('se: %s' % str(se)) for se in stack] and qj.LOG_FN('\n\n')

  return stack


_STACK_EFFECTS3 = {
    'POP_TOP': -1,
    'ROT_TWO': 0,
    'ROT_THREE': 0,
    'DUP_TOP': 1,
    'DUP_TOP_TWO': 2,

    'UNARY_POSITIVE': 0,
    'UNARY_NEGATIVE': 0,
    'UNARY_NOT': 0,
    'UNARY_INVERT': 0,

    'SET_ADD': -1,
    'LIST_APPEND': -1,
    'MAP_ADD': -2,

    'BINARY_POWER': -1,
    'BINARY_MULTIPLY': -1,
    'BINARY_MATRIX_MULTIPLY': -1,
    'BINARY_MODULO': -1,
    'BINARY_ADD': -1,
    'BINARY_SUBTRACT': -1,
    'BINARY_SUBSCR': -1,
    'BINARY_FLOOR_DIVIDE': -1,
    'BINARY_TRUE_DIVIDE': -1,
    'INPLACE_FLOOR_DIVIDE': -1,
    'INPLACE_TRUE_DIVIDE': -1,

    'INPLACE_ADD': -1,
    'INPLACE_SUBTRACT': -1,
    'INPLACE_MULTIPLY': -1,
    'INPLACE_MATRIX_MULTIPLY': -1,
    'INPLACE_MODULO': -1,
    'STORE_SUBSCR': -3,
    'DELETE_SUBSCR': -2,

    'BINARY_LSHIFT': -1,
    'BINARY_RSHIFT': -1,
    'BINARY_AND': -1,
    'BINARY_XOR': -1,
    'BINARY_OR': -1,
    'INPLACE_POWER': -1,
    'GET_ITER': 0,

    'PRINT_EXPR': -1,
    'LOAD_BUILD_CLASS': 1,
    'INPLACE_LSHIFT': -1,
    'INPLACE_RSHIFT': -1,
    'INPLACE_AND': -1,
    'INPLACE_XOR': -1,
    'INPLACE_OR': -1,
    'BREAK_LOOP': 0,
    'SETUP_WITH': 7,
    'WITH_CLEANUP_START': 1,
    'WITH_CLEANUP_FINISH': -1,  # Sometimes more
    'RETURN_VALUE': -1,
    'IMPORT_STAR': -1,
    'SETUP_ANNOTATIONS': 0,
    'YIELD_VALUE': 0,
    'YIELD_FROM': -1,
    'POP_BLOCK': 0,
    'POP_EXCEPT': 0,  # -3 except if bad bytecode
    'END_FINALLY': -1,  # or -2 or -3 if exception occurred

    'STORE_NAME': -1,
    'DELETE_NAME': 0,
    'FOR_ITER': 1,  # or -1, at end of iterator

    'STORE_ATTR': -2,
    'DELETE_ATTR': -1,
    'STORE_GLOBAL': -1,
    'DELETE_GLOBAL': 0,
    'LOAD_CONST': 1,
    'LOAD_NAME': 1,
    'LOAD_ATTR': 0,
    'COMPARE_OP': -1,
    'IMPORT_NAME': -1,
    'IMPORT_FROM': 1,

    'JUMP_FORWARD': 0,
    'JUMP_IF_TRUE_OR_POP': 0,  # -1 if jump not taken
    'JUMP_IF_FALSE_OR_POP': 0,  # -1 if jump not taken
    'JUMP_ABSOLUTE': 0,

    'POP_JUMP_IF_FALSE': -1,
    'POP_JUMP_IF_TRUE': -1,

    'LOAD_GLOBAL': 1,

    'CONTINUE_LOOP': 0,
    'SETUP_LOOP': 0,
    'SETUP_EXCEPT': 6,
    'SETUP_FINALLY': 6,  # can push 3 values for the new exception + 3 others for the previous exception state

    'LOAD_FAST': 1,
    'STORE_FAST': -1,
    'DELETE_FAST': 0,
    'STORE_ANNOTATION': -1,


    'LOAD_CLOSURE': 1,
    'LOAD_DEREF': 1,
    'LOAD_CLASSDEREF': 1,
    'STORE_DEREF': -1,
    'DELETE_DEREF': 0,
    'GET_AWAITABLE': 0,
    'SETUP_ASYNC_WITH': 6,
    'BEFORE_ASYNC_WITH': 1,
    'GET_AITER': 0,
    'GET_ANEXT': 1,
    'GET_YIELD_FROM_ITER': 0,
}


def _stack_effect3(op_code, oparg):
  """Compute the effect an op_code and oparg have on the stack.  See python/compile.c."""
  if op_code == 'UNPACK_SEQUENCE':
    return oparg - 1
  if op_code == 'UNPACK_EX':
    return (oparg & 0xFF) + (oparg >> 8)
  if op_code == 'BUILD_TUPLE':
    return -oparg  # Was 1 - oparg
  if op_code == 'BUILD_LIST':
    return -oparg  # Was 1 - oparg
  if op_code == 'BUILD_SET':
    return -oparg  # Was 1 - oparg
  if op_code == 'BUILD_STRING':
    return -oparg  # Was 1 - oparg
  if op_code == 'BUILD_LIST_UNPACK':
    return -oparg  # Was 1 - oparg
  if op_code == 'BUILD_TUPLE_UNPACK':
    return -oparg  # Was 1 - oparg
  if op_code == 'BUILD_TUPLE_UNPACK_WITH_CALL':
    return -oparg  # Was 1 - oparg
  if op_code == 'BUILD_SET_UNPACK':
    return -oparg  # Was 1 - oparg
  if op_code == 'BUILD_MAP_UNPACK':
    return -oparg  # Was 1 - oparg
  if op_code == 'BUILD_MAP_UNPACK_WITH_CALL':
    return -oparg  # Was 1 - oparg
  if op_code == 'BUILD_MAP':
    return -2 * oparg  # Was 1 - 2 * oparg
  if op_code == 'BUILD_CONST_KEY_MAP':
    return -oparg
  if op_code == 'RAISE_VARARGS':
    return -oparg
  if op_code == 'CALL_FUNCTION':
    return -oparg
  if op_code == 'CALL_FUNCTION_KW':
    return -oparg - 1
  if op_code == 'CALL_FUNCTION_EX':
    return -((oparg & 0x01) != 0) - ((oparg & 0x02) != 0)
  if op_code == 'MAKE_FUNCTION':
    return -1 - ((oparg & 0x01) != 0) - ((oparg & 0x02) != 0) - ((oparg & 0x04) != 0) - ((oparg & 0x08) != 0)
  if op_code == 'BUILD_SLICE':
    return -2 if (oparg == 3) else -1
  if op_code == 'FORMAT_VALUE':
    # If there's a fmt_spec on the stack we go from 2->1 else 1->1.
    return -1 if (oparg & FVS_MASK) == FVS_HAVE_SPEC else 0
  if op_code == 'EXTENDED_ARG':
    return 0  # EXTENDED_ARG just builds up a longer argument value for the next instruction (there may be multiple in a row?)

  return _STACK_EFFECTS3[op_code]



#------------------------------------------------------------------------------
# Python 2.7 Helpers
#------------------------------------------------------------------------------
def _findlinestarts(code):
  """Find the offsets in a byte code which are start of lines in the source.

  Generate pairs (offset, lineno) as described in Python/compile.c.

  Arguments:
    code: code object.

  Yields:
    Address and line number pairs.
  """
  byte_increments = [ord(c) for c in code.co_lnotab[0::2]]
  line_increments = [ord(c) for c in code.co_lnotab[1::2]]

  lastlineno = None
  lineno = code.co_firstlineno
  addr = 0
  for byte_incr, line_incr in zip(byte_increments, line_increments):
    if byte_incr:
      if lineno != lastlineno:
        yield (addr, lineno)
        lastlineno = lineno
      addr += byte_incr
    lineno += line_incr
  if lineno != lastlineno:
    yield (addr, lineno)


def _disassemble(co, lasti):
  code = co.co_code
  linestarts = dict(_findlinestarts(co))
  n = len(code)
  i = 0
  extended_arg = 0
  free = None
  while i < n:
    s = ''
    c = code[i]
    op = ord(c)
    if i in linestarts:
      if i > 0:
        qj.LOG_FN('')
      s += '%3d' % linestarts[i]
    else:
      s += '   '

    if i == lasti:
      s += '-->'
    else:
      s += '   '
    s += repr(i).rjust(4) + ' '
    s += opcode.opname[op].ljust(20)
    i += 1
    if op >= opcode.HAVE_ARGUMENT:
      oparg = ord(code[i]) + ord(code[i + 1]) * 256 + extended_arg
      extended_arg = 0
      i += 2
      if op == opcode.EXTENDED_ARG:
        extended_arg = oparg * 65536
      s += repr(oparg).rjust(5)
      if op in opcode.hasconst:
        s += '(' + repr(co.co_consts[oparg]) + ')'
      elif op in opcode.hasname:
        s += '(' + co.co_names[oparg] + ')'
      elif op in opcode.hasjrel:
        s += '(to ' + repr(i + oparg) + ')'
      elif op in opcode.haslocal:
        s += '(' + co.co_varnames[oparg] + ')'
      elif op in opcode.hascompare:
        s += '(' + opcode.cmp_op[oparg] + ')'
      elif op in opcode.hasfree:
        if free is None:
          free = co.co_cellvars + co.co_freevars
        s += '(' + free[oparg] + ')'
    qj.LOG_FN(s)


_STACK_EFFECTS = {
    'POP_TOP': -1,
    'ROT_TWO': 0,
    'ROT_THREE': 0,
    'DUP_TOP': 1,
    'ROT_FOUR': 0,

    'UNARY_POSITIVE': 0,
    'UNARY_NEGATIVE': 0,
    'UNARY_NOT': 0,
    'UNARY_CONVERT': 0,
    'UNARY_INVERT': 0,

    'SET_ADD': -1,
    'LIST_APPEND': -1,

    'MAP_ADD': -2,

    'BINARY_POWER': -1,
    'BINARY_MULTIPLY': -1,
    'BINARY_DIVIDE': -1,
    'BINARY_MODULO': -1,
    'BINARY_ADD': -1,
    'BINARY_SUBTRACT': -1,
    'BINARY_SUBSCR': -1,
    'BINARY_FLOOR_DIVIDE': -1,
    'BINARY_TRUE_DIVIDE': -1,
    'INPLACE_FLOOR_DIVIDE': -1,
    'INPLACE_TRUE_DIVIDE': -1,

    'SLICE+0': 0,
    'SLICE+1': -1,
    'SLICE+2': -1,
    'SLICE+3': -2,

    'STORE_SLICE+0': -2,
    'STORE_SLICE+1': -3,
    'STORE_SLICE+2': -3,
    'STORE_SLICE+3': -4,

    'DELETE_SLICE+0': -1,
    'DELETE_SLICE+1': -2,
    'DELETE_SLICE+2': -2,
    'DELETE_SLICE+3': -3,

    'INPLACE_ADD': -1,
    'INPLACE_SUBTRACT': -1,
    'INPLACE_MULTIPLY': -1,
    'INPLACE_DIVIDE': -1,
    'INPLACE_MODULO': -1,
    'STORE_SUBSCR': -3,
    'STORE_MAP': -2,
    'DELETE_SUBSCR': -2,

    'BINARY_LSHIFT': -1,
    'BINARY_RSHIFT': -1,
    'BINARY_AND': -1,
    'BINARY_XOR': -1,
    'BINARY_OR': -1,
    'INPLACE_POWER': -1,
    'GET_ITER': 0,

    'PRINT_EXPR': -1,
    'PRINT_ITEM': -1,
    'PRINT_NEWLINE': 0,
    'PRINT_ITEM_TO': -2,
    'PRINT_NEWLINE_TO': -1,
    'INPLACE_LSHIFT': -1,
    'INPLACE_RSHIFT': -1,
    'INPLACE_AND': -1,
    'INPLACE_XOR': -1,
    'INPLACE_OR': -1,
    'BREAK_LOOP': 0,
    'SETUP_WITH': 4,
    # Originally was -1 with note that it's sometimes more.
    # Better to balance with SETUP_WITH.
    # TODO(iansf): Still doesn't work.
    'WITH_CLEANUP': -1,
    'LOAD_LOCALS': 1,
    'RETURN_VALUE': -1,
    'IMPORT_STAR': -1,
    'EXEC_STMT': -3,
    'YIELD_VALUE': 0,

    'POP_BLOCK': 0,
    'END_FINALLY': -3,  # or -1 or -2 if no exception occurred or break/continue
    'BUILD_CLASS': -2,

    'STORE_NAME': -1,
    'DELETE_NAME': 0,
    # 1 at start of iterator, -1 at end of iterator, balances out to 0
    'FOR_ITER': 0,

    'STORE_ATTR': -2,
    'DELETE_ATTR': -1,
    'STORE_GLOBAL': -1,
    'DELETE_GLOBAL': 0,
    'LOAD_CONST': 1,
    'LOAD_NAME': 1,
    'BUILD_MAP': 1,
    'LOAD_ATTR': 0,
    'COMPARE_OP': -1,
    'IMPORT_NAME': -1,
    'IMPORT_FROM': 1,

    'JUMP_FORWARD': 0,
    'JUMP_IF_TRUE_OR_POP': 0,  # -1 if jump not taken
    'JUMP_IF_FALSE_OR_POP': 0,  # -1 if jump not taken
    'JUMP_ABSOLUTE': 0,

    'POP_JUMP_IF_FALSE': -1,
    'POP_JUMP_IF_TRUE': -1,

    'LOAD_GLOBAL': 1,

    'CONTINUE_LOOP': 0,
    'SETUP_LOOP': 0,
    'SETUP_EXCEPT': 0,
    'SETUP_FINALLY': 0,

    'LOAD_FAST': 1,
    'STORE_FAST': -1,
    'DELETE_FAST': 0,

    'LOAD_CLOSURE': 1,
    'LOAD_DEREF': 1,
    'STORE_DEREF': -1,
}


def _stack_effect(op_code, oparg):
  """Compute the effect an op_code and oparg have on the stack.  See python/compile.c."""
  n_args = lambda o: (o % 256) + 2 * (o // 256)

  if op_code == 'DUP_TOPX':
    return oparg
  elif op_code == 'UNPACK_SEQUENCE':
    return oparg - 1
  elif op_code == 'BUILD_TUPLE':
    return -oparg  # Was 1 - oparg
  elif op_code == 'BUILD_LIST':
    return -oparg  # Was 1 - oparg
  elif op_code == 'BUILD_SET':
    return -oparg  # Was 1 - oparg
  elif op_code == 'RAISE_VARARGS':
    return -oparg
  elif op_code == 'CALL_FUNCTION':
    return -n_args(oparg)  # args + (#kwargs << 8)
  elif op_code == 'CALL_FUNCTION_VAR':
    return -n_args(oparg) - 1  # args + (#kwargs << 8)
  elif op_code == 'CALL_FUNCTION_KW':
    return -n_args(oparg) - 1  # args + (#kwargs << 8)
  elif op_code == 'CALL_FUNCTION_VAR_KW':
    return -n_args(oparg) - 2  # args + (#kwargs << 8)
  elif op_code == 'MAKE_FUNCTION':
    return -oparg
  elif op_code == 'BUILD_SLICE':
    if oparg == 3:
      return -2
    else:
      return -1
  elif op_code == 'MAKE_CLOSURE':
    return -oparg - 1

  return _STACK_EFFECTS[op_code]


class _StackEntry(object):
  """An entry in the decompilation stack."""

  def __init__(self,
               stack_depth,
               curr_i,
               curr_l,  # According to python, but can be inaccurate
               opname,
               oparg,
               oparg_repr,
               children,  # Array of StackEntries
              ):
    self.stack_depth = stack_depth
    self.curr_i = curr_i
    self.curr_l = curr_l
    self.opname = opname
    self.oparg = oparg
    self.oparg_repr = oparg_repr
    self.children = children

  def __str__(self):
    # pylint: disable=bad-continuation
    return ('_StackEntry(stack_depth: {stack_depth}, '
                        'curr_i: {curr_i}, '
                        'opname: \'{opname}\', '
                        'oparg: {oparg}, '
                        'oparg_repr: {oparg_repr}, '
                        'children: {children}'
                        ')'.format(
                            **self.__dict__))
# pylint: enable=bad-continuation

  __repr__ = __str__


def _find_earliest_shortest_match(target, reg, search_start, search_end, num_attempts=10):
  """Find the shortest string matching reg in the search area."""
  shortest_match = None
  shortest_match_search_start = 0
  shortest_match_search_end = 0
  qj._DEBUG_QJ and qj.LOG_FN('regex: %s' % reg)
  for i in range(num_attempts):
    search_target = target[search_start:search_end]
    qj._DEBUG_QJ and qj.LOG_FN('searching (%d): %s' % (i, search_target))

    matches = re.search(reg, search_target)
    if (matches
        and (shortest_match is None
             or (shortest_match is not None
                 and (matches.end() - matches.start() < shortest_match.end() - shortest_match.start())))):
      qj._DEBUG_QJ and qj.LOG_FN('found new shortest match: %s (%d, %d)' %
                                 (matches.group(0), matches.start(),
                                  matches.end()))

      shortest_match = matches
      shortest_match_search_start = search_start
      shortest_match_search_end = search_end

      search_end = search_start + matches.end()
      search_start += matches.start() + 1

      if not matches.group(0):
        break
    else:
      break

  return shortest_match, shortest_match_search_start, shortest_match_search_end


def _annotate_fn_args(stack, fn_opname, nargs, nkw=-1, consume_fn_name=True):
  """Add commas and equals as appropriate to function argument lists in the stack."""
  kwarg_names = []
  if nkw == -1:
    if sys.version_info[0] < 3:
      # Compute nkw and nargs from nargs for python 2.7
      nargs, nkw = (nargs % 256, 2 * nargs // 256)
    else:
      if fn_opname == 'CALL_FUNCTION_KW':
        if qj._DEBUG_QJ:
          assert len(stack) and stack[-1].opname == 'LOAD_CONST'
        if not len(stack) or stack[-1].opname != 'LOAD_CONST':
          return
        se = stack.pop()
        kwarg_names = se.oparg_repr[::-1]
        se.oparg_repr = ['']
        nkw = len(kwarg_names)
        nargs -= nkw
        if qj._DEBUG_QJ:
          assert nargs >= 0 and nkw > 0
      else:
        nkw = 0

  for i in range(nkw):
    se = stack.pop()
    if se.stack_depth == 0 and (len(se.oparg_repr) == 0 or se.oparg_repr[0] == ''):
      # Skip stack entries that don't have any effect on the stack
      continue
    if i % 2 == 1 and sys.version_info[0] < 3:
      if qj._DEBUG_QJ:
        assert se.opname == 'LOAD_CONST'
      if se.opname == 'LOAD_CONST':
        # kwargs are pairs of key=value in code
        se.oparg_repr += ['=']
    else:
      pops = []
      if se.opname.startswith('CALL_FUNCTION'):
        _annotate_fn_args(stack[:], se.opname, se.oparg, -1, True)
      pops = _collect_pops(stack, se.stack_depth - 1 if se.opname.startswith('CALL_FUNCTION') else 0, [], False)
      if i > 1 and len(pops):
        pops[-1].oparg_repr += [',']
      if sys.version_info[0] >= 3:
        target_se = pops[-1] if len(pops) else se
        target_se.oparg_repr = [kwarg_names[i], '='] + target_se.oparg_repr

  for i in range(nargs):
    se = stack.pop()
    if se.opname.startswith('CALL_FUNCTION'):
      _annotate_fn_args(stack, se.opname, se.oparg, -1, True)
    elif len(se.oparg_repr) and se.oparg_repr[0] in {']', '}', ')'}:
      if (i > 0 or nkw > 0):
        se.oparg_repr += [',']
    else:
      pops = _collect_pops(stack, se.stack_depth, [], False)
      if (i > 0 or nkw > 0) and len(pops):
        pops[-1].oparg_repr += [',']

  if consume_fn_name:
    _collect_pops(stack, -1, [], False)


def _collect_pops(stack, depth, pops, skip):
  """Recursively collects stack entries off the top of the stack according to the stack entry's depth."""
  if depth >= 0:
    return pops

  set_current_depth_after_recursion = False
  set_skip_for_current_entry_children = False
  set_skip_after_current_entry = False
  extract_next_tokens = False
  expect_extracted_tokens = []

  se = stack.pop()
  pops_len = len(pops)
  if (pops_len > 1
      and se.opname == 'BUILD_TUPLE'
      and pops[-1].opname == 'LOAD_CONST'
      and pops[-1].oparg_repr[0] in ['lambda', '{', '(', '[']
      and pops[-2].opname in ['MAKE_CLOSURE', 'MAKE_FUNCTION']):
    # Skip BUILD_TUPLE and its children if they are storing arguments for a closure, since those don't show up in the code.
    skip = -se.stack_depth + 1

  if (pops_len > 2
      and sys.version_info[0] >= 3
      and se.opname == 'BUILD_TUPLE'
      and pops[-1].opname == 'LOAD_CONST'
      and pops[-1].oparg_repr[0] in ['lambda', '{', '(', '[']
      and pops[-2].opname == 'LOAD_CONST'
      and pops[-3].opname in ['MAKE_CLOSURE', 'MAKE_FUNCTION']):
    # Skip BUILD_TUPLE and its children if they are storing arguments for a closure, since those don't show up in the code.
    skip = -se.stack_depth + 1

  if (pops_len > 0
      and se.opname == 'GET_ITER'
      and pops[-1].opname == 'CALL_FUNCTION'):
    # CALL_FUNCTION followed by GET_ITER means we are calling one of the comprehensions and we are about to load its arguments.
    # The CALL_FUNCTION at the top of the stack should be invisible, since it expects a ')' which won't appear in the code.
    pops[-1].oparg_repr = ['']
    # We need to extract the arguments that we're about to load so that we can store their tokens inside of the upcoming comprehension.
    extract_next_tokens = -1

  if (len(stack)
      and se.opname == 'BUILD_TUPLE_UNPACK_WITH_CALL'):
    extract_next_tokens = se.stack_depth
    expect_extracted_tokens = [
        # Expect LOAD_FAST as the first element (required=True), and prepend its oparg_repr with '*'.
        (0, 'LOAD_FAST', True, 'prepend', ['*']),
        # Expect BUILD_TUPLE as the last stack token extracted (required=False) and replace its oparg_repr with ''.
        (abs(extract_next_tokens) - 1, 'BUILD_TUPLE', False, 'replace', [''])
    ]
    set_current_depth_after_recursion = se.stack_depth
    se.stack_depth = 0

  if (pops_len > 0
      and sys.version_info[0] >= 3
      and se.opname == 'LOAD_CONST'
      and pops[-1].opname == 'MAKE_FUNCTION'):
    # In python 3, MAKE_FUNCTION followed by LOAD_CONST is loading the name of the function, which won't appear in the code.
    se.oparg_repr = ['']
    # Additionally, this entry shouldn't impact future stack computations, as MAKE_FUNCTION will be removed.
    set_current_depth_after_recursion = 0

  if pops_len and pops[-1].opname == 'LIST_APPEND':
    # Skip all but the first stack entry of list comprehensions. Sets the skip value to be all remaining stack entries.
    # The BUILD_LIST check below will disable skip at the right time.
    set_skip_after_current_entry = len(stack)

  if skip > 0 and se.opname == 'BUILD_LIST' and se.stack_depth == 0:
    # If we're in skip mode and we just hit what might be the beginning of a list comprehension, check for a LIST_APPEND in the current pops.
    for popped_se in pops[::-1]:
      if popped_se.opname == 'LIST_APPEND':
        skip = 0
        break

  children_skip = skip
  if (se.opname.startswith('UNARY_')
      or (se.opname.startswith('BINARY_') and se.opname != 'BINARY_SUBSCR')
      or se.opname == 'SLICE+2'
      or se.opname == 'SLICE+3'
      or se.opname == 'COMPARE_OP'):
    # Unary and binary ops come after their operand(s) on the stack, but before (or between) their operand(s) in code, so we need to reverse that.

    if set_skip_for_current_entry_children or skip > 0:
      children_skip = 1
    pops = _collect_pops(stack, -1, pops, children_skip)

    if skip <= 0:
      pops.append(se)
      qj._DEBUG_QJ and qj.LOG_FN('added se: %r' % se)
    else:
      qj._DEBUG_QJ and qj.LOG_FN('(skipping se: %r %r)' % (se.opname, se.oparg_repr))

    popped_depth = se.stack_depth + 1
  else:
    # Non prefix/infix ops -- their representations come after their children in code, or they don't have children.
    if skip <= 0:
      pops.append(se)
      qj._DEBUG_QJ and qj.LOG_FN('added se: %r' % se)
    else:
      qj._DEBUG_QJ and qj.LOG_FN('(skipping se: %r %r)' % (se.opname, se.oparg_repr))

    if ((se.stack_depth < 0
         and se.opname != 'BUILD_SLICE'
         and se.opname.startswith('BUILD_'))
        or se.stack_depth >= 0):
      next_depth = se.stack_depth
    else:
      next_depth = se.stack_depth - 1

    if set_skip_for_current_entry_children or skip > 0:
      children_skip = abs(next_depth)
    if se.opname == 'BUILD_SLICE':
      # BUILD_SLICE's arguments need to be collected, as missing args are replaced with Nones which don't appear in the code.
      slice_pops = _collect_pops(stack, next_depth, [], children_skip)
      added_colon = 0
      for slice_se in slice_pops:
        if slice_se.opname == 'LOAD_CONST' and slice_se.oparg_repr[0] == 'None':
          if added_colon >= 1:
            slice_se.oparg_repr = ['']
          else:
            slice_se.oparg_repr = [':']
            added_colon += 1
        pops.append(slice_se)
    else:
      pops = _collect_pops(stack, next_depth, pops, children_skip)

    # BUILD_LIST 0 marks the start of a list comprehension, but we need it to consume a slot on the stack.
    if se.stack_depth == 0 and se.opname != 'BUILD_LIST':
      popped_depth = 0
    else:
      popped_depth = 1

  tokens = []
  if extract_next_tokens < 0:
    tokens = _collect_pops(stack, extract_next_tokens, [], skip)
    for index, expected_token, required, fixup_type, fixup_value in expect_extracted_tokens:
      if qj._DEBUG_QJ:
        assert (index < 0 and index + len(tokens) > 0) or 0 <= index < len(tokens)
        if required:
          assert tokens[index].opname == expected_token
      if (index < 0 and index + len(tokens) > 0) or 0 <= index < len(tokens) and tokens[index].opname == expected_token:
        if fixup_type == 'prepend':
          tokens[index].oparg_repr = fixup_value + tokens[index].oparg_repr
        elif fixup_type == 'replace':
          tokens[index].oparg_repr = fixup_value
    tokens.reverse()
    popped_depth -= extract_next_tokens

  if children_skip > 0:
    skip -= popped_depth

  if set_skip_after_current_entry > 0:
    skip = set_skip_after_current_entry + max(0, skip)

  pops = _collect_pops(stack, depth + popped_depth, pops, skip)

  if len(tokens):  # pylint: disable=g-explicit-length-test
    target_se = pops[-1]
    target_se.children.append(tokens)
    target_se.oparg_repr = target_se.oparg_repr[:1] + [t for token in tokens for t in token.oparg_repr] + target_se.oparg_repr[1:]

  if set_current_depth_after_recursion is not False:
    se.stack_depth = set_current_depth_after_recursion

  return pops


def _build_instruction_stack(co, lasti):
  code = co.co_code

  linestarts = dict(_findlinestarts(co))

  instr_to_ops = collections.OrderedDict()

  num_instr = len(code)

  if qj._DEBUG_QJ:
    assert lasti < num_instr
  if lasti >= num_instr:
    return ''

  instr = 0
  extended_arg = 0
  free = None
  curr_l = 0
  while instr <= lasti:
    curr_i = instr
    if instr in linestarts:
      curr_l = linestarts[instr]

    op = ord(code[instr])
    opname = opcode.opname[op]

    oparg = -1
    oparg_repr = ''

    instr += 1

    if op >= opcode.HAVE_ARGUMENT:
      oparg = ord(code[instr]) + ord(code[instr + 1]) * 256 + extended_arg
      extended_arg = 0
      instr += 2
      if op == opcode.EXTENDED_ARG:
        extended_arg = oparg * 65536

      if op in opcode.hasconst:
        oparg_repr = co.co_consts[oparg]
        if isinstance(oparg_repr, types.CodeType):
          qj._DEBUG_QJ and qj._DISASSEMBLE_FN(oparg_repr, -1)
          if oparg_repr.co_name == '<lambda>':
            oparg_repr = ['lambda', ':']
          elif oparg_repr.co_name == '<dictcomp>' or oparg_repr.co_name == '<setcomp>':
            oparg_repr = ['{', '}']
          elif oparg_repr.co_name == '<genexpr>':
            oparg_repr = ['(', ')']
          else:
            oparg_repr = ''
      elif op in opcode.hasname:
        oparg_repr = co.co_names[oparg]
      elif op in opcode.hasjrel:
        oparg_repr = ''  # instr + oparg
      elif op in opcode.haslocal:
        oparg_repr = co.co_varnames[oparg]
        if oparg_repr.startswith('.'):
          oparg_repr = ''  # Skip unnamed locals like .0
      elif op in opcode.hascompare:
        oparg_repr = opcode.cmp_op[oparg]
      elif op in opcode.hasfree:
        if free is None:
          free = co.co_cellvars + co.co_freevars
        oparg_repr = free[oparg]

      if oparg > 0:
        if opname == 'BUILD_LIST':
          oparg_repr = ']'
        elif opname == 'BUILD_TUPLE':
          oparg_repr = ')'
        elif opname == 'BUILD_SET':
          oparg_repr = '}'
        elif opname == 'BUILD_MAP':
          oparg_repr = '{'  # BUILD_MAP happens at the beginning of the map
        elif opname == 'LIST_APPEND':
          oparg_repr = ']'
        elif opname == 'SET_ADD':
          oparg_repr = ''
        elif opname.startswith('CALL_FUNCTION'):
          oparg_repr = ')'
        elif opname == 'MAP_ADD':
          oparg_repr = ''
        elif opname == 'FOR_ITER':
          oparg_repr = ''
      elif oparg == 0:
        if opname == 'BUILD_LIST':
          # BUILD_LIST 0 occurs at the beginning of list comprehensions
          oparg_repr = '['
        elif opname == 'BUILD_TUPLE':
          oparg_repr = '('
        elif opname == 'BUILD_SET':
          oparg_repr = '{'
        elif opname == 'BUILD_MAP':
          oparg_repr = '{'
        elif opname.startswith('CALL_FUNCTION'):
          oparg_repr = ')'
        elif opname == 'MAKE_CLOSURE':
          oparg_repr = ''
    else:
      # Ops without arguments.
      if opname == 'UNARY_POSITIVE':
        oparg_repr = '+'
      elif opname == 'UNARY_NEGATIVE':
        oparg_repr = '-'
      elif opname == 'UNARY_NOT':
        oparg_repr = ''  # TODO(iansf)
      elif opname == 'UNARY_CONVERT':
        oparg_repr = ''  # TODO(iansf)
      elif opname == 'UNARY_INVERT':
        oparg_repr = '~'
      elif opname == 'BINARY_POWER':
        oparg_repr = '**'
      elif opname == 'BINARY_MULTIPLY':
        oparg_repr = '*'
      elif opname == 'BINARY_DIVIDE':
        oparg_repr = '/'
      elif opname == 'BINARY_MODULO':
        oparg_repr = '%'
      elif opname == 'BINARY_ADD':
        oparg_repr = '+'
      elif opname == 'BINARY_SUBTRACT':
        oparg_repr = '-'
      elif opname == 'BINARY_SUBSCR':
        oparg_repr = ']'
      elif opname == 'BINARY_FLOOR_DIVIDE':
        oparg_repr = '//'
      elif opname == 'BINARY_TRUE_DIVIDE':
        oparg_repr = '/'
      elif opname == 'BINARY_LSHIFT':
        oparg_repr = '<<'
      elif opname == 'BINARY_RSHIFT':
        oparg_repr = '>>'
      elif opname == 'BINARY_AND':
        oparg_repr = '&'
      elif opname == 'BINARY_XOR':
        oparg_repr = '^'
      elif opname == 'BINARY_OR':
        oparg_repr = '|'
      elif opname == 'GET_ITER':
        oparg_repr = ''
      elif opname.startswith('SLICE+'):
        oparg_repr = ':'

    stack_entry = _StackEntry(
        _stack_effect(opname, oparg),
        curr_i,
        curr_l,
        opname,
        oparg,
        oparg_repr if isinstance(oparg_repr, list) else [str(oparg_repr)],
        [],  # children
    )

    instr_to_ops[curr_i] = stack_entry

  stack = [instr_to_ops[curr_i] for curr_i in sorted(instr_to_ops.keys())]
  qj._DEBUG_QJ and [qj.LOG_FN('se: %s' % str(se)) for se in stack] and qj.LOG_FN('\n\n')

  return stack


def _find_current_fn_call(co, lasti):
  """Find current function call in the byte code."""
  qj._DEBUG_QJ and qj.LOG_FN('co = {}'.format(co))

  if sys.version_info[0] < 3:
    stack = _build_instruction_stack(co, lasti)
  else:
    stack = _build_instruction_stack3(co, lasti)

  source_lines, source_offset = inspect.getsourcelines(co)
  source_lines = [l.strip() for l in source_lines]

  # Apply stack effects backwards until we arrive at the stack entries for a complete function call
  fn_stack = _collect_pops(stack[:-1], stack[-1].stack_depth, [], 0)

  if not fn_stack and stack[-1].stack_depth == 0:
    # The function call took 0 arguments, so return early with a special string.
    return '<empty log>'

  qj._DEBUG_QJ and qj.LOG_FN('collected fn_stack:\n%s\n\n' % '\n'.join(str(se) for se in fn_stack))

  # Prepare to annotate the stack with extra symbols, and filter out MAKE_FUNCTION and MAKE_CLOSURE calls, which are no longer needed.
  annotate_stack = [se for se in fn_stack if not se.opname.startswith('MAKE_')]
  annotate_stack.reverse()
  _annotate_fn_args(annotate_stack, stack[-1].opname, stack[-1].oparg, -1, False)

  qj._DEBUG_QJ and qj.LOG_FN('annotated fn_stack:\n%s\n\n' % '\n'.join(str(se) for se in fn_stack))

  # Find the range of lines to search over.
  min_l = stack[-1].curr_l
  max_l = stack[0].curr_l
  for se in fn_stack:
    min_l = min(min_l, se.curr_l)
    max_l = max(max_l, se.curr_l)

  qj._DEBUG_QJ and qj.LOG_FN('source lines range: %d -> %d (indices: %d, %d)' % (min_l, max_l, min_l - source_offset, max_l - source_offset + 1))
  source_chunk = ' '.join(
      [l for l in source_lines[min_l - source_offset:max_l - source_offset + 1] if l and not l.startswith('#')])

  qj._DEBUG_QJ and qj.LOG_FN('source_chunk: %r' % source_chunk)

  # Build up all of the tokens for the function call.
  tokens = []
  for se in fn_stack:
    opname = se.opname
    for oparg_repr in se.oparg_repr[::-1]:
      # Clean up the tokens
      if not oparg_repr:
        continue
      oparg_repr = re.escape(oparg_repr.replace('\n', '\\n'))
      tokens.append(oparg_repr)

  tokens.reverse()
  qj._DEBUG_QJ and qj.LOG_FN('extracted tokens: {}'.format(tokens))
  if qj._DEBUG_QJ:
    assert tokens

  # Add tokens for the function call we're extracting.
  tokens = ['\\('] + tokens + ['\\)']

  reg = '\b*?.*?\b*?'.join(tokens)
  qj._DEBUG_QJ and qj.LOG_FN(reg)

  # Search for the function call using the full set of tokens.
  # Expand the search with source lines after the current set if we don't find a match.
  shortest_match = None
  match_attempts = 0
  max_match_attempts = 10
  while not shortest_match and match_attempts < max_match_attempts:
    (shortest_match, _, _) = (
        _find_earliest_shortest_match(source_chunk, reg, 0, len(source_chunk), num_attempts=10))
    if not shortest_match:
      match_attempts += 1

      min_l -= 1
      prev_line = ''
      while not prev_line and min_l - source_offset >= 0 and min_l - source_offset < len(source_lines):
        prev_line = source_lines[min_l - source_offset]
        if prev_line.startswith('#'):
          prev_line = ''
        if not prev_line:
          min_l -= 1
      prev_line += ' ' if prev_line else ''
      source_chunk = prev_line + source_chunk

      max_l += 1
      next_line = ''
      while not next_line and max_l - source_offset >= 0 and max_l - source_offset < len(source_lines):
        next_line = source_lines[max_l - source_offset]
        if next_line.startswith('#'):
          next_line = ''
        if not next_line:
          max_l += 1
      next_line = (' ' if next_line else '') + next_line
      source_chunk += next_line

  # Return the string for the function call
  if qj._DEBUG_QJ:
    assert shortest_match
  if shortest_match is not None:
    match = shortest_match.group(0)
    if qj._DEBUG_QJ:
      assert match.startswith('(') and match.endswith(')')
    # Do some parentheses cleanup.
    if match.startswith('('):
      match = match[1:]
    lparens = match.count('(')
    rparens = match.count(')')
    if lparens > rparens:
      match += ')' * (lparens - rparens)
    elif lparens < rparens:
      rparens_to_remove = rparens - lparens
      while len(match) and match[-1] == ')' and rparens_to_remove > 0:
        match = match[:-1]
        rparens_to_remove -= 1
    match = match.strip()
    return match
  else:
    return ''

qj._DISASSEMBLE_FN = _disassemble if sys.version_info[0] < 3 else _disassemble3

###############################################################################
# End Code Correlation Code
###############################################################################

# pylint: enable=g-long-lambda, protected-access, expression-not-assigned
# pylint: enable=line-too-long
