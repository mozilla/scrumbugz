
$(function(){
    "use strict";
    $('ul.storylist').sortable({
        connectWith: 'ul.storylist',
        opacity: 0.7,
        revert: 200,
        placeholder: 'alert alert-info',
        forcePlaceholderSize: true
    }).disableSelection();
    $('#sprint-form').on('submit', function(e){
        var bug_ids = $('.sprint li')
            .map(function(i, el){return $(el).data('id')})
            .toArray();
        if (bug_ids.length) {
            $('#id_sprint_bugs').val(bug_ids.join(','));
        }
        else {
            e.preventDefault();
            $('#form_error').removeClass('hidden');
        }
    });
});
