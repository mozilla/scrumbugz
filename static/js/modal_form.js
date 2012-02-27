$(function(){
    if($('#modal_form div.error').length){
        $('#modal_form').modal('show');
    }
    $('#modal_form').on('shown', function(){
        $(this).find('input:visible:first').focus();
    });
    $('#id_name').on('keyup', function(){
        $('#id_slug').val($(this).val().replace(/\s+/g,'-').replace(/[^a-zA-Z0-9.\-]/g,'').toLowerCase());
    });
    $('input[id*="date"]').attr('placeholder', 'YYYY-MM-DD');
    $('#id_bz_url').attr('placeholder', 'https://bugzilla.mozilla.org/...');
});
