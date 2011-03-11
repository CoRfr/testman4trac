# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi
#

import re
import pkg_resources
import sys
import time
import traceback

from datetime import datetime
from trac.core import *
from trac.perm import IPermissionRequestor, PermissionError
from trac.resource import Resource, IResourceManager, render_resource_link, get_resource_url
from trac.util import get_reporter_id
from trac.util.datefmt import utc
from trac.web.api import IRequestHandler

from tracgenericclass.model import GenericClassModelProvider
from tracgenericclass.util import *

from testmanager.model import TestCatalog, TestCase, TestCaseInPlan, TestPlan

try:
    from trac.util.translation import domain_functions
    _, tag_, N_, add_domain = domain_functions('testmanager', ('_', 'tag_', 'N_', 'add_domain'))
except ImportError:
	from trac.util.translation import _, N_
	tag_ = _
	add_domain = lambda env_path, locale_dir: None

class TestManagerSystem(Component):
    """Test Manager system for Trac."""

    implements(IPermissionRequestor, IRequestHandler, IResourceManager)

    outcomes_by_color = {}
    outcomes_by_name = {}
    default_outcome = None

    def __init__(self, *args, **kwargs):
        """
        Parses the configuration file to find all the test case states
        defined.
        
        Test case outcomes are triple:
        (color, name, label)
        
        Where color = green, yellow, red
        
        To define a set of test case outcomes (a.k.a. verdicts), specify
        each one on a different line in the trac.ini file, as in the 
        following example:
        
        [test-outcomes]
        green.SUCCESSFUL = Successful
        yellow.TO_BE_TESTED = Untested
        red.FAILED = Failed
        default = TO_BE_TESTED
        """
        Component.__init__(self, *args, **kwargs)

        import pkg_resources
        # bind the 'testmanager' catalog to the specified locale directory
        locale_dir = pkg_resources.resource_filename(__name__, 'locale')
        add_domain(self.env.path, locale_dir)

        # Search for custom test case outcomes (a.k.a. verdicts) definitions
        self.log.debug("TestManagerSystem - Looking for custom test outcomes...")
        section_name = 'test-outcomes'
        
        if section_name in self.config.sections():
            self.log.debug("TestManagerSystem - parsing config section %s" % section_name)
            tmp_outcomes = list(self.config.options(section_name))

            for row in tmp_outcomes:
                self.log.debug("  --> Found option: %s = %s" % (row[0], row[1]))

                if row[0] == 'default':
                    self.default_outcome = row[1].lower()
                else:
                    color = row[0].partition('.')[0]
                    outcome = row[0].partition('.')[2].lower()
                    caption = row[1]

                    if color not in self.outcomes_by_color:
                        self.outcomes_by_color[color] = {}
                        
                    self.outcomes_by_color[color][outcome] = caption
        else:
            raise TracError("Configuration section 'test-outcomes' missing in trac.ini file.")

        # Build a reverse map to easily lookup an outcome's color and label
        for color in self.outcomes_by_color:
            for outcome in self.outcomes_by_color[color]:
                self.outcomes_by_name[outcome] = [color, self.outcomes_by_color[color][outcome]]

    def get_next_id(self, type):
        propname = _get_next_prop_name(type)
    
        try:
            # Get next ID
            db, handle_ta = get_db_for_write(self.env)
            cursor = db.cursor()
            sql = "SELECT value FROM testconfig WHERE propname='"+propname+"'"
            
            cursor.execute(sql)
            row = cursor.fetchone()
            
            id = int(row[0])

            # Increment next ID
            cursor = db.cursor()
            cursor.execute("UPDATE testconfig SET value='" + str(id+1) + "' WHERE propname='"+propname+"'")
            
            if handle_ta:
                db.commit()
        except:
            self.env.log.debug(formatExceptionInfo())
            db.rollback()
            raise

        return str(id)
    
    def set_next_id(self, type, value):
        propname = _get_next_prop_name(type)
        
        try:
            # Set next ID to the input value
            db, handle_ta = get_db_for_write(self.env)
            cursor = db.cursor()
            cursor.execute("UPDATE testconfig SET value='" + str(value) + "' WHERE propname='"+propname+"'")
           
            if handle_ta:
                db.commit()
        except:
            self.env.log.debug(formatExceptionInfo())
            db.rollback()
            raise
    
    def get_default_tc_status(self):
        """Returns the default test case in plan status"""
        
        return self.default_outcome
    
    def get_tc_statuses_by_name(self):
        """
        Returns the available test case in plan statuses, along with
        their captions and meaning:
          'green': successful
          'yellow': to be tested
          'red': failed
          
        For example:
            {'SUCCESSFUL': ['green', "Successful"], 
             'TO_BE_TESTED': ['yellow', "Untested"], 
             'FAILED': ['red', "Failed"]}
        """
        return self.outcomes_by_name
        
    def get_tc_statuses_by_color(self):
        """
        Returns the available test case in plan statuses, along with
        their captions and meaning:
          'green': successful
          'yellow': to be tested
          'red': failed
          
        For example:
            {'green': {'SUCCESSFUL': "Successful"}, 
             'yellow': {'TO_BE_TESTED': "Untested"}, 
             'red': {'FAILED': "Failed"}}
        """
        return self.outcomes_by_color
        
    def get_testcase_status_history_markup(self, id, planid):
        """Returns a test case status in a plan audit trail."""

        result = '<table class="listing"><thead>'
        result += '<tr><th>'+_("Timestamp")+'</th><th>'+_("Author")+'</th><th>'+_("Status")+'</th></tr>'
        result += '</thead><tbody>'
        
        db = get_db(self.env)
        cursor = db.cursor()

        sql = "SELECT time, author, status FROM testcasehistory WHERE id='"+str(id)+"' AND planid='"+str(planid)+"' ORDER BY time DESC"
        
        cursor.execute(sql)
        for ts, author, status in cursor:
            result += '<tr>'
            result += '<td>'+str(from_any_timestamp(ts))+'</td>'
            result += '<td>'+author+'</td>'
            result += '<td>'+_("Status")+'</td>'
            result += '</tr>'

        result += '</tbody></table>'
         
        return result
        
        
    # @deprecated
    def list_all_testplans(self):
        """Returns a list of all test plans."""

        db = get_db(self.env)
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
        type = req.args.get('type', '')
        
        match = False
        
        if req.path_info.startswith('/testman4debug'):
            match = True
        
        if req.path_info.startswith('/testcreate') and (((type == 'catalog' or type == 'testcase') and ('TEST_MODIFY' in req.perm)) or 
             (type == 'testplan' and ('TEST_PLAN_ADMIN' in req.perm))):
            match = True
        elif (req.path_info.startswith('/teststatusupdate') and 'TEST_EXECUTE' in req.perm):
            match = True
        elif (req.path_info.startswith('/testdelete') and (type == 'testplan' and ('TEST_PLAN_ADMIN' in req.perm))):
            match = True
        
        return match

    def process_request(self, req):
        """
        Handles Ajax requests to set the test case status and 
        to create test objects.
        """
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
                    tcip.set_status(status, author)
                    tcip.insert()
                
            except:
                self.env.log.debug(formatExceptionInfo())
        
        elif req.path_info.startswith('/testcreate'):
            type = req.args.get('type')
            path = req.args.get('path')
            title = req.args.get('title')
            author = get_reporter_id(req, 'author')

            autosave = req.args.get('autosave', 'false')
            duplicate = req.args.get('duplicate')
            multiple = req.args.get('multiple')
            paste = req.args.get('paste')
            tcId = req.args.get('tcId')

            id = self.get_next_id(type)

            pagename = path
            
            if type == 'catalog':
                req.perm.require('TEST_MODIFY')
                pagename += '_TT'+str(id)

                try:
                    new_tc = TestCatalog(self.env, id, pagename, title, '')
                    new_tc.author = author
                    new_tc.remote_addr = req.remote_addr
                    # This also creates the Wiki page
                    new_tc.insert()
                    
                except:
                    self.env.log.info("Error adding test catalog!")
                    self.env.log.info(formatExceptionInfo())
                    req.redirect(req.href.wiki(path))

                # Redirect to see the new wiki page.
                req.redirect(req.href.wiki(pagename))
                
            elif type == 'testplan':
                req.perm.require('TEST_PLAN_ADMIN')
                
                catid = path.rpartition('_TT')[2]

                try:
                    # Add the new test plan in the database
                    new_tc = TestPlan(self.env, id, catid, pagename, title, author)
                    new_tc.insert()

                except:
                    self.env.log.info("Error adding test plan!")
                    self.env.log.info(formatExceptionInfo())
                    # Back to the catalog
                    req.redirect(req.href.wiki(path))

                # Display the new test plan
                req.redirect(req.href.wiki(path, planid=str(id)))
                    
            elif type == 'testcase':
                req.perm.require('TEST_MODIFY')
                
                pagename += '_TC'+str(id)
                
                if paste and paste != '':
                    # Handle move/paste of the test case into another catalog

                    req.perm.require('TEST_PLAN_ADMIN')

                    if multiple and multiple != '':
                        delete_old = False
                        tcIdsList = tcId.split(',')
                    else:
                        delete_old = True
                        tcIdsList = [tcId]
                    
                    try:
                        catid = path.rpartition('_TT')[2]
                        tcat = TestCatalog(self.env, catid)
                        
                        for tcId in tcIdsList:
                            if tcId is not None and tcId != '':
                                old_pagename = tcId
                                tc_id = tcId.rpartition('_TC')[2]

                                tc = TestCase(self.env, tc_id, tcId)
                                tc.author = author
                                tc.remote_addr = req.remote_addr
                                if tc.exists:
                                    if delete_old:
                                        tc.move_to(tcat)                            
                                    else:
                                        tc['page_name'] = pagename
                                        tc.save_as({'id': id})
                                else:
                                    self.env.log.debug("Test case not found")

                            # Generate a new Id for the next iteration
                            id = self.get_next_id(type)
                            pagename = path + '_TC'+str(id)
                                    
                    except:
                        self.env.log.info("Error pasting test cases!")
                        self.env.log.info(formatExceptionInfo())
                        req.redirect(req.href.wiki(pagename))
                
                    # Redirect to test catalog, forcing a page refresh by means of a random request parameter
                    req.redirect(req.href.wiki(pagename.rpartition('_TC')[0], random=str(datetime.now(utc).microsecond)))
                    
                elif duplicate and duplicate != '':
                    # Duplicate test case
                    old_id = tcId.rpartition('_TC')[2]
                    old_pagename = tcId
                    try:
                        old_tc = TestCase(self.env, old_id, old_pagename)
                        
                        # New test case name will be the old catalog name + the newly generated test case ID
                        author = get_reporter_id(req, 'author')
                        
                        # Create new test case wiki page as a copy of the old one, but change its page path
                        new_tc = old_tc
                        new_tc['page_name'] = pagename
                        new_tc.remote_addr = req.remote_addr
                        # And save it under the new id
                        new_tc.save_as({'id': id})
                        
                    except:
                        self.env.log.info("Error duplicating test case!")
                        self.env.log.info(formatExceptionInfo())
                        req.redirect(req.href.wiki(tcId))

                    # Redirect tp allow for editing the copy test case
                    req.redirect(req.href.wiki(pagename, action='edit'))
                    
                else:
                    # Normal creation of a new test case
                    try:
                        new_tc = TestCase(self.env, id, pagename, title, '')
                        new_tc.author = author
                        new_tc.remote_addr = req.remote_addr
                        # This also creates the Wiki page
                        new_tc.insert()
                        
                    except:
                        self.env.log.info("Error adding test case!")
                        self.env.log.info(formatExceptionInfo())
                        req.redirect(req.path_info)

                    # Redirect to edit the test case description
                    req.redirect(req.href.wiki(pagename, action='edit'))

        elif req.path_info.startswith('/testdelete'):
            type = req.args.get('type')
            path = req.args.get('path')
            author = get_reporter_id(req, 'author')
            mode = req.args.get('mode', 'tree')
            fulldetails = req.args.get('fulldetails', 'False')

            if type == 'testplan':
                req.perm.require('TEST_PLAN_ADMIN')
                
                planid = req.args.get('planid')
                catid = path.rpartition('_TT')[2]

                self.env.log.debug("About to delete test plan %s on catalog %s" % (planid, catid))

                try:
                    # Add the new test plan in the database
                    tp = TestPlan(self.env, planid, catid)
                    tp.delete()

                except:
                    self.env.log.info("Error deleting test plan!")
                    self.env.log.info(formatExceptionInfo())
                    # Back to the catalog
                    req.redirect(req.href.wiki(path))

                # Redirect to test catalog, forcing a page refresh by means of a random request parameter
                req.redirect(req.href.wiki(path, mode=mode, fulldetails=fulldetails, random=str(datetime.now(utc).microsecond)))

        elif req.path_info.startswith('/testman4debug'):
            id = req.args.get('id')
            path = req.args.get('path')
            planid = req.args.get('planid')
            
            result = ''
            
            if planid is None or len(planid) == 0:
                tc = TestCase(self.env, id, path)
                for t in tc.get_related_tickets():
                    result += str(t) + ', '
            else:
                tc = TestCaseInPlan(self.env, id, planid, path)
                for t in tc.get_related_tickets():
                    result += str(t) + ', '
            
            req.send_header("Content-Length", len(result))
            req.write(result)
            return 
        
        return 'empty.html', {}, None


    # IResourceManager methods
    
    def get_resource_realms(self):
        yield 'testcatalog'
        yield 'testcase'
        yield 'testcaseinplan'
        yield 'testplan'

    def get_resource_url(self, resource, href, **kwargs):
        self.env.log.debug(">>> get_resource_url - %s" % resource)
        
        tmmodelprovider = GenericClassModelProvider(self.env)
        obj = tmmodelprovider.get_object(resource.realm, get_dictionary_from_string(resource.id))
        
        if obj and obj.exists:
            args = {}
            
            if resource.realm == 'testcaseinplan':
                args = {'planid': obj['planid']}
            elif resource.realm == 'testplan':
                args = {'planid': obj['id']}

            args.update(kwargs)
                 
            self.env.log.debug("<<< get_resource_url - exists")

            return href('wiki', obj['page_name'], **args)
        else:
            self.env.log.debug("<<< get_resource_url - does NOT exist")
            return href('wiki', 'TC', **kwargs)

    def get_resource_description(self, resource, format='default', context=None,
                                 **kwargs):
        return resource.id

    def resource_exists(self, resource):
        tmmodelprovider = GenericClassModelProvider(self.env)
        obj = tmmodelprovider.get_object(resource.realm, get_dictionary_from_string(resource.id))
        
        return obj.exists

        
def _get_next_prop_name(type):
    propname = ''

    if type == 'catalog':
        propname = 'NEXT_CATALOG_ID'
    elif type == 'testcase':
        propname = 'NEXT_TESTCASE_ID'
    elif type == 'testplan':
        propname = 'NEXT_PLAN_ID'

    return propname
        
