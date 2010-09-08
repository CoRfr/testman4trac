# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi, Marco Cipriani
#

import copy
import re
import sys
import time
import traceback

from datetime import date, datetime

from trac.attachment import Attachment
from trac.core import *
from trac.db import Table, Column, Index
from trac.env import IEnvironmentSetupParticipant
from trac.resource import Resource, ResourceNotFound
from trac.util.datefmt import utc, utcmax
from trac.util.text import empty, CRLF
from trac.util.translation import _, N_, gettext
from trac.wiki.api import WikiSystem
from trac.wiki.model import WikiPage

from testmanager.util import *


__all__ = ['AbstractVariableFieldsObject', 'AbstractWikiPageWrapper', 'TestCatalog', 'TestCase', 'TestCaseInPlan', 'TestPlan', 'TestManagerModelProvider']


class AbstractVariableFieldsObject(object):

    def __init__(self, env, realm='variable_fields_obj', key=None, db=None):
        self.env = env

        self.exists = False
        
        self.realm = realm
        self.resource = Resource(realm, key)
        
        self.fields = TestManagerModelProvider(self.env).get_fields(realm)
        self.time_fields = [f['name'] for f in self.fields
                            if f['type'] == 'time']
                            
        if not key or not self._fetch_object(key, db):
            self._init_defaults(db)
            self.key = None
            self.exists = False

        self.env.log.debug("Exists: %s" % self.exists)
        print(self.values)
        
        self._old = {}

    def _get_db(self, db):
        return db or self.env.get_read_db()

    def get_key_prop_names(self):
        return ['id']
        
    def get_key_prop_values(self):
        result = []

        for f in self.get_key_prop_names():
             result.append(self.values[f])
             
        return result

    def get_resource_id(self):
        return [str(self.values[f])+'|' for f in self.get_key_prop_names()]
        
    def _init_defaults(self, db=None):
        for field in self.fields:
            default = None
            if field['name'] in self.protected_fields:
                # Ignore for new - only change through workflow
                pass
            elif not field.get('custom'):
                default = self.env.config.get(realm,
                                              'default_' + field['name'])
            else:
                default = field.get('value')
                options = field.get('options')
                if default and options and default not in options:
                    try:
                        default = options[int(default)]
                    except (ValueError, IndexError):
                        self.env.log.warning('Invalid default value "%s" '
                                             'for custom field "%s"'
                                             % (default, field['name']))
            if default:
                self.values.setdefault(field['name'], default)

    def _fetch_object(self, key, db=None):
        self.env.log.debug('>>> _fetch_object')
    
        if db is None:
            db = self._get_db(db)
        
        if not self.pre_fetch_object(db):
            return
        
        row = None

        # Fetch the standard fields
        std_fields = [f['name'] for f in self.fields
                      if not f.get('custom')]
        cursor = db.cursor()

        sql_where = "WHERE 1=1"
        for k in self.get_key_prop_names():
            sql_where += " AND " + k + "=%%s" 

        self.env.log.debug("Searching for %s: %s" % (self.realm, sql_where))
        for k in self.get_key_prop_names():
            self.env.log.debug("%s = %s" % (k, self[k]))
        
        cursor.execute(("SELECT %s FROM %s " + sql_where)
                       % (','.join(std_fields), self.realm), self.get_key_prop_values())
        row = cursor.fetchone()

        if not row:
            #raise ResourceNotFound(_('The specified object of type %(realm)s does not exist.', 
            #                         realm=self.realm), _('Invalid object key'))
            self.env.log.debug("Object NOT found.")
            return False

        self.env.log.debug("Object found.")
            
        self.key = self.build_key_object()
        for i, field in enumerate(std_fields):
            value = row[i]
            if field in self.time_fields:
                self.values[field] = from_any_timestamp(value)
            elif value is None:
                self.values[field] = empty
            else:
                self.values[field] = value

        # Fetch custom fields if available
        custom_fields = [f['name'] for f in self.fields if f.get('custom')]
        cursor.execute(("SELECT name,value FROM %s_custom " + sql_where)
                       % self.realm, self.get_key_prop_values())

        for name, value in cursor:
            if name in custom_fields:
                if value is None:
                    self.values[name] = empty
                else:
                    self.values[name] = value

        self.post_fetch_object(db)
        
        self.exists = True

        self.env.log.debug('<<< _fetch_object')
        return True
        

    def pre_fetch_object(self, db):
        return True

    def post_fetch_object(self, db):
        pass
        
    def pre_insert(self, db):
        return True

    def post_insert(self, db):
        pass
        
    def pre_save_changes(self, db):
        return True

    def post_save_changes(self, db):
        pass
        
    def pre_delete(self, db):
        return True

    def post_delete(self, db):
        pass
        
    def post_save_as(self, old_key, new_key, db):
        pass
        
    def pre_list_matching_objects(self, db):
        return True
     
    def build_key_object(self):
        key = None
        for k in self.get_key_prop_names():
            if (self.values[k] is not None):
                if key is None:
                    key = {}

                key[k] = self.values[k]
            
        return key

    def __getitem__(self, name):
        return self.values.get(name)

    def __setitem__(self, name, value):
        """Log object modifications so the table ticket_change can be updated
        """
        self.env.log.debug("Value before: %s" % self.values[name])
        if name in self.values and self.values[name] == value:
            return
        if name not in self._old: # Changed field
            self.env.log.debug("Changing field value.")
            self._old[name] = self.values.get(name)
        elif self._old[name] == value: # Change of field reverted
            del self._old[name]
        if value:
            if isinstance(value, list):
                raise TracError(_("Multi-values fields not supported yet"))
            field = [field for field in self.fields if field['name'] == name]
            if field and field[0].get('type') != 'textarea':
                value = value.strip()
        self.values[name] = value
        self.env.log.debug("Value after: %s" % self.values[name])

    def get_value_or_default(self, name):
        """Return the value of a field or the default value if it is undefined
        """
        try:
            value = self.values[name]
            if value is not empty:
                return value
            field = [field for field in self.fields if field['name'] == name]
            if field:
                return field[0].get('value', '')
        except KeyError:
            pass
        
    def populate(self, values):
        """Populate the object with 'suitable' values from a dictionary"""
        field_names = [f['name'] for f in self.fields]
        for name in [name for name in values.keys() if name in field_names]:
            self[name] = values.get(name, '')

        # We have to do an extra trick to catch unchecked checkboxes
        for name in [name for name in values.keys() if name[9:] in field_names
                     and name.startswith('checkbox_')]:
            if name[9:] not in values:
                self[name[9:]] = '0'

    def insert(self, when=None, db=None):
        """Add object to database.
        
        The `db` argument is deprecated in favor of `with_transaction()`.
        """
        self.env.log.debug('>>> insert')

        assert not self.exists, 'Cannot insert an existing ticket'

        # Add a timestamp
        if when is None:
            when = datetime.now(utc)
        self.values['time'] = self.values['changetime'] = when

        # Perform type conversions
        values = dict(self.values)
        for field in self.time_fields:
            if field in values:
                values[field] = to_any_timestamp(values[field])
        
        # Insert record
        std_fields = []
        custom_fields = []
        for f in self.fields:
            fname = f['name']
            if fname in self.values:
                if f.get('custom'):
                    custom_fields.append(fname)
                else:
                    std_fields.append(fname)

        @self.env.with_transaction(db)
        def do_insert(db):
            if not self.pre_insert(db):
                return
            
            cursor = db.cursor()
            cursor.execute("INSERT INTO %s (%s) VALUES (%s)"
                           % (self.realm,
                              ','.join(std_fields),
                              ','.join(['%s'] * len(std_fields))),
                           [values[name] for name in std_fields])

            # Insert custom fields
            key_names = self.get_key_prop_names()
            key_values = self.get_key_prop_values()
            if custom_fields:
                cursor.executemany("""
                INSERT INTO %s_custom (%s,name,value) VALUES (%s,%%s,%%s)
                """ 
                % (self.realm, 
                   ','.join(key_names),
                   ','.join(['%s'] * len(key_names))),
                [to_list((key_values, name, self[name])) for name in custom_fields])

            self.post_insert(db)
                
        self.exists = True
        self.resource = self.resource(id=self.get_resource_id())
        self._old = {}

        from testmanager.api import TestManagerSystem
        for listener in TestManagerSystem(self.env).change_listeners:
            listener.object_created(self.realm, self)

        self.env.log.debug('<<< insert')
        return self.key

    def save_changes(self, author=None, comment=None, when=None, db=None, cnum=''):
        """
        Store object changes in the database. The object must already exist in
        the database.  Returns False if there were no changes to save, True
        otherwise.
        
        The `db` argument is deprecated in favor of `with_transaction()`.
        """
        self.env.log.debug('>>> save_changes')
        assert self.exists, 'Cannot update a new object'

        if not self._old and not comment:
            return False # Not modified

        if when is None:
            when = datetime.now(utc)
        when_ts = to_any_timestamp(when)

        @self.env.with_transaction(db)
        def do_save(db):
            if not self.pre_save_changes(db):
                return
            
            cursor = db.cursor()

            # store fields
            custom_fields = [f['name'] for f in self.fields if f.get('custom')]
            
            key_names = self.get_key_prop_names()
            key_values = self.get_key_prop_values()
            sql_where = '1=1'
            for k in key_names:
                sql_where += " AND " + k + "=%%s" 

            for name in self._old.keys():
                if name in custom_fields:
                    cursor.execute(("""
                        SELECT * FROM %s_custom 
                        WHERE name=%%s AND 
                        """ + sql_where) % self.realm, to_list((name, key_values)))
                        
                    if cursor.fetchone():
                        cursor.execute(("""
                            UPDATE %s_custom SET value=%%s
                            WHERE name=%%s AND 
                            """ + sql_where) % self.realm, to_list((self[name], name, key_values)))
                    else:
                        cursor.execute("""
                            INSERT INTO %s_custom (%s,name,value) 
                            VALUES (%s,%%s,%%s)
                            """ 
                            % (self.realm, 
                            ','.join(key_names),
                            ','.join(['%s'] * len(key_names))),
                            to_list((key_values, name, self[name])))
                else:
                    cursor.execute(("""
                        UPDATE %s SET %s=%%s WHERE 
                        """ + sql_where) 
                        % (self.realm, name),
                        to_list((self[name], key_values)))
                
                cursor.execute(("""
                    INSERT INTO %s_change
                        (%s, time,author,field,oldvalue,newvalue)
                    VALUES (%s, %%s, %%s, %%s, %%s, %%s)
                    """
                    % (self.realm, 
                    ','.join(key_names),
                    ','.join(['%s'] * len(key_names)))),
                    to_list((key_values, when_ts, author, name, 
                    self._old[name], self[name])))
            
            # always save comment, even if empty 
            # (numbering support for timeline)
            
            # TODO Replace hardcoded '1' for comment number with increment with counter
            #cursor.execute("""
            #    INSERT INTO %s_change
            #        (%s, time,author,field,oldvalue,newvalue)
            #    VALUES (%s, %%s, %%s, %%s, %%s, %%s)
            #    """
            #    % (self.realm, 
            #    ','.join(key_names),
            #    ','.join(['%s'] * len(key_names))),
            #    (key_values, when_ts, author, 'comment', 
            #    "None", comment))
                
            #cursor.execute("""
            #    UPDATE %s SET changetime=%%s WHERE 
            #    """ + sql_where 
            #    % (self.realm, 
            #    ','.join(key_names),
            #    ','.join(['%s'] * len(key_names))),
            #    (when_ts, key_values ))
                           
            self.post_save_changes(db)

        old_values = self._old
        self._old = {}
        self.values['changetime'] = when

        from testmanager.api import TestManagerSystem
        for listener in TestManagerSystem(self.env).change_listeners:
            listener.object_changed(self.realm, self, comment, author, old_values)

        self.env.log.debug('<<< save_changes')
        return True

    def delete(self, db=None):
        """Delete the object.
        
        The `db` argument is deprecated in favor of `with_transaction()`.
        """

        self.env.log.debug('>>> delete')

        @self.env.with_transaction(db)
        def do_delete(db):
            if not self.pre_delete(db):
                return
                
            #Attachment.delete_all(self.env, 'ticket', self.id, db)

            key_names = self.get_key_prop_names()
            key_values = self.get_key_prop_values()
            sql_where = '1=1'
            for k in key_names:
                sql_where += " AND " + k + "=%%s" 
                           
            cursor.execute(("DELETE FROM %s WHERE " + sql_where)
                % self.realm, key_values)
            cursor.execute(("DELETE FROM %s_change WHERE " + sql_where)
                % self.realm, key_values)
            cursor.execute(("DELETE FROM %s_custom WHERE " + sql_where) 
                % self.realm, key_values)

            self.post_delete(db)
                
        from testmanager.api import TestManagerSystem
        for listener in TestManagerSystem(self.env).change_listeners:
            listener.object_deleted(self.realm, self)
        
        self.exists = False

    def save_as(self, new_key, when=None, db=None):
        old_key = self.key
        self.key = new_key
    
        # Copy values from key into corresponding self.values field
        for f in self.get_key_prop_names():
             self.values[f] = new_key[f]

        self.exists = False
        
        # Create object with new key
        self.insert(when, db)
    
        self.post_save_as(old_key, new_key, db)

        self.env.log.debug('<<< delete')
        
    def get_non_empty_prop_names(self):
        result = []
        
        for n in self.values:
            if self.values[n] is not None:
                result.append(n)
                
        return result
        
    def get_values(self, prop_names):
        result = []
        
        for n in prop_names:
            result.append(self.values[n])
                
        return result
                
    def _get_key_from_row(self, row):
        key = {}
        
        for i, f in enumerate(self.get_key_prop_names()):
            key[f] = row[i]

        return key
        
    def create_instance(self, key):
        pass
            
    def list_matching_objects(self, db=None):
        """List the objects that match the current values of this object fields 
        
        The `db` argument is deprecated in favor of `with_transaction()`.
        """
        self.env.log.debug('>>> list_matching_objects')
        
        if db is None:
            db = self._get_db(db)

        self.pre_list_matching_objects(db)

        #try:
        cursor = db.cursor()

        non_empty_names = self.get_non_empty_prop_names()
        non_empty_values = self.get_values(non_empty_names)

        sql_where = '1=1'
        for k in non_empty_names:
            sql_where += " AND " + k + "=%%s" 
        
        cursor.execute(("SELECT %s FROM %s WHERE " + sql_where)
                       % (','.join(self.get_key_prop_names()), self.realm), 
                       non_empty_values)

        for row in cursor:
            key = self._get_key_from_row(row)
            self.env.log.debug('<<< list_matching_objects - returning result')
            yield self.create_instance(key)

        #except:
        #    self.env.log.debug(_formatExceptionInfo())
 
        self.env.log.debug('<<< list_matching_objects')
       

class AbstractWikiPageWrapper(AbstractVariableFieldsObject):
    def __init__(self, env, realm='wiki_wrapper_obj', key=None, db=None):
        AbstractVariableFieldsObject.__init__(self, env, realm, key, db)
    
    def post_fetch_object(self, db):
        self.wikipage = WikiPage(self.env, self.values['page_name'])
    
    def delete(self, del_wiki_page=True, db=None):
        """Delete the object. Also deletes the Wiki page if so specified in the parameters.
        
        The `db` argument is deprecated in favor of `with_transaction()`.
        """
        self.del_wiki_page = del_wiki_page
        
        AbstractVariableFieldsObject.delete(self, db)
        
    def pre_insert(self, db):
        """ Assuming the following fields have been given a value before this call:
            text, author, remote_addr, values['page_name']
        """
        
        wikipage = WikiPage(self.env, self.values['page_name'])
        wikipage.text = self.text
        wikipage.save(self.author, '', self.remote_addr)
        
        self.wikipage = wikipage
        
        return True

    def pre_save_changes(self, db):
        """ Assuming the following fields have been given a value before this call:
            text, author, remote_addr, values['page_name']
        """
        
        wikipage = WikiPage(self.env, self.values['page_name'])
        wikipage.text = self.text
        wikipage.save(self.author, '', self.remote_addr)
    
        self.wikipage = wikipage

        return True

    def pre_delete(self, db):
        """ Assuming the following fields have been given a value before this call:
            values['page_name']
        """
        
        if self.del_wiki_page:
            wikipage = WikiPage(self.env, self.values['page_name'])
            wikipage.delete()
            
        self.wikipage = None
        
        return True


        
class AbstractTestDescription(AbstractWikiPageWrapper):
    # Fields that must not be modified directly by the user
    protected_fields = ('id', 'page_name')

    def __init__(self, env, realm='testdescription', id=None, page_name=None, title=None, description=None, db=None):
    
        self.values = {}

        self.values['id'] = id
        self.values['page_name'] = page_name

        self.title = title
        self.description = description
    
        key = self.build_key_object()
    
        AbstractWikiPageWrapper.__init__(self, env, realm, key, db)

    def post_fetch_object(self, db):
        # Fetch the wiki page
        AbstractWikiPageWrapper.post_fetch_object(self, db)

        # Then parse it and derive title, description and author
        self.title = get_page_title(self.wikipage.text)
        self.description = get_page_title(self.wikipage.text)
        self.author = self.wikipage.author

    def pre_insert(self, db):
        """ Assuming the following fields have been given a value before this call:
            title, description, author, remote_addr 
        """
    
        self.text = self.title + CRLF + CRLF + self.description
        AbstractWikiPageWrapper.pre_insert(self, db)

        return True

    def pre_save_changes(self, db):
        """ Assuming the following fields have been given a value before this call:
            title, description, author, remote_addr 
        """
    
        self.text = self.title + CRLF + CRLF + self.description
        AbstractWikiPageWrapper.pre_save_changes(self, db)
        
        return True

    
class TestCatalog(AbstractTestDescription):
    def __init__(self, env, id=None, page_name=None, title=None, description=None, db=None):
    
        AbstractTestDescription.__init__(self, env, 'testcatalog', id, page_name, title, description, db)

    def list_subcatalogs(self):
        return ()
        
    def list_testcases(self):
        return ()

    def list_testplans(self, db=None):
        """Returns a list of test plans for this catalog."""

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
        page_name = self.values['page_name']
        return TestCatalog(self.env, page_name.rpartition('TT')[2].rpartition('_')[0], page_name.rpartition('_TC')[0])
        
    def create_instance(self, key):
        return TestCase(self.env, key['id'])
        
    def move_to(self, tcat, db=None):
        """ Moves the test case into a different catalog
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

        self.values['page_name'] = new_page_name
        self.wikipage = new_page
        
        
class TestCaseInPlan(AbstractVariableFieldsObject):
    # Fields that must not be modified directly by the user
    protected_fields = ('id', 'planid', 'page_name', 'status')

    def __init__(self, env, id=None, planid=None, page_name=None, status=None, db=None):
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
        self['status'] = status

        @self.env.with_transaction(db)
        def do_set_status(db):
            cursor = db.cursor()
            sql = 'INSERT INTO testcasehistory (id, planid, time, author, status) VALUES (%s, %s, %s, %s, %s)'
            cursor.execute(sql, (self.values['id'], self.values['planid'], to_any_timestamp(datetime.now(utc)), author, status))

    def list_history(self, db=None):
        if db is None:
            db = self._get_db(db)
        
        cursor = db.cursor()

        sql = "SELECT time, author, status FROM testcasehistory WHERE id=%s AND planid=%s ORDER BY time DESC"
        
        cursor.execute(sql, (self.values['id'], self.values['planid']))
        for ts, author, status in cursor:
            yield ts, author, status

    
class TestPlan(AbstractVariableFieldsObject):
    # Fields that must not be modified directly by the user
    protected_fields = ('id', 'catid', 'page_name', 'name', 'author', 'time')

    def __init__(self, env, id=None, catid=None, page_name=None, name=None, author=None, db=None):
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

    
        
def simplify_whitespace(name):
    """Strip spaces and remove duplicate spaces within names"""
    if name:
        return ' '.join(name.split())
    return name
        

class TestManagerModelProvider(Component):
    implements(IEnvironmentSetupParticipant)

    SCHEMA = None
    
    def __init__(self):
        self.SCHEMA = []
        self.SCHEMA.append({'table':
                                Table('testconfig', key = ('propname'))[
                                  Column('propname'),
                                  Column('value')],
                             'has_custom': False,
                             'has_change': False})        

        self.SCHEMA.append({'table':
                                Table('testcatalog', key = ('id'))[
                                      Column('id'),
                                      Column('page_name')],
                             'has_custom': True,
                             'has_change': True})
        self.SCHEMA.append({'table':
                                Table('testcase', key = ('id'))[
                                      Column('id'),
                                      Column('page_name')],
                             'has_custom': True,
                             'has_change': True})
        self.SCHEMA.append({'table':
                                Table('testcaseinplan', key = ('id', 'planid'))[
                                      Column('id'),
                                      Column('planid'),
                                      Column('page_name'),
                                      Column('status')],
                             'has_custom': True,
                             'has_change': True})
        self.SCHEMA.append({'table':
                                Table('testcasehistory', key = ('id', 'planid', 'time'))[
                                      Column('id'),
                                      Column('planid'),
                                      Column('time', type='int64'),
                                      Column('author'),
                                      Column('status'),
                                      Index(['id', 'planid', 'time'])],
                             'has_custom': False,
                             'has_change': False})
        self.SCHEMA.append({'table':
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
                             'has_change': True})

    # IEnvironmentSetupParticipant methods
    def environment_created(self):
        self._create_db(self.env.get_db_cnx())

    def environment_needs_upgrade(self, db):
        if self._need_initialization(db):
            return True

        return False

    def upgrade_environment(self, db):
        # Create db
        if self._need_initialization(db):
            self._upgrade_db(db)

    def _need_initialization(self, db):
        cursor = db.cursor()
        try:
            cursor.execute("select count(*) from testconfig")
            cursor.fetchone()
            cursor.execute("select count(*) from testcatalog")
            cursor.fetchone()
            cursor.execute("select count(*) from testcase")
            cursor.fetchone()
            cursor.execute("select count(*) from testcaseinplan")
            cursor.fetchone()
            cursor.execute("select count(*) from testcasehistory")
            cursor.fetchone()
            cursor.execute("select count(*) from testplan")
            cursor.fetchone()
            return False
        except:
            db.rollback()
            print("Testmanager needs to create the db")
            return True
        
    def _create_db(self, db):
        self._upgrade_db(db)
        
    def _upgrade_db(self, db):
        try:
            try:
                from trac.db import DatabaseManager
                db_backend, _ = DatabaseManager(self.env)._get_connector()
            except ImportError:
                db_backend = self.env.get_db_cnx()

            self.env.log.debug("Upgrading DB...")
                
            # Create the required tables
            cursor = db.cursor()
            for table_metadata in self.SCHEMA:
                tablem = table_metadata['table']

                tname = tablem.name
                key_names = [k for k in tablem.key]
                
               # Create base table
                self.env.log.debug("Creating base table %s..." % tname)
                for stmt in db_backend.to_sql(tablem):
                    self.env.log.debug(stmt)
                    cursor.execute(stmt)
  
                    
                # Create custom fields table if required
                if table_metadata['has_custom']:
                    cols = []
                    for k in key_names:
                        # Determine type of column k
                        type = 'text'
                        for c in tablem.columns:
                            if c.name == k:
                                type = c.type
                                
                        cols.append(Column(k, type=type))
                        
                    cols.append(Column('name'))
                    cols.append(Column('value'))
                    
                    custom_key = key_names
                    custom_key.append('name')
                    
                    table_custom = Table(tname+'_custom', key = custom_key)[cols]
                    self.env.log.debug("Creating custom table %s..." % table_custom.name)
                    for stmt in db_backend.to_sql(table_custom):
                        self.env.log.debug(stmt)
                        cursor.execute(stmt)

                # Create change history table if required
                if table_metadata['has_change']:
                    cols = []
                    for k in key_names:
                        # Determine type of column k
                        type = 'text'
                        for c in tablem.columns:
                            if c.name == k:
                                type = c.type

                        cols.append(Column(k, type=type))
                        
                    cols.append(Column('time', type='int64'))
                    cols.append(Column('author'))
                    cols.append(Column('field'))
                    cols.append(Column('oldvalue'))
                    cols.append(Column('newvalue'))
                    cols.append(Index(key_names))

                    change_key = key_names
                    change_key.append('time')
                    change_key.append('field')

                    table_change = Table(tname+'_change', key = change_key)[cols]
                    self.env.log.debug("Creating change history table %s..." % table_change.name)
                    for stmt in db_backend.to_sql(table_change):
                        self.env.log.debug(stmt)
                        cursor.execute(stmt)

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
            print("exception during upgrade")
            raise

            
    # Field management
    all_fields = {}
    all_custom_fields = {}
    
    def reset_fields(self):
        """Invalidate field cache."""
        self.all_fields = {}
        
    def get_fields(self, realm):
        fields = copy.deepcopy(self.fields()[realm])
        #label = 'label' # workaround gettext extraction bug
        #for f in fields:
        #    f[label] = gettext(f[label])
        return fields
        
    def get_ticket_field_labels(self):
        """Produce a (name,label) mapping from `get_fields`."""
        return dict((f['name'], f['label']) for f in
                    TestManagerModelProvider(self.env).get_fields())

    def fields(self):
        """Return the list of fields available for every realm."""

        if not self.all_fields:
            fields = {}
            
            # testcatalog
            tmp_fields = []
            tmp_fields.append({'name': 'id', 'type': 'text',
                           'label': N_('ID')})
            tmp_fields.append({'name': 'page_name', 'type': 'text',
                           'label': N_('Wiki page name')})
            self.append_custom_fields(tmp_fields, self.get_custom_fields_for_realm('testcatalog'))
            fields['testcatalog'] = tmp_fields

            # testcase
            tmp_fields = []
            tmp_fields.append({'name': 'id', 'type': 'text',
                           'label': N_('ID')})
            tmp_fields.append({'name': 'page_name', 'type': 'text',
                           'label': N_('Wiki page name')})
            self.append_custom_fields(tmp_fields, self.get_custom_fields_for_realm('testcase'))
            fields['testcase'] = tmp_fields

            # testcaseinplan
            tmp_fields = []
            tmp_fields.append({'name': 'id', 'type': 'text',
                           'label': N_('ID')})
            tmp_fields.append({'name': 'planid', 'type': 'text',
                           'label': N_('Plan ID')})
            tmp_fields.append({'name': 'page_name', 'type': 'text',
                           'label': N_('Wiki page name')})
            tmp_fields.append({'name': 'status', 'type': 'text',
                           'label': N_('Status')})
            self.append_custom_fields(tmp_fields, self.get_custom_fields_for_realm('testcaseinplan'))
            fields['testcaseinplan'] = tmp_fields

            # testplan
            tmp_fields = []
            tmp_fields.append({'name': 'id', 'type': 'text',
                           'label': N_('ID')})
            tmp_fields.append({'name': 'catid', 'type': 'text',
                           'label': N_('Catalog ID')})
            tmp_fields.append({'name': 'page_name', 'type': 'text',
                           'label': N_('Wiki page name')})
            tmp_fields.append({'name': 'name', 'type': 'text',
                           'label': N_('Name')})
            tmp_fields.append({'name': 'author', 'type': 'text',
                           'label': N_('Author')})
            tmp_fields.append({'name': 'time', 'type': 'time',
                           'label': N_('Created')})
            self.append_custom_fields(tmp_fields, self.get_custom_fields_for_realm('testplan'))
            fields['testplan'] = tmp_fields

            self.all_fields = fields

        return self.all_fields

    def append_custom_fields(self, fields, custom_fields):
        if len(custom_fields) > 0:
            for f in custom_fields:
                fields.append(f)
        
    def get_custom_fields_for_realm(self, realm):
        fields = []
    
        for field in self.get_custom_fields(realm):
            field['custom'] = True
            fields.append(field)
            
        return fields

    def get_custom_fields(self, realm):
        return copy.deepcopy(self.custom_fields(realm))

    def custom_fields(self, realm):
        """Return the list of available custom fields."""
        
        if not realm in self.all_custom_fields:
            fields = []
            config = self.config[realm+'-custom']
            for name in [option for option, value in config.options()
                         if '.' not in option]:
                if not re.match('^[a-zA-Z][a-zA-Z0-9_]+$', name):
                    self.log.warning('Invalid name for custom field: "%s" '
                                     '(ignoring)', name)
                    continue
                         
                field = {
                    'name': name,
                    'type': config.get(name),
                    'order': config.getint(name + '.order', 0),
                    'label': config.get(name + '.label') or name.capitalize(),
                    'value': config.get(name + '.value', '')
                }
                if field['type'] == 'select' or field['type'] == 'radio':
                    field['options'] = config.getlist(name + '.options', sep='|')
                    if '' in field['options']:
                        field['optional'] = True
                        field['options'].remove('')
                elif field['type'] == 'text':
                    field['format'] = config.get(name + '.format', 'plain')
                elif field['type'] == 'textarea':
                    field['format'] = config.get(name + '.format', 'plain')
                    field['width'] = config.getint(name + '.cols')
                    field['height'] = config.getint(name + '.rows')
                fields.append(field)

            fields.sort(lambda x, y: cmp(x['order'], y['order']))
            
            self.all_custom_fields[realm] = fields
            
        return self.all_custom_fields[realm]

        
def _formatExceptionInfo(maxTBlevel=5):
    cla, exc, trbk = sys.exc_info()
    excName = cla.__name__
    
    try:
        excArgs = exc.__dict__["args"]
    except KeyError:
        excArgs = "<no args>"
    
    excTb = traceback.format_tb(trbk, maxTBlevel)
    return (excName, excArgs, excTb)
