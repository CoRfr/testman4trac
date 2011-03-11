/*- coding: utf-8
 *
 * Copyright (C) 2010 Roberto Longobardi - seccanj@gmail.com
 */

/******************************************************/
/**              Compatibility layer                  */
/******************************************************/


function expandCollapseSection(nodeId) {
    /* In Trac 0.11 we must handle sections explicitly */
    $('#'+nodeId).toggleClass('collapsed');
}

function _(str) {
	return str;
}
