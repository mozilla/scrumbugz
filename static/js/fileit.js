"use strict";
// via https://github.com/harthur/fileit

$(document).ready(function () {
    var bugzilla = bz.createClient();

    var cachedConfig = localStorage["fileit-config"];
    if (cachedConfig) {
        populateAutocomplete(JSON.parse(cachedConfig));
    }

    bugzilla.getConfiguration({
            flags:0,
            cached_ok:1
        },
        function (err, config) {
            if (err) {
                throw "Error getting Bugzilla configuration: " + err;
            }
            if (config) {
                localStorage["fileit-config"] = JSON.stringify(config);
                if (!cachedConfig) {
                    populateAutocomplete(config);
                }
            }
        }
    );
});


function populateAutocomplete(config) {
    var components = [];
    var product;
    var component;
    for (product in config.product) {
        var comps = config.product[product].component;
        comps.__ALL__ = 1;
        for (component in comps) {
            components.push({
                product:product,
                component:component,
                string:componentName({product:product, component:component})
            });
        }
    }

    var input = $("#id_product");
    input.autocomplete({
        list:components,
        minCharacters:2,
        timeout:200,
        threshold:200,
        adjustWidth:360,
        template:function (item) {
            return "<li value='" + item.string + "'><span class='product'>"
                + item.product + "</span>" + "<span class='component'>"
                + item.component + "</span></li>";
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

function toComponent(name) {
    var slash = name.indexOf("/");
    return [name.slice(0, slash), name.slice(slash + 1)];
}
