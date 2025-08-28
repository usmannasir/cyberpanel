
/*
 * LayerSlider
 *
 * (c) 2011-2014 George Krupa, John Gera & Kreatura Media
 *
 * Plugin web:			http://kreaturamedia.com/
 * licenses:				http://codecanyon.net/licenses/
 */



function lsShowNotice(lsobj,issue,ver){

    var el;

    if( typeof lsobj == 'string' ){
        el = jQuery('#'+lsobj);
    }else if( typeof lsobj == 'object' ){
        el = lsobj;
    }

    var errorTitle, errorText;

    switch(issue){
        case 'jquery':
            errorTitle = 'multiple jQuery issue';
            errorText = 'It looks like that another plugin or your theme loads an extra copy of the jQuery library causing problems for LayerSlider to show your sliders. <strong>Please navigate on your WordPress admin area to the main page of LayerSlider and enable the "Put JS includes to body" option within the Troubleshooting & Advanced Settings box.</strong>';
            break;
        case 'oldjquery':
            errorTitle = 'old jQuery issue';
            errorText = 'It looks like you are using an old version ('+ver+') of the jQuery library. LayerSlider requires at least version 1.7.0 or newer. Please update jQuery to 1.10.x or higher. Important: Please do not use the jQuery Updater plugin on WordPress and do not update to 2.x version of jQuery because it is not compatible with older browsers like IE 7 & 8. <a href="http://support.kreaturamedia.com/faq/4/layerslider-for-wordpress/#group-13&entry-60">You can read more about updating jQuery by clicking here.</a>';
            break;
    }

    el.addClass('ls-error');
    el.append('<p class="ls-exclam">!</p>');
    el.append('<p class="ls-error-title">LayerSlider: '+errorTitle+'</p>');
    el.append('<p class="ls-error-text">'+errorText+'</p>');
}

(function($) {

    $.fn.layerSlider = function( options ){

        // IMPROVEMENT v4.1.0 Checking jQuery version
        // IMPROVEMENT v4.1.3 Changed required version from 1.7.2 to 1.7.0

        var reqVer = '1.7.0';
        var curVer = $.fn.jquery;
        var el = $(this);

        var checkVersions = function(v1,v2){

            var v1parts = v1.split('.');
            var v2parts = v2.split('.');

            for (var i = 0; i < v1parts.length; ++i) {

                if (v2parts.length == i) {
                    return false;
                }

                if(parseInt(v1parts[i]) == parseInt(v2parts[i])){
                    continue;
                }else if (parseInt(v1parts[i]) > parseInt(v2parts[i])){
                    return false;
                }else{
                    return true;
                }
            }

            if (v1parts.length != v2parts.length) {
                return true;
            }

            return true;
        };

        if( !checkVersions('1.8.0',curVer) ){
            el.addClass('ls-norotate');
        }

        // Initializing if jQuery version is greater than 1.7.0

        if( !checkVersions(reqVer,curVer) ){
            lsShowNotice( el, 'oldjquery', curVer );
        }else{

            if( (typeof(options)).match('object|undefined') ){
                return this.each(function(i){
                    new layerSlider(this, options);
                });
            }else{
                if( options === 'data' ){
                    var lsData = $(this).data('LayerSlider').g;
                    if( lsData ){
                        return lsData;
                    }

                    // NEW FEATURES v5.2.0 option to get userInitData & defaultInitData

                }else if( options === 'userInitData' ){
                    var lsInitData = $(this).data('LayerSlider').o;
                    if( lsInitData ){
                        return lsInitData;
                    }
                }else if( options === 'defaultInitData' ){
                    var lsInitData = $(this).data('LayerSlider').defaults;
                    if( lsInitData ){
                        return lsInitData;
                    }

                }else{
                    return this.each(function(i){

                        // Control functions: prev, next, start, stop & change

                        var lsData = $(this).data('LayerSlider');
                        if( lsData ){
                            if( !lsData.g.isAnimating && !lsData.g.isLoading ){
                                if( typeof options == 'number' ){
                                    if( options > 0 && options < lsData.g.layersNum + 1 && options != lsData.g.curLayerIndex ){
                                        lsData.change(options);
                                    }
                                }else{
                                    switch(options){
                                        case 'prev':
                                            lsData.o.cbPrev(lsData.g);
                                            lsData.prev('clicked');
                                            break;
                                        case 'next':
                                            lsData.o.cbNext(lsData.g);
                                            lsData.next('clicked');
                                            break;
                                        case 'start':
                                            if( !lsData.g.autoSlideshow ){
                                                lsData.o.cbStart(lsData.g);
                                                lsData.g.originalAutoSlideshow = true;
                                                lsData.start();
                                            }
                                            break;
                                    }
                                }
                            }
                            // if( options === 'debug' ){
                            // 	lsData.d.show();
                            // }
                            if( options === 'redraw' ){
                                lsData.resize();
                            }
                            if( ( lsData.g.autoSlideshow || ( !lsData.g.autoSlideshow && lsData.g.originalAutoSlideshow ) ) && options == 'stop' ){
                                lsData.o.cbStop(lsData.g);
                                lsData.g.originalAutoSlideshow = false;
                                lsData.g.curLayer.find('iframe[src*="youtube.com"], iframe[src*="youtu.be"], iframe[src*="player.vimeo"]').each(function(){

                                    // Clearing videoTimeouts

                                    clearTimeout( $(this).data( 'videoTimer') );
                                });

                                lsData.stop();
                            }
                            if( options == 'forceStop'){
                                lsData.forcestop();
                            }
                        }
                    });
                }
            }
        }
    };

    // LayerSlider methods

    var layerSlider = function(el, options) {

        var ls = this;
        ls.$el = $(el).addClass('ls-container');
        ls.$el.data('LayerSlider', ls);

        ls.load = function(){

            // Setting options (user settings) and global (not modificable) parameters

            ls.defaults = layerSlider.options;
            ls.o = $.extend({},ls.defaults, options);
            ls.g = $.extend({},layerSlider.global);
            ls.lt = $.extend({},layerSlider.layerTransitions );
            ls.st = $.extend({},layerSlider.slideTransitions );

            ls.g.enableCSS3 = $(el).hasClass('ls-norotate') ? false : true;

            // NEW FEATURE v5.2.0 saving original HTML Markup

            ls.g.originalMarkup = $(el).html();

            if( ls.g.ie78 ){
                ls.o.lazyLoad = false;
            }

            // WP parameters

            if( ls.o.autoPauseSlideshow === 'enabled' ){
                ls.o.autoPauseSlideshow = true;
            }
            if( ls.o.autoPauseSlideshow === 'disabled' ){
                ls.o.autoPauseSlideshow = false;
            }

            // If layerslider.transitions.js is loaded...

            if( typeof layerSliderTransitions !== 'undefined' ){
                ls.t = $.extend({},layerSliderTransitions);
            }

            // If custom transitions are loaded...

            if( typeof layerSliderCustomTransitions !== 'undefined' ){
                ls.ct = $.extend({},layerSliderCustomTransitions);
            }

            // NEW IMPROVEMENT v3.6 forbid to call the init code more than once on the same element

            if( !ls.g.initialized ){

                ls.g.initialized = true;

                // Added debug mode v3.5

                // ls.debug();

                if( $('html').find('meta[content*="WordPress"]').length ){
                    ls.g.wpVersion = $('html').find('meta[content*="WordPress"]').attr('content').split('WordPress')[1];
                }

                if( $('html').find('script[src*="layerslider"]').length ){
                    if( $('html').find('script[src*="layerslider"]').attr('src').indexOf('?') != -1 ){
                        ls.g.lswpVersion = $('html').find('script[src*="layerslider"]').attr('src').split('?')[1].split('=')[1];
                    }
                }

                // Debug mode controls

                // ls.d.aT('LayerSlider controls');
                // ls.d.aU('<a href="#">prev</a> | <a href="#">next</a> | <a href="#">start</a> | <a href="#">stop</a> | <a href="#">force stop</a>');
                // ls.d.history.find('a').each(function(){
                // 	$(this).click(function(e){
                // 		e.preventDefault();
                // 		$(el).layerSlider($(this).text());
                // 	});
                // });

                // ls.d.aT('LayerSlider version information');
                // ls.d.aU('JS version: <strong>' + ls.g.version + '</strong>');
                // if(ls.g.lswpVersion){
                // 	ls.d.aL('WP version: <strong>' + ls.g.lswpVersion + '</strong>');
                // }
                // if(ls.g.wpVersion){
                // 	ls.d.aL('WordPress version: <strong>' + ls.g.wpVersion + '</strong>');
                // }

                // ls.d.aL('jQuery version: <strong>' + $().jquery + '</strong>');

                // if( $(el).attr('id') ){

                // 	ls.d.aT('LayerSlider container');
                // 	ls.d.aU('#'+$(el).attr('id'));
                // }

                // NEW LOAD METHOD v3.5
                // FIXED v4.0 If the selected skin is already loaded, calling the ls.init() function immediately

                if( !ls.o.skin || ls.o.skin == '' || !ls.o.skinsPath || ls.o.skinsPath == '' ){

                    // ls.d.aT('Loading without skin. Possibilities: mistyped skin and / or skinsPath.');

                    ls.init();
                }else{

                    // ls.d.aT('Trying to load with skin: '+ls.o.skin, true);

                    // Applying skin

                    $(el).addClass('ls-'+ls.o.skin);

                    var skinStyle = ls.o.skinsPath+ls.o.skin+'/skin.css';

                    cssContainer = $('head');

                    if( !$('head').length ){
                        cssContainer = $('body');
                    }

                    if( $('link[href="'+skinStyle+'"]').length ){

                        // ls.d.aU('Skin "'+ls.o.skin+'" is already loaded.');

                        curSkin = $('link[href="'+skinStyle+'"]');

                        if( !ls.g.loaded ){

                            ls.g.loaded = true;

                            // IMPROVEMENT v4.5.0 Added delay because of caching bugs

                            ls.g.t1 = setTimeout(function(){
                                ls.init();
                            },150);
                        }

                    }else{
                        if (document.createStyleSheet){
                            document.createStyleSheet(skinStyle);
                            var curSkin = $('link[href="'+skinStyle+'"]');
                        }else{
                            var curSkin = $('<link rel="stylesheet" href="'+skinStyle+'" type="text/css" />').appendTo( cssContainer );
                        }
                    }

                    // curSkin.load(); function for most of the browsers.

                    curSkin.load(function(){

                        if( !ls.g.loaded ){

                            // ls.d.aU('curSkin.load(); fired');

                            ls.g.loaded = true;

                            // IMPROVEMENT v4.5.0 Added delay because of caching bugs

                            ls.g.t2 = setTimeout(function(){
                                ls.init();
                            },150);
                        }
                    });

                    // $(window).load(); function for older webkit ( < v536 ).

                    $(window).load(function(){

                        if( !ls.g.loaded ){

                            // ls.d.aU('$(window).load(); fired');

                            ls.g.loaded = true;

                            // IMPROVEMENT v4.5.0 Added delay because of caching bugs

                            ls.g.t3 = setTimeout(function(){
                                ls.init();
                            },150);
                        }
                    });

                    // Fallback: if $(window).load(); not fired in 2 secs after $(document).ready(),
                    // curSkin.load(); not fired at all or the name of the skin and / or the skinsPath
                    // mistyped, we must call the init function manually.

                    ls.g.t4 = setTimeout( function(){

                        if( !ls.g.loaded ){

                            // ls.d.aT('Fallback mode: Neither curSkin.load(); or $(window).load(); were fired');

                            ls.g.loaded = true;
                            ls.init();
                        }
                    }, 1000);
                }
            }
        };

        ls.init = function(){

            // NEW FEATURE v5.5.0 Appending the slider element into the element specified in appendTo

            $(el).prependTo( $( ls.o.appendTo ) );

            // IMPROVEMENT v4.0.1 Trying to add special ID to <body> or <html> (required to overwrite WordPresss global styles)

            if( !$('html').attr('id') ){
                $('html').attr('id','ls-global');
            }else if( !$('body').attr('id') ){
                $('body').attr('id','ls-global');
            }

            // NEW FEATURES v5.5.0 Hiding the slider on mobile devices, smaller resolutions
            // or changing it to a static but responsive image

            if( ls.g.isMobile() === true && ls.o.hideOnMobile === true ){
                $(el).addClass('ls-forcehide');
                $(el).closest('.ls-wp-fullwidth-container').addClass('ls-forcehide');
            }

            var showHide = function(){

                if( ls.o.hideOnMobile === true && ls.g.isMobile() === true ){
                    $(el).addClass('ls-forcehide');
                    $(el).closest('.ls-wp-fullwidth-container').addClass('ls-forcehide');
                    ls.o.autoStart = false;
                }else{
                    if( $(window).width() < ls.o.hideUnder || $(window).width() > ls.o.hideOver ){
                        $(el).addClass('ls-forcehide');
                        $(el).closest('.ls-wp-fullwidth-container').addClass('ls-forcehide');
                    }else{
                        $(el).removeClass('ls-forcehide');
                        $(el).closest('.ls-wp-fullwidth-container').removeClass('ls-forcehide');
                    }
                }
            };

            $(window).resize( function(){

                showHide();
            });

            showHide();

            // NEW FEATURE v1.7 making the slider responsive

            ls.g.sliderWidth = function(){
                return $(el).width();
            }

            ls.g.sliderHeight = function(){
                return $(el).height();
            }

            // Compatibility mode v5.0.0
            //	.ls-layer 	-> .ls-slide
            //	.ls-s 		-> .ls-l

            $(el).find('.ls-layer').removeClass('ls-layer').addClass('ls-slide');
            $(el).find('.ls-slide > *[class*="ls-s"]').each(function(){
                var oldDistanceNum = $(this).attr('class').split('ls-s')[1].split(' ')[0];
                $(this).removeClass('ls-s'+oldDistanceNum).addClass('ls-l'+oldDistanceNum);
            });


            if( ls.o.firstLayer ){
                ls.o.firstSlide = ls.o.firstLayer;
            }
            if( ls.o.animateFirstLayer === false ){
                ls.o.animateFirstSlide = false;
            }

            // REPLACED FEATURE v2.0 If there is only ONE layer, instead of duplicating it, turning off slideshow and loops, hiding all controls, etc.

            if( $(el).find('.ls-slide').length == 1 ){
                ls.o.autoStart = false;
                ls.o.navPrevNext = false;
                ls.o.navStartStop = false;
                ls.o.navButtons = false;
                ls.o.loops = 0;
                ls.o.forceLoopNum = false;
                ls.o.autoPauseSlideshow	= true;
                ls.o.firstSlide = 1;
                ls.o.thumbnailNavigation = 'disabled';
            }

            // IMPROVEMENT v5.2.0 the original width of a full width slider should be always 100% even if the user forgot to set that value
            // BUGFIX v5.3.0 An additional check required (with the original improvement full-width sliders with "normal" responsiveness couldn't be created)

            if( $(el).parent().hasClass('ls-wp-fullwidth-helper') && ls.o.responsiveUnder !== 0 ){
                $(el)[0].style.width = '100%';
            }

            // NEW FEATURE v3.0 added "normal" responsive mode with image and font resizing
            // NEW FEATURE v3.5 responsiveUnder

            if( ls.o.width ){
                ls.g.sliderOriginalWidthRU = ls.g.sliderOriginalWidth = '' + ls.o.width;
            }else{
                ls.g.sliderOriginalWidthRU = ls.g.sliderOriginalWidth = $(el)[0].style.width;
            }

            if( ls.o.height ){
                ls.g.sliderOriginalHeight = '' + ls.o.height;
            }else{
                ls.g.sliderOriginalHeight = $(el)[0].style.height;
            }

            if( ls.g.sliderOriginalWidth.indexOf('%') == -1 && ls.g.sliderOriginalWidth.indexOf('px') == -1 ){
                ls.g.sliderOriginalWidth += 'px';
            }

            if( ls.g.sliderOriginalHeight.indexOf('%') == -1 && ls.g.sliderOriginalHeight.indexOf('px') == -1 ){
                ls.g.sliderOriginalHeight += 'px';
            }

            if( ls.o.responsive && ls.g.sliderOriginalWidth.indexOf('px') != -1 && ls.g.sliderOriginalHeight.indexOf('px') != -1 ){
                ls.g.responsiveMode = true;
            }else{
                ls.g.responsiveMode = false;
            }

            // NEW FEATURE v5.5.0 We must overwrite some user settings if fullScreen mode is enabled

            if( ls.o.fullScreen === true ){
                ls.o.responsiveUnder = 0;
                ls.g.responsiveMode = true;

                if( ls.g.sliderOriginalWidth.indexOf('%') != -1 ){
                    ls.g.sliderOriginalWidth = parseInt( ls.g.sliderOriginalWidth) + 'px';
                }

                if( ls.g.sliderOriginalHeight.indexOf('%') != -1 ){
                    ls.g.sliderOriginalHeight = parseInt( ls.g.sliderOriginalHeight) + 'px';
                }
            }

            // IMPROVEMENT v3.0 preventing WordPress to wrap your sublayers in <code> or <p> elements

            $(el).find('*[class*="ls-l"], *[class*="ls-bg"]').each(function(){
                if( !$(this).parent().hasClass('ls-slide') ){
                    $(this).insertBefore( $(this).parent() );
                }
            });

            $(el).find('.ls-slide').each(function(){
                $(this).children(':not([class*="ls-"])').each(function(){
                    $(this).remove();
                });

                var hd = $('<div>').addClass('ls-gpuhack');
                if( $(this).find('.ls-bg').length ){
                    hd.insertAfter( $(this).find('.ls-bg').eq('0') );
                }else{
                    hd.prependTo( $(this) );
                }
            });

            $(el).find('.ls-slide, *[class*="ls-l"]').each(function(){

                if( $(this).data('ls') || $(this).attr('rel') || $(this).attr('style') ){
                    if( $(this).data('ls') ){
                        var params = $(this).data('ls').toLowerCase().split(';');
                    }else if( $(this).attr('rel') && $(this).attr('rel').indexOf(':') != -1 && $(this).attr('rel').indexOf(';') != -1 ){
                        var params = $(this).attr('rel').toLowerCase().split(';');
                    }else{
                        var params = $(this).attr('style').toLowerCase().split(';');
                    }
                    for(x=0;x<params.length;x++){
                        param = params[x].split(':');

                        if( param[0].indexOf('easing') != -1 ){
                            param[1] = ls.ieEasing( param[1] );
                        }

                        var p2 = '';
                        if( param[2] ){
                            p2 = ':'+$.trim(param[2]);
                        }

                        if( param[0] != ' ' && param[0] != '' ){
                            $(this).data( $.trim(param[0]), $.trim(param[1]) + p2 );
                        }
                    }
                }

                // NEW FEATURE v5.2.0 Starts the slider only if it is in the viewport

                if( ls.o.startInViewport === true && ls.o.autoStart === true ){

                    ls.o.autoStart = false;
                    ls.g.originalAutoStart = true;
                }

                // NEW FEATURE v1.7 and v3.0 making the slider responsive - we have to use style.left instead of jQuery's .css('left') function!

                var sl = $(this);

                sl.data( 'originalLeft', sl[0].style.left );
                sl.data( 'originalTop', sl[0].style.top );

                if( $(this).is('a') && $(this).children().length > 0 ){
                    sl = $(this).children();
                }

                var _w = sl.width();
                var _h = sl.height();

                if( sl[0].style.width && sl[0].style.width.indexOf('%') != -1 ){
                    _w = sl[0].style.width;
                }
                if( sl[0].style.height && sl[0].style.height.indexOf('%') != -1 ){
                    _h = sl[0].style.height;
                }

                sl.data( 'originalWidth', _w );
                sl.data( 'originalHeight', _h );

                sl.data( 'originalPaddingLeft', sl.css('padding-left') );
                sl.data( 'originalPaddingRight', sl.css('padding-right') );
                sl.data( 'originalPaddingTop', sl.css('padding-top') );
                sl.data( 'originalPaddingBottom', sl.css('padding-bottom') );

                // iOS fade bug when GPU acceleration is enabled #1

                var _o = typeof parseFloat( sl.css('opacity') ) == 'number'  ? Math.round( parseFloat( sl.css('opacity') ) * 100 ) / 100  : 1;
                $(this).data( 'originalOpacity', _o );

                if( sl.css('border-left-width').indexOf('px') == -1 ){
                    sl.data( 'originalBorderLeft', sl[0].style.borderLeftWidth );
                }else{
                    sl.data( 'originalBorderLeft', sl.css('border-left-width') );
                }
                if( sl.css('border-right-width').indexOf('px') == -1 ){
                    sl.data( 'originalBorderRight', sl[0].style.borderRightWidth );
                }else{
                    sl.data( 'originalBorderRight', sl.css('border-right-width') );
                }
                if( sl.css('border-top-width').indexOf('px') == -1 ){
                    sl.data( 'originalBorderTop', sl[0].style.borderTopWidth );
                }else{
                    sl.data( 'originalBorderTop', sl.css('border-top-width') );
                }
                if( sl.css('border-bottom-width').indexOf('px') == -1 ){
                    sl.data( 'originalBorderBottom', sl[0].style.borderBottomWidth );
                }else{
                    sl.data( 'originalBorderBottom', sl.css('border-bottom-width') );
                }

                sl.data( 'originalFontSize', sl.css('font-size') );
                sl.data( 'originalLineHeight', sl.css('line-height') );
            });

            // CHANGED FEATURE v3.5 url- / deep linking layers

            if( document.location.hash ){
                for( var dl = 0; dl < $(el).find('.ls-slide').length; dl++ ){
                    if( $(el).find('.ls-slide').eq(dl).data('deeplink') == document.location.hash.split('#')[1] ){
                        ls.o.firstSlide = dl+1;
                    }
                }
            }

            // NEW FEATURE v2.0 linkTo

            $(el).find('*[class*="ls-linkto-"]').each(function(){
                var lClasses = $(this).attr('class').split(' ');
                for( var ll=0; ll<lClasses.length; ll++ ){
                    if( lClasses[ll].indexOf('ls-linkto-') != -1 ){
                        var linkTo = parseInt( lClasses[ll].split('ls-linkto-')[1] );
                        $(this).css({
                            cursor: 'pointer'
                        }).click(function(e){
                            e.preventDefault();
                            $(el).layerSlider( linkTo );
                        });
                    }
                }
            });

            // Setting variables

            ls.g.layersNum = $(el).find('.ls-slide').length;

            // NEW FEATURE v3.5 randomSlideshow

            if( ls.o.randomSlideshow && ls.g.layersNum > 2 ){
                ls.o.firstSlide == 'random';
                ls.o.twoWaySlideshow = false;
            }else{
                ls.o.randomSlideshow = false;
            }

            // NEW FEATURE v3.0 random firstSlide

            if( ls.o.firstSlide == 'random' ){
                ls.o.firstSlide = Math.floor(Math.random() * ls.g.layersNum+1);
            }

            ls.o.fisrtSlide = ls.o.fisrtSlide < ls.g.layersNum + 1 ? ls.o.fisrtSlide : 1;
            ls.o.fisrtSlide = ls.o.fisrtSlide < 1 ? 1 : ls.o.fisrtSlide;

            // NEW FEATURE v2.0 loops

            ls.g.nextLoop = 1;

            if( ls.o.animateFirstSlide ){
                ls.g.nextLoop = 0;
            }

            // NEW FEATURE v2.0 videoPreview
            // IMPROVEMENT v4.6.0 http / https support of embedded videos

            var HTTP = document.location.href.indexOf('file:') === -1 ? '' : 'http:';

            // Youtube videos

            $(el).find('iframe[src*="youtube.com"], iframe[src*="youtu.be"]').each(function(){

                // BUGFIX v4.1.0 Firefox embedded video fix

                $(this).parent().addClass('ls-video-layer');

                if( $(this).parent('[class*="ls-l"]') ){

                    var iframe = $(this);
                    var http = HTTP;

                    // Getting thumbnail

                    $.getJSON( http + '//gdata.youtube.com/feeds/api/videos/' + $(this).attr('src').split('embed/')[1].split('?')[0] + '?v=2&alt=json&callback=?', function(data) {

                        iframe.data( 'videoDuration', parseInt(data['entry']['media$group']['yt$duration']['seconds']) * 1000 );
                    });

                    var vpContainer = $('<div>').addClass('ls-vpcontainer').appendTo( $(this).parent() );

//					if( ls.o.lazyLoad ){
//						$('<img>').appendTo( vpContainer ).addClass('ls-videopreview').attr('alt', 'Play video').data('src',  http + '//img.youtube.com/vi/' + $(this).attr('src').split('embed/')[1].split('?')[0] + '/' + ls.o.youtubePreview );
//					}else{
                    $('<img>').appendTo( vpContainer ).addClass('ls-videopreview').attr('alt', 'Play video').attr('src',  http + '//img.youtube.com/vi/' + $(this).attr('src').split('embed/')[1].split('?')[0] + '/' + ls.o.youtubePreview );
//					}
                    $('<div>').appendTo( vpContainer ).addClass('ls-playvideo');

                    $(this).parent().css({
                        width : $(this).width(),
                        height : $(this).height()
                    }).click(function(){

                        // IMPROVEMENT v5.2.0 if video playing is in progress, video layers with auto play will skip showuntil feature

                        if( $(this).data('showuntil') > 0 && $(this).data('showUntilTimer') ){
                            clearTimeout( $(this).data('showUntilTimer') );
                        }

                        ls.g.isAnimating = true;

                        if( ls.g.paused ){
                            if( ls.o.autoPauseSlideshow != false ){
                                ls.g.paused = false;
                            }
                            ls.g.originalAutoSlideshow = true;
                        }else{
                            ls.g.originalAutoSlideshow = ls.g.autoSlideshow;
                        }

                        if( ls.o.autoPauseSlideshow != false ){
                            ls.stop();
                        }

                        ls.g.pausedByVideo = true;

                        http = $(this).find('iframe').data('videoSrc').indexOf('http') === -1 ? HTTP : '';

                        $(this).find('iframe').attr('src', http + $(this).find('iframe').data('videoSrc') );
                        $(this).find('.ls-vpcontainer').delay(ls.g.v.d).fadeOut(ls.g.v.fo, function(){
                            if( ls.o.autoPauseSlideshow == 'auto' && ls.g.originalAutoSlideshow == true ){
                                var videoTimer = setTimeout(function() {
                                    ls.start();
                                }, iframe.data( 'videoDuration') - ls.g.v.d );
                                iframe.data( 'videoTimer', videoTimer );
                            }
                            ls.g.isAnimating = false;
                            if( ls.g.resize == true ){
                                ls.makeResponsive( ls.g.curLayer, function(){
                                    ls.g.resize = false;
                                });
                            }
                        });
                    });

                    var sep = '&';

                    if( $(this).attr('src').indexOf('?') == -1 ){
                        sep = '?';
                    }

                    // BUGFIX v5.1.0 Fixed several issues with embedded videos (mostly under Firefox and IE)
                    // fixed 'only audio but no video' bug, fixed 'unclickable video controls' bug, fixed 'hidden slider controls' bug

                    var videoFix = '&wmode=opaque&html5=1';

                    // BUGFIX v5.1.0 Fixed autoplay parameter

                    if( $(this).attr('src').indexOf('autoplay') == -1 ){
                        $(this).data( 'videoSrc', $(this).attr('src') + sep + 'autoplay=1' + videoFix );
                    }else{
                        $(this).data( 'videoSrc', $(this).attr('src').replace('autoplay=0','autoplay=1') + videoFix );
                    }

                    $(this).data( 'originalWidth', $(this).attr('width') );
                    $(this).data( 'originalHeight', $(this).attr('height') );
                    $(this).attr('src','');
                }
            });

            // Vimeo videos

            $(el).find('iframe[src*="player.vimeo"]').each(function(){

                // BUGFIX v4.1.0 Firefox embedded video fix

                $(this).parent().addClass('ls-video-layer');

                if( $(this).parent('[class*="ls-l"]') ){

                    var iframe = $(this);
                    var http = HTTP;

                    // Getting thumbnail

                    var vpContainer = $('<div>').addClass('ls-vpcontainer').appendTo( $(this).parent() );

                    $.getJSON( http + '//vimeo.com/api/v2/video/'+ ( $(this).attr('src').split('video/')[1].split('?')[0] ) +'.json?callback=?', function(data){

//						if( ls.o.lazyLoad ){
//							$('<img>').appendTo( vpContainer ).addClass('ls-videopreview').attr('alt', 'Play video').data('src', data[0]['thumbnail_large'] );
//						}else{
                        $('<img>').appendTo( vpContainer ).addClass('ls-videopreview').attr('alt', 'Play video').attr('src', data[0]['thumbnail_large'] );
//						}
                        iframe.data( 'videoDuration', parseInt( data[0]['duration'] ) * 1000 );
                        $('<div>').appendTo( vpContainer ).addClass('ls-playvideo');
                    });


                    $(this).parent().css({
                        width : $(this).width(),
                        height : $(this).height()
                    }).click(function(){

                        // IMPROVEMENT v5.2.0 if video playing is in progress, video layers with auto play will skip showuntil feature

                        if( $(this).data('showuntil') > 0 && $(this).data('showUntilTimer') ){
                            clearTimeout( $(this).data('showUntilTimer') );
                        }

                        ls.g.isAnimating = true;

                        if( ls.g.paused ){
                            if( ls.o.autoPauseSlideshow != false ){
                                ls.g.paused = false;
                            }
                            ls.g.originalAutoSlideshow = true;
                        }else{
                            ls.g.originalAutoSlideshow = ls.g.autoSlideshow;
                        }

                        if( ls.o.autoPauseSlideshow != false ){
                            ls.stop();
                        }

                        ls.g.pausedByVideo = true;

                        http = $(this).find('iframe').data('videoSrc').indexOf('http') === -1 ? HTTP : '';

                        $(this).find('iframe').attr('src', http + $(this).find('iframe').data('videoSrc') );
                        $(this).find('.ls-vpcontainer').delay(ls.g.v.d).fadeOut(ls.g.v.fo, function(){
                            if( ls.o.autoPauseSlideshow == 'auto' && ls.g.originalAutoSlideshow == true ){
                                var videoTimer = setTimeout(function() {
                                    ls.start();
                                }, iframe.data( 'videoDuration') - ls.g.v.d );
                                iframe.data( 'videoTimer', videoTimer );
                            }
                            ls.g.isAnimating = false;
                            if( ls.g.resize == true ){
                                ls.makeResponsive( ls.g.curLayer, function(){
                                    ls.g.resize = false;
                                });
                            }
                        });
                    });

                    var sep = '&';

                    if( $(this).attr('src').indexOf('?') == -1 ){
                        sep = '?';
                    }

                    // BUGFIX v5.1.0 Fixed several issues with embedded videos (mostly under Firefox and IE)
                    // fixed 'only audio but no video' bug, fixed 'unclickable video controls' bug, fixed 'hidden slider controls' bug

                    var videoFix = '&wmode=opaque';

                    // BUGFIX v5.1.0 Fixed autoplay parameter

                    if( $(this).attr('src').indexOf('autoplay') == -1 ){
                        $(this).data( 'videoSrc', $(this).attr('src') + sep + 'autoplay=1' + videoFix );
                    }else{
                        $(this).data( 'videoSrc', $(this).attr('src').replace('autoplay=0','autoplay=1') + videoFix );
                    }

                    $(this).data( 'originalWidth', $(this).attr('width') );
                    $(this).data( 'originalHeight', $(this).attr('height') );
                    $(this).attr('src','');
                }
            });

            // NEW FEATURE v5.0.0 HTML5 Video Support

            $(el).find('video, audio').each(function(){

                // BUGFIX v5.1.0 fixed HTML5 video sizing issue (again :)

                var ow = typeof $(this).attr('width') !== 'undefined' ? $(this).attr('width') : '640';
                var oh = typeof $(this).attr('height') !== 'undefined' ? $(this).attr('height') : '' + $(this).height();

                if( ow.indexOf('%') === -1 ){
                    ow = parseInt( ow );
                }

                if( oh.indexOf('%') === -1 ){
                    oh = parseInt( oh );
                }

                if( ow === '100%' && ( oh === 0 || oh === '0' || oh === '100%' ) ){
                    $(this).attr('height', '100%');
                    oh = 'auto';
                }

                $(this).parent().addClass('ls-video-layer').css({
                    width : ow,
                    height : oh
                }).data({
                    originalWidth : ow,
                    originalHeight : oh
                });

                var curVideo = $(this);

                // BUGFIX v5.3.0 'ended' function removed from 'click' function due to multiply

                $(this).on('ended', function(){
                    if( ls.o.autoPauseSlideshow === 'auto' && ls.g.originalAutoSlideshow === true ){
                        ls.start();
                    }
                });

                $(this).removeAttr('width').removeAttr('height').css({
                    width : '100%',
                    height : '100%'
                }).click(function(e){

                    // BUGFIX v5.3.0 autoplay didn't work in all cases

                    if( !ls.g.pausedByVideo ){

                        if( this.paused ){
                            e.preventDefault();
                        }

                        this.play();

                        ls.g.isAnimating = true;

                        if( ls.g.paused ){
                            if( ls.o.autoPauseSlideshow !== false ){
                                ls.g.paused = false;
                            }
                            ls.g.originalAutoSlideshow = true;
                        }else{
                            ls.g.originalAutoSlideshow = ls.g.autoSlideshow;
                        }

                        if( ls.o.autoPauseSlideshow !== false ){
                            ls.stop();
                        }

                        ls.g.pausedByVideo = true;
                        ls.g.isAnimating = false;

                        if( ls.g.resize === true ){
                            ls.makeResponsive( ls.g.curLayer, function(){
                                ls.g.resize = false;
                            });
                        }
                    }
                });
            });

            // NEW FEATURE v1.7 animating first layer

            if( ls.o.animateFirstSlide ){
                ls.o.firstSlide = ls.o.firstSlide - 1 === 0 ? ls.g.layersNum : ls.o.firstSlide-1;
            }

            ls.g.curLayerIndex = ls.o.firstSlide;
            ls.g.curLayer = $(el).find('.ls-slide:eq('+(ls.g.curLayerIndex-1)+')');

            // Moving all layers to .ls-inner container

            $(el).find('.ls-slide').wrapAll('<div class="ls-inner"></div>');

            // NEW FEATURE v4.5.0 Timers

            if( ls.o.showBarTimer ){
                ls.g.barTimer = $('<div>').addClass('ls-bar-timer').appendTo( $(el).find('.ls-inner') );
            }

            if( ls.o.showCircleTimer && !ls.g.ie78 ){
                ls.g.circleTimer = $('<div>').addClass('ls-circle-timer').appendTo( $(el).find('.ls-inner') );
                ls.g.circleTimer.append( $('<div class="ls-ct-left"><div class="ls-ct-rotate"><div class="ls-ct-hider"><div class="ls-ct-half"></div></div></div></div><div class="ls-ct-right"><div class="ls-ct-rotate"><div class="ls-ct-hider"><div class="ls-ct-half"></div></div></div></div><div class="ls-ct-center"></div>') );
            }

            // NEW FEATURE v4.0 Adding loading indicator into the element

            ls.g.li = $('<div>').css({
                zIndex: -1,
                display: 'none'
            }).addClass('ls-loading-container').appendTo( $(el) );

            $('<div>').addClass('ls-loading-indicator').appendTo( ls.g.li );

            // Adding styles

            if( $(el).css('position') == 'static' ){
                $(el).css('position','relative');
            }

            // IMPROVEMENT & BUGFIX v4.6.0 Fixed transparent global background issue under IE7 & IE8

            if( ls.o.globalBGImage ){
                $(el).find('.ls-inner').css({
                    backgroundImage : 'url('+ls.o.globalBGImage+')'
                });
            }else{
                $(el).find('.ls-inner').css({
                    backgroundColor : ls.o.globalBGColor
                });
            }

            if( ls.o.globalBGColor == 'transparent' && ls.o.globalBGImage == false ){
                $(el).find('.ls-inner').css({
                    background : 'none transparent !important'
                });
            }

            // NEW FEATURES v5.0.0 Lazy-load & remove unnecessary width & height attributes from images

            $(el).find('.ls-slide img').each(function(){

                $(this).removeAttr('width').removeAttr('height');

                if( ls.o.imgPreload === true && ls.o.lazyLoad === true ){

                    if( typeof $(this).data('src') !== 'string' ){

                        $(this).data('src', $(this).attr('src') );
                        var src = ls.o.skinsPath+'../css/blank.gif';
                        $(this).attr('src',src);
                    }
                }else{
                    if( typeof $(this).data('src') === 'string' ){

                        $(this).attr('src',$(this).data('src'));
                        $(this).removeAttr('data-src');
                    }
                }

            });

            // NEW FEATURE v5.0.0 Parallax layers by mousemove

            $(el).find('.ls-slide').on('mouseenter',function(e){

                ls.g.parallaxStartX = e.pageX - $(this).parent().offset().left;
                ls.g.parallaxStartY = e.pageY - $(this).parent().offset().top;
            });

            $(el).find('.ls-slide').on('mousemove',function(e){

                var mX0 = $(this).parent().offset().left + ls.g.parallaxStartX;
                var mY0 = $(this).parent().offset().top + ls.g.parallaxStartY;

                var mX = e.pageX - mX0;
                var mY = e.pageY - mY0;

                $(this).find('> *:not(.ls-bg)').each(function(){

                    if( typeof $(this).data('parallaxlevel') !== 'undefined' && parseInt( $(this).data('parallaxlevel') ) !== 0 ){
                        $(this).css({
                            marginLeft : -mX / 100 * parseInt( $(this).data('parallaxlevel') ),
                            marginTop : -mY / 100 * parseInt( $(this).data('parallaxlevel') )
                        });
                    }
                });
            });

            $(el).find('.ls-slide').on('mouseleave',function(){

                $(this).find('> *:not(.ls-bg)').each(function(){

                    if( typeof $(this).data('parallaxlevel') !== 'undefined' && parseInt( $(this).data('parallaxlevel') ) !== 0 ){
                        TweenLite.to( this, .4, {css:{
                            marginLeft : 0,
                            marginTop : 0
                        }
                        });
                    }
                });
            });

            // Creating navigation

            if( ls.o.navPrevNext ){

                $('<a class="ls-nav-prev" href="#" />').click(function(e){
                    e.preventDefault();
                    $(el).layerSlider('prev');
                }).appendTo($(el));

                $('<a class="ls-nav-next" href="#" />').click(function(e){
                    e.preventDefault();
                    $(el).layerSlider('next');
                }).appendTo($(el));

                if( ls.o.hoverPrevNext ){
                    $(el).find('.ls-nav-prev, .ls-nav-next').css({
                        display: 'none'
                    });

                    $(el).hover(
                        function(){
                            if( !ls.g.forceHideControls ){
                                if( ls.g.ie78 ){
                                    $(el).find('.ls-nav-prev, .ls-nav-next').css('display','block');
                                }else{
                                    $(el).find('.ls-nav-prev, .ls-nav-next').stop(true,true).fadeIn(300);
                                }
                            }
                        },
                        function(){
                            if( ls.g.ie78 ){
                                $(el).find('.ls-nav-prev, .ls-nav-next').css('display','none');
                            }else{
                                $(el).find('.ls-nav-prev, .ls-nav-next').stop(true,true).fadeOut(300);
                            }
                        }
                    );
                }
            }

            // Creating bottom navigation

            if( ls.o.navStartStop || ls.o.navButtons ){

                var bottomNav = $('<div class="ls-bottom-nav-wrapper" />').appendTo( $(el) );

                ls.g.bottomWrapper = bottomNav;

                if( ls.o.thumbnailNavigation == 'always' ){
                    bottomNav.addClass('ls-above-thumbnails');
                }

                if( ls.o.navButtons && ls.o.thumbnailNavigation != 'always' ){

                    $('<span class="ls-bottom-slidebuttons" />').appendTo( $(el).find('.ls-bottom-nav-wrapper') );

                    // NEW FEATURE v3.5 thumbnailNavigation ('hover')

                    if( ls.o.thumbnailNavigation == 'hover' ){

                        var thumbs = $('<div class="ls-thumbnail-hover"><div class="ls-thumbnail-hover-inner"><div class="ls-thumbnail-hover-bg"></div><div class="ls-thumbnail-hover-img"><img></div><span></span></div></div>').appendTo( $(el).find('.ls-bottom-slidebuttons') );
                    }

                    for(x=1;x<ls.g.layersNum+1;x++){

                        var btn = $('<a href="#" />').appendTo( $(el).find('.ls-bottom-slidebuttons') ).click(function(e){
                            e.preventDefault();
                            $(el).layerSlider( ($(this).index() + 1) );
                        });

                        // NEW FEATURE v3.5 thumbnailNavigation ('hover')

                        if( ls.o.thumbnailNavigation == 'hover' ){

                            $(el).find('.ls-thumbnail-hover, .ls-thumbnail-hover-img').css({
                                width : ls.o.tnWidth,
                                height : ls.o.tnHeight
                            });

                            var th = $(el).find('.ls-thumbnail-hover');

                            var ti = th.find('img').css({
                                height : ls.o.tnHeight
                            });

                            var thi = $(el).find('.ls-thumbnail-hover-inner').css({
                                visibility : 'hidden',
                                display: 'block'
                            });

                            btn.hover(
                                function(){

                                    var hoverLayer = $(el).find('.ls-slide').eq( $(this).index() );
                                    var tnSrc;

                                    if( ls.o.imgPreload === true && ls.o.lazyLoad === true ){

                                        if( hoverLayer.find('.ls-tn').length ){
                                            tnSrc = hoverLayer.find('.ls-tn').data('src');
                                        }else if( hoverLayer.find('.ls-videopreview').length ){
                                            tnSrc = hoverLayer.find('.ls-videopreview').attr('src');
                                        }else if( hoverLayer.find('.ls-bg').length ){
                                            tnSrc = hoverLayer.find('.ls-bg').data('src');
                                        }else{
                                            tnSrc = ls.o.skinsPath+ls.o.skin+'/nothumb.png';
                                        }
                                    }else{

                                        if( hoverLayer.find('.ls-tn').length ){
                                            tnSrc = hoverLayer.find('.ls-tn').attr('src');
                                        }else if( hoverLayer.find('.ls-videopreview').length ){
                                            tnSrc = hoverLayer.find('.ls-videopreview').attr('src');
                                        }else if( hoverLayer.find('.ls-bg').length ){
                                            tnSrc = hoverLayer.find('.ls-bg').attr('src');
                                        }else{
                                            tnSrc = ls.o.skinsPath+ls.o.skin+'/nothumb.png';
                                        }
                                    }

                                    $(el).find('.ls-thumbnail-hover-img').css({
                                        left: parseInt( th.css('padding-left') ),
                                        top: parseInt( th.css('padding-top') )
                                    });

                                    ti.load(function(){

                                        if( $(this).width() == 0 ){
                                            ti.css({
                                                position: 'relative',
                                                margin: '0 auto',
                                                left: 'auto'
                                            });
                                        }else{
                                            ti.css({
                                                position: 'absolute',
                                                marginLeft : - $(this).width() / 2,
                                                left: '50%'
                                            });
                                        }
                                    }).attr( 'src', tnSrc );

                                    th.css({
                                        display: 'block'
                                    }).stop().animate({
                                        left: $(this).position().left + ( $(this).width() - th.outerWidth() ) / 2
                                    }, 250 );

                                    thi.css({
                                        display : 'none',
                                        visibility : 'visible'
                                    }).stop().fadeIn(250);
                                },
                                function(){
                                    thi.stop().fadeOut(250, function(){
                                        th.css({
                                            visibility : 'hidden',
                                            display: 'block'
                                        });
                                    });
                                }
                            );
                        }
                    }

                    if( ls.o.thumbnailNavigation == 'hover' ){

                        thumbs.appendTo( $(el).find('.ls-bottom-slidebuttons') );
                    }

                    $(el).find('.ls-bottom-slidebuttons a:eq('+(ls.o.firstSlide-1)+')').addClass('ls-nav-active');
                }

                if( ls.o.navStartStop ){

                    var buttonStart = $('<a class="ls-nav-start" href="#" />').click(function(e){
                        e.preventDefault();
                        $(el).layerSlider('start');
                    }).prependTo( $(el).find('.ls-bottom-nav-wrapper') );

                    var buttonStop = $('<a class="ls-nav-stop" href="#" />').click(function(e){
                        e.preventDefault();
                        $(el).layerSlider('stop');
                    }).appendTo( $(el).find('.ls-bottom-nav-wrapper') );

                }else if( ls.o.thumbnailNavigation != 'always' ){

                    $('<span class="ls-nav-sides ls-nav-sideleft" />').prependTo( $(el).find('.ls-bottom-nav-wrapper') );
                    $('<span class="ls-nav-sides ls-nav-sideright" />').appendTo( $(el).find('.ls-bottom-nav-wrapper') );
                }

                if( ls.o.hoverBottomNav && ls.o.thumbnailNavigation != 'always' ){

                    bottomNav.css({
                        display: 'none'
                    });

                    $(el).hover(
                        function(){
                            if( !ls.g.forceHideControls ){
                                if( ls.g.ie78 ){
                                    bottomNav.css('display','block');
                                }else{
                                    bottomNav.stop(true,true).fadeIn(300);
                                }
                            }
                        },
                        function(){
                            if( ls.g.ie78 ){
                                bottomNav.css('display','none');
                            }else{
                                bottomNav.stop(true,true).fadeOut(300);
                            }
                        }
                    )
                }
            }

            // NEW FEATURE v3x.5 thumbnailNavigation ('always')

            if( ls.o.thumbnailNavigation == 'always' ){

                ls.g.thumbsWrapper = $('<div class="ls-thumbnail-wrapper"></div>').appendTo( $(el) );
                var thumbs = $('<div class="ls-thumbnail"><div class="ls-thumbnail-inner"><div class="ls-thumbnail-slide-container"><div class="ls-thumbnail-slide"></div></div></div></div>').appendTo( ls.g.thumbsWrapper );

                ls.g.thumbnails = $(el).find('.ls-thumbnail-slide-container');

                if( !('ontouchstart' in window) ){
                    ls.g.thumbnails.hover(
                        function(){
                            $(this).addClass('ls-thumbnail-slide-hover');
                        },
                        function(){
                            $(this).removeClass('ls-thumbnail-slide-hover');
                            ls.scrollThumb();
                        }
                    ).mousemove(function(e){

                            var mL = parseInt(e.pageX - $(this).offset().left ) / $(this).width() * ( $(this).width() - $(this).find('.ls-thumbnail-slide').width() );
                            $(this).find('.ls-thumbnail-slide').stop().css({
                                marginLeft : mL
                            });
                        });
                }else{
                    ls.g.thumbnails.addClass('ls-touchscroll');
                }

                $(el).find('.ls-slide').each(function(){

                    var tempIndex = $(this).index() + 1;
                    var tnSrc;

                    if( ls.o.imgPreload === true && ls.o.lazyLoad === true ){

                        if( $(this).find('.ls-tn').length ){
                            tnSrc = $(this).find('.ls-tn').data('src');
                        }else if( $(this).find('.ls-videopreview').length ){
                            tnSrc = $(this).find('.ls-videopreview').attr('src');
                        }else if( $(this).find('.ls-bg').length ){
                            tnSrc = $(this).find('.ls-bg').data('src');
                        }else{
                            tnSrc = ls.o.skinsPath+ls.o.skin+'/nothumb.png';
                        }
                    }else{

                        if( $(this).find('.ls-tn').length ){
                            tnSrc = $(this).find('.ls-tn').attr('src');
                        }else if( $(this).find('.ls-videopreview').length ){
                            tnSrc = $(this).find('.ls-videopreview').attr('src');
                        }else if( $(this).find('.ls-bg').length ){
                            tnSrc = $(this).find('.ls-bg').attr('src');
                        }else{
                            tnSrc = ls.o.skinsPath+ls.o.skin+'/nothumb.png';
                        }
                    }

                    var thumb = $('<a href="#" class="ls-thumb-' + tempIndex + '"><img src="'+tnSrc+'"></a>');
                    thumb.appendTo( $(el).find('.ls-thumbnail-slide') );

                    if( !('ontouchstart' in window) ){

                        thumb.hover(
                            function(){
                                $(this).children().stop().fadeTo(300,ls.o.tnActiveOpacity/100);
                            },
                            function(){
                                if( !$(this).children().hasClass('ls-thumb-active') ){
                                    $(this).children().stop().fadeTo(300,ls.o.tnInactiveOpacity/100);
                                }
                            }
                        );
                    }

                    thumb.click(function(e){
                        e.preventDefault();
                        $(el).layerSlider( tempIndex );
                    });
                });

                if( buttonStart && buttonStop ){
                    var lsBottomBelowTN = ls.g.bottomWrapper = $('<div class="ls-bottom-nav-wrapper ls-below-thumbnails"></div>').appendTo( $(el) );
                    buttonStart.clone().click(function(e){
                        e.preventDefault();
                        $(el).layerSlider('start');
                    }).appendTo( lsBottomBelowTN );
                    buttonStop.clone().click(function(e){
                        e.preventDefault();
                        $(el).layerSlider('stop');
                    }).appendTo( lsBottomBelowTN );
                }

                if( ls.o.hoverBottomNav ){

                    ls.g.thumbsWrapper.css('display','none');

                    if( lsBottomBelowTN ){
                        ls.g.bottomWrapper = lsBottomBelowTN.css('display') == 'block' ? lsBottomBelowTN : $(el).find('.ls-above-thumbnails');
                        ls.g.bottomWrapper.css('display','none');
                    }

                    // BUGFIXES v4.1.3 Added checking of the bottomWrapper variable

                    $(el).hover(
                        function(){
                            $(el).addClass('ls-hover');
                            if( !ls.g.forceHideControls ){
                                if( ls.g.ie78 ){
                                    ls.g.thumbsWrapper.css('display','block');
                                    if( ls.g.bottomWrapper ){
                                        ls.g.bottomWrapper.css('display','block');
                                    }
                                }else{
                                    ls.g.thumbsWrapper.stop(true,true).fadeIn(300);
                                    if( ls.g.bottomWrapper ){
                                        ls.g.bottomWrapper.stop(true,true).fadeIn(300);
                                    }
                                }
                            }
                        },
                        function(){
                            $(el).removeClass('ls-hover');
                            if( ls.g.ie78 ){
                                ls.g.thumbsWrapper.css('display','none');
                                if( ls.g.bottomWrapper ){
                                    ls.g.bottomWrapper.css('display','none');
                                }
                            }else{
                                ls.g.thumbsWrapper.stop(true,true).fadeOut(300);
                                if( ls.g.bottomWrapper ){
                                    ls.g.bottomWrapper.stop(true,true).fadeOut(300);
                                }
                            }
                        }
                    )
                }
            }

            // Adding shadow wrapper

            ls.g.shadow = $('<div class="ls-shadow"></div>').appendTo( $(el) );
            if( ls.g.shadow.css('display') == 'block' && !ls.g.shadow.find('img').length ){
                ls.g.showShadow = function(){
                    ls.g.shadow.css({
                        display: 'none',
                        visibility: 'visible'
                    }).fadeIn( 500, function(){
                        ls.g.showShadow = false;
                    });
                }
                ls.g.shadowImg = $('<img>').attr('src',ls.o.skinsPath+ls.o.skin+'/shadow.png').appendTo( ls.g.shadow );
                ls.g.shadowBtmMod = typeof parseInt( $(el).css('padding-bottom') ) == 'number' ? parseInt( $(el).css('padding-bottom') ) : 0;
            }
            ls.resizeShadow();

            // Adding keyboard navigation if turned on and if number of layers > 1

            if( ls.o.keybNav && $(el).find('.ls-slide').length > 1 ){

                $('body').bind('keydown',function(e){
                    if( !ls.g.isAnimating && !ls.g.isLoading ){
                        if( e.which == 37 ){
                            ls.o.cbPrev(ls.g);
                            ls.prev('clicked');
                        }else if( e.which == 39 ){
                            ls.o.cbNext(ls.g);
                            ls.next('clicked');
                        }
                    }
                });
            }

            // Adding touch-control navigation if number of layers > 1

            if('ontouchstart' in window && $(el).find('.ls-slide').length > 1 && ls.o.touchNav ){

                $(el).find('.ls-inner').bind('touchstart', function( e ) {
                    var t = e.touches ? e.touches : e.originalEvent.touches;
                    if( t.length == 1 ){
                        ls.g.touchStartX = ls.g.touchEndX = t[0].clientX;
                    }
                });

                $(el).find('.ls-inner').bind('touchmove', function( e ) {
                    var t = e.touches ? e.touches : e.originalEvent.touches;
                    if( t.length == 1 ){
                        ls.g.touchEndX = t[0].clientX;
                    }
                    if( Math.abs( ls.g.touchStartX - ls.g.touchEndX ) > 45 ){
                        e.preventDefault();
                    }
                });

                $(el).find('.ls-inner').bind('touchend',function( e ){
                    if( Math.abs( ls.g.touchStartX - ls.g.touchEndX ) > 45 ){
                        if( ls.g.touchStartX - ls.g.touchEndX > 0 ){
                            ls.o.cbNext(ls.g);
                            $(el).layerSlider('next');
                        }else{
                            ls.o.cbPrev(ls.g);
                            $(el).layerSlider('prev');
                        }
                    }
                });
            }

            // Feature: pauseOnHover (if number of layers > 1)

            if( ls.o.pauseOnHover == true && $(el).find('.ls-slide').length > 1 ){

                // BUGFIX v1.6 stop was not working because of pause on hover

                $(el).find('.ls-inner').hover(
                    function(){

                        // Calling cbPause callback function

                        ls.o.cbPause(ls.g);
                        if( ls.g.autoSlideshow ){
                            ls.g.paused = true;
                            ls.stop();

                            // Stopping the animation of Timers

                            if( ls.g.barTimer ){
                                ls.g.barTimer.stop();
                            }

                            if( ls.g.circleTimer ){
                                if( ls.g.cttl ){
                                    ls.g.cttl.pause();
                                }
                            }
                            ls.g.pausedSlideTime = new Date().getTime();
                        }
                    },
                    function(){
                        if( ls.g.paused == true ){
                            ls.start();
                            ls.g.paused = false;
                        }
                    }
                );
            }

            ls.resizeSlider();

            // NEW FEATURE v1.7 added yourLogo

            if( ls.o.yourLogo ){
                ls.g.yourLogo = $('<img>').addClass('ls-yourlogo').appendTo($(el)).attr('style', ls.o.yourLogoStyle ).css({
                    visibility: 'hidden',
                    display: 'bock'
                }).load(function(){

                    // NEW FEATURE v3.0 added responsive yourLogo

                    var logoTimeout = 0;

                    if( !ls.g.yourLogo ){
                        logoTimeout = 1000;
                    }

                    setTimeout( function(){

                        ls.g.yourLogo.data( 'originalWidth', ls.g.yourLogo.width() );
                        ls.g.yourLogo.data( 'originalHeight', ls.g.yourLogo.height() );
                        if( ls.g.yourLogo.css('left') != 'auto' ){
                            ls.g.yourLogo.data( 'originalLeft', ls.g.yourLogo[0].style.left );
                        }
                        if( ls.g.yourLogo.css('right') != 'auto' ){
                            ls.g.yourLogo.data( 'originalRight', ls.g.yourLogo[0].style.right );
                        }
                        if( ls.g.yourLogo.css('top') != 'auto' ){
                            ls.g.yourLogo.data( 'originalTop', ls.g.yourLogo[0].style.top );
                        }
                        if( ls.g.yourLogo.css('bottom') != 'auto' ){
                            ls.g.yourLogo.data( 'originalBottom', ls.g.yourLogo[0].style.bottom );
                        }

                        // NEW FEATURES v1.8 added yourLogoLink & yourLogoTarget

                        if( ls.o.yourLogoLink != false ){
                            $('<a>').appendTo($(el)).attr( 'href', ls.o.yourLogoLink ).attr('target', ls.o.yourLogoTarget ).css({
                                textDecoration : 'none',
                                outline : 'none'
                            }).append( ls.g.yourLogo );
                        }

                        ls.g.yourLogo.css({
                            display: 'none',
                            visibility: 'visible'
                        });

                        ls.resizeYourLogo();

                    }, logoTimeout );

                }).attr( 'src', ls.o.yourLogo );
            }

            // NEW FEATURE v1.7 added window resize function for make responsive layout better

            $(window).resize(function(){

                ls.resize();
            });

            // BUGFIX v5.3.0 Responsiveness not worked in some cases while changed orientation on mobile devices

            $(window).on('orientationchange',function(){

                $(window).resize();
            });

            ls.g.showSlider = true;

            // NEW FEATURE v1.7 animating first slide

            if( ls.o.animateFirstSlide == true ){
                if( ls.o.autoStart ){
                    ls.g.autoSlideshow = true;
                    $(el).find('.ls-nav-start').addClass('ls-nav-start-active');
                }else{
                    $(el).find('.ls-nav-stop').addClass('ls-nav-stop-active');
                }
                ls.next();
            }else if( typeof ls.g.curLayer[0] !== 'undefined' ){
                ls.imgPreload(ls.g.curLayer,function(){
                    ls.g.curLayer.fadeIn(ls.o.sliderFadeInDuration, function(){

                        ls.g.isLoading = false;

                        $(this).addClass('ls-active');

                        // NEW FEATURE v2.0 autoPlayVideos

                        if( ls.o.autoPlayVideos ){
                            $(this).delay( $(this).data('delayin') + 25 ).queue(function(){

                                // YouTube & Vimeo videos

                                $(this).find('.ls-videopreview').click();

                                // HTML5 videos

                                $(this).find('video, audio').each(function(){
                                    if( typeof $(this)[0].currentTime !== 0){
                                        $(this)[0].currentTime = 0;
                                    }
                                    $(this).click();
                                });

                                $(this).dequeue();
                            });
                        }

                        // NEW FEATURE v3.0 showUntil sublayers

                        ls.g.curLayer.find(' > *[class*="ls-l"]').each(function(){

                            // Setting showUntilTimers

                            var cursub = $(this);

                            // IMPROVEMENT v5.2.0 video layers with auto play will skip showuntil feature

                            if( ( !cursub.hasClass('ls-video-layer') || ( cursub.hasClass('ls-video-layer') && ls.o.autoPlayVideos === false ) ) && cursub.data('showuntil') > 0 ){

                                // IMPROVEMENT v4.5.0 sublayerShowUntil will be called anly if necessary

                                cursub.data('showUntilTimer', setTimeout(function(){
                                    ls.sublayerShowUntil( cursub );
                                }, cursub.data('showuntil') ));
                            }
                        });
                    });

                    ls.changeThumb(ls.g.curLayerIndex)

                    // If autoStart is true

                    if( ls.o.autoStart ){
                        ls.g.isLoading = false;
                        ls.start();
                    }else{
                        $(el).find('.ls-nav-stop').addClass('ls-nav-stop-active');
                    }
                });
            }

            // NEW FEATURE v1.7 added cbInit function

            ls.o.cbInit($(el));
        };

        ls.resize = function(){

            ls.g.resize = true;

            if( !ls.g.isAnimating ){

                ls.makeResponsive( ls.g.curLayer, function(){
                    if( ls.g.ltContainer ){
                        ls.g.ltContainer.empty();
                    }
                    ls.g.resize = false;
                });
                if( ls.g.yourLogo ){
                    ls.resizeYourLogo();
                }
            }
        };

        ls.start = function(){

            if( ls.g.autoSlideshow ){
                if( ls.g.prevNext == 'prev' && ls.o.twoWaySlideshow ){
                    ls.prev();
                }else{
                    ls.next();
                }
            }else{
                ls.g.autoSlideshow = true;
                if( !ls.g.isAnimating && !ls.g.isLoading ){
                    ls.timer();
                }
            }

            $(el).find('.ls-nav-start').addClass('ls-nav-start-active');
            $(el).find('.ls-nav-stop').removeClass('ls-nav-stop-active');
        };

        ls.timer = function(){

            if( $(el).find('.ls-active').data('ls') ){
                var sD = ls.st.slideDelay;
            }else{
                var sD = ls.o.slideDelay;
            }

            var delaytime = $(el).find('.ls-active').data('slidedelay') ? parseInt( $(el).find('.ls-active').data('slidedelay') ) : sD;

            // BUGFIX v3.0 delaytime did not work on first layer if animateFirstSlide was set to off
            // BUGFIX v3.5 delaytime did not work on all layers in standalone version after bugfix 3.0 :)

            if( !ls.o.animateFirstSlide && !$(el).find('.ls-active').data('slidedelay') ){
                var tempD = $(el).find('.ls-slide:eq('+(ls.o.firstSlide-1)+')').data('slidedelay');
                delaytime = tempD ? tempD : sD;
            }

            clearTimeout( ls.g.slideTimer );

            // NEW FEATURE v4.5.0 Timers

            if( ls.g.pausedSlideTime ){
                if( !ls.g.startSlideTime ){
                    ls.g.startSlideTime = new Date().getTime();
                }
                if( ls.g.startSlideTime > ls.g.pausedSlideTime ){
                    ls.g.pausedSlideTime =  new Date().getTime();
                }
                if(! ls.g.curSlideTime ){
                    ls.g.curSlideTime = delaytime;
                }
                ls.g.curSlideTime -= (ls.g.pausedSlideTime - ls.g.startSlideTime);
                ls.g.pausedSlideTime = false;
                ls.g.startSlideTime = new Date().getTime();
            }else{
                ls.g.curSlideTime = delaytime;
                ls.g.startSlideTime = new Date().getTime();
            }

            // BUGFIX v4.6.0 fixed Bar Timer animation on the fisrt slide if animateFirstSlide is false

            ls.g.curSlideTime = parseInt( ls.g.curSlideTime );

            ls.g.slideTimer = setTimeout(function(){
                ls.g.startSlideTime = ls.g.pausedSlideTime = ls.g.curSlideTime = false;
                ls.start();
            }, ls.g.curSlideTime );

            // Animating Timers

            if( ls.g.barTimer ){
                ls.g.barTimer.animate({
                    width : ls.g.sliderWidth()
                }, ls.g.curSlideTime, 'linear', function(){
                    $(this).css({
                        width: 0
                    });
                });
            }

            if( ls.g.circleTimer ){

                var ct1 = ls.g.circleTimer.find('.ls-ct-right .ls-ct-rotate');
                var ct2 = ls.g.circleTimer.find('.ls-ct-left .ls-ct-rotate');

                if( ls.g.circleTimer.css('display') == 'none' ){

                    ct1.css({
                        rotate : 0
                    });

                    ct2.css({
                        rotate : 0
                    });

                    ls.g.circleTimer.fadeIn(350);
                }

                if( !ls.g.cttl ){
                    ls.g.cttl = new TimelineLite();
                    ls.g.cttl.add( TweenLite.fromTo(ct1[0],delaytime/2000,{
                        rotation : 0
                    },{
                        ease : Linear.easeNone,
                        rotation : 180,
                        onReverseComplete : function(){
                            ls.g.cttl = false;
                        }
                    }));
                    ls.g.cttl.add( TweenLite.fromTo(ct2[0],delaytime/2000,{
                        rotation : 0
                    },{
                        ease : Linear.easeNone,
                        rotation : 180
                    }));
                }else{
                    ls.g.cttl.resume();
                }

            }
        };

        ls.stop = function(){

            // Stopping Timers

            ls.g.pausedSlideTime = new Date().getTime();

            if( ls.g.barTimer ){
                ls.g.barTimer.stop();
            }

            if( ls.g.circleTimer ){
                if( ls.g.cttl ){
                    ls.g.cttl.pause();
                }
            }

            if( !ls.g.paused && !ls.g.originalAutoSlideshow ){
                $(el).find('.ls-nav-stop').addClass('ls-nav-stop-active');
                $(el).find('.ls-nav-start').removeClass('ls-nav-start-active');
            }
            clearTimeout( ls.g.slideTimer );
            ls.g.autoSlideshow = false;
        };

        ls.forcestop = function(){

            clearTimeout( ls.g.slideTimer );
            ls.g.autoSlideshow = false;

            clearTimeout( ls.g.t1 );
            clearTimeout( ls.g.t2 );
            clearTimeout( ls.g.t3 );
            clearTimeout( ls.g.t4 );
            clearTimeout( ls.g.t5 );

            if( ls.g.barTimer ){
                ls.g.barTimer.stop();
            }

            if( ls.g.circleTimer ){
                if( ls.g.cttl ){
                    ls.g.cttl.pause();
                }
            }

            $(el).find('*').stop(true,false).dequeue();
            $(el).find('.ls-slide >').each(function(){
                if( $(this).data('tr') ){
                    $(this).data('tr').pause();
                }
            });

            if( !ls.g.paused && !ls.g.originalAutoSlideshow ){
                $(el).find('.ls-nav-stop').addClass('ls-nav-stop-active');
                $(el).find('.ls-nav-start').removeClass('ls-nav-start-active');
            }
        };

        ls.restart = function(){

            $(el).find('*').stop();
            clearTimeout( ls.g.slideTimer );
            ls.change(ls.g.curLayerIndex,ls.g.prevNext);
        };

        // Because of an ie7 bug, we have to check & format the strings correctly

        ls.ieEasing = function( e ){

            // BUGFIX v1.6 and v1.8 some type of animations didn't work properly

            if( $.trim(e.toLowerCase()) == 'swing' || $.trim(e.toLowerCase()) == 'linear'){
                return e.toLowerCase();
            }else{
                return e.replace('easeinout','easeInOut').replace('easein','easeIn').replace('easeout','easeOut').replace('quad','Quad').replace('quart','Quart').replace('cubic','Cubic').replace('quint','Quint').replace('sine','Sine').replace('expo','Expo').replace('circ','Circ').replace('elastic','Elastic').replace('back','Back').replace('bounce','Bounce');
            }
        };

        // Calculating prev layer

        ls.prev = function(clicked){

            // NEW FEATURE v2.0 loops

            if( ls.g.curLayerIndex < 2 ){
                ls.g.nextLoop += 1;
            }

            if( ( ls.g.nextLoop > ls.o.loops ) && ( ls.o.loops > 0 ) && !clicked ){
                ls.g.nextLoop = 0;
                ls.stop();
                if( ls.o.forceLoopNum == false ){
                    ls.o.loops = 0;
                }
            }else{
                var prev = ls.g.curLayerIndex < 2 ? ls.g.layersNum : ls.g.curLayerIndex - 1;
                ls.g.prevNext = 'prev';
                ls.change(prev,ls.g.prevNext);
            }
        };

        // Calculating next layer

        ls.next = function(clicked){

            // NEW FEATURE v2.0 loops

            if( !ls.o.randomSlideshow ){

                if( !(ls.g.curLayerIndex < ls.g.layersNum) ){
                    ls.g.nextLoop += 1;
                }

                if( ( ls.g.nextLoop > ls.o.loops ) && ( ls.o.loops > 0 ) && !clicked ){

                    ls.g.nextLoop = 0;
                    ls.stop();
                    if( ls.o.forceLoopNum == false ){
                        ls.o.loops = 0;
                    }
                }else{

                    var next = ls.g.curLayerIndex < ls.g.layersNum ? ls.g.curLayerIndex + 1 : 1;
                    ls.g.prevNext = 'next';
                    ls.change(next,ls.g.prevNext);
                }
            }else if( !clicked ){

                // NEW FEATURE v3.5 randomSlideshow

                var next = ls.g.curLayerIndex;

                var calcRand = function(){

                    next = Math.floor(Math.random() * ls.g.layersNum) + 1;

                    if( next == ls.g.curLayerIndex ){

                        calcRand();
                    }else{
                        ls.g.prevNext = 'next';
                        ls.change(next,ls.g.prevNext);
                    }
                }

                calcRand();
            }else if( clicked ){

                var next = ls.g.curLayerIndex < ls.g.layersNum ? ls.g.curLayerIndex + 1 : 1;
                ls.g.prevNext = 'next';
                ls.change(next,ls.g.prevNext);
            }

        };

        ls.change = function(num,prevnext){

            // Stopping Timers if needed

            ls.g.startSlideTime = ls.g.pausedSlideTime = ls.g.curSlideTime = false;

            // IMPROVEMENT v4.6.0 Bar Timer animation

            if( ls.g.barTimer ){
                ls.g.barTimer.stop().delay(300).animate({
                    width: 0
                },450);
            }
            if( ls.g.circleTimer ){
                ls.g.circleTimer.fadeOut(500);
                if( ls.g.cttl ){
                    ls.g.cttl.reverse().duration(.35);
                }
            }

            // NEW FEATURE v2.0 videoPreview & autoPlayVideos

            if( ls.g.pausedByVideo == true ){
                ls.g.pausedByVideo = false;
                ls.g.autoSlideshow = ls.g.originalAutoSlideshow;

                ls.g.curLayer.find('iframe[src*="youtube.com"], iframe[src*="youtu.be"], iframe[src*="player.vimeo"]').each(function(){

                    $(this).parent().find('.ls-vpcontainer').fadeIn(ls.g.v.fi,function(){
                        $(this).parent().find('iframe').attr('src','');
                    });
                });

                ls.g.curLayer.find('video, audio').each(function(){

                    this.pause();
                });
            }

            $(el).find('iframe[src*="youtube.com"], iframe[src*="youtu.be"], iframe[src*="player.vimeo"]').each(function(){

                // Clearing videoTimeouts

                clearTimeout( $(this).data( 'videoTimer') );
            });

            clearTimeout( ls.g.slideTimer );
            ls.g.nextLayerIndex = num;
            ls.g.nextLayer = $(el).find('.ls-slide:eq('+(ls.g.nextLayerIndex-1)+')');

            // BUGFIX v1.6 fixed wrong directions of animations if navigating by slidebuttons

            if( !prevnext ){

                if( ls.g.curLayerIndex < ls.g.nextLayerIndex ){
                    ls.g.prevNext = 'next';
                }else{
                    ls.g.prevNext = 'prev';
                }
            }

            // Added timeOut to wait for the fade animation of videoPreview image...

            var timeOut = 0;

            if( $(el).find('iframe[src*="youtube.com"], iframe[src*="youtu.be"], iframe[src*="player.vimeo"]').length > 0 ){
                timeOut = ls.g.v.fi;
            }

            if( typeof ls.g.nextLayer[0] !== 'undefined' ){
                ls.imgPreload(ls.g.nextLayer,function(){
                    ls.animate();
                });
            }
        };

        // Preloading images

        ls.imgPreload = function(layer,callback){

            ls.g.isLoading = true;

            // Showing slider for the first time

            if( ls.g.showSlider ){
                $(el).css({
                    visibility : 'visible'
                });
            }

            // If image preload is on

            if( ls.o.imgPreload ){

                var preImages = [];
                var preloaded = 0;

                // NEW FEATURE v1.8 Preloading background images of layers

                if( layer.css('background-image') != 'none' && layer.css('background-image').indexOf('url') != -1 && !layer.hasClass('ls-preloaded') && !layer.hasClass('ls-not-preloaded') ){
                    var bgi = layer.css('background-image');
                    bgi = bgi.match(/url\((.*)\)/)[1].replace(/"/gi, '');
                    preImages[preImages.length] = [bgi, layer];
                }

                // Images inside layers

                layer.find('img:not(.ls-preloaded, .ls-not-preloaded)').each(function(){

                    // NEW FEATURE v5.0.0 Lazy-load

                    if( ls.o.lazyLoad === true ){
                        $(this).attr('src',$(this).data('src'));
                    }
                    preImages[preImages.length] = [$(this).attr('src'), $(this)];
                });

                // Background images inside layers

                layer.find('*').each(function(){

                    // BUGFIX v1.7 fixed preload bug with sublayers with gradient backgrounds

                    if( $(this).css('background-image') != 'none' && $(this).css('background-image').indexOf('url') != -1 && !$(this).hasClass('ls-preloaded') && !$(this).hasClass('ls-not-preloaded') ){
                        var bgi = $(this).css('background-image');
                        bgi = bgi.match(/url\((.*)\)/)[1].replace(/"/gi, '');
                        preImages[preImages.length] = [bgi, $(this)];
                    }
                });

                // BUGFIX v1.7 if there are no images in a layer, calling the callback function

                if(preImages.length == 0){

                    $('.ls-thumbnail-wrapper, .ls-nav-next, .ls-nav-prev, .ls-bottom-nav-wrapper').css({
                        visibility : 'visible'
                    });

                    ls.makeResponsive(layer, callback);
                }else{

                    // NEW FEATURE v4.0 Showing loading indicator

                    if( ls.g.ie78 ){
                        ls.g.li.css('display','block');
                    }else{

                        // BUGIFX v4.1.3 Adding delay to the showing of the loading indicator

                        ls.g.li.delay(400).fadeIn(300);
                    }

                    var afterImgLoad = function(){

                        // NEW FEATURE v4.0 Hiding loading indicator

                        ls.g.li.stop(true,true).css({
                            display: 'none'
                        });

                        $('.ls-thumbnail-wrapper, .ls-nav-next, .ls-nav-prev, .ls-bottom-nav-wrapper').css({
                            visibility : 'visible'
                        });

                        // We love you so much IE... -.-

                        if( navigator.userAgent.indexOf('Trident/7') !== -1 || ls.g.ie78 ){
                            setTimeout(function(){
                                ls.makeResponsive(layer, callback);
                            },50);
                        }else{
                            ls.makeResponsive(layer, callback);
                        }

                    };

                    for(x=0;x<preImages.length;x++){

                        $('<img>').data('el',preImages[x]).load(function(){

                            $(this).data('el')[1].addClass('ls-preloaded');

                            if( ++preloaded == preImages.length ){

                                afterImgLoad();
                            }
                        }).error(function(){
                            var imgURL = $(this).data('el')[0].substring($(this).data('el')[0].lastIndexOf("/") + 1, $(this).data('el')[0].length);
                            if( window.console ){
                                console.log('LayerSlider error:\r\n\r\nIt seems like the URL of the image or background image "'+imgURL+'" is pointing to a wrong location and it cannot be loaded. Please check the URLs of all your images used in the slider.');
                            }else{
                                alert('LayerSlider error:\r\n\r\nIt seems like the URL of the image or background image "'+imgURL+'" is pointing to a wrong location and it cannot be loaded. Please check the URLs of all your images used in the slider.');
                            }

                            $(this).addClass('ls-not-preloaded');

                            // IMPROVEMENT v5.2.0 The slider should not stop even if an image cannot be loaded

                            if( ++preloaded == preImages.length ){

                                afterImgLoad();
                            }

                        }).attr('src',preImages[x][0]);
                    }
                }
            }else{

                $('.ls-thumbnail-wrapper, .ls-nav-next, .ls-nav-prev, .ls-bottom-nav-wrapper').css({
                    visibility : 'visible'
                });

                ls.makeResponsive(layer, callback);
            }
        };

        // NEW FEATURE v1.7 making the slider responsive

        ls.makeResponsive = function(layer, callback ){

            layer.css({
                visibility: 'hidden',
                display: 'block'
            });

            if( ls.g.showShadow ){
                ls.g.showShadow();
            }

            ls.resizeSlider();

            if( ls.o.thumbnailNavigation == 'always' ){
                ls.resizeThumb();
            }
            layer.children().each(function(){

                var sl = $(this);

                // positioning

                var ol = sl.data('originalLeft') ? sl.data('originalLeft') : '0';
                var ot = sl.data('originalTop') ? sl.data('originalTop') : '0';

                if( sl.is('a') && sl.children().length > 0 ){
                    sl.css({
                        display : 'block'
                    });
                    sl = sl.children();
                }

                var ow = 'auto';
                var oh = 'auto';

                if( sl.data('originalWidth') ){

                    if( typeof sl.data('originalWidth') == 'number' ){
                        ow = parseInt( sl.data('originalWidth') ) * ls.g.ratio;
                    }else if( sl.data('originalWidth').indexOf('%') != -1 ){
                        ow = sl.data('originalWidth');
                    }
                }

                if( sl.data('originalHeight') ){
                    if( typeof sl.data('originalHeight') == 'number' ){
                        oh = parseInt( sl.data('originalHeight') ) * ls.g.ratio;
                    }else if( sl.data('originalHeight').indexOf('%') != -1 ){
                        oh = sl.data('originalHeight');
                    }
                }

                // padding

                var opl = sl.data('originalPaddingLeft') ? parseInt( sl.data('originalPaddingLeft') ) * ls.g.ratio : 0;
                var opr = sl.data('originalPaddingRight') ? parseInt( sl.data('originalPaddingRight') ) * ls.g.ratio : 0;
                var opt = sl.data('originalPaddingTop') ? parseInt( sl.data('originalPaddingTop') ) * ls.g.ratio : 0;
                var opb = sl.data('originalPaddingBottom') ? parseInt( sl.data('originalPaddingBottom') ) * ls.g.ratio : 0;

                // border

                var obl = sl.data('originalBorderLeft') ? parseInt( sl.data('originalBorderLeft') ) * ls.g.ratio : 0;
                var obr = sl.data('originalBorderRight') ? parseInt( sl.data('originalBorderRight') ) * ls.g.ratio : 0;
                var obt = sl.data('originalBorderTop') ? parseInt( sl.data('originalBorderTop') ) * ls.g.ratio : 0;
                var obb = sl.data('originalBorderBottom') ? parseInt( sl.data('originalBorderBottom') ) * ls.g.ratio : 0;

                // font

                var ofs = sl.data('originalFontSize');
                var olh = sl.data('originalLineHeight');

                // NEW FEATURE v3.0 added "normal" responsive mode with image and font resizing
                // NEW FEATURE v3.5 added responsiveUnder

                if( ls.g.responsiveMode || ls.o.responsiveUnder > 0 ){

                    if( sl.is('img') && !sl.hasClass('ls-bg') && sl.attr('src') ){

                        sl.css({
                            width: 'auto',
                            height: 'auto'
                        });

                        // IMPROVEMENT v4.5.0 Images can have now starting width / height

                        if( ( ow == 0 || ow == 'auto' ) && typeof oh == 'number' && oh != 0 ){
                            ow = ( oh / sl.height() ) * sl.width();
                        }

                        if( ( oh == 0 || oh == 'auto' ) && typeof ow == 'number' && ow != 0 ){
                            oh = ( ow / sl.width() ) * sl.height();
                        }

                        if( ow == 'auto'){
                            ow = sl.width() * ls.g.ratio;
                        }

                        if( oh == 'auto'){
                            oh = sl.height() * ls.g.ratio;
                        }

                        sl.css({
                            width : ow,
                            height : oh
                        });
                    }

                    if( !sl.is('img') ){
                        sl.css({
                            width : ow,
                            height : oh,
                            'font-size' : parseInt(ofs) * ls.g.ratio +'px',
                            'line-height' : parseInt(olh) * ls.g.ratio + 'px'
                        });
                    }

                    if( sl.is('div') && sl.find('iframe').data('videoSrc') ){

                        var videoIframe = sl.find('iframe');
                        videoIframe.attr('width', parseInt( videoIframe.data('originalWidth') ) * ls.g.ratio ).attr('height', parseInt( videoIframe.data('originalHeight') ) * ls.g.ratio );

                        sl.css({
                            width : parseInt( videoIframe.data('originalWidth') ) * ls.g.ratio,
                            height : parseInt( videoIframe.data('originalHeight') ) * ls.g.ratio
                        });
                    }

                    sl.css({
                        padding : opt + 'px ' + opr + 'px ' + opb + 'px ' + opl + 'px ',
                        borderLeftWidth : obl + 'px',
                        borderRightWidth : obr + 'px',
                        borderTopWidth : obt + 'px',
                        borderBottomWidth : obb + 'px'
                    });
                }

                // If it is NOT a bg sublayer

                if( !sl.hasClass('ls-bg') ){

                    var sl2 = sl;

                    if( sl.parent().is('a') ){
                        sl = sl.parent();
                    }

                    // NEW FEATURE v3.5 sublayerContainer

                    var slC = 0;
                    if( ls.o.layersContainer ){
                        slC = ls.o.layersContainer > 0 ? ( ls.g.sliderWidth() - ls.o.layersContainer ) / 2 : 0;
                    }else if( ls.o.sublayerContainer ){
                        slC = ls.o.sublayerContainer > 0 ? ( ls.g.sliderWidth() - ls.o.sublayerContainer ) / 2 : 0;
                    }
                    slC = slC < 0 ? 0 : slC;

                    // (RE)positioning sublayer (left property)

                    if( ol.indexOf('%') != -1 ){
                        sl.css({
                            left : ls.g.sliderWidth() / 100 * parseInt(ol) - sl2.width() / 2 - opl - obl
                        });
                    }else if( slC > 0 || ls.g.responsiveMode || ls.o.responsiveUnder > 0 ){
                        sl.css({
                            left : slC + parseInt(ol) * ls.g.ratio
                        });
                    }

                    // (RE)positioning sublayer (top property)

                    if( ot.indexOf('%') != -1 ){
                        sl.css({
                            top : ls.g.sliderHeight() / 100 * parseInt(ot) - sl2.height() / 2 - opt - obt
                        });
                    }else if( ls.g.responsiveMode || ls.o.responsiveUnder > 0 ){
                        sl.css({
                            top : parseInt(ot) * ls.g.ratio
                        });
                    }

                }else{

                    var inner = $(el).find('.ls-inner');

                    sl.css({
                        width : 'auto',
                        height : 'auto'
                    });

                    ow = sl.width();
                    oh = sl.height();

                    // IMPROVEMENT v4.5.0 Resizing smaller background images in full width mode as well to fill the whole slide

                    var or = ls.g.ratio;

                    if( ls.g.sliderOriginalWidth.indexOf('%') != -1 ){
                        if( ls.g.sliderWidth() > ow ){
                            or = ls.g.sliderWidth() / ow;
                            if( ls.g.sliderHeight() > oh * or ){
                                or = ls.g.sliderHeight() / oh;
                            }
                        }else if( ls.g.sliderHeight() > oh ){
                            or = ls.g.sliderHeight() / oh;
                            if( ls.g.sliderWidth() > ow * or ){
                                or = ls.g.sliderWidth() / ow;
                            }
                        }
                    }

                    sl.css({
                        width : ow * or,
                        height : oh * or,
                        marginLeft : inner.width() / 2 - ow * or / 2,
                        marginTop : inner.height() / 2 - oh * or / 2
                    });
//					$('#w2 span:eq(0)').html( ( inner.width() / 2 ) - Math.round( ow * or / 2 ) );
                }
            });

            layer.css({
                display: 'none',
                visibility: 'visible'
            });

            // Resizing shadow

            ls.resizeShadow();

            callback();

            $(this).dequeue();
        };

        // Resizing shadow

        ls.resizeShadow = function(){
            if( ls.g.shadowImg ){
                var resizeShadow = function(){
                    if( ls.g.shadowImg.height() > 0 ){
                        if( ls.g.shadowBtmMod > 0 ){
                            ls.g.shadow.css({
                                height: ls.g.shadowImg.height() / 2
                            });
                        }else{
                            ls.g.shadow.css({
                                height: ls.g.shadowImg.height(),
                                marginTop: - ls.g.shadowImg.height() / 2
                            });
                        }
                    }else{
                        setTimeout(function(){
                            resizeShadow();
                        },50);
                    }
                };

                resizeShadow();
            }
        };

        // Resizing the slider

        ls.resizeSlider = function(){

            if( ls.o.responsiveUnder > 0 ){

                if( $(window).width() < ls.o.responsiveUnder ){
                    ls.g.responsiveMode = true;
                    ls.g.sliderOriginalWidth = ls.o.responsiveUnder + 'px';
                }else{
                    ls.g.responsiveMode = false;
                    ls.g.sliderOriginalWidth = ls.g.sliderOriginalWidthRU;
                    ls.g.ratio = 1;
                }
            }

            // BUGFIX 5.3.0 Fixed full-width resize issue

            if( $(el).closest('.ls-wp-fullwidth-container').length ){

                $(el).closest('.ls-wp-fullwidth-helper').css({
                    width : $(window).width()
                });
            }

            // NEW FEATURE v3.0 added "normal" responsive mode with image and font resizing

            if( ls.g.responsiveMode ){

                var parent = $(el).parent();

                // NEW FEATURE v5.5.0 Added fullScreen mode

                if( ls.o.fullScreen === true ){

                    $(el).css({
                        width : '100%',
                        height : $(window).height()
                    });
                }else{

                    // BUGFIX v4.0 there is no need to subtract the values of the left and right paddings of the container element!

                    $(el).css({
                        width : parent.width() - parseInt($(el).css('padding-left')) - parseInt($(el).css('padding-right'))
                    });
                    ls.g.ratio = $(el).width() / parseInt( ls.g.sliderOriginalWidth );
                    $(el).css({
                        height : ls.g.ratio * parseInt( ls.g.sliderOriginalHeight )
                    });
                }

            }else{
                ls.g.ratio = 1;
                $(el).css({
                    width : ls.g.sliderOriginalWidth,
                    height : ls.g.sliderOriginalHeight
                });
            }

            // WP fullWidth mode (originally forceResponsive mode)

            if( $(el).closest('.ls-wp-fullwidth-container').length ){

                $(el).closest('.ls-wp-fullwidth-helper').css({
                    height : $(el).outerHeight(true)
                });

                $(el).closest('.ls-wp-fullwidth-container').css({
                    height : $(el).outerHeight(true)
                });

                $(el).closest('.ls-wp-fullwidth-helper').css({
                    width : $(window).width(),
                    left : - $(el).closest('.ls-wp-fullwidth-container').offset().left
                });

                if( ls.g.sliderOriginalWidth.indexOf('%') != -1 ){

                    var percentWidth = parseInt( ls.g.sliderOriginalWidth );
                    var newWidth = $('body').width() / 100 * percentWidth - ( $(el).outerWidth() - $(el).width() );
                    $(el).width( newWidth );
                }
            }

            $(el).find('.ls-inner, .ls-lt-container').css({
                width : ls.g.sliderWidth(),
                height : ls.g.sliderHeight()
            });

            // BUGFIX v2.0 fixed width problem if firstSlide is not 1

            if( ls.g.curLayer && ls.g.nextLayer ){

                ls.g.curLayer.css({
                    width : ls.g.sliderWidth(),
                    height : ls.g.sliderHeight()
                });

                ls.g.nextLayer.css({
                    width : ls.g.sliderWidth(),
                    height : ls.g.sliderHeight()
                });

            }else{

                $(el).find('.ls-slide').css({
                    width : ls.g.sliderWidth(),
                    height : ls.g.sliderHeight()
                });
            }
        };

        // NEW FEATURE v3.0 added responsive yourLogo

        ls.resizeYourLogo = function(){

            ls.g.yourLogo.css({
                width : ls.g.yourLogo.data( 'originalWidth' ) * ls.g.ratio,
                height : ls.g.yourLogo.data( 'originalHeight' ) * ls.g.ratio
            });

            if( ls.g.ie78 ){
                ls.g.yourLogo.css('display','block');
            }else{
                ls.g.yourLogo.fadeIn(300);
            }

            var oL = oR = oT = oB = 'auto';

            if( ls.g.yourLogo.data( 'originalLeft' ) && ls.g.yourLogo.data( 'originalLeft' ).indexOf('%') != -1 ){
                oL = ls.g.sliderWidth() / 100 * parseInt( ls.g.yourLogo.data( 'originalLeft' ) ) - ls.g.yourLogo.width() / 2 + parseInt( $(el).css('padding-left') );
            }else{
                oL = parseInt( ls.g.yourLogo.data( 'originalLeft' ) ) * ls.g.ratio;
            }

            if( ls.g.yourLogo.data( 'originalRight' ) && ls.g.yourLogo.data( 'originalRight' ).indexOf('%') != -1 ){
                oR = ls.g.sliderWidth() / 100 * parseInt( ls.g.yourLogo.data( 'originalRight' ) ) - ls.g.yourLogo.width() / 2 + parseInt( $(el).css('padding-right') );
            }else{
                oR = parseInt( ls.g.yourLogo.data( 'originalRight' ) ) * ls.g.ratio;
            }

            if( ls.g.yourLogo.data( 'originalTop' ) && ls.g.yourLogo.data( 'originalTop' ).indexOf('%') != -1 ){
                oT = ls.g.sliderHeight() / 100 * parseInt( ls.g.yourLogo.data( 'originalTop' ) ) - ls.g.yourLogo.height() / 2 + parseInt( $(el).css('padding-top') );
            }else{
                oT = parseInt( ls.g.yourLogo.data( 'originalTop' ) ) * ls.g.ratio;
            }

            if( ls.g.yourLogo.data( 'originalBottom' ) && ls.g.yourLogo.data( 'originalBottom' ).indexOf('%') != -1 ){
                oB = ls.g.sliderHeight() / 100 * parseInt( ls.g.yourLogo.data( 'originalBottom' ) ) - ls.g.yourLogo.height() / 2 + parseInt( $(el).css('padding-bottom') );
            }else{
                oB = parseInt( ls.g.yourLogo.data( 'originalBottom' ) ) * ls.g.ratio;
            }

            ls.g.yourLogo.css({
                left : oL,
                right : oR,
                top : oT,
                bottom : oB
            });
        };

        // NEW FEATURE v3.5 thumbnailNavigation ('always')

        // Resizing thumbnails

        ls.resizeThumb = function(){

            ls.bottomNavSizeHelper('on');

            var sliderW = ls.g.sliderOriginalWidth.indexOf('%') == -1 ? parseInt( ls.g.sliderOriginalWidth ) : ls.g.sliderWidth();

            $(el).find('.ls-thumbnail-slide a').css({
                width : parseInt( ls.o.tnWidth * ls.g.ratio ),
                height : parseInt( ls.o.tnHeight * ls.g.ratio )
            });

            $(el).find('.ls-thumbnail-slide a:last').css({
                margin: 0
            });

            $(el).find('.ls-thumbnail-slide').css({
                height : parseInt( ls.o.tnHeight * ls.g.ratio )
            });

            var tn = $(el).find('.ls-thumbnail');

            var originalWidth = ls.o.tnContainerWidth.indexOf('%') == -1 ? parseInt( ls.o.tnContainerWidth ) : parseInt( sliderW / 100 * parseInt( ls.o.tnContainerWidth ) );

            tn.css({
                width : originalWidth * Math.floor( ls.g.ratio * 100 ) / 100
            });

            if( tn.width() > $(el).find('.ls-thumbnail-slide').width() ){
                tn.css({
                    width : $(el).find('.ls-thumbnail-slide').width()
                });
            }

            ls.bottomNavSizeHelper('off');
        };

        // Changing thumbnails

        ls.changeThumb = function(index){

            var curIndex = index ? index : ls.g.nextLayerIndex;

            $(el).find('.ls-thumbnail-slide a:not(.ls-thumb-'+curIndex+')').children().each(function(){
                $(this).removeClass('ls-thumb-active').stop().fadeTo(750,ls.o.tnInactiveOpacity/100);
            });

            $(el).find('.ls-thumbnail-slide a.ls-thumb-'+curIndex).children().addClass('ls-thumb-active').stop().fadeTo(750,ls.o.tnActiveOpacity/100);
        };

        // Scrolling thumbnails

        ls.scrollThumb = function(){

            if( !$(el).find('.ls-thumbnail-slide-container').hasClass('ls-thumbnail-slide-hover') ){
                var curThumb = $(el).find('.ls-thumb-active').length ? $(el).find('.ls-thumb-active').parent() : false;
                if( curThumb ){
                    var thumbCenter = curThumb.position().left + curThumb.width() / 2;
                    var mL = $(el).find('.ls-thumbnail-slide-container').width() / 2 - thumbCenter;
                    mL = mL < $(el).find('.ls-thumbnail-slide-container').width() - $(el).find('.ls-thumbnail-slide').width() ? $(el).find('.ls-thumbnail-slide-container').width() - $(el).find('.ls-thumbnail-slide').width() : mL;
                    mL = mL > 0 ? 0 : mL;
                    $(el).find('.ls-thumbnail-slide').animate({
                        marginLeft : mL
                    }, 600 );
                }
            }
        };

        // IMPROVEMENT v4.1.3 Changed the working of some Thumbnail and Bottom Navigation features

        ls.bottomNavSizeHelper = function(val){

            if( ls.o.hoverBottomNav && !$(el).hasClass('ls-hover') ){
                switch(val){
                    case 'on':
                        ls.g.thumbsWrapper.css({
                            visibility: 'hidden',
                            display: 'block'
                        });
                        break;
                    case 'off':
                        ls.g.thumbsWrapper.css({
                            visibility: 'visible',
                            display: 'none'
                        });
                        break;
                }
            }
        };

        // Animating layers and sublayers

        ls.animate = function(){

            /* GLOBAL (used by both old and new transitions ) */

            // Changing variables
            // BUGFIX v4.6.0 If there is only one layer, there is no need to set ls.g.isAnimating to true

            if( $(el).find('.ls-slide').length > 1 ){
                ls.g.isAnimating = true;
            }

            ls.g.isLoading = false;

            // Clearing timeouts

            clearTimeout( ls.g.slideTimer );
            clearTimeout( ls.g.changeTimer );

            ls.g.stopLayer = ls.g.curLayer;

            // Calling cbAnimStart callback function

            ls.o.cbAnimStart(ls.g);

            // NEW FEATURE v3.5 thumbnailNavigation ('always')

            if( ls.o.thumbnailNavigation == 'always' ){

                // ChangeThumb

                ls.changeThumb();

                // ScrollThumb

                if( !('ontouchstart' in window) ){
                    ls.scrollThumb();
                }
            }

            // Adding .ls-animating class to next layer

            ls.g.nextLayer.addClass('ls-animating');



            /* OLD layer transitions (version 3.x) */

            // Setting position and styling of current and next layers

            var curLayerLeft = curLayerRight = curLayerTop = curLayerBottom = nextLayerLeft = nextLayerRight = nextLayerTop = nextLayerBottom = layerMarginLeft = layerMarginRight = layerMarginTop = layerMarginBottom = 'auto';
            var curLayerWidth = nextLayerWidth = ls.g.sliderWidth();
            var curLayerHeight = nextLayerHeight = ls.g.sliderHeight();

            // Calculating direction

            var prevOrNext = ls.g.prevNext == 'prev' ? ls.g.curLayer : ls.g.nextLayer;
            var chooseDirection = prevOrNext.data('slidedirection') ? prevOrNext.data('slidedirection') : ls.o.slideDirection;

            // Setting the direction of sliding

            var slideDirection = ls.g.slideDirections[ls.g.prevNext][chooseDirection];

            if( slideDirection == 'left' || slideDirection == 'right' ){
                curLayerWidth = curLayerTop = nextLayerWidth = nextLayerTop = 0;
                layerMarginTop = 0;
            }
            if( slideDirection == 'top' || slideDirection == 'bottom' ){
                curLayerHeight = curLayerLeft = nextLayerHeight = nextLayerLeft = 0;
                layerMarginLeft = 0;
            }

            switch(slideDirection){
                case 'left':
                    curLayerRight = nextLayerLeft = 0;
                    layerMarginLeft = -ls.g.sliderWidth();
                    break;
                case 'right':
                    curLayerLeft = nextLayerRight = 0;
                    layerMarginLeft = ls.g.sliderWidth();
                    break;
                case 'top':
                    curLayerBottom = nextLayerTop = 0;
                    layerMarginTop = -ls.g.sliderHeight();
                    break;
                case 'bottom':
                    curLayerTop = nextLayerBottom = 0;
                    layerMarginTop = ls.g.sliderHeight();
                    break;
            }

            // Setting start positions and styles of layers

            ls.g.curLayer.css({
                left : curLayerLeft,
                right : curLayerRight,
                top : curLayerTop,
                bottom : curLayerBottom
            });
            ls.g.nextLayer.css({
                width : nextLayerWidth,
                height : nextLayerHeight,
                left : nextLayerLeft,
                right : nextLayerRight,
                top : nextLayerTop,
                bottom : nextLayerBottom
            });

            // Creating variables for the OLD transitions of CURRENT LAYER

            // BUGFIX v1.6 fixed some wrong parameters of current layer
            // BUGFIX v1.7 fixed using of delayout of current layer

            var curDelay = ls.g.curLayer.data('delayout') ? parseInt(ls.g.curLayer.data('delayout')) : ls.o.delayOut;

            var curDuration = ls.g.curLayer.data('durationout') ? parseInt(ls.g.curLayer.data('durationout')) : ls.o.durationOut;
            var curEasing = ls.g.curLayer.data('easingout') ? ls.g.curLayer.data('easingout') : ls.o.easingOut;

            // Creating variables for the OLD transitions of NEXT LAYER

            var nextDelay = ls.g.nextLayer.data('delayin') ? parseInt(ls.g.nextLayer.data('delayin')) : ls.o.delayIn;
            var nextDuration = ls.g.nextLayer.data('durationin') ? parseInt(ls.g.nextLayer.data('durationin')) : ls.o.durationIn;

            // BUGFIX v5.2.0 duration cannot be 0

            if( nextDuration === 0 ){ nextDuration = 1 }
            var nextEasing = ls.g.nextLayer.data('easingin') ? ls.g.nextLayer.data('easingin') : ls.o.easingIn;

            var curLayer = function(){

                // BUGFIX v1.6 added an additional delaytime to current layer to fix the '1px gap' bug
                // BUGFIX v3.0 modified from curDuration / 80 to curDuration / 15

                ls.g.curLayer.delay( curDelay + curDuration / 15).animate({
                    width : curLayerWidth,
                    height : curLayerHeight
                }, curDuration, curEasing,function(){

                    curLayerCallback();
                });
            };

            var curLayerCallback = function(){

                // Stopping current sublayer animations if needed (they are not visible at this point).

                ls.g.stopLayer.find(' > *[class*="ls-l"]').each(function(){
                    if( $(this).data('tr') ){
                        $(this).data('tr').kill();
                    }

                    $(this).css({
                        filter: 'none'
                    });
                });

                // Setting current layer

                ls.g.curLayer = ls.g.nextLayer;

                // IMPROVEMENT v5.2.0 added prevLayerIndex and fixing curLayerIndex (nextLayerIndex is the same as curLayerIndex because the slider doesn't know at this point which slide will be the next)

                ls.g.prevLayerIndex = ls.g.curLayerIndex;
                ls.g.curLayerIndex = ls.g.nextLayerIndex;

                ls.o.cbAnimStop(ls.g);

                // NEW FEATURE v5.0.0 Lazy-load (preloading here the images of the next layer)

                if( ls.o.imgPreload && ls.o.lazyLoad ){

                    var preLayerIndex = ls.g.curLayerIndex == ls.g.layersNum ? 1 : ls.g.curLayerIndex + 1;
                    $(el).find('.ls-slide').eq(preLayerIndex-1).find('img:not(.ls-preloaded)').each(function(){
                        $(this).load(function(){
                            $(this).addClass('ls-preloaded');
                        }).error(function(){
                            var imgURL = $(this).data('src').substring($(this).data('src').lastIndexOf("/") + 1, $(this).data('src').length);
                            if( window.console ){
                                console('LayerSlider error:\r\n\r\nIt seems like the URL of the image or background image "'+imgURL+'" is pointing to a wrong location and it cannot be loaded. Please check the URLs of all your images used in the slider.');
                            }else{
                                alert('LayerSlider error:\r\n\r\nIt seems like the URL of the image or background image "'+imgURL+'" is pointing to a wrong location and it cannot be loaded. Please check the URLs of all your images used in the slider.');
                            }
                            $(this).addClass('ls-not-preloaded');
                        }).attr('src', $(this).data('src'));
                    });
                }

                // Changing some css classes

                $(el).find('.ls-slide').removeClass('ls-active');
                $(el).find('.ls-slide:eq(' + ( ls.g.curLayerIndex - 1 ) + ')').addClass('ls-active').removeClass('ls-animating');
                $(el).find('.ls-bottom-slidebuttons a').removeClass('ls-nav-active');
                $(el).find('.ls-bottom-slidebuttons a:eq('+( ls.g.curLayerIndex - 1 )+')').addClass('ls-nav-active');

                // Setting timer if needed

                if( ls.g.autoSlideshow ){
                    ls.timer();
                }

                // Changing variables

                ls.g.isAnimating = false;
                if( ls.g.resize == true ){
                    ls.makeResponsive( ls.g.curLayer, function(){
                        ls.g.resize = false;
                    });
                }
            };

            var curSubLayers = function(sublayersDurationOut){

                ls.g.curLayer.find(' > *[class*="ls-l"]').each(function(){

                    if( !$(this).data('transitiontype') ){
                        ls.transitionType( $(this) );
                    }

                    // BUGFIX v5.1.0 Removing ls-videohack class before starting transition

                    $(this).removeClass('ls-videohack');

                    var curSubSlideDir = $(this).data('slidedirection') ? $(this).data('slidedirection') : slideDirection;
                    var lml, lmt;

                    switch(curSubSlideDir){
                        case 'left':
                            lml = -ls.g.sliderWidth();
                            lmt = 0;
                            break;
                        case 'right':
                            lml = ls.g.sliderWidth();
                            lmt = 0;
                            break;
                        case 'top':
                            lmt = -ls.g.sliderHeight();
                            lml = 0;
                            break;
                        case 'bottom':
                            lmt = ls.g.sliderHeight();
                            lml = 0;
                            break;
                        case 'fade':
                            lmt = 0;
                            lml = 0;
                            break;
                    }

                    // NEW FEATURE v1.6 added slideoutdirection to sublayers
                    // NEW FEATURES 5.0.0 added axis-free transitions with offsetx and offsety properties

                    if( $(this).data('transitiontype') === 'new' ){
                        var curSubSlideOutDir = 'new';
                    }else{
                        var curSubSlideOutDir = $(this).data('slideoutdirection') ? $(this).data('slideoutdirection') : false;
                    }

                    switch(curSubSlideOutDir){
                        case 'left':
                            lml = ls.g.sliderWidth();
                            lmt = 0;
                            break;
                        case 'right':
                            lml = -ls.g.sliderWidth();
                            lmt = 0;
                            break;
                        case 'top':
                            lmt = ls.g.sliderHeight();
                            lml = 0;
                            break;
                        case 'bottom':
                            lmt = -ls.g.sliderHeight();
                            lml = 0;
                            break;
                        case 'fade':
                            lmt = 0;
                            lml = 0;
                            break;
                        case 'new':
                            if( $(this).data('offsetxout') ){
                                if( $(this).data('offsetxout') === 'left' ){
                                    lml = ls.g.sliderWidth();
                                }else if( $(this).data('offsetxout') === 'right' ){
                                    lml = -ls.g.sliderWidth();
                                }else{
                                    lml = -parseInt( $(this).data('offsetxout') );
                                }
                            }else{
                                lml = -ls.lt.offsetXOut;
                            }
                            if( $(this).data('offsetyout') ){
                                if( $(this).data('offsetyout') === 'top' ){
                                    lmt = ls.g.sliderHeight();
                                }else if( $(this).data('offsetyout') === 'bottom' ){
                                    lmt = -ls.g.sliderHeight();
                                }else{
                                    lmt = -parseInt( $(this).data('offsetyout') );
                                }
                            }else{
                                lmt = -ls.lt.offsetYOut;
                            }
                            break;
                    }

                    // NEW FEATURES v4.5.0 Rotating & Scaling sublayers
                    // BUGFIX v4.5.5 changing the default value from 0 to 'none' (because of old jQuery, 1.7.2)
                    // NEW FEATURES v5.0.0 Added SkewX, SkewY, ScaleX, ScaleY, RotateX & RotateY transitions

                    var curSubRotate = curSubRotateX = curSubRotateY = curSubScale = curSubSkewX = curSubSkewY = curSubScaleX = curSubScaleY = 'none';
//							if( !ls.g.ie78 && ls.g.enableCSS3 ){
                    curSubRotate = $(this).data('rotateout') ? $(this).data('rotateout') : ls.lt.rotateOut;
                    curSubRotateX = $(this).data('rotatexout') ? $(this).data('rotatexout') : ls.lt.rotateXOut;
                    curSubRotateY = $(this).data('rotateyout') ? $(this).data('rotateyout') : ls.lt.rotateYOut;
                    curSubScale = $(this).data('scaleout') ? $(this).data('scaleout') : ls.lt.scaleOut;
                    curSubSkewX = $(this).data('skewxout') ? $(this).data('skewxout') : ls.lt.skewXOut;
                    curSubSkewY = $(this).data('skewyout') ? $(this).data('skewyout') : ls.lt.skewYOut;
                    if( curSubScale === 1 ){
                        curSubScaleX = $(this).data('scalexout') ? $(this).data('scalexout') : ls.lt.scaleXOut;
                        curSubScaleY = $(this).data('scaleyout') ? $(this).data('scaleyout') : ls.lt.scaleYOut;
                    }else{
                        curSubScaleX = curSubScaleY = curSubScale;
                    }
                    var too = $(this).data('transformoriginout') ? $(this).data('transformoriginout').split(' ') : ls.lt.transformOriginOut;
                    for(var t =0;t<too.length;t++){
                        if( too[t].indexOf('%') === -1 && too[t].indexOf('left') !== -1 && too[t].indexOf('right') !== -1 && too[t].indexOf('top') !== -1 && too[t].indexOf('bottom') !== -1 ){
                            too[t] = '' + parseInt( too[t] ) * ls.g.ratio + 'px';
                        }
                    }
                    var curSubTransformOrigin = too.join(' ');
                    var curSubPerspective = $(this).data('perspectiveout') ? $(this).data('perspectiveout') : ls.lt.perspectiveOut;
//							}

                    // IMPROVEMENT v4.0 Distance (P.level): -1

                    var endLeft = parseInt( $(this).css('left') );
                    var endTop = parseInt( $(this).css('top') );

                    var curSubPLevel = parseInt( $(this).attr('class').split('ls-l')[1] );

                    var wh = $(this).outerWidth() > $(this).outerHeight() ? $(this).outerWidth() : $(this).outerHeight();
                    var modX = parseInt( curSubRotate ) === 0 ? $(this).outerWidth() : wh;
                    var modY = parseInt( curSubRotate ) === 0 ? $(this).outerHeight() : wh;

                    if( ( curSubPLevel === -1 && curSubSlideOutDir !== 'new' ) || ( $(this).data('offsetxout') === 'left' || $(this).data('offsetxout') === 'right' ) ){
                        if( lml < 0 ){
                            lml = - ( ls.g.sliderWidth() - endLeft + ( curSubScaleX / 2 - .5 ) * modX + 100  );
                        }else if( lml > 0 ){
                            lml = endLeft + ( curSubScaleX / 2 + .5 ) * modX + 100;
                        }
                    }else{
                        lml = lml * ls.g.ratio;
                    }

                    if( ( curSubPLevel === -1 && curSubSlideOutDir !== 'new' ) || ( $(this).data('offsetyout') === 'top' || $(this).data('offsetyout') === 'bottom' ) ){
                        if( lmt < 0 ){
                            lmt = - ( ls.g.sliderHeight() - endTop + ( curSubScaleY / 2 - .5 ) * modY + 100  );
                        }else if( lmt > 0 ){
                            lmt = endTop + ( curSubScaleY / 2 + .5 ) * modY + 100;
                        }
                    }else{
                        lmt = lmt * ls.g.ratio;
                    }

                    if( curSubPLevel === -1 || curSubSlideOutDir === 'new' ){
                        var curSubPar = 1;
                    }else{
                        var curSubParMod = ls.g.curLayer.data('parallaxout') ? parseInt(ls.g.curLayer.data('parallaxout')) : ls.o.parallaxOut;
                        var curSubPar = curSubPLevel * curSubParMod;
                    }

                    if( $(this).data('transitiontype') === 'new' ){
                        var deO = ls.lt.delayOut;
                        var duO = ls.lt.durationOut;
                        var eO = ls.lt.easingOut;
                    }else{
                        var deO = ls.o.delayOut;
                        var duO = ls.o.durationOut;
                        var eO = ls.o.easingOut;
                    }

                    var curSubDelay = $(this).data('delayout') ? parseInt($(this).data('delayout')) : deO;
                    var curSubTime = $(this).data('durationout') ? parseInt($(this).data('durationout')) : duO;

                    // BUGFIX v5.2.0 duration cannot be 0

                    if( curSubTime === 0 ){ curSubTime = 1 }
                    var curSubEasing = $(this).data('easingout') ? $(this).data('easingout') : eO;

                    // On new layer transitions, all sublayer will be slide / fade out in 500ms without any delays

                    if(sublayersDurationOut){
                        curSubDelay = 0;
                        curSubTime = sublayersDurationOut;
                        // curSubEasing = 'easeInExpo';
                    }

                    // Clearing showUntilTimers

                    if( $(this).data('showUntilTimer') ){
                        clearTimeout( $(this).data('showUntilTimer') );
                    }

                    var css = {
                        visibility : 'hidden'
                    };

                    var el = $(this);

                    var transition = {
                        rotation : curSubRotate,
                        rotationX : curSubRotateX,
                        rotationY : curSubRotateY,
                        skewX : curSubSkewX,
                        skewY : curSubSkewY,
                        scaleX : curSubScaleX,
                        scaleY : curSubScaleY,
                        x : -lml * curSubPar,
                        y : -lmt * curSubPar,
                        delay : curSubDelay/1000,
                        ease : lsConvertEasing( curSubEasing ),
                        onComplete : function(){
                            el.css( css );
                        }
                    };

                    if( curSubSlideOutDir == 'fade' || ( !curSubSlideOutDir && curSubSlideDir === 'fade' ) || ( $(this).data('fadeout') !== 'false' && $(this).data('transitiontype') === 'new' ) ){
                        transition['opacity'] = 0;
                        css['opacity'] = $(this).data( 'originalOpacity' );
                    }

                    if( $(this).data('tr') ){
                        $(this).data('tr').kill();
                    }

                    TweenLite.set( $(this)[0],{
                        transformOrigin : curSubTransformOrigin,
                        transformPerspective : curSubPerspective
                    });

                    $(this).data('tr', TweenLite.to($(this)[0],curSubTime/1000,transition) );

                    // $(this).stop(true,false).delay( curSubDelay ).animate( transition, curSubTime, curSubEasing,function(){
                    // 	$(this).css( css );
                    // });
                });
            };

            var nextLayer = function(){

                ls.g.nextLayer.delay( curDelay + nextDelay ).animate({
                    width : ls.g.sliderWidth(),
                    height : ls.g.sliderHeight()
                }, nextDuration, nextEasing );
            };

            var nextSubLayers = function(){

                if( ls.g.totalDuration ){
                    curDelay = 0;
                }

                // Needed for the Timeline
                if( typeof ls.o.cbTimeLineStart === 'function' ){
                    ls.o.cbTimeLineStart(ls.g, curDelay+nextDelay );
                }

                ls.g.nextLayer.find(' > *[class*="ls-l"]').each(function(){

                    // Replacing global parameters with unique if need
                    // NEW FEATURES 5.0.0 added axis-free transitions with offsetx and offsety properties

                    if( !$(this).data('transitiontype') ){
                        ls.transitionType( $(this) );
                    }

                    if( $(this).data('transitiontype') === 'new' ){
                        var nextSubSlideDir = 'new';
                    }else{
                        var nextSubSlideDir = $(this).data('slidedirection') ? $(this).data('slidedirection') : slideDirection;
                    }
                    var lml, lmt;

                    switch(nextSubSlideDir){
                        case 'left':
                            lml = -ls.g.sliderWidth();
                            lmt = 0;
                            break;
                        case 'right':
                            lml = ls.g.sliderWidth();
                            lmt = 0;
                            break;
                        case 'top':
                            lmt = -ls.g.sliderHeight();
                            lml = 0;
                            break;
                        case 'bottom':
                            lmt = ls.g.sliderHeight();
                            lml = 0;
                            break;
                        case 'fade':
                            lmt = 0;
                            lml = 0;
                            break;
                        case 'new':
                            if( $(this).data('offsetxin') ){
                                if( $(this).data('offsetxin') === 'left' ){
                                    lml = -ls.g.sliderWidth();
                                }else if( $(this).data('offsetxin') === 'right' ){
                                    lml = ls.g.sliderWidth();
                                }else{
                                    lml = parseInt( $(this).data('offsetxin') );
                                }
                            }else{
                                lml = ls.lt.offsetXIn;
                            }
                            if( $(this).data('offsetyin') ){
                                if( $(this).data('offsetyin') === 'top' ){
                                    lmt = -ls.g.sliderHeight();
                                }else if( $(this).data('offsetyin') === 'bottom' ){
                                    lmt = ls.g.sliderHeight();
                                }else{
                                    lmt = parseInt( $(this).data('offsetyin') );
                                }
                            }else{
                                lmt = ls.lt.offsetYIn;
                            }
                            break;
                    }

                    // NEW FEATURE v4.5.0 Rotating & Scaling sublayers
                    // BUGFIX v4.5.5 changing the default value from 0 to 'none' (because of old jQuery, 1.7.2)
                    // NEW FEATURES v5.0.0 Added SkewX, SkewY, ScaleX, ScaleY, RotateX & RotateY transitions

                    var nextSubRotate = nextSubRotateX = nextSubRotateY = nextSubScale = nextSubSkewX = nextSubSkewY = nextSubScaleX = nextSubScaleY = 'none';
//							if( !ls.g.ie78 && ls.g.enableCSS3 ){
                    nextSubRotate = $(this).data('rotatein') ? $(this).data('rotatein') : ls.lt.rotateIn;
                    nextSubRotateX = $(this).data('rotatexin') ? $(this).data('rotatexin') : ls.lt.rotateXIn;
                    nextSubRotateY = $(this).data('rotateyin') ? $(this).data('rotateyin') : ls.lt.rotateYIn;
                    nextSubScale = $(this).data('scalein') ? $(this).data('scalein') : ls.lt.scaleIn;
                    nextSubSkewX = $(this).data('skewxin') ? $(this).data('skewxin') : ls.lt.skewXIn;
                    nextSubSkewY = $(this).data('skewyin') ? $(this).data('skewyin') : ls.lt.skewYIn;
                    if( nextSubScale === 1 ){
                        nextSubScaleX = $(this).data('scalexin') ? $(this).data('scalexin') : ls.lt.scaleXIn;
                        nextSubScaleY = $(this).data('scaleyin') ? $(this).data('scaleyin') : ls.lt.scaleYIn;
                    }else{
                        nextSubScaleX = nextSubScaleY = nextSubScale;
                    }

                    var toi = $(this).data('transformoriginin') ? $(this).data('transformoriginin').split(' ') : ls.lt.transformOriginIn;
                    for(var t =0;t<toi.length;t++){
                        if( toi[t].indexOf('%') === -1 && toi[t].indexOf('left') !== -1 && toi[t].indexOf('right') !== -1 && toi[t].indexOf('top') !== -1 && toi[t].indexOf('bottom') !== -1 ){
                            toi[t] = '' + parseInt( toi[t] ) * ls.g.ratio + 'px';
                        }
                    }
                    var nextSubTransformOrigin = toi.join(' ');
                    var nextSubPerspective = $(this).data('perspectivein') ? $(this).data('perspectivein') : ls.lt.perspectiveIn;
//							}

                    // IMPROVEMENT v4.0 Distance (P.level): -1

                    var endLeft = parseInt( $(this).css('left') );
                    var endTop = parseInt( $(this).css('top') );

                    var nextSubPLevel = parseInt( $(this).attr('class').split('ls-l')[1] );

                    // BUGFIX v5.0.1 Fixed the starting position of layers with percentage value of width

                    if( $(this)[0].style.width.indexOf('%') !== -1 ){
                        $(this).css({
                            width: ls.g.sliderWidth() / 100 * parseInt( $(this)[0].style.width )
                        });
                    }

                    var wh = $(this).outerWidth() > $(this).outerHeight() ? $(this).outerWidth() : $(this).outerHeight();
                    var modX = parseInt( nextSubRotate ) === 0 ? $(this).outerWidth() : wh;
                    var modY = parseInt( nextSubRotate ) === 0 ? $(this).outerHeight() : wh;

                    // console.log( modX, $(this).outerWidth(), $(this).width(), $(this).height(), $(this)[0].style.width, $(this).outerHeight(), wh );

                    if( ( nextSubPLevel === -1 && nextSubSlideDir !== 'new' ) || ( $(this).data('offsetxin') === 'left' || $(this).data('offsetxin') === 'right' ) ){
                        if( lml < 0 ){
                            lml = - ( endLeft + ( nextSubScaleX / 2 + .5 ) * modX + 100  );
                        }else if( lml > 0 ){
                            lml = ls.g.sliderWidth() - endLeft + ( nextSubScaleX / 2 - .5 ) * modX + 100;
                        }
                    }else{
                        lml = lml * ls.g.ratio;
                    }

                    if( ( nextSubPLevel === -1 && nextSubSlideDir !== 'new' ) || ( $(this).data('offsetyin') === 'top' || $(this).data('offsetyin') === 'bottom' ) ){

                        if( lmt < 0 ){
                            lmt = - ( endTop + ( nextSubScaleY / 2 + .5 ) * modY + 100  );
                        }else if( lmt > 0 ){
                            lmt = ls.g.sliderHeight() - endTop + ( nextSubScaleY / 2 - .5 ) * modY + 100;
                        }
                    }else{
                        lmt = lmt * ls.g.ratio;
                    }

                    if( nextSubPLevel === -1 || nextSubSlideDir === 'new'){
                        var nextSubPar = 1;
                    }else{
                        var nextSubParMod = ls.g.nextLayer.data('parallaxin') ? parseInt(ls.g.nextLayer.data('parallaxin')) : ls.o.parallaxIn;
                        var nextSubPar = nextSubPLevel * nextSubParMod;
                    }

                    if( $(this).data('transitiontype') === 'new' ){
                        var deI = ls.lt.delayIn;
                        var duI = ls.lt.durationIn;
                        var eI = ls.lt.easingIn;
                    }else{
                        var deI = ls.o.delayIn;
                        var duI = ls.o.durationIn;
                        var eI = ls.o.easingIn;
                    }

                    var nextSubDelay = $(this).data('delayin') ? parseInt($(this).data('delayin')) : deI;
                    var nextSubTime = $(this).data('durationin') ? parseInt($(this).data('durationin')) : duI;
                    var nextSubEasing = $(this).data('easingin') ? $(this).data('easingin') : eI;

                    var cursub = $(this);

                    var nextSubCallback = function(){

                        // BUGFIX v5.1.0 Removing transition property from video layers

                        if( cursub.hasClass('ls-video-layer') ){
                            cursub.addClass('ls-videohack');
                        }

                        // NEW FEATURE v2.0 autoPlayVideos

                        if( ls.o.autoPlayVideos == true ){

                            // YouTube & Vimeo videos

                            cursub.find('.ls-videopreview').click();

                            // HTML5 videos

                            cursub.find('video, audio').each(function(){
                                if( typeof $(this)[0].currentTime !== 0){
                                    $(this)[0].currentTime = 0;
                                }
                                $(this).click();
                            });
                        }

                        // NEW FEATURE v3.0 showUntil sublayers
                        // IMPROVEMENT v5.2.0 video layers with auto play will skip showuntil feature

                        if( ( !cursub.hasClass('ls-video-layer') || ( cursub.hasClass('ls-video-layer') && ls.o.autoPlayVideos === false ) ) && cursub.data('showuntil') > 0 ){

                            // IMPROVEMENT v4.5.0 sublayerShowUntil will be called anly if necessary

                            cursub.data('showUntilTimer', setTimeout(function(){
                                ls.sublayerShowUntil( cursub );
                            }, cursub.data('showuntil') ));
                        }
                    };

                    $(this).css({
                        marginLeft : 0,
                        marginTop : 0
                    });

                    var css = {
                        scaleX : nextSubScaleX,
                        scaleY : nextSubScaleY,
                        skewX : nextSubSkewX,
                        skewY : nextSubSkewY,
                        rotation : nextSubRotate,
                        rotationX : nextSubRotateX,
                        rotationY : nextSubRotateY,
                        visibility : 'visible',
                        x : lml * nextSubPar,
                        y : lmt * nextSubPar
                    };

                    var transition = {
                        rotation : 0,
                        rotationX : 0,
                        rotationY : 0,
                        skewX : 0,
                        skewY : 0,
                        scaleX : 1,
                        scaleY : 1,
                        ease : lsConvertEasing( nextSubEasing ),
                        delay : nextSubDelay/1000,
                        x : 0,
                        y : 0,
                        onComplete : function(){
                            nextSubCallback();
                        }
                    };

                    if( nextSubSlideDir.indexOf('fade') != -1 || ( $(this).data('fadein') !== 'false' && $(this).data('transitiontype') === 'new' ) ){

                        css['opacity'] = 0;
                        transition['opacity'] = $(this).data( 'originalOpacity' );
                    }

                    // $(this).css( css );

                    // $(this).stop().delay( curDelay + nextDelay + nextSubDelay ).animate( transition, nextSubTime, nextSubEasing, function(){
                    // 	if( ls.g.ie78 & $(this).data( 'originalOpacity') === 1 ){
                    // 		$(this).get(0).style.removeAttribute('filter');
                    // 	}
                    // 	nextSubCallback();
                    // });

                    if( $(this).data('tr') ){
                        $(this).data('tr').kill();
                    }

                    TweenLite.set( $(this)[0],{
                        transformPerspective : nextSubPerspective,
                        transformOrigin : nextSubTransformOrigin
                    });

                    $(this).data('tr', TweenLite.fromTo($(this)[0],nextSubTime/1000,css,transition) );
                });
            };

            /* NEW FEATURE v4.0 2D & 3D Layer Transitions */

            // Selecting ONE transition (random)
            // If the browser doesn't support CSS3 3D, 2D fallback mode will be used instead
            // In this case, if user didn't specify any 2D transitions, a random will be selected

            var selectTransition = function(){

                // if the browser supports CSS3 3D and user specified at least one of 3D transitions

                if( lsSupport3D( $(el) ) && ( ls.g.nextLayer.data('transition3d') || ls.g.nextLayer.data('customtransition3d') ) ){

                    if( ls.g.nextLayer.data('transition3d') && ls.g.nextLayer.data('customtransition3d') ){
                        var rnd = Math.floor(Math.random() * 2);
                        var rndT = [['3d',ls.g.nextLayer.data('transition3d')],['custom3d',ls.g.nextLayer.data('customtransition3d')]];
                        getTransitionType(rndT[rnd][0],rndT[rnd][1]);
                    }else if( ls.g.nextLayer.data('transition3d') ){
                        getTransitionType('3d',ls.g.nextLayer.data('transition3d'));
                    }else{
                        getTransitionType('custom3d',ls.g.nextLayer.data('customtransition3d'));
                    }

                }else{

                    if( ls.g.nextLayer.data('transition2d') && ls.g.nextLayer.data('customtransition2d') ){
                        var rnd = Math.floor(Math.random() * 2);
                        var rndT = [['2d',ls.g.nextLayer.data('transition2d')],['custom2d',ls.g.nextLayer.data('customtransition2d')]];
                        getTransitionType(rndT[rnd][0],rndT[rnd][1]);
                    }else if( ls.g.nextLayer.data('transition2d') ){
                        getTransitionType('2d',ls.g.nextLayer.data('transition2d'));
                    }else if( ls.g.nextLayer.data('customtransition2d') ){
                        getTransitionType('custom2d',ls.g.nextLayer.data('customtransition2d'));
                    }else{
                        getTransitionType('2d','1');
                    }
                }
            };

            // Needed by the demo page

            var selectCustomTransition = function(){

                if( lsSupport3D( $(el) ) && LSCustomTransition.indexOf('3d') != -1 ){
                    getTransitionType('3d',LSCustomTransition.split(':')[1]);
                }else{
                    if( LSCustomTransition.indexOf('3d') != -1){
                        getTransitionType('2d','all');
                    }else{
                        getTransitionType('2d',LSCustomTransition.split(':')[1]);
                    }
                }
            };

            // Choosing layer transition type (2d, 3d, or both)

            var getTransitionType = function(type,transitionlist){

                var tr = type.indexOf('custom') == -1 ? ls.t : ls.ct;
                var tt = '3d', lt, number;

                if( type.indexOf('2d') != -1 ){
                    tt = '2d';
                }

                if( transitionlist.indexOf('last') != -1 ){
                    number = tr['t'+tt].length-1;
                    lt = 'last';
                }else if( transitionlist.indexOf('all') != -1){
                    number = Math.floor(Math.random() * lsCountProp(tr['t'+tt]) );
                    lt = 'random from all';
                }else{
                    var t = transitionlist.split(',');
                    var l = t.length;
                    number = parseInt(t[Math.floor(Math.random() * l)])-1;
                    lt = 'random from specified';
                }

                slideTransition(tt,tr['t'+tt][number]);

//						$('.test').html('Originals:<br><br>t3D: '+ls.g.nextLayer.data('transition3d')+'<br>t2D: '+ls.g.nextLayer.data('transition2d')+'<br>custom3D: '+ls.g.nextLayer.data('customtransition3d')+'<br>custom2D: '+ls.g.nextLayer.data('customtransition2d')+'<br><br>Support 3D: '+lsSupport3D( $(el) )+'<br><br>Selected transition:<br><br>Type: '+type+' ('+lt+')<br>Number in transition list: '+(number+1)+'<br>Name of the transition: '+tr['t'+tt][number]['name']);
            };

            // The slideTransition function

            var slideTransition = function(type,prop){

                var inner = $(el).find('.ls-inner');

                // sublayersDurationOut - for future usage

                var sublayersDurationOut = ls.g.curLayer.find('*[class*="ls-l"]').length > 0 ? 1000 : 0;

                // Detecting a carousel transition - Transition name must have the carousel string

                var carousel = prop.name.toLowerCase().indexOf('carousel') == -1 ? false : true;

                // Detecting a crossfade transition - Transition name must have the crossfad string

                var crossfade = prop.name.toLowerCase().indexOf('crossfad') == -1 ? false : true;

                // Calculating cols and rows

                var cols = typeof(prop.cols);
                var rows = typeof(prop.rows);

                switch( cols ){
                    case 'number':
                        cols = prop.cols;
                        break;
                    case 'string':
                        cols = Math.floor( Math.random() * ( parseInt( prop.cols.split(',')[1] ) - parseInt( prop.cols.split(',')[0] ) + 1) ) + parseInt( prop.cols.split(',')[0] );
                        break;
                    default:
                        cols = Math.floor( Math.random() * ( prop.cols[1] - prop.cols[0] + 1) ) + prop.cols[0];
                        break;
                }

                switch( rows ){
                    case 'number':
                        rows = prop.rows;
                        break;
                    case 'string':
                        rows = Math.floor( Math.random() * ( parseInt( prop.rows.split(',')[1] ) - parseInt( prop.rows.split(',')[0] ) + 1) ) + parseInt( prop.rows.split(',')[0] );
                        break;
                    default:
                        rows = Math.floor( Math.random() * ( prop.rows[1] - prop.rows[0] + 1) ) + prop.rows[0];
                        break;
                }

                if( ( ls.g.isMobile() == true && ls.o.optimizeForMobile == true ) || ( ls.g.ie78 && ls.o.optimizeForIE78 == true ) ){

                    // Reducing cols in three steps

                    if( cols >= 15 ){
                        cols = 7;
                    }else if( cols >= 5 ){
                        cols = 4;
                    }else if( cols >= 4 ){
                        cols = 3;
                    }else if( cols > 2 ){
                        cols = 2;
                    }

                    // Reducing rows in three steps

                    if( rows >= 15 ){
                        rows = 7;
                    }else if( rows >= 5 ){
                        rows = 4;
                    }else if( rows >= 4 ){
                        rows = 3;
                    }else if( rows > 2 ){
                        rows = 2;
                    }

                    // Reducing more :)

                    if( rows > 2 && cols > 2 ){
                        rows = 2;
                        if( cols > 4){
                            cols = 4;
                        }
                    }
                }

                var tileWidth = $(el).find('.ls-inner').width() / cols;
                var tileHeight = $(el).find('.ls-inner').height() / rows;

                // Creating HTML markup for layer transitions

                if( !ls.g.ltContainer ){
                    ls.g.ltContainer = $('<div>').addClass('ls-lt-container').addClass('ls-overflow-hidden').css({
                        width : inner.width(),
                        height : inner.height()
                    }).prependTo( inner );
                }else{
                    ls.g.ltContainer.stop(true,true).empty().css({
                        display : 'block',
                        width : inner.width(),
                        height : inner.height()
                    });
                }

                // Setting size

                var restW = inner.width() - Math.floor(tileWidth) * cols;
                var restH = inner.height() - Math.floor(tileHeight) * rows;

                var tileSequence = [];

                // IMPROVEMENT v4.1.3 Array-randomizer is now a local function
                // Randomize array function

                tileSequence.randomize = function() {
                    var i = this.length, j, tempi, tempj;
                    if ( i == 0 ) return false;
                    while ( --i ) {
                        j       = Math.floor( Math.random() * ( i + 1 ) );
                        tempi   = this[i];
                        tempj   = this[j];
                        this[i] = tempj;
                        this[j] = tempi;
                    }
                    return this;
                }

                for(var ts=0; ts<cols * rows; ts++){
                    tileSequence.push(ts);
                }

                // Setting the sequences of the transition

                switch( prop.tile.sequence ){
                    case 'reverse':
                        tileSequence.reverse();
                        break;
                    case 'col-forward':
                        tileSequence = lsOrderArray(rows,cols,'forward');
                        break;
                    case 'col-reverse':
                        tileSequence = lsOrderArray(rows,cols,'reverse');
                        break;
                    case 'random':
                        tileSequence.randomize();
                        break;
                }

                var curBG = ls.g.curLayer.find('.ls-bg');
                var nextBG = ls.g.nextLayer.find('.ls-bg');

                // IMPROVEMENT v4.6.0 If current and next layer both have no BG, skipping the slide transition

                if( curBG.length == 0 && nextBG.length == 0 ){
                    type = '2d';
                    prop = $.extend(true, {}, ls.t['t2d'][0]);
                    prop.transition.duration = 1
                    prop.tile.delay = 0;
                }

                if( type == '3d' ){
                    ls.g.totalDuration = ((cols * rows) - 1) * prop.tile.delay;

                    var stepDuration = 0;

                    if( prop.before && prop.before.duration ){
                        stepDuration += prop.before.duration;
                    }
                    if( prop.animation && prop.animation.duration ){
                        stepDuration += prop.animation.duration;
                    }
                    if( prop.after && prop.after.duration ){
                        stepDuration += prop.after.duration;
                    }

                    ls.g.totalDuration += stepDuration;

                    var stepDelay = 0;

                    if( prop.before && prop.before.delay ){
                        stepDelay += prop.before.delay;
                    }
                    if( prop.animation && prop.animation.delay ){
                        stepDelay += prop.animation.delay;
                    }
                    if( prop.after && prop.after.delay ){
                        stepDelay += prop.after.delay;
                    }

                    ls.g.totalDuration += stepDelay;

                }else{
                    ls.g.totalDuration = ((cols * rows) - 1) * prop.tile.delay + prop.transition.duration;

                    // IMPROVEMENT v4.5.0 Creating separated containers for current and next tiles

                    ls.g.curTiles = $('<div>').addClass('ls-curtiles').appendTo( ls.g.ltContainer );
                    ls.g.nextTiles = $('<div>').addClass('ls-nexttiles').appendTo( ls.g.ltContainer );
                }

                var pn = ls.g.prevNext;

                // Creating cuboids for 3d or tiles for 2d transition (cols * rows)

                for(var tiles=0; tiles < cols * rows; tiles++){

                    var rW = tiles%cols == 0 ? restW : 0;
                    var rH = tiles > (rows-1)*cols-1 ? restH : 0;

                    var tile = $('<div>').addClass('ls-lt-tile').css({
                        width : Math.floor(tileWidth) + rW,
                        height : Math.floor(tileHeight) + rH
                    }).appendTo( ls.g.ltContainer );

                    var curTile, nextTile;

                    // If current transition is a 3d transition

                    if( type == '3d' ){

                        tile.addClass('ls-3d-container');

                        var W = Math.floor(tileWidth) + rW;
                        var H = Math.floor(tileHeight) + rH;
                        var D;

                        if( prop.animation.direction == 'horizontal' ){
                            if( Math.abs(prop.animation.transition.rotateY) > 90 && prop.tile.depth != 'large' ){
                                D = Math.floor( W / 7 ) + rW;
                            }else{
                                D = W;
                            }
                        }else{
                            if( Math.abs(prop.animation.transition.rotateX) > 90 && prop.tile.depth != 'large' ){
                                D = Math.floor( H / 7 ) + rH;
                            }else{
                                D = H;
                            }
                        }

                        var W2 = W/2;
                        var H2 = H/2;
                        var D2 = D/2;

                        // createCuboids function will append cuboids with their style settings to their container

                        // BUGFIX v5.1.2 the prefixless transform must be the last property

                        var createCuboids = function(c,a,w,h,tx,ty,tz,rx,ry){
                            $('<div>').addClass(c).css({
                                width: w,
                                height: h,
                                '-o-transform': 'translate3d('+tx+'px, '+ty+'px, '+tz+'px) rotateX('+rx+'deg) rotateY('+ry+'deg) rotateZ(0deg) scale3d(1, 1, 1)',
                                '-ms-transform': 'translate3d('+tx+'px, '+ty+'px, '+tz+'px) rotateX('+rx+'deg) rotateY('+ry+'deg) rotateZ(0deg) scale3d(1, 1, 1)',
                                '-moz-transform': 'translate3d('+tx+'px, '+ty+'px, '+tz+'px) rotateX('+rx+'deg) rotateY('+ry+'deg) rotateZ(0deg) scale3d(1, 1, 1)',
                                '-webkit-transform': 'translate3d('+tx+'px, '+ty+'px, '+tz+'px) rotateX('+rx+'deg) rotateY('+ry+'deg) rotateZ(0deg) scale3d(1, 1, 1)',
                                'transform': 'translate3d('+tx+'px, '+ty+'px, '+tz+'px) rotateX('+rx+'deg) rotateY('+ry+'deg) rotateZ(0deg) scale3d(1, 1, 1)'
                            }).appendTo(a);
                        };

                        createCuboids('ls-3d-box',tile,0,0,0,0,-D2,0,0);

                        var backRotX = 0
                        var topRotX = 0
                        var bottomRotX = 0

                        if( prop.animation.direction == 'vertical' && Math.abs(prop.animation.transition.rotateX) > 90){
                            createCuboids('ls-3d-back',tile.find('.ls-3d-box'),W,H,-W2,-H2,-D2,180,0);
                        }else{
                            createCuboids('ls-3d-back',tile.find('.ls-3d-box'),W,H,-W2,-H2,-D2,0,180);
                        }

                        createCuboids('ls-3d-bottom',tile.find('.ls-3d-box'),W,D,-W2,H2-D2,0,-90,0);
                        createCuboids('ls-3d-top',tile.find('.ls-3d-box'),W,D,-W2,-H2-D2,0,90,0);
                        createCuboids('ls-3d-front',tile.find('.ls-3d-box'),W,H,-W2,-H2,D2,0,0);
                        createCuboids('ls-3d-left',tile.find('.ls-3d-box'),D,H,-W2-D2,-H2,0,0,-90);
                        createCuboids('ls-3d-right',tile.find('.ls-3d-box'),D,H,W2-D2,-H2,0,0,90);

                        curTile = tile.find('.ls-3d-front');

                        if( prop.animation.direction == 'horizontal' ){
                            if( Math.abs(prop.animation.transition.rotateY) > 90 ){
                                nextTile = tile.find('.ls-3d-back');
                            }else{
                                nextTile = tile.find('.ls-3d-left, .ls-3d-right');
                            }
                        }else{
                            if( Math.abs(prop.animation.transition.rotateX) > 90 ){
                                nextTile = tile.find('.ls-3d-back');
                            }else{
                                nextTile = tile.find('.ls-3d-top, .ls-3d-bottom');
                            }
                        }

                        // Animating cuboids

                        var curCubDelay = tileSequence[tiles] * prop.tile.delay;

                        var curCub = ls.g.ltContainer.find('.ls-3d-container:eq('+tiles+') .ls-3d-box');

                        var tl = new TimelineLite();

                        if( prop.before && prop.before.transition ){
                            prop.before.transition.delay = prop.before.transition.delay ? (prop.before.transition.delay + curCubDelay)/1000 : curCubDelay/1000;
                            tl.to( curCub[0],prop.before.duration/1000,lsConvertTransition( prop.before.transition, prop.before.easing ));
                        }else{
                            prop.animation.transition.delay = prop.animation.transition.delay ? (prop.animation.transition.delay + curCubDelay)/1000 : curCubDelay/1000;
                        }

                        tl.to( curCub[0],prop.animation.duration/1000,lsConvertTransition( prop.animation.transition, prop.animation.easing ));

                        if( prop.after ){
                            if( !prop.after.transition ){
                                prop.after.transition = {};
                            }
                            tl.to( curCub[0],prop.after.duration/1000,lsConvertTransition( prop.after.transition, prop.after.easing, 'after' ));
                        }

                    }else{

                        // If current transition is a 2d transition

                        var T1 = L1 = T2 = L2 = 'auto';
                        var O1 = O2 = 1;

                        if( prop.transition.direction == 'random' ){
                            var dir = ['top','bottom','right','left'];
                            var direction = dir[Math.floor(Math.random() * dir.length )];
                        }else{
                            var direction = prop.transition.direction;
                        }

                        // IMPROVEMENT v4.5.0 Reversing animation directions if slider is moving backwards

                        if( prop.name.toLowerCase().indexOf('mirror') != -1 && tiles%2 == 0 ){
                            if( pn == 'prev' ){
                                pn = 'next';
                            }else{
                                pn = 'prev';
                            }
                        }

                        if( pn == 'prev' ){

                            switch( direction ){
                                case 'top':
                                    direction = 'bottom';
                                    break;
                                case 'bottom':
                                    direction = 'top';
                                    break;
                                case 'left':
                                    direction = 'right';
                                    break;
                                case 'right':
                                    direction = 'left';
                                    break;
                                case 'topleft':
                                    direction = 'bottomright';
                                    break;
                                case 'topright':
                                    direction = 'bottomleft';
                                    break;
                                case 'bottomleft':
                                    direction = 'topright';
                                    break;
                                case 'bottomright':
                                    direction = 'topleft';
                                    break;
                            }
                        }

                        switch( direction ){
                            case 'top':
                                T1 = T2 = -tile.height();
                                L1 = L2 = 0;
                                break;
                            case 'bottom':
                                T1 = T2 = tile.height();
                                L1 = L2 = 0;
                                break;
                            case 'left':
                                T1 = T2 = 0;
                                L1 = L2 = -tile.width();
                                break;
                            case 'right':
                                T1 = T2 = 0;
                                L1 = L2 = tile.width();
                                break;
                            case 'topleft':
                                T1 = tile.height();
                                T2 = 0;
                                L1 = tile.width();
                                L2 = 0;
                                break;
                            case 'topright':
                                T1 = tile.height();
                                T2 = 0;
                                L1 = - tile.width();
                                L2 = 0;
                                break;
                            case 'bottomleft':
                                T1 = - tile.height();
                                T2 = 0;
                                L1 = tile.width();
                                L2 = 0;
                                break;
                            case 'bottomright':
                                T1 = - tile.height();
                                T2 = 0;
                                L1 = - tile.width();
                                L2 = 0;
                                break;
                        }

                        ls.g.scale2D = prop.transition.scale ? prop.transition.scale : 1;

                        if( carousel == true && ls.g.scale2D != 1 ){

                            T1 = T1 / 2;
                            T2 = T2 / 2;
                            L1 = L1 / 2;
                            L2 = L2 / 2;
                        }

                        // Selecting the type of the transition

//								if( !ls.g.ie78 || ( ls.g.ie78 && !ls.o.optimizeForIE78 ) ||  ( ls.g.ie78 && ls.o.optimizeForIE78 == true && prop.name.toLowerCase().indexOf('crossfade') != -1 ) ){
                        switch( prop.transition.type ){
                            case 'fade':
                                T1 = T2 = L1 = L2 = 0;
                                O1 = 0;
                                O2 = 1;
                                break;
                            case 'mixed':
                                O1 = 0;
                                O2 = 1;
                                if( ls.g.scale2D == 1 ){
                                    T2 = L2 = 0;
                                }
                                break;
                        }
//								}

                        // IMPROVEMENT v4.5.0 Implemented Rotation and Scale into 2D Transitions

                        if((( prop.transition.rotate || prop.transition.rotateX || prop.transition.rotateY ) || ls.g.scale2D != 1 ) && !ls.g.ie78 && prop.transition.type != 'slide' ){
                            tile.css({
                                overflow : 'visible'
                            });
                        }else{
                            tile.css({
                                overflow : 'hidden'
                            });
                        }

                        if( carousel == true){
                            ls.g.curTiles.css({
                                overflow: 'visible'
                            });
                        }else{
                            ls.g.curTiles.css({
                                overflow: 'hidden'
                            });
                        }

                        if( crossfade == true || prop.transition.type == 'slide' || carousel == true ){
                            var tileInCur = tile.appendTo( ls.g.curTiles );
                            var tileInNext = tile.clone().appendTo( ls.g.nextTiles );
                            curTile = $('<div>').addClass('ls-curtile').appendTo( tileInCur );
                        }else{
                            var tileInNext = tile.appendTo( ls.g.nextTiles );
                        }

                        nextTile = $('<div>').addClass('ls-nexttile').appendTo( tileInNext ).css({
                            top : -T1,
                            left : -L1,
                            dispay : 'block',
                            opacity : O1
                        });

                        // Animating tiles

                        var curTileDelay = tileSequence[tiles] * prop.tile.delay;

                        // IMPROVEMENT v4.5.0 Implemented various types of rotations into 2D Transitions

                        var r = prop.transition.rotate ? prop.transition.rotate : 0;
                        var rX = prop.transition.rotateX ? prop.transition.rotateX : 0;
                        var rY = prop.transition.rotateY ? prop.transition.rotateY : 0;

                        // Reversing rotation degrees if slider is moving backwards

                        if( pn == 'prev' ){
                            r = -r;
                            rX = -rX;
                            rY = -rY;
                        }

                        TweenLite.fromTo(nextTile[0],prop.transition.duration/1000,{
                            rotation : r,
                            rotationX : rX,
                            rotationY : rY,
                            scale : ls.g.scale2D
                        },{
                            delay : curTileDelay / 1000,
                            top : 0,
                            left : 0,
                            opacity : O2,
                            rotation : 0,
                            rotationX : 0,
                            rotationY : 0,
                            scale : 1,
                            ease : lsConvertEasing( prop.transition.easing )
                        });

                        // IMPROVEMENT v5.0.0 Smart crossfading for semi-transparent PNG and different size JPG backgrounds

                        if(
                            crossfade == true && (
                            nextBG.length < 1 || (
                            nextBG.length > 0 && (
                            nextBG.attr('src').toLowerCase().indexOf('png') != -1 || (
                            nextBG.width() < ls.g.sliderWidth() || nextBG.height() < ls.g.sliderHeight()
                            )
                            )
                            )
                            )
                        ){
                            TweenLite.to(curTile[0],prop.transition.duration/1000,{
                                delay : curTileDelay / 1000,
                                opacity : 0,
                                ease : lsConvertEasing( prop.transition.easing )
                            });
                        }

                        if( ( prop.transition.type == 'slide' || carousel == true ) && prop.name.toLowerCase().indexOf('mirror') == -1 ){

                            var r2 = 0;

                            if( r != 0 ){
                                r2 = -r;
                            }

                            TweenLite.to(curTile[0],prop.transition.duration/1000,{
                                delay : curTileDelay / 1000,
                                top : T2,
                                left : L2,
                                rotation : r2,
                                scale : ls.g.scale2D,
                                opacity: O1,
                                ease : lsConvertEasing( prop.transition.easing )
                            });
                        }
                    }

                    // Appending the background images of current and next layers into the tiles on both of 2d & 3d transitions
                    // BUGFIX v5.0.0 added Math.floor to prevent '1px bug' under Safari and Firefox

                    if( curBG.length ){
                        if( type == '3d' || ( type == '2d' && ( crossfade == true || prop.transition.type == 'slide' || carousel == true ) ) ){
                            curTile.append($('<img>').attr('src', curBG.attr('src')).css({
                                width : curBG[0].style.width,
                                height : curBG[0].style.height,
                                marginLeft : parseFloat(curBG.css('margin-left')) - parseFloat(tile.position().left),
                                marginTop : parseFloat(curBG.css('margin-top')) - parseFloat(tile.position().top)
                            }));
                        }else if( ls.g.curTiles.children().length == 0 ){
                            ls.g.curTiles.append($('<img>').attr('src', curBG.attr('src')).css({
                                width : curBG[0].style.width,
                                height : curBG[0].style.height,
                                marginLeft : parseFloat(curBG.css('margin-left')),
                                marginTop : parseFloat(curBG.css('margin-top'))
                            }));

                        }
                    }

                    if( nextBG.length ){
                        nextTile.append( $('<img>').attr('src', nextBG.attr('src')).css({
                            width : nextBG[0].style.width,
                            height : nextBG[0].style.height,
                            marginLeft : parseFloat(nextBG.css('margin-left')) - parseFloat(tile.position().left),
                            marginTop : parseFloat(nextBG.css('margin-top')) - parseFloat(tile.position().top)
                        }));
                    }
                }

                // Storing current and next layer elements in a local variable (needed by setTimeout functions in some cases)

                var curLayer = ls.g.curLayer;
                var nextLayer = ls.g.nextLayer;

                // Hiding the background image of the current and next layers (immediately)

                setTimeout(function(){
                    curLayer.find('.ls-bg').css({
                        visibility : 'hidden'
                    });
                },50);

                nextLayer.find('.ls-bg').css({
                    visibility : 'hidden'
                });
                ls.g.ltContainer.removeClass('ls-overflow-hidden');

                // Sliding out the sublayers of the current layer
                // (immediately, delay out and duration out properties are not applied to the sublayers during the new layer transitions)

                curSubLayers(sublayersDurationOut);

                // BUGFIX v5.2.0 prevents background flickering in some cases

                if( sublayersDurationOut === 0 ){
                    sublayersDurationOut = 10;
                }

                // Hiding current layer after its sublayers animated out

                setTimeout(function(){
                    curLayer.css({
                        width: 0
                    });
                }, sublayersDurationOut );

                // Calculating next layer delay

                var nextLayerTimeShift = parseInt(nextLayer.data('timeshift')) ? parseInt(nextLayer.data('timeshift')) : 0;
                var nextLayerDelay = ls.g.totalDuration + nextLayerTimeShift > 0 ? ls.g.totalDuration + nextLayerTimeShift : 0;

                // Showing next layer and sliding sublayers of the next layer in after the current layer transition ended

                setTimeout(function(){
                    if( ls.g.resize == true ){
                        ls.g.ltContainer.empty();
                        curLayer.removeClass('ls-active');
                        ls.makeResponsive( nextLayer, function(){
                            ls.g.resize = false;
                        });
                    }

                    // Sliding in / fading in the sublayers of the next layer

                    nextSubLayers();

                    // NEW FEATURE v4.6.0 Hiding background if the next layer has png BG or has no BG
                    // BUGFIX v4.6.1 Changed some properties to prevent flickering

                    if( nextLayer.find('.ls-bg').length < 1 || ( nextLayer.find('.ls-bg').length > 0 && nextLayer.find('.ls-bg').attr('src').toLowerCase().indexOf('png') != -1 ) ){

                        ls.g.ltContainer.delay(350).fadeOut(300,function(){
                            $(this).empty().show();
                        });
                    }

                    // Displaying the next layer (immediately)

                    nextLayer.css({
                        width : ls.g.sliderWidth(),
                        height : ls.g.sliderHeight()
                    });
                }, nextLayerDelay );

                // BUGFIX v5.0.1 Added a minimal value of ls.g.totalDuration
                // CHANGED in v5.1.0 due to a fading issue in carousel transition

                if( ls.g.totalDuration < 300 ){
                    ls.g.totalDuration = 1000;
                }

                // Changing visibility to visible of the background image of the next layer and overflow to hidden of .ls-lt-container after the transition and calling callback function

                setTimeout(function(){
                    ls.g.ltContainer.addClass('ls-overflow-hidden');

                    nextLayer.addClass('ls-active');

                    if( nextLayer.find('.ls-bg').length ){

                        nextLayer.find('.ls-bg').css({
                            display : 'none',
                            visibility : 'visible'
                        });
                        if( ls.g.ie78 ){
                            nextLayer.find('.ls-bg').css('display','block');
                            setTimeout(function(){
                                curLayerCallback();
                            },500);
                        }else{
                            nextLayer.find('.ls-bg').fadeIn(500, function(){
                                curLayerCallback();
                            });
                        }
                    }else{
                        curLayerCallback();
                    }

                }, ls.g.totalDuration );
            };



            /* Selecting and running the transition */

            // NEW FEATURE v5.2.0 Starts the slider only if it is in the viewport

            var startInViewport = function(){

                ls.g.nextLayer.find(' > *[class*="ls-l"]').each(function(){

                    $(this).css({
                        visibility : 'hidden'
                    });
                });

                ls.g.sliderTop = $(el).offset().top;

                $(window).load(function(){
                    setTimeout(function(){

                        ls.g.sliderTop = $(el).offset().top;
                    }, 20);
                });

                var isSliderInViewport = function(){
                    if( $(window).scrollTop() + $(window).height() - ( ls.g.sliderHeight() / 2 ) > ls.g.sliderTop ){
                        ls.g.firstSlideAnimated = true;
                        if( ls.g.originalAutoStart === true ){
                            //ls.g.autoSlideshow = true;
                            ls.o.autoStart = true;
                            ls.start();
                        }
                        nextSubLayers();
                    }
                }

                $(window).scroll(function(){
                    if( !ls.g.firstSlideAnimated ){
                        isSliderInViewport();
                    }
                });

                isSliderInViewport();
            };

            var tType = ( ( ls.g.nextLayer.data('transition3d') || ls.g.nextLayer.data('transition2d') ) && ls.t ) || ( ( ls.g.nextLayer.data('customtransition3d') || ls.g.nextLayer.data('customtransition2d') ) && ls.ct ) ? 'new' : 'old';

            if( !ls.g.nextLayer.data('transitiontype') ){
                ls.transitionType( ls.g.nextLayer );
            }

            if( ls.g.nextLayer.data('transitiontype') === 'new' ){
                tType = 'new';
            }

            if( ls.o.slideTransition ){
                tType = 'forced';
            }
            if( ls.o.animateFirstSlide && !ls.g.firstSlideAnimated ){

                // BUGFIX v3.5 there is no need to animate 'current' layer if the following conditions are true
                //			   this fixes the sublayer animation direction bug

                if( ls.g.layersNum == 1 ){
                    var curDelay = 0;

                    // IMPROVEMENT v4.1.0 Calling cbAnimStop(); function if only one layer is in the slider

                    ls.o.cbAnimStop(ls.g);

                }else{
                    var nextLayerTimeShift = parseInt(ls.g.nextLayer.data('timeshift')) ? parseInt(ls.g.nextLayer.data('timeshift')) : 0;
                    var d = tType == 'new' ? 0 : curDuration;
                    ls.g.t5 = setTimeout(function(){
                        curLayerCallback();
                    }, d + Math.abs(nextLayerTimeShift) );
                }

                // curDelay must be 0!

                ls.g.totalDuration = true;

                // Animating SUBLAYERS of the first layer

                if( ls.o.startInViewport === true ){

                    startInViewport();
                }else{

                    ls.g.firstSlideAnimated = true;
                    nextSubLayers();
                }

                // Displaying the first layer (immediately)

                ls.g.nextLayer.css({
                    width : ls.g.sliderWidth(),
                    height : ls.g.sliderHeight()
                });

                if( !ls.g.ie78 ){
                    ls.g.nextLayer.find('.ls-bg').css({
                        display : 'none'
                    }).fadeIn(ls.o.sliderFadeInDuration);
                }

                ls.g.isLoading = false;
            }else{

                switch(tType){

                    // Old transitions (sliding layers)

                    case 'old':

                        ls.g.totalDuration = false;

                        // BUGFIX v4.5.0 Removing elements from ls-lt-container is necessary

                        if( ls.g.ltContainer ){
                            ls.g.ltContainer.empty();
                        }

                        // Animating CURRENT LAYER and its SUBLAYERS

                        curLayer();
                        curSubLayers();

                        // Animating NEXT LAYER and its SUBLAYERS

                        nextLayer();
                        nextSubLayers();
                        break;

                    // NEW FEATURE v4.0 2D & 3D Layer Transitions

                    case 'new':

                        if( typeof LSCustomTransition != 'undefined' ){
                            selectCustomTransition();
                        }else{
                            selectTransition();
                        }
                        break;

                    case 'forced':
                        slideTransition( ls.o.slideTransition.type, ls.o.slideTransition.obj );
                        break;
                }
            }
        };

        ls.transitionType = function( el ){

            var ttype =  el.data('ls') ||
            ( 	!el.data('ls') &&
            !el.data('slidedelay') &&
            !el.data('slidedirection') &&
            !el.data('slideoutdirection') &&
            !el.data('delayin') &&
            !el.data('delayout') &&
            !el.data('durationin') &&
            !el.data('durationout') &&
            !el.data('showuntil') &&
            !el.data('easingin') &&
            !el.data('easingout') &&
            !el.data('scalein') &&
            !el.data('scaleout') &&
            !el.data('rotatein') &&
            !el.data('rotateout')
            ) ? 'new' : 'old';
            el.data('transitiontype', ttype);
        };

        ls.sublayerShowUntil = function( sublayer ){

            if( !sublayer.data('transitiontype') ){
                ls.transitionType( sublayer );
            }

            // BUGFIX v5.1.0 Removing ls-videohack class before starting transition

            sublayer.removeClass('ls-videohack');

            var prevOrNext = ls.g.curLayer;

            if( ls.g.prevNext != 'prev' && ls.g.nextLayer ){
                prevOrNext = ls.g.nextLayer;
            }

            var chooseDirection = prevOrNext.data('slidedirection') ? prevOrNext.data('slidedirection') : ls.o.slideDirection;

            // Setting the direction of sliding

            var slideDirection = ls.g.slideDirections[ls.g.prevNext][chooseDirection];

            var curSubSlideDir = sublayer.data('slidedirection') ? sublayer.data('slidedirection') : slideDirection;
            var lml, lmt;

            switch(curSubSlideDir){
                case 'left':
                    lml = -ls.g.sliderWidth();
                    lmt = 0;
                    break;
                case 'right':
                    lml = ls.g.sliderWidth();
                    lmt = 0;
                    break;
                case 'top':
                    lmt = -ls.g.sliderHeight();
                    lml = 0;
                    break;
                case 'bottom':
                    lmt = ls.g.sliderHeight();
                    lml = 0;
                    break;
                case 'fade':
                    lmt = 0;
                    lml = 0;
                    break;
            }

            // NEW FEATURE v1.6 added slideoutdirection to sublayers
            // NEW FEATURES 5.0.0 added axis-free transitions with offsetx and offsety properties

            if( sublayer.data('transitiontype') === 'new' ){
                var curSubSlideOutDir = 'new';
            }else{
                var curSubSlideOutDir = sublayer.data('slideoutdirection') ? sublayer.data('slideoutdirection') : false;
            }

            switch(curSubSlideOutDir){
                case 'left':
                    lml = ls.g.sliderWidth();
                    lmt = 0;
                    break;
                case 'right':
                    lml = -ls.g.sliderWidth();
                    lmt = 0;
                    break;
                case 'top':
                    lmt = ls.g.sliderHeight();
                    lml = 0;
                    break;
                case 'bottom':
                    lmt = -ls.g.sliderHeight();
                    lml = 0;
                    break;
                case 'fade':
                    lmt = 0;
                    lml = 0;
                    break;
                case 'new':
                    if( sublayer.data('offsetxout') ){
                        if( sublayer.data('offsetxout') === 'left' ){
                            lml = ls.g.sliderWidth();
                        }else if( sublayer.data('offsetxout') === 'right' ){
                            lml = -ls.g.sliderWidth();
                        }else{
                            lml = -parseInt( sublayer.data('offsetxout') );
                        }
                    }else{
                        lml = -ls.lt.offsetXOut;
                    }
                    if( sublayer.data('offsetyout') ){
                        if( sublayer.data('offsetyout') === 'top' ){
                            lmt = ls.g.sliderHeight();
                        }else if( sublayer.data('offsetyout') === 'bottom' ){
                            lmt = -ls.g.sliderHeight();
                        }else{
                            lmt = -parseInt( sublayer.data('offsetyout') );
                        }
                    }else{
                        lmt = -ls.lt.offsetYOut;
                    }
                    break;
            }

            // NEW FEATURE v4.5.0 Rotating & Scaling sublayers
            // BUGFIX v4.5.5 changing the default value from 0 to 'none' (because of old jQuery, 1.7.2)
            // NEW FEATURES v5.0.0 Added SkewX, SkewY, ScaleX, ScaleY, RotateX & RotateY transitions

            var curSubRotate = curSubRotateX = curSubRotateY = curSubScale = curSubSkewX = curSubSkewY = curSubScaleX = curSubScaleY = 'none';
//			if( !ls.g.ie78 && ls.g.enableCSS3 ){
            curSubRotate = sublayer.data('rotateout') ? sublayer.data('rotateout') : ls.lt.rotateOut;
            curSubRotateX = sublayer.data('rotatexout') ? sublayer.data('rotatexout') : ls.lt.rotateXOut;
            curSubRotateY = sublayer.data('rotateyout') ? sublayer.data('rotateyout') : ls.lt.rotateYOut;
            curSubScale = sublayer.data('scaleout') ? sublayer.data('scaleout') : ls.lt.scaleOut;
            curSubSkewX = sublayer.data('skewxout') ? sublayer.data('skewxout') : ls.lt.skewXOut;
            curSubSkewY = sublayer.data('skewyout') ? sublayer.data('skewyout') : ls.lt.skewYOut;
            if( curSubScale === 1 ){
                curSubScaleX = sublayer.data('scalexout') ? sublayer.data('scalexout') : ls.lt.scaleXOut;
                curSubScaleY = sublayer.data('scaleyout') ? sublayer.data('scaleyout') : ls.lt.scaleYOut;
            }else{
                curSubScaleX = curSubScaleY = curSubScale;
            }
            var too = sublayer.data('transformoriginout') ? sublayer.data('transformoriginout').split(' ') : ls.lt.transformOriginOut;

            for(var t =0;t<too.length;t++){
                if( too[t].indexOf('%') === -1 && too[t].indexOf('left') !== -1 && too[t].indexOf('right') !== -1 && too[t].indexOf('top') !== -1 && too[t].indexOf('bottom') !== -1 ){
                    too[t] = '' + parseInt( too[t] ) * ls.g.ratio + 'px';
                }
            }
            var curSubTransformOrigin = too.join(' ');
            var curSubPerspective = sublayer.data('perspectiveout') ? sublayer.data('perspectiveout') : ls.lt.perspectiveOut;

//			}

            // IMPROVEMENT v4.0 Distance (P.level): -1

            var endLeft = parseInt( sublayer.css('left') );
            var endTop = parseInt( sublayer.css('top') );

            var curSubPLevel = parseInt( sublayer.attr('class').split('ls-l')[1] );

            var wh = sublayer.outerWidth() > sublayer.outerHeight() ? sublayer.outerWidth() : sublayer.outerHeight();
            var modX = parseInt( curSubRotate ) === 0 ? sublayer.outerWidth() : wh;
            var modY = parseInt( curSubRotate ) === 0 ? sublayer.outerHeight() : wh;

            if( ( curSubPLevel === -1 && curSubSlideOutDir !== 'new' ) || ( sublayer.data('offsetxout') === 'left' || sublayer.data('offsetxout') === 'right' ) ){
                if( lml < 0 ){
                    lml = - ( ls.g.sliderWidth() - endLeft + ( curSubScaleX / 2 - .5 ) * modX + 100  );
                }else if( lml > 0 ){
                    lml = endLeft + ( curSubScaleX / 2 + .5 ) * modX + 100;
                }
            }else{
                lml = lml * ls.g.ratio;
            }

            if( ( curSubPLevel === -1 && curSubSlideOutDir !== 'new' ) || ( sublayer.data('offsetyout') === 'top' || sublayer.data('offsetyout') === 'bottom' ) ){
                if( lmt < 0 ){
                    lmt = - ( ls.g.sliderHeight() - endTop + ( curSubScaleY / 2 - .5 ) * modY + 100  );
                }else if( lmt > 0 ){
                    lmt = endTop + ( curSubScaleY / 2 + .5 ) * modY + 100;
                }
            }else{
                lmt = lmt * ls.g.ratio;
            }

            if( curSubPLevel === -1 || curSubSlideOutDir === 'new' ){
                var curSubPar = 1;
            }else{
                var curSubParMod = ls.g.curLayer.data('parallaxout') ? parseInt(ls.g.curLayer.data('parallaxout')) : ls.o.parallaxOut;
                var curSubPar = curSubPLevel * curSubParMod;
            }

//			var curSubDelay = parseInt( sublayer.data('showuntil') );

            if( sublayer.data('transitiontype') === 'new' ){
                var duO = ls.lt.durationOut;
                var eO = ls.lt.easingOut;
            }else{
                var duO = ls.o.durationOut;
                var eO = ls.o.easingOut;
            }

            var curSubTime = sublayer.data('durationout') ? parseInt(sublayer.data('durationout')) : duO;

            // BUGFIX v5.2.0 duration cannot be 0

            if( curSubTime === 0 ){ curSubTime = 1 }
            var curSubEasing = sublayer.data('easingout') ? sublayer.data('easingout') : eO;

            var css = {
                visibility : 'hidden'
            };

            var transition = {
                rotation : curSubRotate,
                rotationX : curSubRotateX,
                rotationY : curSubRotateY,
                skewX : curSubSkewX,
                skewY : curSubSkewY,
                scaleX : curSubScaleX,
                scaleY : curSubScaleY,
                x : -lml * curSubPar,
                y : -lmt * curSubPar,
                ease : lsConvertEasing( curSubEasing ),
                onComplete : function(){
                    sublayer.css( css );
                }
            };

            if( curSubSlideOutDir == 'fade' || ( !curSubSlideOutDir && curSubSlideDir == 'fade' ) || ( sublayer.data('fadeout') !== 'false' && sublayer.data('transitiontype') === 'new' ) ){
                transition['opacity'] = 0;
                css['opacity'] = sublayer.data( 'originalOpacity' );
            }

            TweenLite.set( sublayer[0],{
                transformPerspective : curSubPerspective,
                transformOrigin : curSubTransformOrigin
            });

            TweenLite.to(sublayer[0],curSubTime/1000,transition);

            // sublayer.stop(true,false).animate( transition, curSubTime, curSubEasing,function(){
            // 	sublayer.css( css );
            // });
        };

        // v3.6 Improved Debug Mode

// 		ls.debug = function(){

// 			ls.d = {
// 				history : $('<div>'),
// 				// adds a H1 (title)
// 				aT : function(content){
// 					$('<h1>'+content+'</h1>').appendTo( ls.d.history );
// 				},
// 				// adds an empty UL
// 				aeU : function(){
// 					$('<ul>').appendTo( ls.d.history );
// 				},
// 				// adds an UL with a LI
// 				aU : function(content){
// 					$('<ul><li>'+content+'</li></ul>').appendTo( ls.d.history );
// 				},
// 				// adds a LI into the last UL
// 				aL : function(content){
// 					$('<li>'+content+'</li>').appendTo( ls.d.history.find('ul:last') );
// 				},
// 				// adds an UL into the last LI of the last UL
// 				aUU : function(content){
// 					$('<ul>').appendTo( ls.d.history.find('ul:last li:last') );
// 				},
// 				// adds a Function to the first LI inside the last UL
// 				aF : function(elem){
// 					ls.d.history.find('ul:last li:last').hover(
// 						function(){
// 							elem.css({
// 								border: '2px solid red',
// 								marginTop : parseInt( elem.css('margin-top') ) - 2,
// 								marginLeft : parseInt( elem.css('margin-left') ) - 2
// 							});
// 						},
// 						function(){
// 							elem.css({
// 								border: '0px',
// 								marginTop : parseInt( elem.css('margin-top') ) + 2,
// 								marginLeft : parseInt( elem.css('margin-left') ) + 2
// 							});
// 						}
// 					);
// 				},
// 				show : function(){
// 					if( !$('body').find('.ls-debug-console').length ){

// 						if( !ls.d.putData ){

// 							// Init code

// 							ls.d.aT('Init code');
// 							ls.d.aeU();

// 							for( var prop in ls.o ){
// 								ls.d.aL(prop+': <strong>' + ls.o[prop] + '</strong>');
// 							}

// //							ls.d.aL('sliderOriginalWidth: <strong>' + ls.g.sliderOriginalWidth + '</strong>');
// //							ls.d.aL('sliderOriginalHeight: <strong>' + ls.g.sliderOriginalHeight + '</strong>');

// 							// Slides, layers data

// 							ls.d.aT('LayerSlider Content');
// 							ls.d.aU('Number of slides found: <strong>' + $(el).find('.ls-slide').length + '</strong>');

// 							$(el).find('.ls-inner .ls-slide, .ls-inner *[class*="ls-l"]').each(function(){

// 								if( $(this).hasClass('ls-slide') ){
// 									ls.d.aU('<strong>SLIDE ' + ( $(this).index() + 1 ) + '</strong>');
// 									ls.d.aUU();
// 									ls.d.aL('<strong>SLIDE ' + ( $(this).index() + 1 ) + ' properties:</strong><br><br>');
// 								}else{
// 									ls.d.aU('&nbsp;&nbsp;&nbsp;&nbsp;Layer ( '+$(this).prop('tagName')+' )');
// 									ls.d.aF($(this));
// 									ls.d.aUU();
// 									ls.d.aL('<strong>'+$(this).prop('tagName')+' layer properties:</strong><br><br>');
// 									ls.d.aL('distance / class: <strong>'+$(this).attr('class')+'</strong>');
// 								}

// 								$.each( $(this).data(),function(name, val) {
// 									ls.d.aL( name +': <strong>' + val + '</strong>');
// 								});
// 							});

// 							ls.d.putData = true;
// 						}

// 						var dc = $('<div>').addClass('ls-debug-console').css({
// 							position: 'fixed',
// 							zIndex: '10000000000',
// 							top: '10px',
// 							right: '10px',
// 							width: '300px',
// 							padding: '20px',
// 							background: 'black',
// 							'border-radius': '10px',
// 							height: $(window).height() - 60,
// 							opacity: 0,
// 							marginRight: 150
// 						}).appendTo( $('body') ).css({
// 							marginRight: 0,
// 							opacity: .9
// 						}).click(function(e){
// 							if(e.shiftKey && e.altKey){
// 								$(this).remove();
// 							}
// 						});
// 						var ds = $('<div>').css({
// 							width: '100%',
// 							height: '100%',
// 							overflow: 'auto'
// 						}).appendTo( dc );
// 						var dd = $('<div>').css({
// 							width: '100%'
// 						}).appendTo( ds ).append( ls.d.history );
// 					}
// 				},
// 				hide : function(){
// 					$('body').find('.ls-debug-console').remove();
// 				}
// 			};

// 			$(el).click(function(e){
// 				if(e.shiftKey && e.altKey){
// 					ls.d.show();
// 				}
// 			});
// 		};

        // initializing
        ls.load();
    };

    var lsConvertEasing = function( e ){

        var t;

        if( e.toLowerCase().indexOf('swing') !== -1 || e.toLowerCase().indexOf('linear') !== -1 ){
            t = Linear.easeNone;
        }else if( e.toLowerCase().indexOf('easeinout') !== -1 ){
            var ee = e.toLowerCase().split('easeinout')[1];
            t = window[ee.charAt(0).toUpperCase() + ee.slice(1)].easeInOut;
        }else if( e.toLowerCase().indexOf('easeout') !== -1 ){
            var ee = e.toLowerCase().split('easeout')[1];
            t = window[ee.charAt(0).toUpperCase() + ee.slice(1)].easeOut;
        }else if( e.toLowerCase().indexOf('easein') !== -1 ){
            var ee = e.toLowerCase().split('easein')[1];
            t = window[ee.charAt(0).toUpperCase() + ee.slice(1)].easeIn;
        }

        return t;
    };

    var lsConvertTransition = function( t, e, type, undef ){

        if( typeof e === 'undefined' ){
            var e = 'easeInOutQuart';
        }
        var tt = {};

        if( t.rotate !== undef ){
            tt.rotation = t.rotate;
        }
        if( t.rotateY !== undef ){
            tt.rotationY = t.rotateY;
        }
        if( t.rotateX !== undef ){
            tt.rotationX = t.rotateX;
        }
        if( type === 'after' ){
            tt.scaleX = tt.scaleY = tt.scaleZ = 1;
        }else if( t.scale3d !== undef ){
            tt.scaleX = tt.scaleY = tt.scaleZ = t.scale3d;
        }

        if( t.delay ){
            tt.delay = type === 'after' ? t.delay/1000 : t.delay;
        }

        tt.ease = lsConvertEasing( e );

        return tt;
    };

    // Support3D checks the CSS3 3D capability of the browser (based on the idea of Modernizr.js)

    var lsSupport3D = function( el ) {

        var testEl = $('<div>'),
            s3d1 = false,
            s3d2 = false,
            properties = ['perspective', 'OPerspective', 'msPerspective', 'MozPerspective', 'WebkitPerspective'];
        transform = ['transformStyle','OTransformStyle','msTransformStyle','MozTransformStyle','WebkitTransformStyle'];

        for (var i = properties.length - 1; i >= 0; i--){
            s3d1 = s3d1 ? s3d1 : testEl[0].style[properties[i]] != undefined;
        };

        // preserve 3D test

        for (var i = transform.length - 1; i >= 0; i--){
            testEl.css( 'transform-style', 'preserve-3d' );
            s3d2 = s3d2 ? s3d2 : testEl[0].style[transform[i]] == 'preserve-3d';
        };

        // If browser has perspective capability and it is webkit, we must check it with this solution because Chrome can give false positive result if GPU acceleration is disabled

        if (s3d1 && testEl[0].style[properties[4]] != undefined){
            testEl.attr('id','ls-test3d').appendTo( el );
            s3d1 = testEl[0].offsetHeight === 3 && testEl[0].offsetLeft === 9;
            testEl.remove();
        }

        return (s3d1 && s3d2);
    };

    // Order array function

    var lsOrderArray = function(x,y,dir) {
        var i = [];
        if(dir=='forward'){
            for( var a=0; a<x;a++){
                for( var b=0; b<y; b++){
                    i.push(a+b*x);
                }
            }
        }else{
            for( var a=x-1; a>-1;a--){
                for( var b=y-1; b>-1; b--){
                    i.push(a+b*x);
                }
            }
        }
        return i;
    };

    // CountProp counts the properties in an object

    var lsCountProp = function(obj) {
        var count = 0;

        for(var prop in obj) {
            if(obj.hasOwnProperty(prop)){
                ++count;
            }
        }
        return count;
    };

    // We need the browser function (removed from jQuery 1.9)

    var lsBrowser = function(){

        uaMatch = function( ua ) {
            ua = ua.toLowerCase();

            var match = /(chrome)[ \/]([\w.]+)/.exec( ua ) ||
                /(webkit)[ \/]([\w.]+)/.exec( ua ) ||
                /(opera)(?:.*version|)[ \/]([\w.]+)/.exec( ua ) ||
                /(msie) ([\w.]+)/.exec( ua ) ||
                ua.indexOf("compatible") < 0 && /(mozilla)(?:.*? rv:([\w.]+)|)/.exec( ua ) ||
                [];

            return {
                browser: match[ 1 ] || "",
                version: match[ 2 ] || "0"
            };
        };

        var matched = uaMatch( navigator.userAgent ), browser = {};

        if ( matched.browser ) {
            browser[ matched.browser ] = true;
            browser.version = matched.version;
        }

        if ( browser.chrome ) {
            browser.webkit = true;
        } else if ( browser.webkit ) {
            browser.safari = true;
        }

        return browser;
    };

    lsPrefixes = function(obj, method){

        var pfx = ['webkit', 'khtml', 'moz', 'ms', 'o', ''];
        var p = 0, m, t;
        while (p < pfx.length && !obj[m]) {
            m = method;
            if (pfx[p] == '') {
                m = m.substr(0,1).toLowerCase() + m.substr(1);
            }
            m = pfx[p] + m;
            t = typeof obj[m];
            if (t != 'undefined') {
                pfx = [pfx[p]];
                return (t == 'function' ? obj[m]() : obj[m]);
            }
            p++;
        }
    };

    // Global parameters (Do not change these settings!)

    layerSlider.global = {

        version				: '5.3.0',

        isMobile			: function(){
            if( navigator.userAgent.match(/Android/i) || navigator.userAgent.match(/webOS/i) || navigator.userAgent.match(/iPhone/i) || navigator.userAgent.match(/iPad/i) || navigator.userAgent.match(/iPod/i) || navigator.userAgent.match(/BlackBerry/i) || navigator.userAgent.match(/Windows Phone/i) ){
                return true;
            }else{
                return false;
            }
        },
        isHideOn3D			: function(el){
            if( el.css('padding-bottom') == 'auto' || el.css('padding-bottom') == 'none' || el.css('padding-bottom') == 0 || el.css('padding-bottom') == '0px' ){
                return true;
            }else{
                return false;
            }
        },

        ie78				: lsBrowser().msie && lsBrowser().version < 9 ? true : false,
        originalAutoStart	: false,
        paused				: false,
        pausedByVideo		: false,
        autoSlideshow		: false,
        isAnimating			: false,
        layersNum			: null,
        prevNext			: 'next',
        slideTimer			: null,
        sliderWidth			: null,
        sliderHeight		: null,
        slideDirections		: {
            prev : {
                left	: 'right',
                right	: 'left',
                top		: 'bottom',
                bottom	: 'top'
            },
            next : {
                left	: 'left',
                right	: 'right',
                top		: 'top',
                bottom	: 'bottom'
            }
        },

        // Default delay time, fadeout and fadein durations of videoPreview images

        v					: {
            d	: 500,
            fo	: 750,
            fi	: 500
        }
    };

    // Layer Transition Defaults

    layerSlider.layerTransitions = {

        offsetXIn			: 80,
        offsetYIn			: 0,
        durationIn			: 1000,
        delayIn				: 0,
        easingIn			: 'easeInOutQuint',
        fadeIn				: true,
        rotateIn			: 0,
        rotateXIn			: 0,
        rotateYIn			: 0,
        scaleIn				: 1,
        scaleXIn			: 1,
        scaleYIn			: 1,
        skewXIn				: 0,
        skewYIn				: 0,
        transformOriginIn	: ['50%','50%','0'],
        perspectiveIn 		: 500,

        offsetXOut			: -80,
        offsetYOut			: 0,
        durationOut			: 400,
        showUntil			: 0,
        easingOut			: 'easeInOutQuint',
        fadeOut				: true,
        rotateOut			: 0,
        rotateXOut			: 0,
        rotateYOut			: 0,
        scaleOut			: 1,
        scaleXOut			: 1,
        scaleYOut			: 1,
        skewXOut			: 0,
        skewYOut			: 0,
        transformOriginOut	: ['50%','50%','0'],
        perspectiveOut 		: 500
    };

    layerSlider.slideTransitions = {

        slideDelay			: 4000							// Time before the next slide will be loading.
    };

    // Global settings (can be modified)

    layerSlider.options = {

        // Layout

        responsive			: true,
        responsiveUnder		: 0,
        layersContainer		: 0,
        fullScreen			: false,					// NEW FEATURE 5.5.0
        appendTo			: '',						// NEW FEATURE 5.5.0

        // Slideshow

        autoStart			: true,
        startInViewport		: true,						// NEW FEATURE v5.2.0
        pauseOnHover		: true,
        firstSlide			: 1,
        animateFirstSlide	: true,
        sliderFadeInDuration: 350,						// NEW FEATURE v5.2.0
        loops				: 0,
        forceLoopNum		: true,
        twoWaySlideshow		: false,
        randomSlideshow		: false,

        // Appearance

        skin				: 'v5',
        skinsPath			: '/layerslider/skins/',
        globalBGColor		: 'transparent',
        globalBGImage		: false,

        // Navigation Area

        navPrevNext			: true,
        navStartStop		: true,
        navButtons			: true,
        keybNav				: true,
        touchNav			: true,
        hoverPrevNext		: true,
        hoverBottomNav		: false,
        showBarTimer		: false,
        showCircleTimer		: true,

        // Thumbnail navigation

        thumbnailNavigation	: 'hover',
        tnContainerWidth	: '60%',
        tnWidth				: 100,
        tnHeight			: 60,
        tnActiveOpacity		: 35,
        tnInactiveOpacity	: 100,

        // Videos

        autoPlayVideos		: true,
        autoPauseSlideshow	: 'auto',
        youtubePreview		: 'maxresdefault.jpg',

        // Preload

        imgPreload			: true,
        lazyLoad 			: true,

        // YourLogo

        yourLogo			: false,
        yourLogoStyle		: 'left: -10px; top: -10px;',
        yourLogoLink		: false,
        yourLogoTarget		: '_self',

        // Optimize for IE7 and IE8

        optimizeForMobile	: true,
        optimizeForIE78		: true,

        // NEW FEATURES 5.2.0 Mobile features

        hideOnMobile		: false,
        hideUnder			: 0,
        hideOver			: 1000000,

        staticImage			: '', // will be available in 5.5.0

        // API functions

        cbInit				: function(element){},
        cbStart				: function(data){},
        cbStop				: function(data){},
        cbPause				: function(data){},
        cbAnimStart			: function(data){},
        cbAnimStop			: function(data){},
        cbPrev				: function(data){},
        cbNext				: function(data){},

        // !!! IMPORTANT !!! The following properties are deprecated from version 5.0.0 DO NOT USE THEM.
        // The slider will recognize these properties in the init code or if you add these properties into the style attribute of the layer
        // but we recommend you to use to new html5 data attribute (data-ls) with the new properties

        slideDelay			: 4000,
        slideDirection		: 'right',
        parallaxIn			: .45,
        parallaxOut			: .45,
        durationIn			: 1000,
        durationOut			: 1000,
        easingIn			: 'easeInOutQuint',
        easingOut			: 'easeInOutQuint',
        delayIn				: 0,
        delayOut			: 0
    };

})(jQuery);
