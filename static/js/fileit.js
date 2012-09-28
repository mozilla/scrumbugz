(function($){

    "use strict";
    // based on https://github.com/harthur/fileit

    var product_ls_name = 'scrumbugs-products-config';

    $(function () {

        var cachedConfig = localStorage[product_ls_name];
        if (cachedConfig) {
            populateAutocomplete(JSON.parse(cachedConfig));
        }

        $.get('/bugzilla/products/').done(
            function (config, status, jqXHR) {
                if (config) {
                    localStorage[product_ls_name] = JSON.stringify(config);
                    if (!cachedConfig) {
                        populateAutocomplete(config);
                    }
                }
            }
        );
    });


    function populateAutocomplete(config) {
        var components = [];
        _(config).forIn(function(comps, product){
            comps.unshift('__ALL__');
            _(comps).forEach(function(component){
                components.push({
                    product: product,
                    component: component,
                    string: componentName({
                        product: product,
                        component: component
                    })
                });
            });
        });

        $("#id_product").autocomplete({
            list:components,
            minCharacters:2,
            timeout:200,
            threshold:200,
            adjustWidth:360,
            template:function (item) {
                return [
                    '<li value="',
                    item.string,
                    '"><span class="product">',
                    item.product,
                    '</span><span class="component">',
                    item.component,
                    '</span></li>'
                ].join('');
            },
            matcher:function (typed) {
                return typed;
            },
            match:function (item, matcher) {
                var words = matcher.split(/\s+/);
                return _(words).all(function (word) {
                    return item.string.toLowerCase().indexOf(word.toLowerCase()) >= 0;
                });
            },
            insertText:function (item) {
                return item.string;
            }
        });
    }

    function componentName(comp) {
        return comp.product + "/" + comp.component;
    }

    window.toComponent = function(name) {
        var slash = name.indexOf("/");
        return [name.slice(0, slash), name.slice(slash + 1)];
    };

})(jQuery);
