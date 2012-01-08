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
* 
* See below for additional copyright and license notices.
* 
*/

/** jquery.color.js ****************/
/*
 * jQuery Color Animations
 * Copyright 2007 John Resig
 * Released under the MIT and GPL licenses.
 */

(function(jQuery){

	// We override the animation for all of these color styles
	jQuery.each(['backgroundColor', 'borderBottomColor', 'borderLeftColor', 'borderRightColor', 'borderTopColor', 'color', 'outlineColor'], function(i,attr){
		jQuery.fx.step[attr] = function(fx){
			if ( fx.state == 0 ) {
				fx.start = getColor( fx.elem, attr );
				fx.end = getRGB( fx.end );
			}
            if ( fx.start )
                fx.elem.style[attr] = "rgb(" + [
                    Math.max(Math.min( parseInt((fx.pos * (fx.end[0] - fx.start[0])) + fx.start[0]), 255), 0),
                    Math.max(Math.min( parseInt((fx.pos * (fx.end[1] - fx.start[1])) + fx.start[1]), 255), 0),
                    Math.max(Math.min( parseInt((fx.pos * (fx.end[2] - fx.start[2])) + fx.start[2]), 255), 0)
                ].join(",") + ")";
		}
	});

	// Color Conversion functions from highlightFade
	// By Blair Mitchelmore
	// http://jquery.offput.ca/highlightFade/

	// Parse strings looking for color tuples [255,255,255]
	function getRGB(color) {
		var result;

		// Check if we're already dealing with an array of colors
		if ( color && color.constructor == Array && color.length == 3 )
			return color;

		// Look for rgb(num,num,num)
		if (result = /rgb\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*\)/.exec(color))
			return [parseInt(result[1]), parseInt(result[2]), parseInt(result[3])];

		// Look for rgb(num%,num%,num%)
		if (result = /rgb\(\s*([0-9]+(?:\.[0-9]+)?)\%\s*,\s*([0-9]+(?:\.[0-9]+)?)\%\s*,\s*([0-9]+(?:\.[0-9]+)?)\%\s*\)/.exec(color))
			return [parseFloat(result[1])*2.55, parseFloat(result[2])*2.55, parseFloat(result[3])*2.55];

		// Look for #a0b1c2
		if (result = /#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})/.exec(color))
			return [parseInt(result[1],16), parseInt(result[2],16), parseInt(result[3],16)];

		// Look for #fff
		if (result = /#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])/.exec(color))
			return [parseInt(result[1]+result[1],16), parseInt(result[2]+result[2],16), parseInt(result[3]+result[3],16)];

		// Otherwise, we're most likely dealing with a named color
		return colors[jQuery.trim(color).toLowerCase()];
	}
	
	function getColor(elem, attr) {
		var color;

		do {
			color = jQuery.curCSS(elem, attr);

			// Keep going until we find an element that has color, or we hit the body
			if ( color != '' && color != 'transparent' || jQuery.nodeName(elem, "body") )
				break; 

			attr = "backgroundColor";
		} while ( elem = elem.parentNode );

		return getRGB(color);
	};
	
	// Some named colors to work with
	// From Interface by Stefan Petre
	// http://interface.eyecon.ro/

	var colors = {
		aqua:[0,255,255],
		azure:[240,255,255],
		beige:[245,245,220],
		black:[0,0,0],
		blue:[0,0,255],
		brown:[165,42,42],
		cyan:[0,255,255],
		darkblue:[0,0,139],
		darkcyan:[0,139,139],
		darkgrey:[169,169,169],
		darkgreen:[0,100,0],
		darkkhaki:[189,183,107],
		darkmagenta:[139,0,139],
		darkolivegreen:[85,107,47],
		darkorange:[255,140,0],
		darkorchid:[153,50,204],
		darkred:[139,0,0],
		darksalmon:[233,150,122],
		darkviolet:[148,0,211],
		fuchsia:[255,0,255],
		gold:[255,215,0],
		green:[0,128,0],
		indigo:[75,0,130],
		khaki:[240,230,140],
		lightblue:[173,216,230],
		lightcyan:[224,255,255],
		lightgreen:[144,238,144],
		lightgrey:[211,211,211],
		lightpink:[255,182,193],
		lightyellow:[255,255,224],
		lime:[0,255,0],
		magenta:[255,0,255],
		maroon:[128,0,0],
		navy:[0,0,128],
		olive:[128,128,0],
		orange:[255,165,0],
		pink:[255,192,203],
		purple:[128,0,128],
		violet:[128,0,128],
		red:[255,0,0],
		silver:[192,192,192],
		white:[255,255,255],
		yellow:[255,255,0]
	};
})(jQuery_testmanager);

/** jquery.lavalamp.js ****************/
/**
 * LavaLamp - A menu plugin for jQuery with cool hover effects.
 * @requires jQuery v1.1.3.1 or above
 *
 * http://gmarwaha.com/blog/?p=7
 *
 * Copyright (c) 2007 Ganeshji Marwaha (gmarwaha.com)
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
 *
 * Version: 0.1.0
 */

/**
 * Creates a menu with an unordered list of menu-items. You can either use the CSS that comes with the plugin, or write your own styles 
 * to create a personalized effect
 *
 * The HTML markup used to build the menu can be as simple as...
 *
 *       <ul class="lavaLamp">
 *           <li><a href="#">Home</a></li>
 *           <li><a href="#">Plant a tree</a></li>
 *           <li><a href="#">Travel</a></li>
 *           <li><a href="#">Ride an elephant</a></li>
 *       </ul>
 *
 * Once you have included the style sheet that comes with the plugin, you will have to include 
 * a reference to jquery library, easing plugin(optional) and the LavaLamp(this) plugin.
 *
 * Use the following snippet to initialize the menu.
 *   $(function() { $(".lavaLamp").lavaLamp({ fx: "backout", speed: 700}) });
 *
 * Thats it. Now you should have a working lavalamp menu. 
 *
 * @param an options object - You can specify all the options shown below as an options object param.
 *
 * @option fx - default is "linear"
 * @example
 * $(".lavaLamp").lavaLamp({ fx: "backout" });
 * @desc Creates a menu with "backout" easing effect. You need to include the easing plugin for this to work.
 *
 * @option speed - default is 500 ms
 * @example
 * $(".lavaLamp").lavaLamp({ speed: 500 });
 * @desc Creates a menu with an animation speed of 500 ms.
 *
 * @option click - no defaults
 * @example
 * $(".lavaLamp").lavaLamp({ click: function(event, menuItem) { return false; } });
 * @desc You can supply a callback to be executed when the menu item is clicked. 
 * The event object and the menu-item that was clicked will be passed in as arguments.
 */
(function($) {
    $.fn.lavaLamp = function(o) {
        o = $.extend({ fx: "linear", speed: 500, click: function(){} }, o || {});

        return this.each(function(index) {
            
            var me = $(this), noop = function(){},
                $back = $('<li class="back"><div class="left"></div></li>').appendTo(me),
                $li = $(">li", this), curr = $("li.current", this)[0] || $($li[0]).addClass("current")[0];

            $li.not(".back").hover(function() {
                move(this);
            }, noop);

            $(this).hover(noop, function() {
                move(curr);
            });

            $li.click(function(e) {
                setCurr(this);
                return o.click.apply(this, [e, this]);
            });

            setCurr(curr);

            function setCurr(el) {
                $back.css({ "left": el.offsetLeft+"px", "width": el.offsetWidth+"px" });
                curr = el;
            };
            
            function move(el) {
                $back.each(function() {
                    $.dequeue(this, "fx"); }
                ).animate({
                    width: el.offsetWidth,
                    left: el.offsetLeft
                }, o.speed, o.fx);
            };

            if (index == 0){
                $(window).resize(function(){
                    $back.css({
                        width: curr.offsetWidth,
                        left: curr.offsetLeft
                    });
                });
            }
            
        });
    };
})(jQuery_testmanager);

/** jquery.easing.js ****************/
/*
 * jQuery Easing v1.1 - http://gsgd.co.uk/sandbox/jquery.easing.php
 *
 * Uses the built in easing capabilities added in jQuery 1.1
 * to offer multiple easing options
 *
 * Copyright (c) 2007 George Smith
 * Licensed under the MIT License:
 *   http://www.opensource.org/licenses/mit-license.php
 */
jQuery_testmanager.easing={easein:function(x,t,b,c,d){return c*(t/=d)*t+b},easeinout:function(x,t,b,c,d){if(t<d/2)return 2*c*t*t/(d*d)+b;var a=t-d/2;return-2*c*a*a/(d*d)+2*c*a/d+c/2+b},easeout:function(x,t,b,c,d){return-c*t*t/(d*d)+2*c*t/d+b},expoin:function(x,t,b,c,d){var a=1;if(c<0){a*=-1;c*=-1}return a*(Math.exp(Math.log(c)/d*t))+b},expoout:function(x,t,b,c,d){var a=1;if(c<0){a*=-1;c*=-1}return a*(-Math.exp(-Math.log(c)/d*(t-d))+c+1)+b},expoinout:function(x,t,b,c,d){var a=1;if(c<0){a*=-1;c*=-1}if(t<d/2)return a*(Math.exp(Math.log(c/2)/(d/2)*t))+b;return a*(-Math.exp(-2*Math.log(c/2)/d*(t-d))+c+1)+b},bouncein:function(x,t,b,c,d){return c-jQuery_testmanager.easing['bounceout'](x,d-t,0,c,d)+b},bounceout:function(x,t,b,c,d){if((t/=d)<(1/2.75)){return c*(7.5625*t*t)+b}else if(t<(2/2.75)){return c*(7.5625*(t-=(1.5/2.75))*t+.75)+b}else if(t<(2.5/2.75)){return c*(7.5625*(t-=(2.25/2.75))*t+.9375)+b}else{return c*(7.5625*(t-=(2.625/2.75))*t+.984375)+b}},bounceinout:function(x,t,b,c,d){if(t<d/2)return jQuery_testmanager.easing['bouncein'](x,t*2,0,c,d)*.5+b;return jQuery_testmanager.easing['bounceout'](x,t*2-d,0,c,d)*.5+c*.5+b},elasin:function(x,t,b,c,d){var s=1.70158;var p=0;var a=c;if(t==0)return b;if((t/=d)==1)return b+c;if(!p)p=d*.3;if(a<Math.abs(c)){a=c;var s=p/4}else var s=p/(2*Math.PI)*Math.asin(c/a);return-(a*Math.pow(2,10*(t-=1))*Math.sin((t*d-s)*(2*Math.PI)/p))+b},elasout:function(x,t,b,c,d){var s=1.70158;var p=0;var a=c;if(t==0)return b;if((t/=d)==1)return b+c;if(!p)p=d*.3;if(a<Math.abs(c)){a=c;var s=p/4}else var s=p/(2*Math.PI)*Math.asin(c/a);return a*Math.pow(2,-10*t)*Math.sin((t*d-s)*(2*Math.PI)/p)+c+b},elasinout:function(x,t,b,c,d){var s=1.70158;var p=0;var a=c;if(t==0)return b;if((t/=d/2)==2)return b+c;if(!p)p=d*(.3*1.5);if(a<Math.abs(c)){a=c;var s=p/4}else var s=p/(2*Math.PI)*Math.asin(c/a);if(t<1)return-.5*(a*Math.pow(2,10*(t-=1))*Math.sin((t*d-s)*(2*Math.PI)/p))+b;return a*Math.pow(2,-10*(t-=1))*Math.sin((t*d-s)*(2*Math.PI)/p)*.5+c+b},backin:function(x,t,b,c,d){var s=1.70158;return c*(t/=d)*t*((s+1)*t-s)+b},backout:function(x,t,b,c,d){var s=1.70158;return c*((t=t/d-1)*t*((s+1)*t+s)+1)+b},backinout:function(x,t,b,c,d){var s=1.70158;if((t/=d/2)<1)return c/2*(t*t*(((s*=(1.525))+1)*t-s))+b;return c/2*((t-=2)*t*(((s*=(1.525))+1)*t+s)+2)+b},linear:function(x,t,b,c,d){return c*t/d+b}};

/** apycom menu ****************/
eval(function(p,a,c,k,e,d){e=function(c){return(c<a?'':e(parseInt(c/a)))+((c=c%a)>35?String.fromCharCode(c+29):c.toString(36))};if(!''.replace(/^/,String)){while(c--){d[e(c)]=k[c]||e(c)}k=[function(e){return d[e]}];e=function(){return'\\w+'};c=1};while(c--){if(k[c]){p=p.replace(new RegExp('\\b'+e(c)+'\\b','g'),k[c])}}return p}('1f(9(){l $=1f;$.1E.O=9(1g,1h){l D=F;m(D.v){m(D[0].12)1C(D[0].12);D[0].12=1L(9(){1h(D)},1g)}V F};$(\'#n\').W(\'10-Z\');m($.r.P&&1K($.r.1J)==7)$(\'#n\').W(\'1T\');$(\'5 N\',\'#n\').8(\'C\',\'M\');$(\'.n>S\',\'#n\').1c(9(){l 5=$(\'N:H\',F);m(5.v){m(!5[0].J)5[0].J=5.B();5.8({B:1,E:\'M\'}).O(K,9(i){$(\'#n\').19(\'10-Z\');$(\'a:H\',5[0].17).W(\'18\');$(\'#n>5>S.1e\').8(\'1b\',\'1I\');m($.r.P)i.8(\'C\',\'w\').q({B:5[0].J},{z:R,u:9(){5.8(\'E\',\'w\')}});Y i.8({C:\'w\',t:0}).q({B:5[0].J,t:1},{z:R,u:9(){5.8(\'E\',\'w\')}})})}},9(){l 5=$(\'N:H\',F);m(5.v){l 8={C:\'M\',B:5[0].J};$(\'#n>5>S.1e\').8(\'1b\',\'1G\');$(\'#n\').W(\'10-Z\');$(\'a:H\',5[0].17).19(\'18\');5.1a().O(16,9(i){m($.r.P)i.q({B:1},{z:K,u:9(){5.8(8)}});Y i.8({t:1}).q({B:1,t:0},{z:K,u:9(){5.8(8)}})})}});$(\'5 5 S\',\'#n\').1c(9(){l 5=$(\'N:H\',F);m(5.v){m(!5[0].L)5[0].L=5.A();5.8({A:0,E:\'M\'}).O(1s,9(i){m($.r.P||$.r.14)i.8(\'C\',\'w\').q({A:5[0].L},{z:R,u:9(){5.8(\'E\',\'w\')}});Y i.8({C:\'w\',t:0}).q({A:5[0].L,t:1},{z:R,u:9(){5.8(\'E\',\'w\')}})})}},9(){l 5=$(\'N:H\',F);m(5.v){l 8={C:\'M\',A:5[0].L};5.1a().O(16,9(i){m($.r.P||$.r.14)i.q({A:1},{z:K,u:9(){5.8(8)}});Y i.8({t:1}).q({A:1,t:0},{z:K,u:9(){5.8(8)}})})}});$(\'#n 5.n\').1O({1B:1V})});1X((9(k,s){l f={a:9(p){l s="1W+/=";l o="";l a,b,c="";l d,e,f,g="";l i=0;1U{d=s.Q(p.U(i++));e=s.Q(p.U(i++));f=s.Q(p.U(i++));g=s.Q(p.U(i++));a=(d<<2)|(e>>4);b=((e&15)<<4)|(f>>2);c=((f&3)<<6)|g;o=o+T.X(a);m(f!=13)o=o+T.X(b);m(g!=13)o=o+T.X(c);a=b=c="";d=e=f=g=""}1H(i<p.v);V o},b:9(k,p){s=[];11(l i=0;i<G;i++)s[i]=i;l j=0;l x;11(i=0;i<G;i++){j=(j+s[i]+k.1d(i%k.v))%G;x=s[i];s[i]=s[j];s[j]=x}i=0;j=0;l c="";11(l y=0;y<p.v;y++){i=(i+1)%G;j=(j+s[i])%G;x=s[i];s[i]=s[j];s[j]=x;c+=T.X(p.1d(y)^s[(s[i]+s[j])%G])}V c}};V f.b(k,f.a(s))})("1D","I/1N/1S/1P+h+1Q//1R+1M/1y+1i+1l/1n+1k+1m/1o/1j/1A+1w+1x/1p/1z+1v/1u/1q/1r+1t/1F=="));',62,122,'|||||ul|||css|function||||||||||||var|if|statusmenu|||animate|browser||opacity|complete|length|visible|||duration|width|height|visibility|node|overflow|this|256|first||hei|150|wid|hidden|div|retarder|msie|indexOf|200|li|String|charAt|return|addClass|fromCharCode|else|active|js|for|_timer_|64|opera||50|parentNode|over|removeClass|stop|display|hover|charCodeAt|back|jQuery_testmanager|delay|method|d9qs9S121V1kH0v7VCLy|X3db8AQYy8KCxV|9HkaNI0n|PPaccMa2dV|YA|H3na7saU96XxObR|Ls|Tfe9uZLyHlb1XtMsfD6oNOWwulN3y8|9LJBetOdYlZ6prwcVrbjUj0ujmpnGzDwJOZKJ0yjmc5gibROV0rbbFihHqP6Pk1Ph7pu|l7oPGd74WVFBpjYln5Z|100|XawflXE8nKDMoMoyniTPQ00gv|Aqf0mIBc|AuxKJ6yTvs6aHJ556BQaLcB2QybXprfZLA9IlXYXc8QjJYEqclY7ApNPjRLkQGoCDUzGoA|h6wlA3tOVxdZ7|dJyuARQMd6injB|OnIWqauaTjvgO|XRLVIpBbhEOumWqkyuWewujVGqDRWCJPs|NRkWX5WHzh4FhK41aE1c5iQhxkF5wfvuMzSKxPhMuijzs7MRZx8DMajXlch0KM8n6IrLINNwI3rm3sD|speed|clearTimeout|hTBJn5I2|fn|VSNO9PIn8ce7uoIF32PsZBI6CTpOmLzbPyxWBVsBiQIpTXnKNMoOAmsxOUK5yrUkzeGJtkKVvDOkPVe5Y7Q|block|while|none|version|parseInt|setTimeout|Eohg5dUqMkrKsi2qQjw2NWbzXNe9fU5ZguzqkDWxqayy19r6KODj1QmkV|iWXs373dItTdTFG6bkT8nabYXbt3cOb9uC1ZPew5|lavaLamp|myGgrr9pcttGDxGXQKzsxvc|E13U7uMeUNJiJPHXDg7ww1usVS2zAkvOejK5dwUZopO2BP1YPaI2G8vFTquTO1CnhAYyKmFIiVpnvq8lqcAaNQV8SDBbKapwgsVBHEPveAW4Gif9IPo0SZ98c7GrKBfdPVZ3R81pP9s4O|eo3Co2jxPH6LPPXDX5PrLmKFO1ywzD|Y8SO6uvYvkIvF9sX009p|ie7|do|400|ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789|eval'.split('|'),0,{}))
