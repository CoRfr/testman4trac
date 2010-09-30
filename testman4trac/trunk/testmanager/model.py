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
from trac.perm import PermissionError
from trac.resource import Resource, ResourceNotFound
from trac.util.datefmt import utc, utcmax
from trac.util.text import empty, CRLF
from trac.util.translation import _, N_, gettext
from trac.wiki.api import WikiSystem
from trac.wiki.model import WikiPage

from tracgenericclass.model import IConcreteClassProvider, AbstractVariableFieldsObject, AbstractWikiPageWrapper, need_db_upgrade, upgrade_db
from tracgenericclass.util import *

from testmanager.util import *


class AbstractTestDescription(AbstractWikiPageWrapper):
    """
    A test description object based on a Wiki page.
    Concrete subclasses are TestCatalog and TestCase.
    
    Uses a textual 'id' as key.
    
    Comprises a title and a description, currently embedded in the wiki
    page respectively as the first line and the rest of the text.
    The title is automatically wiki-formatted as a second-level title
    (i.e. sorrounded by '==').
    """
    
    # Fields that must not be modified directly by the user
    protected_fields = ('id', 'page_name')

    def __init__(self, env, realm='testdescription', id=None, page_name=None, title=None, description=None, db=None):
    
        self.env = env
        
        self.values = {}

        self.values['id'] = id
        self.values['page_name'] = page_name

        self.title = title
        self.description = description

        self.env.log.debug('Title: %s' % self.title)
        self.env.log.debug('Description: %s' % self.description)
    
        key = self.build_key_object()
    
        AbstractWikiPageWrapper.__init__(self, env, realm, key, db)

    def post_fetch_object(self, db):
        # Fetch the wiki page
        AbstractWikiPageWrapper.post_fetch_object(self, db)

        # Then parse it and derive title, description and author
        self.title = get_page_title(self.wikipage.text)
        self.description = get_page_description(self.wikipage.text)
        self.author = self.wikipage.author

        self.env.log.debug('Title: %s' % self.title)
        self.env.log.debug('Description: %s' % self.description)

    def pre_insert(self, db):
        """ Assuming the following fields have been given a value before this call:
            title, description, author, remote_addr 
        """
    
        self.text = '== '+self.title+' ==' + CRLF + CRLF + self.description
        AbstractWikiPageWrapper.pre_insert(self, db)

        return True

    def pre_save_changes(self, db):
        """ Assuming the following fields have been given a value before this call:
            title, description, author, remote_addr 
        """
    
        self.text = '== '+self.title+' ==' + CRLF + CRLF + self.description
        AbstractWikiPageWrapper.pre_save_changes(self, db)
        
        return True

    
class TestCatalog(AbstractTestDescription):
    """
    A container for test cases and sub-catalogs.
    
    Test catalogs are organized in a tree. Since wiki pages are instead
    on a flat plane, we use a naming convention to flatten the tree into
    page names. These are examples of wiki page names for a tree:
        TC          --> root of the tree. This page is automatically 
                        created at plugin installation time.
        TC_TT0      --> test catalog at the first level. Note that 0 is
                        the catalog ID, generated at creation time.
        TC_TT0_TT34 --> sample sub-catalog, with ID '34', of the catalog 
                        with ID '0'
        TC_TT27     --> sample other test catalog at first level, with
                        ID '27'
                        
        There is not limit to the depth of a test tree.
                        
        Test cases are contained in test catalogs, and are always
        leaves of the tree:

        TC_TT0_TT34_TC65 --> sample test case, with ID '65', contained 
                             in sub-catalog '34'.
                             Note that test case IDs are independent on 
                             test catalog IDs.
    """
    def __init__(self, env, id=None, page_name=None, title=None, description=None, db=None):
    
        AbstractTestDescription.__init__(self, env, 'testcatalog', id, page_name, title, description, db)

    def list_subcatalogs(self):
        """
        Returns a list of the sub catalogs of this catalog.
        """
        # TODO: Implement method
        return ()
        
    def list_testcases(self):
        """
        Returns a list of the test cases in this catalog.
        """
        # TODO: Implement method
        return ()

    def list_testplans(self, db=None):
        """
        Returns a list of test plans for this catalog.
        """

        tp_search = TestPlan(self.env)
        tp_search['catid'] = self.values['id']
        
        for tp in tp_search.list_matching_objects(db):
            yield tp

    def create_instance(self, key):
        return TestCatalog(self.env, key['id'])
        
    
class TestCase(AbstractTestDescription):
    def __init__(self, env, id=None, page_name=None, title=None, description=None, db=None):
    
        AbstractTestDescription.__init__(self, env, 'testcase', id, page_name, title, description, db)

    def get_enclosing_catalog(self):
        """
        Returns the catalog containing this test case.
        """
        page_name = self.values['page_name']
        cat_id = page_name.rpartition('TT')[2].rpartition('_')[0]
        cat_page = page_name.rpartition('_TC')[0]
        
        return TestCatalog(self.env, cat_id, cat_page)
        
    def create_instance(self, key):
        return TestCase(self.env, key['id'])
        
    def move_to(self, tcat, db=None):
        """ 
        Moves the test case into a different catalog.
        
        Note: the test case keeps its ID, but the old wiki page is
        deleted and a new page is created with the new "path".
        This means the page change history is lost.
        """
        
        text = self.wikipage.text
        
        old_cat = self.get_enclosing_catalog()
        
        # Create new wiki page to store the test case
        new_page_name = tcat['page_name'] + '_TC' + self['id']
        new_page = WikiPage(self.env, new_page_name)
               
        new_page.text = text
        new_page.save(self.author, "Moved from catalog \"%s\" (%s)" % (old_cat.title, old_cat['page_name']), '127.0.0.1')

        # Remove test case from all the plans
        tcip_search = TestCaseInPlan(self.env)
        tcip_search['id'] = self.values['id']
        for tcip in tcip_search.list_matching_objects(db):
            tcip.delete(db)

        # Delete old wiki page
        self.wikipage.delete()

        self['page_name'] = new_page_name
        self.wikipage = new_page
        
        
class TestCaseInPlan(AbstractVariableFieldsObject):
    """
    This object represents a test case in a test plan.
    It keeps the latest test execution status (aka verdict).
    
    The status, as far as this class is concerned, can be just any 
    string.
    The plugin logic, anyway, currently recognizes only three hardcoded
    statuses, but this can be evolved without need to modify also this
    class. 
    
    The history of test execution status changes is instead currently
    kept in another table, testcasehistory, which is not backed by any
    python class. 
    This is a duplication, since the 'changes' table also keeps track
    of status changes, so the testcasehistory table may be removed in 
    the future.
    """
    
    # Fields that must not be modified directly by the user
    protected_fields = ('id', 'planid', 'page_name', 'status')

    def __init__(self, env, id=None, planid=None, page_name=None, status=None, db=None):
        """
        The test case in plan is related to a test case, the 'id' and 
        'page_name' arguments, and to a test plan, the 'planid' 
        argument.
        """
        self.values = {}

        self.values['id'] = id
        self.values['planid'] = planid
        self.values['page_name'] = page_name
        self.values['status'] = status

        key = self.build_key_object()
    
        AbstractVariableFieldsObject.__init__(self, env, 'testcaseinplan', key, db)

    def get_key_prop_names(self):
        return ['id', 'planid']
        
    def create_instance(self, key):
        return TestCaseInPlan(self.env, key['id'], key['planid'])
        
    def set_status(self, status, author, db=None):
        """
        Sets the execution status of the test case in the test plan.
        This method immediately writes into the test case history, but
        does not write the new status into the database table for this
        test case in plan.
        You need to call 'save_changes' to achieve that.
        """
        self['status'] = status

        @self.env.with_transaction(db)
        def do_set_status(db):
            cursor = db.cursor()
            sql = 'INSERT INTO testcasehistory (id, planid, time, author, status) VALUES (%s, %s, %s, %s, %s)'
            cursor.execute(sql, (self.values['id'], self.values['planid'], to_any_timestamp(datetime.now(utc)), author, status))

    def list_history(self, db=None):
        """
        Returns an ordered list of status changes, along with timestamp
        and author, starting from the most recent.
        """
        if db is None:
            db = self._get_db(db)
        
        cursor = db.cursor()

        sql = "SELECT time, author, status FROM testcasehistory WHERE id=%s AND planid=%s ORDER BY time DESC"
        
        cursor.execute(sql, (self.values['id'], self.values['planid']))
        for ts, author, status in cursor:
            yield ts, author, status

    
class TestPlan(AbstractVariableFieldsObject):
    """
    A test plan represents a particular instance of test execution
    for a test catalog.
    You can create any number of test plans on any test catalog (or 
    sub-catalog).
    A test plan is associated to a test catalog, and to every 
    test case in it, with the initial state equivalent to 
    "to be executed".
    The association with test cases is achieved through the 
    TestCaseInPlan objects.
    
    For optimization purposes, a TestCaseInPlan is created in the
    database only as soon as its status is changed (i.e. from "to be
    executed" to something else).
    So you cannot always count on the fact that a TestCaseInPlan 
    actually exists for every test case in a catalog, when a particular
    test plan has been created for it.
    """
    
    # Fields that must not be modified directly by the user
    protected_fields = ('id', 'catid', 'page_name', 'name', 'author', 'time')

    def __init__(self, env, id=None, catid=None, page_name=None, name=None, author=None, db=None):
        """
        A test plan has an ID, generated at creation time and 
        independent on those for test catalogs and test cases.
        It is associated to a test catalog, the 'catid' and 'page_name'
        arguments.
        It has a name and an author.
        """
        self.values = {}

        self.values['id'] = id
        self.values['catid'] = catid
        self.values['page_name'] = page_name
        self.values['name'] = name
        self.values['author'] = author

        key = self.build_key_object()
    
        AbstractVariableFieldsObject.__init__(self, env, 'testplan', key, db)

    def create_instance(self, key):
        return TestPlan(self.env, key['id'])

        
class TestManagerModelProvider(Component):
    """
    This class provides the data model for the test management plugin.
    
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
                'testconfig':
                    {'table':
                        Table('testconfig', key = ('propname'))[
                          Column('propname'),
                          Column('value')],
                     'has_custom': False,
                     'has_change': False},
                'testcatalog':  
                    {'table':
                        Table('testcatalog', key = ('id'))[
                              Column('id'),
                              Column('page_name')],
                     'has_custom': True,
                     'has_change': True},
                'testcase':  
                    {'table':
                        Table('testcase', key = ('id'))[
                              Column('id'),
                              Column('page_name')],
                     'has_custom': True,
                     'has_change': True},
                'testcaseinplan':  
                    {'table':
                        Table('testcaseinplan', key = ('id', 'planid'))[
                              Column('id'),
                              Column('planid'),
                              Column('page_name'),
                              Column('status')],
                     'has_custom': True,
                     'has_change': True},
                'testcasehistory':  
                    {'table':
                        Table('testcasehistory', key = ('id', 'planid', 'time'))[
                              Column('id'),
                              Column('planid'),
                              Column('time', type='int64'),
                              Column('author'),
                              Column('status'),
                              Index(['id', 'planid', 'time'])],
                     'has_custom': False,
                     'has_change': False},
                'testplan':  
                    {'table':
                        Table('testplan', key = ('id'))[
                              Column('id'),
                              Column('catid'),
                              Column('page_name'),
                              Column('name'),
                              Column('author'),
                              Column('time', type='int64'),
                              Index(['id']),
                              Index(['catid'])],
                     'has_custom': True,
                     'has_change': True}
            }

    FIELDS = {
                'testcatalog': [
                    {'name': 'id', 'type': 'text', 'label': N_('ID')},
                    {'name': 'page_name', 'type': 'text', 'label': N_('Wiki page name')}
                ],
                'testcase': [
                    {'name': 'id', 'type': 'text', 'label': N_('ID')},
                    {'name': 'page_name', 'type': 'text', 'label': N_('Wiki page name')}
                ],
                'testcaseinplan': [
                    {'name': 'id', 'type': 'text', 'label': N_('ID')},
                    {'name': 'planid', 'type': 'text', 'label': N_('Plan ID')},
                    {'name': 'page_name', 'type': 'text', 'label': N_('Wiki page name')},
                    {'name': 'status', 'type': 'text', 'label': N_('Status')}
                ],
                'testplan': [
                    {'name': 'id', 'type': 'text', 'label': N_('ID')},
                    {'name': 'catid', 'type': 'text', 'label': N_('Catalog ID')},
                    {'name': 'page_name', 'type': 'text', 'label': N_('Wiki page name')},
                    {'name': 'name', 'type': 'text', 'label': N_('Name')},
                    {'name': 'author', 'type': 'text', 'label': N_('Author')},
                    {'name': 'time', 'type': 'time', 'label': N_('Created')}
                ]
            }
            
    METADATA = {'testcatalog': {
                        'label': "Test Catalog", 
                        'searchable': True,
                        'has_custom': True,
                        'has_change': True
                    },
                'testcase': {
                        'label': "Test Case", 
                        'searchable': True,
                        'has_custom': True,
                        'has_change': True
                    },
                'testcaseinplan': {
                        'label': "Test Case in a Plan", 
                        'searchable': True,
                        'has_custom': True,
                        'has_change': True
                    },
                'testplan': {
                        'label': "Test Plan", 
                        'searchable': True,
                        'has_custom': True,
                        'has_change': True
                    }
                }

            
    # IConcreteClassProvider methods
    def get_realms(self):
            yield 'testcatalog'
            yield 'testcase'
            yield 'testcaseinplan'
            yield 'testplan'

    def get_data_models(self):
        return self.SCHEMA

    def get_fields(self):
        return self.FIELDS
        
    def get_metadata(self):
        return self.METADATA
        
    def create_instance(self, realm, key=None):
        self.env.log.debug(">>> create_instance - %s %s" % (realm, key))

        obj = None
        
        if realm == 'testcatalog':
            if key is not None:
                obj = TestCatalog(self.env, key['id'])
            else:
                obj = TestCatalog(self.env)
        elif realm == 'testcase':
            if key is not None:
                obj = TestCase(self.env, key['id'])
            else:
                obj = TestCase(self.env)
        elif realm == 'testcaseinplan':
            if key is not None:
                obj = TestCaseInPlan(self.env, key['id'], key['planid'])
            else:
                obj = TestCaseInPlan(self.env)
        elif realm == 'testplan':
            if key is not None:
                obj = TestPlan(self.env, key['id'])
            else:
                obj = TestPlan(self.env)
        
        self.env.log.debug("<<< create_instance")

        return obj

    def check_permission(self, req, realm, key_str=None, operation='set', name=None, value=None):
        if 'TEST_VIEW' not in req.perm:
            raise PermissionError('TEST_VIEW', realm)
            
        if operation == 'set' and 'TEST_MODIFY' not in req.perm:
            raise PermissionError('TEST_MODIFY', realm)


    # IEnvironmentSetupParticipant methods
    def environment_created(self):
        self.upgrade_environment(self.env.get_db_cnx())

    def environment_needs_upgrade(self, db):
        return self._need_initialization(db)

    def upgrade_environment(self, db):
        # Create db
        if self._need_initialization(db):
            upgrade_db(self.env, self.SCHEMA, db)

            try:            
                cursor = db.cursor()

                # Create default values for configuration properties and initialize counters
                cursor.execute("INSERT INTO testconfig (propname, value) VALUES ('NEXT_CATALOG_ID', '0')")
                cursor.execute("INSERT INTO testconfig (propname, value) VALUES ('NEXT_TESTCASE_ID', '0')")
                cursor.execute("INSERT INTO testconfig (propname, value) VALUES ('NEXT_PLAN_ID', '0')")
                db.commit()

                # Create the basic "TC" Wiki page, used as the root test catalog
                tc_page = WikiPage(self.env, 'TC')
                tc_page.text = ' '
                tc_page.save('System', '', '127.0.0.1')

            except:
                db.rollback()
                self.env.log.debug("Esxception during upgrade")
                raise
                

    def _need_initialization(self, db):
        return need_db_upgrade(self.env, self.SCHEMA, db)
      
