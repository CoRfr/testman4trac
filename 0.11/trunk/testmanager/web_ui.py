# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi, Marco Cipriani
#

import re
import math
from trac.core import *
from trac.web.chrome import ITemplateProvider, INavigationContributor, \
                            add_stylesheet, add_script, add_ctxtnav
from genshi.builder import tag
from trac.util import to_unicode
from trac.util.text import CRLF
from trac.util.compat import sorted, set, any
from trac.resource import Resource
from trac.mimeview import Context
from trac.wiki.formatter import Formatter
from trac.wiki.model import WikiPage

from testmanager.api import TestManagerSystem
from testmanager.labels import *

class TestManagerTemplateProvider(Component):
    """Provides templates and static resources for the TestManager plugin."""

    implements(ITemplateProvider)

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
        return [('testmanager', resource_filename(__name__, 'htdocs'))]


class TestManager(Component):
    """Implements the /testmanager handler and the Test Manager tab."""

    implements(INavigationContributor)

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        if 'TEST_VIEW' in req.perm:
            return 'testmanager'

    def get_navigation_items(self, req):
        if 'TEST_VIEW' in req.perm:
            yield ('mainnav', 'testmanager',
                tag.a(LABELS['main_tab_title'], href=req.href.wiki()+'/TC', accesskey='M'))

