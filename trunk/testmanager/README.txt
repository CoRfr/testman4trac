Test Manager plugin for Trac

  Copyright 2010 Roberto Longobardi, Marco Cipriani

  Project web page on TracHacks: http://trac-hacks.org/wiki/TestManagerForTracPlugin
  
  Project web page on SourceForge.net: http://sourceforge.net/projects/testman4trac/
  
  Project web page on Pypi: http://pypi.python.org/pypi/TestManager

  
A Trac plugin to create Test Cases, organize them in catalogs, generate test plans and track their execution status and outcome.

=================================================================================================  
Change History:

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
    
  o Enhancement #7704 Add workflow capabilities, with custom states, transitions and operations, and state transition listeners support
      A generic Trac Resource workflow system has been implemented, allowing to add workflow capabilities 
      to any Trac resource.
      Test objects have been implemented as Trac resources as well, so they benefit of workflow capabilities.

  o Enhancement #7705 Add support for custom properties and change history to all of the test management objects
      A generic object supporting programmatic definition of its standard fields, declarative definition 
      of custom fields (in trac.ini) and keeping track of change history has been created, by generalizing 
      the base Ticket code.

  o Enhancement #7569 Add listener interface to let other components react to test case status change
      Added listener interface for all of the test objects lifecycle:
       * Object created
       * Object modified (including custom properties)
       * Object deleted
      This applies to test catalogs, test cases, test plans and test cases in a plan (i.e. with a status).
  
Release 1.1.2 (2010-08-25):
  o Enhancement #7552 Export test statistics in CSV and bookmark this chart features in the test stats chart
  o Fixed Ticket #7551 Test statistics don't work on Trac 0.11

Release 1.1.1 (2010-08-20):
  o Enhancement #7526 Add ability to duplicate a test case
  o Enhancement #7536 Add test management statistics
  o Added "autosave=true" parameter to the RESTful API to create test catalogs 
    and test cases programmatically without need to later submit the wiki editing form.

Release 1.1.0 (2010-08-18):
  o Enhancement #7487 Add multiple test plans capability
  o Enhancement #7507 Implement security permissions
  o Enhancement #7484 Reverse the order of changes in the test case status change history

Release 1.0.2 (2010-08-17):
  o Fixed Ticket #7485 "Open ticket on this test case" should work without a patched TracTicketTemplatePlugin

Release 1.0.1 (2010-08-12):
  o First attempt at externalizing strings

Release 1.0 (2010-08-10):
  o First release publicly available
  
