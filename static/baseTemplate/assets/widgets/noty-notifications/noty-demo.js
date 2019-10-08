  /* Noty */

  $(function() {

      var notes = [];

      notes[''] = '<i class="glyph-icon icon-cog mrg5R"></i>This is a default notification message.';
      notes['alert'] = '<i class="glyph-icon icon-cog mrg5R"></i>This is an alert notification message.';
      notes['error'] = '<i class="glyph-icon icon-cog mrg5R"></i>This is an error notification message.';
      notes['success'] = '<i class="glyph-icon icon-cog mrg5R"></i>You successfully read this important message.';
      notes['information'] = '<i class="glyph-icon icon-cog mrg5R"></i>This is an information notification message!';
      notes['notification'] = '<i class="glyph-icon icon-cog mrg5R"></i>This alert needs your attention, but it\'s for demonstration purposes only.';
      notes['warning'] = '<i class="glyph-icon icon-cog mrg5R"></i>This is a warning for demonstration purposes.';


      $('.noty').click(function() {

          var self = $(this);


          noty({
              text: notes[self.data('type')],
              type: self.data('type'),
              dismissQueue: true,
              theme: 'agileUI',
              layout: self.data('layout')
          });
          return false;
      });


  });
