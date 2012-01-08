Test Manager plugin for Trac

  Copyright 2010-2011 Roberto Bordolanghi
  
  The Test Manager plugin for Trac is free software: you can 
  redistribute it and/or modify it under the terms of the GNU General 
  Public License as published by the Free Software Foundation, either 
  version 3 of the License, or (at your option) any later version.
  
  The Test Manager plugin for Trac is distributed in the hope that it 
  will be useful, but WITHOUT ANY WARRANTY; without even the implied 
  warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
  See the GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License
  along with he Test Manager plugin for Trac. See LICENSE.txt.
  If not, see <http://www.gnu.org/licenses/>.


  Project web page on TracHacks: http://trac-hacks.org/wiki/TestManagerForTracPlugin
  
  Project web page on SourceForge.net: http://sourceforge.net/projects/testman4trac/
  
  Project web page on Pypi: http://pypi.python.org/pypi/TestManager


Refer to BUILD.txt for details about how to build.

Refer to INSTALL.txt for installation details.


A Trac plugin to create Test Cases, organize them in catalogs, generate test plans 
and track their execution status and outcome.

The same code works well with Python 2.5, 2.6 and 2.7 and on Trac 0.11 and 0.12.
The same egg file runs on both Trac 0.11 and 0.12.
All database backends are supported.

The Test Manager functionality is split up into three plugins:


    TracGenericClass:
    
        This module provides a framework to help creating classes on Trac that:
         * Are persisted on the DB
         * Support change history
         * Support extensibility through custom properties that the User can specify declaratively in the trac.ini file
         * Support custom operations to be performed before and after the standard object lifecycle events.
         * Listener interface for Components willing to be notified on any object lifecycle event (i.e. creation, modification, deletion).

        Database tables are also automatically created by the framework as declaratively stated by the client Components.
         
        Also provides an intermediate class to build objects that wrap Wiki pages and have additional properties.


        More details:

        A generic object framework supporting programmatic and declarative definition of its standard fields, declarative definition of custom fields (in trac.ini) and keeping track of change history has been created, by generalizing the base Ticket code.

        The specific object "type" is specified during construction as the "realm" parameter.
        This name must also correspond to the database table storing the corresponding objects, and is used as the base name for the custom fields table and the change tracking table (see below).

        Features:
            * Support for custom fields, specified in the trac.ini file
              with the same syntax as for custom Ticket fields. Custom
              fields are kept in a "<schema>_custom" table
            * Keeping track of all changes to any field, into a separate
              "<schema>_change" table
            * A set of callbacks to allow for subclasses to control and 
              perform actions pre and post any operation pertaining the 
              object's lifecycle
            * Registering listeners, via the ITestObjectChangeListener
              interface, for object creation, modification and deletion.
            * Searching objects by similarity, i.e. matching any set of 
              valorized fields (even non-key fields), applying the 
              "dynamic record" pattern.
              See the method list_matching_objects.
            * Integration with the Trac Search page.
            * Integration with the Trac Resource API.
            * Support for declarative specification of the database 
              backing a particular class. The tables are created 
              automatically.
            * Fine-grained security access control to any operation on 
              any resource type or instance.


    TracGenericWorkflow:
    
        Provides a framework to help creating workflows around any Trac Resource.

        Features:
            * Declarative definition of the workflow, specified in trac.ini.
            * Same syntax as the basic Ticket workflow (I may have derived
              some line of code from Trac itself... ;-))
            * Easy GUI integration support. You can expose the workflow 
              operation widgets anywhere in your application pages.
            * Fine-grained authorization control. You can specify which role
              is required to perform each state transition, and to execute
              each corresponding action.
            * Custom actions. An open API allows you to program your own 
              custom actions to be executed at any workflow state transition.
            * Out-of-the-box built-in actions are provided.
            * XML-RPC remote API.


    TestManager:
        
        Provides the test management-related funcitonality.
        
        Features:
            * Define test cases and organize in test catalogs (test suites).
            * Define a hierarchy of catalogs and sub-catalogs, whatever deep.
            * Test case and catalogs versioning and history of changes.
            * Test cases and catalogs support Wiki formatting and attachments.
            * Copy/move individual or a set of test cases among catalogs.
            * Define one or more test plans (test rounds) based on all or a portion 
              of the test cases in a (sub-)catalog. Specify whether the test 
              case version should be freezed in the test plan, or always link 
              to the latest version. 
            * One-click change status of a test case.
            * Ticket integration: open tickets directly from a (failed) test case,
              keep track of the relationship. Navigate froma a test case to its
              related tickets and vice-versa.
            * Test cases, catalogs and plans can have their own custom properties,
              defined in trac.ini like tickets.
            * Definition of custom test outcomes (statuses), in addition to the 
              built-in "Untested", "Success", "Failed".
            * Test execution statistical charts. Export to CSV.
            * Statistical charts about tickets related to test plans. Export to CSV.
            * Tree and tabular view of the test catalogs or test plans, and the 
              contained test cases.
            * Type-ahead searching and filtering from the tree and tabular view.
            * Breadcrumbs to easily navigate through test catalogs and plans.
            * Integration with Trac search engine.
            * Fina-grained security with six new Trac permissions.
            * Create templates for test cases and test catalogs. Specify which default
              template should be used for test cases in any particular catalog.
            * Import/export test cases from/to Excel in CSV format.
            * National Language Support (NLS) and currently translated in Italian, 
              French, German and Spanish.
            * Remote APIs: XML-RPC, RESTful.
            * Python API.
              
        
An additional plugin is only useful for debugging and should not be installed 
in a production environment.

    SQLExecutor:
    
        Allows for running arbitrary SQL statements on the internal Trac database
        from a simple web page, and see the results.


=================================================================================================  
Change History:

(Refer to the tickets on trac-hacks or SourceForge for complete descriptions.)

Release 1.4.9 (2012-01-04):

  o Enhancement #8958 (Track-Hacks): An ability to export test data to CSV format needed.
                                     You can now export to CSV a test catalog or a test plan.
                                     In the test catalog and test plan pages you will find an "Export ..." button.
                                     The export format is designed to eventually import the stuff back into another 
                                     Test Manager plugin evironment, as soon as a compatible import feature will be 
                                     implemented :D (the current import feature is simpler than that.)

  o Enhancement #9287 (Track-Hacks): New browser tab for existing testcases. Now you have an option in trac.ini to choose what
                                     to do when clicking on a test case in the catalog/plan. 
                                     The default is to NOT open it in a new window, but you can change that from the admin panel,
                                     under Testmanage->Settings, or directly in the trac.ini file like this:
                                     
                                        [testmanager]
                                        testcase.open_new_window = True

  o Fixed Ticket #9297 (Track-Hacks): Can't print testplan table overview. There was a problem with the default print css from Trac.

  o Fixed Ticket #9510 (Track-Hacks): TestStats for single Testplans at 1.4.8 not working - patched. 
                                      Thanks so much Andreas for finding it and for patching it!!!

  o Fixed Ticket #9530 (Track-Hacks): Expand all / Collapse all is not running

  o Fixed Ticket #9654 (Track-Hacks): Error when creating test plans

Release 1.4.8 (2011-10-23):
  o Strongly enhanced the upgrade mechanism. Now it's more robust, should work with all the databases and between arbitrary Test Manager versions.

    The only drawback is that upgrade is only supported from 1.4.7, not from previous versions.

  o Enhancement #9077 (Track-Hacks): Ability to separate and report on test plans by product

  o Enhancement #9208 (Track-Hacks): Test plan with only selected test cases from the catalog, take snapshot version of test cases.
                                     This is an important one. Many users were asking for a way of including only selected test cases into
                                     a Test Plan, for different reasons. Now you have it :D

  o Added French language catalog! Thanks to someone who doesn't want to be cited :D

  o Fixed Ticket #9141 (Track-Hacks): Update installation 1.4.6 -> 1.4.7 not possible
  o Fixed Ticket #9167 (Track-Hacks): installation of 1.4.7 with postgres database not possible
  o Fixed Ticket #9187 (Track-Hacks): Current test status report should consider only last result of a testcase in the plan. 
                                      Thanks to Andreas for his contribution to fixing this one!

Release 1.4.7 (2011-08-28):
  o Enhancement #8907 (Track-Hacks): Add template for "New TestCase" - Thanks a lot to Christian for the hard work on this enhancement!!!
                                     Now you can define templates for your new test catalogs and new test cases, and assign default templates based
                                     on each test catalog!
  o Enhancement #8908 (Track-Hacks): Possiblity to change test case status from the tree view.
                                     No more need to open each test case in a plan to set its result, you can now do this directly from the tree view!
  o Fixed Ticket #8869 (Track-Hacks): Loading of Test Manager takes too long and sometimes time out
  o Added Spanish and German catalogs! Thanks a lot to Christopher and Andreas for the translations!!! Italian was already part of the plugin.

Release 1.4.6 (2011-06-19):
  o Fixed Ticket #8871 (Track-Hacks): No # allowed at custom fields
  o Fixed Ticket #8873 (Track-Hacks): css styles ar not compatible with the agilo plugin
  o Fixed Ticket #8876 (Track-Hacks): Can't create Catalogs/Test cases when trac runs from site root
  o Fixed Ticket #8878 (Track-Hacks): TestManagerForTracPlugin does not play well with MenusPlugin
  o Fixed Ticket #8898 (Track-Hacks): yui_base_url not honored in templates ?
  o Enhancement #8875 (Track-Hacks): More visibility for Tickets related to test suites
  Added more statistical charts, including Current test status pie chart and Tickets related to test cases trend chart
  Simplified setting the outcome of a test case

Release 1.4.5 (2011-05-21):
  o Enhancement #8825 (Track-Hacks): Ability to import test cases from Excel (CSV) file

Release 1.4.4 (2011-03-11):
  o Fixed Ticket #8567 (Track-Hacks): Javascript error when deleting test plans
  o Enhancement #8596 (Track-Hacks): Remove hard dependency on XML RPC plugin for Trac 0.11
  o Enhancement #8761 (Track-Hacks): Copy multiple test cases into another catalog
  Added wiki documentation for copying multiple test cases into another catalog.

Release 1.4.3 (2011-01-20):
  o Enhancement #8427 (Track-Hacks): Add XML-RPC complete interface for remote management of test objects

Release 1.4.2 (2011-01-09):
  o Fixed Ticket #8378 (Track-Hacks): Set date and time format correctly in Test Stats page
  Also added support for custom test case outcomes in the Test Stats page

Release 1.4.1 (2010-12-27):
  o Enhancement #7846 (Track-Hacks): Customizable test case outcomes (aka verdicts)
  o Enhancement #7570 (Track-Hacks): Add a relationship table between tickets and test cases in plan, and corresponding API

Release 1.3.12 (2010-12-19):
  o Enhancement #8321 (Track-Hacks): Add standard internationalization support (i18n)
  o Enhancement #8322 (Track-Hacks): Show timestamps according to User's locale
  o Fixed Ticket #8323 (Track-Hacks): Unable to expand Available plans and Test case status change history collapsable sections

Release 1.3.11 (2010-12-02):
  o Added out of the box operation to workflow engine: set_owner and set_owner_to_self
  o Enhancement #8259 (Track-Hacks): Add navigation from a test case to its related tickets

Release 1.3.10 (2010-11-28):
  o Fixed Ticket #8154 (Track-Hacks): LookupError: unknown encoding: cp0

Release 1.3.9 (2010-11-23):
  o Fixed Ticket #8144 (Track-Hacks): Test statistical charts don't show successful and failed figures.

Release 1.3.8 (2010-11-22):
  o Fixed Ticket #8121 (Track-Hacks): Catalog Wiki Page not added
  o Fixed Ticket #8123 (Track-Hacks): Can't move testcase more than one time into different catalog
  o Fixed Ticket #8124 (Track-Hacks): AttributeError: 'NoneType' object has no attribute 'splitlines'
  o Fixed Ticket #8125 (Track-Hacks): "duplicate test case" does not work for previously moved test case

Release 1.3.7 (2010-11-20):
  o Enhancement #7704 (Track-Hacks): Add ability to delete a Test Plan
  o Fixet Ticket #8084 (Track-Hacks): Ordering issue

Release 1.3.6 (2010-11-09):
  o Fixed Ticket #8004 (Track-Hacks): Cannot search if an admin

Release 1.3.5 (2010-10-17):
  o Restored compatibility with Trac 0.11. Now again both 0.11 and 0.12 are supported.

Release 1.3.4 (2010-10-15):
  o Added tabular view to catalogs and plans. Search now works with custom properties in tabular views.

Release 1.3.3 (2010-10-05):
  o Enhancement feature 3076739 (SourceForge): Full Test Plan display / print

Release 1.3.2 (2010-10-03):
  o Added feature 3076739 (SourceForge): Full Test Plan display / print

Release 1.3.1 (2010-10-02):
  o Fixed a base-code bug that prevented test catalog modification with a PostgreSQL binding. (Thanks Rodel for reporting it).

Release 1.3.0 (2010-10-01):
  o The base Test Manager plugin has been separated and other plugins have been created to embed the functionalities of generic class framework and the workflow engine.
    Now we have four plugins:
      * Trac Generic Class plugin, providing the persistent class framework
      * Trac Generic Workflow plugin, providing the generic workflow engine applicable 
        to any Trac Resource. This plugin requires the Trac Generic Class plugin.
      * SQL Executor plugin, as a debugging tool when dealing with persistent data. Not to be enabled in a production environment.

    Moreover, the generic class framework has been added a set of new functionalities. 
    Refer to the README file in its package for more details.
      
Release 1.2.0 (2010-09-20):
  o The data model has been completely rewritten, now using python classes for all the test objects.
    A generic object supporting programmatic definition of its standard fields, declarative 
    definition of custom fields (in trac.ini) and keeping track of change history has been created, 
    by generalizing the base Ticket code.
    
    The specific object "type" is specified during construction
    as the "realm" parameter.
    This name must also correspond to the database table storing the
    corresponding objects, and is used as the base name for the 
    custom fields table and the change tracking table (see below).
    
    Features:
        * Support for custom fields, specified in the trac.ini file
          with the same syntax as for custom Ticket fields. Custom
          fields are kept in a "<schema>_custom" table
        * Keeping track of all changes to any field, into a separate
          "<schema>_change" table
        * A set of callbacks to allow for subclasses to control and 
          perform actions pre and post any operation pertaining the 
          object's lifecycle
        * Registering listeners, via the ITestObjectChangeListener
          interface, for object creation, modification and deletion.
        * Searching objects matching any set of valorized fields,
          (even non-key fields), applying the "dynamic record" pattern. 
          See the method list_matching_objects.
    
  o Enhancement #7704 (Track-Hacks): Add workflow capabilities, with custom states, transitions and operations, and state transition listeners support
      A generic Trac Resource workflow system has been implemented, allowing to add workflow capabilities 
      to any Trac resource.
      Test objects have been implemented as Trac resources as well, so they benefit of workflow capabilities.

      Available objects 'realms' to associate workflows to are: testcatalog, testcase, testcaseinplan, testplan.
      
      Note that the object with realm 'resourceworkflowstate', which manages the state of any resource in a
      workflow, also supports custom properties (see below), so plugins can augment a resource workflow state
      with additional context information and use it inside listener callbacks, for example.

      For example, add the following to your trac.ini file to associate a workflow with all Test Case objects.
      The sample_operation is currently provided by the Test Manager system itself, as an example.
      It just logs a debug message with the text input by the User in a text field.
      
        [testcase-resource_workflow]
        leave = * -> *
        leave.operations = sample_operation
        leave.default = 1

        accept = new -> accepted
        accept.permissions = TEST_MODIFY
        accept.operations = sample_operation

        resolve = accepted -> closed
        resolve.permissions = TEST_MODIFY
        resolve.operations = sample_operation

  o Enhancement #7705 (Track-Hacks): Add support for custom properties and change history to all of the test management objects
      A generic object supporting programmatic definition of its standard fields, declarative definition 
      of custom fields (in trac.ini) and keeping track of change history has been created, by generalizing 
      the base Ticket code.
      
      Only text type of properties are currently supported.

      For example, add the following to your trac.ini file to add custom properties to all of the four
      test objects.
      Note that the available realms to augment are, as above, testcatalog, testcase, testcaseinplan and testplan, 
      with the addition of resourceworkflowstate.

        [testcatalog-tm_custom]
        prop1 = text
        prop1.value = Default value

        [testcaseinplan-tm_custom]
        prop_strange = text
        prop_strange.value = windows

        [testcase-tm_custom]
        nice_prop = text
        nice_prop.value = My friend

        [testplan-tm_custom]
        good_prop = text
        good_prop.value = linux

  o Enhancement #7569 (Track-Hacks): Add listener interface to let other components react to test case status change
      Added listener interface for all of the test objects lifecycle:
       * Object created
       * Object modified (including custom properties)
       * Object deleted
      This applies to test catalogs, test cases, test plans and test cases in a plan (i.e. with a status).
  
Release 1.1.2 (2010-08-25):
  o Enhancement #7552 (Track-Hacks): Export test statistics in CSV and bookmark this chart features in the test stats chart
  o Fixed Ticket #7551 (Track-Hacks): Test statistics don't work on Trac 0.11

Release 1.1.1 (2010-08-20):
  o Enhancement #7526 (Track-Hacks): Add ability to duplicate a test case
  o Enhancement #7536 (Track-Hacks): Add test management statistics
  o Added "autosave=true" parameter to the RESTful API to create test catalogs 
    and test cases programmatically without need to later submit the wiki editing form.

Release 1.1.0 (2010-08-18):
  o Enhancement #7487 (Track-Hacks): Add multiple test plans capability
  o Enhancement #7507 (Track-Hacks): Implement security permissions
  o Enhancement #7484 (Track-Hacks): Reverse the order of changes in the test case status change history

Release 1.0.2 (2010-08-17):
  o Fixed Ticket #7485 (Track-Hacks): "Open ticket on this test case" should work without a patched TracTicketTemplatePlugin

Release 1.0.1 (2010-08-12):
  o First attempt at externalizing strings

Release 1.0 (2010-08-10):
  o First release publicly available
  
