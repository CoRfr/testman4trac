# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi
#

import copy

from datetime import datetime
from StringIO import StringIO

from trac.core import *
from trac.mimeview.api import Context
from trac.util import format_datetime, format_date
from trac.wiki.macros import WikiMacroBase
from trac.wiki.api import WikiSystem, parse_args
from trac.wiki.formatter import Formatter, format_to_html
from trac.wiki.model import WikiPage
from trac.wiki.parser import WikiParser

from genshi import HTML
from genshi.builder import tag
from genshi.core import Stream, Markup, escape

from tracgenericclass.model import GenericClassModelProvider
from tracgenericclass.util import *

from testmanager.api import TestManagerSystem
from testmanager.model import TestCatalog, TestCase, TestCaseInPlan, TestPlan
from testmanager.util import *

try:
    from testmanager.api import _, tag_, N_
except ImportError:
	from trac.util.translation import _, N_
	tag_ = _

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

        args, kw = parse_args(content)

        page_name = kw.get('page_name', 'TC')
        planid = kw.get('planid', '-1')
        mode = kw.get('mode', 'tree')
        fulldetails = kw.get('fulldetails', 'False')
        
        fulldetails = (fulldetails == 'True')
        
        req = formatter.req

        return _build_testcases_breadcrumb(self.env, req, page_name, planid, mode, fulldetails)
        

class TestCaseTreeMacro(WikiMacroBase):
    """Display a tree with catalogs and test cases.

    Usage:

    {{{
    [[TestCaseTree(mode={'tree'|'tree_table'}, fulldetails={'True|False})]]
    }}}
    """
    
    def expand_macro(self, formatter, name, content):
        args, kw = parse_args(content)

        catpath = kw.get('catalog_path', 'TC')
        mode = kw.get('mode', 'tree')
        fulldetails = kw.get('fulldetails', 'False')
        
        fulldetails = (fulldetails == 'True')
        
        req = formatter.req

        return _build_catalog_tree(self.env, req, formatter.context, catpath, mode, fulldetails)
        

class TestPlanTreeMacro(WikiMacroBase):
    """Display a tree table with catalogs and test cases in a test plan. 
       Includes test case status in the plan.

    Usage:

    {{{
    [[TestPlanTree(planid=<Plan ID>, catalog_path=<Catalog path>, mode={'tree'|'tree_table'}, sortby={'modification_time'|'name'})]]
    }}}
    """
    
    def expand_macro(self, formatter, name, content):
        args, kw = parse_args(content)

        planid = kw.get('planid', '-1')
        catpath = kw.get('catalog_path', 'TC')
        mode = kw.get('mode', 'tree')
        sortby = kw.get('sortby', 'name')
        
        req = formatter.req

        return _build_testplan_tree(self.env, req, formatter.context, planid, catpath, mode, sortby)


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
        mode = kw.get('mode', 'tree')
        fulldetails = kw.get('fulldetails', 'False')
        
        fulldetails = (fulldetails == 'True')
        
        req = formatter.req

        return _build_testplan_list(self.env, req, catpath, mode, fulldetails)

        
class TestCaseStatusMacro(WikiMacroBase):
    """Display a colored icon according to the test case status in the specified test plan.

    Usage:

    {{{
    [[TestCaseStatus(planid=<Plan ID>)]]
    }}}
    """
    
    def expand_macro(self, formatter, name, content):
        args, kw = parse_args(content)

        planid = kw.get('planid', '-1')
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

        planid = kw.get('planid', '-1')
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

        planid = kw.get('planid', '-1')
        curpage = kw.get('page_name', 'TC')
        
        req = formatter.req

        return _build_testcase_status_history(self.env, req, planid, curpage)

        

# Internal methods

def _build_testcases_breadcrumb(env, req, curpage, planid, mode, fulldetails):
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
        page = WikiPage(env, curr_path)
        page_title = get_page_title(page.text)
        
        breadcrumb[(i+1):] = [{'name': tc, 'title': page_title, 'id': curr_path}]

        if tc == cat_name:
            break

    text = ''

    text +='<div>'
    text += _render_breadcrumb(breadcrumb, planid, mode, fulldetails)
    text +='</div>'

    return text    
            

def _build_catalog_tree(env,req, context, curpage, mode='tree', fulldetails=False):
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
    components = {'name': curpage, 'childrenC': {},'childrenT': {}, 'tot': 0}

    unique_idx = 0

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
            if tc == '':
                break

            curr_path += '_'+tc
            
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
                tc_id = tc.rpartition('TC')[2]
                
                if subpage_title in parent['childrenT']:
                    unique_idx += 1
                    key = subpage_title+str(unique_idx)
                else:
                    key = subpage_title
                    
                parent['childrenT'][key]={'id':curr_path, 'tc_id':tc_id, 'title': subpage_title, 'status': '__none__'}
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

    if mode == 'tree':
        text +='<div style="padding: 0px 0px 10px 10px">'+_("Filter:")+' <input id="tcFilter" title="'+_("Type the test to search for, even more than one word. You can also filter on the test case status (untested, successful, failed).")+'" type="text" size="40" onkeyup="starthighlight(this.value)"/>&nbsp;&nbsp;<span id="searchResultsNumberId" style="font-weight: bold;"></span></div>'
        text +='<div style="font-size: 0.8em;padding-left: 10px"><a style="margin-right: 10px" onclick="toggleAll(true)" href="javascript:void(0)">'+_("Expand all")+'</a><a onclick="toggleAll(false)" href="javascript:void(0)">'+_("Collapse all")+'</a></div>';
        text +='<div id="ticketContainer">'

        text += _render_subtree(env, '-1', components, ind, 0)
        
        text +='</div>'
        
    elif mode == 'tree_table':
        tcat_fields = GenericClassModelProvider(env).get_custom_fields_for_realm('testcatalog')
        tcat_has_custom = tcat_fields is not None and len(tcat_fields) > 0
        
        tc_fields = GenericClassModelProvider(env).get_custom_fields_for_realm('testcase')
        tc_has_custom = tc_fields is not None and len(tc_fields) > 0
        
        custom_ctx = {
            'testcatalog': [tcat_has_custom, tcat_fields],
            'testcase': [tc_has_custom, tc_fields],
            'testcaseinplan': [False, None]
            }

        text +='<div style="padding: 0px 0px 10px 10px">'+_("Filter:")+' <input id="tcFilter" title="'+_("Type the test to search for, even more than one word. You can also filter on the test case status (untested, successful, failed).")+'" type="text" size="40" onkeyup="starthighlightTable(this.value)"/>&nbsp;&nbsp;<span id="searchResultsNumberId" style="font-weight: bold;"></span></div>'
        text += '<form id="testCatalogRunBook"><fieldset id="testCatalogRunBookFields" class="expanded">'
        text += '<table id="testcaseList" class="listing"><thead><tr>';
        
        # Common columns
        text += '<th>'+_("Name")+'</th>'
        
        # Custom testcatalog columns
        if tcat_has_custom:
            for f in tcat_fields:
                if f['type'] == 'text':
                    text += '<th>'+f['label']+'</th>'

        # Base testcase columns
        text += '<th>'+_("ID")+'</th>'

        # Custom testcase columns
        if tc_has_custom:
            for f in tc_fields:
                if f['type'] == 'text':
                    text += '<th>'+f['label']+'</th>'
        
        # Test case full details
        if fulldetails:
            text += '<th>'+_("Description")+'</th>'
            
        text += '</tr></thead><tbody>';
        
        text += _render_subtree_as_table(env, context, None, components, ind, 0, custom_ctx, fulldetails=fulldetails)
        
        text += '</tbody></table>'
        text += '</fieldset></form>'
    
    return text
    
def _build_testplan_tree(env, req, context, planid, curpage, mode='tree',sortby='name'):
    testmanagersystem = TestManagerSystem(env)
    default_status = testmanagersystem.get_default_tc_status()
    
    # Determine current catalog name
    cat_name = 'TC'
    if curpage.find('_TC') >= 0:
        cat_name = curpage.rpartition('_TC')[0].rpartition('_')[2]
    elif not curpage == 'TC':
        cat_name = curpage.rpartition('_')[2]

    tp = TestPlan(env, planid)

    # Create the catalog subtree model
    components = {'name': curpage, 'childrenC': {},'childrenT': {}, 'tot': 0}

    unique_idx = 0

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
                tc_id = tc.partition('TC')[2]
                tcip = TestCaseInPlan(env, tc_id, planid)
                if tcip.exists:
                    for ts, author, status in tcip.list_history():
                        break
                    
                    if not isinstance(ts, datetime):
                        ts = from_any_timestamp(ts)

                else:
                    ts = tp['time']
                    author = tp['author']
                    status = default_status
                
                if sortby == 'name':
                    key = subpage_title
                else:
                    key = ts.isoformat()

                if key in parent['childrenT']:
                    unique_idx += 1
                    key = key+str(unique_idx)
                    
                parent['childrenT'][key]={'id':curr_path, 'tc_id': tc_id, 'title': subpage_title, 'status': status.lower(), 'ts': ts, 'author': author}
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

    if mode == 'tree':
        text +='<div style="padding: 0px 0px 10px 10px">'+_("Filter:")+' <input id="tcFilter" title="'+_("Type the test to search for, even more than one word. You can also filter on the test case status (untested, successful, failed).")+'" type="text" size="40" onkeyup="starthighlight(this.value)"/>&nbsp;&nbsp;<span id="searchResultsNumberId" style="font-weight: bold;"></span></div>'
        text +='<div style="font-size: 0.8em;padding-left: 10px"><a style="margin-right: 10px" onclick="toggleAll(true)" href="javascript:void(0)">'+_("Expand all")+'</a><a onclick="toggleAll(false)" href="javascript:void(0)">'+_("Collapse all")+'</a></div>';
        text +='<div id="ticketContainer">'
        text += _render_subtree(env, planid, components, ind, 0)
        text +='</div>'

    elif mode == 'tree_table':
        tcat_fields = GenericClassModelProvider(env).get_custom_fields_for_realm('testcatalog')
        tcat_has_custom = tcat_fields is not None and len(tcat_fields) > 0
        
        tc_fields = GenericClassModelProvider(env).get_custom_fields_for_realm('testcase')
        tc_has_custom = tc_fields is not None and len(tc_fields) > 0
        
        tcip_fields = GenericClassModelProvider(env).get_custom_fields_for_realm('testcaseinplan')
        tcip_has_custom = tcip_fields is not None and len(tcip_fields) > 0

        custom_ctx = {
            'testcatalog': [tcat_has_custom, tcat_fields],
            'testcase': [tc_has_custom, tc_fields],
            'testcaseinplan': [tcip_has_custom, tcip_fields]
            }

        text +='<div style="padding: 0px 0px 10px 10px">'+_("Filter:")+' <input id="tcFilter" title="'+_("Type the test to search for, even more than one word. You can also filter on the test case status (untested, successful, failed).")+'" type="text" size="40" onkeyup="starthighlightTable(this.value)"/>&nbsp;&nbsp;<span id="searchResultsNumberId" style="font-weight: bold;"></span></div>'
        text += '<form id="testPlan"><fieldset id="testPlanFields" class="expanded">'
        text += '<table id="testcaseList" class="listing"><thead><tr>';

        # Common columns
        text += '<th>'+_("Name")+'</th>'
        
        # Custom testcatalog columns
        if custom_ctx['testcatalog'][0]:
            for f in custom_ctx['testcatalog'][1]:
                if f['type'] == 'text':
                    text += '<th>'+f['label']+'</th>'

        # Base testcase columns
        text += '<th>'+_("ID")+'</th>'

        #Custom testcase columns
        if custom_ctx['testcase'][0]:
            for f in custom_ctx['testcase'][1]:
                if f['type'] == 'text':
                    text += '<th>'+f['label']+'</th>'

        # Base testcaseinplan columns
        text += '<th>'+_("Status")+'</th><th>'+_("Author")+'</th><th>'+_("Last Change")+'</th>'
        
        # Custom testcaseinplan columns
        if custom_ctx['testcaseinplan'][0]:
            for f in custom_ctx['testcaseinplan'][1]:
                if f['type'] == 'text':
                    text += '<th>'+f['label']+'</th>'

        text += '</tr></thead><tbody>';
        
        text += _render_subtree_as_table(env, context, planid, components, ind, 0, custom_ctx)

        text += '</tbody></table>'
        text += '</fieldset></form>'

    return text


def _build_testplan_list(env, req, curpage, mode, fulldetails):
    # Determine current catalog name
    cat_name = 'TC'
    catid = '-1'
    if curpage.find('_TC') >= 0:
        cat_name = curpage.rpartition('_TC')[0].rpartition('_')[2]
        catid = cat_name.rpartition('TT')[2]
    elif not curpage == 'TC':
        cat_name = curpage.rpartition('_')[2]
        catid = cat_name.rpartition('TT')[2]
    
    if 'TEST_PLAN_ADMIN' in req.perm:
        show_delete_button = True
    else:
        show_delete_button = False
    
    markup, num_plans = _render_testplan_list(env, catid, mode, fulldetails, show_delete_button)

    text = '<form id="testPlanList"><fieldset id="testPlanListFields" class="collapsed"><legend class="foldable" style="cursor: pointer;"><a href="#no4"  onclick="expandCollapseSection(\'testPlanListFields\')">'+_("Available Test Plans")+' ('+str(num_plans)+')</a></legend>'
    text += markup
    text += '</fieldset></form>'

    return text
    
def _render_testplan_list(env, catid, mode, fulldetails, show_delete_button):
    """Returns a test case status in a plan audit trail."""

    delete_icon = '../chrome/testmanager/images/trash.png'

    cat = TestCatalog(env, catid)
    
    result = '<table class="listing"><thead>'
    result += '<tr><th>'+_("Plan Name")+'</th><th>'+_("Author")+'</th><th>'+_("Timestamp")+'</th><th></th></tr>'
    result += '</thead><tbody>'
    
    num_plans = 0
    for tp in sorted(cat.list_testplans(), cmp=lambda x,y: cmp(x['time'],y['time']), reverse=True):
        result += '<tr>'
        result += '<td><a title="'+_("Open Test Plan")+'" href="'+tp['page_name']+'?planid='+tp['id']+'">'+tp['name']+'</a></td>'
        result += '<td>'+tp['author']+'</td>'
        result += '<td>'+format_datetime(tp['time'])+'</td>'
        
        if show_delete_button:
            result += '<td style="cursor: pointer;"><img class="iconElement" alt="'+_("Delete")+'" title="'+_("Delete")+'" src="'+delete_icon+'" onclick="deleteTestPlan(\'../testdelete?type=testplan&path='+tp['page_name']+'&mode='+mode+'&fulldetails='+str(fulldetails)+'&planid='+tp['id']+'\')"/></td>'
        else:
            result += '<td></td>'
        
        result += '</tr>'
        num_plans += 1

    result += '</tbody></table>'

    return result, num_plans
    
# Render the breadcrumb
def _render_breadcrumb(breadcrumb, planid, mode, fulldetails):
    plan_ref = ''
    if planid is not None and not planid == '-1':
        plan_ref = '&planid='+planid
    
    text = ''
    path_len = len(breadcrumb)
    for i, x in enumerate(breadcrumb):
        if i == 0:
            plan_param = ''
        else:
            plan_param = plan_ref
    
        text += '<span name="breadcrumb" style="cursor: pointer; color: #BB0000; margin-left: 10px; margin-right: 5px; font-size: 0.8em;" '
        text += ' onclick="window.location=\''+x['id']+'?mode='+mode+plan_param+'&fulldetails='+str(fulldetails)+'\'">'+x['title']
        
        if i < path_len-1:
            text += '&nbsp;&nbsp;->'
        
        text += '</span>'
        
    return text
 
# Render the subtree
def _render_subtree(env, planid, component, ind, level):
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
                
            text+='<span name="'+toggable+'" style="cursor: pointer" id="b_'+index+'"><span onclick="toggle(\'b_'+index+'\')"><img class="iconElement" src="'+toggle_icon+'" /></span><span id="l_'+index+'" onmouseover="underlineLink(\'l_'+index+'\')" onmouseout="removeUnderlineLink(\'l_'+index+'\')" onclick="window.location=\''+comp['id']+plan_param+'\'" title='+_("Open")+'>'+comp['title']+'</span></span><span style="color: gray;">&nbsp;('+str(comp['tot'])+')</span>'
            text +='<ul id="b_'+index+'_list" style="display:none;list-style: none;">';
            ind['count']+=1
            text+=_render_subtree(env, planid, subcData, ind, level+1)
            if ('childrenT' in comp):            
                mtData=comp['childrenT']
                text+=_render_testcases(env, planid, mtData)
        text+='</ul>'
        text+='</li>'
    if (level == 0):
        if ('childrenT' in component):            
            cmtData=component['childrenT']
            text+=_render_testcases(env, planid, cmtData)
        text+='</ul>'        
    return text

def _render_testcases(env, planid, data): 
    
    testmanagersystem = TestManagerSystem(env)
    tc_statuses = testmanagersystem.get_tc_statuses_by_name()
    
    text=''
    keyList = data.keys()
    sortedList = sorted(keyList)
    for x in sortedList:
        tick = data[x]
        status = tick['status']
        has_status = True
        if status is not None and len(status) > 0 and status != '__none__':
            stat_meaning = tc_statuses[status][0]
            if stat_meaning == 'green':
                statusIcon='../chrome/testmanager/images/green.png'
            elif stat_meaning == 'yellow':
                statusIcon='../chrome/testmanager/images/yellow.png'
            elif stat_meaning == 'red':
                statusIcon='../chrome/testmanager/images/red.png'
        else:
            has_status = False

        if has_status:
            statusLabel = tc_statuses[status][1]
            text+="<li name='tc_node' style='font-weight: normal;' onmouseover='showPencil(\"pencilIcon"+tick['id']+"\", true)' onmouseout='hidePencil(\"pencilIcon"+tick['id']+"\", false)'><img class='iconElement' src='"+statusIcon+"' title='"+statusLabel+"'></img><a href='"+tick['id']+"?planid="+planid+"' target='_blank'>"+tick['title']+"&nbsp;</a><span style='display: none;'>"+statusLabel+"</span><span><a class='rightIcon' style='display: none;' title='"+_("Edit the Test Case")+"' href='"+tick['id']+"?action=edit&planid="+planid+"' target='_blank' id='pencilIcon"+tick['id']+"'></a></span></li>"
        else:
            text+="<li name='tc_node' style='font-weight: normal;' onmouseover='showPencil(\"pencilIcon"+tick['id']+"\", true)' onmouseout='hidePencil(\"pencilIcon"+tick['id']+"\", false)'><input name='select_tc_checkbox' value='"+tick['id']+"' type='checkbox' style='display: none;float: left; position: relative; top: 3px;' /><a href='"+tick['id']+"' target='_blank'>"+tick['title']+"&nbsp;</a><span><a class='rightIcon' style='display: none;' title='"+_("Edit the Test Case")+"' href='"+tick['id']+"?action=edit' target='_blank' id='pencilIcon"+tick['id']+"'></a></span></li>"
            
    return text
        
def _build_testcase_status(env, req, planid, curpage):
    testmanagersystem = TestManagerSystem(env)
    tc_statuses = testmanagersystem.get_tc_statuses_by_name()
    
    tc_id = curpage.rpartition('_TC')[2]
    
    tcip = TestCaseInPlan(env, tc_id, planid)
    if tcip.exists:
        status = tcip['status'].lower()
    else:
        status = testmanagersystem.get_default_tc_status()
    
    # Hide all icons except the one relative to the current test
    # case status
    display = {'green': 'none', 'yellow': 'none', 'red': 'none'}
    
    display[tc_statuses[status][0]] = 'block'
    
    text = ''
    text += '<img style="display: '+display['green']+';" id="tcTitleStatusIcongreen" src="../chrome/testmanager/images/green.png" title="'+_(tc_statuses[status][1])+'"></img></span>'
    text += '<img style="display: '+display['yellow']+';" id="tcTitleStatusIconyellow" src="../chrome/testmanager/images/yellow.png" title="'+_(tc_statuses[status][1])+'"></img></span>'
    text += '<img style="display: '+display['red']+';" id="tcTitleStatusIconred" src="../chrome/testmanager/images/red.png" title="'+_(tc_statuses[status][1])+'"></img></span>'
    
    return text
    
# Render the subtree as a tree table
def _render_subtree_as_table(env, context, planid, component, ind, level, custom_ctx=None, fulldetails=False):
    data = component
    text = ''

    if (level == 0):
        data = component['childrenC']

    keyList = data.keys()
    sortedList = sorted(keyList)
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
            
            # Common columns
            text += '<tr name="testcatalog"><td style="padding-left: '+str(level*30)+'px;"><a href="'+comp['id']+'?mode=tree_table'+plan_param+'&fulldetails='+str(fulldetails)+'" title="'+_("Open")+'">'+comp['title']+'</a></td>'

            # Custom testcatalog columns
            if custom_ctx['testcatalog'][0]:
                tcat_id = comp['id'].rpartition('TT')[2]
                tcat = TestCatalog(env, tcat_id)
                text += _get_custom_fields_columns(tcat, custom_ctx['testcatalog'][1])

            text += '</tr>'
            
            ind['count']+=1
            text+=_render_subtree_as_table(env, context, planid, subcData, ind, level+1, custom_ctx, fulldetails)
            if ('childrenT' in comp):            
                mtData=comp['childrenT']
                text+=_render_testcases_as_table(env, context, planid, mtData, level+1, custom_ctx, fulldetails)

    if (level == 0):
        if ('childrenT' in component):            
            cmtData=component['childrenT']
            text+=_render_testcases_as_table(env, context, planid, cmtData, level+1, custom_ctx, fulldetails)

    return text

def _render_testcases_as_table(env, context, planid, data, level=0, custom_ctx=None, fulldetails=False): 

    testmanagersystem = TestManagerSystem(env)
    tc_statuses = testmanagersystem.get_tc_statuses_by_name()
    
    text=''
    keyList = data.keys()
    sortedList = sorted(keyList)
    for x in sortedList:
        tick = data[x]
        status = tick['status']
        has_status = True
        if status is not None and len(status) > 0 and status != '__none__':
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
        if fulldetails or custom_ctx['testcase'][0]:
            tc = TestCase(env, tick['tc_id'])

        text += '<tr name="testcase">'

        # Common columns
        if has_status:
            statusLabel = tc_statuses[status][1]
            text += '<td style="padding-left: '+str(level*30)+'px;"><img class="iconElement" src="'+statusIcon+'" title="'+statusLabel+'"></img><a href="'+tick['id']+'?planid='+planid+'&mode=tree_table" target="_blank">'+tick['title']+'</a></td>'
        else:
            text += '<td style="padding-left: '+str(level*30)+'px;"><a href="'+tick['id']+'?mode=tree_table&fulldetails='+str(fulldetails)+'" target="_blank">'+tick['title']+'</a></td>'
            
        # Custom testcatalog columns
        if custom_ctx['testcatalog'][0]:
            for f in custom_ctx['testcatalog'][1]:
                text += '<td></td>'

        # Base testcase columns
        text += '<td>'+tick['tc_id']+'</td>'

        # Custom testcase columns
        if tc and tc.exists and custom_ctx['testcase'][0]:
            text += _get_custom_fields_columns(tc, custom_ctx['testcase'][1])

        if has_status:
            # Base testcaseinplan columns
            text += '<td>'+statusLabel+'</td><td>'+tick['author']+'</td><td>'+format_datetime(tick['ts'])+'</td>'

            # Custom testcaseinplan columns
            if custom_ctx['testcaseinplan'][0]:
                tcip = TestCaseInPlan(env, tick['tc_id'], planid)
                text += _get_custom_fields_columns(tcip, custom_ctx['testcaseinplan'][1])

        if fulldetails:
            wikidom = WikiParser(env).parse(tc.description)
            out = StringIO()
            f = Formatter(env, context)
            f.reset(wikidom)
            f.format(wikidom, out, False)
            description = out.getvalue()

            text += '<td>'+description+'</td>'
                    
        text += '</tr>'

    return text
        
def _build_testcase_change_status(env, req, planid, curpage):
    testmanagersystem = TestManagerSystem(env)
    tc_statuses = testmanagersystem.get_tc_statuses_by_name()
    tc_statuses_by_color = testmanagersystem.get_tc_statuses_by_color()

    tc_id = curpage.rpartition('_TC')[2]
    
    tcip = TestCaseInPlan(env, tc_id, planid)
    if tcip.exists:
        status = tcip['status'].lower()
    else:
        status = testmanagersystem.get_default_tc_status()

    status_meaning = tc_statuses[status][0]
    
    text = ''
    text += '<div id="copyright" style="display: none;">Copyright &copy; 2010 <a href="http://apycom.com/">Apycom jQuery Menus</a></div>'
    
    text += '<script type="text/javascript">'
    text += 'var currStatus = "'+status+'";'
    text += 'var currStatusColor = "'+status_meaning+'";'
    
    text += '</script>'

    text += _("Change the Status:")
    
    text += '<span style="margin-left: 15px;">'

    text += '<div id="menu"><ul class="menu">'
    
    for color in ['green', 'yellow', 'red']:
        border = ''
        if status_meaning == color:
            border = 'border: 2px solid black;'
        
        text += '<li><a href="#" class="parent"><span id="tcStatus%s" style="%s"><img src="../chrome/testmanager/images/%s.png"></img></span></a><div><ul>' % (color, border, color) 

        for outcome in tc_statuses_by_color[color]:
            label = tc_statuses_by_color[color][outcome]
            text += '<li><a href="#" onclick="changestate(\''+tc_id+'\', \''+planid+'\', \''+curpage+'\', \''+outcome+'\', \''+color+'\', \'%s\')"><span>%s</span></a></li>' % (label, label)

        text += '</ul></div></li>'
    
    text += '</ul></div>'

    text += '</span>'
    
    return text
    
def _build_testcase_status_history(env,req,planid,curpage):
    testmanagersystem = TestManagerSystem(env)
    tc_statuses = testmanagersystem.get_tc_statuses_by_name()

    tc_id = curpage.rpartition('_TC')[2]
    
    tcip = TestCaseInPlan(env, tc_id, planid)
    
    text = '<form id="testCaseHistory"><fieldset id="testCaseHistoryFields" class="collapsed"><legend class="foldable" style="cursor: pointer;"><a href="#no3"  onclick="expandCollapseSection(\'testCaseHistoryFields\')">'+_("Status change history")+'</a></legend>'
    
    text += '<table class="listing"><thead>'
    text += '<tr><th>'+_("Timestamp")+'</th><th>'+_("Author")+'</th><th>'+_("Status")+'</th></tr>'
    text += '</thead><tbody>'

    for ts, author, status in tcip.list_history():
        text += '<tr>'
        text += '<td>'+format_datetime(from_any_timestamp(ts))+'</td>'
        text += '<td>'+author+'</td>'
        text += '<td>'+tc_statuses[status][1]+'</td>'
        text += '</tr>'
        
    text += '</tbody></table>'
    text += '</fieldset></form>'

    return text
    
def _get_custom_fields_columns(obj, fields):
    result = ''
    
    for f in fields:
        if f['type'] == 'text':
            result += '<td>'
            if obj[f['name']] is not None:
                result += obj[f['name']]
            result += '</td>'

        # TODO Support other field types

    return result
