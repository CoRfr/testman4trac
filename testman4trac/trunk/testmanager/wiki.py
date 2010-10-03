# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi
#

from trac.core import *
from trac.web.chrome import add_stylesheet, add_script, ITemplateProvider
from trac.wiki.api import IWikiSyntaxProvider
from trac.resource import Resource
from trac.mimeview.api import Context
from trac.web.api import ITemplateStreamFilter
from trac.wiki.api import WikiSystem, IWikiChangeListener
from trac.wiki.model import WikiPage
from trac.wiki.formatter import Formatter
from genshi.builder import tag
from genshi.filters.transform import Transformer
from genshi import HTML

from tracgenericclass.model import GenericClassModelProvider

from testmanager.macros import TestCaseBreadcrumbMacro, TestCaseTreeMacro, TestPlanTreeMacro, TestPlanTreeTableMacro, TestPlanListMacro, TestCaseStatusMacro, TestCaseChangeStatusMacro, TestCaseStatusHistoryMacro
from testmanager.labels import *
from testmanager.model import TestCatalog, TestCase, TestCaseInPlan, TestPlan


class WikiTestManagerInterface(Component):
    """Implement generic template provider."""
    
    implements(ITemplateStreamFilter, IWikiChangeListener)
    
    # IWikiChangeListener methods
    def wiki_page_added(self, page):
        #page_on_db = WikiPage(self.env, page.name)
        pass

    def wiki_page_changed(self, page, version, t, comment, author, ipnr):
        pass

    def wiki_page_deleted(self, page):
        if page.name.find('_TC') >= 0:
            # Only Test Case deletion is supported. 
            # Deleting a Test Catalog will not delete all of the inner
            #   Test Cases.
            tc_id = page.name.rpartition('_TC')[2]
            tc = TestCase(self.env, tc_id)
            if tc.exists:
                tc.delete(del_wiki_page=False)
            else:
                self.env.log.debug("Test case not found")

    def wiki_page_version_deleted(self, page):
        pass


    # ITemplateStreamFilter methods
    def filter_stream(self, req, method, filename, stream, data):
        page_name = req.args.get('page', 'WikiStart')
        planid = req.args.get('planid', '-1')

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
            else:
                if filename == 'wiki_view.html':
                    if not planid or planid == '-1':
                        return self._catalog_wiki_view(req, formatter, page_name, stream)
                    else:
                        return self._testplan_wiki_view(req, formatter, page_name, planid, stream)

        return stream

        
    # Internal methods

    def _catalog_wiki_view(self, req, formatter, page_name, stream):
        path_name = req.path_info
        cat_name = path_name.rpartition('/')[2]
        cat_id = cat_name.rpartition('TT')[2]

        tmmodelprovider = GenericClassModelProvider(self.env)
        test_catalog = TestCatalog(self.env, cat_id, page_name)
        
        add_stylesheet(req, 'testmanager/css/testmanager.css')
        add_stylesheet(req, 'common/css/report.css')

        add_script(req, 'testmanager/js/cookies.js')
        add_script(req, 'testmanager/js/labels.js')
        add_script(req, 'testmanager/js/testmanager.js')

        breadcrumb_macro = TestCaseBreadcrumbMacro(self.env)
        tree_macro = TestCaseTreeMacro(self.env)

        if page_name == 'TC':
            # Root of all catalogs
            insert1 = tag.div()(
                        tag.div(id='pasteTCHereMessage', class_='messageBox', style='display: none;')(LABELS['select_cat_to_move'],
                            tag.a(href='javascript:void(0);', onclick='cancelTCMove()')(LABELS['cancel'])
                            ),
                        tag.h1(LABELS['tc_list']),
                        tag.br(), tag.br()
                        )
            fieldLabel = LABELS['new_catalog']
            buttonLabel = LABELS['add_catalog']
        else:
            insert1 = tag.div()(
                        HTML(breadcrumb_macro.expand_macro(formatter, None, page_name)),
                        tag.br(), 
                        tag.div(id='pasteTCHereMessage', class_='messageBox', style='display: none;')(
                            LABELS['select_cat_to_move2'],
                            tag.a(href='javascript:void(0);', onclick='cancelTCMove()')(LABELS['cancel'])
                            ),
                        tag.br(),
                        tag.h1(LABELS['tc_catalog'])
                        )
            fieldLabel = LABELS['new_subcatalog']
            buttonLabel = LABELS['add_subcatalog']

        insert2 = tag.div()(
                    HTML(tree_macro.expand_macro(formatter, None, page_name)),
                    tag.div(class_='testCaseList')(
                        tag.br(), tag.br()
                    ))
                    
        if not page_name == 'TC':
            # The root of all catalogs cannot contain itself test cases
            insert2.append(tag.div()(
                        self._get_custom_fields_markup(test_catalog, tmmodelprovider.get_custom_fields_for_realm('testcatalog')),
                        tag.br()
                    ))
            insert2.append(tag.div(id='pasteTCHereDiv')(
                        tag.input(type='button', id='pasteTCHereButton', value=LABELS['move_here'], onclick='pasteTestCaseIntoCatalog("'+cat_name+'")')
                    ))
                    
        insert2.append(tag.div(class_='field')(
                    tag.script('var baseLocation="'+req.href()+'";', type='text/javascript'),
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
                        tag.script('var baseLocation="'+req.href()+'";', type='text/javascript'),
                        tag.br(),
                        tag.label(
                            LABELS['new_tc_label'],
                            tag.span(id='errorMsgSpan', style='color: red;'),
                            tag.br(),
                            tag.input(id='tcName', type='text', name='tcName', size='50'),
                            tag.input(type='button', value=LABELS['add_tc_button'], onclick='creaTestCase("'+cat_name+'")')
                            ),
                        tag.br(), tag.br(), tag.br(),
                        tag.label(
                            LABELS['new_plan_label'],
                            tag.span(id='errorMsgSpan2', style='color: red;'),
                            tag.br(),
                            tag.input(id='planName', type='text', name='planName', size='50'),
                            tag.input(type='button', value=LABELS['add_test_plan_button'], onclick='creaTestPlan("'+cat_name+'")')
                            ),
                        tag.br(), 
                        self._get_testplan_list_markup(formatter, cat_name),
                        ))
                    
        insert2.append(tag.div()(tag.br(), tag.br(), tag.br(), tag.br()))
        
        return stream | Transformer('//div[contains(@class,"wikipage")]').after(insert2) | Transformer('//div[contains(@class,"wikipage")]').before(insert1)

        
    def _testplan_wiki_view(self, req, formatter, page_name, planid, stream):
        path_name = req.path_info
        cat_name = path_name.rpartition('/')[2]
        cat_id = cat_name.rpartition('TT')[2]
        
        mode = req.args.get('mode', 'tree')

        tmmodelprovider = GenericClassModelProvider(self.env)
        test_plan = TestPlan(self.env, planid, cat_id, page_name)
        
        add_stylesheet(req, 'testmanager/css/testmanager.css')
        add_stylesheet(req, 'common/css/report.css')

        add_script(req, 'testmanager/js/cookies.js')
        add_script(req, 'testmanager/js/labels.js')
        add_script(req, 'testmanager/js/testmanager.js')

        if mode == 'tree':
            tree_macro = TestPlanTreeMacro(self.env)
        elif mode == 'tree_table':
            tree_macro = TestPlanTreeTableMacro(self.env)
            
        tp = TestPlan(self.env, planid)
        
        insert1 = tag.div()(
                    tag.a(href=req.href.wiki(page_name))(LABELS['back_to_catalog']),
                    tag.div(style='border: 1px, solid, gray; padding: 1px;')(
                        tag.span()(
                            tag.a(href=req.href.wiki(page_name, mode='tree', planid=planid))(
                                tag.img(src='../chrome/testmanager/images/tree.png', title="Tree View"))
                            ),
                        tag.span()(
                            tag.a(href=req.href.wiki(page_name, mode='tree_table', planid=planid))(
                                tag.img(src='../chrome/testmanager/images/tree_table.png', title="Table View"))
                            )),
                    tag.br(), 
                    tag.h1(LABELS['test_plan']+tp['name'])
                    )

        insert2 = tag.div()(
                    HTML(tree_macro.expand_macro(formatter, None, 'planid='+str(planid)+',catalog_path='+page_name)),
                    tag.div(class_='testCaseList')(
                    tag.br(), tag.br(),
                    self._get_custom_fields_markup(test_plan, tmmodelprovider.get_custom_fields_for_realm('testplan')),
                    tag.br(),
                    tag.div(class_='field')(
                        tag.script('var baseLocation="'+req.href()+'";', type='text/javascript'),
                        tag.br(), tag.br(), tag.br(), tag.br(),
                        #tag.input(type='button', value=LABELS['regenerate_plan_button'], onclick='regenerateTestPlan("'+str(planid)+'", "'+page_name+'")')
                        )
                    ))
                    
        insert2.append(tag.div()(tag.br(), tag.br(), tag.br(), tag.br()))
        
        return stream | Transformer('//div[contains(@class,"wikipage")]').after(insert2) | Transformer('//div[contains(@class,"wikipage")]').before(insert1)
        

    def _testcase_wiki_view(self, req, formatter, planid, page_name, stream):
        tc_name = page_name
        cat_name = page_name.partition('_TC')[0]
        
        is_edit = req.args.get('edit_custom', 'false')
        
        has_status = False
        plan_name = ''
    
        tc_id = tc_name.partition('_TC')[2]
        test_case = TestCase(self.env, tc_id, tc_name)
        
        tmmodelprovider = GenericClassModelProvider(self.env)
        
        add_stylesheet(req, 'testmanager/css/testmanager.css')
        add_stylesheet(req, 'common/css/report.css')

        add_script(req, 'testmanager/js/cookies.js')
        add_script(req, 'testmanager/js/labels.js')
        add_script(req, 'testmanager/js/testmanager.js')
        
        breadcrumb_macro = TestCaseBreadcrumbMacro(self.env)
        
        insert1 = tag.div()(
                    self._get_breadcrumb_markup(formatter, planid, page_name),
                    tag.br(), tag.br(), 
                    tag.div(id='copiedTCMessage', class_='messageBox', style='display: none;')(
                        LABELS['move_tc_help_msg'],
                        tag.a(href='javascript:void(0);', onclick='cancelTCMove()')(LABELS['cancel'])
                        ),
                    tag.br(),
                    tag.span(style='font-size: large; font-weight: bold;')(
                        tag.span()(
                            LABELS['test_case']
                            )
                        )
                    )
        
        insert2 = tag.div(class_='field', style='marging-top: 60px;')(
                    tag.br(), tag.br(), 
                    self._get_custom_fields_markup(test_case, tmmodelprovider.get_custom_fields_for_realm('testcase')),
                    tag.br(),
                    tag.script('var baseLocation="'+req.href()+'";', type='text/javascript'),
                    tag.input(type='button', value=LABELS['open_ticket_button'], onclick='creaTicket("'+tc_name+'", "", "")'),
                    HTML('&nbsp;&nbsp;'), 
                    tag.input(type='button', id='moveTCButton', value=LABELS['move_tc_button'], onclick='copyTestCaseToClipboard("'+tc_name+'")'),
                    HTML('&nbsp;&nbsp;'), 
                    tag.input(type='button', id='duplicateTCButton', value=LABELS['duplicate_tc_button'], onclick='duplicateTestCase("'+tc_name+'", "'+cat_name+'")'),
                    tag.br(), tag.br()
                    )
                    
        return stream | Transformer('//div[contains(@class,"wikipage")]').after(insert2) | Transformer('//div[contains(@class,"wikipage")]').before(insert1)

    def _testcase_in_plan_wiki_view(self, req, formatter, planid, page_name, stream):
        tc_name = page_name
        cat_name = page_name.partition('_TC')[0]
        
        mode = req.args.get('mode', 'tree')

        has_status = True
        tp = TestPlan(self.env, planid)
        plan_name = tp['name']
    
        tc_id = tc_name.partition('_TC')[2]
        # Note that assigning a default status here is functional. If the tcip actually exists,
        # the real status will override this value.
        tcip = TestCaseInPlan(self.env, tc_id, planid, page_name, 'TO_BE_TESTED')
        
        tmmodelprovider = GenericClassModelProvider(self.env)
    
        add_stylesheet(req, 'testmanager/css/testmanager.css')
        add_stylesheet(req, 'common/css/report.css')

        add_script(req, 'testmanager/js/cookies.js')
        add_script(req, 'testmanager/js/labels.js')
        add_script(req, 'testmanager/js/testmanager.js')
        
        insert1 = tag.div()(
                    self._get_breadcrumb_markup(formatter, planid, page_name, mode),
                    tag.br(), tag.br(), tag.br(), 
                    tag.span(style='font-size: large; font-weight: bold;')(
                        self._get_testcase_status_markup(formatter, has_status, page_name, planid),
                        tag.span()(                            
                            LABELS['test_case']
                            )
                        )
                    )
        
        insert2 = tag.div(class_='field', style='marging-top: 60px;')(
                    tag.br(), tag.br(),
                    self._get_custom_fields_markup(tcip, tmmodelprovider.get_custom_fields_for_realm('testcaseinplan'), ('page_name', 'status')),
                    tag.br(), 
                    tag.script('var baseLocation="'+req.href()+'";', type='text/javascript'),
                    self._get_testcase_change_status_markup(formatter, has_status, page_name, planid),
                    tag.br(), tag.br(),
                    tag.input(type='button', value=LABELS['open_ticket_button'], onclick='creaTicket("'+tc_name+'", "'+planid+'", "'+plan_name+'")'),
                    HTML('&nbsp;&nbsp;'), 
                    tag.br(), tag.br(), 
                    self._get_testcase_status_history_markup(formatter, has_status, page_name, planid),
                    tag.br(), tag.br()
                    )
                    
        return stream | Transformer('//div[contains(@class,"wikipage")]').after(insert2) | Transformer('//div[contains(@class,"wikipage")]').before(insert1)
    
    def _get_breadcrumb_markup(self, formatter, planid, page_name, mode='tree'):
        if planid and not planid == '-1':
            # We are in the context of a test plan
            if not page_name.rpartition('_TC')[2] == '':
                # It's a test case
                tp = TestPlan(self.env, planid)
                catpath = tp['page_name']
                return tag.a(href=formatter.req.href.wiki(catpath, planid=planid, mode=mode))(LABELS['back_to_plan'])
            else:
                # It's a test plan
                return tag.a(href=formatter.req.href.wiki(page_name))(LABELS['back_to_catalog'])
                
        else:
            breadcrumb_macro = TestCaseBreadcrumbMacro(self.env)
            return HTML(breadcrumb_macro.expand_macro(formatter, None, page_name))

    def _get_testcase_status_markup(self, formatter, has_status, page_name, planid):
        if has_status:
            testcase_status_macro = TestCaseStatusMacro(self.env)
            return tag.span(style='float: left; padding-top: 4px; padding-right: 5px;')(
                            HTML(testcase_status_macro.expand_macro(formatter, None, 'page_name='+page_name+',planid='+planid))
                            )
        else:
            return tag.span()()

    def _get_testcase_change_status_markup(self, formatter, has_status, page_name, planid):
        if has_status:
            testcase_change_status_macro = TestCaseChangeStatusMacro(self.env)
            return HTML(testcase_change_status_macro.expand_macro(formatter, None, 'page_name='+page_name+',planid='+planid))
        else:
            return tag.span()()
            
    def _get_testcase_status_history_markup(self, formatter, has_status, page_name, planid):
        if has_status:
            testcase_status_history_macro = TestCaseStatusHistoryMacro(self.env)
            return HTML(testcase_status_history_macro.expand_macro(formatter, None, 'page_name='+page_name+',planid='+planid))
        else:
            return tag.span()()

    def _get_testplan_list_markup(self, formatter, cat_name):
        testplan_list_macro = TestPlanListMacro(self.env)
        return HTML(testplan_list_macro.expand_macro(formatter, None, 'catalog_path='+cat_name))

    def _get_custom_fields_markup(self, obj, fields, props=None):
        obj_key = obj.gey_key_string()

        obj_props = ''
        if props is not None:
            obj_props = obj.get_values_as_string(props)
        
        result = '<input type="hidden" value="' + obj_key + '" id="obj_key_field"></input>'
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
                result += '<span class="rightIcon" style="display: none;" title="'+LABELS['edit_label']+'" onclick="editField(\''+f['name']+'\')" id="field_pencilIcon'+f['name']+'"></span>'
                result += '</td>'

                result += '<td>'
                result += '<input style="display: none;" type="button" onclick="sendUpdate(\''+obj.realm+'\', \'' + f['name']+'\')" id="update_button_'+f['name']+'" name="update_button_'+f['name']+'" value="'+LABELS['update_button']+'"></input>'
                result += '</td>'

            # TODO Support other field types
            
            result += '</tr>'

        result += '</tbody></table>'

        return HTML(result)

