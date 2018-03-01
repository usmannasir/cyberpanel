  /* jQuery UI Slider */

  $(function() {
      "use strict";
      $("#slider-example").slider();
  });

  $(function() {
      "use strict";
      $("#horizontal-slider").slider({
          value: 40,
          orientation: "horizontal",
          range: "min",
          animate: true
      });
  });

  $(function() {
      "use strict";
      $("#slider-range-vertical").slider({
          orientation: "vertical",
          range: true,
          values: [17, 67],
          slide: function(event, ui) {
              $("#amount-vertical-range").val("$" + ui.values[0] + " - $" + ui.values[1]);
          }
      });
      $("#amount-vertical-range").val("$" + $("#slider-range-vertical").slider("values", 0) +
          " - $" + $("#slider-range-vertical").slider("values", 1));
  });

  $(function() {
      "use strict";
      $("#slider-range").slider({
          range: true,
          min: 0,
          max: 500,
          values: [75, 300],
          slide: function(event, ui) {
              $("#amount").val("$" + ui.values[0] + " - $" + ui.values[1]);
          }
      });
      $("#amount").val("$" + $("#slider-range").slider("values", 0) +
          " - $" + $("#slider-range").slider("values", 1));
  });

  $(function() {
      "use strict";
      $("#slider-vertical").slider({
          orientation: "vertical",
          range: "min",
          min: 0,
          max: 100,
          value: 60,
          slide: function(event, ui) {
              $("#amount3").val(ui.value);
          }
      });
      $("#amount3").val($("#slider-vertical").slider("value"));
  });

  $(function() {
      "use strict";
      // setup master volume
      $("#master").slider({
          value: 60,
          orientation: "horizontal",
          range: "min",
          animate: true
      });
      // setup graphic EQ
      $("#eq > span").each(function() {
          // read initial values from markup and remove that
          var value = parseInt($(this).text(), 10);
          $(this).empty().slider({
              value: value,
              range: "min",
              animate: true,
              orientation: "vertical"
          });
      });
  });
