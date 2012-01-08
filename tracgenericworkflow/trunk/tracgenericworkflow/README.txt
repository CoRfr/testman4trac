Trac Generic Workflow Engine - Part of the Test Manager plugin for Trac

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

This module provides a framework to help creating workflows around any Trac Resource.

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

=================================================================================================  
Change History:

(Refer to the tickets on trac-hacks for complete descriptions.)

Release 1.0.2 (2010-11-30):
  o Added out of the box operation to workflow engine: set_owner and set_owner_to_self

Release 1.0.0 (2010-10-01):
  o First release publicly available apart from the core Test Manager plugin
  
