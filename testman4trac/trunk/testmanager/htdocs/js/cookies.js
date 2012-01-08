/* -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2011 Roberto Bordolanghi
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
*/

/**
 * Returns the value of the specified cookie, or null if the cookie is not found or has no value.
 */
function getCookie( name ) {
	var allCookies = document.cookie.split( ';' );
	var tempCookie = '';
	var cookieName = '';
	var cookieValue = '';
	var found = false;
	var i = '';
	
	for ( i = 0; i < allCookies.length; i++ ) {
		/* split name=value pairs */
		tempCookie = allCookies[i].split( '=' );
		
		
		/* trim whitespace */
		cookieName = tempCookie[0].replace(/^\s+|\s+$/g, '');
	
		if ( cookieName == name ) {
			found = true;
			/* handle case where cookie has no value (i.e. no equal sign)  */
			if ( tempCookie.length > 1 ) {
				cookieValue = unescape( tempCookie[1].replace(/^\s+|\s+$/g, '') );
			}
            
			return cookieValue;
			break;
		}
		tempCookie = null;
		cookieName = '';
	}
    
	if ( !found ) {
		return null;
	}
}

/**
 * Sets a cookie with the input name and value.
 * These are the only required parameters.
 * The expires parameter must be expressed in hours.
 * Generally you don't need to worry about domain, path or secure for most applications.
 * In these cases, do not pass null values, but empty strings.
 */
function setCookie( name, value, expires, path, domain, secure ) {
	var today = new Date();
	today.setTime( today.getTime() );

	if ( expires ) {
		expires = expires * 1000 * 60 * 60;
	}

	var expires_date = new Date( today.getTime() + (expires) );

	document.cookie = name + "=" +escape( value ) +
		( ( expires ) ? ";expires=" + expires_date.toGMTString() : "" ) +
		( ( path ) ? ";path=" + path : "" ) + 
		( ( domain ) ? ";domain=" + domain : "" ) +
		( ( secure ) ? ";secure" : "" );
}

/**
 * Deletes the specified cookie
 */
function deleteCookie( name, path, domain ) {
	if ( getCookie( name ) ) {
        document.cookie = name + "=" +
			( ( path ) ? ";path=" + path : "") +
			( ( domain ) ? ";domain=" + domain : "" ) +
			";expires=Thu, 01-Jan-1970 00:00:01 GMT";
    }
}
