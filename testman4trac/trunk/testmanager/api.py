# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi
#

import csv
import os
import pkg_resources
import re
import shutil
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

    NEXT_PROPERTY_NAME = {
        'catalog': 'NEXT_CATALOG_ID',
        'testcase': 'NEXT_TESTCASE_ID',
        'testplan': 'NEXT_PLAN_ID'
    }

    outcomes_by_color = {}
    outcomes_by_name = {}
    default_outcome = None
    testcaseimport_target_subdir = 'testcaseimport'
    testcaseimport_target_filename = 'testcaseimport.csv'

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
        propname = NEXT_PROPERTY_NAME[type]
    
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
            self.env.log.error(formatExceptionInfo())
            db.rollback()
            raise

        return str(id)
    
    def set_next_id(self, type, value):
        propname = NEXT_PROPERTY_NAME[type]
        
        try:
            # Set next ID to the input value
            db, handle_ta = get_db_for_write(self.env)
            cursor = db.cursor()
            cursor.execute("UPDATE testconfig SET value='" + str(value) + "' WHERE propname='"+propname+"'")
           
            if handle_ta:
                db.commit()
        except:
            self.env.log.error(formatExceptionInfo())
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
        elif (req.path_info.startswith('/testdelete') and type == 'testplan' and 'TEST_PLAN_ADMIN' in req.perm):
            match = True
        elif (req.path_info.startswith('/testimport') and ('TEST_MODIFY' in req.perm)):
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
                self.env.log.error(formatExceptionInfo())
        
        elif req.path_info.startswith('/testcreate'):
            type = req.args.get('type')
            path = req.args.get('path')
            title = req.args.get('title')

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
                    self.env.log.error("Error adding test catalog!")
                    self.env.log.error(formatExceptionInfo())
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
                    self.env.log.error("Error adding test plan!")
                    self.env.log.error(formatExceptionInfo())
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
                        self.env.log.error("Error pasting test cases!")
                        self.env.log.error(formatExceptionInfo())
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
                        self.env.log.error("Error duplicating test case!")
                        self.env.log.error(formatExceptionInfo())
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
                        self.env.log.error("Error adding test case!")
                        self.env.log.error(formatExceptionInfo())
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
                    self.env.log.error("Error deleting test plan!")
                    self.env.log.error(formatExceptionInfo())
                    # Back to the catalog
                    req.redirect(req.href.wiki(path))

                # Redirect to test catalog, forcing a page refresh by means of a random request parameter
                req.redirect(req.href.wiki(path, mode=mode, fulldetails=fulldetails, random=str(datetime.now(utc).microsecond)))

        elif req.path_info.startswith('/testimport'):
            if req.method == 'POST':
                if 'import_file' in req.args:
                    if not (req.args.has_key('input_file')) or req.args['input_file'] == '':
                        raise TracError('You must specify the file name.')
                    
                    if not (req.args.has_key('column_separator')) or req.args['column_separator'] == '' or len(req.args['column_separator'].strip()) != 1:
                        raise TracError('You must specify the column separator.')

                    input_file = req.args['input_file']
                    column_separator = req.args['column_separator'].strip()
                    cat_name = req.args['cat_name']
                    
                    upload_file_to_subdir(self.env, req, self.testcaseimport_target_subdir, input_file, self.testcaseimport_target_filename)
                    csv_file = csv.reader(open(os.path.join(self.env.path, 'upload', self.testcaseimport_target_subdir, self.testcaseimport_target_filename), 'rb'), delimiter=column_separator.encode('ascii'))
        
                    testcaseimport_info = {}
                    testcaseimport_info['cat_name'] = cat_name
                    testcaseimport_info['imported_ok'] = []
                    testcaseimport_info['errors'] = []
                    
                    i = 0
                    for row in csv_file:
                        if i == 0:
                            self._process_imported_testcase_header(row, cat_name, testcaseimport_info)
                        else:
                            self._process_imported_testcase_row(i, row, cat_name, author, req.remote_addr, testcaseimport_info)

                        i += 1
                    
                    return 'testimportresults.html', testcaseimport_info, None
                    
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
    
    def _process_imported_testcase_header(self, row, cat_name, testcaseimport_info):
        if len(row) < 2:
            raise TracError('At least two columns are required.')
            
        testcaseimport_info['column_names'] = []
            
        # See if the user specified anu test case custom field
        if len(row) > 2:
            config_dirty = False

            for i, field_name in enumerate(row):
                if i < 2:
                    # The first two columns indicate title and description, regardless of the names the user gave them
                    continue
            
                field_name = '_'.join(field_name.strip().lower().split())
                testcaseimport_info['column_names'].append(field_name)

                # Write custom test case fields in the trac.ini file
                need_to_add = False
                if 'testcase-tm_custom' in self.config:
                    if field_name not in self.config['testcase-tm_custom']:
                        need_to_add = True
                else:
                    need_to_add = True

                if need_to_add:
                    self.config.set('testcase-tm_custom', field_name, 'text')
                    self.config.set('testcase-tm_custom', field_name + '.value', '')
                    config_dirty = True
                
            if config_dirty:
                self.config.save()
                # Full reload config here and in the GenericClassModelProvider to get new custom fields working
                self.config.parse_if_needed()
                gcm_provider = GenericClassModelProvider(self.env)
                gcm_provider.config.parse_if_needed()
                gcm_provider.custom_fields('testcase', True)
                gcm_provider.fields(True)
                
    def _process_imported_testcase_row(self, row_num, row, cat_name, author, remote_addr, testcaseimport_info):
        if len(row) < 2:
            testcaseimport_info['errors'].append([row_num, '', 'At least two columns are required.'])
            return

        title = row[0]
        try:
            title = title.strip()
            description = row[1].strip()

            id = self.get_next_id('testcase')

            pagename = cat_name + '_TC'+str(id)

            new_tc = TestCase(self.env, id, pagename, title, description)

            # Set custom field values into the new test case
            for i, field_value in enumerate(row):
                if i < 2:
                    # The first two columns indicate title and description
                    continue
            
                field_name = testcaseimport_info['column_names'][i-2]
                field_value = field_value.strip()
                new_tc[field_name] = field_value
            
            new_tc.author = author
            new_tc.remote_addr = remote_addr

            # Create the test case
            new_tc.insert()
            
            testcaseimport_info['imported_ok'].append(title)
            
        except:
            testcaseimport_info['errors'].append([row_num, title, formatExceptionInfo()])
            self.env.log.error("Error importing test case number %s:\n%s" % (row_num, row))
            self.env.log.error(formatExceptionInfo())

