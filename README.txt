Test Manager plugin for Trac

  Copyright 2010 Roberto Longobardi

  Project web page on TracHacks: http://trac-hacks.org/wiki/TestManagerForTracPlugin
  
  Project web page on SourceForge.net: http://sourceforge.net/projects/testman4trac/
  
  Project web page on Pypi: http://pypi.python.org/pypi/TestManager


A Trac plugin to create Test Cases, organize them in catalogs, generate test plans and track their execution status and outcome.

Refer to BUILD.txt for details about how to build.

Refer to INSTALL.txt for installation details.

=================================================================================================  
Change History:

(Refer to the tickets on trac-hacks or SourceForge for complete descriptions.)

Release 1.4.4 (2011-02-11):
  o Fixed Ticket #8567 (Track-Hacks): Javascript error when deleting test plans
  o Enhancement #8596 (Track-Hacks): Remove hard dependency on XML RPC plugin for Trac 0.11

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
  o Enhanced feature 3076739 (SourceForge): Full Test Plan display / print

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
  
