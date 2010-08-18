# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi, Marco Cipriani
#

import re
import time
import sys
import traceback

from datetime import datetime
from trac.core import *
from trac.perm import IPermissionRequestor, PermissionError
from trac.util import get_reporter_id
from trac.util.datefmt import utc, to_timestamp
from trac.web.api import IRequestHandler

from testmanager.util import formatExceptionInfo
from testmanager.labels import *


# Public methods

class TestManagerSystem(Component):
    """Test Manager system for Trac."""

    implements(IPermissionRequestor, IRequestHandler)

    # Public methods
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
            print self._formatExceptionInfo()
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
            print self._formatExceptionInfo()
            db.rollback()
            raise
    
    def add_testcase(self, id, planid, is_update=False, author="System", status='TO_BE_TESTED'):
        """Add a test case to a test plan."""

        db = self.env.get_db_cnx()

        existing = False
        if is_update:
            cursor = db.cursor()
            sql = "SELECT status FROM testcases WHERE id='"+str(id)+"' AND planid='"+str(planid)+"'"
            cursor.execute(sql)
            row = cursor.fetchone()
            
            if row:
                existing = True

        if not is_update or not existing:
            try:
                cursor = db.cursor()
                sql = "INSERT INTO testcases (id, planid, status) VALUES ('"+str(id)+"', '"+str(planid)+"', '"+status+"')"
                cursor.execute(sql)

                cursor = db.cursor()
                sql = 'INSERT INTO testcasehistory (id, planid, time, author, status) VALUES (%s, %s, '+str(to_timestamp(datetime.now(utc)))+', %s, %s)'
                cursor.execute(sql, (str(id), str(planid), author, status))

                db.commit()
                
            except:
                print self._formatExceptionInfo()
                db.rollback()
                raise

    def delete_testcase(self, id):
        """Delete a test case from all test plans."""

        try:
            db = self.env.get_db_cnx()
            cursor = db.cursor()

            sql = "DELETE FROM testcases WHERE id='"+str(id)+"'"
            
            cursor.execute(sql)
            db.commit()

            cursor = db.cursor()

            sql = "DELETE FROM testcasehistory WHERE id='"+str(id)+"'"
            
            cursor.execute(sql)
            db.commit()
        except:
            print self._formatExceptionInfo()
            db.rollback()
            raise

    def get_testcase_status(self, id, planid):
        """Returns a test case status in a test plan."""

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        sql = "SELECT status FROM testcases WHERE id='"+str(id)+"' AND planid='"+str(planid)+"'"
        
        cursor.execute(sql)
        row = cursor.fetchone()
        
        status = 'TO_BE_TESTED'
        if row:
            status = row[0]
        
        return status

    def set_testcase_status(self, id, planid, status, author="Unknown"):
        """Set a test case status in a test plan."""

        try:
            db = self.env.get_db_cnx()

            cursor = db.cursor()
            sql = "SELECT status FROM testcases WHERE id='"+str(id)+"' AND planid='"+str(planid)+"'"
            cursor.execute(sql)
            row = cursor.fetchone()
            
            if row:
                cursor = db.cursor()
                sql = 'UPDATE testcases SET status=%s WHERE id=%s AND planid=%s'
                cursor.execute(sql, (status, str(id), str(planid)))
            else:
                cursor = db.cursor()
                sql = "INSERT INTO testcases (id, planid, status) VALUES ('"+str(id)+"', '"+str(planid)+"', '"+status+"')"
                cursor.execute(sql)

            cursor = db.cursor()
            sql = 'INSERT INTO testcasehistory (id, planid, time, author, status) VALUES (%s, %s, '+str(to_timestamp(datetime.now(utc)))+', %s, %s)'
            cursor.execute(sql, (str(id), str(planid), author, status))
            
            db.commit()

        except:
            print self._formatExceptionInfo()
            db.rollback()
            
            raise

    def report_testcase_status(self):
        """Prints a list of all test cases with their status."""

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        sql = "SELECT id, planid, status FROM testcases"
        
        cursor.execute(sql)

        print "-- BEGIN Test Cases --"
        
        print "id,plan id,status"
        for id, planid, status in cursor:
            print id+","+planid+","+status

        print "-- END Test Cases --"

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
            result += '<td>'+str(datetime.fromtimestamp(ts, utc))+'</td>'
            result += '<td>'+author+'</td>'
            result += '<td>'+LABELS[status]+'</td>'
            result += '</tr>'

        result += '</tbody></table>'
         
        return result

    def move_testcase(self, old_id, new_id):
        """Moves all records related to the status of the old test case in all its plans (including history) to the new test case"""
        
        try:
            db = self.env.get_db_cnx()
            
            cursor = db.cursor()
            sql = "UPDATE testcases SET id='"+str(new_id)+"' WHERE id='"+str(old_id)+"'"
            cursor.execute(sql)
                
            cursor = db.cursor()
            sql = "UPDATE testcasehistory SET id='"+str(new_id)+"' WHERE id='"+str(old_id)+"'"
            cursor.execute(sql)

            db.commit()
            
        except:
            print self._formatExceptionInfo()
            db.rollback()
            raise
        
        
    def add_testplan(self, planid, catid, catpath, name, author="System"):
        """Add a test plan."""
        
        try:
            db = self.env.get_db_cnx()
            cursor = db.cursor()
            sql = "INSERT INTO testplans (planid, catid, catpath, name, author, time) VALUES ('"+str(planid)+"', '"+str(catid)+"', '"+catpath+"', '"+name+"', '"+author+"', "+str(to_timestamp(datetime.now(utc)))+")"
            cursor.execute(sql)

            db.commit()
            
        except:
            print self._formatExceptionInfo()
            db.rollback()
            raise

    def get_testplan(self, planid):
        """Returns the specified test plan."""

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        sql = "SELECT planid, catid, catpath, name, author, time FROM testplans WHERE planid='"+str(planid)+"'"
        
        cursor.execute(sql)
        for planid, catid, catpath, name, author, ts in cursor:
            return planid, catid, catpath, name, author, str(datetime.fromtimestamp(ts, utc))

    def list_all_testplans(self):
        """Returns a list of all test plans."""

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        sql = "SELECT planid, catid, catpath, name, author, time FROM testplans ORDER BY catid, planid"
        
        cursor.execute(sql)
        for planid, catid, catpath, name, author, ts  in cursor:
            yield planid, catid, catpath, name, author, str(datetime.fromtimestamp(ts, utc))

    def list_testplans_for_catalog(self, catid):
        """Returns a list of test plans for the specified catalog."""

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        sql = "SELECT planid, catid, catpath, name, author, time FROM testplans WHERE catid='"+str(catid)+"' ORDER BY planid DESC"
        
        cursor.execute(sql)
        for planid, catid, catpath, name, author, ts in cursor:
            yield planid, catid, catpath, name, author, str(datetime.fromtimestamp(ts, utc))

    def list_testplans_for_testcase(self, id):
        """Returns a list of test plans for the specified test case."""

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        sql = "SELECT planid, catid, catpath, name, author, time, status FROM testplans, testcases WHERE testplans.planid=testcases.planid AND testcases.id='"+str(id)+"' ORDER BY name"
        
        cursor.execute(sql)
        for planid, catid, catpath, name, author, ts, status in cursor:
            yield planid, catid, catpath, name, author, str(datetime.fromtimestamp(ts, utc)), status

    def delete_testplan(self, planid):
        """Delete a test plan."""

        try:
            db = self.env.get_db_cnx()
            cursor = db.cursor()

            sql = "DELETE FROM testplans WHERE planid='"+str(planid)+"'"
            
            cursor.execute(sql)
            db.commit()

            cursor = db.cursor()

            sql = "DELETE FROM testcases WHERE planid='"+str(planid)+"'"
            
            cursor.execute(sql)
            db.commit()

            cursor = db.cursor()

            sql = "DELETE FROM testcasehistory WHERE planid='"+str(planid)+"'"
            
            cursor.execute(sql)
            db.commit()
        except:
            print self._formatExceptionInfo()
            db.rollback()
            raise

            
    def get_testplan_list_markup(self, catid):
        """Returns a test case status in a plan audit trail."""

        result = '<table class="listing"><thead>'
        result += '<tr><th>'+LABELS['plan_name']+'</th><th>'+LABELS['author']+'</th><th>'+LABELS['timestamp']+'</th></tr>'
        result += '</thead><tbody>'
        
        num_plans = 0
        for planid, catid, catpath, name, author, timestr in self.list_testplans_for_catalog(catid):
            result += '<tr>'
            result += '<td><a title="'+LABELS['open_testplan_title']+'" href="'+catpath+'?planid='+str(planid)+'">'+name+'</a></td>'
            result += '<td>'+author+'</td>'
            result += '<td>'+timestr+'</td>'
            result += '</tr>'
            num_plans += 1

        result += '</tbody></table>'
         
        return result, num_plans

            
    # IPermissionRequestor methods
    def get_permission_actions(self):
        return ['TEST_VIEW', 'TEST_MODIFY', 'TEST_EXECUTE', 'TEST_DELETE', 'TEST_PLAN_ADMIN']

        
    # IRequestHandler methods

    def match_request(self, req):
        return req.path_info.startswith('/teststatusupdate') and 'TEST_EXECUTE' in req.perm

    def process_request(self, req):
        """Handles Ajax requests to set the test case status."""

        req.perm.require('TEST_EXECUTE')
        
        # Print the status of all test cases
        #self.report_testcase_status()
    
        id = req.args.get('id')
        planid = req.args.get('planid')
        status = req.args.get('status')
        author = get_reporter_id(req, 'author')

        self.set_testcase_status(id, planid, status, author)
        
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
        
