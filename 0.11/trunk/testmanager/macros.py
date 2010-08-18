# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi, Marco Cipriani
#

import re

from genshi.builder import tag

from trac.resource import Resource, get_resource_url
from trac.core import *
from trac.wiki.macros import WikiMacroBase
from trac.wiki.api import WikiSystem, parse_args
from trac.wiki.model import WikiPage

from testmanager.api import TestManagerSystem
from testmanager.util import get_page_title
from testmanager.labels import *


# Macros

class TestCaseBreadcrumbMacro(WikiMacroBase):
    """Display a breadcrumb with the path to the current catalog or test case.

    Usage:

    {{{
    [[TestCaseBreadcrumb()]]
    }}}
    """
    
    def expand_macro(self, formatter, name, content):
        if not content:
            content = formatter.resource.id
        
        req = formatter.req

        return _build_testcases_breadcrumb(self.env, req, content)

        

class TestCaseTreeMacro(WikiMacroBase):
    """Display a tree with catalogs and test cases.

    Usage:

    {{{
    [[TestCaseTree()]]
    }}}
    """
    
    def expand_macro(self, formatter, name, content):
        if not content:
            content = formatter.resource.id
        
        req = formatter.req

        return _build_catalog_tree(self.env, req, content)


class TestPlanTreeMacro(WikiMacroBase):
    """Display a tree with catalogs and test cases in a test plan. 
       Includes test case status in the plan.

    Usage:

    {{{
    [[TestPlanTree(planid=<Plan ID>, catalog_path=<Catalog path>)]]
    }}}
    """
    
    def expand_macro(self, formatter, name, content):
        args, kw = parse_args(content)

        planid = int(kw.get('planid', -1))
        catpath = kw.get('catalog_path', 'TC')
        
        req = formatter.req

        return _build_testplan_tree(self.env, req, planid, catpath)


class TestPlanListMacro(WikiMacroBase):
    """Display a list of all the plans available for a test catalog.

    Usage:

    {{{
    [[TestPlanListMacro(catalog_path=<Catalog path>)]]
    }}}
    """
    
    def expand_macro(self, formatter, name, content):
        args, kw = parse_args(content)

        catpath = kw.get('catalog_path', 'TC')
        
        req = formatter.req

        return _build_testplan_list(self.env, req, catpath)

        
class TestCaseStatusMacro(WikiMacroBase):
    """Display a colored icon according to the test case status in the specified test plan.

    Usage:

    {{{
    [[TestCaseStatus(planid=<Plan ID>)]]
    }}}
    """
    
    def expand_macro(self, formatter, name, content):
        args, kw = parse_args(content)

        planid = int(kw.get('planid', -1))
        curpage = kw.get('page_name', 'TC')
        
        req = formatter.req

        return _build_testcase_status(self.env, req, planid, curpage)

        
class TestCaseChangeStatusMacro(WikiMacroBase):
    """Display a semaphore to set the test case status in the specified test plan.

    Usage:

    {{{
    [[TestCaseChangeStatus(planid=<Plan ID>)]]
    }}}
    """
    
    def expand_macro(self, formatter, name, content):
        args, kw = parse_args(content)

        planid = int(kw.get('planid', -1))
        curpage = kw.get('page_name', 'TC')
        
        req = formatter.req

        return _build_testcase_change_status(self.env, req, planid, curpage)

        
class TestCaseStatusHistoryMacro(WikiMacroBase):
    """Display the history of status changes of a test case in the specified test plan.

    Usage:

    {{{
    [[TestCaseStatusHistory(planid=<Plan ID>)]]
    }}}
    """
    
    def expand_macro(self, formatter, name, content):
        args, kw = parse_args(content)

        planid = int(kw.get('planid', -1))
        curpage = kw.get('page_name', 'TC')
        
        req = formatter.req

        return _build_testcase_status_history(self.env, req, planid, curpage)

        

# Internal methods

def _build_testcases_breadcrumb(env,req,curpage):
    test_manager_system = TestManagerSystem(env)

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
    
    breadcrumb = [{'name': 'TC', 'title': LABELS['all_catalogs'], 'id': 'TC'}]

    for i, tc in enumerate(tokens):
        curr_path += '_'+tc
        page = WikiPage(env, curr_path)
        page_title = get_page_title(page.text)
        
        breadcrumb[(i+1):] = [{'name': tc, 'title': page_title, 'id': curr_path}]

        if tc == cat_name:
            break

    text = ''

    text +='<div>'
    text += _render_breadcrumb(breadcrumb)
    text +='</div>'

    return text    
            

def _build_catalog_tree(env,req,curpage):
    test_manager_system = TestManagerSystem(env)

    # Determine current catalog name
    cat_name = 'TC'
    if curpage.find('_TC') >= 0:
        cat_name = curpage.rpartition('_TC')[0].rpartition('_')[2]
    elif not curpage == 'TC':
        cat_name = curpage.rpartition('_')[2]
    # Create the catalog subtree model
    components = {'name': curpage, 'childrenC': {},'childrenT': {}, 'tot': 0}

    for subpage_name in sorted(WikiSystem(env).get_pages(curpage+'_')):
        subpage = WikiPage(env, subpage_name)
        subpage_title = get_page_title(subpage.text)

        path_name = subpage_name.partition(curpage+'_')[2]
        tokens = path_name.split("_")
        parent = components
        ltok = len(tokens)
        count = 1
        curr_path = curpage
        for tc in tokens:
            curr_path += '_'+tc
            
            if tc == '':
                break

            if not tc.startswith('TC'):
                comp = {}
                if (tc not in parent['childrenC']):
                    comp = {'id': curr_path, 'name': tc, 'title': subpage_title, 'childrenC': {},'childrenT': {}, 'tot': 0, 'parent': parent}
                    parent['childrenC'][tc]=comp
                else:
                    comp = parent['childrenC'][tc]
                parent = comp

            else:
                # It is a test case page
                parent['childrenT'][tc]={'id':curr_path, 'title': subpage_title, 'status': 'NONE'}
                compLoop = parent
                while (True):
                    compLoop['tot']+=1
                    if ('parent' in compLoop):
                        compLoop = compLoop['parent']
                    else:
                        break
            count+=1

    # Generate the markup
    ind = {'count': 0}
    text = ''

    text +='<div style="padding: 0px 0px 10px 10px">'+LABELS['filter_label']+' <input id="tcFilter" title="'+LABELS['filter_help']+'" type="text" size="40" onkeyup="starthighlight(this.value)"/>&nbsp;&nbsp;<span id="searchResultsNumberId" style="font-weight: bold;"></span></div>'
    text +='<div style="font-size: 0.8em;padding-left: 10px"><a style="margin-right: 10px" onclick="toggleAll(true)" href="javascript:void(0)">'+LABELS['expand_all']+'</a><a onclick="toggleAll(false)" href="javascript:void(0)">'+LABELS['collapse_all']+'</a></div>';
    text +='<div id="ticketContainer">'

    text += _render_subtree(-1, components, ind, 0)
    
    text +='</div>'
    return text
    
def _build_testplan_tree(env, req, planid, curpage):
    test_manager_system = TestManagerSystem(env)

    # Determine current catalog name
    cat_name = 'TC'
    if curpage.find('_TC') >= 0:
        cat_name = curpage.rpartition('_TC')[0].rpartition('_')[2]
    elif not curpage == 'TC':
        cat_name = curpage.rpartition('_')[2]
    # Create the catalog subtree model
    components = {'name': curpage, 'childrenC': {},'childrenT': {}, 'tot': 0}

    for subpage_name in sorted(WikiSystem(env).get_pages(curpage+'_')):
        subpage = WikiPage(env, subpage_name)
        subpage_title = get_page_title(subpage.text)

        path_name = subpage_name.partition(curpage+'_')[2]
        tokens = path_name.split("_")
        parent = components
        ltok = len(tokens)
        count = 1
        curr_path = curpage
        for tc in tokens:
            curr_path += '_'+tc
            
            if tc == '':
                break

            if not tc.startswith('TC'):
                comp = {}
                if (tc not in parent['childrenC']):
                    comp = {'id': curr_path, 'name': tc, 'title': subpage_title, 'childrenC': {},'childrenT': {}, 'tot': 0, 'parent': parent}
                    parent['childrenC'][tc]=comp
                else:
                    comp = parent['childrenC'][tc]
                parent = comp

            else:
                # It is a test case page
                status = test_manager_system.get_testcase_status(tc.partition('TC')[2], planid)
                parent['childrenT'][tc]={'id':curr_path, 'title': subpage_title, 'status': status}
                compLoop = parent
                while (True):
                    compLoop['tot']+=1
                    if ('parent' in compLoop):
                        compLoop = compLoop['parent']
                    else:
                        break
            count+=1

    # Generate the markup
    ind = {'count': 0}
    text = ''

    text +='<div style="padding: 0px 0px 10px 10px">'+LABELS['filter_label']+' <input id="tcFilter" title="'+LABELS['filter_help']+'" type="text" size="40" onkeyup="starthighlight(this.value)"/>&nbsp;&nbsp;<span id="searchResultsNumberId" style="font-weight: bold;"></span></div>'
    text +='<div style="font-size: 0.8em;padding-left: 10px"><a style="margin-right: 10px" onclick="toggleAll(true)" href="javascript:void(0)">'+LABELS['expand_all']+'</a><a onclick="toggleAll(false)" href="javascript:void(0)">'+LABELS['collapse_all']+'</a></div>';
    text +='<div id="ticketContainer">'

    text += _render_subtree(planid, components, ind, 0)
    
    text +='</div>'
    return text


def _build_testplan_list(env, req, curpage):
    test_manager_system = TestManagerSystem(env)

    # Determine current catalog name
    cat_name = 'TC'
    catid = -1
    if curpage.find('_TC') >= 0:
        cat_name = curpage.rpartition('_TC')[0].rpartition('_')[2]
        catid = int(cat_name.rpartition('TT')[2])
    elif not curpage == 'TC':
        cat_name = curpage.rpartition('_')[2]
        catid = int(cat_name.rpartition('TT')[2])
        
    markup, num_plans = test_manager_system.get_testplan_list_markup(catid)
        
    text = '<form id="testPlanList"><fieldset id="testPlanListFields" class="collapsed"><legend class="foldable" style="cursor: pointer;"><a href="#no4"  onclick="expandCollapseSection(\'testPlanListFields\')">'+LABELS['test_plan_list']+' ('+str(num_plans)+')</a></legend>'
    text += markup
    text += '</fieldset></form>'

    return text

    
# Render the breadcrumb
def _render_breadcrumb(breadcrumb):
    text = ''
    path_len = len(breadcrumb)
    for i, x in enumerate(breadcrumb):
        text += '<span name="breadcrumb" style="cursor: pointer; color: #BB0000; margin-left: 10px; margin-right: 10px; font-size: 0.8em;" '
        text += ' onclick="window.location=\''+x['id']+'\'">'+x['title']
        
        if i < path_len-1:
            text += '&nbsp;&nbsp;->'
        
        text += '</span>'
        
    return text
 
# Render the subtree
def _render_subtree(planid, component, ind, level, path=''):
    data = component
    text = ''
    if (level == 0):
        data = component['childrenC']
        text +='<ul style="list-style: none;">';        
    keyList = data.keys()
    sortedList = sorted(keyList)
    for x in sortedList:
        ind['count'] += 1
        text+='<li style="font-weight: normal">'
        comp = data[x]
        fullpath = path+x+" - "
        if ('childrenC' in comp):
            subcData=comp['childrenC']
            
            toggle_icon = '../chrome/testmanager/images/plus.png'
            toggable = 'toggable'
            if (len(comp['childrenC']) + len(comp['childrenT'])) == 0:
                toggable = 'nope'
                toggle_icon = '../chrome/testmanager/images/empty.png'
                
            index = str(ind['count'])
            
            text+='<span name="'+toggable+'" style="cursor: pointer" id="b_'+index+'"><span onclick="toggle(\'b_'+index+'\')"><img class="iconElement" src="'+toggle_icon+'" /></span><span id="l_'+index+'" onmouseover="underlineLink(\'l_'+index+'\')" onmouseout="removeUnderlineLink(\'l_'+index+'\')" onclick="window.location=\''+comp['id']+'\'" title='+LABELS['open']+'>'+comp['title']+'</span></span><span style="color: gray;">&nbsp;('+str(comp['tot'])+')</span>'
            text +='<ul id="b_'+index+'_list" style="display:none;list-style: none;">';
            ind['count']+=1
            text+=_render_subtree(planid, subcData, ind, level+1, fullpath)
            if ('childrenT' in comp):            
                mtData=comp['childrenT']
                text+=_render_testcases(planid, mtData)
        text+='</ul>'
        text+='</li>'
    if (level == 0):
        if ('childrenT' in component):            
            cmtData=component['childrenT']
            text+=_render_testcases(planid, cmtData)
        text+='</ul>'        
    return text


def _render_testcases(planid, data): 
    text=''
    keyList = data.keys()
    sortedList = sorted(keyList)
    for x in sortedList:
        tick = data[x]
        status = tick['status']
        has_status = True
        if status == 'SUCCESSFUL':
            statusIcon='../chrome/testmanager/images/green.png'
        elif status == 'FAILED':
            statusIcon='../chrome/testmanager/images/red.png'
        elif status == 'TO_BE_TESTED':
            statusIcon='../chrome/testmanager/images/yellow.png'
        else:
            has_status = False

        if has_status:
            statusLabel = LABELS[status]
            text+="<li style='font-weight: normal;'><img class='iconElement' src='"+statusIcon+"' title='"+statusLabel+"'></img><a href='"+tick['id']+"?planid="+str(planid)+"' target='_blank'>"+tick['title']+"&nbsp;</a><span style='display: none;'>"+statusLabel+"</span></li>"
        else:
            text+="<li style='font-weight: normal;'><a href='"+tick['id']+"' target='_blank'>"+tick['title']+"&nbsp;</a></li>"
            
    return text
    
    
def _build_testcase_status(env, req, planid, curpage):
    test_manager_system = TestManagerSystem(env)

    tc = curpage.rpartition('_TC')[2]
    status = test_manager_system.get_testcase_status(tc, planid)
    
    display = {'SUCCESSFUL': 'none', 'TO_BE_TESTED': 'none', 'FAILED': 'none'}
    display[status] = 'block'
    
    text = ''
    text += '<img style="display: '+display['TO_BE_TESTED']+';" id="tcTitleStatusIconTO_BE_TESTED" src="../chrome/testmanager/images/yellow.png" title="'+LABELS['TO_BE_TESTED']+'"></img></span>'
    text += '<img style="display: '+display['FAILED']+';" id="tcTitleStatusIconFAILED" src="../chrome/testmanager/images/red.png" title="'+LABELS['FAILED']+'"></img></span>'
    text += '<img style="display: '+display['SUCCESSFUL']+';" id="tcTitleStatusIconSUCCESSFUL" src="../chrome/testmanager/images/green.png" title="'+LABELS['SUCCESSFUL']+'"></img></span>'
    
    return text

    
def _build_testcase_change_status(env, req, planid, curpage):
    test_manager_system = TestManagerSystem(env)

    tc = curpage.rpartition('_TC')[2]
    status = test_manager_system.get_testcase_status(tc, planid)
    
    text = ''
    
    text += '<script type="text/javascript">var currStatus = "'+status+'";</script>'

    text += LABELS['change_status_label']
    
    text += '<span style="margin-left: 15px;">'

    border = ''
    if status == 'SUCCESSFUL':
        border = 'border: 2px solid black;'

    text += '<span id="tcStatusSUCCESSFUL" style="padding: 3px; cursor: pointer;'+border+'" onclick="changestate(\''+tc+'\', \''+str(planid)+'\', \'SUCCESSFUL\')">'
    text += '<img src="../chrome/testmanager/images/green.png" title="'+LABELS['SUCCESSFUL']+'"></img></span>'

    border = ''
    if status == 'TO_BE_TESTED':
        border = 'border: 2px solid black;'

    text += '<span id="tcStatusTO_BE_TESTED" style="padding: 3px; cursor: pointer;'+border+'" onclick="changestate(\''+tc+'\', \''+str(planid)+'\', \'TO_BE_TESTED\')">'
    text += '<img src="../chrome/testmanager/images/yellow.png" title="'+LABELS['TO_BE_TESTED']+'"></img></span>'

    border = ''
    if status == 'FAILED':
        border = 'border: 2px solid black;'

    text += '<span id="tcStatusFAILED" style="padding: 3px; cursor: pointer;'+border+'" onclick="changestate(\''+tc+'\', \''+str(planid)+'\', \'FAILED\')">'
    text += '<img src="../chrome/testmanager/images/red.png" title="'+LABELS['FAILED']+'"></img></span>'

    text += '</span>'
    
    return text

    
def _build_testcase_status_history(env,req,planid,curpage):
    test_manager_system = TestManagerSystem(env)

    tc = curpage.rpartition('_TC')[2]
    
    text = '<form id="testCaseHistory"><fieldset id="testCaseHistoryFields" class="collapsed"><legend class="foldable" style="cursor: pointer;"><a href="#no3"  onclick="expandCollapseSection(\'testCaseHistoryFields\')">'+LABELS['status_change_hist']+'</a></legend>'
    text += test_manager_system.get_testcase_status_history_markup(tc, planid)
    text += '</fieldset></form>'

    return text
    
