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
from trac.perm import IPermissionRequestor
from trac.util.translation import _, N_, gettext
from trac.web.api import IRequestHandler
from trac.web.chrome import ITemplateProvider

from tracgenericclass.util import *


class SqlExecutor(Component):
    """SQL Executor."""

    implements(IPermissionRequestor, IRequestHandler, ITemplateProvider)
    
    # IPermissionRequestor methods
    def get_permission_actions(self):
        return ['SQL_RUN']

        
    # IRequestHandler methods

    def match_request(self, req):
        return req.path_info.startswith('/sqlexec') and 'SQL_RUN' in req.perm

    def process_request(self, req):
        """
        Executes a generic SQL.
        """

        req.perm.require('SQL_RUN')
        
        sql = req.args.get('sql')
        self.env.log.debug(sql)

        try:
            db = self.env.get_db_cnx()
            cursor = db.cursor()
            cursor.execute(sql)
            
            result = ''
            for row in cursor:
                for i in row:
                    result += str(i) + ', '

            db.commit()
            
            self.env.log.debug(result)
        except:
            result = formatExceptionInfo()
            db.rollback()
            self.env.log.debug("SqlExecutor - Exception: ")
            self.env.log.debug(result)
        
        return 'result.html', {'result': result}, None


    # ITemplateProvider methods
    def get_templates_dirs(self):
        """
        Return the absolute path of the directory containing the provided
        Genshi templates.
        """
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        """Return the absolute path of a directory containing additional
        static resources (such as images, style sheets, etc).
        """
        from pkg_resources import resource_filename
        return [('sqlexecutor', resource_filename(__name__, 'htdocs'))]

       