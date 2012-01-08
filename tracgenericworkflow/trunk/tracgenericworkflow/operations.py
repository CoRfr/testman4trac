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
from trac.perm import PermissionSystem
from trac.resource import Resource
from trac.util.datefmt import utc
from trac.util.translation import _, N_, gettext
from trac.web.chrome import Chrome

from genshi.builder import tag
from genshi.filters.transform import Transformer
from genshi import HTML

from tracgenericclass.util import *

from tracgenericworkflow.model import ResourceWorkflowState
from tracgenericworkflow.api import IWorkflowOperationProvider, ResourceWorkflowSystem


# Out-of-the-box operations
class WorkflowStandardOperations(Component):
    """Adds a set of standard, out-of-the-box workflow operations."""
    
    implements(IWorkflowOperationProvider)

    # IWorkflowOperationProvider methods
    def get_implemented_operations(self):
        self.log.debug(">>> WorkflowStandardOperations - get_implemented_operations")
        self.log.debug("<<< WorkflowStandardOperations - get_implemented_operations")

        yield 'set_owner'
        yield 'set_owner_to_self'
        yield 'std_notify'

    def get_operation_control(self, req, action, operation, res_wf_state, resource):
        self.log.debug(">>> WorkflowStandardOperations - get_operation_control: %s" % operation)

        id = 'action_%s_operation_%s' % (action, operation)

        # A custom field named "owner" is required in the ResourceWorkflowState 
        # class for this operation to be available
        
        self.env.log.debug(res_wf_state.fields)
        
        if operation == 'set_owner' and self._has_field_named('owner', res_wf_state.fields):
            self.log.debug("Creating control for setting owner.")

            current_owner = res_wf_state['owner'] or '(none)'
            if not (Chrome(self.env).show_email_addresses
                    or 'EMAIL_VIEW' in req.perm(resource)):
                format_user = obfuscate_email_address
            else:
                format_user = lambda address: address
            current_owner = format_user(current_owner)

            self.log.debug("Current owner is %s." % current_owner)

            selected_owner = req.args.get(id, req.authname)

            control = None
            hint = ''

            owners = None

            available_owners = self.config.get(resource.realm, 'available_owners')
            if available_owners is not None and not available_owners == '':
                owners = [x.strip() for x in
                          available_owners.split(',')]
            elif self.config.getbool(resource.realm, 'restrict_owner'):
                target_permission = self.config.get(resource.realm, 'restrict_owner_to_permission')
                if target_permission is not None and not target_permission == '':
                    perm = PermissionSystem(self.env)
                    owners = perm.get_users_with_permission(target_permission)
                    owners.sort()

            if owners == None:
                owner = req.args.get(id, req.authname)
                control = tag('Assign to ',
                                    tag.input(type='text', id=id,
                                                    name=id, value=owner))
                hint = "The owner will be changed from %s" % current_owner
            elif len(owners) == 1:
                owner = tag.input(type='hidden', id=id, name=id,
                                  value=owners[0])
                formatted_owner = format_user(owners[0])
                control = tag('Assign to ',
                                    tag(formatted_owner, owner))
                if res_wf_state['owner'] != owners[0]:
                    hint = "The owner will be changed from %s to %s" % (current_owner, formatted_owner)
            else:
                control = tag('Assign to ', tag.select(
                    [tag.option(format_user(x), value=x,
                                selected=(x == selected_owner or None))
                     for x in owners],
                    id=id, name=id))
                hint = "The owner will be changed from %s" % current_owner

            return control, hint

        elif operation == 'set_owner_to_self' and self._has_field_named('owner', res_wf_state.fields) and \
                res_wf_state['owner'] != req.authname:
                    
            current_owner = res_wf_state['owner'] or '(none)'
            if not (Chrome(self.env).show_email_addresses
                    or 'EMAIL_VIEW' in req.perm(resource)):
                format_user = obfuscate_email_address
            else:
                format_user = lambda address: address
            current_owner = format_user(current_owner)
                    
            control = tag('')
            hint = "The owner will be changed from %s to %s" % (current_owner, req.authname)

            self.log.debug("<<< WorkflowStandardOperations - get_operation_control - set_owner_to_self")
            
            return control, hint

        elif operation == 'std_notify':
            pass
        
        self.log.debug("<<< WorkflowStandardOperations - get_operation_control")

        return None, ''
        
    def perform_operation(self, req, action, operation, old_state, new_state, res_wf_state, resource):
        self.log.debug("---> Performing operation %s while transitioning from %s to %s."
            % (operation, old_state, new_state))

        if operation == 'set_owner':
            if self.config.getbool(resource.realm, 'set_owners'):
                target_owners = self.config.getstring(resource.realm, 'restrict_to_permission')
                new_owner = target_owners.strip()
            else:
                new_owner = req.args.get('action_%s_operation_%s' % (action, operation), None)

            if new_owner is not None and len(new_owner.strip()) > 0:
                res_wf_state['owner'] = new_owner.strip()
                #res_wf_state.save_changes()
            else:
                self.log.debug("Unable to get the new owner!") 

        elif operation == 'set_owner_to_self':
            res_wf_state['owner'] = req.authname.strip()

    def _has_field_named(self, field_name, fields):
        for f in fields:
            if 'name' in f and f['name'] == field_name:
                return True
                
        return False

