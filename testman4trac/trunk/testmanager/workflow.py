# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2011 Roberto Bordolanghi
# 
# This file is part of the Test Manager plugin for Trac.
# 
# The Test Manager plugin for Trac is free software: you can 
# redistribute it and/or modify it under the terms of the GNU 
# General Public License as published by the Free Software Foundation, 
# either version 3 of the License, or (at your option) any later 
# version.
# 
# The Test Manager plugin for Trac is distributed in the hope that it 
# will be useful, but WITHOUT ANY WARRANTY; without even the implied 
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with the Test Manager plugin for Trac. See the file LICENSE.txt. 
# If not, see <http://www.gnu.org/licenses/>.
#

from trac.core import *
from trac.resource import Resource
from trac.util.datefmt import utc
from trac.web.api import ITemplateStreamFilter

from genshi.builder import tag
from genshi.filters.transform import Transformer
from genshi import HTML

from tracgenericclass.util import *

from tracgenericworkflow.model import ResourceWorkflowState
from tracgenericworkflow.api import IWorkflowOperationProvider, ResourceWorkflowSystem

# Workflow support
class TestManagerWorkflowInterface(Component):
    """Adds workflow capabilities to the TestManager plugin."""
    
    implements(IWorkflowOperationProvider, ITemplateStreamFilter)

    # IWorkflowOperationProvider methods
    # Just a sample operation
    def get_implemented_operations(self):
        self.log.debug(">>> TestManagerWorkflowInterface - get_implemented_operations")
        self.log.debug("<<< TestManagerWorkflowInterface - get_implemented_operations")

        yield 'sample_operation'

    def get_operation_control(self, req, action, operation, res_wf_state, resource):
        self.log.debug(">>> TestManagerWorkflowInterface - get_operation_control: %s" % operation)

        if operation == 'sample_operation':
            id = 'action_%s_operation_%s' % (action, operation)
            speech = 'Hello World!'

            control = tag.input(type='text', id=id, name=id, 
                                    value=speech)
            hint = "Will sing %s" % speech

            self.log.debug("<<< TestManagerWorkflowInterface - get_operation_control")
            
            return control, hint
        
        return None, ''
        
    def perform_operation(self, req, action, operation, old_state, new_state, res_wf_state, resource):
        self.log.debug("---> Performing operation %s while transitioning from %s to %s."
            % (operation, old_state, new_state))

        speech = req.args.get('action_%s_operation_%s' % (action, operation), 'Not found!')

        self.log.debug("        The speech is %s" % speech)


    # ITemplateStreamFilter methods
    def filter_stream(self, req, method, filename, stream, data):
        page_name = req.args.get('page', 'WikiStart')
        planid = req.args.get('planid', '-1')

        if page_name == 'TC':
            # The root catalog does not have workflows
            return stream

        if page_name.startswith('TC') and filename == 'wiki_view.html':
            self.log.debug(">>> TestManagerWorkflowInterface - filter_stream")
            req.perm.require('TEST_VIEW')
            
            # Determine which object is being displayed (i.e. realm), 
            # based on Wiki page name and the presence of the planid 
            # request parameter.
            realm = None
            if page_name.find('_TC') >= 0:
                if not planid or planid == '-1':
                    realm = 'testcase'
                    key = {'id': page_name.rpartition('_TC')[2]}
                else:
                    realm = 'testcaseinplan'
                    key = {'id': page_name.rpartition('_TC')[2], 'planid': planid}
            else:
                if not planid or planid == '-1':
                    realm = 'testcatalog'
                    key = {'id': page_name.rpartition('_TT')[2]}
                else:
                    realm = 'testplan'
                    key = {'id': planid}

            id = get_string_from_dictionary(key)
            res = Resource(realm, id)

            rwsystem = ResourceWorkflowSystem(self.env)
            workflow_markup = rwsystem.get_workflow_markup(req, '..', realm, res)
            
            self.log.debug("<<< TestManagerWorkflowInterface - filter_stream")

            return stream | Transformer('//div[contains(@class,"wikipage")]').after(workflow_markup) 

        return stream

