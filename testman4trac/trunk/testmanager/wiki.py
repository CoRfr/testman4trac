# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi
#

from trac.core import *
from trac.mimeview.api import Context
from trac.resource import Resource
from trac.util import format_datetime, format_date
from trac.web.api import ITemplateStreamFilter
from trac.web.chrome import add_stylesheet, add_script, ITemplateProvider
from trac.wiki.api import WikiSystem, IWikiChangeListener
from trac.wiki.formatter import Formatter
from trac.wiki.model import WikiPage

from genshi import HTML
from genshi.builder import tag
from genshi.filters.transform import Transformer

from tracgenericclass.model import GenericClassModelProvider
from tracgenericclass.util import *

from testmanager.api import TestManagerSystem
from testmanager.macros import TestCaseBreadcrumbMacro, TestCaseTreeMacro, TestPlanTreeMacro, TestPlanListMacro, TestCaseStatusMacro, TestCaseChangeStatusMacro, TestCaseStatusHistoryMacro
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
    
    def __init__(self, *args, **kwargs):
        """
        Parses the configuration file for the section 'testmanager'.
        
        Available properties are:
        
          testplan.sortby = {modification_time|name}    (default is name)
        """
        
        Component.__init__(self, *args, **kwargs)

        for section in self.config.sections():
            if section == 'testmanager':
                self.log.debug("WikiTestManagerInterface - parsing config section %s" % section)
                options = list(self.config.options(section))
                
                self._parse_config_options(options)
                break

    
    def _parse_config_options(self, options):
        for option in options:
            name = option[0]
            value = option[1]
            self.env.log.debug("  %s = %s" % (name, value))
            
            self._config_properties[name] = value
    
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

        mode = req.args.get('mode', 'tree')
        fulldetails = req.args.get('fulldetails', 'False')
        
        tmmodelprovider = GenericClassModelProvider(self.env)
        test_catalog = TestCatalog(self.env, cat_id, page_name)
        
        tree_macro = TestCaseTreeMacro(self.env)

        if page_name == 'TC':
            # Root of all catalogs
            insert1 = tag.div()(
                        tag.div(id='pasteMultipleTCsHereMessage', class_='messageBox', style='display: none;')(_("Select the catalog into which to paste the Test Cases and click on 'Paste the copied Test Cases here'. "),
                            tag.a(href='javascript:void(0);', onclick='cancelTCsCopy()')(_("Cancel"))
                            ),
                        tag.br(), 
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
                            tag.span()(
                                tag.a(href=req.href.wiki(page_name, mode='tree'))(
                                    tag.img(src='../chrome/testmanager/images/tree.png', title="Tree View"))
                                ),
                            tag.span()(
                                tag.a(href=req.href.wiki(page_name, mode='tree_table', fulldetails='True'))(
                                    tag.img(src='../chrome/testmanager/images/tree_table.png', title="Table View"))
                                )),
                        tag.br(), 
                        tag.div(id='pasteMultipleTCsHereMessage', class_='messageBox', style='display: none;')(
                            _("Select the catalog (even this one) into which to paste the Test Cases and click on 'Paste the copied Test Cases here'. "),
                            tag.a(href='javascript:void(0);', onclick='cancelTCsCopy()')(_("Cancel"))
                            ),
                        tag.br(),
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
                    HTML(tree_macro.expand_macro(formatter, None, 'mode='+mode+',fulldetails='+fulldetails+',catalog_path='+page_name)),
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

            insert2.append(tag.div(class_='field')(
                self._get_testplan_list_markup(formatter, cat_name, mode, fulldetails)
                ))

            insert2.append(tag.div(class_='field')(
                self._get_object_change_history_markup(test_catalog)
                ))

        insert2.append(tag.div()(tag.br(), tag.br(), tag.br(), tag.br()))
        
        common_code = self._write_common_code(req)
        
        return stream | Transformer('//body').append(common_code) | Transformer('//div[contains(@class,"wikipage")]').after(insert2) | Transformer('//div[contains(@class,"wikipage")]').before(insert1)

        
    def _testplan_wiki_view(self, req, formatter, page_name, planid, stream):
        path_name = req.path_info
        cat_name = path_name.rpartition('/')[2]
        cat_id = cat_name.rpartition('TT')[2]
        
        mode = req.args.get('mode', 'tree')
        fulldetails = req.args.get('fulldetails', 'False')

        if 'testplan.sortby' in self._config_properties:
            sortby = self._config_properties['testplan.sortby']
        else:
            sortby = 'name'

        tmmodelprovider = GenericClassModelProvider(self.env)
        test_plan = TestPlan(self.env, planid, cat_id, page_name)
        
        tree_macro = TestPlanTreeMacro(self.env)
            
        tp = TestPlan(self.env, planid)
        
        insert1 = tag.div()(
                    tag.a(href=req.href.wiki(page_name))(_("Back to the Catalog")),
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
                    tag.h1(_("Test Plan: ")+tp['name'])
                    )

        insert2 = tag.div()(
                    HTML(tree_macro.expand_macro(formatter, None, 'planid='+str(planid)+',catalog_path='+page_name+',mode='+mode+',fulldetails='+fulldetails+',sortby='+sortby)),
                    tag.div(class_='testCaseList')(
                    tag.br(), tag.br(),
                    self._get_custom_fields_markup(test_plan, tmmodelprovider.get_custom_fields_for_realm('testplan')),
                    tag.br(),
                    ),
                    tag.div(class_='field')(
                        self._get_object_change_history_markup(test_plan)
                        ),
                    tag.br(), tag.br(), tag.br(), tag.br()
                    )
                            
        common_code = self._write_common_code(req, True)
        
        return stream | Transformer('//body').append(common_code) | Transformer('//div[contains(@class,"wikipage")]').after(insert2) | Transformer('//div[contains(@class,"wikipage")]').before(insert1)
        

    def _testcase_wiki_view(self, req, formatter, planid, page_name, stream):
        tc_name = page_name
        cat_name = page_name.partition('_TC')[0]
        
        mode = req.args.get('mode', 'tree')
        fulldetails = req.args.get('fulldetails', 'False')
        is_edit = req.args.get('edit_custom', 'false')
        
        has_status = False
        plan_name = ''
    
        tc_id = tc_name.partition('_TC')[2]
        test_case = TestCase(self.env, tc_id, tc_name)
        summary = test_case.title
        
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
                    tag.div(class_='field')(
                        self._get_object_change_history_markup(test_case)
                        ),
                    tag.br(), tag.br(), tag.br(), tag.br()
                    )

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
                    tag.input(type='button', value=_("Open a Ticket on this Test Case"), onclick='creaTicket("'+tc_name+'", "'+planid+'", "'+plan_name+'", "'+summary+'")'),
                    HTML('&nbsp;&nbsp;'), 
                    tag.input(type='button', value=_("Show Related Tickets"), onclick='showTickets("'+tc_name+'", "'+planid+'", "'+plan_name+'")'),
                    HTML('&nbsp;&nbsp;'), 
                    tag.br(), tag.br(), 
                    self._get_testcase_status_history_markup(formatter, has_status, page_name, planid),
                    self._get_object_change_history_markup(tcip, ['status']),
                    tag.br(), tag.br(), tag.br(), tag.br()
                    )
                    
        common_code = self._write_common_code(req, False, need_menu)
        
        return stream | Transformer('//body').append(common_code) | Transformer('//div[contains(@class,"wikipage")]').after(insert2) | Transformer('//div[contains(@class,"wikipage")]').before(insert1)
    
    def _get_breadcrumb_markup(self, formatter, planid, page_name, mode='tree', fulldetails='False'):
        breadcrumb_macro = TestCaseBreadcrumbMacro(self.env)
        if planid and not planid == '-1':
            # We are in the context of a test plan
            if not page_name.rpartition('_TC')[2] == '':
                # It's a test case in plan
                tp = TestPlan(self.env, planid)
                catpath = tp['page_name']
                result = tag.span()(
                    tag.a(href=formatter.req.href.wiki(catpath, planid=planid, mode=mode, fulldetails=fulldetails))(_("Back to the Test Plan")),
                    HTML(breadcrumb_macro.expand_macro(formatter, None, 'page_name='+page_name+',mode='+mode+',planid='+planid+',fulldetails='+fulldetails))
                )
                
                return result
            else:
                # It's a test plan
                return tag.a(href=formatter.req.href.wiki(page_name))(_("Back to the Catalog"))
                
        else:
            # It's a test catalog or test case description
            return HTML(breadcrumb_macro.expand_macro(formatter, None, 'page_name='+page_name+',mode='+mode+',fulldetails='+fulldetails))

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

    def _get_testplan_list_markup(self, formatter, cat_name, mode, fulldetails):
        testplan_list_macro = TestPlanListMacro(self.env)
        return HTML(testplan_list_macro.expand_macro(formatter, None, 'catalog_path='+cat_name+',mode='+mode+',fulldetails='+str(fulldetails)))

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
        result = """
            <div id="dialog_testplan" style="padding:20px; display:none;" title="New Test Plan">
                <form id="new_testplan_form" class="addnew">
                    Specify the new Test Plan properties.
                <br />
                <fieldset>
                    <legend>Test Plan properties</legend>
                    <table><tbody>
                        <tr>
                            <td>
                                <div class="field">
                                  <label>
                                    The new Test Plan will contain:
                                  </label>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <input type="radio" name="testplan_contains_all" value="true" checked="checked" /> All the Test Cases in the Catalog<br />
                                <input type="radio" name="testplan_contains_all" value="false" /> Only the Test Cases selected before
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
                                    The new Test Plan will:
                                  </label>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <input type="radio" name="testplan_snapshot" value="true" /> Refer to a current snapshot of the versions of the test cases<br />
                                <input type="radio" name="testplan_snapshot" value="false" checked="checked" /> Always point to the latest version of the Test Cases
                            </td>
                        </tr>
                    </tbody></table>
                </fieldset>
                <fieldset>
                    <div class="buttons">
                        <input type="hidden" name="cat_name" value="%s" />
                        <input type="button" value="Create Test Plan" onclick="createTestPlanConfirm('%s')" style="text-align: right;"></input>
                        <input type="button" value="Cancel" onclick="createTestPlanCancel()" style="text-align: right;"></input>
                    </div>
                </fieldset>
                </form>
            </div>
        """ % (cat_name, cat_name)
        
        return result
    
    def _get_object_change_history_markup(self, obj, exclude_fields=None):
        text = '<form id="objectChangeHistory"><fieldset id="objectChangeHistoryFields" class="collapsed"><legend class="foldable" style="cursor: pointer;"><a href="#no6"  onclick="expandCollapseSection(\'objectChangeHistoryFields\')">'+_("Object change history")+'</a></legend>'
        
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
            text += '<td>'+author+'</td>'
            text += '<td>'+fname+'</td>'
            text += '<td>'+oldvalue+'</td>'
            text += '<td>'+newvalue+'</td>'
            text += '</tr>'
            
        text += '</tbody></table>'
        text += '</fieldset></form>'

        return HTML(text)
    
    def _get_import_dialog_markup(self, req, cat_name):
        result = """
            <div id="dialog_import" style="padding:20px; display:none;" title="Import test cases">
                <form id="import_file" class="addnew" method="post" enctype="multipart/form-data" action="%s/testimport">
                Select a file in CSV format to import the test cases from.
                <br />
                The first row will have column names. The data must start from the second row.
                The file should have the following required columns:
                <ul>
                    <li>title</li>
                    <li>description</li>
                </ul>
                Any subsequent columns are optional, and will generate <a href="http://trac-hacks.org/wiki/TestManagerForTracPlugin#Customfields" target="_blank">custom test case fields</a>.
                Use lowercase identifiers, with no blanks, for the column names.
                <br />
                <fieldset>
                    <legend>Upload file</legend>
                    <table><tbody>
                        <tr>
                            <td>
                                <div class="field">
                                  <label>
                                    File name:
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
                                    Column separator:
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
                        <input type="submit" name="import_file" value="Import" style="text-align: right;"></input>
                        <input type="button" value="Cancel" onclick="importTestCasesCancel()" style="text-align: right;"></input>
                    </div>
                </fieldset>
                </form>
            </div>
        """ % (fix_base_location(req), cat_name)
        
        return result
    
    def _write_common_code(self, req, add_statuses_and_colors=False, add_menu=False):
        add_stylesheet(req, 'common/css/report.css')
        add_stylesheet(req, 'testmanager/css/blitzer/jquery-ui-1.8.13.custom.css')
        add_stylesheet(req, 'testmanager/css/testmanager.css')

        before_jquery = 'var baseLocation="'+fix_base_location(req)+'";' + \
            'var jQuery_trac_old = $.noConflict(true);'
        after_jquery = 'var jQuery_testmanager = $.noConflict(true);$ = jQuery_trac_old;'

        if add_statuses_and_colors and 'TEST_EXECUTE' in req.perm:
            after_jquery += self._get_statuses_and_colors_javascript()
        else:
            after_jquery += "var statuses_by_color = null;"
        
        common_code = tag.div()(
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
        result = 'var statuses_by_color = {'

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
        
