(function($){
    "use strict";
    $(function(){
        $('.show-tooltip').tooltip();
        $('#shift-refresh').on('click', function(e){
            e.preventDefault();
            window.location.reload(true);
        });
        var $bug_id_search = $('#bug_id_search');
        var $bug_id_search_btn = $('#bug_id_search_btn');
        $bug_id_search_btn.on('click', function(e){
            e.preventDefault();
            var bugID = $bug_id_search.val();
            window.location.href = '/b/' + bugID + '/';
        });
        $('#bug_id_search_modal').on('shown', function(){
            $bug_id_search.focus();
        });
        $bug_id_search.on('keyup', function(e){
            if (e.which === 13) {
                e.preventDefault();
                $bug_id_search_btn.trigger('click');
            }
        });
    });
})(jQuery);
