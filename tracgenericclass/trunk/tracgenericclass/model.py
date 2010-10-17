# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi
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
from trac.resource import Resource, ResourceNotFound
from trac.util.datefmt import utc, utcmax
from trac.util.text import CRLF
from trac.util.translation import _, N_, gettext
from trac.wiki.api import WikiSystem
from trac.wiki.model import WikiPage
from trac.wiki.web_ui import WikiModule

from tracgenericclass.util import *


class IConcreteClassProvider(Interface):
    """
    Extension point interface for components willing to implement
    concrete classes based on this generic class framework.
    """

    def get_realms():
        """
        Return class realms provided by the component.

        :rtype: `basestring` generator
        """

    def get_data_models():
        """
        Return database tables metadata to allow the framework to create the
        db schema for the classes provided by the component.

        :rtype: a dictionary, which keys are schema names and values 
                are dictionaries with table metadata, as in the following example:
                return {'sample_realm':
                            {'table':
                                Table('samplerealm', key = ('id', 'otherid'))[
                                      Column('id'),
                                      Column('otherid'),
                                      Column('prop1'),
                                      Column('prop2'),
                                      Column('time', type='int64')],
                             'has_custom': True,
                             'has_change': True},
                       }
        """

    def get_fields():
        """
        Return the standard fields for classes in all the realms 
        provided by the component.

        :rtype: a dictionary, which keys are realm names and values 
                are arrays of fields metadata, as in the following example:
                return {'sample_realm': [
                            {'name': 'id', 'type': 'text', 'label': N_('ID')},
                            {'name': 'otherid', 'type': 'text', 'label': N_('Other ID')},
                            {'name': 'prop1', 'type': 'text', 'label': N_('Property 1')},
                            {'name': 'prop2', 'type': 'text', 'label': N_('Property 2')},
                            {'name': 'time', 'type': 'time', 'label': N_('Last Change')}
                       }
        """
        
    def get_metadata():
        """
        Return a set of metadata about the classes in all the realms 
        provided by the component.

        :rtype: a dictionary, which keys are realm names and values 
                are dictionaries of properties.
                
                Available metadata properties are:
                    label: A User-friendly name for the objects in this class.
                    searchable: If present and equal to True indicates the class
                                partecipates in the Trac search framework, and
                                must implement the get_search_results() method.
                    'has_custom': If present and equal to True indicates the class
                                  supports custom fields.
                    'has_change': If present and equal to True indicates the class
                                  supports property change history.
                    
                See the following example:
                return {'sample_realm': {
                                'label': "Sample Realm", 
                                'searchable': True
                            }
                       }
        """
        
    def create_instance(realm, props=None):
        """
        Return an instance of the specified realm, with the specified properties,
        or an empty object if props is None.

        :rtype: `AbstractVariableFieldsObject` sub-class instance
        """


    def check_permission(req, realm, key_str=None, operation='set', name=None, value=None):
        """
        Checks whether the logged in User has permission to perform
        the specified operation on a resource of the specified realm and 
        optionally with the specified key.
        
        Raise an exception if authorization is denied.
        
        Possible operations are:
            'set': set a property with a value. 'name' and 'value' parameters are required.
            'search': search for objects of this class.
        
        :param key_str: optional, the object's key, in the form of a string representing 
                        a dictionary. To get this string, use the 
                        get_string_from_dictionary() function in the
                        tracgenericclass.util package.
        :param operation: optional, the operatyion to be performed on the object.
                          TODO: specify the list of available operations.
        :param name: optional property name, valid for the 'set' operation type
        :param value: optional property value, valid for the 'set' operation type
        """

        
class AbstractVariableFieldsObject(object):
    """ 
    An object which fields are declaratively specified.
    
    The specific object "type" is specified during construction
    as the "realm" parameter.
    This name must also correspond to the database table storing the
    corresponding objects, and is used as the base name for the 
    custom fields table and the change tracking table (see below).
    
    Features:
        * Support for custom fields, specified in the trac.ini file
          with the same syntax as for custom Ticket fields. Custom
          fields are kept in a "<schema>_custom" table
        * Keeping track of all changes to any field, into a separate
          "<schema>_change" table
        * A set of callbacks to allow for subclasses to control and 
          perform actions pre and post any operation pertaining the 
          object's lifecycle
        * Registering listeners, via the IGenericObjectChangeListener
          interface, for object creation, modification and deletion.
        * Searching objects matching any set of valorized fields,
          (even non-key fields), applying the "dynamic record" pattern. 
          See the method list_matching_objects.
    
    Notes on special fields:
    
        self.exists : always tells whether the object currently exists 
                      in the database.
                      
        self.resource: points to a Resource, in the trac environment,
                       corresponding to this object. This is used, for 
                       example, in the workflow implementation.
                       
        self.fields: points to an array of dictionary objects describing
                     name, label, type and other properties of all of
                     this object's fields.
                     
        self.metadata: points to a dictionary object describing 
                       further meta-data about this object.
    
    Note: database tables for specific realms are supposed to already
          exist, this object does not create any tables.
          See below the GenericClassModelProvider to see how to 
          declaratively create the required tables.
    """

    def __init__(self, env, realm='variable_fields_obj', key=None, db=None):
        """
        Creates an empty object and also tries to fetches it from the 
        database, if an object with a matching key is found.
        
        To create an empty, template object, do not specify a key.
        
        To create an object to be later stored in the database:
           1) specify a key at contruction time
           2) set any other property via the obj['fieldname'] = value
              syntax, including custom fields
           3) call the insert() method.
           
        To fetch an existing object from the database:
           1) specify a key at contruction time: the object will be 
            filled with all of the values form the database
           2) modify any other property via the obj['fieldname'] = value
              syntax, including custom fields. This syntax is the only
              one to keep track of the changes to any field
           3) call the save_changes() method.
        """
        self.env = env

        self.exists = False
        
        self.realm = realm
        
        tmmodelprovider = GenericClassModelProvider(self.env)
        
        self.fields = tmmodelprovider.get_fields(realm)
        self.time_fields = [f['name'] for f in self.fields
                            if f['type'] == 'time']

        self.metadata = tmmodelprovider.get_metadata(realm)

        if key is not None and len(key) > 0:
            self.key = key
            self.resource = Resource(realm, self.gey_key_string())
        else:
            self.resource = None
            
        if not key or not self._fetch_object(key, db):
            self._init_defaults(db)
            self.exists = False

        self.env.log.debug("Exists: %s" % self.exists)
        self.env.log.debug(self.values)
        
        self._old = {}

    def get_key_prop_names(self):
        """
        Returns an array with the fields representing the identity
        of this object. 
        The specified fields are assumed being also part of the 
        self.fields array.
        The specified fields are also assumed to correspond to
        columns with same name in the database table.
        """
        return ['id']
        
    def get_key_prop_values(self):
        """
        Returns an array of values for the properties returned by
        get_key_prop_names.
        """
        result = []

        for f in self.get_key_prop_names():
             result.append(self.values[f])
             
        return result

    def get_resource_id(self):
        """
        Returns a string representation of the object's identity.
        Used with the trac Resource API.
        """
        return [str(self.values[f])+'|' for f in self.get_key_prop_names()]
        
    def _init_defaults(self, db=None):
        """ 
        Initializes default values for a new object, based on
        default values specified in the trac.ini file.
        """
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
            db = get_db(self.env, db)
        
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
                self.values[field] = '0'
            else:
                self.values[field] = value

        # Fetch custom fields if available
        custom_fields = [f['name'] for f in self.fields if f.get('custom')]
        cursor.execute(("SELECT name,value FROM %s_custom " + sql_where)
                       % self.realm, self.get_key_prop_values())

        for name, value in cursor:
            if name in custom_fields:
                if value is None:
                    self.values[name] = '0'
                else:
                    self.values[name] = value

        self.post_fetch_object(db)
        
        self.exists = True

        self.env.log.debug('<<< _fetch_object')
        return True
        
    def build_key_object(self):
        """
        Builds and returns a dictionary object with the key properties,
        as returned by get_key_prop_names.
        """
        key = None
        for k in self.get_key_prop_names():
            if (self.values[k] is not None):
                if key is None:
                    key = {}

                key[k] = self.values[k]
        
        return key

    def gey_key_string(self):
        """
        Returns a JSON string with the object key properties
        """
        return get_string_from_dictionary(self.key)

    def get_values_as_string(self, props):
        """
        Returns a JSON string for the specified object properties.
        
        :param props: An array of field names. 
        """
        return get_string_from_dictionary(props, self.values)

    def __getitem__(self, name):
        """
        Allows for using the syntax "obj['fieldname']" to access this
        object's values.
        """
        return self.values.get(name)

    def __setitem__(self, name, value):
        """
        Allows for using the syntax "obj['fieldname']" to access this
        object's values.
        Also logs object modifications so the table <realm>_change 
        can be updated.
        """
        if name in self.values:
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
        """
        Return the value of a field or the default value if it is undefined
        """
        try:
            value = self.values[name]
            if value is not '0':
                return value
            field = [field for field in self.fields if field['name'] == name]
            if field:
                return field[0].get('value', '')
        except KeyError:
            pass
        
    def populate(self, values):
        """
        Populate the object with 'suitable' values from a dictionary
        """
        field_names = [f['name'] for f in self.fields]
        for name in [name for name in values.keys() if name in field_names]:
            self[name] = values.get(name, '')

        # We have to do an extra trick to catch unchecked checkboxes
        for name in [name for name in values.keys() if name[9:] in field_names
                     and name.startswith('checkbox_')]:
            if name[9:] not in values:
                self[name[9:]] = '0'

    def insert(self, when=None, db=None):
        """
        Add object to database.
        
        Parameters:
            When: a datetime object to specify a creation date.
        
        The `db` argument is deprecated in favor of `with_transaction()`.
        """
        self.env.log.debug('>>> insert')

        assert not self.exists, 'Cannot insert an existing object'

        db, handle_ta = get_db_for_write(self.env, db)

        # Add a timestamp
        if when is None:
            when = datetime.now(utc)
        self.values['time'] = self.values['changetime'] = when

        # Perform type conversions
        self.env.log.debug('  Performing type conversions')
        values = dict(self.values)
        for field in self.time_fields:
            if field in values:
                values[field] = to_any_timestamp(values[field])
        
        # Insert record
        self.env.log.debug('  Getting fields')
        std_fields = []
        custom_fields = []
        for f in self.fields:
            fname = f['name']
            if fname in self.values:
                if f.get('custom'):
                    custom_fields.append(fname)
                else:
                    std_fields.append(fname)

        if not self.pre_insert(db):
            return

        self.env.log.debug('  Inserting record')
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
            self.env.log.debug('  Inserting custom fields')
            cursor.executemany("""
            INSERT INTO %s_custom (%s,name,value) VALUES (%s,%%s,%%s)
            """ 
            % (self.realm, 
               ','.join(key_names),
               ','.join(['%s'] * len(key_names))),
            [to_list((key_values, name, self[name])) for name in custom_fields])

        self.post_insert(db)
                
        if handle_ta:
            db.commit()

        self.env.log.debug('  Setting up internal fields')
        self.exists = True
        self.resource = self.resource(id=self.get_resource_id())
        self._old = {}

        self.env.log.debug('  Calling listeners')
        from tracgenericclass.api import GenericClassSystem
        for listener in GenericClassSystem(self.env).change_listeners:
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

        db, handle_ta = get_db_for_write(self.env, db)

        if when is None:
            when = datetime.now(utc)
        when_ts = to_any_timestamp(when)

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
        
        self.post_save_changes(db)

        if handle_ta:
            db.commit()

        old_values = self._old
        self._old = {}
        self.values['changetime'] = when

        from tracgenericclass.api import GenericClassSystem
        for listener in GenericClassSystem(self.env).change_listeners:
            listener.object_changed(self.realm, self, comment, author, old_values)

        self.env.log.debug('<<< save_changes')
        return True

    def delete(self, db=None):
        """
        Delete the object. Also clears the change history and the
        custom fields.
        
        The `db` argument is deprecated in favor of `with_transaction()`.
        """

        self.env.log.debug('>>> delete')

        db, handle_ta = get_db_for_write(self.env, db)

        if not self.pre_delete(db):
            return
            
        #Attachment.delete_all(self.env, 'ticket', self.id, db)

        cursor = db.cursor()

        key_names = self.get_key_prop_names()
        key_values = self.get_key_prop_values()

        sql_where = 'WHERE 1=1'
        for k in key_names:
            sql_where += " AND " + k + "=%%s" 

        self.env.log.debug("Deleting %s: %s" % (self.realm, sql_where))
        for k in key_names:
            self.env.log.debug("%s = %s" % (k, self[k]))
                       
        cursor.execute(("DELETE FROM %s " + sql_where)
            % self.realm, key_values)
        cursor.execute(("DELETE FROM %s_change " + sql_where)
            % self.realm, key_values)
        cursor.execute(("DELETE FROM %s_custom " + sql_where) 
            % self.realm, key_values)

        self.post_delete(db)
                
        if handle_ta:
            db.commit()

        from tracgenericclass.api import GenericClassSystem
        for listener in GenericClassSystem(self.env).change_listeners:
            listener.object_deleted(self.realm, self)
        
        self.exists = False
        self.env.log.debug('<<< delete')

    def save_as(self, new_key, when=None, db=None):
        """
        Saves (a copy of) the object with different key.
        The previous object is not deleted, so if needed it must be
        deleted explicitly.
        """
        self.env.log.debug('>>> save_as')

        db, handle_ta = get_db_for_write(self.env, db)

        old_key = self.key
        if self.pre_save_as(old_key, new_key, db):
            self.key = new_key
        
            # Copy values from key into corresponding self.values field
            for f in self.get_key_prop_names():
                 self.values[f] = new_key[f]

            self.exists = False

            # Create object with new key
            self.insert(when, db)
        
            self.post_save_as(old_key, new_key, db)

            if handle_ta:
                db.commit()

        self.env.log.debug('<<< save_as')
        
    def get_non_empty_prop_names(self):
        """
        Returns a list of names of the fields that are not None.
        """
        std_field_names = []
        custom_field_names = []

        for field in self.fields:
            n = field.get('name')

            if n in self.values and self.values[n] is not None:
                if not field.get('custom'):
                    std_field_names.append(n)
                else:
                    custom_field_names.append(n)
                
        return std_field_names, custom_field_names
        
    def get_values(self, prop_names):
        """ 
        Returns a list of the values for the specified properties,
        in the same order as the property names.
        """
        result = []
        
        for n in prop_names:
            result.append(self.values[n])
                
        return result
                
    def set_values(self, props):
        """
        Sets multiple properties into this object.
        
        Note: this method does not keep history of property changes.
        """
        for n in props:
            self.values[n] = props[n]
                
    def _get_key_from_row(self, row):
        """
        Given a database row with the key properties, builds a 
        dictionary with this object's key.
        """
        key = {}
        
        for i, f in enumerate(self.get_key_prop_names()):
            key[f] = row[i]

        return key
        
    def create_instance(self, key):
        """ 
        Subclasses should override this method to create an instance
        of them with the specified key.
        """
        pass
            
    def list_matching_objects(self, db=None):
        """
        List the objects that match the current values of this object's
        fields.
        To use this method, first create an instance with no key, then
        fill some of its fields with the values you want to find a 
        match on, then call this method.
        A collection of objects found in the database matching the 
        fields you had provided values for will be returned.
        
        The `db` argument is deprecated in favor of `with_transaction()`.
        """
        self.env.log.debug('>>> list_matching_objects')
        
        if db is None:
            db = get_db(self.env, db)

        self.pre_list_matching_objects(db)

        cursor = db.cursor()

        non_empty_std_names, non_empty_custom_names = self.get_non_empty_prop_names()
        
        non_empty_std_values = self.get_values(non_empty_std_names)
        non_empty_custom_values = self.get_values(non_empty_custom_names)

        sql_where = '1=1'
        for k in non_empty_std_names:
            sql_where += " AND " + k + "=%%s" 
        
        cursor.execute(("SELECT %s FROM %s WHERE " + sql_where)
                       % (','.join(self.get_key_prop_names()), self.realm), 
                       non_empty_std_values)

        for row in cursor:
            key = self._get_key_from_row(row)
            self.env.log.debug('<<< list_matching_objects - returning result')
            yield self.create_instance(key)

        self.env.log.debug('<<< list_matching_objects')
       
    def get_search_results(self, req, terms, filters):
        """
        Called in the context of the trac search API, to return a list
        of objects of this class matching the specified terms.�
        
        Concrete classes should override this method to perform class-specific
        searches.
        """
        if False:
            yield None

    # Following is a set of callbacks allowing subclasses to perform
    # actions around the operations that pertain the lifecycle of 
    # this object.
    
    def pre_fetch_object(self, db):
        """ 
        Use this method to perform initialization before fetching the
        object from the database.
        Return False to prevent the object from being fetched from the 
        database.
        """
        return True

    def post_fetch_object(self, db):
        """
        Use this method to further fulfill your object after being
        fetched from the database.
        """
        pass
        
    def pre_insert(self, db):
        """ 
        Use this method to perform work before inserting the
        object into the database.
        Return False to prevent the object from being inserted into the 
        database.
        """
        return True

    def post_insert(self, db):
        """
        Use this method to perform further work after your object has
        been inserted into the database.
        """
        pass
        
    def pre_save_changes(self, db):
        """ 
        Use this method to perform work before saving the object changes
        into the database.
        Return False to prevent the object changes from being saved into 
        the database.
        """
        return True

    def post_save_changes(self, db):
        """
        Use this method to perform further work after your object 
        changes have been saved into the database.
        """
        pass
        
    def pre_delete(self, db):
        """ 
        Use this method to perform work before deleting the object from 
        the database.
        Return False to prevent the object from being deleted from the 
        database.
        """
        return True

    def post_delete(self, db):
        """
        Use this method to perform further work after your object 
        has been deleted from the database.
        """
        pass
        
    def pre_save_as(self, old_key, new_key, db):
        """ 
        Use this method to perform work before saving the object with
        a different identity into the database.
        Return False to prevent the object from being saved into the 
        database.
        """
        return True
        
    def post_save_as(self, old_key, new_key, db):
        """
        Use this method to perform further work after your object 
        has been saved into the database.
        """
        pass
        
    def pre_list_matching_objects(self, db):
        """ 
        Use this method to perform work before finding matches in the 
        database.
        Return False to prevent the search.
        """
        return True


class AbstractWikiPageWrapper(AbstractVariableFieldsObject):
    """
    This subclass is a generic object that is based on a wiki page,
    identified by the 'page_name' field.
    The wiki page lifecycle is managed along with the normal object's
    one.     
    """
    def __init__(self, env, realm='wiki_wrapper_obj', key=None, db=None):
        AbstractVariableFieldsObject.__init__(self, env, realm, key, db)
    
    def post_fetch_object(self, db):
        self.wikipage = WikiPage(self.env, self.values['page_name'])
    
    def delete(self, del_wiki_page=True, db=None):
        """
        Delete the object. Also deletes the Wiki page if so specified in the parameters.
        
        The `db` argument is deprecated in favor of `with_transaction()`.
        """
        
        # The actual wiki page deletion is delayed until pre_delete.
        self.del_wiki_page = del_wiki_page
        
        AbstractVariableFieldsObject.delete(self, db)
        
    def pre_insert(self, db):
        """ 
        Assuming the following fields have been given a value before this call:
        text, author, remote_addr, values['page_name']
        """
        
        wikipage = WikiPage(self.env, self.values['page_name'])
        wikipage.text = self.text
        wikipage.save(self.author, '', self.remote_addr)
        
        self.wikipage = wikipage
        
        return True

    def pre_save_changes(self, db):
        """ 
        Assuming the following fields have been given a value before this call:
        text, author, remote_addr, values['page_name']
        """
        
        wikipage = WikiPage(self.env, self.values['page_name'])
        wikipage.text = self.text
        wikipage.save(self.author, '', self.remote_addr)
    
        self.wikipage = wikipage

        return True

    def pre_delete(self, db):
        """ 
        Assuming the following fields have been given a value before this call:
        values['page_name']
        """
        
        if self.del_wiki_page:
            wikipage = WikiPage(self.env, self.values['page_name'])
            wikipage.delete()
            
        self.wikipage = None
        
        return True


    def get_search_results(self, req, terms, filters):
        """
        Currently delegates the search to the Wiki module. 
        """
        for result in WikiModule(self.env).get_search_results(req, terms, ('wiki',)):
            yield result


class GenericClassModelProvider(Component):
    """
    This class provides a factory for generic classes and derivatives.
    
    The actual data model on the db is created starting from the
    SCHEMA declaration below.
    For each table, we specify whether to create also a '_custom' and
    a '_change' table.
    
    This class also provides the specification of the available fields
    for each class, being them standard fields and the custom fields
    specified in the trac.ini file.
    The custom field specification follows the same syntax as for
    Tickets.
    Currently, only 'text' type of fields are supported.
    """

    class_providers = ExtensionPoint(IConcreteClassProvider)
    
    all_fields = {}
    all_custom_fields = {}
    all_metadata = {}
    
    _class_providers_map = None

    # Class providers managament
    def get_class_provider(self, realm):
        """
        Return the component responsible for providing the specified
        concrete class implementation.

        :param  realm: the realm which uniquely identifies the class.
        :return: a `Component` implementing `IConcreteClassProvider`
                 or `None`
        """
        # build a dict of realm keys to IConcreteClassProvider
        # implementations
        if not self._class_providers_map:
            map = {}
            for provider in self.class_providers:
                for r in provider.get_realms() or []:
                    self.env.log.debug("Mapping realm %s to provider %s" % (r, provider))
                    map[r] = provider
            self._class_providers_map = map
        
        if realm in self._class_providers_map:
            return self._class_providers_map.get(realm)
        else:
            return None

    def get_known_realms(self):
        """
        Return a list of all the realm names of registered
        class providers.
        """
        realms = []
        for provider in self.class_providers:
            for realm in provider.get_realms() or []:
                realms.append(realm)
                
        return realms


    # Factory method
    def get_object(self, realm, key=None):
        """
        Returns an instance of the specified class (by means of its 
        realm name), with the specified key.
        """
        obj = None
        
        provider = self.get_class_provider(realm)
        self.env.log.debug("Provider for realm %s is %s" % (realm, provider))

        if provider:
            self.env.log.debug("Object key is %s" % key)
            return provider.create_instance(realm, key)
        else:
            self.env.log.debug("Provider for realm %s not found" % realm)
            return None


    # Permission check
    def check_permission(self, req, realm, key_str=None, operation='set', name=None, value=None):
        """
        Checks whether the logged in User has permission to perform
        the specified operation on a resource of the specified realm and 
        optionally with the specified key.
        
        Raise an exception if authorization is denied.

        Actually delegates to the concrete class provider the permission check.

        See the IConcreteClassProvider method with the same name for more details
        about the available operations and the function parameters.
        """

        provider = self.get_class_provider(realm)
        if provider is not None:
            provider.check_permission(req, realm, key_str, operation, name, value)

            
    # Fields management
    def reset_fields(self):
        """
        Invalidate field cache.
        """
        self.all_fields = {}
        
    def get_fields(self, realm):
        self.env.log.debug(">>> get_fields")
        
        if realm not in self.fields():
            raise TracError("Requested field information not found for class %s." % realm)
            
        fields = copy.deepcopy(self.fields()[realm])
        #label = 'label' # workaround gettext extraction bug
        #for f in fields:
        #    f[label] = gettext(f[label])

        self.env.log.debug("<<< get_fields")
        return fields
        
    def get_metadata(self, realm):
        tmp_metadata = self.metadata()
        if realm in tmp_metadata:
            metadata = copy.deepcopy(tmp_metadata[realm])
        else:
            metadata = None

        return metadata
        
    def fields(self):
        """Return the list of fields available for every realm."""

        if not self.all_fields:
            fields = {}

            for provider in self.class_providers:
                realm_fields = provider.get_fields()
                for realm in realm_fields:
                    tmp_fields = realm_fields[realm]

                    self.append_custom_fields(tmp_fields, self.get_custom_fields_for_realm(realm))
                    
                    fields[realm] = tmp_fields

            self.all_fields = fields

            # Print debug information about all known realms and fields
            for r in self.all_fields:
                self.env.log.debug("Fields for realm %s:" % r)
                for f in self.all_fields[r]:
                    self.env.log.debug("   %s : %s" % (f['name'], f['type']))
                    if 'custom' in f:
                        self.env.log.debug("     (custom)")

        return self.all_fields
        
    def metadata(self):
        """Return metadata information about concrete classes."""

        if not self.all_metadata:
            metadata = {}

            for provider in self.class_providers:
                realm_metadata = provider.get_metadata()
                for realm in realm_metadata:
                    metadata[realm] = realm_metadata[realm]

            self.all_metadata = metadata

        return self.all_metadata

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
            config = self.config[realm+'-tm_custom']

            self.env.log.debug(config.options())
    
            for name in [option for option, value in config.options()
                         if '.' not in option]:
                if not re.match('^[a-zA-Z][a-zA-Z0-9_]+$', name):
                    self.log.warning('Invalid name for custom field: "%s" '
                                     '(ignoring)', name)
                    continue

                self.env.log.debug("  Option: %s" % name)
                         
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

# Methods to help components create their databases
def need_db_upgrade(env, schema, db):
    """
    Call this method from inside your Component IEnvironmentSetupParticipant's
    environment_needs_upgrade() function to check whether your Component 
    using the generic classes needs to create the corresponding database tables.
    
    :param schema: The db schema definition, as returned by 
                   the get_data_models() function in the IConcreteClassProvider
                   interface.
    """
    cursor = db.cursor()
    try:
        for realm in schema:
            table_metadata = schema[realm]
            tablem = table_metadata['table']
            
            tname = tablem.name

            cursor.execute("select count(*) from %s" % tname)
            cursor.fetchone()
        
        return False
    except:
        db.rollback()
        print("Need to create db tables for class '%s'." % realm)
        return True

        
def upgrade_db(env, schema, db):
    """
    Call this method from inside your Component IEnvironmentSetupParticipant's
    upgrade_environment() function to create the database tables corresponding to
    your Component's generic classes.
    
    :param schema: The db schema definition, as returned by 
                   the get_data_models() function in the IConcreteClassProvider
                   interface.
    """
    try:
        try:
            from trac.db import DatabaseManager
            db_backend, _ = DatabaseManager(env)._get_connector()
        except ImportError:
            db_backend = env.get_db_cnx()

        env.log.debug("Upgrading DB...")
            
        # Create the required tables
        cursor = db.cursor()
        for realm in schema:
            table_metadata = schema[realm]
            tablem = table_metadata['table']
            
            tname = tablem.name

            key_names = [k for k in tablem.key]
            
            # Create base table
            env.log.debug("Creating base table %s..." % tname)
            for stmt in db_backend.to_sql(tablem):
                env.log.debug(stmt)
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
                
                custom_key = copy.deepcopy(key_names)
                custom_key.append('name')
                
                table_custom = Table(tname+'_custom', key = custom_key)[cols]
                env.log.debug("Creating custom properties table %s..." % table_custom.name)
                for stmt in db_backend.to_sql(table_custom):
                    env.log.debug(stmt)
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

                change_key = copy.deepcopy(key_names)
                change_key.append('time')
                change_key.append('field')

                table_change = Table(tname+'_change', key = change_key)[cols]
                env.log.debug("Creating change history table %s..." % table_change.name)
                for stmt in db_backend.to_sql(table_change):
                    env.log.debug(stmt)
                    cursor.execute(stmt)

        db.commit()

    except:
        env.log.debug(formatExceptionInfo())
        env.log.debug("Exception during database creation.")

        db.rollback()
        raise

