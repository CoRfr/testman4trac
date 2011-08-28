﻿/*- coding: utf-8
 *
 * Copyright (C) 2010 Roberto Longobardi - seccanj@gmail.com
 */

/******************************************************/
/**         Test case, catalog, plan creation         */
/******************************************************/

function creaTestCatalog(path) {
	var tcInput = document.getElementById("catName");
	var catalogName = tcInput.value;
    
    if (catalogName == null || catalogName.length == 0) {
		document.getElementById('catErrorMsgSpan').innerHTML = _("You must specify a name. Length between 4 and 90 characters.");
    } else {
    	var catName = stripLessSpecialChars(catalogName);
    	
    	if (catName.length > 90 || catName.length < 4) {
    		document.getElementById('catErrorMsgSpan').innerHTML = _("Length between 4 and 90 characters.");
    	} else { 
    		document.getElementById('catErrorMsgSpan').innerHTML = ''; 
    		var url = baseLocation+"/testcreate?type=catalog&path="+path+"&title="+catName;
    		window.location = url;
    	}
    }
}

function creaTestCase(catName){ 
	var tcInput = document.getElementById('tcName');
	var testCaseName = tcInput.value; 

    if (testCaseName == null || testCaseName.length == 0) {
		document.getElementById('errorMsgSpan').innerHTML = _("You must specify a name. Length between 4 and 90 characters.");
    } else {
    	var tcName = stripLessSpecialChars(testCaseName); 
    	
    	if (tcName.length > 90 || tcName.length < 4) {
    		document.getElementById('errorMsgSpan').innerHTML = _("Length between 4 and 90 characters.");
    	} else { 
    		document.getElementById('errorMsgSpan').innerHTML = ''; 
    		var url = baseLocation+"/testcreate?type=testcase&path="+catName+"&title="+tcName;
    		window.location = url;
    	}
    }
}

function creaTestPlan(catName){ 
	var planInput = document.getElementById('planName');
	var testPlanName = planInput.value; 

    if (testPlanName == null || testPlanName.length == 0) {
		document.getElementById('errorMsgSpan2').innerHTML = _("You must specify a name. Length between 4 and 90 characters.");
    } else {
    	var tplanName = stripLessSpecialChars(testPlanName); 
    	
    	if (tplanName.length > 90 || tplanName.length < 4) {
    		document.getElementById('errorMsgSpan2').innerHTML = _("Length between 4 and 90 characters.");
    	} else { 
    		document.getElementById('errorMsgSpan2').innerHTML = ''; 
    		var url = baseLocation+"/testcreate?type=testplan&path="+catName+"&title="+tplanName;
    		window.location = url;
    	}
    }
}

function duplicateTestCase(tcName, catName){ 
	var url = baseLocation+'/testcreate?type=testcase&duplicate=true&tcId='+tcName+'&path='+catName; 
	window.location = url;
}

function regenerateTestPlan(planId, path) {
    var url = baseLocation+"/testcreate?type=testplan&update=true&planid="+planId+"&path="+path;
    window.location = url;
}

function creaTicket(tcName, planId, planName, summary){
    var tokens = $('span[name=breadcrumb]').map(function() { return this.innerHTML }).get();
    var fullSummary = "";
    
    for (i=1; i<tokens.length; i++) {
        fullSummary += tokens[i] + " - ";
    }
    
    fullSummary += summary + " - " + _("[Insert problem summary]");

	var url = baseLocation+'/newticket?testcaseid='+tcName+'&planid='+planId+'&planname='+planName+'&summary='+stripLessSpecialChars(fullSummary)+'&description=Test%20Case:%20[wiki:'+tcName+'?planid='+planId+'],%20Test%20Plan:%20'+planName+'%20('+planId+')'; 
	window.location = url;
}

function showTickets(tcName, planId, planName){ 
	var url = baseLocation+'/query?description=~'+tcName+'?planId='+planId; 
	window.location = url;
}

function duplicateTestCatalog(catName){
    if (confirm(_("Are you sure you want to duplicate the test catalog and all its contained test cases?"))) {
        var url = baseLocation+'/testcreate?type=catalog&duplicate=true&path='+catName; 
        window.location = url;
    }
}

function deleteTestPlan(url){
    if (confirm(_("Are you sure you want to delete the test plan and the state of all its contained test cases?"))) {
        window.location = url;
    }
}

/******************************************************/
/**    Move or copy test case into another catalog    */
/******************************************************/

function checkMoveTCDisplays() {
    displayNode('copiedTCMessage', isPasteEnabled());
    displayNode('pasteTCHereMessage', isPasteEnabled());
    displayNode('pasteTCHereButton', isPasteEnabled(), 'inline');

    displayNode('copiedMultipleTCsMessage', isMultiplePasteEnabled());
    displayNode('pasteMultipleTCsHereMessage', isMultiplePasteEnabled());
    displayNode('pasteMultipleTCsHereButton', isMultiplePasteEnabled(), 'inline');
}

function isPasteEnabled() {
    if (getCookie('TestManager_TestCase')) {
        return true;
    }
    
    return false;
}

function isMultiplePasteEnabled() {
    if (getCookie('TestManager_MultipleTestCases')) {
        return true;
    }
    
    return false;
}

function showSelectionCheckboxes(id) {
	/* toggleAll(true); */

    var nodes=null;
    if (document.getElementById("ticketContainer") !== null) {
        nodes=document.getElementById("ticketContainer").getElementsByTagName('input');
    }
    
    if (document.getElementById("testcaseList") !== null) {
        nodes=document.getElementById("testcaseList").getElementsByTagName('input');
    }

	for (var i=0;i<nodes.length;i++) {
		var el=nodes.item(i);
		
		if (el.getAttribute("name") && el.getAttribute("name") == "select_tc_checkbox") {
			el.style.display = "block";
		}
	}
}

function copyTestCaseToClipboard(tcId) {
    setCookie('TestManager_TestCase', tcId, 1, '/', '', '');
    setTimeout('window.location="'+window.location+'"', 100);
}

function copyMultipleTestCasesToClipboard() {
	var selectedTickets = "";

    var nodes=document.getElementById("ticketContainer").getElementsByTagName('input');
	for (var i=0;i<nodes.length;i++) {
		var el=nodes.item(i);
		
		if (el.getAttribute("name") && el.getAttribute("name") == "select_tc_checkbox") {
			if (el.checked) {
				selectedTickets += el.value + ','
			}
		}
	}

    setCookie('TestManager_MultipleTestCases', selectedTickets, 1, '/', '', '');
    setTimeout('window.location="'+window.location+'"', 100);
}

function pasteTestCaseIntoCatalog(catName) {
    var tcId = getCookie('TestManager_TestCase');
    
    if (tcId != null) {
        deleteCookie('TestManager_TestCase', '/', '');
        var url = baseLocation+"/testcreate?type=testcase&paste=true&path="+catName+"&tcId="+tcId;
        window.location = url;
    }
}

function pasteMultipleTestCasesIntoCatalog(catName) {
    var tcIds = getCookie('TestManager_MultipleTestCases');
    
    if (tcIds != null) {
        deleteCookie('TestManager_MultipleTestCases', '/', '');
        var url = baseLocation+"/testcreate?type=testcase&paste=true&multiple=true&path="+catName+"&tcId="+tcIds;
        window.location = url;
    }
}

function cancelTCMove() {
    deleteCookie('TestManager_TestCase', '/', '');
    setTimeout('window.location="'+window.location+'"', 100);
}

function cancelTCsCopy() {
    deleteCookie('TestManager_MultipleTestCases', '/', '');
    setTimeout('window.location="'+window.location+'"', 100);
}

/******************************************************/
/**                 Tree view widget                  */
/******************************************************/

function importTestCasesIntoCatalog(catName) {
	(function($) {
        $(function() {
            $("#dialog").dialog({width: 640, height: 430, modal: true});
        });
    })(jQuery_testmanager);	
}

function importTestCasesCancel() {
	(function($) {
        $(function() {
            $("#dialog").dialog('close');
        });
    })(jQuery_testmanager);	
}

/******************************************************/
/**                 Tree view widget                  */
/******************************************************/

/** Configuration property to specify whether non-matching search results should be hidden. */ 
var selectHide = true;
/** Configuration property to specify whether matching search results should be displayed in bold font. */
var selectBold = true;

var selectData = [];
var deselectData = [];
var htimer = null;
var searchResults = 0;

function toggleAll(isexpand) {
    var nodes=document.getElementById("ticketContainer").getElementsByTagName("span");
    for(var i=0;i<nodes.length;i++) {
        if(nodes.item(i).getAttribute("name") === "toggable") {
            if (isexpand) {
                expand(nodes.item(i).id);
            } else {
                collapse(nodes.item(i).id);
            }
        }
    }
}

function collapse(id) {
    el = document.getElementById(id);
    if (el.getAttribute("name") === "toggable") {
        el.firstChild['expanded'] = false;
        el.firstChild.innerHTML = '<img class="iconElement" src="'+baseLocation+'/chrome/testmanager/images/plus.png" />';
        document.getElementById(el.id+"_list").style.display = "none";
    }
}

function expand(id) {
    el = document.getElementById(id);
    if (el.getAttribute("name") === "toggable") {
        el.firstChild['expanded'] = true;
        el.firstChild.innerHTML = '<img class="iconElement" src="'+baseLocation+'/chrome/testmanager/images/minus.png" />';
        document.getElementById(el.id+"_list").style.display = "";
    }
}

function toggle(id) {
    var el=document.getElementById(id);
    if (el.firstChild['expanded']) {
        collapse(id)
    } else {
        expand(id)
    }
}

function highlight(str) {
    clearSelection();
    if (str && str !== "") {
        var res=[];
        var tks=str.split(" ");
        for (var i=0;i<tks.length;i++) {
            res[res.length]=new RegExp(regexpescape(tks[i].toLowerCase()), "g");
        }
        var nodes=document.getElementById("ticketContainer").getElementsByTagName("a");
        for(var i=0;i<nodes.length;i++) {
            var n=nodes.item(i);
            if (n.nextSibling) {
                if (filterMatch(n, n.nextSibling, res)) {
                    select(n);
                } else {
                    deselect(n);
                }
            }
        }

        document.getElementById('searchResultsNumberId').innerHTML = _("Results: ")+searchResults;
    }
}

function regexpescape(text) {
    return text.replace(/[-[\]{}()+?.,\\\\^$|#\s]/g, "\\\\$&").replace(/\*/g,".*");
}

function filterMatch(node1,node2,res) {
    var name=(node1.innerHTML + (node2 ? node2.innerHTML : "")).toLowerCase();
    var match=true;
    for (var i=0;i<res.length;i++) {
        match=match && name.match(res[i]);
    } 
    return match;
}

function clearSelection() {
    toggleAll(false);
    for (var i=0;i<selectData.length;i++) {
        selectData[i].style.fontWeight="normal";
        selectData[i].style.display=""
    };
    
    selectData=[];
    
    for (var i=0;i<deselectData.length;i++) {
        if (selectHide) {
            deselectData[i].style.display=""
        }
    };
    
    deselectData=[];
    searchResults = 0;
    
    document.getElementById("searchResultsNumberId").innerHTML = '';
}

function select(node) {
    searchResults++;

    do {
        if(node.tagName ==="UL" && node.id.indexOf("b_") === 0) {
            expand(node.id.substr(0,node.id.indexOf("_list")));
        };

        if(node.tagName === "LI") {
            if (selectBold) {
                node.style.fontWeight = "bold";
            };
            
            if (selectHide) {
                node.style.display = "block";
            };
            
            selectData[selectData.length]=node;
        };
        node=node.parentNode;
    } while (node.id!=="ticketContainer");
}

function deselect(node) {
    do {
        if (node.tagName === "LI") {
            if (selectHide && node.style.display==="") {
                node.style.display = "none";
                deselectData[deselectData.length]=node;
            }
        };
        
        node=node.parentNode;
    } while (node.id!=="ticketContainer");
}

function starthighlight(str,now) {
    if (htimer) {
        clearTimeout(htimer);
    } 
    if (now) {
        highlight(str);
    } else {
        htimer = setTimeout(function() {
                                highlight(str);
                            },500);
    }
}

function checkFilter(now) {
    var f=document.getElementById("tcFilter");
    if (f) {
        if (document.getElementById("ticketContainer") !== null) {
            starthighlight(f.value,now);
        }
        
        if (document.getElementById("testcaseList") !== null) {
            starthighlightTable(f.value,now);
        }
    }
}

function underlineLink(id) {
    el = document.getElementById(id);
    el.style.backgroundColor = '#EEEEEE';
    el.style.color = '#BB0000';
    el.style.textDecoration = 'underline';
}

function removeUnderlineLink(id) {
    el = document.getElementById(id);
    el.style.backgroundColor = 'white';
    el.style.color = 'black';
    el.style.textDecoration = 'none';
}

/******************************************************/
/**                 Tree table widget                 */
/******************************************************/

function starthighlightTable(str,now) {
    if (htimer) {
        clearTimeout(htimer);
    } 
    if (now) {
        highlightTable(str);
    } else {
        htimer = setTimeout(function() {
                                highlightTable(str);
                            },500);
    }
}

function highlightTable(str) {
    clearSelectionTable();
    if (str && str !== "") {
        var res=[];
        var tks=str.split(" ");
        for (var i=0;i<tks.length;i++) {
            res[res.length]=new RegExp(regexpescape(tks[i].toLowerCase()), "g");
        }
        var nodes=document.getElementById("testcaseList").getElementsByTagName("tr");
        for(var i=0;i<nodes.length;i++) {
            var n=nodes.item(i);
            if (filterMatchTable(n, res)) {
                selectRow(n);
            } else {
                deselectRow(n);
            }
        }

        document.getElementById('searchResultsNumberId').innerHTML = _("Results: ")+searchResults;
    }
}

function filterMatchTable(node, res) {
    var name = ""
    
    while (node.tagName !== "TR") {
        node = node.parentNode;
    }
    
    if (node.getAttribute("name") === "testcatalog") {
        return false;
    }
    
    node = node.firstChild;
    while (node != null) {
        if (node.tagName === "TD") {
            name += node.innerHTML;
        }
        
        node = node.nextSibling;
    }
    
    name = name.toLowerCase();

    var match=true;
    for (var i=0;i<res.length;i++) {
        match=match && name.match(res[i]);
    }
    
    return match;
}

function clearSelectionTable() {
    for (var i=0;i<selectData.length;i++) {
        selectData[i].className="";
    };
    
    selectData=[];
    
    for (var i=0;i<deselectData.length;i++) {
        deselectData[i].className=""
    };
    
    deselectData=[];
    searchResults = 0;
    
    document.getElementById("searchResultsNumberId").innerHTML = '';
}

function selectRow(node) {
    searchResults++;

    while (node.tagName !== "TR") {
        node = node.parentNode;
    }

    node.className = "rowSelected"

    selectData[selectData.length]=node;
}

function deselectRow(node) {
    while (node.tagName !== "TR") {
        node = node.parentNode;
    }

    node.className = "rowHidden"
    
    deselectData[deselectData.length]=node;
}

function showPencil(id) {
    el = document.getElementById(id);
    el.style.display = '';
}

function hidePencil(id) {
    el = document.getElementById(id);
    el.style.display = 'none';
}

/******************************************************/
/**        Test case in plan status management        */
/******************************************************/

function changestate(tc, planid, path, newStatus, newStatusColor, newLabel) {

    var url = baseLocation+"/teststatusupdate?id="+tc+"&planid="+planid+"&status="+newStatus+"&path="+path;
    
    result = doAjaxCall(url, "GET", "");
    
    oldIconSpan = document.getElementById("tcStatus"+currStatusColor);
    oldIconSpan.style.border="";
    
    newIconSpan = document.getElementById("tcStatus"+newStatusColor);
    newIconSpan.style.border="2px solid black";
    
    displayNode("tcTitleStatusIcon"+currStatusColor, false);

    document.getElementById("tcTitleStatusIcon"+newStatusColor).title = newLabel;
    displayNode("tcTitleStatusIcon"+newStatusColor, true);

    currStatus = newStatus; 
    currStatusColor = newStatusColor;
}

function changestateOnPlan(imgNodeId, tc, planid, newStatus, newStatusColor, newLabel) {
    var url = baseLocation+"/teststatusupdate?id="+tc+"&planid="+planid+"&status="+newStatus;
    result = doAjaxCall(url, "GET", "");
    
    // TODO: Handle errors in the Ajax call
    
    $('#'+imgNodeId)[0].src = "../chrome/testmanager/images/"+newStatusColor+".png";
    $('#'+imgNodeId)[0].title = newLabel;
}

function showColorOutcomes(imgNodeId, color) {
    var menuColorIcon = $("#statusContextMenuColorIcon"+color);
    var position = menuColorIcon.offset();
    
    for (c in statuses_by_color) {
        if (c == color) {
            if (statuses_by_color[c].length > 1) {
                $("#statusChangeSubMenu"+c)[0].innerHTML = getStatusSubContextMenuMarkup(imgNodeId, color);
                $("#statusChangeSubMenu"+c).css({display: "block", left: position.left - 27, top: position.top + 20}).stop(true,true).fadeTo(200, 1);
            }
        } else {
            $("#statusChangeSubMenu"+c).hide();
        }
    }
}

function bindTCStatusMenus() {
    if (statuses_by_color) {
        (function($) {
            $(function() {
                var menu = document.createElement("div");
                menu.setAttribute("id", "statusChangeMenu");
                menu.className = "statusContextMenuDiv";
                menu.style.display = "none";
                document.body.appendChild(menu);

                for (color in statuses_by_color) {
                    if (statuses_by_color[color].length > 1) {
                        var subMenu = document.createElement("div");
                        subMenu.setAttribute("id", "statusChangeSubMenu"+color);
                        subMenu.className = "statusContextSubMenuDiv";
                        subMenu.style.display = "none";
                        document.body.appendChild(subMenu);
                    }
                }

                $(".statusIconElement").bind('click', function(event) {
                    event.stopPropagation();
                
                    var $this = $(this);
                    var position = $this.offset();
                    
                    $("#statusChangeMenu")[0].innerHTML = getStatusContextMenuMarkup($this[0]);
                    $("#statusChangeMenu").css({left: position.left - 20, top: position.top}).stop(true,true).fadeTo(200, 1);
                });
                
                $(document).bind('click', function(event) {
                    if ($("#statusChangeMenu").css("display") == "block") {
                        $("#statusChangeMenu").hide();
                    }
                    
                    for (color in statuses_by_color) {
                        if (statuses_by_color[color].length > 1) {
                            if ($("#statusChangeSubMenu"+color).css("display") == "block") {
                                $("#statusChangeSubMenu"+color).hide();
                            }
                        }
                    }
                });
            });
        })(jQuery_testmanager);	
    }
}

function getStatusContextMenuMarkup(imgNode) {
    var params = imgNode.getAttribute("name").split(",");
    var tcid = params[0];
    var planid = params[1];
    var path = params[2];
    var oldStatus = params[3];
    var oldColor = params[4];
    var oldLabel = params[5];

    var result = "<ul class=\"statusContextMenuUl\">";

    for (color in statuses_by_color) {
        if (statuses_by_color[color].length > 1) {
            result += "<li><img id='statusContextMenuColorIcon"+color+"' class=\"statusContextMenuColorIcon\" onmouseover=\"showColorOutcomes('"+imgNode.id+"', '"+color+"');\" src=\"../chrome/testmanager/images/"+color+".png\"></img></li>";
        } else {
            for (outcome in statuses_by_color[color][0]) {
                var label = statuses_by_color[color][0][outcome];
                result += "<li><img id='statusContextMenuColorIcon"+color+"' class=\"statusContextMenuColorIcon\" onmouseover=\"showColorOutcomes('"+imgNode.id+"', '"+color+"');\" onclick=\"changestateOnPlan('"+imgNode.id+"', '"+tcid+"', '"+planid+"', '"+outcome+"', '"+color+"', '"+label+"');\" src=\"../chrome/testmanager/images/"+color+".png\"></img></li>";
            }
        }
    }
    
    result += "</ul>";
    
    return result;
}

function getStatusSubContextMenuMarkup(imgNodeId, color) {
    var imgNode = $("#"+imgNodeId)[0];

    var params = imgNode.getAttribute("name").split(",");
    var tcid = params[0];
    var planid = params[1];
    var path = params[2];
    var oldStatus = params[3];
    var oldColor = params[4];
    var oldLabel = params[5];

    var result = "<ul class='statusContextSubMenuUl'>";
    
    for (i=0; i<statuses_by_color[color].length; i++) {
        for (outcome in statuses_by_color[color][i]) {
            var label = statuses_by_color[color][i][outcome];
            result += "<li class='statusContextSubMenuItem"+color+"' onclick=\"changestateOnPlan('"+imgNode.id+"', '"+tcid+"', '"+planid+"', '"+outcome+"', '"+color+"', '"+label+"');\">"+statuses_by_color[color][i][outcome]+"</li>";
        }
    }

    result += "</ul>";

    return result;
}


/******************************************************/
/**                  Utility functions                */
/******************************************************/

function expandCollapseSection(nodeId) {
    /* In Trac 0.12 should do nothing, because a listener is
     * already in charge of handling sections */
}

function stripSpecialChars(str) {
    result = str.replace(/[ ',;:àèéìòù£§<>!"%&=@#\[\]\-\\\\^\$\.\|\?\*\+\(\)\{\}]/g, '');
    return result;
}

function stripLessSpecialChars(str) {
    result = str.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/[;#&\?]/g, '');
    return result;
}

function displayNode(id, show, mode) {
    var msgNode = document.getElementById(id);
    if (msgNode) {
       msgNode.style.display = show ? (mode ? mode : "block") : "none";
    }
}

function doAjaxCall(url, method, params) {
    if (window.XMLHttpRequest) {
        /* code for IE7+, Firefox, Chrome, Opera, Safari */
         xmlhttp = new XMLHttpRequest();
    } else {
        /* code for IE6, IE5 */
        xmlhttp = new ActiveXObject("Microsoft.XMLHTTP");
    }
    
    xmlhttp.open(method, url, false);
    
    if (method == "POST") {
        xmlhttp.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
        params = "__FORM_TOKEN="+getCookie('trac_form_token')+"&"+params;
    }
    
    xmlhttp.send(params);
    responseText = xmlhttp.responseText;
    
    return responseText;
}



function editField(name) {
    displayNode('custom_field_value_'+name, false);
    displayNode('custom_field_'+name, true);
    displayNode('update_button_'+name, true);
}

function sendUpdate(realm, name) {
   	var objKeyField = document.getElementById("obj_key_field");
    var objKey = objKeyField.value;

   	var objPropsField = document.getElementById("obj_props_field");
    var objProps = objPropsField.value;

   	var inputField = document.getElementById("custom_field_"+name);
	var value = inputField.value;
    
    var url = baseLocation+"/propertyupdate";
    params = "realm="+realm+"&key="+objKey+"&props="+objProps+"&name="+name+"&value="+value;
    
    result = doAjaxCall(url, "POST", params); 

   	var readonlyField = document.getElementById("custom_field_value_"+name);
    readonlyField.innerHTML = value;

    displayNode('custom_field_value_'+name, true);
    displayNode('custom_field_'+name, false);
    displayNode('update_button_'+name, false);
}

function getLocale() {
	if ( navigator ) {
		if ( navigator.language ) {
			return navigator.language;
		}
		else if ( navigator.browserLanguage ) {
			return navigator.browserLanguage;
		}
		else if ( navigator.systemLanguage ) {
			return navigator.systemLanguage;
		}
		else if ( navigator.userLanguage ) {
			return navigator.userLanguage;
		}
	}
}

function include(filename) {
	var head = document.getElementsByTagName('head')[0];
	
	script = document.createElement('script');
	script.src = filename;
	script.type = 'text/javascript';
	
	head.appendChild(script)
}

function loadMessageCatalog() {
	var lc = getLocale();
	include('../chrome/testmanager/js/' + lc + '.js');
}

/**
 * Adds the specified function, by name or by pointer, to the window.onload() queue.
 * 
 * Usage:
 *
 * addLoadHandler(nameOfSomeFunctionToRunOnPageLoad); 
 *
 * addLoadHandler(function() { 
 *   <more code to run on page load>
 * }); 
 */
function addLoadHandler(func) { 
    var oldonload = window.onload; 
    if (typeof window.onload != 'function') { 
        window.onload = func; 
    } else { 
        window.onload = function() { 
            if (oldonload) { 
                oldonload(); 
            } 
            func(); 
        } 
    } 
}

/**
 * Do some checks as soon as the page is loaded.
 */
addLoadHandler(function() {
        checkFilter(true);
        checkMoveTCDisplays();
        bindTCStatusMenus();
		/* loadMessageCatalog(); */
    });
