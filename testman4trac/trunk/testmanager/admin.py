# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 Christian Masopust and Roberto Bordolanghi. 
# All rights reserved.
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

import re
import os.path
from operator import itemgetter

from trac.core import *
from trac.db import *
from trac.web.chrome import add_notice, add_warning, add_stylesheet
from trac.admin.web_ui import IAdminPanelProvider
from trac.wiki.formatter import format_to_html
from trac.mimeview.api import Context

from testmanager.api import *
from tracgenericclass.util import *
from testmanager.util import *

try:
    from testmanager.api import _, tag_, N_
except ImportError:
	from trac.util.translation import _, N_
	tag_ = _

class TestManagerAdmin(Component):
    """
    Provide the functionality to add, edit and create
    templates for TestCases and TestCatalogs
    """

    implements(IAdminPanelProvider)

    # IAdminPanelProvider methods:
    #
    def get_admin_panels(self, req):
        if req.perm.has_permission('TRAC_ADMIN'):
            yield('testmanager', 'Test Manager', 'settings', _("Settings"))
            yield('testmanager', 'Test Manager', 'templates', _("Templates"))

    def render_admin_panel(self, req, cat, page, component):
        if page == 'settings':
            return self._render_settings(req, cat, page, component)
        if page == 'templates':
            return self._render_templates(req, cat, page, component)


    def _render_settings(self, req, cat, page, component):
        req.perm.assert_permission('TRAC_ADMIN')

        data = {}

        try:
            if req.method == 'POST':
                default_days_back = req.args.get('default_days_back')
                default_interval = req.args.get('default_interval')
                testplan_sortby = req.args.get('testplan_sortby')
                open_new_window = req.args.get('open_new_window')

                self.env.config.set('testmanager', 'default_days_back', default_days_back)
                self.env.config.set('testmanager', 'default_interval', default_interval)
                self.env.config.set('testmanager', 'testplan.sortby', testplan_sortby)
                self.env.config.set('testmanager', 'testcase.open_new_window', ("False", "True")[open_new_window == "on"])

                self.env.config.save()
                add_notice(req, _("Settings saved"))
        except:
            self.env.log.error(formatExceptionInfo())
            add_warning(req, _("Error saving the settings"))

        data['default_days_back'] = self.env.config.get('testmanager', 'default_days_back')
        data['default_interval'] = self.env.config.get('testmanager', 'default_interval')
        data['testplan_sortby'] = self.env.config.get('testmanager', 'testplan.sortby')
        data['open_new_window'] = self.env.config.get('testmanager', 'testcase.open_new_window')

        return 'admin_settings.html', data

    def _render_templates(self, req, cat, page, component):
        req.perm.assert_permission('TRAC_ADMIN')

        for key, value in req.args.items():
            self.env.log.debug("Key: %s, Value: %s", key, value)

        testmanagersystem = TestManagerSystem(self.env)

        context = Context.from_request(req)

        data = {}

        data['template_overview'] = True
        data['edit_template'] = False

        data['tc_templates'] = testmanagersystem.get_templates(testmanagersystem.TEMPLATE_TYPE_TESTCASE)
        data['tcat_templates'] = testmanagersystem.get_templates(testmanagersystem.TEMPLATE_TYPE_TESTCATALOG)
        data['tcat_list'] = testmanagersystem.get_testcatalogs()
        data['tcat_selected'] = testmanagersystem.get_default_tcat_template_id()

        if req.method == 'POST':
            
            # add a Test Case template?
            if req.args.get('tc_add'):
                tc_name = req.args.get('tc_add_name')
                self.env.log.debug("Add new TC-template: %s" % tc_name)

                if len(tc_name) > 0:
                    if testmanagersystem.template_exists(tc_name, testmanagersystem.TEMPLATE_TYPE_TESTCASE):
                        data['tc_add_name'] = tc_name
                        add_warning(req, _("A Test Case template with that name already exists"))
                    else:
                        data['template_overview'] = False
                        data['edit_template'] = True
                        data['t_edit_type'] = testmanagersystem.TEMPLATE_TYPE_TESTCASE
                        data['t_edit_name'] = tc_name
                        data['t_edit_action'] = 'ADD'
                else:
                    add_warning(req, _("Please enter a Template name first"))

            # add a Test Catalog template?
            if req.args.get('tcat_add'):
                tcat_name = req.args.get('tcat_add_name')
                self.env.log.debug("Add new TCat-template: %s" % tcat_name)

                if len(tcat_name) > 0:
                    if testmanagersystem.template_exists(tcat_name, testmanagersystem.TEMPLATE_TYPE_TESTCATALOG):
                        data['tcat_add_name'] = tcat_name
                        add_warning(req, _("A Test Catalog template with that name already exists"))
                    else:
                        data['template_overview'] = False
                        data['edit_template'] = True
                        data['t_edit_type'] = testmanagersystem.TEMPLATE_TYPE_TESTCATALOG
                        data['t_edit_name'] = tcat_name
                        data['t_edit_action'] = 'ADD'
                else:
                    add_warning(req, _("Please enter a Template name first"))

            # delete a Test Case template?
            if req.args.get('tc_del'):
                tc_sel = req.args.get('tc_sel')
                for t_id in tc_sel:
                    t = testmanagersystem.get_template_by_id(t_id)
                    if testmanagersystem.template_in_use(t_id):
                        add_warning(req, _("Template '%s' not removed as it is in use for a Test Catalog") % t['name'])
                        continue
                    
                    self.env.log.debug("remove test case template with id: " + t_id)
                    if not testmanagersystem.remove_template(t_id):
                        add_warning(req, _("Error deleting Test Case template '%s'") % t['name'])
                    else:
                        add_notice(req, _("Test Case template '%s' deleted") % t['name'])
                    
                data['tc_templates'] = testmanagersystem.get_templates(testmanagersystem.TEMPLATE_TYPE_TESTCASE)
                data['tcat_templates'] = testmanagersystem.get_templates(testmanagersystem.TEMPLATE_TYPE_TESTCATALOG)

            # delete a Test Catalog template?
            if req.args.get('tcat_del'):
                tcat_sel = req.args.get('tcat_sel')
                tcat_default = testmanagersystem.get_default_tcat_template_id()
                for t_id in tcat_sel:
                    t = testmanagersystem.get_template_by_id(t_id)
                    if t_id == tcat_default:
                        add_warning(req, _("Template '%s' not removed as it is currently the default template") % t['name'])
                        continue
                    
                    self.env.log.debug("remove test catalog template with id: " + t_id)
                    if not testmanagersystem.remove_template(t_id):
                        add_warning(req, _("Error deleting Test Catalog template '%s'") % t['name'])
                    else:
                        add_notice(req, _("Test Catalog template '%s' deleted") % t['name'])
                        
                data['tc_templates'] = testmanagersystem.get_templates(testmanagersystem.TEMPLATE_TYPE_TESTCASE)
                data['tcat_templates'] = testmanagersystem.get_templates(testmanagersystem.TEMPLATE_TYPE_TESTCATALOG)

            # save default Test Catalog template
            if req.args.get('tcat_default_save'):
                tcat_default = req.args.get('tcat_default')
                if testmanagersystem.set_config_property('TEST_CATALOG_DEFAULT_TEMPLATE', tcat_default):
                    add_notice(req, _("Default Test Catalog template updated"))
                    data['tcat_selected'] = tcat_default
                else:
                    add_warning(req, _("Failed to update default Test Catalog template"))

            # save templates for TestCatalogs
            if req.args.get('tc_templates_save'):
                warning = False
                for key, value in req.args.items():
                    self.env.log.debug("checking key: " + key)
                    if 'TC_TEMPLATE_FOR_TCAT_' in key:
                        self.env.log.debug("saving tc-template for: %s, value: %s" % (key, value))
                        if not testmanagersystem.set_config_property(key, value):
                            warning = True
                if warning:
                    add_warning(req, _("Failed to update Test Case templates"))
                else:
                    add_notice(req, _("Default Test Case templates updated"))
                    data['tcat_list'] = testmanagersystem.get_testcatalogs()

            # preview template
            if req.args.get('t_edit_preview'):
                data['template_overview'] = False
                data['edit_template'] = True
                data['t_edit_id'] = req.args.get('t_edit_id')
                data['t_edit_type'] = req.args.get('t_edit_type')
                data['t_edit_name'] = req.args.get('t_edit_name')
                data['t_edit_description'] = req.args.get('t_edit_description')
                data['t_edit_content'] = req.args.get('t_edit_content')
                data['t_edit_action'] = req.args.get('t_edit_action')
                data['t_show_preview'] = True
                data['t_preview_content'] = format_to_html(self.env, context, req.args.get('t_edit_content'))

            # save an edited template?
            if req.args.get('t_edit_save'):
                t_id = req.args.get('t_edit_id')
                t_type = req.args.get('t_edit_type')
                t_name = req.args.get('t_edit_name')
                t_desc = req.args.get('t_edit_description')
                t_cont = req.args.get('t_edit_content')
                t_action = req.args.get('t_edit_action')

                testmanagersystem.save_template(t_id, t_name, t_type, t_desc, t_cont, t_action)

                data['template_overview'] = True
                data['edit_template'] = False
                data['tc_templates'] = testmanagersystem.get_templates(testmanagersystem.TEMPLATE_TYPE_TESTCASE)
                data['tcat_templates'] = testmanagersystem.get_templates(testmanagersystem.TEMPLATE_TYPE_TESTCATALOG)
                add_notice(req, _("Template saved"))

        else:
            # method 'GET' (template selected for 'edit')
            if component:
                t_type = req.args.get('t_type')
                t_id = component
                self.env.log.debug("component: " + component)
                template = testmanagersystem.get_template_by_id(t_id)

                data['t_edit_id'] = template['id']
                data['t_edit_type'] = template['type']
                data['t_edit_name'] = template['name']
                data['t_edit_description'] = template['description']
                data['t_edit_content'] = template['content']
                data['t_edit_action'] = 'EDIT'

                data['template_overview'] = False
                data['edit_template'] = True

        add_stylesheet(req, 'common/css/wiki.css')
        add_stylesheet(req, 'testmanager/css/admin.css')
        return 'admin_templates.html', data
