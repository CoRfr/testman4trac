/*- coding: utf-8
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

function creaTicket(tcName, planId, planName){ 
	var url = baseLocation+'/newticket?testcaseid='+tcName+'&planid='+planId+'&planname='+planName+'&description=Test%20Case:%20[wiki:'+tcName+'?planid='+planId+'],%20Test%20Plan:%20'+planName+'%20('+planId+')'; 
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

    var nodes=document.getElementById("ticketContainer").getElementsByTagName('input');
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
    
    result = doAjaxCall(url); 
    
    oldIconSpan = document.getElementById("tcStatus"+currStatusColor);
    oldIconSpan.style.border="";
    
    newIconSpan = document.getElementById("tcStatus"+newStatusColor);
    newIconSpan.style.border="2px solid black";
    
    displayNode("tcTitleStatusIcon"+currStatusColor, false);
    displayNode("tcTitleStatusIcon"+newStatusColor, true);
    document.getElementById("tcStatus"+newStatusColor).title = newLabel;

    currStatus = newStatus; 
    currStatusColor = newStatusColor;
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
    result = str.replace(/[;#&\?]/g, '');
    return result;
}

function displayNode(id, show, mode) {
    var msgNode = document.getElementById(id);
    if (msgNode) {
       msgNode.style.display = show ? (mode ? mode : "block") : "none";
    }
}

function doAjaxCall(url) {
    if (window.XMLHttpRequest) {
        /* code for IE7+, Firefox, Chrome, Opera, Safari */
         xmlhttp = new XMLHttpRequest();
    } else {
        /* code for IE6, IE5 */
        xmlhttp = new ActiveXObject("Microsoft.XMLHTTP");
    }
    
    xmlhttp.open("GET", url, false);
    xmlhttp.send("");
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
    
    var url = baseLocation+"/propertyupdate?realm="+realm+"&key="+objKey+"&props="+objProps+"&name="+name+"&value="+value;
    
    result = doAjaxCall(url); 

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
		/* loadMessageCatalog(); */
    });
