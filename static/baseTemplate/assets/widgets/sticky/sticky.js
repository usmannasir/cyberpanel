// jQuery HC-Sticky
// =============
// Version: 1.2.43
// Copyright: Some Web Media
// Author: Some Web Guy
// Author URL: http://twitter.com/some_web_guy
// Website: http://someweblog.com/
// Plugin URL: https://github.com/somewebmedia/hc-sticky
// License: Released under the MIT License www.opensource.org/licenses/mit-license.php
// Description: Cross-browser jQuery plugin that makes any element attached to the page and always visible while you scroll.

(function($, window, undefined) {
    "use strict";

    // console.log shortcut
    var log = function(t){console.log(t)};

    var $window = $(window),
        document = window.document,
        $document = $(document);

    // detect IE version
    var ie = (function(){var undef, v = 3, div = document.createElement('div'), all = div.getElementsByTagName('i'); while (div.innerHTML = '<!--[if gt IE ' + (++v) + ']><i></i><![endif]-->', all[0]){}; return v > 4 ? v : undef})();

    /*----------------------------------------------------
     Global functions
     ----------------------------------------------------*/

    // check for scroll direction and speed
    var getScroll = function() {
        var pageXOffset = window.pageXOffset !== undefined ? window.pageXOffset : (document.compatMode == "CSS1Compat" ? window.document.documentElement.scrollLeft : window.document.body.scrollLeft),
            pageYOffset = window.pageYOffset !== undefined ? window.pageYOffset : (document.compatMode == "CSS1Compat" ? window.document.documentElement.scrollTop : window.document.body.scrollTop);

        if (typeof getScroll.x == 'undefined') {
            getScroll.x = pageXOffset;
            getScroll.y = pageYOffset;
        }
        if (typeof getScroll.distanceX == 'undefined') {
            getScroll.distanceX = pageXOffset;
            getScroll.distanceY = pageYOffset;
        } else {
            getScroll.distanceX = pageXOffset - getScroll.x;
            getScroll.distanceY = pageYOffset - getScroll.y;
        }

        var diffX = getScroll.x - pageXOffset,
            diffY = getScroll.y - pageYOffset;

        getScroll.direction = diffX < 0 ? 'right' :
            diffX > 0 ? 'left' :
                diffY <= 0 ? 'down' :
                    diffY > 0 ? 'up' : 'first';

        getScroll.x = pageXOffset;
        getScroll.y = pageYOffset;
    };
    $window.on('scroll', getScroll);


    // little original style plugin
    $.fn.style = function(style) {
        if (!style) return null;

        var $this = $(this),
            value;

        // clone element
        var $clone = $this.clone().css('display','none');
        // randomize the name of cloned radio buttons, otherwise selections get screwed
        $clone.find('input:radio').attr('name','copy-' + Math.floor((Math.random()*100)+1));
        // insert clone to DOM
        $this.after($clone);

        var getStyle = function(el, style){
            var val;
            if (el.currentStyle) {
                // replace dashes with capitalized letter, e.g. padding-left to paddingLeft
                val = el.currentStyle[style.replace(/-\w/g, function(s){return s.toUpperCase().replace('-','')})];
            } else if (window.getComputedStyle) {
                val = document.defaultView.getComputedStyle(el,null).getPropertyValue(style);
            }
            // check for margin:auto
            val = (/margin/g.test(style)) ? ((parseInt(val) === $this[0].offsetLeft) ? val : 'auto') : val;
            return val;
        };

        if (typeof style == 'string') {
            value = getStyle($clone[0], style);
        } else {
            value = {};
            $.each(style, function(i, s){
                value[s] = getStyle($clone[0], s);
            });
        }

        // destroy clone
        $clone.remove();

        return value || null;
    };


    /*----------------------------------------------------
     jQuery plugin
     ----------------------------------------------------*/

    $.fn.extend({

        hcSticky: function(options) {

            // check if selected element exist in DOM, user doesn't have to worry about that
            if (this.length == 0) return this;

            this.pluginOptions('hcSticky', {
                top: 0,
                bottom: 0,
                bottomEnd: 0,
                innerTop: 0,
                innerSticker: null,
                className: 'sticky',
                wrapperClassName: 'wrapper-sticky',
                stickTo: null,
                responsive: true,
                followScroll: true,
                offResolutions: null,
                onStart: $.noop,
                onStop: $.noop,
                on: true,
                fn: null // used only by the plugin
            }, options || {}, {
                reinit: function(){
                    // just call itself again
                    $(this).hcSticky();
                },
                stop: function(){
                    $(this).pluginOptions('hcSticky', {on: false}).each(function(){
                        var $this = $(this),
                            options = $this.pluginOptions('hcSticky'),
                            $wrapper = $this.parent('.' + options.wrapperClassName);

                        // set current position
                        var top = $this.offset().top - $wrapper.offset().top;
                        $this.css({
                            position: 'absolute',
                            top: top,
                            bottom: 'auto',
                            left: 'auto',
                            right: 'auto'
                        }).removeClass(options.className);
                    });
                },
                off: function(){
                    $(this).pluginOptions('hcSticky', {on: false}).each(function(){
                        var $this = $(this),
                            options = $this.pluginOptions('hcSticky'),
                            $wrapper = $this.parent('.' + options.wrapperClassName);

                        // clear position
                        $this.css({
                            position: 'relative',
                            top: 'auto',
                            bottom: 'auto',
                            left: 'auto',
                            right: 'auto'
                        }).removeClass(options.className);

                        $wrapper.css('height', 'auto');
                    });
                },
                on: function(){
                    $(this).each(function(){
                        $(this).pluginOptions('hcSticky', {
                            on: true,
                            remember: {
                                offsetTop: $window.scrollTop()
                            }
                        }).hcSticky();
                    });
                },
                destroy: function(){
                    var $this = $(this),
                        options = $this.pluginOptions('hcSticky'),
                        $wrapper = $this.parent('.' + options.wrapperClassName);

                    // reset position to original
                    $this.removeData('hcStickyInit').css({
                        position: $wrapper.css('position'),
                        top: $wrapper.css('top'),
                        bottom: $wrapper.css('bottom'),
                        left: $wrapper.css('left'),
                        right: $wrapper.css('right')
                    }).removeClass(options.className);

                    // remove events
                    $window.off('resize', options.fn.resize).off('scroll', options.fn.scroll);

                    // destroy wrapper
                    $this.unwrap();
                }
            });

            // on/off settings
            if (options && typeof options.on != 'undefined') {
                if (options.on) {
                    this.hcSticky('on');
                } else {
                    this.hcSticky('off');
                }
            }

            // stop on commands
            if (typeof options == 'string') return this;

            // do our thing
            return this.each(function(){

                var $this = $(this),
                    options = $this.pluginOptions('hcSticky');

                var $wrapper = (function(){ // wrapper exists
                        var $this_wrapper = $this.parent('.' + options.wrapperClassName);
                        if ($this_wrapper.length > 0) {
                            $this_wrapper.css({
                                'height': $this.outerHeight(true),
                                'width': (function(){
                                    // check if wrapper already has width in %
                                    var width = $this_wrapper.style('width');
                                    if (width.indexOf('%') >= 0 || width == 'auto') {
                                        if ($this.css('box-sizing') == 'border-box' || $this.css('-moz-box-sizing') == 'border-box') {
                                            $this.css('width', $this_wrapper.width());
                                        } else {
                                            $this.css('width', $this_wrapper.width() - parseInt($this.css('padding-left') - parseInt($this.css('padding-right'))));
                                        }
                                        return width;
                                    } else {
                                        return $this.outerWidth(true);
                                    }
                                })()
                            });
                            return $this_wrapper;
                        } else {
                            return false;
                        }
                    })() || (function(){ // wrapper doesn't exist

                        var this_css = $this.style(['width', 'margin-left', 'left', 'right', 'top', 'bottom', 'float', 'display']);
                        var display = $this.css('display');

                        var $this_wrapper = $('<div>', {
                            'class': options.wrapperClassName
                        }).css({
                            'display': display,
                            'height': $this.outerHeight(true),
                            'width': (function(){
                                if (this_css['width'].indexOf('%') >= 0 || (this_css['width'] == 'auto' && display != 'inline-block' && display != 'inline')) { // check if element has width in %
                                    $this.css('width', parseFloat($this.css('width')));
                                    return this_css['width'];
                                } else if (this_css['width'] == 'auto' && (display == 'inline-block' || display == 'inline')) {
                                    return $this.width();
                                } else {
                                    // check if margin is set to 'auto'
                                    return (this_css['margin-left'] == 'auto') ? $this.outerWidth() : $this.outerWidth(true);
                                }
                            })(),
                            'margin': (this_css['margin-left']) ? 'auto' : null,
                            'position': (function(){
                                var position = $this.css('position');
                                return position == 'static' ? 'relative' : position;
                            })(),
                            'float': this_css['float'] || null,
                            'left': this_css['left'],
                            'right': this_css['right'],
                            'top': this_css['top'],
                            'bottom': this_css['bottom'],
                            'vertical-align': 'top'
                        });

                        $this.wrap($this_wrapper);

                        // ie7 inline-block fix
                        if (ie === 7) {
                            if ($('head').find('style#hcsticky-iefix').length === 0) {
                                $('<style id="hcsticky-iefix">.' + options.wrapperClassName + ' {zoom: 1;}</style>').appendTo('head');
                            }
                        }

                        // return appended element
                        return $this.parent();
                    })();


                // check if we should go further
                if ($this.data('hcStickyInit')) return;
                // leave our mark
                $this.data('hcStickyInit', true);


                // check if referring element is document
                var stickTo_document = options.stickTo && (options.stickTo == 'document' || (options.stickTo.nodeType && options.stickTo.nodeType == 9) || (typeof options.stickTo == 'object' && options.stickTo instanceof (typeof HTMLDocument != 'undefined' ? HTMLDocument : Document))) ? true : false;

                // select container ;)
                var $container = options.stickTo
                    ? stickTo_document
                    ? $document
                    : typeof options.stickTo == 'string'
                    ? $(options.stickTo)
                    : options.stickTo
                    : $wrapper.parent();

                // clear sticky styles
                $this.css({
                    top: 'auto',
                    bottom: 'auto',
                    left: 'auto',
                    right: 'auto'
                });

                // attach event on entire page load, maybe some images inside element has been loading, so chek height again
                $window.load(function(){
                    if ($this.outerHeight(true) > $container.height()) {
                        $wrapper.css('height', $this.outerHeight(true));
                        $this.hcSticky('reinit');
                    }
                });

                // functions for attachiung and detaching sticky
                var _setFixed = function(args) {
                        // check if already floating
                        if ($this.hasClass(options.className)) return;

                        // apply styles
                        args = args || {};
                        $this.css({
                            position: 'fixed',
                            top: args.top || 0,
                            left: args.left || $wrapper.offset().left
                        }).addClass(options.className);

                        // start event
                        options.onStart.apply($this[0]);
                        // add class to wrpaeer
                        $wrapper.addClass('sticky-active');
                    },
                    _reset = function(args) {
                        args = args || {};
                        args.position = args.position || 'absolute';
                        args.top = args.top || 0;
                        args.left = args.left || 0;

                        // check if we should apply css
                        if ($this.css('position') != 'fixed' && parseInt($this.css('top')) == args.top) return;

                        // apply styles
                        $this.css({
                            position: args.position,
                            top: args.top,
                            left: args.left
                        }).removeClass(options.className);

                        // stop event
                        options.onStop.apply($this[0]);
                        // remove class from wrpaeer
                        $wrapper.removeClass('sticky-active');
                    };

                // sticky scroll function
                var onScroll = function(init) {

                    // check if we need to run sticky
                    if (!options.on || $this.outerHeight(true) >= $container.height()) return;

                    var top_spacing = (options.innerSticker) ? $(options.innerSticker).position().top : ((options.innerTop) ? options.innerTop : 0),
                        wrapper_inner_top = $wrapper.offset().top,
                        bottom_limit = $container.height() - options.bottomEnd + (stickTo_document ? 0 : wrapper_inner_top),
                        top_limit = $wrapper.offset().top - options.top + top_spacing,
                        this_height = $this.outerHeight(true) + options.bottom,
                        window_height = $window.height(),
                        offset_top = $window.scrollTop(),
                        this_document_top = $this.offset().top,
                        this_window_top = this_document_top - offset_top,
                        bottom_distance;


                    // if sticky has been restarted with on/off wait for it to reach top or bottom
                    if (typeof options.remember != 'undefined' && options.remember) {

                        var position_top = this_document_top - options.top - top_spacing;

                        if (this_height - top_spacing > window_height && options.followScroll) { // element bigger than window with follow scroll on

                            if (position_top < offset_top && offset_top + window_height <= position_top + $this.height()) {
                                // element is in the middle of the screen, let our primary calculations do the work
                                options.remember = false;
                            }

                        } else { // element smaller than window or follow scroll turned off

                            if (options.remember.offsetTop > position_top) {
                                // slide up
                                if (offset_top <= position_top) {
                                    _setFixed({
                                        top: options.top - top_spacing
                                    });
                                    options.remember = false;
                                }
                            } else {
                                // slide down
                                if (offset_top >= position_top) {
                                    _setFixed({
                                        top: options.top - top_spacing
                                    });
                                    options.remember = false;
                                }
                            }

                        }

                        return;
                    }


                    if (offset_top > top_limit) {

                        // http://geek-and-poke.com/geekandpoke/2012/7/27/simply-explained.html

                        if (bottom_limit + options.bottom - (options.followScroll && window_height < this_height ? 0 : options.top) <= offset_top + this_height - top_spacing - ((this_height - top_spacing > window_height - (top_limit - top_spacing) && options.followScroll) ? (((bottom_distance = this_height - window_height - top_spacing) > 0) ? bottom_distance : 0) : 0)) {
                            // bottom reached end
                            _reset({
                                top: bottom_limit - this_height + options.bottom - wrapper_inner_top
                            });
                        } else if (this_height - top_spacing > window_height && options.followScroll) {

                            if (this_window_top + this_height <= window_height) { // element bigger than window with follow scroll on

                                if (getScroll.direction == 'down') {
                                    // scroll down
                                    _setFixed({
                                        top: window_height - this_height
                                    });
                                } else {
                                    // scroll up
                                    if (this_window_top < 0 && $this.css('position') == 'fixed') {
                                        _reset({
                                            top: this_document_top - (top_limit + options.top - top_spacing) - getScroll.distanceY
                                        });
                                    }
                                }

                            } else { // element smaller than window or follow scroll turned off

                                if (getScroll.direction == 'up' && this_document_top >= offset_top + options.top - top_spacing) {
                                    // scroll up
                                    _setFixed({
                                        top: options.top - top_spacing
                                    });
                                } else if (getScroll.direction == 'down' && this_document_top + this_height > window_height && $this.css('position') == 'fixed') {
                                    // scroll down
                                    _reset({
                                        top: this_document_top - (top_limit + options.top - top_spacing) - getScroll.distanceY
                                    });
                                }

                            }
                        } else {
                            // starting (top) fixed position
                            _setFixed({
                                top: options.top - top_spacing
                            });
                        }
                    } else {
                        // reset
                        _reset();
                    }

                };


                // store resize data in case responsive is on
                var resize_timeout = false,
                    $resize_clone = false;

                var onResize = function() {

                    // check if sticky is attached to scroll event
                    attachScroll();

                    // check for off resolutions
                    checkResolutions();

                    // check if we need to run sticky
                    if (!options.on) return;

                    var setLeft = function(){
                        // set new left position
                        if ($this.css('position') == 'fixed') {
                            $this.css('left', $wrapper.offset().left);
                        } else {
                            $this.css('left', 0);
                        }
                    };

                    // check for width change (css media queries)
                    if (options.responsive) {
                        // clone element and make it invisible
                        if (!$resize_clone) {
                            $resize_clone = $this.clone().attr('style', '').css({
                                visibility: 'hidden',
                                height: 0,
                                overflow: 'hidden',
                                paddingTop: 0,
                                paddingBottom: 0,
                                marginTop: 0,
                                marginBottom: 0
                            });
                            $wrapper.after($resize_clone);
                        }

                        var wrapper_width = $wrapper.style('width');
                        var resize_clone_width = $resize_clone.style('width');

                        if (resize_clone_width == 'auto' && wrapper_width != 'auto') {
                            resize_clone_width = parseInt($this.css('width'));
                        }

                        // recalculate wrpaeer width
                        if (resize_clone_width != wrapper_width) {
                            $wrapper.width(resize_clone_width);
                        }

                        // clear previous timeout
                        if (resize_timeout) {
                            clearTimeout(resize_timeout);
                        }
                        // timedout destroing of cloned elements so we don't clone it again and again while resizing the window
                        resize_timeout = setTimeout(function() {
                            // clear timeout id
                            resize_timeout = false;
                            // destroy cloned element
                            $resize_clone.remove();
                            $resize_clone = false;
                        }, 250);
                    }

                    // set new left position
                    setLeft();

                    // recalculate inner element width (maybe original width was in %)
                    if ($this.outerWidth(true) != $wrapper.width()) {
                        var this_w = ($this.css('box-sizing') == 'border-box' || $this.css('-moz-box-sizing') == 'border-box')
                            ? $wrapper.width()
                            : $wrapper.width() - parseInt($this.css('padding-left')) - parseInt($this.css('padding-right'));
                        // subtract margins
                        this_w = this_w - parseInt($this.css('margin-left')) - parseInt($this.css('margin-right'));
                        // set new width
                        $this.css('width', this_w);
                    }
                };


                // remember scroll and resize callbacks so we can attach and detach them
                $this.pluginOptions('hcSticky', {fn: {
                    scroll: onScroll,
                    resize: onResize
                }});


                // check for off resolutions
                var checkResolutions = function(){
                    if (options.offResolutions) {
                        // convert to array
                        if (!$.isArray(options.offResolutions)) {
                            options.offResolutions = [options.offResolutions];
                        }

                        var isOn = true;

                        $.each(options.offResolutions, function(i, rez){
                            if (rez < 0) {
                                // below
                                if ($window.width() < rez * -1) {
                                    isOn = false;
                                    $this.hcSticky('off');
                                }
                            } else {
                                // abowe
                                if ($window.width() > rez) {
                                    isOn = false;
                                    $this.hcSticky('off');
                                }
                            }
                        });

                        // turn on again
                        if (isOn && !options.on) {
                            $this.hcSticky('on');
                        }
                    }
                };
                checkResolutions();


                // attach resize function to event
                $window.on('resize', onResize);


                // attaching scroll function to event
                var attachScroll = function(){
                    // check if element height is bigger than the content
                    if ($this.outerHeight(true) < $container.height()) {
                        var isAttached = false;
                        if ($._data(window, 'events').scroll != undefined) {
                            $.each($._data(window, 'events').scroll, function(i, f){
                                if (f.handler == options.fn.scroll) {
                                    isAttached = true;
                                }
                            });
                        }
                        if (!isAttached) {
                            // run it once to disable glitching
                            options.fn.scroll(true);
                            // attach function to scroll event only once
                            $window.on('scroll', options.fn.scroll);
                        }
                    }
                };
                attachScroll();

            });
        }
    });

})(jQuery, this);



// jQuery HC-PluginOptions
// =============
// Version: 1.0
// Copyright: Some Web Media
// Author: Some Web Guy
// Author URL: http://twitter.com/some_web_guy
// Website: http://someweblog.com/
// License: Released under the MIT License www.opensource.org/licenses/mit-license.php

(function($, undefined) {
    "use strict";

    $.fn.extend({

        pluginOptions: function(pluginName, defaultOptions, userOptions, commands) {

            // create object to store data
            if (!this.data(pluginName)) this.data(pluginName, {});

            // return options
            if (pluginName && typeof defaultOptions == 'undefined') return this.data(pluginName).options;

            // update
            userOptions = userOptions || (defaultOptions || {});

            if (typeof userOptions == 'object' || userOptions === undefined) {

                // options
                return this.each(function(){
                    var $this = $(this);

                    if (!$this.data(pluginName).options) {
                        // init our options and attach to element
                        $this.data(pluginName, {options: $.extend(defaultOptions, userOptions || {})});
                        // attach commands if any
                        if (commands) {
                            $this.data(pluginName).commands = commands;
                        }
                    } else {
                        // update existing options
                        $this.data(pluginName, $.extend($this.data(pluginName), {options: $.extend($this.data(pluginName).options, userOptions || {})}));
                    }
                });

            } else if (typeof userOptions == 'string') {

                return this.each(function(){
                    $(this).data(pluginName).commands[userOptions].call(this);
                });

            } else {

                return this;

            }

        }

    });

})(jQuery);