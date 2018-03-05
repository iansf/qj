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

import setuptools


def readme():
  with open('README.md') as f:
    return f.read()


def version():
  return '0.1.2'


setuptools.setup(
    name='qj',
    description='qj: logging designed for debugging.',
    long_description=readme(),
    version=version(),
    url='https://github.com/iansf/qj',
    download_url='https://github.com/iansf/qj/archive/%s.tar.gz' % version(),
    author='Ian Fischer, Google',
    author_email='iansf@google.com',
    packages=['qj', 'qj_global'],
    license='Apache 2.0',
    install_requires=[],
    test_suite='nose.collector',
    tests_require=['nose'],
)
