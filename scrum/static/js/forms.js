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
    var $start_date = $('#id_start_date');
    var $end_date = $('#id_end_date');
    if ($start_date.length) {
        var start_picker = $start_date.datepicker({
            format: 'yyyy-mm-dd'
        }).data('datepicker');
        var end_picker = $end_date.datepicker({
            format: 'yyyy-mm-dd',
            onRender: function(date){
                // disable dates before start_date.
                return date.valueOf() <= start_picker.date.valueOf() ? 'disabled' : '';
            }
        }).data('datepicker');
        $start_date.on('changeDate', function(e){
            if (e.date.valueOf() > end_picker.date.valueOf()) {
                var endDate = new Date(e.date);
                // set the end date 2 weeks out by default.
                endDate.setDate(endDate.getDate() + 14);
                end_picker.setValue(endDate);
            }
            start_picker.hide();
            $end_date.focus();
        });
        $end_date.on('changeDate', function(e){
            end_picker.hide();
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
