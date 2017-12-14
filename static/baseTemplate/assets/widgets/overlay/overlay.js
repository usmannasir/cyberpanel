$(document).ready(function(){

  /* Loader Show */

  $('.overlay-button').click(function(){

	var loadertheme = $(this).attr('data-theme');
	var loaderopacity = $(this).attr('data-opacity');
	var loaderstyle = $(this).attr('data-style');


	var loader = '<div id="loader-overlay" class="ui-front loader ui-widget-overlay ' + loadertheme + ' opacity-' + loaderopacity + '"><img src="../../assets/images/spinner/loader-' + loaderstyle + '.gif" alt="" /></div>';

    if ( $('#loader-overlay').length ) {
	    $('#loader-overlay').remove();
    }
    $('body').append(loader);
    $('#loader-overlay').fadeIn('fast');

    //demo

    setTimeout(function() {
      $('#loader-overlay').fadeOut('fast');
    }, 3000);

  });

	/* Refresh Box */

	$('.refresh-button').click(function(ev){

		$('.glyph-icon', this).addClass('icon-spin');

	    ev.preventDefault();

	    var refreshParent = $(this).parents('.content-box');

		var loaderTheme = $(this).attr('data-theme');
		var loaderOpacity = $(this).attr('data-opacity');
		var loaderStyle = $(this).attr('data-style');


		var loader = '<div id="refresh-overlay" class="ui-front loader ui-widget-overlay ' + loaderTheme + ' opacity-' + loaderOpacity + '"><img src="../../assets/images/spinner/loader-' + loaderStyle + '.gif" alt="" /></div>';

        if ( $('#refresh-overlay').length ) {
            $('#refresh-overlay').remove();
        }
	    $(refreshParent).append(loader);
	    $('#refresh-overlay').fadeIn('fast');

		//DEMO

        setTimeout(function() {
            $('#refresh-overlay').fadeOut('fast');
            $('.glyph-icon', this).removeClass('icon-spin');
        }, 1500);

	});

});