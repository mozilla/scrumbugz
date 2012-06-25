$(function(){
    // focus first field
    $(this).find('input:visible:first').focus();

    // slugify the names
    $('#id_name').on('keyup', function(){
        $('#id_slug').val($(this).val().replace(/\s+/g,'-').replace(/[^a-zA-Z0-9.\-]/g,'').toLowerCase());
    });

    // cool date picker stuffs
    if($('#id_start_date').length){
        $(':date').dateinput({
            format: 'yyyy-mm-dd'
        });
        $('#id_start_date').data('dateinput').change(function(){
            $('#id_end_date').data('dateinput')
                // make the min date for end be after start
                .setMin(this.getValue(), true)
                // set the end date to two weeks from start
                .setValue(new Date(this.getValue().getTime() + 1000 * 60 * 60 * 24 * 7 * 2));
        });
        $('#id_end_date').data('dateinput').onBeforeShow(function(){
            this.setMin($('#id_start_date').data('dateinput').getValue());
        });
    };

    // url management
    $('#bzurl_form').on('submit', function(e){
        e.preventDefault();
        $('.control-group.error').removeClass('error');
        $('.help-block').remove();
        var post_url = $(this).attr('action');
        var post_data = {'url': $('#id_url').val()};
        $.post(post_url, post_data)
            .done(function(data, status, jqxhr){
                $('#bzurl_list').replaceWith(data);
                $('#id_url').val('').focus();
            })
            .fail(function(jqxhr, status, err){
                var errors = $.parseJSON(jqxhr.responseText);
                $('#id_url_wrapper')
                    .append('<p class="help-block"></p>')
                    .html(errors.url)
                    .closest('.control-group').addClass('error');
            });
    });
    $('#bzurl_list_wrapper').on('click', '.bzurl-remove', function(e){
        e.preventDefault();
        var post_url = $(this).attr('href');
        $.post(post_url)
            .done(function(data, status, jqxhr){
                $('#bzurl_list_wrapper').load($('#bzurl_list_wrapper').data('url'));
            });
    });
});

// Django recommended CSRF code
// https://docs.djangoproject.com/en/1.4/ref/contrib/csrf/
jQuery(document).ajaxSend(function(event, xhr, settings) {
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    function sameOrigin(url) {
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }
    function safeMethod(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
    }
});
