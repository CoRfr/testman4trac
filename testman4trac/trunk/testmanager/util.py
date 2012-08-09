# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2012 Roberto Longobardi
# 
# This file is part of the Test Manager plugin for Trac.
# 
# The Test Manager plugin for Trac is free software: you can 
# redistribute it and/or modify it under the terms of the GNU 
# General Public License as published by the Free Software Foundation, 
# either version 3 of the License, or (at your option) any later 
# version.
# 
# The Test Manager plugin for Trac is distributed in the hope that it 
# will be useful, but WITHOUT ANY WARRANTY; without even the implied 
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with the Test Manager plugin for Trac. See the file LICENSE.txt. 
# If not, see <http://www.gnu.org/licenses/>.
#

import re
from trac.core import *
from trac.util.text import CRLF

def get_page_title(text):
    result = None
    
    if text is not None:
        result = text.split('\n')[0].strip('\r\n').strip('= \'')

    if result == None:
        if text is not None:
            result = text
        else:
            result = ''
    
    return result
    
def get_page_description(text):
    result = None
    
    if text is not None:
        result = text.partition(CRLF)[2]

    if result == None:
        if text is not None:
            result = text
        else:
            result = ''
        
    return result
 
html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
    }

def html_escape(text):
    """Produce entities within text."""
    return "".join(html_escape_table.get(c,c) for c in text)
    
