$(function(){
    "use strict";

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

    var button_props = {
        bugs: {
            title: 'Remove from sprint',
            color: 'btn-danger'
        },
        backlog: {
            title: 'Add to sprint',
            color: 'btn-success'
        }
    };

    var button_colors = 'btn-danger btn-success';

    $('.bug-list').each(function(){
        var table_type = $(this).attr('id').split('_')[0];
        $('.act-toggle-sprint', this).each(function(){
            $(this).prop('title', button_props[table_type].title);
        });
    }).on('click', '.act-toggle-sprint', function(){
        var $button = $(this);
        var $table = $button.closest('table');
        var new_table_type = $table.is('#bugs_table') ? 'backlog' : 'bugs';
        var $new_table = $('#'+new_table_type+'_table');
        $button.attr('title', button_props[new_table_type].title);
        $button.removeClass(button_colors)
               .addClass(button_props[new_table_type].color);
        $new_table.find('tbody').append($button.closest('tr'));
        if($new_table.is('.empty')){
            $new_table.removeClass('empty').find('.empty_message').remove();
        }
        set_sprint_points();
    });

    $('#sprint-form').on('submit', function(e){
        var bug_ids = $('#bugs_table tbody tr')
              .map(function(i, el){return $(el).data('bugid');}).get();

        if (bug_ids.length) {
            $('#id_new_bugs').val(bug_ids.join(','));
        }
        else {
            e.preventDefault();
            $('#form_error').show();
        }
    });
    $('a.close').on('click', function(){$(this).parent().hide();});

    set_sprint_points();
});
