/* logdweb library */

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

    $.ajax({
      url: url,
      dataType: 'json',
      success: function(data) {
        for (var i=0; i<data.length; i++) {
          var line = data[i];
          $('table.log').append(line.rendered);
        }
      }
    });
  };

  /* update the log once per second */
  setInterval(function() {
    $('table.log').updateLog();
  }, 2000);

})(jQuery);
