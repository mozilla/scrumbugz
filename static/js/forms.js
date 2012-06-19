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
    }
});
