# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Roberto Longobardi
#

import re
from trac.core import *
from trac.util.text import CRLF

def get_page_title(text):
    return text.split('\n')[0].strip('\r\n').strip('= \'')

    
def get_page_description(text):
    return text.partition(CRLF)[2]

 
