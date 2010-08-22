# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi
#
# The structure of this plugin is stolen from the Tracticketstats plugin, 
# by Prentice Wongvibulisn

import re

from genshi.builder import tag

from trac.core import *
from trac.config import Option, IntOption
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.perm import IPermissionRequestor

from datetime import date, datetime, time, timedelta
from time import strptime
from trac.util.datefmt import to_utimestamp, utc, to_timestamp

from testmanager.api import TestManagerSystem


# ************************
DEFAULT_DAYS_BACK = 30*6 
DEFAULT_INTERVAL = 30
# ************************

class TestStatsPlugin(Component):
    implements(INavigationContributor, IRequestHandler, ITemplateProvider, IPermissionRequestor)

    yui_base_url = Option('teststats', 'yui_base_url',
            default='http://yui.yahooapis.com/2.5.2',
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
            path_filter = "TC_%"
        else:
            path_filter = catpath + "_%" 

        dates_condition = ''
        
        if from_date:
            dates_condition += " AND time > %s" % to_utimestamp(from_date)

        if at_date:
            dates_condition += " AND time <= %s" % to_utimestamp(at_date)

        db = self.env.get_db_cnx()
        cursor = db.cursor()
        
        # TODO: Fix this query because it also counts test catalogs
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

        cursor.execute("SELECT COUNT(*) from testcasehistory WHERE status = '%s' AND time > %s AND time <= %s %s" % (status, to_timestamp(from_date), to_timestamp(at_date), testplan_filter))

        row = cursor.fetchone()
        
        count = row[0]

        #print("dates: "+str(to_timestamp(from_date))+"-"+str(to_timestamp(at_date)))
        #cursor = db.cursor()
        #cursor.execute("SELECT time from testcasehistory WHERE status = '%s' AND time > %s AND time <= %s" % (status, to_timestamp(from_date), to_timestamp(at_date)))
        #for row in cursor:
        #    print (row[0])

        return count


    # ==[ IRequestHandle methods ]==

    def match_request(self, req):
        return re.match(r'/teststats(?:_trac)?(?:/.*)?$', req.path_info)

    def process_request(self, req):
        test_manager_system = TestManagerSystem(self.env)
        #test_manager_system.report_testcase_status()
        
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

            # TODO: I'm letting the exception raised by 
            #  strptime() appear as the Trac error.
            #  Maybe a wrapper should be written.

            at_date = datetime(*strptime(grab_at_date, "%m/%d/%Y")[0:6])
            at_date = datetime.combine(at_date, time(11,59,59,0,utc)) # Add tzinfo

            from_date = datetime(*strptime(grab_from_date, "%m/%d/%Y")[0:6])
            from_date = datetime.combine(from_date, time(0,0,0,0,utc)) # Add tzinfo

            graph_res = int(grab_resolution)

        else:
            # default data
            todays_date = date.today()
            at_date = datetime.combine(todays_date,time(11,59,59,0,utc))
            from_date = at_date - timedelta(self.default_days_back)
            graph_res = self.default_interval
    
            at_date_str = at_date.strftime("%m/%d/%Y")
            from_date_str=  from_date.strftime("%m/%d/%Y")

            # 2.5 only: at_date = datetime.strptime(at_date_str, "%m/%d/%Y")
            at_date = datetime(*strptime(at_date_str, "%m/%d/%Y")[0:6])
            at_date = datetime.combine(at_date, time(11,59,59,0,utc)) # Add tzinfo
            
            # 2.5 only: from_date = datetime.strptime(from_date_str, "%m/%d/%Y")
            from_date = datetime(*strptime(from_date_str, "%m/%d/%Y")[0:6])
            from_date = datetime.combine(from_date, time(0,0,0,0,utc)) # Add tzinfo
            
        count = []

        # Calculate 0th point 
        last_date = from_date - timedelta(graph_res)

        # Calculate remaining points
        for cur_date in daterange(from_date, at_date, graph_res):
            
            print cur_date
            
            num_new = self._get_num_testcases(last_date, cur_date, catpath, testplan, req)
            num_successful = self._get_num_tcs_by_status(last_date, cur_date, 'SUCCESSFUL', testplan, req)
            num_failed = self._get_num_tcs_by_status(last_date, cur_date, 'FAILED', testplan, req)
            
            num_all = self._get_num_testcases(None, cur_date, catpath, testplan, req)
            num_all_successful = self._get_num_tcs_by_status(from_date, cur_date, 'SUCCESSFUL', testplan, req)
            num_all_failed = self._get_num_tcs_by_status(from_date, cur_date, 'FAILED', testplan, req)

            num_all_untested = num_all - num_all_successful - num_all_failed

            datestr = cur_date.strftime("%m/%d/%Y") 
            if graph_res != 1:
                datestr = "%s thru %s" % (last_date.strftime("%m/%d/%Y"), datestr) 
            count.append( {'date'  : datestr,
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
            req.send_header("Content-Length", len(jsdstr))
            req.write(jsdstr)
            return 
        else:
            db = self.env.get_db_cnx()
            showall = req.args.get('show') == 'all'

            testplan_list = []
            for planid, catid, catpath, name, author, ts_str in test_manager_system.list_all_testplans():
                testplan_list.append({'planid': planid, 'catpath': catpath, 'name': name})

            data = {}
            data['testcase_data'] = count
            data['start_date'] = from_date.strftime("%m/%d/%Y")
            data['end_date'] = at_date.strftime("%m/%d/%Y")
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
     end    -- a date (or datetime) object; the end of the range.
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




