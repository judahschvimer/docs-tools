# Copyright 2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

logger = logging.getLogger('giza.content.examples.models')

from giza.config.base import ConfigurationBase
from giza.inheritance import DataCache, DataContentBase, InheritableContentBase
from giza.serialization import ingest_yaml_doc

from pygments.lexers import get_all_lexers

# get a list of all supported pygment lexers.
all_languages = []
[ all_languages.extend(lexers[1]) for lexers in get_all_lexers() ]

class ExampleData(InheritableContentBase):
    @property
    def collection(self):
        if 'collection' not in self.state:
            return None
        else:
            return self.state['collection']

    @collection.setter
    def collection(self, value):
        self.state['collection'] = value

    @property
    def name(self):
        return self.collection

    @property
    def ref(self):
        return self.collection

    @property
    def documents(self):
        return self.state['documents']

    @documents.setter
    def documents(self, value):
        if isinstance(value, list):
            self.state['documents'] = value
        else:
            raise TypeError('{0} is not a list'.format(value))

class ExampleOperationBlock(ConfigurationBase):
    _option_registry = ['pre', 'post' ]

    @property
    def code(self):
        return self.state['code']

    @code.setter
    def code(self, value):
        if isinstance(value, list):
            self.state['code'] = value
        else:
            self.state['code'] = value.split('\n')

    @property
    def language(self):
        return self.state['language']

    @language.setter
    def language(self, value):
        if value in all_languages:
            self.state['language'] = value
        else:
            m = '{0} is not a supported language'.format(value)
            logger.error(m)
            TypeError(m)

class ExampleCase(InheritableContentBase):
    @property
    def operation(self):
        return self.state['operation']

    @operation.setter
    def operation(self, value):
        if isinstance(value, list):
            self.state['operation'] = [ ExampleOperationBlock(doc)
                                        for doc in value ]
        elif isinstance(value, dict):
            self.state['operation'] = [ ExampleOperationBlock(value) ]
        else:
            m = 'unable to create operation block from {0}'.format(value)
            logger.error(m)
            TypeError(m)

    name = operation
    @property
    def results(self):
        return self.state['results']

    @results.setter
    def results(self, value):
        if isinstance(value, list):
            self.state['results'] = value
        else:
            self.state['results'] = [ value ]
