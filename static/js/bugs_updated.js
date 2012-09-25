(function($){
    "use strict";

    var bugsUpdatedRecently = function(){
        var bug_ids = $('.bug-list tbody tr').map(function(i, el){return $(el).data('bugid');}).get();
        if(bug_ids.length){
            bug_ids = bug_ids.join(',');
            $.ajax({
                url: '/bugs_updated/',
                type: 'POST',
                data: {'bug_ids': bug_ids},
                statusCode: {
                    404: function(){
                        window.setTimeout(bugsUpdatedRecently, 25000);
                    },
                    204: function(){
                        $('#alert_messages').append([
                            '<div class="alert alert-info hide">',
                            '<a class="close" data-dismiss="alert">&times;</a>',
                            '<strong>Bugs on this page have been updated.</strong> Refresh to see.',
                            '</div>'
                        ].join('')).find('.alert').slideDown();
                    }
                }
            });
        }
    };

    $(function(){
        // Check for bug updates.
        window.setTimeout(bugsUpdatedRecently, 35000);
    });

})(jQuery);
