$(function(){
    "use strict";

    $('<div id="tooltip"></div>').appendTo("body");
    $('table').tablesorter({sortList: [[8,0]]});
    $('td.ttip').tooltip();

    function set_sprint_points(){
        var points = $('#bugs_table tbody tr')
              .map(function(i, el){return $(el).data('points');}).get();

        if (points.length === 0) {
            points = [0];
        }

        $('#current-points').html(_.reduce(points, function(sum, cpoints){
            return sum + cpoints;
        }));
    }

    function refresh_actions(){
        $('.act-toggle-sprint').unbind('click');

        $('#bugs_table .act-toggle-sprint').each(function(){
            $(this).attr('title', 'Remove from sprint.');
            $(this).click(function(){
                append_bug(this, '#backlog_table');
            });
        });

        $('#backlog_table .act-toggle-sprint').each(function(){
            $(this).attr('title', 'Add to sprint.');
            $(this).click(function(){
                append_bug(this, '#bugs_table');
            });
        });
    }

    function append_bug(button, table) {
        $(table).find('tbody').append($(button).parents('tr').first());
        set_sprint_points();
        refresh_actions();
    }

    $('#sprint-form').on('submit', function(e){
        var bug_ids = $('#bugs_table tbody tr')
              .map(function(i, el){return $(el).data('bugid');}).get();

        if (bug_ids.length) {
            $('#id_sprint_bugs').val(bug_ids.join(','));
        }
        else {
            e.preventDefault();
            $('#form_error').show();
        }
    });

    set_sprint_points();
    refresh_actions();
});
