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
from trac.util.text import CRLF
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

        strdata = """
            <html>
              <body>
                <p>Result:</p>
                <br />
                <div id="response">
                    <table><tbody>
            """
    
        try:
            db = self.env.get_db_cnx()
            cursor = db.cursor()
            cursor.execute(sql)
            
            for row in cursor:
                strdata += '<tr>'
                for i in row:
                    strdata += '<td>'
                    if isinstance(i, basestring):
                        strdata += i.encode('utf-8')
                    elif isinstance(i, long):
                        strdata += from_any_timestamp(i).isoformat() + ' (' + str(i) + ')'
                    else:
                        strdata += str(i).encode('utf-8')
                    strdata += '<td>'

                strdata += '<tr>'

            db.commit()
            
            self.env.log.debug(strdata)
        except:
            strdata = formatExceptionInfo()
            db.rollback()
            self.env.log.debug("SqlExecutor - Exception: ")
            self.env.log.debug(strdata)

        strdata += """
                    </tbody></table>
                </div>
              </body>
            </html>
            """
        
        req.send_header("Content-Length", len(strdata))
        req.write(strdata)
        
        #return 'result.html', {'result': result}, None
        return


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

       
