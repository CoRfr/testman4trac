# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi
#

import re
import time

from datetime import date, datetime

from trac.core import *
from trac.db import Table, Column, Index
from trac.env import IEnvironmentSetupParticipant
from trac.resource import Resource, ResourceNotFound
from trac.util.translation import _, N_, gettext

from tracgenericclass.model import IConcreteClassProvider, AbstractVariableFieldsObject, need_db_upgrade, upgrade_db
from tracgenericclass.util import *


class ResourceWorkflowState(AbstractVariableFieldsObject):
    """
    This object represents the current workflow state of the associated
    resource.
    """
    
    # Fields that must not be modified directly by the user
    protected_fields = ('id', 'res_realm', 'state')

    def __init__(self, env, id=None, res_realm=None, state='new', db=None):
        """
        The resource workflow state is related to a resource, the 'id' 
        and 'res_realm' arguments.
        The state can be any string.
        """
        self.values = {}

        self.values['id'] = id
        self.values['res_realm'] = res_realm
        self.values['state'] = state

        key = self.build_key_object()
    
        AbstractVariableFieldsObject.__init__(self, env, 'resourceworkflowstate', key, db)

    def get_key_prop_names(self):
        return ['id', 'res_realm']
        
    def create_instance(self, key):
        return ResourceWorkflowState(self.env, key['id'], key['res_realm'])


class GenericWorkflowModelProvider(Component):
    """
    This class provides the data model for the generic workflow plugin.
    
    The actual data model on the db is created starting from the
    SCHEMA declaration below.
    For each table, we specify whether to create also a '_custom' and
    a '_change' table.
    
    This class also provides the specification of the available fields
    for each class, being them standard fields and the custom fields
    specified in the trac.ini file.
    The custom field specification follows the same syntax as for
    Tickets.
    Currently, only 'text' type of custom fields are supported.
    """

    implements(IConcreteClassProvider, IEnvironmentSetupParticipant)

    SCHEMA = {
                'resourceworkflowstate':  
                    {'table':
                        Table('resourceworkflowstate', key = ('id', 'res_realm'))[
                              Column('id'),
                              Column('res_realm'),
                              Column('state')],
                     'has_custom': True,
                     'has_change': True}
            }

    FIELDS = {
                'resourceworkflowstate': [
                    {'name': 'id', 'type': 'text', 'label': N_('ID')},
                    {'name': 'res_realm', 'type': 'text', 'label': N_('Resource realm')},
                    {'name': 'state', 'type': 'text', 'label': N_('Workflow state')}
                ]
            }
            
    METADATA = {
                'resourceworkflowstate': {
                        'label': "Workflow State", 
                        'searchable': False,
                        'has_custom': True,
                        'has_change': True
                    },
                }

            
    # IConcreteClassProvider methods
    def get_realms(self):
            yield 'resourceworkflowstate'

    def get_data_models(self):
        return self.SCHEMA

    def get_fields(self):
        return self.FIELDS
        
    def get_metadata(self):
        return self.METADATA
        
    def create_instance(self, realm, key=None):
        obj = None
        
        if realm == 'resourceworkflowstate':
            if key is not None:
                obj = ResourceWorkflowState(self.env, key['id'], key['res_realm'])
            else:
                obj = ResourceWorkflowState(self.env)
        
        return obj

    def check_permission(self, req, realm, key_str=None, operation='set', name=None, value=None):
        pass

    # IEnvironmentSetupParticipant methods
    def environment_created(self):
        self.upgrade_environment(self.env.get_db_cnx())

    def environment_needs_upgrade(self, db):
        return self._need_initialization(db)

    def upgrade_environment(self, db):
        # Create db
        if self._need_initialization(db):
            upgrade_db(self.env, self.SCHEMA, db)

    def _need_initialization(self, db):
        return need_db_upgrade(self.env, self.SCHEMA, db)
      
