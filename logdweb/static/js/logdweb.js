/* logdweb library */

var viewSettings = {
  autoScroll: true,
  update: true
};

(function($) {
  /* update a log, run on a table dom element */
  $.fn.updateLog = function() {
    var $this = $(this);
    var path = $this.attr('id');
    if (!path) {
      return;
    }
    var last_id = Number($(this).find('tr:last td.id').html());
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
            $this.truncateLog(1000);
          }
        }
      });
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
      console.log("pruning " + num + "rows");
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
        var re = new RegExp(key + "=[^&]+");
        if ( src.match(re) ) {
          src = src.replace(new RegExp(key + "=[^&]+"), key + '=' + opts[key]);
        } else {
          src += '&' + key + '=' + opts[key];
        }
      }
      this.src = src
    });
    return this;
  };

  /* update the log once per second */
  setInterval(function() {
    $('table.log').updateLog();
  }, 2000);

  setInterval(function() {
    $('div.chart img').updateChart();
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


  });

})(jQuery);
