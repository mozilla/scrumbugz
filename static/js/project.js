/*global $tooltip:true */
$(function(){
    "use strict";
    window.$tooltip = $('<div id="tooltip"></div>').appendTo("body");
    $('#bugs_table').stupidtable();
    $('#backlog_table').stupidtable();
    $('td.ttip').tooltip();
});
