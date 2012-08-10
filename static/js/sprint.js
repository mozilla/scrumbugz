(function(){
    "use strict";

    window.Burndown = function(selector, bugs_data) {
        var self = this;
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
        self.ideal_plot = {data: [
            [bugs_data.burndown_axis[0], bugs_data['total_points']],
            [bugs_data.burndown_axis[bugs_data.burndown_axis.length-1], 0]
        ], lines: {fill: false}, points: {show: false}, color: '#0f0', label: 'Ideal'};
        self.bug_plot = {data: bugs_data.bugdown, color: '#db9c04', label: 'Bugs'}
        self.completed_data = [];
        for (var i=0;i < bugs_data.burndown_axis.length; i++){
          var prev = i-1;
          if (prev < 0) {
              prev = 0;
          }
          if (bugs_data.burndown[i] === undefined){
            bugs_data.burndown[i] = 0;
          }
          self.completed_data.push([bugs_data.burndown_axis[i], bugs_data.burndown[prev][1]-bugs_data.burndown[i][1]]);
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
                return parseInt($(this).css('width'))/2;
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
            return item.datapoint[1];
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
                markings.push({ xaxis: { from: i, to: i + 2 * 24 * 60 * 60 * 1000 } });
                i += 7 * 24 * 60 * 60 * 1000;
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
                min: 0,
                tickSize: 2,
                tickFormatter: parseInt
            },
            grid: {
                hoverable: true,
                clickable: true,
                markings: self.weekend_areas
            },
        };

        self.resize();

        $.plot(self.$element, [self.actual_plot, self.ideal_plot, self.completed_plot], self.base_options);

        self.$element.bind({
            plothover: self.plothover,
            resize: self.resize
        });
    }


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
                            if(opts['label'] == item){
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
            }
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
        $('#bugs-table').tablesorter({sortList: [[7,0]]});
        $('td.ttip').tooltip();
    };

    var cur_key = null;
    var $tooltip = null;
    var tooltipvisible = false;
    var showTooltip = function(x, y, contents) {
        $tooltip.css({
            top: y + 10,
            left: x + 10,
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
})(jQuery);
