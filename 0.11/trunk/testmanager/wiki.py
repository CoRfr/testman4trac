# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi, Marco Cipriani
#

import re
import sys
import traceback

import time
from datetime import datetime

from trac.core import *
from trac.web.chrome import add_stylesheet, add_script, ITemplateProvider #, INavigationContributor
from trac.wiki.api import IWikiSyntaxProvider
from trac.resource import Resource, render_resource_link, get_resource_url
from trac.mimeview.api import Context
from trac.web.api import ITemplateStreamFilter, IRequestHandler
from trac.wiki.api import WikiSystem, IWikiPageManipulator, IWikiChangeListener
from trac.wiki.model import WikiPage
from trac.wiki.formatter import Formatter
from trac.util import get_reporter_id
from trac.util.compat import sorted
from trac.util.datefmt import utc, to_timestamp
from genshi.builder import tag
from genshi.filters.transform import Transformer
from genshi.core import Markup
from genshi import HTML

from testmanager.api import TestManagerSystem
from testmanager.macros import TestCaseBreadcrumbMacro, TestCaseTreeMacro, TestPlanTreeMacro, TestPlanListMacro, TestCaseStatusMacro, TestCaseChangeStatusMacro, TestCaseStatusHistoryMacro
from testmanager.labels import *
from testmanager.model import TestCatalog, TestCase, TestCaseInPlan, TestPlan


class WikiTestManagerInterface(Component):
    """Implement generic template provider."""
    
    implements(ITemplateProvider, ITemplateStreamFilter, IRequestHandler, IWikiChangeListener)
    
    # ITemplateProvider
    def get_templates_dirs(self):
        """
            Return the absolute path of the directory containing the provided
            templates
        """
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        """
            Return a list of directories with static resources (such as style
            sheets, images, etc.)
    
            Each item in the list must be a '(prefix, abspath)' tuple. The
            'prefix' part defines the path in the URL that requests to these
            resources are prefixed with.
            
            The 'abspath' is the absolute path to the directory containing the
            resources on the local file system.
        """
        from pkg_resources import resource_filename
        return [('testmanager', resource_filename(__name__, 'htdocs'))]

        
    # IRequestHandler methods

    def match_request(self, req):
        type = req.args.get('type')
        return req.path_info.startswith('/testcreate') and (((type == 'catalog' or type == 'testcase') and ('TEST_MODIFY' in req.perm)) or 
             (type == 'testplan' and ('TEST_PLAN_ADMIN' in req.perm))) 

    def process_request(self, req):
        type = req.args.get('type')
        path = req.args.get('path')
        title = req.args.get('title')
        author = get_reporter_id(req, 'author')

        autosave = req.args.get('autosave', 'false')
        duplicate = req.args.get('duplicate')
        paste = req.args.get('paste')
        tcId = req.args.get('tcId')

        test_manager_system = TestManagerSystem(self.env)
        id = test_manager_system.get_next_id(type)

        pagename = path
        
        if type == 'catalog':
            req.perm.require('TEST_MODIFY')
            pagename += '_TT'+str(id)

            try:
                new_tc = TestCatalog(self.env, id, pagename, '== '+title+' ==', '')
                new_tc.author = author
                new_tc.remote_addr = req.remote_addr
                # This also creates the Wiki page
                new_tc.insert()
            except:
                print "Error adding test catalog!"
                print self._formatExceptionInfo()
                req.redirect(req.path_info)

            # Redirect to see the new wiki page.
            req.redirect(req.href.wiki(pagename))
            
        elif type == 'testplan':
            req.perm.require('TEST_PLAN_ADMIN')
            
            catid = path.rpartition('_TT')[2]

            try:
                # Add the new test plan in the database
                new_tc = TestPlan(self.env, id, catid, pagename, title, author)
                new_tc.insert()

            except:
                print "Error adding test plan!"
                print self._formatExceptionInfo()
                # Back to the catalog
                req.redirect(req.href.wiki(path))

            # Display the new test plan
            req.redirect(req.href.wiki(path, planid=str(id)))
                
        elif type == 'testcase':
            req.perm.require('TEST_MODIFY')
            
            pagename += '_TC'+str(id)
            
            if paste and paste != '':
                # Handle move/paste of the test case into another catalog

                req.perm.require('TEST_PLAN_ADMIN')

                try:
                    catid = path.rpartition('_TT')[2]
                    tcat = TestCatalog(self.env, catid)
                    
                    old_pagename = tcId
                    tc_id = tcId.rpartition('_TC')[2]
                    tc = TestCase(self.env, tc_id)
                    if tc.exists:
                        tc.move_to(tcat)
                    else:
                        print("Test case not found")
                except:
                    print "Error pasting test case!"
                    print self._formatExceptionInfo()
                    req.redirect(req.path_info)
            
                # Redirect to test catalog, forcing a page refresh by means of a random request parameter
                req.redirect(req.href.wiki(pagename.rpartition('_TC')[0], random=str(datetime.now(utc).microsecond)))
                
            elif duplicate and duplicate != '':
                # Duplicate test case
                old_id = tcId.rpartition('_TC')[2]
                old_pagename = tcId
                try:
                    old_tc = TestCase(self.env, old_id, old_pagename)
                    
                    # New test case name will be the old catalog name + the newly generated test case ID
                    author = get_reporter_id(req, 'author')
                    
                    # Create new test case wiki page as a copy of the old one, but change its page path
                    new_tc = old_tc
                    new_tc['page_name'] = pagename
                    new_tc.remote_addr = req.remote_addr
                    # And save it under the new id
                    new_tc.save_as({'id': id})
                except:
                    print "Error duplicating test case!"
                    print self._formatExceptionInfo()
                    req.redirect(req.path_info)

                # Redirect tp allow for editing the copy test case
                req.redirect(req.href.wiki(pagename, action='edit'))
                
            else:
                # Normal creation of a new test case
                try:
                    new_tc = TestCase(self.env, id, pagename, '== '+title+' ==', '')
                    new_tc.author = author
                    new_tc.remote_addr = req.remote_addr
                    # This also creates the Wiki page
                    new_tc.insert()
                except:
                    print "Error adding test case!"
                    print self._formatExceptionInfo()
                    req.redirect(req.path_info)

                # Redirect to edit the test case description
                req.redirect(req.href.wiki(pagename, action='edit'))

        
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
                tc.delete(del_wiki_page=false)
            else:
                print("Test case not found")

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
            insert2.append(tag.div(id='pasteTCHereDiv')(
                        tag.br(), tag.br(),
                        tag.input(type='button', id='pasteTCHereButton', value=LABELS['move_here'], onclick='pasteTestCaseIntoCatalog("'+cat_name+'")')
                    ))
                    
        insert2.append(tag.div(class_='field')(
                    tag.script('var baseLocation="'+req.href()+'";', type='text/javascript'),
                    tag.br(), tag.br(), tag.br(), tag.br(),
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

        add_stylesheet(req, 'testmanager/css/testmanager.css')
        add_stylesheet(req, 'common/css/report.css')

        add_script(req, 'testmanager/js/cookies.js')
        add_script(req, 'testmanager/js/labels.js')
        add_script(req, 'testmanager/js/testmanager.js')

        tree_macro = TestPlanTreeMacro(self.env)
        tp = TestPlan(self.env, planid)
        
        insert1 = tag.div()(
                    tag.a(href=req.href.wiki(page_name))(LABELS['back_to_catalog']),
                    tag.br(), tag.br(), tag.br(), 
                    tag.h1(LABELS['test_plan']+tp['name'])
                    )

        insert2 = tag.div()(
                    HTML(tree_macro.expand_macro(formatter, None, 'planid='+str(planid)+',catalog_path='+page_name)),
                    tag.div(class_='testCaseList')(
                    tag.br(), tag.br(),
                    tag.div(class_='field')(
                        tag.script('var baseLocation="'+req.href()+'";', type='text/javascript'),
                        tag.br(), tag.br(), tag.br(), tag.br(),
                        #tag.input(type='button', value=LABELS['regenerate_plan_button'], onclick='regenerateTestPlan("'+str(planid)+'", "'+page_name+'")')
                        )
                    ))
                    
        insert2.append(tag.div()(tag.br(), tag.br(), tag.br(), tag.br()))
        
        return stream | Transformer('//div[contains(@class,"wikipage")]').after(insert2) | Transformer('//div[contains(@class,"wikipage")]').before(insert1)
        

    def _testcase_wiki_view(self, req, formatter, planid, page_name, stream):
        path_name = req.path_info
        tc_name = path_name.rpartition('/')[2]
        cat_name = path_name.rpartition('/')[2].partition('_TC')[0]
        
        has_status = False
        plan_name = ''
    
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
                    tag.br(), tag.br(), tag.br(), tag.br(),
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
        path_name = req.path_info
        tc_name = path_name.rpartition('/')[2]
        cat_name = path_name.rpartition('/')[2].partition('_TC')[0]
        
        has_status = True
        tp = TestPlan(self.env, planid)
        plan_name = tp['name']
    
        add_stylesheet(req, 'testmanager/css/testmanager.css')
        add_stylesheet(req, 'common/css/report.css')

        add_script(req, 'testmanager/js/cookies.js')
        add_script(req, 'testmanager/js/labels.js')
        add_script(req, 'testmanager/js/testmanager.js')
        
        insert1 = tag.div()(
                    self._get_breadcrumb_markup(formatter, planid, page_name),
                    tag.br(), tag.br(), tag.br(), 
                    tag.span(style='font-size: large; font-weight: bold;')(
                        self._get_testcase_status_markup(formatter, has_status, page_name, planid),
                        tag.span()(                            
                            LABELS['test_case']
                            )
                        )
                    )
        
        insert2 = tag.div(class_='field', style='marging-top: 60px;')(
                    tag.br(), tag.br(), tag.br(), tag.br(),
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
    
    def _get_breadcrumb_markup(self, formatter, planid, page_name):
        if planid and not planid == '-1':
            # We are in the context of a test plan
            if not page_name.rpartition('_TC')[2] == '':
                # It's a test case
                tp = TestPlan(self.env, planid)
                catpath = tp['page_name']
                return tag.a(href=formatter.req.href.wiki(catpath, planid=planid))(LABELS['back_to_plan'])
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

        
    def _formatExceptionInfo(maxTBlevel=5):
        cla, exc, trbk = sys.exc_info()
        excName = cla.__name__
        
        try:
            excArgs = exc.__dict__["args"]
        except KeyError:
            excArgs = "<no args>"
        
        excTb = traceback.format_tb(trbk, maxTBlevel)
        return (excName, excArgs, excTb)

        
