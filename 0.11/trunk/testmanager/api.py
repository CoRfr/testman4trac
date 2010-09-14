# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi, Marco Cipriani
#

import re
import sys
import time
import traceback

from datetime import datetime
from trac.core import *
from trac.perm import IPermissionRequestor, PermissionError
from trac.util import get_reporter_id
from trac.util.datefmt import utc
from trac.util.translation import _, N_, gettext
from trac.web.api import IRequestHandler

from testmanager.util import *
from testmanager.labels import *
from testmanager.model import TestCatalog, TestCase, TestCaseInPlan, TestPlan, TestManagerModelProvider


class ITestObjectChangeListener(Interface):
    """Extension point interface for components that require notification
    when test objects, e.g. test cases, catalogs, plans etc, are created, 
    modified, or deleted."""

    def object_created(testobject):
        """Called when a test object is created."""

    def object_changed(testobject, comment, author, old_values):
        """Called when a test object is modified.
        
        `old_values` is a dictionary containing the previous values of the
        fields that have changed.
        """

    def object_deleted(testobject):
        """Called when a test object is deleted."""


class TestManagerSystem(Component):
    """Test Manager system for Trac."""

    implements(IPermissionRequestor, IRequestHandler)

    change_listeners = ExtensionPoint(ITestObjectChangeListener)

    def get_next_id(self, type):
        propname = _get_next_prop_name(type)
    
        try:
            # Get next ID
            db = self.env.get_db_cnx()
            cursor = db.cursor()
            sql = "SELECT value FROM testconfig WHERE propname='"+propname+"'"
            
            cursor.execute(sql)
            row = cursor.fetchone()
            
            id = int(row[0])

            # Increment next ID
            cursor = db.cursor()
            cursor.execute("UPDATE testconfig SET value='" + str(id+1) + "' WHERE propname='"+propname+"'")
            
            db.commit()
        except:
            self.env.log.debug(self._formatExceptionInfo())
            db.rollback()
            raise

        return id
    
    def set_next_id(self, type, value):
        propname = _get_next_prop_name(type)
        
        try:
            # Set next ID to the input value
            db = self.env.get_db_cnx()
            cursor = db.cursor()
            cursor.execute("UPDATE testconfig SET value='" + str(value) + "' WHERE propname='"+propname+"'")
           
            db.commit()
        except:
            self.env.log.debug(self._formatExceptionInfo())
            db.rollback()
            raise
    
    def get_testcase_status_history_markup(self, id, planid):
        """Returns a test case status in a plan audit trail."""

        result = '<table class="listing"><thead>'
        result += '<tr><th>'+LABELS['timestamp']+'</th><th>'+LABELS['author']+'</th><th>'+LABELS['status']+'</th></tr>'
        result += '</thead><tbody>'
        
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        sql = "SELECT time, author, status FROM testcasehistory WHERE id='"+str(id)+"' AND planid='"+str(planid)+"' ORDER BY time DESC"
        
        cursor.execute(sql)
        for ts, author, status in cursor:
            result += '<tr>'
            result += '<td>'+str(from_any_timestamp(ts))+'</td>'
            result += '<td>'+author+'</td>'
            result += '<td>'+LABELS[status]+'</td>'
            result += '</tr>'

        result += '</tbody></table>'
         
        return result

    # @deprecated
    def list_all_testplans(self):
        """Returns a list of all test plans."""

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        sql = "SELECT id, catid, page_name, name, author, time FROM testplan ORDER BY catid, id"
        
        cursor.execute(sql)
        for id, catid, page_name, name, author, ts  in cursor:
            yield id, catid, page_name, name, author, str(from_any_timestamp(ts))


    # IPermissionRequestor methods
    def get_permission_actions(self):
        return ['TEST_VIEW', 'TEST_MODIFY', 'TEST_EXECUTE', 'TEST_DELETE', 'TEST_PLAN_ADMIN']

        
    # IRequestHandler methods

    def match_request(self, req):
        return (req.path_info.startswith('/teststatusupdate') and 'TEST_EXECUTE' in req.perm) or (req.path_info.startswith('/testpropertyupdate') and 'TEST_MODIFY' in req.perm)

    def process_request(self, req):
        """Handles Ajax requests to set the test case status."""

        author = get_reporter_id(req, 'author')

        if req.path_info.startswith('/teststatusupdate'):
            req.perm.require('TEST_EXECUTE')
        
            id = req.args.get('id')
            planid = req.args.get('planid')
            path = req.args.get('path')
            status = req.args.get('status')

            try:
                self.env.log.debug("Setting status %s to test case %s in plan %s" % (status, id, planid))
                tcip = TestCaseInPlan(self.env, id, planid)
                if tcip.exists:
                    tcip.set_status(status, author)
                    tcip.save_changes(author, "Status changed")
                else:
                    tcip['page_name'] = path
                    tcip['status'] = status
                    tcip.insert()
            except:
                self.env.log.debug(self._formatExceptionInfo())
        
        elif req.path_info.startswith('/testpropertyupdate'):
            req.perm.require('TEST_MODIFY')

            realm = req.args.get('realm')
            key_str = req.args.get('key')
            name = req.args.get('name')
            value = req.args.get('value')

            key = get_dictionary_from_string(key_str)

            try:
                self.env.log.debug("Setting property %s to %s, in %s with key %s" % (name, value, realm, key))
                
                tmmodelprovider = TestManagerModelProvider(self.env)
                obj = tmmodelprovider.get_object(realm, key)
                
                obj[name] = value
                obj.author = author
                obj.remote_addr = req.remote_addr
                if obj is not None and obj.exists:
                    obj.save_changes(author, "Custom property changed")
                else:
                    self.env.log.debug("Object to update not found. Creating it.")
                    props_str = req.args.get('props')
                    if props_str is not None and not props_str == '':
                        props = get_dictionary_from_string(props_str)
                        obj.set_values(props)
                    obj.insert()
            except:
                self.env.log.debug(self._formatExceptionInfo())

        
        return 'empty.html', {}, None

        
    # Internal methods
        
    def _formatExceptionInfo(maxTBlevel=5):
        cla, exc, trbk = sys.exc_info()
        excName = cla.__name__
        
        try:
            excArgs = exc.__dict__["args"]
        except KeyError:
            excArgs = "<no args>"
        
        excTb = traceback.format_tb(trbk, maxTBlevel)
        return (excName, excArgs, excTb)

def _get_next_prop_name(type):
    propname = ''

    if type == 'catalog':
        propname = 'NEXT_CATALOG_ID'
    elif type == 'testcase':
        propname = 'NEXT_TESTCASE_ID'
    elif type == 'testplan':
        propname = 'NEXT_PLAN_ID'

    return propname
        
