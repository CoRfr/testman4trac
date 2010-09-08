/*- coding: utf-8
 *
 * Copyright (C) 2010 Roberto Longopbardi - seccanj@gmail.com, Marco Cipriani
 */

/******************************************************/
/**         Test case, catalog, plan creation         */
/******************************************************/

function creaTestCatalog(path) {
	var tcInput = document.getElementById("catName");
	var catalogName = tcInput.value;
    
    if (catalogName == null || catalogName.length == 0) {
		document.getElementById('catErrorMsgSpan').innerHTML = messages['name_help'];
    } else {
    	var catName = stripLessSpecialChars(catalogName);
    	
    	if (catName.length > 90 || catName.length < 4) {
    		document.getElementById('catErrorMsgSpan').innerHTML = messages['length_error'];
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
		document.getElementById('errorMsgSpan').innerHTML = messages['name_help'];
    } else {
    	var tcName = stripLessSpecialChars(testCaseName); 
    	
    	if (tcName.length > 90 || tcName.length < 4) {
    		document.getElementById('errorMsgSpan').innerHTML = messages['length_error'];
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
		document.getElementById('errorMsgSpan2').innerHTML = messages['name_help'];
    } else {
    	var tplanName = stripLessSpecialChars(testPlanName); 
    	
    	if (tplanName.length > 90 || tplanName.length < 4) {
    		document.getElementById('errorMsgSpan2').innerHTML = messages['length_error'];
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
	var url = baseLocation+'/newticket?testCaseNumber='+tcName+'&planId='+planId+'&planName='+planName+'&description=Test%20Case:%20[wiki:'+tcName+'?planid='+planId+'],%20Test%20Plan:%20'+planName+'%20('+planId+')'; 
	window.location = url;
}

/******************************************************/
/**         Move test case into another catalog       */
/******************************************************/

function checkMoveTCDisplays() {
    displayNode('copiedTCMessage', isPasteEnabled());
    displayNode('pasteTCHereMessage', isPasteEnabled());
    displayNode('pasteTCHereDiv', isPasteEnabled());
}

function isPasteEnabled() {
    if (getCookie('TestManager_TestCase')) {
        return true;
    }
    
    return false;
}

function copyTestCaseToClipboard(tcId) {
    setCookie('TestManager_TestCase', tcId, 1, '/', '', '');
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

function cancelTCMove() {
    deleteCookie('TestManager_TestCase', '/', '');
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

function highlight(string) {
    clearSelection();
    if (string && string !== "") {
        var res=[];
        var tks=string.split(" ");
        for (var i=0;i<tks.length;i++) {
            res[res.length]=new RegExp(regexpescape(tks[i].toLowerCase()), "g");
        }
        var nodes=document.getElementById("ticketContainer").getElementsByTagName("a");
        for(var i=0;i<nodes.length;i++) {
            var n=nodes.item(i);
            if (filterMatch(n, n.nextSibling, res)) {
                select(n);
            }else{
                deselect(n);
            }
        }

        document.getElementById('searchResultsNumberId').innerHTML = labels['results']+searchResults;
    }
}

function regexpescape(text) {
    return text.replace(/[-[\]{}()+?.,\\\\^$|#\s]/g, "\\\\$&").replace(/\*/g,".*");
}

function filterMatch(node1,node2,res) {
    var name=(node1.innerHTML + node2.innerHTML).toLowerCase();
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

function starthighlight(string,now) {
    if (htimer) {
        clearTimeout(htimer);
    } 
    if (now) {
        highlight(string);
    } else {
        htimer = setTimeout(function() {
                                highlight(string);
                            },500);
    }
}

function checkFilter(now) {
    var f=document.getElementById("tcFilter");
    if (f) {
        starthighlight(f.value,now);
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
/**        Test case in plan status management        */
/******************************************************/

function changestate(tc, planid, path, newStatus) {

    var url = baseLocation+"/teststatusupdate?id="+tc+"&planid="+planid+"&status="+newStatus+"&path="+path;
    
    xmlDoc = doAjaxCall(url); 
    
    oldIconSpan = document.getElementById("tcStatus"+currStatus);
    oldIconSpan.style.border="";
    
    newIconSpan = document.getElementById("tcStatus"+newStatus);
    newIconSpan.style.border="2px solid black";
    
    document.getElementById("tcTitleStatusIcon"+currStatus).style.display="none";
    document.getElementById("tcTitleStatusIcon"+newStatus).style.display="block";
    
    currStatus = newStatus; 
}

/******************************************************/
/**                  Utility functions                */
/******************************************************/

function expandCollapseSection(nodeId) {
    toggleClass(nodeId, "collapsed");
}

function stripSpecialChars(str) {
    result = str.replace(/[ ',;:àèéìòù£§<>!"%&=@#��\[\]\-\\\\^\$\.\|\?\*\+\(\)\{\}]/g, '');
    return result;
}

function stripLessSpecialChars(str) {
    result = str.replace(/[;#&\?]/g, '');
    return result;
}

function displayNode(id, show) {
    var msgNode = document.getElementById(id);
    if (msgNode) {
        msgNode.style.display = show ? "block" : "none";
    }
}

function toggleClass(nodeId, className) {
    var node = document.getElementById(nodeId);
    if (node.className === "") {
        node.className = className;
    } else {
        node.className = "";
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
    });
