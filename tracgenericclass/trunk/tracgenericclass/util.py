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

import os
import re
import shutil
import sys
import traceback

from datetime import datetime

from trac.core import *

    
def formatExceptionInfo(maxTBlevel=5):
    cla, exc, trbk = sys.exc_info()
    excName = cla.__name__
    
    try:
        excArgs = exc.__dict__["args"]
    except KeyError:
        excArgs = "<no args>"
    
    excTb = traceback.format_tb(trbk, maxTBlevel)
    
    tracestring = ""
    for step in excTb:
        tracestring += step + "\n"
    
    return "Error name: %s\nArgs: %s\nTraceback:\n%s" % (excName, excArgs, tracestring)


checked_utimestamp = False
has_utimestamp = False
checked_compatibility = False
has_read_db = False
    
def to_any_timestamp(date_obj):
    global checked_utimestamp
    global has_utimestamp

    if not checked_utimestamp:
        check_utimestamp()

    if has_utimestamp:
        from trac.util.datefmt import to_utimestamp
        return to_utimestamp(date_obj)
    else:
        # Trac 0.11
        from trac.util.datefmt import to_timestamp
        return to_timestamp(date_obj)

def from_any_timestamp(ts):
    global checked_utimestamp
    global has_utimestamp

    if not checked_utimestamp:
        check_utimestamp()

    if has_utimestamp:
        from trac.util.datefmt import from_utimestamp
        return from_utimestamp(ts)
    else:
        # Trac 0.11
        from trac.util.datefmt import utc
        return datetime.fromtimestamp(ts, utc)

def get_db(env, db=None):
    global checked_compatibility
    global has_read_db

    if db:
        return db

    if not checked_compatibility:
        check_compatibility(env)

    if has_read_db:
        return env.get_read_db()
    else:
        # Trac 0.11
        return env.get_db_cnx()

def get_db_for_write(env, db=None):
    global checked_compatibility
    global has_read_db

    if db:
        return (db, True)

    if not checked_compatibility:
        check_compatibility(env)

    if has_read_db:
        return (env.get_read_db(), True)
    else:
        # Trac 0.11
        return (env.get_db_cnx(), True)

def check_utimestamp():
    global checked_utimestamp
    global has_utimestamp

    try:
        from trac.util.datefmt import to_utimestamp, from_utimestamp
        has_utimestamp = True
    except:
        # Trac 0.11
        has_utimestamp = False

    checked_utimestamp = True

def check_compatibility(env):
    global checked_compatibility
    global has_read_db

    try:
        if env.get_read_db():
            has_read_db = True
    except:
        # Trac 0.11
        has_read_db = False

    checked_compatibility = True

def to_list(params=[]):
    result = []
    
    for i in params:
        if isinstance(i, list):
            for v in i:
                result.append(v)
        else:
            result.append(i)
    
    return tuple(result)
  

def get_dictionary_from_string(str):
    result = {}

    sub = str.partition('{')[2].rpartition('}')[0]
    tokens = sub.split(",")

    for tok in tokens:
        name = remove_quotes(tok.partition(':')[0])
        value = remove_quotes(tok.partition(':')[2])
        
        result[name] = value

    return result


def get_string_from_dictionary(dictionary, values=None):
    if values is None:
        values = dictionary
    
    result = '{'
    for i, k in enumerate(dictionary):
        result += "'"+k+"':'"+values[k]+"'"
        if i < len(dictionary)-1:
            result += ","
    
    result += '}'
    
    return result


def remove_quotes(str, quote='\''):
    return str.partition(quote)[2].rpartition(quote)[0]


def compatible_domain_functions(domain, function_name_list):
    return lambda x: x, lambda x: x, lambda x: x, lambda x: x

def get_timestamp_db_type():
    global checked_utimestamp
    global has_utimestamp

    if not checked_utimestamp:
        check_utimestamp()

    if has_utimestamp:
        return 'int64'
    else:
        # Trac 0.11
        return 'int'
    
def upload_file_to_subdir(env, req, subdir, param_name, target_filename):
    upload = param_name
    
    if isinstance(upload, unicode) or not upload.filename:
        raise TracError('You must provide a file.')
    
    txt_filename = upload.filename.replace('\\', '/').replace(':', '/')
    txt_filename = os.path.basename(txt_filename)
    if not txt_filename:
        raise TracError('You must provide a file.')
        
    target_dir = os.path.join(env.path, 'upload', subdir)
    
    if not os.access(target_dir, os.F_OK):
        os.makedirs(target_dir)
        
    target_path = os.path.join(target_dir, target_filename)
    
    try:
        target_file = open(target_path, 'w')
        shutil.copyfileobj(upload.file, target_file)
    finally:
        target_file.close()


def db_insert_or_ignore(env, tablename, propname, value):
    if db_get_config_property(env, tablename, propname) is None:
        db_set_config_property(env, tablename, propname, value)

def db_get_config_property(env, tablename, propname):
    try:
        db = get_db(env)
        cursor = db.cursor()
        sql = "SELECT value FROM %s WHERE propname=%%s" % tablename
        
        cursor.execute(sql, (propname,))
        row = cursor.fetchone()
        
        if not row or len(row) == 0:
            return None
            
        return row[0]
        
    except:
        env.log.error("Error getting configuration property '%s' from table '%s'" % (propname, tablename))
        env.log.error(formatExceptionInfo())
        
        return None

def db_set_config_property(env, tablename, propname, value):
    db, handle_ta = get_db_for_write(env)
    try:
        cursor = db.cursor()
        sql = "SELECT COUNT(*) FROM %s WHERE propname = %%s" % tablename
        cursor.execute(sql, (propname,))
        row = cursor.fetchone()
        if row is not None and int(row[0]) > 0:
            cursor.execute("""
                           UPDATE %s
                               SET value = %%s
                               WHERE propname = %%s 
                           """ % tablename, (str(value), propname))
        else:
            cursor.execute("""
                           INSERT INTO %s (propname,value)
                               VALUES (%%s,%%s)
                           """ % tablename, (propname, str(value)))
        if handle_ta:
            db.commit()

        return True

    except:
        env.log.error("Error setting configuration property '%s' to '%s' into table '%s'" % (propname, str(value), tablename))
        env.log.error(formatExceptionInfo())
        db.rollback()

    return False

def fix_base_location(req):
    return req.href('/').rstrip('/')

