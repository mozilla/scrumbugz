(function(){
    "use strict";

    window.Burndown = function(selector, bugs_data) {
        var self = this;
        var DAY = 24 * 60 * 60 * 1000;
        self.$element = $(selector);
        self.$element.data('flot', self);
        self.ticks = bugs_data.burndown_axis;
        self.tip_cache = {};
        self.actual_plot = {
            data: bugs_data.burndown,
            color: '#049cdb',
            label: 'Actual',
            lines: { show: true, fill: 0.4},
            points: {show: true, fill: true, radius: 4}
        };

        self.bug_plot = {data: bugs_data.bugdown, color: '#db9c04', label: 'Bugs'};
        self.completed_data = [];
        for (var i = 0; i < bugs_data.burndown_axis.length; i++) {
            var prev = i - 1;
            if (prev < 0) {
                prev = 0;
            }
            if (bugs_data.burndown[i] === undefined) {
                bugs_data.burndown[i] = 0;
            }
            self.completed_data.push([bugs_data.burndown_axis[i], bugs_data.burndown[prev][1] - bugs_data.burndown[i][1]]);
        }
        self.completed_plot = {
            data: self.completed_data,
            color: '#db9c04',
            label: 'Completed',
            bars: {show: true},
            points: {show: true, fill: true, radius: 4}
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
            var points = Math.round(item.datapoint[1]);
            var units = (points === 1) ? ' point' : ' points';
            return points + units;
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
            d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 2) % 7));
            d.setUTCSeconds(0);
            d.setUTCMinutes(0);
            var i = d.getTime();
            do {
                // when we don't set yaxis, the rectangle automatically
                // extends to infinity upwards and downwards
                markings.push({
                    xaxis: {
                        from: i,
                        to: i + 2 * DAY
                    }
                });
                i += 7 * DAY;
            } while (i < axes.xaxis.max);

            return markings;
        };

        // Get an ideal burn line that takes into account weekends.
        function ideal_burn_data() {
            function is_weekday(date) {
                var day_of_week = date.getUTCDay();
                return day_of_week !== 0 && day_of_week !== 6;
            }

            var burn_start = new Date(bugs_data.burndown_axis[0]);
            var burn_end = new Date(bugs_data.burndown_axis[bugs_data.burndown_axis.length - 1]);

            var adj_start = burn_start;
            var adj_end = burn_end;

            // Make start and end dates weekdays.
            while (!is_weekday(burn_start)) {
                burn_start.setDate(burn_start.getDate() + 1);
            }
            while (!is_weekday(burn_end)) {
                burn_end.setDate(burn_end.getDate() - 1);
            }
            // count number of weekdays.
            var weekend_days = Math.floor((adj_end - adj_start) / DAY / 7 * 2);
            var days = (burn_end - burn_start) / DAY - weekend_days;
            var burnrate = bugs_data.total_points / days;

            // From this, calculate the burn rate per weekday, then iterate
            // through the days, setting points that drop appropriately.
            var ideal_data = [[bugs_data.burndown_axis[0], bugs_data.total_points]];
            var last_value = bugs_data.total_points;
            var timestamp = bugs_data.burndown_axis[0];

            while(timestamp <= bugs_data.burndown_axis[bugs_data.burndown_axis.length - 1]) {
                timestamp += DAY;
                if (is_weekday(new Date(timestamp))) {
                    last_value -= burnrate;
                }
                ideal_data.push([timestamp, last_value]);
            }
            return ideal_data;
        }

        self.ideal_plot = {
            data: ideal_burn_data(),
            lines: {fill: false},
            points: {show: false},
            color: '#0f0',
            label: 'Ideal'
        };

        self.base_options = {
            xaxis: {
                mode: 'time',
                ticks: self.ticks,
                min: self.ticks[0],
                max: self.ticks[self.ticks.length-1]
            },
            yaxis: {
                min: 0,
                tickSize: 2,
                tickFormatter: parseInt
            },
            grid: {
                hoverable: true,
                clickable: true,
                markings: self.weekend_areas
            }
        };

        self.resize();

        $.plot(self.$element, [self.actual_plot, self.ideal_plot, self.completed_plot], self.base_options);

        self.$element.bind({
            plothover: self.plothover,
            resize: self.resize
        });
    };

    window.PieFlot = function(selector, data, extra) {
        var self = this;
        self.$element = $(selector);
        self.data = data;
        self.extra = extra;
        self.tip_cache = {};

        self.$element.data('flot', self);

        self.resize = function(){
            self.$element.css('height', function(){
                return $(this).css('width');
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

        self.get_data = function(){
            if(self.extra){
                $.each(self.extra, function(key, values){
                    $.each(values, function(item, value){
                        $.each(data, function(i, opts){
                            if(opts.label === item){
                                opts[key] = value;
                                return false;
                            }
                        });
                    });
                });
            }
            return self.data;
        };

        self.get_tip_key = function(item){
            return item.series.label;
        };

        self.get_tip_msg = function(item){
            var key = self.get_tip_key(item);
            if(!(key in self.tip_cache)){
                var itemprops = self.getItemProps(item);
                var msg = ['<strong>'+itemprops.label+'</strong>'];
                msg.push(itemprops.rawnum + ' (' + itemprops.percent + '%)');
                self.tip_cache[key] = msg.join('<br>');
            }
            return {'key':key, 'msg':self.tip_cache[key]};
        };

        self.getItemProps = function(item){
            return {
                label: item.series.label,
                percent: Math.round(item.series.percent * 100)/100,
                rawnum: item.series.datapoints.points[1]
            };
        };

        self.resize();

        $.plot(self.$element, self.get_data(), {
            series: {
                pie: {
                    //innerRadius: 0.5,
                    radius: 0.85,
                    show: true,
                    label: {
                        show: false
                    }
                }
            },
            grid: {
                hoverable: true,
                clickable: true
            },
            legend: {
                show: true
            }
        });

        self.$element.bind({
            plothover: self.plothover,
            resize: self.resize
        });
    };

    window.init_sprint = function(){
        $tooltip = $('<div id="tooltip"></div>').appendTo("body");
        $('#bugs_table').stupidtable();
        $('#backlog_table').stupidtable();
        $('#old_sprint_table').stupidtable();
        $('.ttip').tooltip();
    };

    var cur_key = null;
    var $tooltip = null;
    var tooltipvisible = false;
    var showTooltip = function(x, y, contents) {
        $tooltip.css({
            top: y + 10,
            left: x + 10
        });
        if(contents.key !== cur_key){
            cur_key = contents.key;
            $tooltip.html(contents.msg);
        }
        if(!tooltipvisible){
            tooltipvisible = true;
            $tooltip.stop(true, true).fadeIn(200);
        }
    };

    var hideTooltip = function(){
        if(tooltipvisible){
            tooltipvisible = false;
            $('#tooltip').stop(true, true).fadeOut(200);
        }
    };

    $(function(){
        /* Show hide stats area, must use negative position due to flot rendering */
        $('.stats-toggle button').on('click', function(){
            if(!$(this).hasClass('active')){
                var action = $(this).is('.stats-on') ? 'removeClass' : 'addClass';
                $('.stats-container')[action]('offscreen-hide');
                $.cookie('show_pretty_graphs',
                         action === 'addClass' ? 'false' : 'true',
                         {expires: 90});
            }
        });

        var show_graphs = $.cookie('show_pretty_graphs');
        if(show_graphs !== null){
            $(show_graphs === 'false' ? '.stats-off' : '.stats-on').click();
        }

    });

})(jQuery);
