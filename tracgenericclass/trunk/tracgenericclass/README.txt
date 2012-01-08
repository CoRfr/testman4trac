Trac Generic Class - Part of the Test Manager plugin for Trac

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

  
A Trac plugin to create Test Cases, organize them in catalogs, generate test plans and track their execution status and outcome.

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

=================================================================================================  
Change History:

(Refer to the tickets on trac-hacks for complete descriptions.)

Release 1.0.7 (2011-08-28):
  o Enhanced upgrade process

Release 1.0.6 (2011-06-19):
  o Fixed Ticket #8871 (Track-Hacks): No # allowed at custom fields

Release 1.0.4 (2011-01-17):
  o Added support for LIKE match in list_matching_objects.

Release 1.0.0 (2010-10-01):
  o First release publicly available apart from the core Test Manager plugin
  
