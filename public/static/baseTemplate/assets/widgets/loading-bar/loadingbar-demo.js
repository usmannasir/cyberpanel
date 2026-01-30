  /* Loading bars */

  $(function() {
      "use strict";

      $(".loadingbar-demo").loadingbar({
          direction: "left",
          done: function(data) {
              $.each(data.items, function(i, item) {
                  $("<img/>").attr("src", item.media.m).prependTo($("#loading-frame"));
                  if (i === 2) {
                      return false;
                  }
              });
          }
      });

  });

  $(function() {
      "use strict";

      $(".loadingbar-demo-right").loadingbar({
          direction: "right",
          done: function(data) {
              $.each(data.items, function(i, item) {
                  $("<img/>").attr("src", item.media.m).prependTo($("#loading-frame"));
                  if (i === 2) {
                      return false;
                  }
              });
          }
      });

  });

  $(function() {
      "use strict";

      $(".loadingbar-demo-down").loadingbar({
          direction: "down",
          done: function(data) {
              $.each(data.items, function(i, item) {
                  $("<img/>").attr("src", item.media.m).prependTo($("#loading-frame"));
                  if (i === 2) {
                      return false;
                  }
              });
          }
      });

  });

  $(function() {
      "use strict";

      $(".loadingbar-demo-up").loadingbar({
          direction: "up",
          done: function(data) {
              $.each(data.items, function(i, item) {
                  $("<img/>").attr("src", item.media.m).prependTo($("#loading-frame"));
                  if (i === 2) {
                      return false;
                  }
              });
          }
      });

  });
