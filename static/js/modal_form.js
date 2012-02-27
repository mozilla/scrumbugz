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
    $('#id_bz_url').attr('placeholder', 'https://bugzilla.mozilla.org/...');
    $(':date').dateinput({
        format: 'yyyy-mm-dd'
    });
    $('#id_start_date').data('dateinput').change(function(){
        $('#id_end_date').data('dateinput').setMin(this.getValue(), true)
                                           .setValue(new Date(this.getValue().getTime() + 1000 * 60 * 60 * 24 * 7))
    });
    $('#id_end_date').data('dateinput').onBeforeShow(function(){
        this.setMin($('#id_start_date').data('dateinput').getValue());
    });
});
