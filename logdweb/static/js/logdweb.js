/* logdweb library */

var viewSettings = {
  autoScroll: true,
  update: true,
  refreshCharts: true,
  timeStep: "-1hours"
};

/* given two strings like -1hours or -1week (in the same units), return the
 * result of adding them together.
 */
function addFuzzyTime(t1, t2) {
  if (typeof(t2) == "undefined") {
    return t1;
  }
  var t1int = parseInt(t1);
  var t2int = parseInt(t2);
  var units = t1.replace(t1int, "");

  return (t1int + t2int).toString() + units;
}

/* given two strings like -1hours or -1week, subtract t2 from t1 */
function subFuzzyTime(t1, t2) {
  if (typeof(t2) == "undefined") {
    return t1;
  }
  var t1int = parseInt(t1);
  var t2int = parseInt(t2);
  var units = t1.replace(t1int, "");

  return (t1int - t2int).toString() + units;
}

(function($) {
  /* update a log, run on a table dom element */
  $.fn.updateLog = function(opts) {
    var $this = $(this);
    var config = $.extend({callback: function() {}}, opts);
    var path = $this.attr('id');
    if (!path) {
      return;
    }
    var last_id = $(this).find('tr:last td.id').html();
    //console.log("Updating path " + path + " with last id " + last_id);
    var url = logd_base_url + path + '/new/?id=' + last_id;
    var $div = $this.closest('div.log-container');
    
    if (viewSettings.update) {
      $.ajax({
        url: url,
        dataType: 'json',
        success: function(data) {
          for (var i=0; i<data.length; i++) {
            var line = data[i];
            $('table.log').append(line.rendered);
          }
          if (viewSettings.autoScroll) {
            $div.scrollTop($div[0].scrollHeight);
            $this.truncateLog(250);
          } else {
            // there is a maximum number of rows where the page gets unusable
            $this.truncateLog(2000);
          }
        },
        complete: function() {
          config.callback();
        }
      });
    } else {
      config.callback();
    }
    return this;
  };

  /* truncate a log to a number of lines */
  $.fn.truncateLog = function(lines) {
    var $this = $(this);
    rows = $this.find('tr').length;
    if (rows > lines) {
      /* chop the first rows - lines tr's */
      var num = rows - lines;
      console.log(rows + "lines but max is " + lines + "; pruning " + num + " rows");
      $this.find('tr:lt(' + num + ')').remove();
    }
    return this;
  }

  $.fn.updateChart = function() {
    $.each(this, function() {
      var src = this.src.replace(/&_flub=\d+/, '');
      this.src = src + '&_flub=' + new Date().getTime();
    });
    return this;
  };

  /* alter a chart.  send it a mapping of new parameters for the url
   * and it will alter the charts parameters and reload it.
   */
  $.fn.alterChart = function(opts) {
    $.each(this, function() {
      var src = this.src;
      for (var key in opts) {
        var val = opts[key];
        var re = new RegExp(key + "=[^&]+");
        if ( src.match(re) ) {
          if (val != false) {
            src = src.replace(new RegExp(key + "=[^&]+"), key + '=' + opts[key]);
          } else {
            /* if val is false, remove it */
            src = src.replace(new RegExp(key + "=[^&]+"), "");
          }
        } else {
          src += '&' + key + '=' + opts[key];
        }
      }
      this.src = src
    });
    return this;
  };

  /* return an object representing the current chart options */
  $.fn.chartOptions = function() {
    var opts = {};
    var re = new RegExp("\s=[^&]+");
    var src = this[0].src;
    var qs = src.slice(src.indexOf('?')+1);
    var keyvals = qs.match(/(\w+=[^&]+)+/g);
    $.each(qs.match(/(\w+=[^&]+)+/g), function() {
      var keyvals = this.match(/([^=]+)=(.+)/);
      var key = keyvals[1], val=keyvals[2];
      if (key in opts && typeof(opts[key]) != "object") {
        opts[key] = [opts[key]];
      }
      if (key in opts) {
        opts[key][opts[key].length] = val;
      } else {
        opts[key] = val;
      }
    });
    return opts;
  };

  /* update the log once per second */
  var updater = function() {
    setTimeout(function() {
      $('table.log').updateLog({callback: updater});
    }, 2000);
  };
  updater();

  setInterval(function() {
    if (viewSettings.refreshCharts) {
      $('div.chart img').updateChart();
    }
  }, 10000);

  /* set up event handlers on load */
  $(function() {
    $('table.log').updateLog();

    /* disable autoscroll unless container is scrolled to the bottom */
    $('div.log-container').scroll(function(e) {
      var $this = $(this);
      var $inner = $this.find('table.log');
      /* add a fudge factor here */
      if ( Math.abs($inner.offset().top) + $this.height() + $this.offset().top + 15
            >= $inner.outerHeight()) {
        viewSettings.autoScroll = true;
      } else {
        viewSettings.autoScroll = false;
      }
    });

    $('.timers a').click(function(e) {
      e.preventDefault();
      var $this = $(this);
      var opts = eval('('+$this.attr('change')+')');
      viewSettings.timeStep = opts.from;
      $('div.chart img').alterChart(opts);
      $('.timers a').removeClass('on');
      $this.addClass('on');
      return false;
    });

    $('#auto_refresh').click(function(e) {
      e.preventDefault();
      var $this = $(this);
      viewSettings.refreshCharts = !$this.hasClass("on");
      if (!viewSettings.refreshCharts) {
        $this.removeClass("on").addClass("off");
      } else {
        $this.removeClass("off").addClass("on");
      }
    });

    $('#contrast_mode').click(function(e) {
      e.preventDefault();
      var $this = $(this);
      var on = $this.hasClass("on")
      if (on) {
        $this.html('&#x25a0;').removeClass("on");
        $('div.chart img').alterChart({template: 'default'});
      } else {
        $this.html('&#x25a1;').addClass("on");
        $('div.chart img').alterChart({template: 'plain'});
      }
    });
  
    $('.modal .cancel').click(function(e) {
      e.preventDefault();
      var modal = $(this).parents('.modal');
      $(modal).modal('hide');
    });

    $('.left.overlay a').click(function(e) {
      e.preventDefault();
      var $chart = $(this).parents(".chart-container").find("img");
      var opts = $chart.chartOptions();
      var from = addFuzzyTime(opts.from, viewSettings.timeStep);
      if ("until" in opts) {
        var until = addFuzzyTime(opts.until, viewSettings.timeStep);
      } else {
        var until = viewSettings.timeStep;
      }

      $chart.alterChart({from: from, until: until});

    });

    $('.right.overlay a').click(function(e) {
      e.preventDefault();
      var $chart = $(this).parents(".chart-container").find("img");
      var opts = $chart.chartOptions();
      var from = subFuzzyTime(opts.from, viewSettings.timeStep);
      if ("until" in opts) {
        var until = subFuzzyTime(opts.until, viewSettings.timeStep);
      } else {
        return;
      }
      if( parseInt(from) == 0 ) { return; }
      if( parseInt(until) == 0 ) { until = false; }
      $chart.alterChart({from: from, until: until});
    });

  });
  

})(jQuery);
