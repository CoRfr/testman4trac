# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi
#

import re
import sys
import time
import traceback

from datetime import datetime
from trac.core import *
from trac.perm import IPermissionRequestor, PermissionError
from trac.util.translation import _, N_, gettext
from trac.web.api import IRequestHandler


class SqlExecutor(Component):
    """SQL Executor."""

    implements(IPermissionRequestor, IRequestHandler)
    
    # IPermissionRequestor methods
    def get_permission_actions(self):
        return ['SQL_RUN']

        
    # IRequestHandler methods

    def match_request(self, req):
        return req.path_info.startswith('/sqlexec') and 'SQL_RUN' in req.perm

    def process_request(self, req):
        """Executes a generic SQL."""

        req.perm.require('SQL_RUN')
        
        sql = req.args.get('sql')
        print (sql)

        try:
            db = self.env.get_db_cnx()
            cursor = db.cursor()
            cursor.execute(sql)
            
            result = ''
            for row in cursor:
                for i in row:
                    result += str(i) + ', '

            db.commit()
            
            print(result)
        except:
            result = self._formatExceptionInfo()
            db.rollback()
            print("SqlExecutor - Exception: ")
            print(result)
            
        
        return 'result.html', {'result': result}, None

        
    def _formatExceptionInfo(maxTBlevel=5):
        cla, exc, trbk = sys.exc_info()
        excName = cla.__name__
        
        try:
            excArgs = exc.__dict__["args"]
        except KeyError:
            excArgs = "<no args>"
        
        excTb = traceback.format_tb(trbk, maxTBlevel)
        return (excName, excArgs, excTb)
 
