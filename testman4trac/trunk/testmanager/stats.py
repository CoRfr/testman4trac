# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi
#
# The structure of this plugin is copied from the Tracticketstats plugin, 
# by Prentice Wongvibulisn
#

import re

from genshi.builder import tag

from trac.core import *
from trac.config import Option, IntOption
from trac.util import format_date, format_datetime
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.perm import IPermissionRequestor

from datetime import date, datetime, time, timedelta
from time import strptime
from trac.util.datefmt import utc, parse_date

from tracgenericclass.util import *

from testmanager.api import TestManagerSystem
from testmanager.util import *



# ************************
DEFAULT_DAYS_BACK = 30*3 
DEFAULT_INTERVAL = 7
# ************************

class TestStatsPlugin(Component):
    implements(INavigationContributor, IRequestHandler, ITemplateProvider, IPermissionRequestor)

    yui_base_url = Option('teststats', 'yui_base_url',
            default='http://yui.yahooapis.com/2.8.2r1',
            doc='Location of YUI API')

    default_days_back = IntOption('teststats', 'default_days_back',
            default=DEFAULT_DAYS_BACK,
            doc='Number of days to show by default')

    default_interval = IntOption('teststats', 'default_interval',
            default=DEFAULT_INTERVAL,
            doc='Number of days between each data point'\
                ' (resolution) by default')

    # ==[ INavigationContributor methods ]==

    def get_active_navigation_item(self, req):
        return 'teststats'

    def get_permission_actions(self):
        return ['TEST_STATS_VIEW']

    def get_navigation_items(self, req):
        if req.perm.has_permission('TEST_STATS_VIEW'):
            yield ('mainnav', 'teststats', 
                tag.a('Test Stats', href=req.href.teststats()))

    # ==[ Helper functions ]==
    def _get_num_testcases(self, from_date, at_date, catpath, testplan, req):
        '''
        Returns an integer of the number of test cases 
        counted between from_date and at_date.
        '''

        if catpath == None or catpath == '':
            path_filter = "TC_%_TC%"
        else:
            path_filter = catpath + "%_TC%" 

        dates_condition = ''

        if from_date:
            dates_condition += " AND time > %s" % to_any_timestamp(from_date)

        if at_date:
            dates_condition += " AND time <= %s" % to_any_timestamp(at_date)

        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM wiki WHERE name LIKE '%s' AND version = 1 %s" % (path_filter, dates_condition))

        row = cursor.fetchone()
        
        count = row[0]

        return count


    def _get_num_tcs_by_status(self, from_date, at_date, status, testplan, req):
        '''
        Returns an integer of the number of test cases that had the
        specified status between from_date to at_date.
        '''
        
        if testplan == None or testplan == '':
            testplan_filter = ''
        else:
            testplan_filter = " AND planid = '%s'" % (testplan) 
        
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        cursor.execute("SELECT COUNT(*) from testcasehistory WHERE status = '%s' AND time > %s AND time <= %s %s" % (status, to_any_timestamp(from_date), to_any_timestamp(at_date), testplan_filter))

        row = cursor.fetchone()
        
        count = row[0]

        return count


    # ==[ IRequestHandle methods ]==

    def match_request(self, req):
        return re.match(r'/teststats(?:_trac)?(?:/.*)?$', req.path_info)

    def process_request(self, req):
        testmanagersystem = TestManagerSystem(self.env)
        tc_statuses = testmanagersystem.get_tc_statuses_by_color()
        
        req_content = req.args.get('content')
        testplan = None
        catpath = None
        
        if not None in [req.args.get('end_date'), req.args.get('start_date'), req.args.get('resolution')]:
            # form submit
            grab_at_date = req.args.get('end_date')
            grab_from_date = req.args.get('start_date')
            grab_resolution = req.args.get('resolution')
            grab_testplan = req.args.get('testplan')
            if grab_testplan and not grab_testplan == "__all":
                testplan = grab_testplan.partition('|')[0]
                catpath = grab_testplan.partition('|')[2]

            # validate inputs
            if None in [grab_at_date, grab_from_date]:
                raise TracError('Please specify a valid range.')

            if None in [grab_resolution]:
                raise TracError('Please specify the graph interval.')
            
            if 0 in [len(grab_at_date), len(grab_from_date), len(grab_resolution)]:
                raise TracError('Please ensure that all fields have been filled in.')

            if not grab_resolution.isdigit():
                raise TracError('The graph interval field must be an integer, days.')

            at_date = parse_date(grab_at_date, req.tz)
            from_date = parse_date(grab_from_date, req.tz)

            graph_res = int(grab_resolution)

        else:
            # default data
            todays_date = datetime.today()
            at_date = todays_date #+ timedelta(1) # datetime.combine(todays_date,time(23,59,59,0,req.tz))
            at_date = at_date.replace(tzinfo = req.tz)
            from_date = at_date - timedelta(self.default_days_back)
            graph_res = self.default_interval
            
        count = []

        # Calculate 0th point 
        last_date = from_date - timedelta(graph_res)

        # Calculate remaining points
        for cur_date in daterange(from_date, at_date, graph_res):
            # Handling custom test case outcomes here
            num_new = self._get_num_testcases(last_date, cur_date, catpath, testplan, req)
            
            num_successful = 0
            for tc_outcome in tc_statuses['green']:
                num_successful += self._get_num_tcs_by_status(last_date, cur_date, tc_outcome, testplan, req)

            num_failed = 0
            for tc_outcome in tc_statuses['red']:
                num_failed += self._get_num_tcs_by_status(last_date, cur_date, tc_outcome, testplan, req)
            
            num_all = self._get_num_testcases(None, cur_date, catpath, testplan, req)

            num_all_successful = 0
            for tc_outcome in tc_statuses['green']:
                num_all_successful += self._get_num_tcs_by_status(from_date, cur_date, tc_outcome, testplan, req)

            num_all_failed = 0
            for tc_outcome in tc_statuses['red']:
                num_all_failed += self._get_num_tcs_by_status(from_date, cur_date, tc_outcome, testplan, req)

            num_all_untested = num_all - num_all_successful - num_all_failed

            datestr = format_date(cur_date) 
            if graph_res != 1:
                datestr = "%s thru %s" % (format_date(last_date), datestr) 
            count.append( {'from_date': format_date(last_date),
                         'to_date': datestr,
                         'date'  : datestr,
                         'new_tcs'    : num_new,
                         'successful': num_successful,
                         'failed': num_failed,
                         'all_tcs'    : num_all,
                         'all_successful': num_all_successful,
                         'all_untested': num_all_untested,
                         'all_failed': num_all_failed })
            last_date = cur_date

        # if chartdata is requested, raw text is returned rather than data object
        # for templating
        if (not req_content == None) and (req_content == "chartdata"):
            jsdstr = '{"chartdata": [\n'

            for x in count:
                jsdstr += '{"date": "%s",' % x['date']
                jsdstr += ' "new_tcs": %s,' % x['new_tcs']
                jsdstr += ' "successful": %s,' % x['successful']
                jsdstr += ' "failed": %s,' % x['failed']
                jsdstr += ' "all_tcs": %s,' % x['all_tcs']
                jsdstr += ' "all_successful": %s,' % x['all_successful']
                jsdstr += ' "all_untested": %s,' % x['all_untested']
                jsdstr += ' "all_failed": %s},\n' % x['all_failed']
            jsdstr = jsdstr[:-2] +'\n]}'

            if isinstance(jsdstr, unicode): 
                jsdstr = jsdstr.encode('utf-8') 

            req.send_header("Content-Length", len(jsdstr))
            req.write(jsdstr)
            return
        elif (not req_content == None) and (req_content == "downloadcsv"):
            csvstr = "Date from;Date to;New Test Cases;Successful;Failed;Total Test Cases;Total Successful;Total Untested;Total Failed\r\n"
            for x in count:
                csvstr += '%s;' % x['from_date']
                csvstr += '%s;' % x['to_date']
                csvstr += '%s;' % x['new_tcs']
                csvstr += '%s;' % x['successful']
                csvstr += '%s;' % x['failed']
                csvstr += '%s;' % x['all_tcs']
                csvstr += '%s;' % x['all_successful']
                csvstr += '%s;' % x['all_untested']
                csvstr += '%s\r\n' % x['all_failed']
                
            if isinstance(csvstr, unicode): 
                csvstr = csvstr.encode('utf-8') 

            req.send_header("Content-Length", len(csvstr))
            req.send_header("Content-Disposition", "attachment;filename=Test_stats.csv")
            req.write(csvstr)
            return
        else:
            db = self.env.get_db_cnx()
            showall = req.args.get('show') == 'all'

            testplan_list = []
            for planid, catid, catpath, name, author, ts_str in testmanagersystem.list_all_testplans():
                testplan_list.append({'planid': planid, 'catpath': catpath, 'name': name})

            data = {}
            data['testcase_data'] = count
            data['start_date'] = format_date(from_date)
            data['end_date'] = format_date(at_date)
            data['resolution'] = str(graph_res)
            data['baseurl'] = req.base_url
            data['testplans'] = testplan_list
            data['ctestplan'] = testplan
            return 'testmanagerstats.html', data, None
 
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
        #return [('testmanager', resource_filename(__name__, 'htdocs'))]
        return [('testmanager', resource_filename('testmanager', 'htdocs'))]

def daterange(begin, end, delta = timedelta(1)):
     """Stolen from: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/574441

     Form a range of dates and iterate over them.  

     Arguments:
     begin -- a date (or datetime) object; the beginning of the range.
     end   -- a date (or datetime) object; the end of the range.
     delta -- (optional) a timedelta object; how much to step each iteration.
                 Default step is 1 day.
                 
     Usage:

     """
     if not isinstance(delta, timedelta):
          delta = timedelta(delta)

     ZERO = timedelta(0)

     if begin < end:
          if delta <= ZERO:
                raise StopIteration
          test = end.__gt__
     else:
          if delta >= ZERO:
                raise StopIteration
          test = end.__lt__

     while test(begin):
          yield begin
          begin += delta




