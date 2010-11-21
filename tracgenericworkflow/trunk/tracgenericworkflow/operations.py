from trac.core import *
from trac.resource import Resource
from trac.util.datefmt import utc
from trac.util.translation import _, N_, gettext

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
        
        print (res_wf_state.fields)
        
        if operation == 'set_owner' and 'owner' in res_wf_state.fields:
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

            if self.config.getbool(resource.realm, 'set_owners'):
                target_owners = self.config.getstring(resource.realm, 'restrict_to_permission')
                owners = [x.strip() for x in
                          target_owners.split(',')]
            elif self.config.getbool(resource.realm, 'restrict_owner'):
                target_permission = self.config.getstring(resource.realm, 'restrict_to_permission')
                perm = PermissionSystem(self.env)
                owners = perm.get_users_with_permission(target_permission)
                owners.sort()
            else:
                owners = None

            if owners == None:
                owner = req.args.get(id, req.authname)
                control = tag_('to %(owner)s',
                                    owner=tag.input(type='text', id=id,
                                                    name=id, value=owner))
                hint = _("The owner will be changed from "
                               "%(current_owner)s",
                               current_owner=current_owner)
            elif len(owners) == 1:
                owner = tag.input(type='hidden', id=id, name=id,
                                  value=owners[0])
                formatted_owner = format_user(owners[0])
                control = tag_('to %(owner)s ',
                                    owner=tag(formatted_owner, owner))
                if res_wf_state['owner'] != owners[0]:
                    hint = _("The owner will be changed from "
                                   "%(current_owner)s to %(selected_owner)s",
                                   current_owner=current_owner,
                                   selected_owner=formatted_owner)
            else:
                control = tag_('to %(owner)s', owner=tag.select(
                    [tag.option(format_user(x), value=x,
                                selected=(x == selected_owner or None))
                     for x in owners],
                    id=id, name=id))
                hint = _("The owner will be changed from "
                               "%(current_owner)s",
                               current_owner=current_owner)

            return control, hint

        elif operation == 'set_owner_to_self' and 'owner' in res_wf_state.fields and \
                res_wf_state['owner'] != req.authname:
            hint = _("The owner will be changed from %(current_owner)s "
                           "to %(authname)s", current_owner=current_owner,
                           authname=req.authname)

            self.log.debug("<<< WorkflowStandardOperations - get_operation_control - set_owner_to_self")
            
            return None, hint

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
                res_wf_state['owner'] = newowner.strip()
            else:
                self.log.debug("Unable to get the new owner!") 

        elif operation == 'set_owner_to_self':
            res_wf_state['owner'] = req.authname.strip()

