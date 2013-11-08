(function($){
    "use strict";

    window.numberWithCommas = function(x) {
        return parseInt(x, 10).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    };

    window.StatsChart = function(selector, stats_data, ticks) {
        var DAY = 24 * 60 * 60 * 1000;
        var self = this;
        self.$element = $(selector);
        self.$element.data('flot', self);
        self.tip_cache = {};
        self.ticks = ticks;
        self.data = stats_data;
        self.get_plot = function(){
            return {
                data: self.filter_data(),
                lines: {show: true},
                points: {show: true, fill: true, radius: 4}
            };
        };

        self.filter_data = function(){
            // filter leading 0 values
            var non_0 = false;
            return _.filter(self.data, function(x){
                if (non_0) return true;
                if (x[1]) non_0 = true;
                return non_0;
            });
        };

        self.resize = function(){
            self.$element.css('height', function(){
                return parseInt($(this).css('width'), 10)/2;
            });
        };

        self.plothover = function(e, pos, item){
            if(item){
                showTooltip(pos.pageX, pos.pageY, self.get_tip_msg(item));
            }
            else{
                hideTooltip();
            }
        };

        self.get_tip_key = function(item){
            return window.numberWithCommas(item.datapoint[1]);
        };

        self.get_tip_msg = function(item){
            var key = self.get_tip_key(item);
            if(!(key in self.tip_cache)){
                self.tip_cache[key] = '<strong>'+key+'</strong>';
            }
            return {'key':key, 'msg':self.tip_cache[key]};
        };

        // helper for returning the weekends in a period
        // copied from flot visitors example
        self.weekend_areas = function(axes) {
            var markings = [];
            var d = new Date(axes.xaxis.min);
            // go to the first Saturday
            d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 1) % 7));
            d.setUTCSeconds(0);
            d.setUTCMinutes(0);
            // This make the markings line up with the grid.
            // Could this be time zone related?
            d.setUTCHours(-1);
            var i = d.getTime();
            do {
                // when we don't set yaxis, the rectangle automatically
                // extends to infinity upwards and downwards
                markings.push({ xaxis: { from: i, to: i + 2 * DAY } });
                i += 7 * DAY;
            } while (i < axes.xaxis.max);

            return markings;
        };

        self.base_options = {
            xaxis: {
                mode: 'time',
                ticks: self.ticks,
                min: self.ticks[0],
                max: self.ticks[self.ticks.length-1]
            },
            yaxis: {
                tickFormatter: window.numberWithCommas,
                minTickSize: 1
            },
            grid: {
                hoverable: true,
                clickable: true,
                markings: self.weekend_areas
            }
        };

        self.resize();

        $.plot(self.$element, [self.get_plot()], self.base_options);

        self.$element.bind({
            plothover: self.plothover,
            resize: self.resize
        });
    };

    var cur_key = null;
    var tooltipvisible = false;
    var showTooltip = function(x, y, contents) {
        $('#tooltip').css({
            top: y + 10,
            left: x + 10
        });
        if(contents.key !== cur_key){
            cur_key = contents.key;
            $('#tooltip').html(contents.msg);
        }
        if(!tooltipvisible){
            tooltipvisible = true;
            $('#tooltip').stop(true, true).fadeIn(200);
        }
    };

    var hideTooltip = function(){
        if(tooltipvisible){
            tooltipvisible = false;
            $('#tooltip').stop(true, true).fadeOut(200);
        }
    };

    $('<div id="tooltip"></div>').appendTo("body");

})(jQuery);
