
  /* Colorpicker */

$(function() { "use strict";
  $('#colorpicker-inline').minicolors(
      {
          animationSpeed: 100,
          change: null,
          changeDelay: 0,
          control: 'hue',
          defaultValue: '',
          hide: null,
          hideSpeed: 100,
          inline: true,
          letterCase: 'lowercase',
          opacity: true,
          position: 'bottom right',
          show: null,
          showSpeed: 100,
          textfield: true,
          theme: 'default'
      });
});

$(function() { "use strict";
  $('#colorpicker-tl').minicolors(
      {
          animationSpeed: 100,
          change: null,
          changeDelay: 0,
          control: 'wheel',
          defaultValue: '',
          hide: null,
          hideSpeed: 100,
          inline: false,
          letterCase: 'lowercase',
          opacity: false,
          position: 'top left',
          show: null,
          showSpeed: 100,
          textfield: true,
          theme: 'default'
      });
  });

$(function() { "use strict";
  $('#colorpicker-br').minicolors(
      {
          animationSpeed: 100,
          change: null,
          changeDelay: 0,
          control: 'hue',
          defaultValue: '',
          hide: null,
          hideSpeed: 100,
          inline: false,
          letterCase: 'lowercase',
          opacity: false,
          position: 'bottom right',
          show: null,
          showSpeed: 100,
          textfield: true,
          theme: 'default'
      });
  });
