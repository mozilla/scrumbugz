"use strict";

function set_sprint_points(){
    var points = $('#sprint-bugs tbody tr')
        .map(function(i, el){return $(el).data('points');}).get();

    $('#current-points').html(_.reduce(points, function(sum, cpoints){
        return sum + cpoints;
    }));
}

$(function(){
    $('<div id="tooltip"></div>').appendTo("body");
    $('table').tablesorter({sortList: [[8,0]]});
    $('td.ttip').tooltip();

    $('#sprint-form').on('submit', function(e){
        var bug_ids = $('ul.sprint').sortable('toArray');

        if (bug_ids.length) {
            $('#id_sprint_bugs').val(bug_ids.join(','));
        }
        else {
            e.preventDefault();
            $('#form_error').show();
        }
    });

    set_sprint_points();
});
