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

import csv
import os
import pkg_resources
import re
import shutil
import sys
import time
import traceback

from datetime import datetime
from operator import itemgetter
from StringIO import StringIO

from trac.core import *
from trac.mimeview.api import Context
from trac.perm import IPermissionRequestor, PermissionError
from trac.resource import Resource, IResourceManager, render_resource_link, get_resource_url
from trac.util import get_reporter_id, format_datetime, format_date
from trac.util.datefmt import utc
from trac.web.api import IRequestHandler
from trac.web.chrome import add_notice, add_warning, add_stylesheet
from trac.wiki.formatter import Formatter, format_to_html
from trac.wiki.model import WikiPage
from trac.wiki.parser import WikiParser

from tracgenericclass.model import GenericClassModelProvider
from tracgenericclass.util import *

from testmanager.model import TestCatalog, TestCase, TestCaseInPlan, TestPlan
from testmanager.util import *

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
    
    TEMPLATE_TYPE_TESTCASE = 'TC'
    TEMPLATE_TYPE_TESTCATALOG = 'TCAT'
    DOUBLE_QUOTES = re.compile("\"")

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
        propname = self.NEXT_PROPERTY_NAME[type]
    
        # Get current latest ID for the desired object type
        latest_id = self.get_config_property(propname)
        if not latest_id:
            latest_id = '0'

        # Increment next ID
        self.set_config_property(propname, str(int(latest_id)+1))

        return latest_id
    
    def set_next_id(self, type_, value):
        propname = self.NEXT_PROPERTY_NAME[type_]
        self.set_config_property(type_, value)

    def get_config_property(self, propname):
        try:
            db = get_db(self.env)
            cursor = db.cursor()
            sql = "SELECT value FROM testconfig WHERE propname=%s"
            
            cursor.execute(sql, (propname,))
            row = cursor.fetchone()
            
            if not row or len(row) == 0:
                return None
                
            return row[0]
            
        except:
            self.env.log.error("Error getting configuration property '%s'" % propname)
            self.env.log.error(formatExceptionInfo())
            
            return None
    
    def set_config_property(self, propname, value):
        db, handle_ta = get_db_for_write(self.env)
        try:
            cursor = db.cursor()
            sql = "SELECT COUNT(*) FROM testconfig WHERE propname = %s"
            cursor.execute(sql, (propname,))
            row = cursor.fetchone()
            if row is not None and int(row[0]) > 0:
                cursor.execute("""
                               UPDATE testconfig
                                   SET value = %s
                                   WHERE propname = %s 
                               """, (str(value), propname))
            else:
                cursor.execute("""
                               INSERT INTO testconfig (propname,value)
                                   VALUES (%s,%s)
                               """, (propname, str(value)))
            if handle_ta:
                db.commit()
 
            return True
 
        except:
            self.env.log.error("Error setting configuration property '%s' to '%s'" % (propname, str(value)))
            self.env.log.error(formatExceptionInfo())
            db.rollback()

        return False
    
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
        elif (req.path_info.startswith('/testexport') and ('TEST_VIEW' in req.perm)):
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
                    tc = TestCase(self.env, id)
                    tcip['page_name'] = tc['page_name']
                    tcip.set_status(status, author)
                    tcip.insert()
                
            except:
                self.env.log.error(formatExceptionInfo())
        
        elif req.path_info.startswith('/testcreate'):
            object_type = req.args.get('type')
            path = req.args.get('path')
            title = req.args.get('title')

            autosave = req.args.get('autosave', 'false')
            duplicate = req.args.get('duplicate')
            multiple = req.args.get('multiple')
            paste = req.args.get('paste')
            tcId = req.args.get('tcId')

            id = self.get_next_id(object_type)

            pagename = path
            
            if object_type == 'catalog':
                req.perm.require('TEST_MODIFY')
                pagename += '_TT'+str(id)

                try:
                    # Add template if exists...
                    new_content = self.get_default_tcat_template()
                    new_tc = TestCatalog(self.env, id, pagename, title, new_content)
                    new_tc.author = author
                    new_tc.remote_addr = req.remote_addr
                    # This also creates the Wiki page
                    new_tc.insert()
                    
                except:
                    self.env.log.error("Error adding test catalog!")
                    self.env.log.error(formatExceptionInfo())
                    add_notice(req, _("Error adding test catalog"))
                    req.redirect(req.href.wiki(path))

                # Redirect to see the new wiki page.
                req.redirect(req.href.wiki(pagename))
                
            elif object_type == 'testplan':
                req.perm.require('TEST_PLAN_ADMIN')

                contains_all_str = req.args.get('containsAll', 'true')
                snapshot_str = req.args.get('snapshot', 'false')
                selected_tcs_str = req.args.get('selectedTCs', '')

                contains_all = (0, 1)[contains_all_str == 'true']
                snapshot = (0, 1)[snapshot_str == 'true']
                selected_tcs = []
                if contains_all_str == 'false' and not selected_tcs_str == '':
                    selected_tcs = selected_tcs_str.split(',')

                catid = path.rpartition('_TT')[2]

                try:
                    # Add the new test plan in the database
                    new_tc = TestPlan(self.env, id, catid, pagename, title, author, contains_all, snapshot, selected_tcs)
                    new_tc.insert()

                except:
                    self.env.log.error("Error adding test plan!")
                    self.env.log.error(formatExceptionInfo())
                    # Back to the catalog
                    req.redirect(req.href.wiki(path))

                # Display the new test plan
                req.redirect(req.href.wiki(path, planid=str(id)))
                    
            elif object_type == 'testcase':
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
                            id = self.get_next_id(object_type)
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
                        # Add template if it exists
                        new_content = self.get_tc_template(path)
                        new_tc = TestCase(self.env, id, pagename, title, new_content)
                        new_tc.author = author
                        new_tc.remote_addr = req.remote_addr
                        # This also creates the Wiki page
                        new_tc.insert()
                        
                    except:
                        self.env.log.error("Error adding test case!")
                        self.env.log.error(formatExceptionInfo())
                        add_notice(req, _("Error adding test case"))
                        req.redirect(req.path_info)

                    # Redirect to edit the test case description
                    req.redirect(req.href.wiki(pagename, action='edit'))

        elif req.path_info.startswith('/testdelete'):
            object_type = req.args.get('type')
            path = req.args.get('path')
            author = get_reporter_id(req, 'author')
            mode = req.args.get('mode', 'tree')
            fulldetails = req.args.get('fulldetails', 'False')

            if object_type == 'testplan':
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
                    
        elif req.path_info.startswith('/testexport'):
            object_type = req.args.get('type')
            cat_name = req.args.get('cat_name')
            planid = req.args.get('planid', '-1')
            separator = req.args.get('separator', ',')
            fulldetails_str = req.args.get('fulldetails', '')
            raw_wiki_format_str = req.args.get('raw_wiki_format', '')
            
            catid = cat_name.rpartition('_TT')[2]
            fulldetails = (fulldetails_str == 'on')
            raw_wiki_format = (raw_wiki_format_str == 'on')

            context = Context.from_request(req, WikiPage('TC').resource)

            data_model = self.get_test_catalog_data_model(cat_name, (planid != '-1'), planid)
            csvstr = self.get_catalog_model_csv_markup(context, planid, data_model, catid, separator, (planid != '-1'), fulldetails, raw_wiki_format)
            
            if isinstance(csvstr, unicode): 
                csvstr = csvstr.encode('utf-8') 

            req.send_header("Content-Length", len(csvstr))
            req.send_header("Content-Disposition", "attachment;filename=Test_catalogs.csv")
            req.write(csvstr)
            return

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
                
                
    # Test case import management
                
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


    # Template management

    def get_default_tcat_template_id(self):
        """ get default TestCatalog template id """
        try:
            return self.get_config_property('TEST_CATALOG_DEFAULT_TEMPLATE')

        except:
            self.env.log.error("Error getting default test catalog template id")
            self.env.log.error(formatExceptionInfo())
            return None

    def get_default_tcat_template(self):
        """ get default TestCatalog template """
        try:
            # first get template id from testconfig
            t_id = self.get_config_property('TEST_CATALOG_DEFAULT_TEMPLATE')
            if not t_id:
                return ''

            # now get template
            result = self.get_template_by_id(t_id)
            if not result:
                return ''
                
            return result['content']

        except:
            self.env.log.error("Error getting default test catalog template")
            self.env.log.error(formatExceptionInfo())
            return None

    def get_tc_template_id_for_catalog(self, t_cat_id):
        """ get test case template for catalog with specified id """
        try:
            return self.get_config_property('TC_TEMPLATE_FOR_TCAT_' + t_cat_id)

        except:
            self.env.log.error("Error getting default test catalog template id")
            self.env.log.error(formatExceptionInfo())
            return None

    def get_tc_template(self, t_cat_page):
        """ get TestCase template for TestCatalog """
        db = get_db(self.env)
        cursor = db.cursor()

        try:
            # first get TestCatalog ID
            t_cat_id = t_cat_page.rpartition('TT')[2]

            # now get Template ID
            t_id = self.get_tc_template_id_for_catalog(t_cat_id)
            if not t_id:
                return ''

            # and finally get the template
            result = self.get_template_by_id(t_id)
            if not result:
                return ''
                
            return result['content']

        except:
            self.env.log.error("Error getting test case template for catalog %s" % t_cat_page)
            self.env.log.error(formatExceptionInfo())
            return None

    def get_template_by_id(self, t_id):
        """ Returns a template text by its id """
        db = get_db(self.env)
        cursor = db.cursor()

        try:
            sql = "SELECT id, name, type, description, content FROM testmanager_templates WHERE id = %s"
            cursor.execute(sql, (t_id,))
            result = None
            for id_, name, type_, description, content in cursor:
                result = { 'id': id_, 'name': name, 'type': type_, 'description': description, 'content': content }
                self.env.log.debug(result)
            return result

        except:
            self.env.log.error("Error getting template with id %s" % t_id)
            self.env.log.error(formatExceptionInfo())
            return None

    def get_template_by_name(self, t_name, t_type):
        """ Get a single template by name and type """
        db = get_db(self.env)
        cursor = db.cursor()
        
        try:
            sql = "SELECT id, name, type, description, content FROM testmanager_templates WHERE name = %s AND type = %s;"
            cursor.execute(sql, (t_name, t_type))
            result = None
            for id_, name, type_, description, content in cursor:
                result = { 'id': id_, 'name': name, 'type': type_, 'description': description, 'content': content }
            return result

        except:
            self.env.log.error("Error getting template with name '%s' and type '%s'" % (t_name, t_type))
            self.env.log.error(formatExceptionInfo())
            return None

    # save a template
    def save_template(self, t_id, t_name, t_type, t_desc, t_cont, t_action):
        db, handle_ta = get_db_for_write(self.env)
        cursor = db.cursor()

        try:
            if t_action == 'ADD':
                t_id = self.get_next_template_id()
                self.env.log.debug("next id is: " + t_id)
                cursor.execute("""
                    INSERT INTO testmanager_templates (id, name, type, description, content) 
                        VALUES (%s,%s,%s,%s,%s)
                """, (t_id, t_name, t_type, t_desc, t_cont))
            else:
                cursor.execute("""
                    UPDATE testmanager_templates 
                        SET description = %s, content = %s 
                        WHERE id = %s AND name = %s AND type = %s
                """, (t_desc, t_cont, t_id, t_name, t_type))

            if handle_ta:
                db.commit()
                
        except:
            self.env.log.error("Error saving template with id '%s'" % t_id)
            self.env.log.error(formatExceptionInfo())
            db.rollback()
            return False
            
        return True

    def remove_template(self, t_id):
        """ Removes a single template by id """
        db, handle_ta = get_db_for_write(self.env)
        cursor = db.cursor()
        
        try:
            sql = "DELETE FROM testmanager_templates WHERE id = %s"
            self.env.log.debug("removing template with id '%s'" % t_id)
            cursor.execute(sql, (t_id,))
            
            if handle_ta:
                db.commit()

        except:
            self.env.log.error("Error removing template with id '%s'" % t_id)
            self.env.log.error(formatExceptionInfo())
            db.rollback()
            return False
        
        return True

    def get_templates(self, t_type):
        """ Get all templates of desired type """
        db = get_db(self.env)
        cursor = db.cursor()

        items = []
        
        try:
            sql = "SELECT id, name, type, description, content FROM testmanager_templates WHERE type = %s ORDER BY name" 
            cursor.execute(sql, (t_type,))
            for id_, name, type_, description, content in cursor:
                template = { 'id': id_, 'name': name, 'type': type_, 'description': description, 'content': content }
                items.append(template)
            
        except:
            self.env.log.error("Error retrieving all the templates of type '%s'" % t_type)
            self.env.log.error(formatExceptionInfo())

        return items

    def template_exists(self, name, t_type):
        """ Check if a given template with desired name and type already exists """
        db = get_db(self.env)
        cursor = db.cursor()
        
        try:
            sql = "SELECT COUNT(id) FROM testmanager_templates WHERE name = %s AND type = %s"
            cursor.execute(sql, (name, t_type))
            row = cursor.fetchone()

            if row is not None and int(row[0]) > 0:
                return True

        except:
            self.env.log.error("Error checking if template with name '%s' and type '%s' exists" % (name, t_type))
            self.env.log.error(formatExceptionInfo())

        return False

    def template_in_use(self, t_id):
        """ Check if a given Test Case template is in use """
        db = get_db(self.env)
        cursor = db.cursor()
        
        try:
            sql = "SELECT COUNT(*) FROM testconfig where value = %s AND propname LIKE 'TC_TEMPLATE_FOR_TCAT_%%';"
            cursor.execute(sql, (t_id))
            row = cursor.fetchone()
            
            if int(row[0]) > 0:
                return True
            else:
                return False
        except:
            self.env.log.error("Error checking if template with id '%s' is in use" % (t_id))
            self.env.log.error(formatExceptionInfo())
        
        # return true, just to be save and not remove a template in case of other errors
        return True

    def get_next_template_id(self):
        """ Get next id to assign a new temmplate """
        db = get_db(self.env)
        cursor = db.cursor()
        ids = []
        try:
            sql = "SELECT id FROM testmanager_templates;"
            cursor.execute(sql)
            for row in cursor:
                ids.append(int(row[0]))
            if ids:
                ids.sort()
                return (str(ids.pop() + 1))
            else:
                return '0'
        except:
            self.env.log.error("Error retrieving all the templates of type '%s'" % t_type)
            self.env.log.error(formatExceptionInfo())
            raise

    def get_testcatalogs(self):
        """ get list of testcatalogs """
        
        # TODO: Use the TestCatalog class instead
        
        db = get_db(self.env)
        cursor = db.cursor()
        cursor.execute("SELECT * from testcatalog")
        items = []
        for row in cursor:
            c_id = row[0]
            c_name = row[1]
            wikipage = WikiPage(self.env, c_name)
            c_title = get_page_title(wikipage.text)
            c_template = self.get_tc_template_id_for_catalog(c_id)
            cat = {'id': c_id, 'name': c_name, 'title': c_title, 'template': c_template}
            items.append(cat)
            
        return sorted(items, key=itemgetter('title'))

    def get_test_catalog_data_model(self, pagename, include_status=False, planid=None, sortby='name'):
        
        # Create the catalog subtree model
        if pagename != 'TC':
            tcat_id = pagename.rpartition('_TT')[2]
            tcat = TestCatalog(self.env, tcat_id)

            components = {'id': pagename, 'name': pagename.rpartition('_')[2], 'title': tcat.title, 'childrenC': {},'childrenT': {}, 'tot': 0}
        else:
            components = {'name': pagename, 'childrenC': {},'childrenT': {}, 'tot': 0}

        if planid is not None:
            tp = TestPlan(self.env, planid)
            contains_all = tp['contains_all']
            snapshot = tp['freeze_tc_versions']
        else:
            contains_all = True
            snapshot = False

        ts = 0
        author = ''
        status = ''
        version = -1                

        default_status = self.get_default_tc_status()
        
        unique_idx = 0

        for subpage_name, text in self.list_matching_subpages(pagename+'_'):
            subpage_title = get_page_title(text)

            path_name = subpage_name.partition(pagename+'_')[2]
            tokens = path_name.split("_")
            parent = components
            ltok = len(tokens)
            count = 1
            curr_path = pagename
            for tc in tokens:
                curr_path += '_'+tc
                
                if tc == '':
                    break

                if not tc.startswith('TC'):
                    # It is a test catalog page
                    comp = {}
                    if (tc not in parent['childrenC']):
                        comp = {'id': curr_path, 'name': tc, 'title': subpage_title, 'childrenC': {},'childrenT': {}, 'tot': 0, 'parent': parent}
                        parent['childrenC'][tc]=comp
                    else:
                        comp = parent['childrenC'][tc]
                    parent = comp

                else:
                    # It is a test case page
                    tc_id = tc.partition('TC')[2]
                    
                    if include_status:
                        tcip = TestCaseInPlan(self.env, tc_id, planid)
                        if tcip.exists:
                            version = tcip['page_version']

                            for ts, author, status in tcip.list_history():
                                break
                            
                            if not isinstance(ts, datetime):
                                ts = from_any_timestamp(ts)

                        else:
                            if not contains_all:
                                continue
                                
                            ts = tp['time']
                            author = tp['author']
                            status = default_status
                            version = -1                
                        
                    if sortby == 'name':
                        key = subpage_title
                    else:
                        key = ts.isoformat()

                    if key in parent['childrenT']:
                        unique_idx += 1
                        key = key+str(unique_idx)
                        
                    parent['childrenT'][key]={'id':curr_path, 'tc_id': tc_id, 'title': subpage_title, 'status': status.lower(), 'ts': ts, 'author': author, 'version': version}
                    compLoop = parent
                    
                    while (True):
                        compLoop['tot']+=1
                        if ('parent' in compLoop):
                            compLoop = compLoop['parent']
                        else:
                            break
                count+=1

        return components
        
    def get_catalog_model_csv_markup(self, context, planid, components, root_catalog_id, separator=',', include_status=False, fulldetails=False, raw_wiki_format=True):
        # Generate the markup
        ind = {'count': 0}
        text = ''
        
        tcat_fields = GenericClassModelProvider(self.env).get_custom_fields_for_realm('testcatalog')
        tcat_has_custom = tcat_fields is not None and len(tcat_fields) > 0
        
        tc_fields = GenericClassModelProvider(self.env).get_custom_fields_for_realm('testcase')
        tc_has_custom = tc_fields is not None and len(tc_fields) > 0
        
        tcip_fields = GenericClassModelProvider(self.env).get_custom_fields_for_realm('testcaseinplan')
        tcip_has_custom = tcip_fields is not None and len(tcip_fields) > 0

        tp_fields = GenericClassModelProvider(self.env).get_custom_fields_for_realm('testplan')
        tp_has_custom = tp_fields is not None and len(tp_fields) > 0

        custom_ctx = {
            'testcatalog': [tcat_has_custom, tcat_fields],
            'testcase': [tc_has_custom, tc_fields],
            'testcaseinplan': [tcip_has_custom, tcip_fields],
            'testplan': [tp_has_custom, tp_fields]
            }

        text += _("Type")+separator+_("ID")+separator+_("Parent ID")
        
        if include_status:
            text += separator+_("Test Plan Title")
         
        text += separator+_("Title")
            
        if include_status:
            text += separator+_("Contains all Test Cases")+separator+_("Snapshot")
        
        # Include long description only if required
        if fulldetails:
            text += separator+_("Description")

        # Custom testcatalog columns
        if custom_ctx['testcatalog'][0]:
            for f in custom_ctx['testcatalog'][1]:
                if f['type'] == 'text':
                    text += separator+f['label']

        # Custom testplan columns
        if include_status and custom_ctx['testplan'][0]:
            for f in custom_ctx['testplan'][1]:
                if f['type'] == 'text':
                    text += separator+f['label']
                    
        # Custom testcase columns
        if custom_ctx['testcase'][0]:
            for f in custom_ctx['testcase'][1]:
                if f['type'] == 'text':
                    text += separator+f['label']

        # Base testcaseinplan columns
        if include_status:
            text += separator+_("Status")+separator+_("Author")+separator+_("Last Change")
        
            # Custom testcaseinplan columns
            if custom_ctx['testcaseinplan'][0]:
                for f in custom_ctx['testcaseinplan'][1]:
                    if f['type'] == 'text':
                        text += separator+f['label']

        text += '\r\n'

        text += self._get_catalog_csv_markup(context, planid, components, 0, None, '', custom_ctx, separator, include_status, fulldetails, raw_wiki_format)
        text += self._get_subtree_csv_markup(context, planid, components, ind, 0, None, root_catalog_id, custom_ctx, separator, include_status, fulldetails, raw_wiki_format)

        return text

    # Render a single catalog in CSV
    def _get_catalog_csv_markup(self, context, planid, data, level, tp=None, parent_id='', custom_ctx=None, separator=',', include_status=False, fulldetails=False, raw_wiki_format=True):
        text = ''

        tcat_id = data['id'].rpartition('TT')[2]
        tcat = TestCatalog(self.env, tcat_id)
        tcat_title = data['title']
        
        object_type = 'testcatalog'
        if (level == 0):
            object_type = ('testplan', 'testcatalog')[planid=='-1']

        # Common columns
        text += object_type
        
        tplan_title = ''
        tplan_contains_all = ''
        tplan_freeze_tc_versions = ''

        # Common columns
        if object_type == 'testplan':
            tp = TestPlan(self.env, planid)
            if tp.exists:
                tplan_title = tp['name']
                tplan_contains_all = (_("No"), _("Yes"))[tp['contains_all']]
                tplan_freeze_tc_versions = (_("No"), _("Yes"))[tp['freeze_tc_versions']]

            text += separator+planid+separator+tcat_id+separator+tplan_title+separator+((3*level) * ' ')+tcat_title+separator+tplan_contains_all+separator+tplan_freeze_tc_versions
        else:
            text += separator+tcat_id+separator+parent_id+separator+((3*level) * ' ')+tcat_title

        # Include long description only if required
        if fulldetails:
            description = self._get_object_description(tcat.description, raw_wiki_format, context)
            text += separator+description
            
        # Custom testcatalog columns
        if custom_ctx['testcatalog'][0]:
            text += self._get_custom_fields_columns(tcat, custom_ctx['testcatalog'][1], separator)
        
        if object_type == 'testplan':
            # Custom testplan columns
            if custom_ctx['testplan'][0]:
                text += self._get_custom_fields_columns(tp, custom_ctx['testplan'][1], separator)

        text += '\r\n'

        if ('childrenT' in data):            
            cmtData=data['childrenT']
            tcat_id = data['id'].rpartition('TT')[2]
            text += self._get_testcases_csv_markup(context, planid, cmtData, level+1, tp, tcat_id, custom_ctx, separator, include_status, fulldetails, raw_wiki_format)
                    
        return text

    # Render the subtree in CSV
    def _get_subtree_csv_markup(self, context, planid, components, ind, level, tp=None, parent_id='', custom_ctx=None, separator=',', include_status=False, fulldetails=False, raw_wiki_format=True):
        text = ''

        if (level == 0):
            data = components['childrenC']
        else:
            data = components

        keyList = data.keys()
        sortedList = sorted(keyList)
        for x in sortedList:
            ind['count'] += 1
            comp = data[x]
            if ('childrenC' in comp):
                subcData=comp['childrenC']
                
                index = str(ind['count'])

                tcat_id = comp['id'].rpartition('TT')[2]
                tcat = TestCatalog(self.env, tcat_id)
                
                # Common columns
                text += 'testcatalog'+separator+tcat_id+separator+parent_id

                if include_status:
                    text += separator+''+separator+((3*(level+1)) * ' ')+comp['title']+separator+separator
                else:
                    text += separator+((3*(level+1)) * ' ')+comp['title']

                # Include long description only if required
                if fulldetails:
                    description = self._get_object_description(tcat.description, raw_wiki_format, context)
                    text += separator+description
                    
                # Custom testcatalog columns
                if custom_ctx['testcatalog'][0]:
                    text += self._get_custom_fields_columns(tcat, custom_ctx['testcatalog'][1], separator)

                # Custom testplan columns
                if include_status and custom_ctx['testplan'][0]:
                    for f in custom_ctx['testplan'][1]:
                        text += separator
                
                text += '\r\n'
                    
                ind['count']+=1
                text += self._get_subtree_csv_markup(context, planid, subcData, ind, level+1, tp, tcat_id, custom_ctx, separator, include_status, fulldetails, raw_wiki_format)
                if ('childrenT' in comp):            
                    mtData=comp['childrenT']
                    text += self._get_testcases_csv_markup(context, planid, mtData, level+1, tp, tcat_id, custom_ctx, separator, include_status, fulldetails, raw_wiki_format)

        return text

    def _get_testcases_csv_markup(self, context, planid, data, level=0, tp=None, parent_id='', custom_ctx=None, separator=',', include_status=False, fulldetails=False, raw_wiki_format=True): 

        if include_status:
            object_type = 'testcaseinplan'
        else:
            object_type = 'testcase'
            
        text=''
        keyList = data.keys()
        sortedList = sorted(keyList)
        for x in sortedList:
            tick = data[x]
            status = tick['status']

            version = tick['version']
            version_str = (str(version), '')[version == -1]

            tc = None
            if fulldetails or custom_ctx['testcase'][0]:
                tc = TestCase(self.env, tick['tc_id'])

            # Common columns
            text += object_type+separator+tick['tc_id']+separator+parent_id
            
            if include_status:
                text += separator

            text += separator+((3*(level+1)) * ' ')+tick['title']

            if include_status:
                text += separator+separator

            if fulldetails:
                description = self._get_object_description(tc.description, raw_wiki_format, context)
                text += separator+description
                        
            # Custom testcatalog columns
            if custom_ctx['testcatalog'][0]:
                for f in custom_ctx['testcatalog'][1]:
                    text += separator

            # Custom testplan columns
            if include_status and custom_ctx['testplan'][0]:
                for f in custom_ctx['testplan'][1]:
                    text += separator

            # Custom testcase columns
            if custom_ctx['testcase'][0]:
                if tc and tc.exists:
                    text += self._get_custom_fields_columns(tc, custom_ctx['testcase'][1], separator)
                else:
                    for f in custom_ctx['testcase'][1]:
                        text += separator

            has_status = False
            if include_status:
                if status is not None and len(status) > 0 and status != '__none__':
                    # Base testcaseinplan columns
                    text += separator+status+separator+tick['author']+separator+format_datetime(tick['ts'])
                else:
                    text += separator+separator+separator
            
                # Custom testcaseinplan columns
                if custom_ctx['testcaseinplan'][0]:
                    tcip = TestCaseInPlan(self.env, tick['tc_id'], planid)
                    if tcip and tcip.exists:
                        text += self._get_custom_fields_columns(tcip, custom_ctx['testcaseinplan'][1], separator)
                    else:
                        for f in custom_ctx['testcaseinplan'][1]:
                            text += separator

            text += '\r\n'

        return text

    def _get_object_description(self, text, raw_wiki_format, context):
        if raw_wiki_format:
            description = re.sub(self.DOUBLE_QUOTES, "\"\"", text)
        else:
            wikidom = WikiParser(self.env).parse(text)
            out = StringIO()
            f = Formatter(self.env, context)
            f.reset(wikidom)
            f.format(wikidom, out, False)
            description = re.sub(self.DOUBLE_QUOTES, "\"\"", out.getvalue())

        return '"' + description + '"'

    def _get_custom_fields_columns(self, obj, fields, separator):
        result = ''
        
        for f in fields:
            if f['type'] == 'text':
                result += separator
                if obj[f['name']] is not None:
                    result += obj[f['name']]

            # TODO Support other field types

        return result
        
    def list_matching_subpages(self, curpage):
        db = get_db(self.env)
        cursor = db.cursor()

        sql = "SELECT w1.name, w1.text, w1.version FROM wiki w1, (SELECT name, max(version) as ver FROM wiki WHERE name LIKE '%s%%' GROUP BY name) w2 WHERE w1.version = w2.ver AND w1.name = w2.name ORDER BY w2.name" % curpage
        
        cursor.execute(sql)
        for name, text, version in cursor:
            yield name, text
        
        return
        

