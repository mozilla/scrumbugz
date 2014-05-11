$(function(){
    "use strict";

    var bug_actions = {'add': [], 'remove': []};
    var original_bugs = $('#bugs_table tbody tr')
        .map(function(i, el){return $(el).data('bugid');}).get();

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
        var table_type = $(this).attr('id').split('_')[0] == 'bugs' ? 'bugs' : 'backlog';
        $('.act-toggle-sprint', this).each(function(){
            $(this).prop('title', button_props[table_type].title);
        });
    }).on('click', '.act-toggle-sprint', function(){
        var $button = $(this);
        var $bug = $button.closest('tr');
        var $table = $bug.closest('table');
        var bugid = $bug.data('bugid');
        var new_table_type = $table.is('#bugs_table') ? 'backlog' : 'bugs';
        var action = new_table_type === 'bugs' ? 'add' : 'remove';
        var other_action = action === 'add' ? 'remove' : 'add';
        var $original_table = $bug.data('originalTable');
        if(action === 'add' && !$original_table){
            $bug.data('originalTable', $table);
        }
        var $new_table;
        if(action === 'remove' && $original_table){
            $new_table = $original_table;
        }
        else{
            $new_table = $('#'+new_table_type+'_table');
        }
        /* bugs not originally on the sprint shouldn't be removed, and
         * bugs originally on the sprint shouldn't be added. */
        if(!(action === 'remove' && !_.contains(original_bugs, bugid)) &&
           !(action === 'add' && _.contains(original_bugs, bugid))){
            bug_actions[action].push(bugid);
        }
        /* remove the bug from the opposite action if it's there */
        bug_actions[other_action] = _.filter(bug_actions[other_action], function(bid){
            return bid !== bugid;
        });
        $button.attr('title', button_props[new_table_type].title);
        $button.removeClass(button_colors)
               .addClass(button_props[new_table_type].color);
        $new_table.find('tbody').append($bug);
        if($new_table.is('.empty')){
            $new_table.removeClass('empty').find('.empty_message').remove();
        }
        set_sprint_points();
    });

    $('#sprint-form').on('submit', function(e){
        var do_submit = false;
        _.forIn(bug_actions, function(bugids, action){
            if(bugids.length){
                do_submit = true;
                $('#id_' + action + '_bugs').val(bugids.join(','));
                bugids.length = 0;
            }
        });
        if(!do_submit){
            e.preventDefault();
            $('#form_error').show();
        }
    });
    $('a.close').on('click', function(){$(this).parent().hide();});
    $(window).on('beforeunload', function(e){
        var ask_user = false;
        _.forIn(bug_actions, function(bugids){
            if(bugids.length){
                ask_user = true;
            }
        });
        if(ask_user){
            return 'You have moved bugs but not saved!';
        }
    });

    set_sprint_points();
});
