/*
 * Superclick v1.0.0 - jQuery menu widget
 * Copyright (c) 2013 Joel Birch
 *
 * Dual licensed under the MIT and GPL licenses:
 * 	http://www.opensource.org/licenses/mit-license.php
 * 	http://www.gnu.org/licenses/gpl.html
 */

;(function($) {

	var methods = (function(){
		// private properties and methods go here
		var c = {
				bcClass: 'sf-breadcrumb',
				menuClass: 'sf-js-enabled',
				anchorClass: 'sf-with-ul',
				menuArrowClass: 'sf-arrows'
			},
			outerClick = (function() {
				$(window).load(function() {
					$('body').children().on('click.superclick', function() {
						var $allMenus = $('.sf-js-enabled');
						$allMenus.superclick('reset');
					});
				});
			})(),
			toggleMenuClasses = function($menu, o) {
				var classes = c.menuClass;
				if (o.cssArrows) {
					classes += ' ' + c.menuArrowClass;
				}
				$menu.toggleClass(classes);
			},
			setPathToCurrent = function($menu, o) {
				return $menu.find('li.' + o.pathClass).slice(0, o.pathLevels)
					.addClass(o.activeClass + ' ' + c.bcClass)
						.filter(function() {
							return ($(this).children('.sidebar-submenu').hide().show().length);
						}).removeClass(o.pathClass);
			},
			toggleAnchorClass = function($li) {
				$li.children('a').toggleClass(c.anchorClass);
			},
			toggleTouchAction = function($menu) {
				var touchAction = $menu.css('ms-touch-action');
				touchAction = (touchAction === 'pan-y') ? 'auto' : 'pan-y';
				$menu.css('ms-touch-action', touchAction);
			},
			clickHandler = function(e) {
				var $this = $(this),
					$ul = $this.siblings('.sidebar-submenu'),
					func;

				if ($ul.length) {
					func = ($ul.is(':hidden')) ? over : out;
					$.proxy(func, $this.parent('li'))();
					return false;
				}
			},
			over = function() {
				var $this = $(this),
					o = getOptions($this);
				$this.siblings().superclick('hide').end().superclick('show');
			},
			out = function() {
				var $this = $(this),
					o = getOptions($this);
				$.proxy(close, $this, o)();
			},
			close = function(o) {
				o.retainPath = ( $.inArray(this[0], o.$path) > -1);
				this.superclick('hide');

				if (!this.parents('.' + o.activeClass).length) {
					o.onIdle.call(getMenu(this));
					if (o.$path.length) {
						$.proxy(over, o.$path)();
					}
				}
			},
			getMenu = function($el) {
				return $el.closest('.' + c.menuClass);
			},
			getOptions = function($el) {
				return getMenu($el).data('sf-options');
			};

		return {
			// public methods
			hide: function(instant) {
				if (this.length) {
					var $this = this,
						o = getOptions($this);
						if (!o) {
							return this;
						}
					var not = (o.retainPath === true) ? o.$path : '',
						$ul = $this.find('li.' + o.activeClass).add(this).not(not).removeClass(o.activeClass).children('.sidebar-submenu'),
						speed = o.speedOut;

					if (instant) {
						$ul.show();
						speed = 0;
					}
					o.retainPath = false;
					o.onBeforeHide.call($ul);
					$ul.stop(true, true).animate(o.animationOut, speed, function() {
						var $this = $(this);
						o.onHide.call($this);
					});
				}
				return this;
			},
			show: function() {
				var o = getOptions(this);
				if (!o) {
					return this;
				}
				var $this = this.addClass(o.activeClass),
					$ul = $this.children('.sidebar-submenu');

				o.onBeforeShow.call($ul);
				$ul.stop(true, true).animate(o.animation, o.speed, function() {
					o.onShow.call($ul);
				});
				return this;
			},
			destroy: function() {
				return this.each(function(){
					var $this = $(this),
						o = $this.data('sf-options'),
						$liHasUl = $this.find('li:has(ul)');
					if (!o) {
						return false;
					}
					toggleMenuClasses($this, o);
					toggleAnchorClass($liHasUl);
					toggleTouchAction($this);
					// remove event handlers
					$this.off('.superclick');
					// clear animation's inline display style
					$liHasUl.children('.sidebar-submenu').attr('style', function(i, style){
						return style.replace(/display[^;]+;?/g, '');
					});
					// reset 'current' path classes
					o.$path.removeClass(o.activeClass + ' ' + c.bcClass).addClass(o.pathClass);
					$this.find('.' + o.activeClass).removeClass(o.activeClass);
					o.onDestroy.call($this);
					$this.removeData('sf-options');
				});
			},
			reset: function() {
				return this.each(function(){
					var $menu = $(this),
						o = getOptions($menu),
						$openLis = $( $menu.find('.' + o.activeClass).toArray().reverse() );
					$openLis.children('a').trigger('click');
				});
			},
			init: function(op){
				return this.each(function() {
					var $this = $(this);
					if ($this.data('sf-options')) {
						return false;
					}
					var o = $.extend({}, $.fn.superclick.defaults, op),
						$liHasUl = $this.find('li:has(ul)');
					o.$path = setPathToCurrent($this, o);

					$this.data('sf-options', o);

					toggleMenuClasses($this, o);
					toggleAnchorClass($liHasUl);
					toggleTouchAction($this);
					$this.on('click.superclick', 'a', clickHandler);

					$liHasUl.not('.' + c.bcClass).superclick('hide',true);

					o.onInit.call(this);
				});
			}
		};
	})();

	$.fn.superclick = function(method, args) {
		if (methods[method]) {
			return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
		}
		else if (typeof method === 'object' || ! method) {
			return methods.init.apply(this, arguments);
		}
		else {
			return $.error('Method ' +  method + ' does not exist on jQuery.fn.superclick');
		}
	};

	$.fn.superclick.defaults = {
		activeClass: 'sfHover', // keep 'hover' in classname for compatibility reasons
		pathClass: 'overrideThisToUse',
		pathLevels: 1,
		animation: {opacity:'show'},
		animationOut: {opacity:'hide'},
		speed: 'normal',
		speedOut: 'fast',
		cssArrows: true,
		onInit: $.noop,
		onBeforeShow: $.noop,
		onShow: $.noop,
		onBeforeHide: $.noop,
		onHide: $.noop,
		onIdle: $.noop,
		onDestroy: $.noop
	};

})(jQuery);