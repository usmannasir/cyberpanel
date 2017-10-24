/**
 * @preserve Copyright 2011 Syd Lawrence ( www.sydlawrence.com ).
 * Version: 0.2
 *
 * Licensed under MIT and GPLv2.
 *
 * Usage: $('body').videoBG(options);
 *
 */

(function( $ ){

	$.fn.videoBG = function( selector, options ) { 
		
		var options = {};
		if (typeof selector == "object") {
			options = $.extend({}, $.fn.videoBG.defaults, selector);
		}
		else if (!selector) {
			options = $.fn.videoBG.defaults;
		}
		else {
			return $(selector).videoBG(options);		
		}
		
		var container = $(this);
		
		// check if elements available otherwise it will cause issues
		if (!container.length)
			return;
		
		// container to be at least relative
		if (container.css('position') == 'static' || !container.css('position'))
			container.css('position','relative');
		
		// we need a width
		if (options.width == 0)
			options.width = container.width();
		
		// we need a height
		if (options.height == 0)
			options.height = container.height();	
		
		// get the wrapper
		var wrap = $.fn.videoBG.wrapper();
		wrap.height(options.height)
			.width(options.width);
		
		// if is a text replacement
		if (options.textReplacement) {
		
			// force sizes
			options.scale = true;
			
			// set sizes and forcing text out
			container.width(options.width)
				.height(options.height)
				.css('text-indent','-9999px');
		}
		else {
		
			// set the wrapper above the video
			wrap.css('z-index',options.zIndex+1);
		}
		
		// move the contents into the wrapper
		wrap.html(container.clone(true));
		
		// get the video
		var video = $.fn.videoBG.video(options);
		
		// if we are forcing width / height
		if (options.scale) {
			
			// overlay wrapper
			wrap.height(options.height)
				.width(options.width);
			
			// video
			video.height(options.height)
				.width(options.width);
		}
		
		// add it all to the container
		container.html(wrap);
		container.append(video);
		
		return video.find("video")[0];
	}

	// set to fullscreen
	$.fn.videoBG.setFullscreen = function($el) {
		var windowWidth = $(window).width(),
			windowHeight = $(window).height();

		$el.css('min-height',0).css('min-width',0);
		$el.parent().width(windowWidth).height(windowHeight);
		// if by width 
		if (windowWidth / windowHeight > $el.aspectRatio) {
			$el.width(windowWidth).height('auto');
			// shift the element up
			var height = $el.height();
			var shift = (height - windowHeight) / 2;
			if (shift < 0) shift = 0;
			$el.css("top",-shift);
		} else {
			$el.width('auto').height(windowHeight);			
			// shift the element left
			var width = $el.width();
			var shift = (width - windowWidth) / 2;
			if (shift < 0) shift = 0;
			$el.css("left",-shift);
			
			// this is a hack mainly due to the iphone
			if (shift === 0) {
				var t = setTimeout(function() {
					$.fn.videoBG.setFullscreen($el);
				},500);
			}
		}

		$('body > .videoBG_wrapper').width(windowWidth).height(windowHeight);
			
	}

	// get the formatted video element
	$.fn.videoBG.video = function(options) {
		
		$('html, body').scrollTop(-1);

		// video container
		var $div = $('<div/>');
		$div.addClass('videoBG')
			.css('position',options.position)
			.css('z-index',options.zIndex)
			.css('top',0)
			.css('left',0)
			.css('height',options.height)
			.css('width',options.width)
			.css('opacity',options.opacity)
			.css('overflow','hidden');
		
		// video element
		var $video = $('<video/>');
		$video.css('position','absolute')
			.css('z-index',options.zIndex)
			.attr('poster',options.poster)
			.css('top',0)
			.css('left',0)
			.css('min-width','100%')
			.css('min-height','100%');
		
		if (options.autoplay) {
			$video.attr('autoplay',options.autoplay);
		}

		// if fullscreen
		if (options.fullscreen) {
			$video.bind('canplay',function() {
				// set the aspect ratio
				$video.aspectRatio = $video.width() / $video.height();
				$.fn.videoBG.setFullscreen($video);
			})

			// listen out for screenresize
			var resizeTimeout;
			$(window).resize(function() {
				clearTimeout(resizeTimeout);
				resizeTimeout = setTimeout(function() {
					$.fn.videoBG.setFullscreen($video);
				},100);	
			});
			$.fn.videoBG.setFullscreen($video);
		}
			
		
		// video standard element
		var v = $video[0];
		
		// if meant to loop
		if (options.loop) {
			loops_left = options.loop;
		
			// cant use the loop attribute as firefox doesnt support it
			$video.bind('ended', function(){
				
				// if we have some loops to throw
				if (loops_left)
					// replay that bad boy
					v.play();
				
				// if not forever
				if (loops_left !== true)
					// one less loop
					loops_left--;
  			});
		}
		
		// when can play, play
		$video.bind('canplay', function(){
			
			if (options.autoplay)
				// replay that bad boy
				v.play();
				
		});
		
		
		// if supports video
		if ($.fn.videoBG.supportsVideo()) {

		  	// supports webm
		  	if ($.fn.videoBG.supportType('webm')){
		  		
		  		// play webm
		  		$video.attr('src',options.webm);
		  	}
		  	// supports mp4
		  	else if ($.fn.videoBG.supportType('mp4')) {	  	
		  		
		  		// play mp4
		  		$video.attr('src',options.mp4);
		  		
		  	//	$video.html('<source src="'.options.mp4.'" />');
		  		
		  	}
		  	// throw ogv at it then
		  	else {
		  		
		  		// play ogv
		  		$video.attr('src',options.ogv);
		  	}
	  	
	  	}
	  	
	  	
		
		// image for those that dont support the video	
		var $img = $('<img/>');
		$img.attr('src',options.poster)
			.css('position','absolute')
			.css('z-index',options.zIndex)
			.css('top',0)
			.css('left',0)
			.css('min-width','100%')
			.css('min-height','100%');
		
		// add the image to the video
		// if suuports video
		if ($.fn.videoBG.supportsVideo()) {
			// add the video to the wrapper
			$div.html($video);
		}
		
		// nope - whoa old skool
		else {
			
			// add the image instead
			$div.html($img);
		}
		
		// if text replacement
		if (options.textReplacement) {
	
			// force the heights and widths
			$div.css('min-height',1).css('min-width',1);
			$video.css('min-height',1).css('min-width',1);
			$img.css('min-height',1).css('min-width',1);
			
			$div.height(options.height).width(options.width);
			$video.height(options.height).width(options.width);
			$img.height(options.height).width(options.width);	
		}
		
		if ($.fn.videoBG.supportsVideo()) {
			v.play();
		}
		return $div;
	}
	
	// check if suuports video
	$.fn.videoBG.supportsVideo = function() {
		return (document.createElement('video').canPlayType);
	}
	
	// check which type is supported
	$.fn.videoBG.supportType = function(str) {
		
		// if not at all supported
		if (!$.fn.videoBG.supportsVideo())
			return false;
		
		// create video
		var v = document.createElement('video');
		
		// check which?
		switch (str) {
			case 'webm' :
				return (v.canPlayType('video/webm; codecs="vp8, vorbis"'));
				break;
			case 'mp4' :
				return (v.canPlayType('video/mp4; codecs="avc1.42E01E, mp4a.40.2"'));
				break;
			case 'ogv' :
				return (v.canPlayType('video/ogg; codecs="theora, vorbis"'));
				break;			
		}
		// nope
		return false;	
	}
	
	// get the overlay wrapper
	$.fn.videoBG.wrapper = function() {
		var $wrap = $('<div/>');
		$wrap.addClass('videoBG_wrapper')
			.css('position','absolute')
			.css('top',0)
			.css('left',0);
		return $wrap;
	}
	
	// these are the defaults
	$.fn.videoBG.defaults = {
			mp4:'',
			ogv:'',
			webm:'',
			poster:'',
			autoplay:true,
			loop:true,
			scale:false,
			position:"absolute",
			opacity:0.7,
			textReplacement:false,
			zIndex:0,
			width:0,
			height:0,
			fullscreen:false,
			imgFallback:true
		}

})( jQuery );