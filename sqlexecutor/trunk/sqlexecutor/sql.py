# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi
#

import re
import sys
import time
import traceback

from genshi.builder import tag
from datetime import datetime

from trac.core import *
from trac.perm import IPermissionRequestor
from trac.util.text import CRLF
from trac.util.translation import _, N_, gettext
from trac.web.api import IRequestHandler
from trac.web.chrome import ITemplateProvider, INavigationContributor

from tracgenericclass.util import *


class SqlExecutor(Component):
    """SQL Executor."""

    implements(IPermissionRequestor, IRequestHandler, ITemplateProvider, INavigationContributor)
    
    # IPermissionRequestor methods
    def get_permission_actions(self):
        return ['SQL_RUN']

        
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        if 'SQL_RUN' in req.perm:
            return 'sqlexecutor'

    def get_navigation_items(self, req):
        if 'SQL_RUN' in req.perm:
            yield ('mainnav', 'sqlexecutor',
                tag.a(_("SQL Executor"), href=req.href+'/sqlexec', accesskey='Q'))


    # IRequestHandler methods

    def match_request(self, req):
        return (req.path_info.startswith('/sqlexec') and 'SQL_RUN' in req.perm)

    def process_request(self, req):
        """
        Executes a generic SQL.
        """

        req.perm.require('SQL_RUN')
        
        if req.path_info.startswith('/sqlexec'):
            sql = req.args.get('sql', '')
            result = []
            message = ""
            
            if not sql == '':
                self.env.log.debug(sql)

                try:
                    db = self.env.get_db_cnx()
                    cursor = db.cursor()
                    cursor.execute(sql)
                    
                    for row in cursor:
                        curr_row = []
                        for i in row:
                            if isinstance(i, basestring):
                                curr_row.append(i.encode('utf-8'))
                            elif isinstance(i, long):
                                curr_row.append(from_any_timestamp(i).isoformat() + ' (' + str(i) + ')')
                            else:
                                curr_row.append(str(i).encode('utf-8'))
                            
                        result.append(curr_row)

                    db.commit()
                    
                    message = "Query executed successfully."
                    
                    self.env.log.debug(result)
                except:
                    message = formatExceptionInfo()
                    db.rollback()
                    self.env.log.debug("SqlExecutor - Exception: ")
                    self.env.log.debug(message)

            data = {'sql': sql, 'result': result, 'message': message, 'baseurl': fix_base_location(req)}
            
            return 'result.html', data, None


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

       
