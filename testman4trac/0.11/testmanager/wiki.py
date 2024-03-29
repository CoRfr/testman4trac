# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2012 Roberto Longobardi
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

from operator import itemgetter
from StringIO import StringIO

from trac.core import *
from trac.mimeview.api import Context
from trac.resource import Resource
from trac.util import format_datetime, format_date
from trac.web.api import ITemplateStreamFilter
from trac.web.chrome import add_stylesheet, add_script, ITemplateProvider
from trac.wiki.api import WikiSystem, IWikiChangeListener
from trac.wiki.formatter import Formatter
from trac.wiki.model import WikiPage
from trac.wiki.parser import WikiParser

from genshi import HTML
from genshi.builder import tag
from genshi.filters.transform import Transformer

from tracgenericclass.model import GenericClassModelProvider
from tracgenericclass.util import *

from testmanager.util import *
from testmanager.admin import get_all_table_columns_for_object
from testmanager.api import TestManagerSystem
from testmanager.model import TestCatalog, TestCase, TestCaseInPlan, TestPlan, TestManagerModelProvider

try:
    from testmanager.api import _, tag_, N_
except ImportError:
	from trac.util.translation import _, N_
	tag_ = _

class WikiTestManagerInterface(Component):
    """Implement generic template provider."""
    
    implements(ITemplateStreamFilter, IWikiChangeListener)
    
    _config_properties = {}
    sortby = 'name'
    open_new_window = False
    
    def __init__(self, *args, **kwargs):
        """
        Parses the configuration file for the section 'testmanager'.
        
        Available properties are:
        
          testplan.sortby = {modification_time|name}    (default is name)
          testcase.open_new_window = {True|False}       (default is False)
        """
        
        Component.__init__(self, *args, **kwargs)

        self._parse_config_options()

    
    def _parse_config_options(self):
        if 'testmanager' in self.config:
            self.sortby = self.config.get('testmanager', 'testplan.sortby', 'name')
            self.open_new_window = self.config.get('testmanager', 'testcase.open_new_window', '') == 'True'
                        
    # IWikiChangeListener methods
    def wiki_page_added(self, page):
        """Called whenever a new Wiki page is added."""
        #page_on_db = WikiPage(self.env, page.name)
        pass

    def wiki_page_changed(self, page, version, t, comment, author, ipnr):
        """Called when a page has been modified."""
        pass

    def wiki_page_deleted(self, page):
        """Called when a page has been deleted."""
        if page.name.find('_TC') >= 0:
            # Delete test case
            tc_id = page.name.rpartition('_TC')[2]
            self.env.log.debug("Deleting Test case with id '%s" % tc_id)
            tc = TestCase(self.env, tc_id)
            if tc.exists:
                tc.delete(del_wiki_page=False)
            else:
                self.env.log.debug("Test case with id '%s' not found" % tc_id)
        
        elif page.name.find('_TT') >= 0:
            # Delete test catalog and all its contained test cases
            tcat_id = page.name.rpartition('_TT')[2]
            self.env.log.debug("Deleting Test catalog with id '%s" % tcat_id)
            tcat = TestCatalog(self.env, tcat_id)
            if tcat.exists:
                tcat.delete(del_wiki_page=False)
            else:
                self.env.log.debug("Test catalog with id '%s' not found" % tcat_id)

    def wiki_page_version_deleted(self, page):
        """Called when a version of a page has been deleted."""
        
        # TODO Maybe should look into all test plans with "snapshot" test case versions and handle this deletion in some way?
        pass

    def wiki_page_renamed(self, page, old_name): 
        """Called when a page has been renamed.""" 
        
        if page.name.find('TC_') == 0:
            raise TracError(_("You cannot rename Test Catalog, Test Case or Test Plan wiki pages this way. If you wish to modify the TITLE of the object, just Edit the page and change the text between '==' and '=='. If you wish to move the object elsewhere, instead, use the 'move' Test Manager functions."))
        
    # ITemplateStreamFilter methods
    def filter_stream(self, req, method, filename, stream, data):
        self._parse_config_options()

        page_name = req.args.get('page', 'WikiStart')
        planid = req.args.get('planid', '-1')
        delete_version = req.args.get('delete_version', '')
        version = req.args.get('version', '')

        formatter = Formatter(
            self.env, Context.from_request(req, Resource('testmanager'))
            )
        
        if page_name.startswith('TC'):
            req.perm.require('TEST_VIEW')
            
            if page_name.find('_TC') >= 0:
                if filename == 'wiki_view.html':
                    if not planid or planid == '-1':
                        return self._testcase_wiki_view(req, formatter, planid, page_name, stream)
                    else:
                        return self._testcase_in_plan_wiki_view(req, formatter, planid, page_name, stream)
            elif page_name == 'TC' or page_name.find('_TT') >= 0:
                if filename == 'wiki_view.html':
                    if not planid or planid == '-1':
                        return self._catalog_wiki_view(req, formatter, page_name, stream)
                    else:
                        return self._testplan_wiki_view(req, formatter, page_name, planid, stream)
                elif filename == 'wiki_delete.html':
                    if not planid or planid == '-1':
                        if not delete_version or delete_version == '' or version == '1':
                            return self._catalog_wiki_delete(req, formatter, page_name, stream)
                    else:
                        raise TracError(_("You cannot delete a Test Plan this way. Expand the Test Plans list under the corrisponding Catalog and use the X buttons to delete the Test Plans."))

        return stream

        
    # Internal methods

    def _catalog_wiki_delete(self, req, formatter, page_name, stream):
        if page_name == 'TC':
            raise TracError(_("You cannot delete the root catalogs list."))

        return stream | Transformer('//input[contains(@value, "delete")]').after(tag.div()(
            tag.br(),
            tag.p(style='font-size: 150%;font-weight: bold;')(
                    _("Deleting this Test Catalog will delete all the contained Test Catalogs, Test Cases, Test Plans and the status history of them.")
                    )
            ))


    def _catalog_wiki_view(self, req, formatter, page_name, stream):
        path_name = req.path_info
        cat_name = path_name.rpartition('/')[2]
        cat_id = cat_name.rpartition('TT')[2]

        mode = req.args.get('mode', self.env.config.get('testmanager', 'testcatalog.default_view', 'tree'))
        fulldetails = req.args.get('fulldetails', 'False')
        
        table_columns = None
        table_columns_map = None
        custom_ctx = None
        if mode == 'tree_table':
            table_columns, table_columns_map, custom_ctx = get_all_table_columns_for_object(self.env, 'testcatalog', self.env.config)
        
        tmmodelprovider = GenericClassModelProvider(self.env)
        test_catalog = TestCatalog(self.env, cat_id, page_name)

        if 'TEST_PLAN_ADMIN' in req.perm:
            show_delete_button = True
        else:
            show_delete_button = False
        
        if page_name == 'TC':
            # Root of all catalogs
            insert1 = tag.div()(
                        tag.div(id='pasteMultipleTCsHereMessage', class_='messageBox', style='display: none;')(_("Select the catalog into which to paste the Test Cases and click on 'Paste the copied Test Cases here'. "),
                            tag.a(href='javascript:void(0);', onclick='cancelTCsCopy()')(_("Cancel"))
                            ),
                        tag.div(id='pasteTCHereMessage', class_='messageBox', style='display: none;')(_("Select the catalog into which to paste the Test Case and click on 'Move the copied Test Case here'. "),
                            tag.a(href='javascript:void(0);', onclick='cancelTCMove()')(_("Cancel"))
                            ),
                        tag.h1(_("Test Catalogs List")),
                        tag.br(), tag.br()
                        )
            fieldLabel = _("New Catalog:")
            buttonLabel = _("Add a Catalog")
        else:
            insert1 = tag.div()(
                        self._get_breadcrumb_markup(formatter, None, page_name, mode, fulldetails),
                        tag.div(style='border: 1px, solid, gray; padding: 1px;')(
                            self._get_switch_view_icon_markup(req, page_name, mode, fulldetails)
                            ),
                        tag.br(), 
                        tag.div(id='pasteMultipleTCsHereMessage', class_='messageBox', style='display: none;')(
                            _("Select the catalog (even this one) into which to paste the Test Cases and click on 'Paste the copied Test Cases here'. "),
                            tag.a(href='javascript:void(0);', onclick='cancelTCsCopy()')(_("Cancel"))
                            ),
                        tag.div(id='pasteTCHereMessage', class_='messageBox', style='display: none;')(
                            _("Select the catalog (even this one) into which to paste the Test Case and click on 'Move the copied Test Case here'. "),
                            tag.a(href='javascript:void(0);', onclick='cancelTCMove()')(_("Cancel"))
                            ),
                        tag.br(),
                        tag.h1(_("Test Catalog"))
                        )
            fieldLabel = _("New Sub-Catalog:")
            buttonLabel = _("Add a Sub-Catalog")

        insert2 = tag.div()(
                    HTML(self._build_catalog_tree(formatter.context, page_name, mode, fulldetails, table_columns, table_columns_map, custom_ctx)),
                    tag.div(class_='testCaseList')(
                        tag.br(), tag.br()
                    ))

        if not page_name == 'TC':
            # The root of all catalogs cannot contain itself test cases
            insert2.append(tag.div()(
                        self._get_custom_fields_markup(test_catalog, tmmodelprovider.get_custom_fields_for_realm('testcatalog')),
                        tag.br()
                    ))

        insert2.append(tag.div(class_='field')(
                    tag.br(), tag.br(), tag.br(),
                    tag.label(
                        fieldLabel,
                        tag.span(id='catErrorMsgSpan', style='color: red;'),
                        tag.br(),
                        tag.input(id='catName', type='text', name='catName', size='50'),
                        tag.input(type='button', value=buttonLabel, onclick='creaTestCatalog("'+cat_name+'")')
                        )
                    ))

        if not page_name == 'TC':
            # The root of all catalogs cannot contain itself test cases,
            #   cannot generate test plans and does not need a test plans list
            insert2.append(tag.div(class_='field')(
                        tag.label(
                            _("New Test Case:"),
                            tag.span(id='errorMsgSpan', style='color: red;'),
                            tag.br(),
                            tag.input(id='tcName', type='text', name='tcName', size='50'),
                            tag.input(type='button', value=_("Add a Test Case"), onclick='creaTestCase("'+cat_name+'")')
                            ),
                        tag.br(), 
                        tag.label(
                            _("New Test Plan:"),
                            tag.span(id='errorMsgSpan2', style='color: red;'),
                            tag.br(),
                            tag.input(id='planName', type='text', name='planName', size='50'),
                            tag.input(type='button', value=_("Generate a new Test Plan"), onclick='creaTestPlan("'+cat_name+'")')
                            ),
                        tag.br(), 
                        ))
            insert2.append(HTML(self._get_testplan_dialog_markup(req, cat_name)))
                    
        insert2.append(tag.br())
        insert2.append(tag.br())
                    
        insert2.append(tag.input(
                type='button', id='showSelectionBoxesButton', value=_("Select Multiple Test Cases"), onclick='showSelectionCheckboxes()')
                )
        insert2.append(tag.input(
                type='button', id='copyMultipleTCsButton', value=_("Copy the Selected Test Cases"), onclick='copyMultipleTestCasesToClipboard()')
                )
                    
        if not page_name == 'TC':
            insert2.append(tag.input(type='button', id='pasteMultipleTCsHereButton', value=_("Paste the copied Test Cases here"), onclick='pasteMultipleTestCasesIntoCatalog("'+cat_name+'")')
                    )

            insert2.append(tag.input(type='button', id='pasteTCHereButton', value=_("Move the copied Test Case here"), onclick='pasteTestCaseIntoCatalog("'+cat_name+'")')
                    )

            insert2.append(HTML(self._get_import_dialog_markup(req, cat_name)))
            insert2.append(tag.input(type='button', id='importTestCasesButton', value=_("Import Test Cases"), onclick='importTestCasesIntoCatalog("'+cat_name+'")')
                    )
            insert2.append(HTML(self._get_export_dialog_markup(req, cat_name, '-1', 'testcatalog')))
            insert2.append(tag.input(type='button', id='exportTestCasesButton', value=_("Export Test Catalog"), onclick='exportTestCasesFromCatalog("'+cat_name+'")')
                    )

            insert2.append(tag.div(class_='field')(
                self._build_testplan_list(cat_name, mode, fulldetails, show_delete_button)
                ))

            insert2.append(tag.div(class_='field')(
                self._get_object_change_history_markup(test_catalog)
                ))

        insert2.append(tag.div()(tag.br(), tag.br(), tag.br(), tag.br()))

        if not page_name == 'TC':        
            insert3 = tag.div(id='new_delete')(
                tag.input(type='submit', value=_("Delete this version"), name='delete_version'),
                tag.input(type='submit', value=_("Delete Test Catalog"))
                )
        else:
            insert3 = HTML('')
        
        common_code = self._write_common_code(req)
        
        stream = stream | Transformer('//div[contains(@id, "delete")]').wrap(tag.div(id='old_delete', style='display: none;'))
        stream = stream | Transformer('//div[contains(@id, "old_delete")]').after(insert3)
        
        return stream | Transformer('//body').append(common_code) | Transformer('//div[contains(@class,"wikipage")]').after(insert2) | Transformer('//div[contains(@class,"wikipage")]').before(insert1)

        
    def _testplan_wiki_view(self, req, formatter, page_name, planid, stream):
        path_name = req.path_info
        cat_name = path_name.rpartition('/')[2]
        cat_id = cat_name.rpartition('TT')[2]
        
        mode = req.args.get('mode', self.env.config.get('testmanager', 'testplan.default_view', 'tree'))
        fulldetails = req.args.get('fulldetails', 'False')

        table_columns = None
        table_columns_map = None
        custom_ctx = None
        if mode == 'tree_table':
            table_columns, table_columns_map, custom_ctx = get_all_table_columns_for_object(self.env, 'testplan', self.env.config)
            
        tmmodelprovider = GenericClassModelProvider(self.env)
        test_plan = TestPlan(self.env, planid, cat_id, page_name)
        
        tp = TestPlan(self.env, planid)
        
        insert1 = tag.div()(
                    tag.a(href=req.href.wiki(page_name))(_("Back to the Catalog")),
                    tag.div(style='border: 1px, solid, gray; padding: 1px;')(
                        self._get_switch_view_icon_markup(req, page_name, mode, fulldetails, planid)
                        ),
                    tag.br(), 
                    tag.h1(_("Test Plan: ")+tp['name']),
                    tag.div(class_='testArtifactPropertiesDiv')(
                        HTML(self._get_testplan_properties_markup(planid, cat_id, page_name))
                        ),
                    )

        insert2 = tag.div()(
                    HTML(self._build_testplan_tree(formatter.context, str(planid), page_name, mode, self.sortby, table_columns, table_columns_map, custom_ctx)),
                    tag.div(class_='testCaseList')(
                    tag.br(),
                    self._get_custom_fields_markup(test_plan, tmmodelprovider.get_custom_fields_for_realm('testplan')),
                    tag.br(),
                    HTML(self._get_export_dialog_markup(req, cat_name, planid, 'testplan')),
                    tag.input(type='button', id='exportTestCasesButton', value=_("Export Test Plan"), onclick='exportTestCasesFromCatalog("'+cat_name+'")'),
                    tag.br(),
                    ),
                    tag.div(class_='field')(
                        self._get_object_change_history_markup(test_plan)
                        ),
                    tag.br(), tag.br(), tag.br(), tag.br()
                    )
                            
        common_code = self._write_common_code(req, True)
        
        stream = stream | Transformer('//div[contains(@id, "delete")]').append(tag.input(name='planid', type='hidden', value='%s' % planid))
        
        return stream | Transformer('//body').append(common_code) | Transformer('//div[contains(@class,"wikipage")]').after(insert2) | Transformer('//div[contains(@class,"wikipage")]').before(insert1)
        
    def _get_testplan_properties_markup(self, planid, catid, page_name):
        tp = TestPlan(self.env, planid, catid, page_name)
        
        result = u''
        result += _("Author")+': '+html_escape(tp['author'])+'<br />'
        result += _("Created")+': '+format_datetime(tp['time'])+'<br />'
        result += _("Contained Test Cases")+': '+(_("Contains selected Test Cases"), _("Contains all Test Cases"))[tp['contains_all']]+'<br />'
        result += _("Test Case Versions")+': '+(_("Points to latest Test Case versions"), _("Contains a snapshot of Test Case versions"))[tp['freeze_tc_versions']]
        
        return result

    def _get_switch_view_icon_markup(self, req, page_name, mode='tree', fulldetails='False', planid='-1'):
        if mode == 'tree':
            return tag.span()(
                tag.a(href=req.href.wiki(page_name, mode='tree_table', fulldetails=fulldetails, planid=planid))(
                    tag.img(src='../chrome/testmanager/images/tree_table.png', title=_("Switch to Tabular View"), alt=_("Switch to Tabular View")))
                )
        else:
            return tag.span()(
                tag.a(href=req.href.wiki(page_name, mode='tree', fulldetails=fulldetails, planid=planid))(
                    tag.img(src='../chrome/testmanager/images/tree.png', title=_("Switch to Tree View"), alt=_("Switch to Tree View")))
                )
        
    def _testcase_wiki_view(self, req, formatter, planid, page_name, stream):
        tc_name = page_name
        cat_name = page_name.partition('_TC')[0]
        cat_id = cat_name.rpartition('_TT')[2]
        
        mode = req.args.get('mode', 'tree')
        fulldetails = req.args.get('fulldetails', 'False')
        is_edit = req.args.get('edit_custom', 'false')
        
        has_status = False
        plan_name = u''
    
        tc_id = tc_name.partition('_TC')[2]
        test_case = TestCase(self.env, tc_id, tc_name)
        summary = test_case.title

        tcat = TestCatalog(self.env, cat_id)
        
        tmmodelprovider = GenericClassModelProvider(self.env)
        
        insert1 = tag.div()(
                    self._get_breadcrumb_markup(formatter, planid, page_name, mode, fulldetails),
                    tag.br(),
                    tag.div(id='copiedMultipleTCsMessage', class_='messageBox', style='display: none;')(
                        _("The Test Cases have been copied. Now select the catalog into which to paste the Test Cases and click on 'Paste the copied Test Cases here'.  "),
                        tag.a(href='javascript:void(0);', onclick='cancelTCsCopy()')(_("Cancel"))
                        ),
                    tag.br(),
                    tag.div(id='copiedTCMessage', class_='messageBox', style='display: none;')(
                        _("The Test Case has been cut. Now select the catalog into which to move the Test Case and click on 'Move the copied Test Case here'. "),
                        tag.a(href='javascript:void(0);', onclick='cancelTCMove()')(_("Cancel"))
                        ),
                    tag.br(),
                    tag.span(style='font-size: large; font-weight: bold;')(
                        tag.span()(
                            _("Test Case")
                            )
                        )
                    )
        
        insert2 = tag.div(class_='field', style='marging-top: 60px;')(
                    tag.br(), tag.br(), 
                    self._get_custom_fields_markup(test_case, tmmodelprovider.get_custom_fields_for_realm('testcase')),
                    tag.br(),
                    tag.input(type='button', value=_("Open a Ticket on this Test Case"), onclick='creaTicket("'+tc_name+'", "", "", "'+summary+'")'),
                    HTML('&nbsp;&nbsp;'), 
                    tag.input(type='button', value=_("Show Related Tickets"), onclick='showTickets("'+tc_name+'", "", "")'),
                    HTML('&nbsp;&nbsp;'), 
                    tag.input(type='button', id='moveTCButton', value=_("Move the Test Case into another catalog"), onclick='copyTestCaseToClipboard("'+tc_name+'")'),
                    HTML('&nbsp;&nbsp;'), 
                    tag.input(type='button', id='duplicateTCButton', value=_("Duplicate the Test Case"), onclick='duplicateTestCase("'+tc_name+'", "'+cat_name+'")'),
                    HTML('&nbsp;&nbsp;'), 
                    tag.input(type='button', id='addToTestPlanTCButton', value=_("Add to a Test Plan"), onclick='addTestCaseToTestplanDialog("'+tc_name+'")'),
                    tag.div(class_='field')(
                        self._get_object_change_history_markup(test_case)
                        ),
                    tag.br(), tag.br(), tag.br(), tag.br()
                    )

        insert2.append(HTML(self._get_select_testplan_dialog_markup(req, test_case, tcat)))
                    
        common_code = self._write_common_code(req)
        
        return stream | Transformer('//body').append(common_code) | Transformer('//div[contains(@class,"wikipage")]').after(insert2) | Transformer('//div[contains(@class,"wikipage")]').before(insert1)

    def _testcase_in_plan_wiki_view(self, req, formatter, planid, page_name, stream):
        tc_name = page_name
        cat_name = page_name.partition('_TC')[0]
        
        mode = req.args.get('mode', 'tree')
        fulldetails = req.args.get('fulldetails', 'False')

        has_status = True
        tp = TestPlan(self.env, planid)
        plan_name = tp['name']
    
        tc_id = tc_name.partition('_TC')[2]
        # Note that assigning a default status here is functional. If the tcip actually exists,
        # the real status will override this value.
        tcip = TestCaseInPlan(self.env, tc_id, planid, tc_name, -1, TestManagerSystem(self.env).get_default_tc_status())
        test_case = TestCase(self.env, tc_id, tc_name)
        summary = test_case.title
        
        tmmodelprovider = GenericClassModelProvider(self.env)

        tc_statuses_by_color = TestManagerSystem(self.env).get_tc_statuses_by_color()
        need_menu = False
        for color in ['green', 'yellow', 'red']:
            if len(tc_statuses_by_color[color]) > 1:
                need_menu = True
        
        add_stylesheet(req, 'testmanager/css/menu.css')
        
        insert1 = tag.div()(
                    self._get_breadcrumb_markup(formatter, planid, page_name, mode, fulldetails),
                    tag.br(), tag.br(), tag.br(), 
                    tag.span(style='font-size: large; font-weight: bold;')(
                        self._get_testcase_status_markup(formatter, has_status, page_name, planid),
                        tag.span()(                            
                            _("Test Case")
                            )
                        )
                    )
        
        insert2 = tag.div(class_='field', style='marging-top: 60px;')(
                    tag.br(), tag.br(),
                    self._get_custom_fields_markup(tcip, tmmodelprovider.get_custom_fields_for_realm('testcaseinplan'), ('page_name', 'status')),
                    tag.br(), 
                    self._get_testcase_change_status_markup(formatter, has_status, page_name, planid),
                    tag.br(), tag.br(),
                    self._get_update_to_latest_version_markup(tp, tc_name, planid),
                    tag.input(type='button', value=_("Open a Ticket on this Test Case"), onclick='creaTicket("'+tc_name+'", "'+planid+'", "'+plan_name+'", "'+summary+'")'),
                    HTML('&nbsp;&nbsp;'), 
                    tag.input(type='button', value=_("Show Related Tickets"), onclick='showTickets("'+tc_name+'", "'+planid+'", "'+plan_name+'")'),
                    HTML('&nbsp;&nbsp;'), 
                    self._get_remove_from_tp_markup(tp, tc_name, planid),
                    tag.br(), tag.br(), 
                    self._get_testcase_status_history_markup(formatter, has_status, page_name, planid),
                    self._get_object_change_history_markup(tcip, ['status']),
                    tag.br(), tag.br(), tag.br(), tag.br()
                    )
                    
        common_code = self._write_common_code(req, False, need_menu)
        
        return stream | Transformer('//body').append(common_code) | Transformer('//div[contains(@class,"wikipage")]').after(insert2) | Transformer('//div[contains(@class,"wikipage")]').before(insert1)

    def _get_update_to_latest_version_markup(self, tp, tc_name, planid):
        if tp['freeze_tc_versions']:
            return tag.input(type='button', value=_("Update to latest version of Test Case"), onclick='updateTestCase("'+tc_name+'", "'+planid+'")'), HTML('&nbsp;&nbsp;')
        else:
            return HTML('')
        
    def _get_remove_from_tp_markup(self, tp, tc_name, planid):
        if not tp['contains_all']:
            return tag.input(type='button', value=_("Remove from the Test Plan"), onclick='removeTestCase("'+tc_name+'", "'+planid+'")'), HTML('&nbsp;&nbsp;')
        else:
            return HTML('')
    
    def _get_breadcrumb_markup(self, formatter, planid, page_name, mode='tree', fulldetails='False'):
        if planid and not planid == '-1':
            # We are in the context of a test plan
            if not page_name.rpartition('_TC')[2] == '':
                # It's a test case in plan
                tp = TestPlan(self.env, planid)
                catpath = tp['page_name']
                result = tag.span()(
                    tag.a(href=formatter.req.href.wiki(catpath, planid=planid, mode=mode, fulldetails=fulldetails))(_("Back to the Test Plan")),
                    HTML(self._build_testcases_breadcrumb(page_name, planid, mode, (fulldetails == 'True')))
                )
                
                return result
            else:
                # It's a test plan
                return tag.a(href=formatter.req.href.wiki(page_name))(_("Back to the Catalog"))
                
        else:
            # It's a test catalog or test case description
            return HTML(self._build_testcases_breadcrumb(page_name, '-1', mode, (fulldetails == 'True')))

    def _get_testcase_status_markup(self, formatter, has_status, page_name, planid):
        if has_status:
            return tag.span(style='float: left; padding-top: 4px; padding-right: 5px;')(
                            HTML(self._build_testcase_status(planid, page_name))
                            )
        else:
            return tag.span()()

    def _get_testcase_change_status_markup(self, formatter, has_status, page_name, planid):
        if has_status:
            return HTML(self._build_testcase_change_status(planid, page_name))
        else:
            return tag.span()()
            
    def _get_testcase_status_history_markup(self, formatter, has_status, page_name, planid):
        if has_status:
            return HTML(self._build_testcase_status_history(planid, page_name))
        else:
            return tag.span()()

    def _get_custom_fields_markup(self, obj, fields, props=None):
        obj_key = obj.gey_key_string()

        obj_props = ''
        if props is not None:
            obj_props = obj.get_values_as_string(props)
        
        result = u'<input type="hidden" value="' + obj_key + '" id="obj_key_field"></input>'
        result += '<input type="hidden" value="' + obj_props + '" id="obj_props_field"></input>'
        
        result += '<table><tbody>'
        
        for f in fields:
            result += "<tr onmouseover='showPencil(\"field_pencilIcon"+f['name']+"\", true)' onmouseout='hidePencil(\"field_pencilIcon"+f['name']+"\", false)'>"
            
            if f['type'] == 'text':
                result += '<td><label for="custom_field_'+f['name']+'">'+f['label']+':</label></td>'
                
                result += '<td>'
                result += '<span id="custom_field_value_'+f['name']+'" name="custom_field_value_'+f['name']+'">'
                if obj[f['name']] is not None:
                    result += obj[f['name']]
                result += '</span>'
            
                result += '<input style="display: none;" type="text" id="custom_field_'+f['name']+'" name="custom_field_'+f['name']+'" '
                if obj[f['name']] is not None:
                    result += ' value="' + obj[f['name']] + '" '
                result += '></input>'
                result += '</td>'

                result += '<td>'
                result += '<span class="rightIcon" style="display: none;" title="'+_("Edit")+'" onclick="editField(\''+f['name']+'\')" id="field_pencilIcon'+f['name']+'"></span>'
                result += '</td>'

                result += '<td>'
                result += '<input style="display: none;" type="button" onclick="sendUpdate(\''+obj.realm+'\', \'' + f['name']+'\')" id="update_button_'+f['name']+'" name="update_button_'+f['name']+'" value="'+_("Save")+'"></input>'
                result += '</td>'

            # TODO Support other field types
            
            result += '</tr>'

        result += '</tbody></table>'

        return HTML(result)

    def _get_testplan_dialog_markup(self, req, cat_name):
        result = u"""
            <div id="dialog_testplan" style="padding:20px; display:none;" title="New Test Plan">
                <form id="new_testplan_form" class="addnew">
                """ + _("Specify the new Test Plan properties.") + """
                <br />
                <fieldset>
                    <legend>""" + _("Test Plan properties") + """</legend>
                    <table><tbody>
                        <tr>
                            <td>
                                <div class="field">
                                  <label>
                                    """ + _("The new Test Plan will contain:") + """
                                  </label>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <input type="radio" name="testplan_contains_all" value="true" checked="checked" /> """ + _("All the Test Cases in the Catalog") + """<br />
                                <input type="radio" name="testplan_contains_all" value="false" /> """ + _("Only the Test Cases selected before") + """
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <br />
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div class="field">
                                  <label>
                                    """ + _("The new Test Plan will:") + """
                                  </label>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <input type="radio" name="testplan_snapshot" value="true" /> """ + _("Refer to a current snapshot of the versions of the test cases") + """<br />
                                <input type="radio" name="testplan_snapshot" value="false" checked="checked" /> """ + _("Always point to the latest version of the Test Cases") + """
                            </td>
                        </tr>
                    </tbody></table>
                </fieldset>
                <fieldset>
                    <div class="buttons">
                        <input type="hidden" name="cat_name" value="%s" />
                        <input type="button" value='""" + _("Create Test Plan") + """' onclick="createTestPlanConfirm('%s')" style="text-align: right;"></input>
                        <input type="button" value='""" + _("Cancel") + """' onclick="createTestPlanCancel()" style="text-align: right;"></input>
                    </div>
                </fieldset>
                </form>
            </div>
        """
        
        result = result % (cat_name, cat_name)
        
        return result
    
    def _get_object_change_history_markup(self, obj, exclude_fields=None):
        text = u'<form id="objectChangeHistory" class="printableform"><fieldset id="objectChangeHistoryFields" class="collapsed"><legend class="foldable" style="cursor: pointer;"><a href="#no6"  onclick="expandCollapseSection(\'objectChangeHistoryFields\')">'+_("Object change history")+'</a></legend>'
        
        text += '<table class="listing"><thead>'
        text += '<tr><th>'+_("Timestamp")+'</th><th>'+_("Author")+'</th><th>'+_("Property")+'</th><th>'+_("Previous Value")+'</th><th>'+_("New Value")+'</th></tr>'
        text += '</thead><tbody>'

        for ts, author, fname, oldvalue, newvalue in obj.list_change_history():
            if exclude_fields is not None and fname in exclude_fields:
                continue
            
            if oldvalue is None:
                oldvalue = ''
            
            if newvalue is None:
                newvalue = ''
            
            text += '<tr>'
            text += '<td>'+format_datetime(from_any_timestamp(ts))+'</td>'
            text += '<td>'+html_escape(author)+'</td>'
            text += '<td>'+fname+'</td>'
            text += '<td>'+oldvalue+'</td>'
            text += '<td>'+newvalue+'</td>'
            text += '</tr>'
            
        text += '</tbody></table>'
        text += '</fieldset></form>'

        return HTML(text)
    
    def _get_import_dialog_markup(self, req, cat_name):
        result = u"""
            <div id="dialog_import" style="padding:20px; display:none;" title="Import test cases">
                <form id="import_file" class="addnew" method="post" enctype="multipart/form-data" action="%s/testimport">
                """ + _("Select a file in CSV format to import the test cases from.") + """
                <br />
                """ + _("The first row will have column names. The data must start from the second row.") + """
                """ + _("The file should have the following required columns:") + """
                <ul>
                    <li>title</li>
                    <li>description</li>
                </ul>
                """ + _("Any subsequent columns are optional, and will generate <a href='http://trac-hacks.org/wiki/TestManagerForTracPlugin#Customfields' target='_blank'>custom test case fields</a>.") + """
                """ + _("Use lowercase identifiers, with no blanks, for the column names.") + """
                <br />
                <fieldset>
                    <legend>""" + _("Upload file") + """</legend>
                    <table><tbody>
                        <tr>
                            <td>
                                <div class="field">
                                  <label>
                                    """ + _("File name:") + """
                                  </label>
                                </div>
                            </td>
                            <td>
                                <input type="file" name="input_file" />
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div class="field">
                                  <label>
                                    """ + _("Column separator:") + """
                                  </label>
                                </div>
                            </td>
                            <td>
                                <input type="text" name="column_separator" value=","/>
                            </td>
                        </tr>
                    </tbody></table>
                </fieldset>
                <fieldset>
                    <div class="buttons">
                        <input type="hidden" name="cat_name" value="%s" />
                        <input type="submit" name="import_file" value='""" + _("Import") + """' style="text-align: right;"></input>
                        <input type="button" value='""" + _("Cancel") + """' onclick="importTestCasesCancel()" style="text-align: right;"></input>
                    </div>
                </fieldset>
                </form>
            </div>
        """
        
        result = result % (fix_base_location(req), cat_name)
        
        return result
    
    def _get_export_dialog_markup(self, req, cat_name, planid, object_type):
        result = u"""
            <div id="dialog_export" style="padding:20px; display:none;" title="Export test cases">
                <form id="export_file" class="addnew" method="post" action="%s/testexport">
                """ + _("Select a name and a location on your machine for the CSV file to export the test cases to.") + """
                <br />
                <fieldset>
                    <legend>""" + _("Export options") + """</legend>
                    <table><tbody>
                        <tr>
                            <td>
                                <div class="field">
                                  <label>
                                    """ + _("Include full description:") + """
                                  </label>
                                </div>
                            </td>
                            <td>
                                <input type="checkbox" name="fulldetails" />
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div class="field">
                                  <label>
                                    """ + _("Raw wiki syntax:") + """
                                  </label>
                                </div>
                            </td>
                            <td>
                                <input type="checkbox" name="raw_wiki_format" />
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div class="field">
                                  <label>
                                    """ + _("Column separator:") + """
                                  </label>
                                </div>
                            </td>
                            <td>
                                <input type="text" name="column_separator" value=","/>
                            </td>
                        </tr>
                    </tbody></table>
                </fieldset>
                <fieldset>
                    <div class="buttons">
                        <input type="hidden" name="cat_name" value="%s" />
                        <input type="hidden" name="planid" value="%s" />
                        <input type="hidden" name="type" value="%s" />
                        <input type="submit" name="export_file" value='""" + _("Export") + """' style="text-align: right;"></input>
                        <input type="button" value='""" + _("Cancel") + """' onclick="exportTestCasesCancel()" style="text-align: right;"></input>
                    </div>
                </fieldset>
                </form>
            </div>
        """
        
        result = result % (fix_base_location(req), cat_name, planid, object_type)
        
        return result
    
    def _get_select_testplan_dialog_markup(self, req, tc, tcat):
        result = u"""
            <div id="dialog_select_testplan" style="padding:20px; display:none;" title='""" + _("Add Test Case to a Test Plan") + """'>
                <form id="add_to_testplan_form" class="addnew">
                    """ + _("Select the Test Plan to add the Test Case to.") + """
                <br />
                <fieldset style="height: 210px; overflow: auto;">
                    <legend>""" + _("Test Plans") + """</legend>
                    <table class="listing"><tbody>
                        <thead>
                            <tr>
                                <th></th><th>""" + _("Name") + """</th><th>""" + _("Author") + """</th><th>""" + _("Created") + """</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        num_plans = 0
        
        tp_search = TestPlan(self.env)
        # Go up to outer enclosing Test Catalog
        tp_search['page_name'] = 'TC_TT' + tcat['page_name'].partition('TC_TT')[2].partition('_')[0] + '%'
        tp_search['contains_all'] = None
        tp_search['freeze_tc_versions'] = None
        
        for tp in sorted(tp_search.list_matching_objects(exact_match=False), cmp=lambda x,y: cmp(x['time'],y['time']), reverse=True):
            if not tp['contains_all']:
                result += '<tr>'

                result += '<td><input type="radio" name="selected_planid" value="'+tp['id']+'" /></td>'
                result += '<td>'+tp['name']+'</td>'
                result += '<td>'+html_escape(tp['author'])+'</td>'
                result += '<td>'+format_datetime(tp['time'])+'</td>'
                
                result += '</tr>'
                num_plans += 1

        if num_plans == 0:
            result += '<tr>'
            result += '<td colspan="99">'+_("No suitable Test Plans (i.e. with only selected Test Cases) found.")+'</td>'
            result += '</tr>'

        result += """
                        </tbody>
                    </table>
                </fieldset>
                <fieldset>
                    <div class="buttons">
                        <input type="button" value='""" + _("Add to Test Plan") + """' onclick="addTestCaseToPlan('%s', '%s')" style="text-align: right;"></input>
                        <input type="button" value='""" + _("Cancel") + """' onclick="addTestCaseToPlanCancel()" style="text-align: right;"></input>
                    </div>
                </fieldset>
                </form>
            </div>
        """
        
        result = result % (tc['id'], tcat['id'])

        return result
    
    def _get_error_dialog_markup(self, req):
        result = u"""
            <div id="dialog_error" style="padding:20px; display:none;" title='""" + _("Error") + """'>
                %s
            </div>
        """ % (_("An error occurred performing the operation.<br /><br />Please try again."))
        
        return result
    
    def _write_common_code(self, req, add_statuses_and_colors=False, add_menu=False):
        add_stylesheet(req, 'common/css/report.css')
        add_stylesheet(req, 'testmanager/css/blitzer/jquery-ui-1.8.13.custom.css')
        add_stylesheet(req, 'testmanager/css/testmanager.css')

        before_jquery = u'var baseLocation="'+fix_base_location(req)+'";' + \
            'var jQuery_trac_old = $.noConflict(true);'
        after_jquery = u'var jQuery_testmanager = $.noConflict(true);$ = jQuery_trac_old;jQuery = $;'

        if add_statuses_and_colors and 'TEST_EXECUTE' in req.perm:
            after_jquery += self._get_statuses_and_colors_javascript()
        else:
            after_jquery += "var statuses_by_color = null;"
        
        common_code = tag.div()(
            HTML(self._get_error_dialog_markup(req)),
            tag.script(before_jquery, type='text/javascript'),
            tag.script(src='../chrome/testmanager/js/jquery-1.5.1.min.js', type='text/javascript'),
            tag.script(src='../chrome/testmanager/js/jquery-ui-1.8.13.custom.min.js', type='text/javascript'),
            tag.script(after_jquery, type='text/javascript'),
            tag.script(src='../chrome/testmanager/js/cookies.js', type='text/javascript'),
            tag.script(src='../chrome/testmanager/js/testmanager.js', type='text/javascript'),
            )

        if self.env.get_version() < 25:
            common_code.append(tag.script(src='../chrome/testmanager/js/compatibility.js', type='text/javascript'))

        if add_menu:
            common_code.append(tag.script(src='../chrome/testmanager/js/menu.js', type='text/javascript'))
            
        try:
            if req.locale is not None:
                common_code.append(tag.script(src='../chrome/testmanager/js/%s.js' % req.locale, type='text/javascript'))
        except:
            # Trac 0.11
			pass

        #common_code.append(tag.script("""
        #    (function($) {
        #        $('<button>Use jQuery 1.5.1</button>')
        #            .click(function() {
        #                alert('Top: ' + $(this).offset().top + '\n' +
        #                    'jQuery: ' + $.fn.jquery);
        #            })
        #            .appendTo('body');
        #    })(jQuery_testmanager);
        #""", type='text/javascript'))
            
        return common_code

    def _get_statuses_and_colors_javascript(self):
        result = u'var statuses_by_color = {'

        testmanagersystem = TestManagerSystem(self.env)
        tc_statuses_by_color = testmanagersystem.get_tc_statuses_by_color()
        for color in ['green', 'yellow', 'red']:
            result += '\'%s\': [' % color

            for outcome in tc_statuses_by_color[color]:
                label = tc_statuses_by_color[color][outcome]
                result += '{\'%s\': \'%s\'},' % (outcome, label)

            result = result[:-1]
            result += '],'
        
        result = result[:-1]
        result += '};\n'
        
        return result
        
    def _build_testcases_breadcrumb(self, curpage, planid, mode, fulldetails):
        # Determine current catalog name
        cat_name = 'TC'
        if curpage.find('_TC') >= 0:
            cat_name = curpage.rpartition('_TC')[0].rpartition('_')[2]
        elif not curpage == 'TC':
            cat_name = curpage.rpartition('_')[2]
        
        # Create the breadcrumb model
        path_name = curpage.partition('TC_')[2]
        tokens = path_name.split("_")
        curr_path = 'TC'
        
        breadcrumb = [{'name': 'TC', 'title': _("All Catalogs"), 'id': 'TC'}]

        for i, tc in enumerate(tokens):
            curr_path += '_'+tc
            page = WikiPage(self.env, curr_path)
            page_title = get_page_title(page.text)
            
            breadcrumb[(i+1):] = [{'name': tc, 'title': page_title, 'id': curr_path}]

            if tc == cat_name:
                break

        text = u''

        text +='<div>'
        text += self._render_breadcrumb(breadcrumb, planid, mode, fulldetails)
        text +='</div>'

        return text    
                
    def _build_catalog_tree(self, context, curpage, mode='tree', fulldetails=False, table_columns=None, table_columns_map=None, custom_ctx=None):
        # Determine current catalog name
        cat_name = 'TC'
        if curpage.find('_TC') >= 0:
            cat_name = curpage.rpartition('_TC')[0].rpartition('_')[2]
            #cat_id = '-1'
        elif not curpage == 'TC':
            cat_name = curpage.rpartition('_')[2]

        if cat_name == 'TC':
            mode = 'tree'
            fulldetails = False

        # Create the catalog subtree model
        components = TestManagerSystem(self.env).get_test_catalog_data_model(curpage)

        # Generate the markup
        ind = {'count': 0, 'totals': None}
        text = u''

        if mode == 'tree':
            text +='<div style="padding: 0px 0px 10px 10px">'+_("Filter:")+' <input id="tcFilter" title="'+_("Type the test to search for, even more than one word. You can also filter on the test case status (untested, successful, failed).")+'" type="text" size="40" onkeyup="starthighlight(\'ticketContainer\', this.value)"/>&nbsp;&nbsp;<span id="ticketContainer_searchResultsNumberId" style="font-weight: bold;"></span></div>'
            text +='<div style="font-size: 0.8em;padding-left: 10px"><a style="margin-right: 10px" onclick="toggleAll(\'ticketContainer\', true)" href="javascript:void(0)">'+_("Expand all")+'</a><a onclick="toggleAll(\'ticketContainer\', false)" href="javascript:void(0)">'+_("Collapse all")+'</a></div>'
            text +='<div id="ticketContainer">'

            text += self._render_subtree('-1', components, ind, 0)
            
            text +='</div>'
            
        elif mode == 'tree_table':
            text +='<div style="padding: 0px 0px 10px 10px">'+_("Filter:")+' <input id="tcFilter" title="'+_("Type the test to search for, even more than one word. You can also filter on the test case status (untested, successful, failed).")+'" type="text" size="40" onkeyup="starthighlightTable(\'testcaseList\', this.value)"/>&nbsp;&nbsp;<span id="testcaseList_searchResultsNumberId" style="font-weight: bold;"></span></div>'
            text += '<form id="testCatalogRunBook" class="printableform"><fieldset id="testCatalogRunBookFields" class="expanded">'
            text += '<table id="testcaseList" class="listing"><thead><tr>';
            
            # Prepare a container for calculating and keeping the totals
            totals = {}
            for col in table_columns:
                if col['visible'] == 'True':
                    text += '<th>'+col['label']+'</th>'
                
                if col['totals'] is not None:
                    totals[col['name']] = {'operation': col['totals'], 'count': 0, 'sum': 0, 'average': 0}

            ind['totals'] = totals
            text += '</tr></thead><tbody>';
            
            text += self._render_subtree_as_table(context, None, components, ind, 0, table_columns, table_columns_map, custom_ctx, fulldetails)
            
            text += self._render_totals(table_columns, ind['totals'])
            
            text += '</tbody></table>'
            text += '</fieldset></form>'
        
        return text
    
    def _build_testplan_tree(self, context, planid, curpage, mode='tree', sortby='name', table_columns=None, table_columns_map=None, custom_ctx=None):
        testmanagersystem = TestManagerSystem(self.env)
        default_status = testmanagersystem.get_default_tc_status()
        
        # Determine current catalog name
        cat_name = 'TC'
        if curpage.find('_TC') >= 0:
            cat_name = curpage.rpartition('_TC')[0].rpartition('_')[2]
        elif not curpage == 'TC':
            cat_name = curpage.rpartition('_')[2]

        # Create the catalog subtree model
        components = TestManagerSystem(self.env).get_test_catalog_data_model(curpage, True, planid, sortby)

        # Generate the markup
        ind = {'count': 0, 'totals': None}
        text = u''
        
        if mode == 'tree':
            text +='<div style="padding: 0px 0px 10px 10px">'+_("Filter:")+' <input id="tcFilter" title="'+_("Type the test to search for, even more than one word. You can also filter on the test case status (untested, successful, failed).")+'" type="text" size="40" onkeyup="starthighlight(\'ticketContainer\', this.value)"/>&nbsp;&nbsp;<span id="ticketContainer_searchResultsNumberId" style="font-weight: bold;"></span></div>'
            text +='<div style="font-size: 0.8em;padding-left: 10px"><a style="margin-right: 10px" onclick="toggleAll(\'ticketContainer\', true)" href="javascript:void(0)">'+_("Expand all")+'</a><a onclick="toggleAll(\'ticketContainer\', false)" href="javascript:void(0)">'+_("Collapse all")+'</a></div>'
            text +='<div id="ticketContainer">'
            text += self._render_subtree(planid, components, ind, 0)
            text +='</div>'

        elif mode == 'tree_table':
            text +='<div style="padding: 0px 0px 10px 10px">'+_("Filter:")+' <input id="tcFilter" title="'+_("Type the test to search for, even more than one word. You can also filter on the test case status (untested, successful, failed).")+'" type="text" size="40" onkeyup="starthighlightTable(\'testcaseList\', this.value)"/>&nbsp;&nbsp;<span id="testcaseList_searchResultsNumberId" style="font-weight: bold;"></span></div>'
            text += '<form id="testPlan" class="printableform"><fieldset id="testPlanFields" class="expanded">'
            text += '<table id="testcaseList" class="listing"><thead><tr>';

            # Prepare a container for calculating and keeping the totals
            totals = {}
            for col in table_columns:
                if col['visible'] == 'True':
                    text += '<th>'+col['label']+'</th>'
                    
                if col['totals'] is not None:
                    totals[col['name']] = {'operation': col['totals'], 'count': 0, 'sum': 0, 'average': 0}

            ind['totals'] = totals
                    
            text += '</tr></thead><tbody>';
            
            text += self._render_subtree_as_table(context, planid, components, ind, 0, table_columns, table_columns_map, custom_ctx)

            text += self._render_totals(table_columns, ind['totals'])
            
            text += '</tbody></table>'
            text += '</fieldset></form>'

        return text


    def _build_testplan_list(self, curpage, mode, fulldetails, show_delete_button):
        # Determine current catalog name
        cat_name = 'TC'
        catid = '-1'
        if curpage.find('_TC') >= 0:
            cat_name = curpage.rpartition('_TC')[0].rpartition('_')[2]
            catid = cat_name.rpartition('TT')[2]
        elif not curpage == 'TC':
            cat_name = curpage.rpartition('_')[2]
            catid = cat_name.rpartition('TT')[2]
        
        markup, num_plans = self._render_testplan_list(catid, mode, fulldetails, show_delete_button)


        text = u'<form id="testPlanList" class="printableform"><fieldset id="testPlanListFields" class="collapsed"><legend class="foldable" style="cursor: pointer;"><a href="#no4"  onclick="expandCollapseSection(\'testPlanListFields\')">'+_("Available Test Plans")+' ('+str(num_plans)+')</a></legend>'
        text +='<div style="padding: 0px 0px 10px 10px">'+_("Filter:")+' <input id="tpFilter" title="'+_("Type the test to search for, even more than one word.")+'" type="text" size="40" onkeyup="starthighlightTable(\'testPlanListTable\', this.value)"/>&nbsp;&nbsp;<span id="testPlanListTable_searchResultsNumberId" style="font-weight: bold;"></span></div>'
        text += markup
        text += '</fieldset></form>'

        return HTML(text)
        
    def _render_testplan_list(self, catid, mode, fulldetails, show_delete_button):
        """Returns a test case status in a plan audit trail."""

        delete_icon = '../chrome/testmanager/images/trash.png'

        cat = TestCatalog(self.env, catid)
        
        result = u'<table class="listing" id="testPlanListTable"><thead>'
        result += '<tr><th>'+_("Plan Name")+'</th><th>'+_("Author")+'</th><th>'+_("Timestamp")+'</th><th>'+_("Contained Test Cases")+'</th><th>'+_("Test Case Versions")+'</th><th></th></tr>'
        result += '</thead><tbody>'
        
        num_plans = 0
        for tp in sorted(cat.list_testplans(), cmp=lambda x,y: cmp(x['time'],y['time']), reverse=True):
            result += '<tr>'
            result += '<td><a title="'+_("Open Test Plan")+'" href="'+tp['page_name']+'?planid='+tp['id']+'">'+tp['name']+'</a></td>'
            result += '<td>'+html_escape(tp['author'])+'</td>'
            result += '<td>'+format_datetime(tp['time'])+'</td>'
            result += '<td>'+(_("Contains selected Test Cases"), _("Contains all Test Cases"))[tp['contains_all']]+'</td>'
            result += '<td>'+(_("Points to latest Test Case versions"), _("Contains a snapshot of Test Case versions"))[tp['freeze_tc_versions']]+'</td>'
            
            if show_delete_button:
                result += '<td style="cursor: pointer;"><img class="iconElement" width="16" height="16" alt="'+_("Delete")+'" title="'+_("Delete")+'" src="'+delete_icon+'" onclick="deleteTestPlan(\'../testdelete?type=testplan&path='+tp['page_name']+'&mode='+mode+'&fulldetails='+str(fulldetails)+'&planid='+tp['id']+'\')"/></td>'
            else:
                result += '<td></td>'
            
            result += '</tr>'
            num_plans += 1

        result += '</tbody></table>'

        return result, num_plans
        
    # Render the breadcrumb
    def _render_breadcrumb(self, breadcrumb, planid, mode, fulldetails):
        plan_ref = ''
        if planid is not None and not planid == '-1':
            plan_ref = '&planid='+planid
            display_breadcrumb = 'none'
        else:
            display_breadcrumb = 'block'
        
        text = u'<span style="display: %s">' % display_breadcrumb
        path_len = len(breadcrumb)
        for i, x in enumerate(breadcrumb):
            if i == 0:
                plan_param = ''
            else:
                plan_param = plan_ref
        
            text += '<span name="breadcrumb" style="cursor: pointer; color: #BB0000; margin-left: 5px; margin-right: 5px; font-size: 0.8em;" '
            text += ' onclick="window.location=\''+x['id']+'?mode='+mode+plan_param+'&fulldetails='+str(fulldetails)+'\'">'+x['title']
            
            if i < path_len-1:
                text += '</span><span style="color: #BB0000; margin-left: 2px; margin-right: 2px;">->'
            
            text += '</span>'

        text += '</span>'
            
        return text

    # Render the subtree
    def _render_subtree(self, planid, component, ind, level):
        data = component
        text = u''
        if (level == 0):
            data = component['childrenC']
            text +='<ul style="list-style: none;">';
        
        sortedList = sorted(data, key=lambda k: data[k]['title'])
        
        for x in sortedList:
            ind['count'] += 1
            text+='<li style="font-weight: normal">'
            comp = data[x]
            if ('childrenC' in comp):
                subcData=comp['childrenC']
                
                toggle_icon = '../chrome/testmanager/images/plus.png'
                toggable = 'toggable'
                if (len(comp['childrenC']) + len(comp['childrenT'])) == 0:
                    toggable = 'nope'
                    toggle_icon = '../chrome/testmanager/images/empty.png'
                    
                index = str(ind['count'])
                if planid is not None and not planid == '-1':
                    plan_param = '?planid='+planid
                else:
                    plan_param = ''
                    
                text += '<span name="'+toggable+'" style="cursor: pointer" id="b_'+index+'"><span onclick="toggle(\'b_'+index+'\')"><img class="iconElement" src="'+toggle_icon+'" /></span><span id="l_'+index+'" onmouseover="underlineLink(\'l_'+index+'\')" onmouseout="removeUnderlineLink(\'l_'+index+'\')" onclick="window.location=\''+comp['id']+plan_param+'\'" title="'+_("Open")+'">'+comp['title']+'</span></span><span style="color: gray;">&nbsp;('+str(comp['tot'])+')</span>'
                text +='<ul id="b_'+index+'_list" style="display:none;list-style: none;">';
                ind['count']+=1
                text += self._render_subtree(planid, subcData, ind, level+1)
                if ('childrenT' in comp):            
                    mtData=comp['childrenT']
                    text += self._render_testcases(planid, mtData)
            text+='</ul>'
            text+='</li>'
        if (level == 0):
            if ('childrenT' in component):            
                cmtData=component['childrenT']
                text += self._render_testcases(planid, cmtData)
            text+='</ul>'        
        return text

    def _render_testcases(self, planid, data): 
        
        testmanagersystem = TestManagerSystem(self.env)
        tc_statuses = testmanagersystem.get_tc_statuses_by_name()
        
        tc_target = ("", " target='_blank'")[self.open_new_window]
        
        text=u''
        sortedList = sorted(data)
        for x in sortedList:
            tick = data[x]
            status = tick['status']

            version = tick['version']
            version_str = ('&version='+str(version), '')[version == -1]

            has_status = True
            stat_meaning = 'yellow'
            if status is not None and len(status) > 0 and status != '__none__':
                if status in tc_statuses:
                    stat_meaning = tc_statuses[status][0]
            
                statusIcon='../chrome/testmanager/images/%s.png' % stat_meaning
            else:
                has_status = False

            if has_status:
                statusLabel = "Unknown"
                if status in tc_statuses:
                    statusLabel = tc_statuses[status][1]
            
                tcid = tick['id'].rpartition('TC')[2]
                text+="<li name='tc_node' style='font-weight: normal;'><img name='"+tcid+","+planid+","+tick['id']+","+status+","+stat_meaning+","+statusLabel+"' id='statusIcon"+tick['id']+"' class='statusIconElement' src='"+statusIcon+"' title='"+statusLabel+"' style='cursor: pointer;'></img><span onmouseover='showPencil(\"pencilIcon"+tick['id']+"\", true)' onmouseout='hidePencil(\"pencilIcon"+tick['id']+"\", false)'><a href='"+tick['id']+"?planid="+planid+version_str+"' "+tc_target+">"+tick['title']+"&nbsp;</a><span style='display: none;'>"+statusLabel+"</span><span><a class='rightIcon' style='display: none;' title='"+_("Edit the Test Case")+"' href='"+tick['id']+"?action=edit&planid="+planid+"' "+tc_target+" id='pencilIcon"+tick['id']+"'></a></span></span></li>"
            else:
                text+="<li name='tc_node' style='font-weight: normal;'><input name='select_tc_checkbox' value='"+tick['id']+"' type='checkbox' style='display: none;float: left; position: relative; top: 3px;' /><span onmouseover='showPencil(\"pencilIcon"+tick['id']+"\", true)' onmouseout='hidePencil(\"pencilIcon"+tick['id']+"\", false)'><a href='"+tick['id']+'?a=a'+version_str+"' "+tc_target+">"+tick['title']+"&nbsp;</a><span><a class='rightIcon' style='display: none;' title='"+_("Edit the Test Case")+"' href='"+tick['id']+"?action=edit' "+tc_target+" id='pencilIcon"+tick['id']+"'></a></span></span></li>"
                
        return text
            
    def _build_testcase_status(self, planid, curpage):
        testmanagersystem = TestManagerSystem(self.env)
        tc_statuses = testmanagersystem.get_tc_statuses_by_name()
        
        tc_id = curpage.rpartition('_TC')[2]
        
        tcip = TestCaseInPlan(self.env, tc_id, planid)
        if tcip.exists:
            status = tcip['status'].lower()
        else:
            status = testmanagersystem.get_default_tc_status()
        
        # Hide all icons except the one relative to the current test
        # case status
        display = {'green': 'none', 'yellow': 'none', 'red': 'none'}
        
        if status in tc_statuses:
            display[tc_statuses[status][0]] = 'block'
            statusLabel = tc_statuses[status][1]
        else:
            statusLabel = _("Unknown")
        
        text = u''
        text += '<img style="display: '+display['green']+';" id="tcTitleStatusIcongreen" src="../chrome/testmanager/images/green.png" title="'+_(statusLabel)+'"></img></span>'
        text += '<img style="display: '+display['yellow']+';" id="tcTitleStatusIconyellow" src="../chrome/testmanager/images/yellow.png" title="'+_(statusLabel)+'"></img></span>'
        text += '<img style="display: '+display['red']+';" id="tcTitleStatusIconred" src="../chrome/testmanager/images/red.png" title="'+_(statusLabel)+'"></img></span>'
        
        return text
        
    # Render the subtree as a tree table
    def _render_subtree_as_table(self, context, planid, component, ind, level, table_columns=None, table_columns_map=None, custom_ctx=None, fulldetails=False):
        data = component
        text = u''

        if (level == 0):
            data = component['childrenC']

        sortedList = sorted(data, key=lambda k: data[k]['title'])

        for x in sortedList:
            ind['count'] += 1
            comp = data[x]
            if ('childrenC' in comp):
                subcData=comp['childrenC']
                
                index = str(ind['count'])
                if planid is not None and not planid == '-1':
                    plan_param = '&planid='+planid
                else:
                    plan_param = ''
                
                text += '<tr name="testcatalog">'

                # Common columns
                if table_columns_map['title']['visible'] == 'True':
                    text += '<td style="padding-left: '+str(level*30)+'px;"><a href="'+comp['id']+'?mode=tree_table'+plan_param+'&fulldetails='+str(fulldetails)+'" title="'+_("Open")+'">'+comp['title']+'</a></td>'

                # Custom testcatalog columns
                tcat = None
                if custom_ctx['testcatalog'][0]:
                    tcat_id = comp['id'].rpartition('TT')[2]
                    tcat = TestCatalog(self.env, tcat_id)
                    text += self._get_custom_fields_columns(tcat, table_columns, table_columns_map, custom_ctx['testcatalog'][1])

                text += '</tr>'

                self._update_totals(ind['totals'], tcat)
                
                ind['count']+=1
                text += self._render_subtree_as_table(context, planid, subcData, ind, level+1, table_columns, table_columns_map, custom_ctx, fulldetails)
                if ('childrenT' in comp):            
                    mtData=comp['childrenT']
                    text += self._render_testcases_as_table(context, planid, mtData, ind, level+1, table_columns, table_columns_map, custom_ctx, fulldetails)

        if (level == 0):
            if ('childrenT' in component):            
                cmtData = component['childrenT']
                text += self._render_testcases_as_table(context, planid, cmtData, ind, level, table_columns, table_columns_map, custom_ctx, fulldetails)

        return text

    def _render_testcases_as_table(self, context, planid, data, ind, level=0, table_columns=None, table_columns_map=None, custom_ctx=None, fulldetails=False): 

        testmanagersystem = TestManagerSystem(self.env)
        tc_statuses = testmanagersystem.get_tc_statuses_by_name()

        tc_target = ("", " target='_blank'")[self.open_new_window]
        
        text=u''
        sortedList = sorted(data)
        for x in sortedList:
            tick = data[x]
            status = tick['status']

            version = tick['version']
            version_str = ('&version='+str(version), '')[version == -1]
            
            stat_meaning = ''
            has_status = True
            if status is not None and len(status) > 0 and status != '__none__':
                stat_meaning = 'yellow'
                if status in tc_statuses:
                    stat_meaning = tc_statuses[status][0]
            
                if stat_meaning == 'green':
                    statusIcon='../chrome/testmanager/images/green.png'
                elif stat_meaning == 'yellow':
                    statusIcon='../chrome/testmanager/images/yellow.png'
                elif stat_meaning == 'red':
                    statusIcon='../chrome/testmanager/images/red.png'
            else:
                has_status = False

            tc = None
            if fulldetails or custom_ctx['testcase'][0] or table_columns_map['description']['visible'] == 'True':
                tc = TestCase(self.env, tick['tc_id'])

            text += '<tr name="testcase">'

            # Common columns
            if has_status:
                if status in tc_statuses:
                    statusLabel = tc_statuses[status][1]
                else:
                    statusLabel = _("Unknown")

            # TODO Hide status icon if Status column deselected in preferences
            if table_columns_map['title']['visible'] == 'True':
                if has_status:
                    text += '<td style="padding-left: '+str(level*30)+'px;"><img name="'+tick['tc_id']+','+planid+','+tick['id']+','+status+','+stat_meaning+','+statusLabel+'" id="statusIcon'+tick['id']+'" class="statusIconElement" src="'+statusIcon+'" title="'+statusLabel+'"></img><a href="'+tick['id']+'?planid='+planid+version_str+'&mode=tree_table" '+tc_target+'>'+tick['title']+'</a></td>'
                else:
                    text += '<td style="padding-left: '+str(level*30)+'px;"><input name="select_tc_checkbox" value="'+tick['id']+'" type="checkbox" style="display: none;float: left; position: relative; top: 3px;" /><a href="'+tick['id']+'?mode=tree_table&fulldetails='+str(fulldetails)+version_str+'" '+tc_target+'>'+tick['title']+'</a></td>'
                
            # Custom testcatalog columns
            if custom_ctx['testcatalog'][0]:
                for f in custom_ctx['testcatalog'][1]:
                    if table_columns_map[f['name']]['visible'] == 'True':
                        text += '<td></td>'

            # Base testcase columns
            if table_columns_map['id']['visible'] == 'True':
                text += '<td>'+tick['tc_id']+'</td>'

            # Custom testcase columns
            if tc and tc.exists and custom_ctx['testcase'][0]:
                text += self._get_custom_fields_columns(tc, table_columns, table_columns_map, custom_ctx['testcase'][1])

            self._update_totals(ind['totals'], tc)
                
            if has_status:
                # Base testcaseinplan columns
                if table_columns_map['status']['visible'] == 'True':
                    text += '<td>'+statusLabel+'</td>'
                if table_columns_map['author']['visible'] == 'True':
                    text += '<td>'+html_escape(tick['author'])+'</td>'
                if table_columns_map['time']['visible'] == 'True':
                    text += '<td>'+format_datetime(tick['ts'])+'</td>'
                
                # Custom testcaseinplan columns
                tcip = None
                if custom_ctx['testcaseinplan'][0]:
                    tcip = TestCaseInPlan(self.env, tick['tc_id'], planid)
                    text += self._get_custom_fields_columns(tcip, table_columns, table_columns_map, custom_ctx['testcaseinplan'][1])

                self._update_totals(ind['totals'], tcip)
                    
            #if fulldetails:
            if table_columns_map['description']['visible'] == 'True':
                wikidom = WikiParser(self.env).parse(tc.description)
                out = StringIO()
                f = Formatter(self.env, context)
                f.reset(wikidom)
                f.format(wikidom, out, False)
                description = out.getvalue()

                text += '<td>'+description+'</td>'

            text += '</tr>'
            
        return text

    def _render_totals(self, table_columns, totals):
        text = u''
    
        for col in table_columns:
            if col['visible'] == 'True':
                if col['name'] in totals:
                    text += '<td>'
                
                    col_totals = totals[col['name']]
                    operation = col_totals['operation']
                    if operation == 'sum':
                        text += str(col_totals['sum']) + ' ' + _("(Sum)")
                    elif operation == 'average':
                        text += str(col_totals['average']) + ' ' + _("(Average)")
                    elif operation == 'count':
                        text += str(col_totals['count']) + ' ' + _("(Count)")
                
                    text += '</td>'
                
                else:
                    text += '<td></td>'
                
        return text
        
    def _build_testcase_change_status(self, planid, curpage):
        testmanagersystem = TestManagerSystem(self.env)
        tc_statuses = testmanagersystem.get_tc_statuses_by_name()
        tc_statuses_by_color = testmanagersystem.get_tc_statuses_by_color()

        tc_id = curpage.rpartition('_TC')[2]
        
        tcip = TestCaseInPlan(self.env, tc_id, planid)
        if tcip.exists:
            status = tcip['status'].lower()
        else:
            status = testmanagersystem.get_default_tc_status()

        if status in tc_statuses:
            status_meaning = tc_statuses[status][0]
        else:
            # The status outcome has been removed from trac.ini after it was used for some test case
            # Take the first outcome for the yellow color
            status_meaning = 'yellow'
            for status in tc_statuses_by_color['yellow']:
                pass
        
        need_menu = False
        for color in ['green', 'yellow', 'red']:
            if len(tc_statuses_by_color[color]) > 1:
                need_menu = True

        text = u''

        if need_menu:
            text += '<div id="copyright" style="display: none;">Copyright &copy; 2010 <a href="http://apycom.com/">Apycom jQuery Menus</a></div>'
        
        text += '<script type="text/javascript">'
        text += 'var currStatus = "'+status+'";'
        text += 'var currStatusColor = "'+status_meaning+'";'
        
        text += '</script>'

        text += _("Change the Status:")
        
        text += '<span style="margin-left: 15px;">'
     
        if need_menu:
            text += '<div id="statusmenu"><ul class="statusmenu">'
        else:
            text += '<div>'

        for color in ['green', 'yellow', 'red']:
            border = ''
            if status_meaning == color:
                border = 'border: 2px solid black;'
            
            if need_menu:
                text += '<li><a href="#" class="parent"><span id="tcStatus%s" style="%s"><img src="../chrome/testmanager/images/%s.png"></img></span></a><div><ul>' % (color, border, color) 

                for outcome in tc_statuses_by_color[color]:
                    label = tc_statuses_by_color[color][outcome]
                    text += '<li><a href="#" onclick="changestate(\''+tc_id+'\', \''+planid+'\', \''+curpage+'\', \''+outcome+'\', \''+color+'\', \'%s\')"><span>%s</span></a></li>' % (label, label)

                text += '</ul></div></li>'
                
            else:
                for outcome in tc_statuses_by_color[color]:
                    label = tc_statuses_by_color[color][outcome]
                    
                    text += ('<span id="tcStatus%s" style="padding: 3px; cursor: pointer;%s" onclick="changestate(\''+tc_id+'\', \''+planid+'\', \''+curpage+'\', \'%s\', \'%s\', \'%s\')">') % (color, border, outcome, color, label)
                    text += '<img src="../chrome/testmanager/images/%s.png" title="%s"></img>' % (color, label)
                    text += '</span>'
        
        if need_menu:
            text += '</ul>'

        text += '</div>'
            
        text += '</span>'
        
        return text
        
    def _build_testcase_status_history(self, planid, curpage):
        testmanagersystem = TestManagerSystem(self.env)
        tc_statuses = testmanagersystem.get_tc_statuses_by_name()

        tc_id = curpage.rpartition('_TC')[2]
        
        tcip = TestCaseInPlan(self.env, tc_id, planid)
        
        text = '<form id="testCaseHistory" class="printableform"><fieldset id="testCaseHistoryFields" class="collapsed"><legend class="foldable" style="cursor: pointer;"><a href="#no3"  onclick="expandCollapseSection(\'testCaseHistoryFields\')">'+_("Status change history")+'</a></legend>'
        
        text += '<table class="listing"><thead>'
        text += '<tr><th>'+_("Timestamp")+'</th><th>'+_("Author")+'</th><th>'+_("Status")+'</th></tr>'
        text += '</thead><tbody>'

        for ts, author, status in tcip.list_history():
            if status in tc_statuses:
                statusLabel = tc_statuses[status][1]
            else:
                statusLabel = _("Unknown")

            text += '<tr>'
            text += '<td>'+format_datetime(from_any_timestamp(ts))+'</td>'
            text += '<td>'+html_escape(author)+'</td>'
            text += '<td>'+statusLabel+'</td>'
            text += '</tr>'
            
        text += '</tbody></table>'
        text += '</fieldset></form>'

        return text

    def _update_totals(self, totals, obj):
        self.env.log.debug(">>> _update_totals: %s %s", totals, obj)
        if obj is not None:
            for col in totals:
                col_totals = totals[col]
                operation = col_totals['operation']
                if operation == 'sum':
                    col_totals['sum'] += self._get_field_value(col, obj)

                elif operation == 'average':
                    val = self._get_field_value(col, obj)
                    
                    if val != 0:
                        prev_count = col_totals['count']
                        if prev_count > 0:
                            prev_average = col_totals['average']
                            col_totals['average'] = (val + (prev_average * prev_count)) / (prev_count + 1)
                        else:
                            col_totals['average'] = val

                        col_totals['count'] += 1
                    
                elif operation == 'count':
                    val = self._get_field_value(col, obj)
                    if val != 0:
                        col_totals['count'] += 1

        self.env.log.debug("<<< _update_totals: %s", totals)
                        
    def _get_custom_fields_columns(self, obj, table_columns, table_columns_map, fields):
        result = u''
        
        for f in fields:
            if table_columns_map[f['name']]['visible'] == 'True':
                if f['type'] == 'text':
                    result += '<td>'
                    if obj[f['name']] is not None:
                        result += obj[f['name']]
                    result += '</td>'

                # TODO Support other field types

        return result

    def _get_field_value(self, col_name, obj):
        result = 0
        self.env.log.debug(">>> _get_field_value %s %s", col_name, obj)
        if obj[col_name] is not None and obj[col_name] != '':
            try:
                self.env.log.debug("    _get_field_value - value: %s", obj[col_name])
                # Try to parse the value as a number
                result = float(obj[col_name])
            except:
                # Just count as 1 (non-empty value)
                result = 1

        self.env.log.debug("<<< _get_field_value: %s", result)
                
        return result
