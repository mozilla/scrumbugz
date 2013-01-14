/*global Spinner:false */
"use strict";

$(function(){
    // focus first field
    $(this).find('input:visible:first').focus();

    // slugify the names
    $('#id_name').on('keyup', function(){
        $('#id_slug').val($(this).val().replace(/\s+/g,'-').replace(/[^a-zA-Z0-9.\-]/g,'').toLowerCase());
    });

    // cool date picker stuffs
    var $date_fields = $(':date');
    if($date_fields.length){
        $date_fields.dateinput({format: 'yyyy-mm-dd', offset:[5, 5]});
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

    // product management
    var $btn_icon = $('#add_product_icon');
    var $add_product_btn = $('#add_product_btn');
    var add_product_spinner = new Spinner({
        lines: 12,
        length: 5,
        width: 1,
        radius: 2
    });
    function start_spin () {
        //$btn_icon.detach();
        add_product_spinner.spin();
        $btn_icon
            .attr('disabled', 'disabled')
            .addClass('icon-blank')
            .removeClass('icon-plus');
        $(add_product_spinner.el).prependTo($add_product_btn).css({
            top: '8px',
            left: '6px'
        });
        $add_product_btn.attr('disabled', 'disabled');
    }
    function stop_spin () {
        add_product_spinner.stop();
        $btn_icon
            .removeClass('icon-blank')
            .addClass('icon-plus');
        $add_product_btn.removeAttr('disabled');
    }
    $('#bzproduct_form').on('submit', function(e){
        e.preventDefault();
        $('.control-group.error').removeClass('error');
        $('.help-block.error').remove();
        start_spin();
        var comp = toComponent($('#id_product').val());
        var post_url = $(this).attr('action');
        var post_data = {
            'name': comp[0],
            'component': comp[1]
        };
        $.post(post_url, post_data)
            .done(function(data, status, jqxhr){
                $('#bzproduct_list').replaceWith(data);
                $('#id_product').val('').focus();
            })
            .fail(function(jqxhr, status, err){
                var errors = $.parseJSON(jqxhr.responseText);
                $('#id_product_wrapper')
                    .append('<p class="help-block error">'+errors.name.join(', ')+'</p>')
                    .closest('.control-group').addClass('error');
            })
            .always(stop_spin);
    });
    $('#bzproducts_list_wrapper').on('click', '.bzproduct-remove', function(e){
        e.preventDefault();
        var post_url = $(this).attr('href');
        $.post(post_url)
            .done(function(data, status, jqxhr){
                $('#bzproducts_list_wrapper').load($('#bzproducts_list_wrapper').data('url'));
            });
    });

    var toComponent = function(name) {
        var slash = name.indexOf("/");
        return [name.slice(0, slash), name.slice(slash + 1)];
    };
});
