
(doc=>{
	Array.prototype.unique = function() { return this.filter((v, i, a) => a.indexOf(v) === i); };
	Array.prototype.validUnique = function(fn) {
		return this.filter((v, i, a) => (fn ? fn(v) : v) && a.indexOf(v) === i);
	};

	// full = Monday, December 12, 2022 at 12:16:21 PM Central European Standard Time
	// long = December 12, 2022 at 12:16:21 PM GMT+1
	// medium = Dec 12, 2022, 12:16:21 PM
	// short = 12/12/22, 12:16 PM
	let formats = {
//		LT   : {timeStyle: 'short'}, // Issue in Safari
		LT   : {hour: 'numeric', minute: 'numeric'},
		LLL  : {dateStyle: 'long', timeStyle: 'short'}
	};

	// Format momentjs/PHP date formats to Intl.DateTimeFormat
	// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat
	Date.prototype.format = function (options, UTC, hourCycle) {
		if (typeof options == 'string') {
			if (formats[options]) {
				options = formats[options];
			} else {
				console.log('Date.format('+options+')');
				options = {};
			}
		}
		if (hourCycle) {
			options.hourCycle = hourCycle;
		}
		let el = doc.documentElement;
		return this.toLocaleString(el.dataset.dateLang || el.lang, options);
	};

	Element.prototype.closestWithin = function(selector, parent) {
		const el = this.closest(selector);
		return (el && el !== parent && parent.contains(el)) ? el : null;
	};

	Element.fromHTML = string => {
		const template = doc.createElement('template');
		template.innerHTML = string.trim();
		return template.content.firstChild;
	};

	/**
	 * https://github.com/tc39/proposal-regex-escaping
	 */
	if (!RegExp.escape){
		RegExp.escape = s => String(s).replace(/[\\^$*+?.()|[\]{}]/g, '\\$&');
	}

	/**
	 * Every time the function is executed,
	 * it will delay the execution with the given amount of milliseconds.
	 */
	if (!Function.prototype.debounce) {
		Function.prototype.debounce = function(ms) {
			let func = this, timer;
			return function(...args) {
				timer && clearTimeout(timer);
				timer = setTimeout(()=>{
					func.apply(this, args);
					timer = 0;
				}, ms);
			};
		};
	}

	/**
	 * No matter how many times the event is executed,
	 * the function will be executed only once, after the given amount of milliseconds.
	 */
	if (!Function.prototype.throttle) {
		Function.prototype.throttle = function(ms) {
			let func = this, timer;
			return function(...args) {
				timer = timer || setTimeout(()=>{
						func.apply(this, args);
						timer = 0;
					}, ms);
			};
		};
	}

})(document);

/**
 * Modified version of https://github.com/Bernardo-Castilho/dragdroptouch
 * This is to only support Firefox Mobile.
 * Because touchstart must call preventDefault() to prevent scrolling
 * but then it doesn't work native in Chrome on Android
 */

(doc => {
	let ua = navigator.userAgent.toLowerCase();
	// Chrome on mobile supports drag & drop
	if (ua.includes('mobile') && ua.includes('gecko/')) {

		let opt = { passive: false, capture: false },

			dropEffect = 'move',
			effectAllowed = 'all',
			data = {},

			dataTransfer,
			dragSource,
			isDragging,
			allowDrop,
			lastTarget,
			lastTouch,
			holdInterval,

			img;

/*
		class DataTransferItem
		{
			get kind() { return 'string'; }
		}
*/
		/** https://developer.mozilla.org/en-US/docs/Web/API/DataTransfer */
		class DataTransfer
		{
			get dropEffect() { return dropEffect; }
			set dropEffect(value) { dropEffect = value; }

			get effectAllowed() { return effectAllowed; }
			set effectAllowed(value) { effectAllowed = value; }

			get files() { return []; }
			get items() { return []; } // DataTransferItemList
			get types() { return Object.keys(data); }

			clearData(type) {
				if (type != null) {
					delete data[type];
				} else {
					data = {};
				}
			}

			getData(type) {
				return data[type] || '';
			}

			setData(type, value) {
				data[type] = value;
			}

			constructor() {
				this.setDragImage = setDragImage;
			}
		}

		const
		htmlDrag = b => doc.documentElement.classList.toggle('firefox-drag', b),

		setDragImage = (src, xOffset, yOffset) => {
			img?.remove();
			if (src) {
				// create drag image from custom element or drag source
				img = src.cloneNode(true);
				copyStyle(src, img);
				img._x = xOffset ?? src.clientWidth / 2;
				img._y = yOffset ?? src.clientHeight / 2;
			}
		},

		// clear all members
		reset = () => {
			if (dragSource) {
				clearInterval(holdInterval);
				// dispose of drag image element
				img?.remove();
				isDragging && dispatchEvent(lastTouch, 'dragend', dragSource);
				img = dragSource = lastTouch = lastTarget = dataTransfer = holdInterval = null;
				isDragging = allowDrop = false;
				htmlDrag(false);
			}
		},

		// get point for a touch event
		getPoint = e => {
			e = e.touches ? e.touches[0] : e;
			return { x: e.clientX, y: e.clientY };
		},

		touchend = e => {
			if (dragSource) {
				// finish dragging
				allowDrop && 'touchcancel' !== e.type && dispatchEvent(lastTouch, 'drop', lastTarget);
				reset();
			}
		},

		// get the element at a given touch event
		getTarget = pt => {
			let el = doc.elementFromPoint(pt.x, pt.y);
			while (el && getComputedStyle(el).pointerEvents == 'none') {
				el = el.parentElement;
			}
			return el;
		},

		// move the drag image element
		moveImage = pt => {
			requestAnimationFrame(() => {
				if (img) {
					img.style.left = Math.round(pt.x - img._x) + 'px';
					img.style.top = Math.round(pt.y - img._y) + 'px';
				}
			});
		},

		copyStyle = (src, dst) => {
			// remove potentially troublesome attributes
			['id','class','style','draggable'].forEach(att => dst.removeAttribute(att));
			// copy canvas content
			if (src instanceof HTMLCanvasElement) {
				let cSrc = src, cDst = dst;
				cDst.width = cSrc.width;
				cDst.height = cSrc.height;
				cDst.getContext('2d').drawImage(cSrc, 0, 0);
			}
			// copy style (without transitions)
			let cs = getComputedStyle(src);
			Object.entries(cs).forEach(([key, value]) => key.includes('transition') || (dst.style[key] = value));
			dst.style.pointerEvents = 'none';
			// and repeat for all children
			let i = src.children.length;
			while (i--) copyStyle(src.children[i], dst.children[i]);
		},

		// return false when cancelled
		dispatchEvent = (e, type, target) => {
			if (e && target) {
				let evt = new Event(type, {bubbles:true,cancelable:true});
				evt.button = 0;
				evt.buttons = 1;
				// copy event properties into new event
				['altKey','ctrlKey','metaKey','shiftKey'].forEach(k => evt[k] = e[k]);
				let src = e.touches ? e.touches[0] : e;
				['pageX','pageY','clientX','clientY','screenX','screenY','offsetX','offsetY'].forEach(k => evt[k] = src[k]);
				if (dragSource) {
					evt.dataTransfer = dataTransfer;
				}
				return target.dispatchEvent(evt);
			}
			return false;
		};

/*
		doc.addEventListener('pointerdown', e => {
			doc.addEventListener('pointermove', e => {
				e.clientX
			});
			doc.setPointerCapture(e.pointerId);
		});
		doc.addEventListener('pointerup', e => {
			doc.releasePointerCapture(e.pointerId);
		});
*/
		doc.addEventListener('touchstart', e => {
			// clear all variables
			reset();
			// ignore events that have been handled or that involve more than one touch
			if (e && !e.defaultPrevented && e.touches && e.touches.length < 2) {
				// get nearest draggable element
				dragSource = e.target.closest('[draggable]');
				if (dragSource) {
					// get ready to start dragging
					lastTouch = e;
//					dragSource.style.userSelect = 'none';

					// 1000 ms to wait, chrome on android triggers dragstart in 600
					holdInterval = setTimeout(() => {
						// start dragging
						dataTransfer = new DataTransfer();
						if ((isDragging = dispatchEvent(e, 'dragstart', dragSource))) {
							htmlDrag(true);

							let pt = getPoint(e);

							// create drag image from custom element or drag source
							img || setDragImage(dragSource);
							let style = img.style;
							style.top = style.left = '-9999px';
							style.position = 'fixed';
							style.pointerEvents = 'none';
							style.zIndex = '999999999';
							// add image to document
							moveImage(pt);
							doc.body.append(img);

							dispatchEvent(e, 'dragenter', getTarget(pt));
						} else {
							reset();
						}
					}, 1000);
				}
			}
		}, opt);

		doc.addEventListener('touchmove', e => {
			if (isDragging) {
				// continue dragging
				let pt = getPoint(e),
					target = getTarget(pt);
				lastTouch = e;
				if (target != lastTarget) {
					dispatchEvent(e, 'dragleave', lastTarget);
					dispatchEvent(e, 'dragenter', target);
					lastTarget = target;
				}
				moveImage(pt);
				allowDrop = !dispatchEvent(e, 'dragover', target);
			} else {
				reset();
			}
		}, opt);

		doc.addEventListener('touchend', touchend);
		doc.addEventListener('touchcancel', touchend);
	}

})(document);


(win => {

let
	scope = {},
	_scope = 'all';

const
	doc = document,
	// On Mac we use ⌘ else the Ctrl key
	meta = /Mac OS X/.test(navigator.userAgent) ? 'meta' : 'ctrl',
	_scopes = {
		all: {}
	},
	toArray = v => Array.isArray(v) ? v : v.split(/\s*,\s*/),

	exec = (event, cmd) => {
		try {
			// call the handler and stop the event if neccessary
			if (!event.defaultPrevented && cmd(event) === false) {
				event.preventDefault();
				event.stopPropagation();
			}
		} catch (e) {
			console.error(e);
		}
	},

	shortcuts = {
		on: () => doc.addEventListener('keydown', keydown),
		off: () => doc.removeEventListener('keydown', keydown),
		add: (keys, modifiers, scopes, method) => {
			if (null == method) {
				method = scopes;
				scopes = 'all';
			}
			toArray(scopes).forEach(scope => {
				if (!_scopes[scope]) {
					_scopes[scope] = {};
				}
				toArray(keys).forEach(key => {
					key = key.toLowerCase();
					if (!_scopes[scope][key]) {
						_scopes[scope][key] = {};
					}
					modifiers = toArray(modifiers)
						.map(key => 'meta' == key ? meta : key)
						.unique().sort().join('+');
					if (!_scopes[scope][key][modifiers]) {
						_scopes[scope][key][modifiers] = [];
					}
					_scopes[scope][key][modifiers].push(method);
				});
			});
		},
		setScope: value => {
			_scope = value || 'all';
			scope = _scopes[_scope] || {};
			console.log('Shortcuts scope set to: ' + _scope);
		},
		getScope: () => _scope,
		getMetaKey: () => 'meta' === meta ? '⌘' : 'Ctrl'
	},

	keydown = event => {
		let key = (event.key || '').toLowerCase().replace(' ','space'),
			modifiers = ['alt','ctrl','meta','shift'].filter(v => event[v+'Key']).join('+');
		scope[key]?.[modifiers]?.forEach(cmd => exec(event, cmd));
		!event.defaultPrevented && _scope !== 'all' && _scopes.all[key]?.[modifiers]?.forEach(cmd => exec(event, cmd));
	};

win.shortcuts = shortcuts;

shortcuts.on();

})(this);

/*!!
 * Hasher <http://github.com/millermedeiros/hasher>
 * @author Miller Medeiros
 * @version 1.1.2 (2012/10/31 03:19 PM)
 * Released under the MIT License
 */

(global => {

    //--------------------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------------------

    const
    _hashValRegexp = /#(.*)$/,
    _hashRegexp = /^[#/]+/,
    _hashTrim = /^\/+/g,
    _trimHash = hash => hash?.replace(_hashTrim, '') || '',
    _getWindowHash = () => {
        //parsed full URL instead of getting window.location.hash because Firefox decode hash value (and all the other browsers don't)
        var result = _hashValRegexp.exec( location.href );
        return result?.[1] ? decodeURIComponent(result[1]) : '';
    },
    _registerChange = newHash => {
        if (_hash !== newHash) {
            var oldHash = _hash;
            _hash = newHash; //should come before event dispatch to make sure user can get proper value inside event handler
            _dispatch(_trimHash(newHash), _trimHash(oldHash));
        }
    },
    _setHash = (path, replace) => {
        path = path ? '/' + path.replace(_hashRegexp, '') : path;
        if (path !== _hash){
            // we should store raw value
            _registerChange(path);
            if (path === _hash) {
                path = '#' + encodeURI(path)
                // we check if path is still === _hash to avoid error in
                // case of multiple consecutive redirects [issue #39]
                replace
                    ? location.replace(path)
                    : (location.hash = path);
            }
        }
    },
    _dispatch = (...args) => hasher.active && _bindings.forEach(callback => callback(...args)),

    //--------------------------------------------------------------------------------------
    // Public (API)
    //--------------------------------------------------------------------------------------

    hasher = /** @lends hasher */ {
        clear : () => {
            _bindings = [];
            hasher.active = true;
        },

        /**
         * Signal dispatched when hash value changes.
         * - pass current hash as 1st parameter to listeners and previous hash value as 2nd parameter.
         * @type signals.Signal
         */
        active : true,
        add : callback => _bindings.push(callback),

        /**
         * Start listening/dispatching changes in the hash/history.
         * <ul>
         *   <li>hasher won't dispatch CHANGE events by manually typing a new value or pressing the back/forward buttons before calling this method.</li>
         * </ul>
         */
        init : () => _dispatch(_trimHash(_hash)),

        /**
         * Set Hash value, generating a new history record.
         * @param {...string} path    Hash value without '#'.
         * @example hasher.setHash('lorem/ipsum/dolor') -> '#/lorem/ipsum/dolor'
         */
        setHash : path => _setHash(path),

        /**
         * Set Hash value without keeping previous hash on the history record.
         * @param {...string} path    Hash value without '#'.
         * @example hasher.replaceHash('lorem/ipsum/dolor') -> '#/lorem/ipsum/dolor'
         */
        replaceHash : path => _setHash(path, true)
    };

    var _hash = _getWindowHash(),
        _bindings = [];

    addEventListener('hashchange', () => _registerChange(_getWindowHash()));

    global.hasher = hasher;
})(this);

/** @license
 * Crossroads.js <http://millermedeiros.github.com/crossroads.js>
 * Released under the MIT license
 * Author: Miller Medeiros
 * Version: 0.7.1 - Build: 93 (2012/02/02 09:29 AM)
 */

(global => {

    const isFunction = obj => typeof obj === 'function';

    // Crossroads --------
    //====================

    global.Crossroads = class Crossroads {

        constructor() {
            this._routes = [];
        }

        addRoute(pattern, callback) {
            var route = new Route(pattern, callback, this);
            this._routes.push(route);
            return route;
        }

        parse(request) {
            request = request || '';
            var i = 0,
                routes = this._routes,
                n = routes.length,
                route;
            //should be decrement loop since higher priorities are added at the end of array
            while (n--) {
                route = routes[n];
                if ((!i || route.greedy) && route.match(request)) {
                    route.callback?.(...route._getParamsArray(request));
                    ++i;
                }
            }
        }
    }

    // Route --------------
    //=====================

    class Route {

        constructor(pattern, callback, router) {
            var isRegexPattern = pattern instanceof RegExp;
            Object.assign(this, {
                greedy: false,
                rules: {},
                _router: router,
                _pattern: pattern,
                _paramsIds: isRegexPattern ? null : captureVals(PARAMS_REGEXP, pattern),
                _optionalParamsIds: isRegexPattern ? null : captureVals(OPTIONAL_PARAMS_REGEXP, pattern),
                _matchRegexp: isRegexPattern ? pattern : compilePattern(pattern),
                callback: isFunction(callback) ? callback : null
            });
        }

        match(request) {
            // validate params even if regexp.
            var values = this._getParamsObject(request);
            return this._matchRegexp.test(request)
             && 0 == Object.entries(this.rules).filter(([key, validationRule]) => {
                var val = values[key],
                    isValid = false;
                if (key === 'normalize_'
                 || (val == null && this._optionalParamsIds?.includes(key))) {
                    isValid = true;
                }
                else if (validationRule instanceof RegExp) {
                    isValid = validationRule.test(val);
                }
                else if (Array.isArray(validationRule)) {
                    isValid = validationRule.includes(val);
                }
                else if (isFunction(validationRule)) {
                    isValid = validationRule(val, request, values);
                }
                // fail silently if validationRule is from an unsupported type
                return !isValid;
            }).length;
        }

        _getParamsObject(request) {
            var values = getParamValues(request, this._matchRegexp) || [],
                n = values.length;
            if (this._paramsIds) {
                while (n--) {
                    values[this._paramsIds[n]] = values[n];
                }
            }
            return values;
        }

        _getParamsArray(request) {
            var norm = this.rules.normalize_;
            return isFunction(norm)
                ? norm(request, this._getParamsObject(request))
                : getParamValues(request, this._matchRegexp);
        }

    }



    // Pattern Lexer ------
    //=====================

    const
        ESCAPE_CHARS_REGEXP = /[\\.+*?^$[\](){}/'#]/g, //match chars that should be escaped on string regexp
        UNNECESSARY_SLASHES_REGEXP = /\/$/g, //trailing slash
        OPTIONAL_SLASHES_REGEXP = /([:}]|\w(?=\/))\/?(:)/g, //slash between `::` or `}:` or `\w:`. $1 = before, $2 = after
        REQUIRED_SLASHES_REGEXP = /([:}])\/?(\{)/g, //used to insert slash between `:{` and `}{`

        REQUIRED_PARAMS_REGEXP = /\{([^}]+)\}/g, //match everything between `{ }`
        OPTIONAL_PARAMS_REGEXP = /:([^:]+):/g, //match everything between `: :`
        PARAMS_REGEXP = /(?:\{|:)([^}:]+)(?:\}|:)/g, //capture everything between `{ }` or `: :`

        //used to save params during compile (avoid escaping things that
        //shouldn't be escaped).
        SAVE_REQUIRED_PARAMS = '__CR_RP__',
        SAVE_OPTIONAL_PARAMS = '__CR_OP__',
        SAVE_REQUIRED_SLASHES = '__CR_RS__',
        SAVE_OPTIONAL_SLASHES = '__CR_OS__',
        SAVED_REQUIRED_REGEXP = new RegExp(SAVE_REQUIRED_PARAMS, 'g'),
        SAVED_OPTIONAL_REGEXP = new RegExp(SAVE_OPTIONAL_PARAMS, 'g'),
        SAVED_OPTIONAL_SLASHES_REGEXP = new RegExp(SAVE_OPTIONAL_SLASHES, 'g'),
        SAVED_REQUIRED_SLASHES_REGEXP = new RegExp(SAVE_REQUIRED_SLASHES, 'g'),

        captureVals = (regex, pattern) => {
            var vals = [], match;
            while ((match = regex.exec(pattern))) {
                vals.push(match[1]);
            }
            return vals;
        },

        getParamValues = (request, regexp) => {
            var vals = regexp.exec(request);
            vals?.shift();
            return vals;
        },
        compilePattern = pattern => {
            return new RegExp('^' + (pattern
                ? pattern
                    // tokenize, save chars that shouldn't be escaped
                    .replace(UNNECESSARY_SLASHES_REGEXP, '')
                    .replace(OPTIONAL_SLASHES_REGEXP, '$1'+ SAVE_OPTIONAL_SLASHES +'$2')
                    .replace(REQUIRED_SLASHES_REGEXP, '$1'+ SAVE_REQUIRED_SLASHES +'$2')
                    .replace(OPTIONAL_PARAMS_REGEXP, SAVE_OPTIONAL_PARAMS)
                    .replace(REQUIRED_PARAMS_REGEXP, SAVE_REQUIRED_PARAMS)
                    .replace(ESCAPE_CHARS_REGEXP, '\\$&')
                    // untokenize
                    .replace(SAVED_OPTIONAL_SLASHES_REGEXP, '\\/?')
                    .replace(SAVED_REQUIRED_SLASHES_REGEXP, '\\/')
                    .replace(SAVED_OPTIONAL_REGEXP, '([^\\/]+)?/?')
                    .replace(SAVED_REQUIRED_REGEXP, '([^\\/]+)')
                : ''
            ) + '/?$'); //trailing slash is optional
        };

})(this);

/* RainLoop Webmail (c) RainLoop Team | MIT */
(doc => {
	const
		defined = v => undefined !== v,
		/**
		 * @param {*} aItems
		 * @param {Function} fFileCallback
		 * @param {number=} iLimit = 20
		 */
		getDataFromFiles = (aItems, fFileCallback, iLimit) =>
		{
			if (aItems?.length)
			{
				let
					oFile,
					iCount = 0,
					bCallLimit = false
				;

				[...aItems].forEach(oItem => {
					if (oItem) {
						if (iLimit && iLimit < ++iCount) {
							if (!bCallLimit) {
								bCallLimit = true;
//								fLimitCallback(iLimit);
							}
						} else {
							oFile = getDataFromFile(oItem);
							oFile && fFileCallback(oFile);
						}
					}
				});
			}
		},

		addEventListeners = (element, obj) =>
			Object.entries(obj).forEach(([key, value]) => element.addEventListener(key, value)),

		/**
		 * @param {*} oFile
		 * @return {Object}
		 */
		getDataFromFile = oFile =>
		{
			return oFile.size
				? {
					fileName: (oFile.name || '').replace(/^.*\/([^/]*)$/, '$1'),
					size: oFile.size,
					file: oFile
				}
				: null; // Folder
		},

		eventContainsFiles = oEvent => oEvent.dataTransfer.types.includes('Files');

	class Queue extends Array
	{
		push(fn, ...args) {
			super.push([fn, args]);
			this.call();
		}
		call() {
			if (!this.running) {
				this.running = true;
				let f;
				while ((f = this.shift())) f[0](...f[1]);
				this.running = false;
			}
		}
	}

	/**
	 * @constructor
	 * @param {Object=} options
	 */
	class Jua
	{
		constructor(options)
		{
			let timer,
				el = options.clickElement;

			const self = this,
				timerStart = fn => {
					timerStop();
					timer = setTimeout(fn, 200);
				},
				timerStop = () => {
					timer && clearTimeout(timer);
					timer = 0;
				};

			self.oEvents = {
				onSelect: null,
				onStart: null,
				onComplete: null,
				onProgress: null,
				onDragEnter: null,
				onDragLeave: null,
				onBodyDragEnter: null,
				onBodyDragLeave: null
			};

			self.oXhrs = {};
			self.oUids = {};
			self.options = Object.assign({
					action: '',
					name: 'uploader',
					limit: 0,
//					clickElement:
//					dragAndDropElement:
				}, options || {});
			self.oQueue = new Queue();

			// clickElement
			if (el) {
				el.style.position = 'relative';
				el.style.overflow = 'hidden';
				if ('inline' === el.style.display) {
					el.style.display = 'inline-block';
				}

				self.generateNewInput(el);
			}

			el = options.dragAndDropElement;
			if (el) {
				addEventListeners(doc, {
					dragover: oEvent => {
						if (eventContainsFiles(oEvent)) {
							timerStop();
							if (el.contains(oEvent.target)) {
								oEvent.dataTransfer.dropEffect = 'copy';
								oEvent.stopPropagation();
							} else {
								oEvent.dataTransfer.dropEffect = 'none';
							}
							oEvent.preventDefault();
						}
					},
					dragenter: oEvent => {
						if (eventContainsFiles(oEvent)) {
							timerStop();
							oEvent.preventDefault();
							self.runEvent('onBodyDragEnter', oEvent);
							if (el.contains(oEvent.target)) {
								timerStop();
								self.runEvent('onDragEnter', el, oEvent);
							}
						}
					},
					dragleave: oEvent => {
						if (eventContainsFiles(oEvent)) {
							let oRelatedTarget = doc.elementFromPoint(oEvent.clientX, oEvent.clientY);
							if (!oRelatedTarget || !el.contains(oRelatedTarget)) {
								self.runEvent('onDragLeave', el, oEvent);
							}
							timerStart(() => self.runEvent('onBodyDragLeave', oEvent))
						}
					},
					drop: oEvent => {
						if (eventContainsFiles(oEvent)) {
							timerStop();
							oEvent.preventDefault();
							if (el.contains(oEvent.target)) {
								getDataFromFiles(
									oEvent.files || oEvent.dataTransfer.files,
									oFile => {
										if (oFile) {
											self.addFile(oFile);
										}
									},
									self.options.limit
								);
							}
						}
						self.runEvent('onDragLeave', oEvent);
						self.runEvent('onBodyDragLeave', oEvent);
					}
				});
			}
		}

		/**
		 * @param {string} sName
		 * @param {Function} fFunc
		 */
		on(sName, fFunc)
		{
			this.oEvents[sName] = fFunc;
			return this;
		}

		/**
		 * @param {string} sName
		 */
		runEvent(sName, ...aArgs)
		{
			this.oEvents[sName]?.apply(null, aArgs);
		}

		/**
		 * @param {string} sName
		 */
		getEvent(sName)
		{
			return this.oEvents[sName] || null;
		}

		/**
		 * @param {Object} oFileInfo
		 */
		addFile(oFileInfo)
		{
			const sUid = 'jua-uid-' + Jua.randomId(16) + '-' + (Date.now().toString()),
				fOnSelect = this.getEvent('onSelect');
			if (oFileInfo && (!fOnSelect || (false !== fOnSelect(sUid, oFileInfo))))
			{
				this.oUids[sUid] = true;
				this.oQueue.push((...args) => this.uploadTask(...args), sUid, oFileInfo);
			}
			else
			{
				this.cancel(sUid);
			}
		}

		/**
		 * @param {string} sUid
		 * @param {?} oFileInfo
		 */
		uploadTask(sUid, oFileInfo)
		{
			if (false === this.oUids[sUid] || !oFileInfo || !oFileInfo.file)
			{
				return false;
			}

			try
			{
				const
					self = this,
					oXhr = new XMLHttpRequest(),
					oFormData = new FormData(),
					sAction = this.options.action,
					fStartFunction = this.getEvent('onStart'),
					fProgressFunction = this.getEvent('onProgress')
				;

				oXhr.open('POST', sAction, true);

				if (fProgressFunction && oXhr.upload)
				{
					oXhr.upload.onprogress = oEvent => {
						if (oEvent && oEvent.lengthComputable && defined(oEvent.loaded) && defined(oEvent.total))
						{
							fProgressFunction(sUid, oEvent.loaded, oEvent.total);
						}
					};
				}

				oXhr.onreadystatechange = () => {
					if (4 === oXhr.readyState)
					{
						delete self.oXhrs[sUid];
						let bResult = false,
							oResult = null;
						if (200 === oXhr.status)
						{
							try
							{
								oResult = JSON.parse(oXhr.responseText);
								bResult = true;
							}
							catch (e)
							{
								console.error(e);
							}
						}
						this.getEvent('onComplete')(sUid, bResult, oResult);
					}
				};

				fStartFunction && fStartFunction(sUid);

				oFormData.append(this.options.name, oFileInfo.file);

				oXhr.send(oFormData);

				this.oXhrs[sUid] = oXhr;
				return true;
			}
			catch (oError)
			{
				console.error(oError)
			}

			return false;
		}

		generateNewInput(oClickElement)
		{
			if (oClickElement)
			{
				const self = this,
					limit = self.options.limit,
					oInput = doc.createElement('input'),
					onClick = ()=>oInput.click();

				oInput.type = 'file';
				oInput.tabIndex = -1;
				oInput.style.display = 'none';
				oInput.multiple = 1 != limit;

				oClickElement.addEventListener('click', onClick);

				oInput.addEventListener('input', () => {
					const fFileCallback = oFile => {
						self.addFile(oFile);
						setTimeout(() => {
							oInput.remove();
							oClickElement.removeEventListener('click', onClick);
							self.generateNewInput(oClickElement);
						}, 10);
					};
					if (oInput.files?.length) {
						getDataFromFiles(oInput.files, fFileCallback, limit);
					} else {
						fFileCallback({
							fileName: oInput.value.split(/\\\//).pop(),
							size: null,
							file : null
						});
					}
				});
			}
		}

		/**
		 * @param {string} sUid
		 */
		cancel(sUid)
		{
			this.oUids[sUid] = false;
			if (this.oXhrs[sUid])
			{
				try
				{
					this.oXhrs[sUid].abort && this.oXhrs[sUid].abort();
				}
				catch (oError)
				{
					console.error(oError);
				}

				delete this.oXhrs[sUid];
			}
		}
	}

	Jua.randomId = len => {
		let arr = new Uint8Array((len || 32) / 2);
		crypto.getRandomValues(arr);
		return arr.map(dec => dec.toString(16).padStart(2,'0')).join('');
	}

	this.Jua = Jua;

})(document);

/*!
	* Native JavaScript for Bootstrap v3.0.10 (https://thednp.github.io/bootstrap.native/)
	* Copyright 2015-2020 © dnp_theme
	* Licensed under MIT (https://github.com/thednp/bootstrap.native/blob/master/LICENSE)
	*/

(doc => {
	const
		setFocus = element => element.focus ? element.focus() : element.setActive(),
		isArrow = e => 'ArrowUp' === e.key || 'ArrowDown' === e.key;

	this.BSN = {
		Dropdown: function(toggleBtn) {
			let menu, menuItems = [];
			const self = this,
				parent = toggleBtn.parentNode,
				preventEmptyAnchor = e => {
					const t = e.target;
					('#' === (t.href || t.parentNode?.href)?.slice(-1)) && e.preventDefault();
				},
				open = bool => {
					menu?.classList.toggle('show', bool);
					parent.classList.toggle('show', bool);
					toggleBtn.setAttribute('aria-expanded', bool);
					toggleBtn.open = bool;
					if (bool) {
						toggleBtn.removeEventListener('click',clickHandler);
					} else {
						setTimeout(() => toggleBtn.addEventListener('click',clickHandler), 1);
					}
				},
				toggleEvents = () => {
					const action = (toggleBtn.open ? 'add' : 'remove') + 'EventListener';
					doc[action]('click',dismissHandler);
					doc[action]('keydown',preventScroll);
					doc[action]('keyup',keyHandler);
					doc[action]('focus',dismissHandler);
				},
				dismissHandler = e => {
					const eventTarget = e.target;
					if ((!menu.contains(eventTarget) && !toggleBtn.contains(eventTarget)) || e.type !== 'focus') {
						self.hide();
						preventEmptyAnchor(e);
					}
				},
				clickHandler = e => {
					self.show();
					preventEmptyAnchor(e);
				},
				preventScroll = e => isArrow(e) && e.preventDefault(),
				keyHandler = e => {
					if ('Escape' === e.key) {
						self.toggle();
					} else if (isArrow(e)) {
						let activeItem = doc.activeElement,
							isMenuButton = activeItem === toggleBtn,
							idx = isMenuButton ? 0 : menuItems.indexOf(activeItem);
						if (parent.contains(activeItem)) {
							if (!isMenuButton) {
								idx = 'ArrowUp' === e.key
									? (idx > 1 ? idx-1 : 0)
									: (idx < menuItems.length-1 ? idx+1 : idx);
							}
							menuItems[idx] && setFocus(menuItems[idx]);
						} else {
							console.log('activeElement not in menu');
						}
					}
				};
			self.show = () => {
				menu = parent.querySelector('.dropdown-menu');
				menuItems = [...menu.querySelectorAll('A')].filter(item => 'none' != item.parentNode.style.display);
				!('tabindex' in menu) && menu.setAttribute('tabindex', '0');
				open(true);
				setTimeout(() => {
					setFocus( menu.getElementsByTagName('INPUT')[0] || toggleBtn );
					toggleEvents();
				},1);
			};
			self.hide = () => {
				open(false);
				toggleEvents();
				setFocus(toggleBtn);
			};
			self.toggle = () => toggleBtn.open ? self.hide() : self.show();
			open(false);
			toggleBtn.Dropdown = self;
		}
	};

})(document);

/*!
 * Knockout JavaScript library v3.5.1-sm
 * (c) The Knockout.js team - http://knockoutjs.com/
 * License: MIT (http://www.opensource.org/licenses/mit-license.php)
 */

(R=>{function L(a,b){return a===b&&a!==Object(a)}function ca(a,b){var d;return()=>{d||(d=setTimeout(()=>{d=0;a()},b))}}function da(a,b){var d;return()=>{clearTimeout(d);d=setTimeout(a,b)}}function ea(a,b){b?.dispose?.()}function fa(a,b){var d=this.Lb,e=d[x];e.X||(this.Ma&&this.va[b]?(d.kb(b,a,this.va[b]),this.va[b]=null,--this.Ma):e.v[b]||d.kb(b,a,e.A?{S:a}:d.Cb(a)),a.ea&&a.Gb())}var J=R.document,M={},c="undefined"!==typeof M?M:{};c.U=(a,b)=>{a=a.split(".");for(var d=c,e=0,g=a.length-1;e<g;e++)d=
d[a[e]];d[a[g]]=b};c.g={extend:(a,b)=>b?Object.assign(a,b):a,K:(a,b)=>a&&Object.entries(a).forEach(d=>b(d[0],d[1])),Qa:a=>[...a.childNodes].forEach(b=>c.removeNode(b)),Wb:a=>{a=[...a];var b=(a[0]?.ownerDocument||J).createElement("div");a.forEach(d=>b.append(c.ha(d)));return b},ua:(a,b)=>Array.prototype.map.call(a,b?d=>c.ha(d.cloneNode(!0)):d=>d.cloneNode(!0)),pa:(a,b)=>{c.g.Qa(a);b&&a.append(...b)},xa:(a,b)=>{if(a.length){for(b=8===b.nodeType&&b.parentNode||b;a.length&&a[0].parentNode!==b;)a.splice(0,
1);for(;1<a.length&&a[a.length-1].parentNode!==b;)--a.length;if(1<a.length){b=a[0];var d=a[a.length-1];for(a.length=0;b!==d;)a.push(b),b=b.nextSibling;a.push(d)}}return a},Bb:a=>null==a?"":a.trim?a.trim():a.toString().replace(/^[\s\xa0]+|[\s\xa0]+$/g,""),Pa:a=>a.ownerDocument.documentElement.contains(1!==a.nodeType?a.parentNode:a),Db:(a,b)=>{if(!a?.nodeType)throw Error("element must be a DOM node when calling triggerEvent");a.dispatchEvent(new Event(b))},h:a=>c.W(a)?a():a,Za:(a,b)=>a.textContent=
c.g.h(b)};c.U("utils",c.g);c.U("unwrap",c.g.h);(()=>{let a=0,b="__ko__"+Date.now(),d=new WeakMap;c.g.l={get:(e,g)=>(d.get(e)||{})[g],set:(e,g,l)=>{d.has(e)?d.get(e)[g]=l:d.set(e,{[g]:l});return l},Ra(e,g,l){return this.get(e,g)||this.set(e,g,l)},clear:e=>d.delete(e),Z:()=>a++ +b}})();c.g.N=(()=>{var a=c.g.l.Z(),b={1:1,8:1,9:1},d={1:1,9:1};const e=(f,h)=>{var k=c.g.l.get(f,a);h&&!k&&(k=new Set,c.g.l.set(f,a,k));return k},g=f=>{var h=e(f);h&&(new Set(h)).forEach(k=>k(f));c.g.l.clear(f);d[f.nodeType]&&
l(f.childNodes,!0)},l=(f,h)=>{for(var k=[],m,p=0;p<f.length;p++)if(!h||8===f[p].nodeType)if(g(k[k.length]=m=f[p]),f[p]!==m)for(;p--&&!k.includes(f[p]););};return{addDisposeCallback:(f,h)=>{if("function"!=typeof h)throw Error("Callback must be a function");e(f,1).add(h)},Ya:(f,h)=>{var k=e(f);k&&(k.delete(h),k.size||c.g.l.set(f,a,null))},ha:f=>{c.u.I(()=>{b[f.nodeType]&&(g(f),d[f.nodeType]&&l(f.getElementsByTagName("*")))});return f},removeNode:f=>{c.ha(f);f.parentNode&&f.parentNode.removeChild(f)}}})();
c.ha=c.g.N.ha;c.removeNode=c.g.N.removeNode;c.U("utils.domNodeDisposal",c.g.N);c.extenders={debounce:(a,b)=>a.Da(d=>da(d,b)),rateLimit:(a,b)=>a.Da(d=>ca(d,b)),notify:(a,b)=>{a.ka="always"==b?null:L}};class ha{constructor(a,b,d){this.S=a;this.eb=b;this.za=d;this.Ha=!1;this.H=this.da=null}dispose(){this.Ha||(this.H&&c.g.N.Ya(this.da,this.H),this.Ha=!0,this.za(),this.S=this.eb=this.za=this.da=this.H=null)}s(a){this.da=a;c.g.N.addDisposeCallback(a,this.H=this.dispose.bind(this))}}c.P=function(){Object.setPrototypeOf(this,
N);N.init(this)};var N={init:a=>{a.R=new Map;a.R.set("change",new Set);a.jb=1},subscribe:function(a,b,d){var e=this;d=d||"change";var g=new ha(e,b?a.bind(b):a,()=>{e.R.get(d).delete(g);e.Ia?.(d)});e.Ja?.(d);e.R.has(d)||e.R.set(d,new Set);e.R.get(d).add(g);return g},B(a,b){b=b||"change";"change"===b&&this.Ea();if(this.na(b)){b="change"===b&&this.Eb||new Set(this.R.get(b));try{c.u.nb(),b.forEach(d=>{d.Ha||d.eb(a)})}finally{c.u.end()}}},ya(){return this.jb},Rb(a){return this.ya()!==a},Ea(){++this.jb},
Da(a){var b=this,d=c.W(b),e,g,l,f,h;b.ra||(b.ra=b.B,b.B=(m,p)=>{p&&"change"!==p?"beforeChange"===p?b.gb(m):b.ra(m,p):b.hb(m)});var k=a(()=>{b.ea=!1;d&&f===b&&(f=b.fb?b.fb():b());var m=g||h&&b.Ba(l,f);h=g=e=!1;m&&b.ra(l=f)});b.hb=(m,p)=>{p&&b.ea||(h=!p);b.Eb=new Set(b.R.get("change"));b.ea=e=!0;f=m;k()};b.gb=m=>{e||(l=m,b.ra(m,"beforeChange"))};b.ib=()=>{h=!0};b.Gb=()=>{b.Ba(l,b.L(!0))&&(g=!0)}},na(a){return(this.R.get(a)||[]).size},Ba(a,b){return!this.ka||!this.ka(a,b)},toString:()=>"[object Object]",
extend:function(a){var b=this;a&&c.g.K(a,(d,e)=>{d=c.extenders[d];"function"==typeof d&&(b=d(b,e)||b)});return b}};c.P.fn=Object.setPrototypeOf(N,Function.prototype);c.Vb=a=>"function"==typeof a?.subscribe&&"function"==typeof a.B;(()=>{let a=[],b,d=0;c.u={nb:e=>{a.push(b);b=e},end:()=>b=a.pop(),zb:e=>{if(b){if(!c.Vb(e))throw Error("Only subscribable things can act as dependencies");b.Jb.call(b.Kb,e,e.Fb||(e.Fb=++d))}},I(e,g,l){try{return a.push(b),b=void 0,e.apply(g,l||[])}finally{b=a.pop()}},ma:()=>
b?.o.ma(),Ca:()=>b?.Ca,o:()=>b?.o}})();const A=Symbol("_latestValue");c.$=a=>{function b(){if(0<arguments.length)return b.Ba(b[A],arguments[0])&&(b.cb(),b[A]=arguments[0],b.valueHasMutated()),this;c.u.zb(b);return b[A]}b[A]=a;Object.defineProperty(b,"length",{get:()=>b[A]?.length});c.P.fn.init(b);return Object.setPrototypeOf(b,E)};var E={toJSON:function(){let a=this[A];return a?.toJSON?.()||a},ka:L,L(){return this[A]},valueHasMutated:function(){this.B(this[A],"spectate");this.B(this[A])},cb(){this.B(this[A],
"beforeChange")}};Object.setPrototypeOf(E,c.P.fn);var D=c.$.Zb="__ko_proto__";E[D]=c.$;c.W=a=>{if((a="function"==typeof a&&a[D])&&a!==E[D]&&a!==c.o.fn[D])throw Error("Invalid object that looks like an observable; possibly from another Knockout instance");return!!a};c.vb=a=>"function"==typeof a&&(a[D]===E[D]||a[D]===c.o.fn[D]&&a.Sb);c.U("observable",c.$);c.U("isObservable",c.W);c.U("observable.fn",E);c.observableArray=a=>{a=a||[];if(!Array.isArray(a))throw Error("The argument passed when initializing an observable array must be an array, or null, or undefined.");
return Object.setPrototypeOf(c.$(a),c.observableArray.fn).extend({trackArrayChanges:!0})};const S=Symbol("IS_OBSERVABLE_ARRAY");c.observableArray.fn=Object.setPrototypeOf({[S]:1,remove:function(a){for(var b=this.L(),d=!1,e="function"!=typeof a||c.W(a)?f=>f===a:a,g=b.length;g--;){var l=b[g];if(e(l)){if(b[g]!==l)throw Error("Array modified during remove; cannot remove item");d||this.cb();d=!0;b.splice(g,1)}}d&&this.valueHasMutated()}},c.$.fn);Object.getOwnPropertyNames(Array.prototype).forEach(a=>{"function"===
typeof Array.prototype[a]&&"constructor"!=a&&("copyWithin fill pop push reverse shift sort splice unshift".split(" ").includes(a)?c.observableArray.fn[a]=function(...b){var d=this.L();this.cb();this.pb(d,a,b);b=d[a](...b);this.valueHasMutated();return b===d?this:b}:c.observableArray.fn[a]=function(...b){return this()[a](...b)})});c.isObservableArray=a=>!(!a||!a[S]);c.extenders.trackArrayChanges=(a,b)=>{function d(){if(k){var q=[].concat(a.L()||[]);if(a.na("arrayChange")){if(!l||1<k)l=c.g.qb(m,q,a.Ka);
var r=l}m=q;l=null;k=0;r?.length&&a.B(r,"arrayChange")}}function e(){g?d():(g=!0,h=a.subscribe(()=>++k,null,"spectate"),m=[].concat(a.L()||[]),l=null,f=a.subscribe(d))}a.Ka={};"object"==typeof b&&c.g.extend(a.Ka,b);a.Ka.sparse=!0;if(!a.pb){var g=!1,l=null,f,h,k=0,m,p=a.Ja,n=a.Ia;a.Ja=q=>{p?.call(a,q);"arrayChange"===q&&e()};a.Ia=q=>{n?.call(a,q);"arrayChange"!==q||a.na("arrayChange")||(f?.dispose(),h?.dispose(),h=f=null,g=!1,m=void 0)};a.pb=(q,r,u)=>{if(g&&!k){var t=[],z=q.length,w=u.length,y=0,B=
(ia,ja,ka)=>t[t.length]={status:ia,value:ja,index:ka};switch(r){case "push":y=z;case "unshift":for(q=0;q<w;++q)B("added",u[q],y+q);break;case "pop":y=z-1;case "shift":z&&B("deleted",q[y],y);break;case "splice":y=Math.min(Math.max(0,0>u[0]?z+u[0]:u[0]),z);z=1===w?z:Math.min(y+(u[1]||0),z);w=y+w-2;r=Math.max(z,w);for(var v=[],F=[],C=2;y<r;++y,++C)y<z&&F.push(B("deleted",q[y],y)),y<w&&v.push(B("added",u[C],y));c.g.tb(F,v);break;default:return}l=t}}}};var x=Symbol("_state");c.o=(a,b)=>{function d(){if(0<
arguments.length){if("function"!==typeof e)throw Error("Cannot write a value to a ko.computed unless you specify a 'write' option. If you wish to read the current value, don't pass any parameters.");e(...arguments);return this}g.X||c.u.zb(d);(g.V||g.A&&d.oa())&&d.T();return g.J}"object"===typeof a?b=a:(b=b||{},a&&(b.read=a));if("function"!=typeof b.read)throw Error("Pass a function that returns the value of the ko.computed");var e=b.write,g={J:void 0,Y:!0,V:!0,Aa:!1,ab:!1,X:!1,Xa:!1,A:!1,yb:b.read,
s:b.s||null,ia:b.ia,Oa:null,v:{},G:0,bc:null};d[x]=g;d.Sb="function"===typeof e;c.P.fn.init(d);Object.setPrototypeOf(d,K);b.pure&&(g.Xa=!0,g.A=!0,c.g.extend(d,la));g.s&&(g.ab=!0,g.s.nodeType||(g.s=null));g.A||d.T();g.s&&d.isActive()&&c.g.N.addDisposeCallback(g.s,g.Oa=()=>{d.dispose()});return d};var K={ka:L,ma(){return this[x].G},Pb(){var a=[];c.g.K(this[x].v,(b,d)=>a[d.fa]=d.S);return a},Sa(a){if(!this[x].G)return!1;var b=this.Pb();return b.includes(a)||!!b.find(d=>d.Sa&&d.Sa(a))},kb(a,b,d){if(this[x].Xa&&
b===this)throw Error("A 'pure' computed must not be called recursively");this[x].v[a]=d;d.fa=this[x].G++;d.ga=b.ya()},oa(){var a,b=this[x].v;for(a in b)if(Object.prototype.hasOwnProperty.call(b,a)){var d=b[a];if(this.qa&&d.S.ea||d.S.Rb(d.ga))return!0}},dc(){this[x].Aa||this.qa?.(!1)},isActive(){var a=this[x];return a.V||0<a.G},ec(){this.ea?this[x].V&&(this[x].Y=!0):this.sb()},Cb(a){return a.subscribe(this.sb,this)},sb(){this.qa?this.qa(!0):this.T(!0)},T(a){var b=this[x],d=b.ia,e=!1;if(!b.Aa&&!b.X){if(b.s&&
!c.g.Pa(b.s)||d?.()){if(!b.ab){this.dispose();return}}else b.ab=!1;try{b.Aa=!0,e=this.Nb(a)}finally{b.Aa=!1}return e}},Nb(a){var b=this[x],d=b.Xa?void 0:!b.G;var e={Lb:this,va:b.v,Ma:b.G};c.u.nb({Kb:e,Jb:fa,o:this,Ca:d});b.v={};b.G=0;a:{try{var g=b.yb();break a}finally{c.u.end(),e.Ma&&!b.A&&c.g.K(e.va,ea),b.Y=b.V=!1}g=void 0}b.G?e=this.Ba(b.J,g):(this.dispose(),e=!0);e&&(b.A?this.Ea():this.B(b.J,"beforeChange"),b.J=g,this.B(b.J,"spectate"),!b.A&&a&&this.B(b.J),this.ib&&this.ib());d&&this.B(b.J,"awake");
return e},L(a){var b=this[x];(b.V&&(a||!b.G)||b.A&&this.oa())&&this.T();return b.J},Da(a){var b=this;c.P.fn.Da.call(b,a);b.fb=()=>{b[x].A||(b[x].Y?b.T():b[x].V=!1);return b[x].J};b.qa=d=>{b.gb(b[x].J);b[x].V=!0;d&&(b[x].Y=!0);b.hb(b,!d)}},dispose:function(){var a=this[x];!a.A&&a.v&&c.g.K(a.v,(b,d)=>d.dispose?.());a.s&&a.Oa&&c.g.N.Ya(a.s,a.Oa);a.v=void 0;a.G=0;a.X=!0;a.Y=!1;a.V=!1;a.A=!1;a.s=void 0;a.ia=void 0;a.yb=void 0}},la={Ja(a){var b=this,d=b[x];if(!d.X&&d.A&&"change"==a){d.A=!1;if(d.Y||b.oa())d.v=
null,d.G=0,b.T()&&b.Ea();else{var e=[];c.g.K(d.v,(g,l)=>e[l.fa]=g);e.forEach((g,l)=>{var f=d.v[g],h=b.Cb(f.S);h.fa=l;h.ga=f.ga;d.v[g]=h});b.oa()&&b.T()&&b.Ea()}d.X||b.B(d.J,"awake")}},Ia(a){var b=this[x];b.X||"change"!=a||this.na("change")||(c.g.K(b.v,(d,e)=>{e.dispose&&(b.v[d]={S:e.S,fa:e.fa,ga:e.ga},e.dispose())}),b.A=!0,this.B(void 0,"asleep"))},ya(){var a=this[x];a.A&&(a.Y||this.oa())&&this.T();return c.P.fn.ya.call(this)}};Object.setPrototypeOf(K,c.P.fn);var O=c.$.Zb;K[O]=c.o;c.o.fn=K;c.U("computed",
c.o);c.isComputed=a=>"function"==typeof a&&a[O]===K[O];c.xb=a=>{if("function"===typeof a)return c.o(a,{pure:!0});a={...a,pure:!0};return c.o(a)};c.C={M:a=>{switch(a.nodeName){case "OPTION":return!0===a.__ko__hasDomDataOptionValue__?c.g.l.get(a,c.i.options.Wa):a.value;case "SELECT":return 0<=a.selectedIndex?c.C.M(a.options[a.selectedIndex]):void 0;default:return a.value}},Fa:(a,b)=>{switch(a.nodeName){case "OPTION":"string"===typeof b?(c.g.l.set(a,c.i.options.Wa,void 0),delete a.__ko__hasDomDataOptionValue__,
a.value=b):(c.g.l.set(a,c.i.options.Wa,b),a.__ko__hasDomDataOptionValue__=!0,a.value="number"===typeof b?b:"");break;case "SELECT":for(var d=-1,e=""===(b??""),g=a.options.length,l;g--;)if(l=c.C.M(a.options[g]),l==b||""===l&&e){d=g;break}if(0<=d||e&&1<a.size)a.selectedIndex=d;break;default:a.value=b??""}}};c.la=(()=>{var a=RegExp("\"(?:\\\\.|[^\"])*\"|'(?:\\\\.|[^'])*'|`(?:\\\\.|[^`])*`|/\\*(?:[^*]|\\*+[^*/])*\\*+/|//.*\n|/(?:\\\\.|[^/])+/w*|[^\\s:,/][^,\"'`{}()/:[\\]]*[^\\s,\"'`{}()/:[\\]]|[^\\s]",
"g"),b=/[\])"'A-Za-z0-9_$]+$/,d={"in":1,"return":1,"typeof":1};return{Yb:e=>{e=c.g.Bb(e);123===e.charCodeAt(0)&&(e=e.slice(1,-1));e+="\n,";var g=[],l=e.match(a),f=[],h=0;if(1<l.length){for(var k=0,m;m=l[k++];){var p=m.charCodeAt(0);if(44===p){if(0>=h){n&&f.length&&g.push("'"+n+"':()=>("+f.join("")+")");var n=h=0;f=[];continue}}else if(58===p){if(!h&&!n&&1===f.length){n=f.pop();continue}}else if(47===p&&1<m.length&&(47===m.charCodeAt(1)||42===m.charCodeAt(1)))continue;else 47===p&&k&&1<m.length?(p=
l[k-1].match(b))&&!d[p[0]]&&(e=e.slice(e.indexOf(m)+1),l=e.match(a),k=-1,m="/"):40===p||123===p||91===p?++h:41===p||125===p||93===p?--h:n||f.length||34!==p&&39!==p||(m=m.slice(1,-1));f.push(m)}if(0<h)throw Error("Unbalanced parentheses, braces, or brackets");}g.push("'$data':()=>$data");return g.join(",")},cc:(e,g)=>-1<e.findIndex(l=>l.key==g),Ga:(e,g,l,f,h,k)=>{g&&c.W(g)?!c.vb(g)||k&&g.L()===h||g(h):(console.error(`"${f}" should be observable in ${e.outerHTML.replace(/>.+/,">")}`),l.get("$data")[f]=
h)}}})();(()=>{function a(f){return 8==f.nodeType&&e.test(f.nodeValue)}function b(f){return 8==f.nodeType&&g.test(f.nodeValue)}function d(f,h){for(var k=f,m=1,p=[];k=k.nextSibling;){if(b(k)&&(c.g.l.set(k,l,!0),!--m))return p;p.push(k);a(k)&&++m}if(!h)throw Error("Cannot find closing comment tag to match: "+f.nodeValue);return null}var e=/^\s*ko(?:\s+([\s\S]+))?\s*$/,g=/^\s*\/ko\s*$/,l="__ko_matchedEndComment__";c.m={aa:{},childNodes:f=>a(f)?d(f):f.childNodes,ja:f=>{a(f)?(f=d(f))&&[...f].forEach(h=>
c.removeNode(h)):c.g.Qa(f)},pa:(f,h)=>{a(f)?(c.m.ja(f),f.after(...h)):c.g.pa(f,h)},prepend:(f,h)=>{a(f)?f.nextSibling.before(h):f.prepend(h)},Ub:(f,h,k)=>{k?k.after(h):c.m.prepend(f,h)},firstChild:f=>{if(a(f))return f=f.nextSibling,!f||b(f)?null:f;let h=f.firstChild;if(h&&b(h))throw Error("Found invalid end comment, as the first child of "+f);return h},nextSibling:f=>{if(a(f)){var h=d(f,void 0);f=h?(h.length?h[h.length-1]:f).nextSibling:null}if((h=f.nextSibling)&&b(h)){if(b(h)&&!c.g.l.get(h,l))throw Error("Found end comment without a matching opening comment, as child of "+
f);return null}return h},Qb:a,ac:f=>(f=f.nodeValue.match(e))?f[1]:null}})();const T=new Map;c.ob=new class{Xb(a){switch(a.nodeType){case 1:return null!=a.getAttribute("data-bind");case 8:return c.m.Qb(a)}return!1}Ob(a,b){a:{switch(a.nodeType){case 1:var d=a.getAttribute("data-bind");break a;case 8:d=c.m.ac(a);break a}d=null}if(d)try{let g=T.get(d);if(!g){var e="with($data){return{"+c.la.Yb(d)+"}}";g=new Function("$context","$root","$parent","$data","$element",e);T.set(d,g)}return g(b,b.$root,b.$parent,
b.$data||{},a)}catch(g){throw g.message="Unable to parse bindings.\nBindings value: "+d+"\nMessage: "+g.message,g;}return null}};const G=Symbol("_subscribable"),H=Symbol("_ancestorBindingInfo"),U=Symbol("_dataDependency"),V={},I=c.g.l.Z();c.i={};c.ba=class{constructor(a,b,d,e){var g=this,l=a===V,f=l?void 0:a,h="function"==typeof f&&!c.W(f),k=e?.dataDependency;a=()=>{var p=h?f():f;p=c.g.h(p);b?(c.g.extend(g,b),H in b&&(g[H]=b[H])):g.$root=p;g[G]=m;l?p=g.$data:g.$data=p;d?.(g,b,p);if(b?.[G]&&!c.u.o().Sa(b[G]))b[G]();
k&&(g[U]=k);return g.$data};if(e?.exportDependencies)a();else{var m=c.xb(a);m.L();m.isActive()?m.ka=null:g[G]=void 0}}createChildContext(a,b){return new c.ba(a,this,(d,e)=>{d.$parent=e.$data;b.extend?.(d)},b)}extend(a,b){return new c.ba(V,this,d=>c.g.extend(d,"function"==typeof a?a(d):a),b)}};const W=a=>{a=c.g.l.get(a,I);var b=a?.D;b&&(a.D=null,b.wb())};class ma{constructor(a,b,d){this.H=a;this.da=b;this.ta=new Set;this.F=!1;b.D||c.g.N.addDisposeCallback(a,W);d?.D&&(d.D.ta.add(a),this.za=d)}wb(){this.za?.D?.Mb(this.H)}Mb(a){this.ta.delete(a);
this.ta.size||this.rb?.()}rb(){this.F=!0;this.da.D&&!this.ta.size&&(this.da.D=null,c.g.N.Ya(this.H,W),c.j.notify(this.H,c.j.ca),this.wb())}}c.j={F:"childrenComplete",ca:"descendantsComplete",subscribe:(a,b,d,e,g)=>{var l=c.g.l.Ra(a,I,{});l.wa||(l.wa=new c.P);g?.notifyImmediately&&l.Va[b]&&c.u.I(d,e,[a]);return l.wa.subscribe(d,e,b)},notify:(a,b)=>{var d=c.g.l.get(a,I);if(d&&(d.Va[b]=!0,d.wa?.B(a,b),b==c.j.F))if(d.D)d.D.rb();else if(void 0===d.D&&d.wa?.na(c.j.ca))throw Error("descendantsComplete event not supported for bindings on this node");
},$a:(a,b)=>{var d=c.g.l.Ra(a,I,{});d.D||(d.D=new ma(a,d,b[H]));return b[H]==d?b:b.extend(e=>{e[H]=d})}};const Y=(a,b)=>{for(var d,e=c.m.firstChild(b);d=e;)e=c.m.nextSibling(d),X(a,d);c.j.notify(b,c.j.F)},X=(a,b)=>{var d=a;if(1===b.nodeType||c.ob.Xb(b))d=Z(b,null,a);d&&!b.matches?.("SCRIPT,TEXTAREA,TEMPLATE")&&Y(d,b)},na=a=>{var b=[],d={},e=[],g=l=>{if(!d[l]){var f=c.i[l];f&&(f.after&&(e.push(l),f.after.forEach(h=>{if(a[h]){if(e.includes(h))throw Error("Cannot combine the following bindings, because they have a cyclic dependency: "+
e.join(", "));g(h)}}),e.length--),b.push({key:l,ub:f}));d[l]=!0}};c.g.K(a,g);return b},Z=(a,b,d)=>{var e=c.g.l.Ra(a,I,{}),g=e.Hb;if(!b){if(g)throw Error("You cannot apply bindings multiple times to the same element.");e.Hb=!0}g||(e.context=d);e.Va||(e.Va={});if(b&&"function"!==typeof b)var l=b;else{var f=c.o(()=>{if(l=b?b(d,a):c.ob.Ob(a,d))d[G]?.(),d[U]?.();return l},{s:a});l&&f.isActive()||(f=null)}var h=d,k;if(l){var m=f?n=>()=>f()[n]():n=>l[n],p={get:n=>l[n]&&m(n)(),has:n=>n in l};c.j.F in l&&
c.j.subscribe(a,c.j.F,()=>{var n=l[c.j.F]();if(n){var q=c.m.childNodes(a);q.length&&n(q,c.dataFor(q[0]))}});c.j.ca in l&&(h=c.j.$a(a,d),c.j.subscribe(a,c.j.ca,()=>{var n=l[c.j.ca]();n&&c.m.firstChild(a)&&n(a)}));na(l).forEach(n=>{var q=n.ub.init,r=n.ub.update,u=n.key;if(8===a.nodeType&&!c.m.aa[u])throw Error("The binding '"+u+"' cannot be used with comment nodes");try{"function"==typeof q&&c.u.I(()=>{var t=q(a,m(u),p,h.$data,h);if(t&&t.controlsDescendantBindings){if(void 0!==k)throw Error("Multiple bindings ("+
k+" and "+u+") are trying to control descendant bindings of the same element. You cannot use these bindings together on the same element.");k=u}}),"function"==typeof r&&c.o(()=>r(a,m(u),p,h.$data,h),{s:a})}catch(t){throw t.message='Unable to process binding "'+u+": "+l[u]+'"\nMessage: '+t.message,t;}})}return void 0===k&&h};c.$b=a=>c.g.l.get(a,I)?.context;const P=a=>a&&a instanceof c.ba?a:new c.ba(a);c.applyBindingAccessorsToNode=(a,b,d)=>Z(a,b,P(d));c.mb=(a,b)=>{1!==b.nodeType&&8!==b.nodeType||Y(P(a),
b)};c.Ib=(a,b)=>X(P(a),b);c.dataFor=a=>([1,8].includes(a?.nodeType)&&c.$b(a))?.$data;c.U("bindingHandlers",c.i);(()=>{var a=Object.create(null),b=new Map;c.components={get:(l,f)=>{if(b.has(l))f(b.get(l));else{var h=a[l];h?h.subscribe(f):(h=a[l]=new c.P,h.subscribe(f),g(l,k=>{b.set(l,k);delete a[l];h.B(k)}))}},register:(l,f)=>{if(!f)throw Error("Invalid configuration for "+l);if(d[l])throw Error("Component "+l+" is already registered");d[l]=f}};var d=Object.create(null),e=(l,f)=>{throw Error(`Component '${l}': ${f}`);
},g=(l,f)=>{var h={},k=d[l]||{},m=k.template;k=k.viewModel;if(m){m.element||e(l,"Unknown template value: "+m);m=m.element;var p=J.getElementById(m);p||e(l,"Cannot find element with ID "+m);p.matches("TEMPLATE")||e(l,"Template Source Element not a <template>");h.template=c.g.ua(p.content.childNodes)}k&&("function"!==typeof k.createViewModel&&e(l,"Unknown viewModel value: "+k),h.createViewModel=k.createViewModel);f(h.template&&h.createViewModel?h:null)}})();(()=>{var a=0;c.i.component={init:(b,d,e,
g,l)=>{var f,h,k,m=()=>{var p=f&&f.dispose;"function"===typeof p&&p.call(f);k&&k.dispose();h=f=k=null};c.m.ja(b);c.g.N.addDisposeCallback(b,m);c.o(()=>{var p=c.g.h(d());if("string"!==typeof p){var n=c.g.h(p.params);p=c.g.h(p.name)}if(!p)throw Error("No component name specified");var q=c.j.$a(b,l),r=h=++a;c.components.get(p,u=>{if(h===r){m();if(!u)throw Error("Unknown component '"+p+"'");var t=u.template;if(!t)throw Error("Component '"+p+"' has no template");c.m.pa(b,c.g.ua(t));f=u.createViewModel(n,
{element:b});c.mb(q.createChildContext(f,{}),b)}})},{s:b});return{controlsDescendantBindings:!0}}};c.m.aa.component=!0})();c.i.attr={update:(a,b)=>{b=c.g.h(b())||{};c.g.K(b,function(d,e){e=c.g.h(e);var g=d.indexOf(":");g="lookupNamespaceURI"in a&&0<g&&a.lookupNamespaceURI(d.slice(0,g));!1===e||null==e?g?a.removeAttributeNS(g,d):a.removeAttribute(d):(e=e.toString(),g?a.setAttributeNS(g,d,e):a.setAttribute(d,e))})}};(()=>{c.i.checked={after:["value","attr"],init:function(a,b,d){var e="checkbox"==a.type,
g="radio"==a.type;if(e||g){const n=c.xb(()=>{if(d.has("checkedValue"))return c.g.h(d.get("checkedValue"));if(m)return d.has("value")?c.g.h(d.get("value")):a.value});var l=()=>{if(!c.u.Ca()){var q=a.checked,r=n();if(q||!g&&!c.u.ma()){var u=c.u.I(b);if(h){var t=k?u.L():u,z=p;p=r;z!==r?q&&(t.push(r),t.remove(z)):q?t.push(r):t.remove(r);k&&c.vb(u)&&u(t)}else e&&(void 0===r?r=q:q||(r=void 0)),c.la.Ga(a,u,d,"checked",r,!0)}}},f=b(),h=e&&c.g.h(f)instanceof Array,k=!(h&&f.push&&f.splice),m=g||h,p=h?n():void 0;
c.o(l,null,{s:a});a.addEventListener("click",l);c.o(()=>{var q=c.g.h(b()),r=n();h?(a.checked=q.includes(r),p=r):a.checked=e&&void 0===r?!!q:n()===q},null,{s:a});f=void 0}}};c.i.checkedValue={update:function(a,b){a.value=c.g.h(b())}}})();var Q=(a,b,d)=>b&&b.split(/\s+/).forEach(e=>a.classList.toggle(e,d));c.i.css={update:(a,b)=>{b=c.g.h(b());"object"==typeof b?c.g.K(b,(d,e)=>{e=c.g.h(e);Q(a,d,!!e)}):(b=c.g.Bb(b),Q(a,a.__ko__cssValue,!1),a.__ko__cssValue=b,Q(a,b,!0))}};c.i.enable={update:(a,b)=>{(b=
c.g.h(b()))&&a.disabled?a.removeAttribute("disabled"):b||a.disabled||(a.disabled=!0)}};c.i.disable={update:(a,b)=>c.i.enable.update(a,()=>!c.g.h(b()))};c.i.event={init:function(a,b,d,e,g){c.g.K(b()||{},l=>{"string"==typeof l&&a.addEventListener(l,(...f)=>{var h=b()[l];if(h)try{e=g.$data;var k=h.apply(e,[e,...f])}finally{!0!==k&&f[0].preventDefault()}})})}};const aa=a=>()=>{var b=a(),d=c.W(b)?b.L():b;if(!d||Array.isArray(d))return{foreach:b};c.g.h(b);return{foreach:d.data}};c.i.foreach={init:(a,b)=>
c.i.template.init(a,aa(b)),update:(a,b,d,e,g)=>c.i.template.update(a,aa(b),d,e,g)};c.m.aa.foreach=!0;c.i.hasfocus={init:(a,b,d)=>{var e=l=>{a.__ko_hasfocusUpdating=!0;l=a.ownerDocument.activeElement===a;c.la.Ga(a,b(),d,"hasfocus",l,!0);a.__ko_hasfocusLastValue=l;a.__ko_hasfocusUpdating=!1},g=e.bind(null,!0);e=e.bind(null,!1);a.addEventListener("focus",g);a.addEventListener("focusin",g);a.addEventListener("blur",e);a.addEventListener("focusout",e);a.__ko_hasfocusLastValue=!1},update:(a,b)=>{b=!!c.g.h(b());
a.__ko_hasfocusUpdating||a.__ko_hasfocusLastValue===b||(b?a.focus():a.blur())}};c.i.html={init:()=>({controlsDescendantBindings:!0}),update:(a,b)=>{c.g.Qa(a);b=c.g.h(b());if(null!=b){const d=J.createElement("template");d.innerHTML="string"!=typeof b?b.toString():b;a.appendChild(d.content)}}};(()=>{function a(b,d,e){c.i[b]={init:(g,l,f,h,k)=>{var m,p={};d&&(p={exportDependencies:!0});var n=f.has(c.j.ca);c.o(()=>{var q=c.g.h(l()),r=!e!==!q,u=!m;n&&(k=c.j.$a(g,k));if(r){p.dataDependency=c.u.o();var t=
d?k.createChildContext("function"==typeof q?q:l,p):c.u.ma()?k.extend(null,p):k}u&&c.u.ma()&&(m=c.g.ua(c.m.childNodes(g),!0));r?(u||c.m.pa(g,c.g.ua(m)),c.mb(t,g)):(c.m.ja(g),c.j.notify(g,c.j.F))},{s:g});return{controlsDescendantBindings:!0}}};c.m.aa[b]=!0}a("if");a("ifnot",!1,!0);a("with",!0)})();var ba={};c.i.options={init:a=>{if(!a.matches("SELECT"))throw Error("options binding applies only to SELECT elements");let b=a.length;for(;b--;)a.remove(b);return{controlsDescendantBindings:!0}},update:(a,
b,d)=>{var e=a.multiple,g=0!=a.length&&e?a.scrollTop:null,l=c.g.h(b()),f=[];b=()=>Array.from(a.options).filter(n=>n.selected);var h=(n,q,r)=>{var u=typeof q;return"function"==u?q(n):"string"==u?n[q]:r},k=(n,q)=>{f.length&&(n=f.includes(c.C.M(q[0])),q[0].selected=n,p&&!n&&c.u.I(c.g.Db,null,[a,"change"]))};e?f=b().map(c.C.M):0<=a.selectedIndex&&f.push(c.C.M(a.options[a.selectedIndex]));if(l){Array.isArray(l)||(l=[l]);var m=l.filter(n=>n??1)}var p=!1;l=k;d.has("optionsAfterRender")&&"function"==typeof d.get("optionsAfterRender")&&
(l=(n,q)=>{k(n,q);c.u.I(d.get("optionsAfterRender"),null,[q[0],n!==ba?n:void 0])});c.g.Ab(a,m,(n,q,r)=>{r.length&&(f=r[0].selected?[c.C.M(r[0])]:[],p=!0);q=a.ownerDocument.createElement("option");n===ba?(c.g.Za(q),c.C.Fa(q,void 0)):(r=h(n,d.get("optionsValue"),n),c.C.Fa(q,c.g.h(r)),n=h(n,d.get("optionsText"),r),c.g.Za(q,n));return[q]},{},l);m=f.length;(e?m&&b().length<m:m&&0<=a.selectedIndex?c.C.M(a.options[a.selectedIndex])!==f[0]:m||0<=a.selectedIndex)&&c.u.I(c.g.Db,null,[a,"change"]);c.u.Ca()&&
c.j.notify(a,c.j.F);g&&20<Math.abs(g-a.scrollTop)&&(a.scrollTop=g)}};c.i.options.Wa=c.g.l.Z();c.i.style={update:(a,b)=>{c.g.K(c.g.h(b()||{}),(d,e)=>{e=c.g.h(e);if(null==e||!1===e)e="";if(/^--/.test(d))a.style.setProperty(d,e);else{d=d.replace(/-(\w)/g,(l,f)=>f.toUpperCase());var g=a.style[d];a.style[d]=e;e===g||a.style[d]!=g||isNaN(e)||(a.style[d]=e+"px")}})}};c.i.submit={init:(a,b,d,e,g)=>{if("function"!=typeof b())throw Error("The value for a submit binding must be a function");a.addEventListener("submit",
l=>{var f=b();try{var h=f.call(g.$data,a)}finally{!0!==h&&l.preventDefault()}})}};c.i.text={init:()=>({controlsDescendantBindings:!0}),update:(a,b)=>{8===a.nodeType&&(a.text||a.after(a.text=J.createTextNode("")),a=a.text);c.g.Za(a,b())}};c.m.aa.text=!0;c.i.textInput={init:(a,b,d)=>{var e=a.value,g,l,f=()=>{clearTimeout(g);l=g=void 0;var k=a.value;a.checkValidity()&&e!==k&&(e=k,c.la.Ga(a,b(),d,"textInput",k))},h=()=>{var k=c.g.h(b())??"";void 0!==l&&k===l?setTimeout(h,4):a.value!==k&&(a.value=k,e=
a.value)};a.addEventListener("input",f);a.addEventListener("change",f);c.o(h,{s:a})}};c.i.value={init:(a,b,d)=>{var e=a.matches("SELECT"),g=a.matches("INPUT");if(!g||"checkbox"!=a.type&&"radio"!=a.type){var l=new Set,f=d.get("valueUpdate"),h=null,k=()=>{h=null;var n=b(),q=c.C.M(a);c.la.Ga(a,n,d,"value",q)};f&&("string"==typeof f?l.add(f):f.forEach(n=>l.add(n)),l.delete("change"));l.forEach(n=>{var q=k;(n||"").startsWith("after")&&(q=()=>{h=c.C.M(a);setTimeout(k,0)},n=n.slice(5));a.addEventListener(n,
q)});var m=g&&"file"==a.type?()=>{var n=c.g.h(b());null==n||""===n?a.value="":c.u.I(k)}:()=>{var n=c.g.h(b()),q=c.C.M(a);if(null!==h&&n===h)setTimeout(m,0);else if(n!==q||void 0===q)e?(c.C.Fa(a,n),n!==c.C.M(a)&&c.u.I(k)):c.C.Fa(a,n)};if(e){var p;c.j.subscribe(a,c.j.F,()=>{p?d.get("valueAllowUnset")?m():k():(a.addEventListener("change",k),p=c.o(m,{s:a}))},null,{notifyImmediately:!0})}else a.addEventListener("change",k),c.o(m,{s:a})}else c.applyBindingAccessorsToNode(a,{checkedValue:b})},update:()=>
{}};c.i.visible={update:(a,b)=>{b=c.g.h(b());var d="none"!=a.style.display;b&&!d?a.style.display="":d&&!b&&(a.style.display="none")}};c.i.hidden={update:(a,b)=>a.hidden=!!c.g.h(b())};(function(a){c.i[a]={init:function(b,d,e,g,l){return c.i.event.init.call(this,b,()=>({[a]:d()}),e,g,l)}}})("click");(()=>{let a=c.g.l.Z();class b{constructor(e){this.Na=e}Ua(...e){let g=this.Na;if(!e.length)return c.g.l.get(g,a)||(11===this.H?g.content:1===this.H?g:void 0);c.g.l.set(g,a,e[0])}}class d extends b{constructor(e){super(e);
e&&(this.H=e.matches("TEMPLATE")&&e.content?e.content.nodeType:1)}}c.bb={Na:d,lb:b}})();(()=>{const a=(h,k,m)=>{var p;for(k=c.m.nextSibling(k);h&&(p=h)!==k;)h=c.m.nextSibling(p),m(p,h)},b=(h,k)=>{if(h.length){var m=h[0],p=m.parentNode;a(m,h[h.length-1],n=>(1===n.nodeType||8===n.nodeType)&&c.Ib(k,n));c.g.xa(h,p)}},d=(h,k,m,p)=>{var n=(h&&(h.nodeType?h:0<h.length?h[0]:null)||m||{}).ownerDocument;if("string"==typeof m){n=n||J;n=n.getElementById(m);if(!n)throw Error("Cannot find template with ID "+m);
m=new c.bb.Na(n)}else if([1,8].includes(m.nodeType))m=new c.bb.lb(m);else throw Error("Unknown template type: "+m);m=(m=m.Ua?m.Ua():null)?[...m.cloneNode(!0).childNodes]:null;if(!Array.isArray(m)||0<m.length&&"number"!=typeof m[0].nodeType)throw Error("Template engine must return an array of DOM nodes");k&&(c.m.pa(h,m),b(m,p),c.j.notify(h,c.j.F));return m},e=(h,k,m)=>c.W(h)?h():"function"===typeof h?h(k,m):h,g=(h,k,m,p)=>{m=m||{};if(p){var n=p.nodeType?p:0<p.length?p[0]:null;return c.o(()=>{var q=
k instanceof c.ba?k:new c.ba(k,null,null,{exportDependencies:!0}),r=e(h,q.$data,q);d(p,!0,r,q,m)},{ia:()=>!n||!c.g.Pa(n),s:n})}console.log("no targetNodeOrNodeArray")},l=(h,k,m,p,n)=>{var q,r=(w,y)=>{q=n.createChildContext(w,{extend:B=>B.$index=y});w=e(h,w,q);return d(p,!1,w,q,m)},u=(w,y)=>{b(y,q);q=null},t=(w,y)=>{c.u.I(c.g.Ab,null,[p,w,r,m,u,y]);c.j.notify(p,c.j.F)};if(c.isObservableArray(k)){t(k.L());var z=k.subscribe(w=>{t(k(),w)},null,"arrayChange");z.s(p);return z}return c.o(()=>{var w=c.g.h(k)||
[];Array.isArray(w)||(w=[w]);t(w)},{s:p})},f=c.g.l.Z();c.i.template={init:(h,k)=>{k=c.g.h(k());if("string"==typeof k||"name"in k)c.m.ja(h);else if(k=c.m.childNodes(h),k.length)k=c.g.Wb(k),(new c.bb.lb(h)).Ua(k);else throw Error("Anonymous template defined, but no template content was provided");return{controlsDescendantBindings:!0}},update:(h,k,m,p,n)=>{p=k();k=c.g.h(p);m=null;"string"==typeof k?k={}:p="name"in k?k.name:h;var q=!!p;"foreach"in k?m=l(p,q&&k.foreach||[],k,h,n):q?(m=n,"data"in k&&(m=
n.createChildContext(k.data,{exportDependencies:!0})),m=g(p,m,k,h)):c.m.ja(h);n=m;c.g.l.get(h,f)?.dispose?.();c.g.l.set(h,f,!n||n.isActive&&!n.isActive()?void 0:n)}};c.m.aa.template=!0})();c.g.tb=(a,b,d)=>{var e=0,g,l=b.length;l&&a.every(f=>{g=b.findIndex(h=>f.value===h.value);0<=g&&(f.moved=b[g].index,b[g].moved=f.index,b.splice(g,1),e=g=0,--l);e+=l;return l&&(!d||e<d)})};c.g.qb=(()=>{var a=(b,d,e,g,l)=>{for(var f=Math.min,h=Math.max,k=[],m=-1,p=b.length,n,q=d.length,r=q-p||1,u=p+q+1,t,z,w;++m<=
p;)for(z=t,k.push(t=[]),w=f(q,m+r),n=h(0,m-1);n<=w;n++)t[n]=n?m?b[m-1]===d[n-1]?z[n-1]:f(z[n]||u,t[n-1]||u)+1:n+1:m+1;f=[];h=[];r=[];m=p;for(n=q;m||n;)q=k[m][n]-1,n&&q===k[m][n-1]?h.push(f[f.length]={status:e,value:d[--n],index:n}):m&&q===k[m-1][n]?r.push(f[f.length]={status:g,value:b[--m],index:m}):(--n,--m,l.sparse||f.push({status:"retained",value:d[n]}));c.g.tb(r,h,10*p);return f.reverse()};return(b,d,e)=>{b=b||[];d=d||[];return b.length<d.length?a(b,d,"added","deleted",e):a(d,b,"deleted","added",
e)}})();(()=>{function a(e,g,l,f,h){var k=[],m=c.o(()=>{var p=g(l,h,c.g.xa(k,e))||[];if(0<k.length){var n=k.nodeType?[k]:k;if(0<n.length){var q=n[0],r=q.parentNode;p.forEach(u=>r.insertBefore(u,q));n.forEach(u=>c.removeNode(u))}f&&c.u.I(f,null,[l,p,h])}k.length=0;k.push(...p)},{s:e,ia:()=>!!k.find(c.g.Pa)});return{O:k,La:m.isActive()?m:void 0}}var b=c.g.l.Z(),d=c.g.l.Z();c.g.Ab=(e,g,l,f,h,k)=>{g=g||[];Array.isArray(g)||(g=[g]);var m=c.g.l.get(e,b),p=[],n=0,q=0,r=[],u=[],t,z=v=>{t={sa:v,Ta:c.$(q++)};
p.push(t)},w=v=>{t=m[v];t.Ta(q++);c.g.xa(t.O,e);p.push(t)};if(m){if(!k||m&&m._countWaitingForRemove)k=c.g.qb(Array.prototype.map.call(m,C=>C.sa),g,{sparse:!0});let v,F;for(k.forEach(C=>{v=C.moved;F=C.index;switch(C.status){case "deleted":for(;n<F;)w(n++);void 0===v&&(t=m[n],t.La&&(t.La.dispose(),t.La=void 0),c.g.xa(t.O,e).length&&t&&r.push.apply(r,t.O));n++;break;case "added":for(;q<F;)w(n++);void 0!==v?(u.push(p.length),w(v)):z(C.value)}});q<g.length;)w(n++);p._countWaitingForRemove=0}else g.forEach(z);
c.g.l.set(e,b,p);r.forEach(c.removeNode);var y=v=>{c.m.Ub(e,v,B);B=v};k=e.ownerDocument.activeElement;if(u.length)for(;null!=(g=u.shift());){for(t=p[g];g--;)if(f=p[g].O,f?.length){var B=f[f.length-1];break}t.O.forEach(y)}p.forEach(v=>{v.O||c.g.extend(v,a(e,l,v.sa,h,v.Ta));v.O.forEach(y);!v.Tb&&h&&(h(v.sa,v.O,v.Ta),v.Tb=!0,B=v.O[v.O.length-1])});e.ownerDocument.activeElement!=k&&k?.focus();[].forEach(v=>v&&(v.sa=d))}})();R.ko=M})(this);

"use strict";
(() => {
  // source/node/TreeIterator.ts
  var SHOW_ELEMENT = 1;
  var SHOW_TEXT = 4;
  var SHOW_ELEMENT_OR_TEXT = 5;

  // source/node/TreeWalker.ts
  var FILTER_ACCEPT = NodeFilter.FILTER_ACCEPT;
  TreeWalker.prototype.previousPONode = function() {
    const root = this.root;
    let current = this.currentNode;
    let node;
    while (true) {
      node = current.lastChild;
      while (!node && current) {
        if (current === root) {
          break;
        }
        node = current.previousSibling;
        if (!node) {
          current = current.parentNode;
        }
      }
      if (!node) {
        return null;
      }
      const nodeType = node.nodeType;
      const nodeFilterType = nodeType === Node.ELEMENT_NODE ? NodeFilter.SHOW_ELEMENT : nodeType === Node.TEXT_NODE ? NodeFilter.SHOW_TEXT : 0;
      if (!!(nodeFilterType & this.whatToShow) && FILTER_ACCEPT === this.filter.acceptNode(node)) {
        this.currentNode = node;
        return node;
      }
      current = node;
    }
  };
  var createTreeWalker = (root, whatToShow, filter) => document.createTreeWalker(
    root,
    whatToShow,
    {
      acceptNode: (node) => !filter || filter(node) ? FILTER_ACCEPT : NodeFilter.FILTER_SKIP
    }
  );

  // source/Constants.ts
  var ELEMENT_NODE = 1;
  var TEXT_NODE = 3;
  var DOCUMENT_FRAGMENT_NODE = 11;
  var ZWS = "\u200B";
  var ua = navigator.userAgent;
  var isMac = /Mac OS X/.test(ua);
  var isWin = /Windows NT/.test(ua);
  var isIOS = /iP(?:ad|hone)/.test(ua) || isMac && !!navigator.maxTouchPoints;
  var isAndroid = /Android/.test(ua);
  var isWebKit = /WebKit\//.test(ua);
  var ctrlKey = isMac || isIOS ? "Meta-" : "Ctrl-";
  var cantFocusEmptyTextNodes = isWebKit;
  var notWS = /[^ \t\r\n]/;

  // source/node/Category.ts
  var inlineNodeNames = /^(?:#text|A(?:BBR|CRONYM)?|B(?:R|D[IO])?|C(?:ITE|ODE)|D(?:ATA|EL|FN)|EM|FONT|HR|I(?:MG|NS)?|KBD|Q|R(?:P|T|UBY)|S(?:AMP|MALL|PAN|TR(?:IKE|ONG)|U[BP])?|TIME|U|VAR|WBR)$/;
  var leafNodeNames = /* @__PURE__ */ new Set(["BR", "HR", "IMG"]);
  var UNKNOWN = 0;
  var INLINE = 1;
  var BLOCK = 2;
  var CONTAINER = 3;
  var cache = /* @__PURE__ */ new WeakMap();
  var resetNodeCategoryCache = () => {
    cache = /* @__PURE__ */ new WeakMap();
  };
  var isLeaf = (node) => leafNodeNames.has(node.nodeName);
  var getNodeCategory = (node) => {
    switch (node.nodeType) {
      case TEXT_NODE:
        return INLINE;
      case ELEMENT_NODE:
      case DOCUMENT_FRAGMENT_NODE:
        if (cache.has(node)) {
          return cache.get(node);
        }
        break;
      default:
        return UNKNOWN;
    }
    let nodeCategory;
    if (!Array.from(node.childNodes).every(isInline)) {
      nodeCategory = CONTAINER;
    } else if (inlineNodeNames.test(node.nodeName)) {
      nodeCategory = INLINE;
    } else {
      nodeCategory = BLOCK;
    }
    cache.set(node, nodeCategory);
    return nodeCategory;
  };
  var isInline = (node) => getNodeCategory(node) === INLINE;
  var isBlock = (node) => getNodeCategory(node) === BLOCK;
  var isContainer = (node) => getNodeCategory(node) === CONTAINER;

  // source/node/Node.ts
  var createElement = (tag, props, children) => {
    const el = document.createElement(tag);
    if (props instanceof Array) {
      children = props;
      props = null;
    }
    setAttributes(el, props);
    children && el.append(...children);
    return el;
  };
  var areAlike = (node, node2) => {
    if (isLeaf(node)) {
      return false;
    }
    if (node.nodeType !== node2.nodeType || node.nodeName !== node2.nodeName) {
      return false;
    }
    if (node instanceof HTMLElement && node2 instanceof HTMLElement) {
      return node.nodeName !== "A" && node.className === node2.className && node.style.cssText === node2.style.cssText;
    }
    return true;
  };
  var hasTagAttributes = (node, tag, attributes) => {
    if (node.nodeName !== tag) {
      return false;
    }
    for (const attr in attributes) {
      if (!("getAttribute" in node) || node.getAttribute(attr) !== attributes[attr]) {
        return false;
      }
    }
    return true;
  };
  var getNearest = (node, root, tag, attributes) => {
    while (node && node !== root) {
      if (hasTagAttributes(node, tag, attributes)) {
        return node;
      }
      node = node.parentNode;
    }
    return null;
  };
  var getNodeBeforeOffset = (node, offset) => {
    let children = node.childNodes;
    while (offset && node instanceof Element) {
      node = children[offset - 1];
      children = node.childNodes;
      offset = children.length;
    }
    return node;
  };
  var getNodeAfterOffset = (node, offset) => {
    let returnNode = node;
    if (returnNode instanceof Element) {
      const children = returnNode.childNodes;
      if (offset < children.length) {
        returnNode = children[offset];
      } else {
        while (returnNode && !returnNode.nextSibling) {
          returnNode = returnNode.parentNode;
        }
        if (returnNode) {
          returnNode = returnNode.nextSibling;
        }
      }
    }
    return returnNode;
  };
  var getLength = (node) => node instanceof Element || node instanceof DocumentFragment ? node.childNodes.length : node instanceof CharacterData ? node.length : 0;
  var empty = (node) => {
    const frag = document.createDocumentFragment();
    frag.append(...node.childNodes);
    return frag;
  };
  var detach = (node) => {
    node.parentNode?.removeChild(node);
    return node;
  };
  var replaceWith = (node, node2) => node.parentNode?.replaceChild(node2, node);
  var getClosest = (node, root, selector) => {
    node = (node && !node.closest ? node.parentElement : node)?.closest(selector);
    return node && root.contains(node) ? node : null;
  };
  var setAttributes = (node, props) => {
    props && Object.entries(props).forEach(([k, v]) => {
      if (null == v) {
        node.removeAttribute(k);
      } else if ("style" === k && typeof v === "object") {
        Object.entries(v).forEach(([k2, v2]) => node.style[k2] = v2);
      } else {
        node.setAttribute(k, v);
      }
    });
  };

  // source/node/Whitespace.ts
  var notWSTextNode = (node) => node instanceof Element ? node.nodeName === "BR" : (
    // okay if data is 'undefined' here.
    notWS.test(node.data)
  );
  var isLineBreak = (br) => {
    let block = br.parentNode;
    while (isInline(block)) {
      block = block.parentNode;
    }
    const walker = createTreeWalker(
      block,
      SHOW_ELEMENT_OR_TEXT,
      notWSTextNode
    );
    walker.currentNode = br;
    return !!walker.nextNode();
  };
  var removeZWS = (root, keepNode) => {
    const walker = createTreeWalker(root, SHOW_TEXT);
    let textNode;
    let index;
    while (textNode = walker.nextNode()) {
      while ((index = textNode.data.indexOf(ZWS)) > -1 && // eslint-disable-next-line no-unmodified-loop-condition
      (!keepNode || textNode.parentNode !== keepNode)) {
        if (textNode.length === 1) {
          let node = textNode;
          let parent = node.parentNode;
          while (parent) {
            parent.removeChild(node);
            walker.currentNode = parent;
            if (!isInline(parent) || getLength(parent)) {
              break;
            }
            node = parent;
            parent = node.parentNode;
          }
          break;
        } else {
          textNode.deleteData(index, 1);
        }
      }
    }
  };

  // source/range/Boundaries.ts
  var START_TO_START = 0;
  var END_TO_END = 2;
  var isNodeContainedInRange = (range, node, partial) => {
    if (partial) {
      return range.intersectsNode(node);
    } else {
      const nodeRange = document.createRange();
      nodeRange.selectNode(node);
      const nodeStartAfterStart = range.compareBoundaryPoints(START_TO_START, nodeRange) < 1;
      const nodeEndBeforeEnd = range.compareBoundaryPoints(END_TO_END, nodeRange) > -1;
      return nodeStartAfterStart && nodeEndBeforeEnd;
    }
  };
  var moveRangeBoundariesDownTree = (range) => {
    let { startContainer, startOffset, endContainer, endOffset } = range;
    while (!(startContainer instanceof Text)) {
      let child = startContainer.childNodes[startOffset];
      if (!child || isLeaf(child)) {
        if (startOffset) {
          child = startContainer.childNodes[startOffset - 1];
          if (child instanceof Text) {
            let textChild = child;
            let prev;
            while (!textChild.length && (prev = textChild.previousSibling) && prev instanceof Text) {
              textChild.remove();
              textChild = prev;
            }
            startContainer = textChild;
            startOffset = textChild.length;
          }
        }
        break;
      }
      startContainer = child;
      startOffset = 0;
    }
    if (endOffset) {
      while (!(endContainer instanceof Text)) {
        const child = endContainer.childNodes[endOffset - 1];
        if (!child || isLeaf(child)) {
          if (child && child.nodeName === "BR" && !isLineBreak(child)) {
            --endOffset;
            continue;
          }
          break;
        }
        endContainer = child;
        endOffset = getLength(endContainer);
      }
    } else {
      while (!(endContainer instanceof Text)) {
        const child = endContainer.firstChild;
        if (!child || isLeaf(child)) {
          break;
        }
        endContainer = child;
      }
    }
    range.setStart(startContainer, startOffset);
    range.setEnd(endContainer, endOffset);
  };
  var moveRangeBoundariesUpTree = (range, startMax, endMax, root) => {
    let startContainer = range.startContainer;
    let startOffset = range.startOffset;
    let endContainer = range.endContainer;
    let endOffset = range.endOffset;
    let parent;
    if (!startMax) {
      startMax = range.commonAncestorContainer;
    }
    if (!endMax) {
      endMax = startMax;
    }
    while (!startOffset && startContainer !== startMax && startContainer !== root) {
      parent = startContainer.parentNode;
      startOffset = Array.from(parent.childNodes).indexOf(
        startContainer
      );
      startContainer = parent;
    }
    while (true) {
      if (endContainer === endMax || endContainer === root) {
        break;
      }
      if (endContainer.nodeType !== TEXT_NODE && endContainer.childNodes[endOffset] && endContainer.childNodes[endOffset].nodeName === "BR" && !isLineBreak(endContainer.childNodes[endOffset])) {
        ++endOffset;
      }
      if (endOffset !== getLength(endContainer)) {
        break;
      }
      parent = endContainer.parentNode;
      endOffset = Array.from(parent.childNodes).indexOf(endContainer) + 1;
      endContainer = parent;
    }
    range.setStart(startContainer, startOffset);
    range.setEnd(endContainer, endOffset);
  };
  var moveRangeBoundaryOutOf = (range, tag, root) => {
    let parent = getClosest(range.endContainer, root, tag);
    if (parent && (parent = parent.parentNode)) {
      const clone = range.cloneRange();
      moveRangeBoundariesUpTree(clone, parent, parent, root);
      if (clone.endContainer === parent) {
        range.setStart(clone.endContainer, clone.endOffset);
        range.setEnd(clone.endContainer, clone.endOffset);
      }
    }
    return range;
  };

  // source/Clean.ts
  var styleToSemantic = {
    "font-weight": {
      regexp: /^bold|^700/i,
      replace() {
        return createElement("B");
      }
    },
    "font-style": {
      regexp: /^italic/i,
      replace() {
        return createElement("I");
      }
    },
    "font-family": {
      regexp: notWS,
      replace(classNames, family) {
        return createElement("SPAN", {
          class: classNames.fontFamily,
          style: "font-family:" + family
        });
      }
    },
    "font-size": {
      regexp: notWS,
      replace(classNames, size) {
        return createElement("SPAN", {
          class: classNames.fontSize,
          style: "font-size:" + size
        });
      }
    },
    "text-decoration": {
      regexp: /^underline/i,
      replace() {
        return createElement("U");
      }
    }
  };
  var replaceStyles = (node, _, config) => {
    const style = node.style;
    let newTreeBottom;
    let newTreeTop;
    for (const attr in styleToSemantic) {
      const converter = styleToSemantic[attr];
      const css = style.getPropertyValue(attr);
      if (css && converter.regexp.test(css)) {
        const el = converter.replace(config.classNames, css);
        if (el.nodeName === node.nodeName && el.className === node.className) {
          continue;
        }
        if (!newTreeTop) {
          newTreeTop = el;
        }
        if (newTreeBottom) {
          newTreeBottom.append(el);
        }
        newTreeBottom = el;
        node.style.removeProperty(attr);
      }
    }
    if (newTreeTop && newTreeBottom) {
      newTreeBottom.append(empty(node));
      if (node.style.cssText) {
        node.append(newTreeTop);
      } else {
        replaceWith(node, newTreeTop);
      }
    }
    return newTreeBottom || node;
  };
  var replaceWithTag = (tag) => {
    return (node, parent) => {
      const el = createElement(tag);
      const attributes = node.attributes;
      for (let i = 0, l = attributes.length; i < l; ++i) {
        const attribute = attributes[i];
        el.setAttribute(attribute.name, attribute.value);
      }
      parent.replaceChild(el, node);
      el.append(empty(node));
      return el;
    };
  };
  var fontSizes = {
    "1": "x-small",
    "2": "small",
    "3": "medium",
    "4": "large",
    "5": "x-large",
    "6": "xx-large",
    "7": "xxx-large",
    "-1": "smaller",
    "+1": "larger"
  };
  var stylesRewriters = {
    STRONG: replaceWithTag("B"),
    EM: replaceWithTag("I"),
    INS: replaceWithTag("U"),
    STRIKE: replaceWithTag("S"),
    SPAN: replaceStyles,
    FONT: (node, parent, config) => {
      const font = node;
      const face = font.face;
      const size = font.size;
      let color = font.color;
      let newTag = createElement("SPAN");
      let css = newTag.style;
      newTag.style.cssText = node.style.cssText;
      if (face) {
        css.fontFamily = face;
      }
      if (size) {
        css.fontSize = fontSizes[size];
      }
      if (color && /^#?([\dA-F]{3}){1,2}$/i.test(color)) {
        if (color.charAt(0) !== "#") {
          color = "#" + color;
        }
        css.color = color;
      }
      replaceWith(node, newTag);
      newTag.append(empty(node));
      return newTag;
    },
    TT: (node, parent, config) => {
      const el = createElement("SPAN", {
        class: config.classNames.fontFamily,
        style: 'font-family:menlo,consolas,"courier new",monospace'
      });
      replaceWith(node, el);
      el.append(empty(node));
      return el;
    }
  };
  var allowedBlock = /^(?:A(?:DDRESS|RTICLE|SIDE|UDIO)|BLOCKQUOTE|CAPTION|D(?:[DLT]|IV)|F(?:IGURE|IGCAPTION|OOTER)|H[1-6]|HEADER|L(?:ABEL|EGEND|I)|O(?:L|UTPUT)|P(?:RE)?|SECTION|T(?:ABLE|BODY|D|FOOT|H|HEAD|R)|COL(?:GROUP)?|UL)$/;
  var blacklist = /* @__PURE__ */ new Set(["HEAD", "META", "STYLE"]);
  var cleanTree = (node, config, preserveWS) => {
    const children = node.childNodes;
    let nonInlineParent = node;
    while (isInline(nonInlineParent)) {
      nonInlineParent = nonInlineParent.parentNode;
    }
    const walker = createTreeWalker(
      nonInlineParent,
      SHOW_ELEMENT_OR_TEXT
    );
    let i = children.length;
    while (i--) {
      let child = children[i];
      const nodeName = child.nodeName;
      if (child instanceof HTMLElement) {
        const childLength = child.childNodes.length;
        if (stylesRewriters[nodeName]) {
          child = stylesRewriters[nodeName](child, node, config);
        } else if (blacklist.has(nodeName)) {
          child.remove();
          continue;
        } else if (!allowedBlock.test(nodeName) && !isInline(child)) {
          i += childLength;
          replaceWith(child, empty(child));
          continue;
        }
        if (childLength) {
          cleanTree(child, config, preserveWS || nodeName === "PRE");
        }
      }
    }
    return node;
  };
  var removeEmptyInlines = (node) => {
    const children = node.childNodes;
    let l = children.length;
    while (l--) {
      const child = children[l];
      if (child instanceof Element && !isLeaf(child)) {
        removeEmptyInlines(child);
        if (isInline(child) && !child.firstChild) {
          node.removeChild(child);
        }
      } else if (child instanceof Text && !child.length) {
        node.removeChild(child);
      }
    }
  };
  var cleanupBRs = (node) => {
    const brs = node.querySelectorAll("BR:last-child");
    let l = brs.length;
    while (l--) {
      const br = brs[l];
      if (!isLineBreak(br)) {
        br.remove();
      }
    }
  };
  var escapeHTML = (text) => {
    return text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
  };

  // source/node/MergeSplit.ts
  var fixCursor = (node) => {
    if ((node instanceof Element || node instanceof DocumentFragment) && !isInline(node) && !node.children.length && !node.textContent.length) {
      node.appendChild(createElement("BR"));
    }
    return node;
  };
  var fixContainer = (container) => {
    let wrapper = null;
    [...container.childNodes].forEach((child) => {
      if (isInline(child)) {
        wrapper || (wrapper = createElement("DIV"));
        wrapper.append(child);
      } else if (wrapper) {
        (wrapper.children.length || wrapper.textContent.trim().length) && container.insertBefore(wrapper, child);
        wrapper = null;
      }
    });
    wrapper && container.append(wrapper);
    return container;
  };
  var split = (node, offset, stopNode, root) => {
    if (node instanceof Text && node !== stopNode) {
      if (typeof offset !== "number") {
        throw new Error("Offset must be a number to split text node!");
      }
      if (!node.parentNode) {
        throw new Error("Cannot split text node with no parent!");
      }
      return split(node.parentNode, node.splitText(offset), stopNode, root);
    }
    let nodeAfterSplit = typeof offset === "number" ? offset < node.childNodes.length ? node.childNodes[offset] : null : offset;
    const parent = node.parentNode;
    if (!parent || node === stopNode || !(node instanceof Element)) {
      return nodeAfterSplit;
    }
    const clone = node.cloneNode(false);
    while (nodeAfterSplit) {
      const next = nodeAfterSplit.nextSibling;
      clone.append(nodeAfterSplit);
      nodeAfterSplit = next;
    }
    if (node instanceof HTMLOListElement && getClosest(node, root, "BLOCKQUOTE")) {
      clone.start = (+node.start || 1) + node.childNodes.length - 1;
    }
    fixCursor(node);
    fixCursor(clone);
    node.after(clone);
    return split(parent, clone, stopNode, root);
  };
  var _mergeInlines = (node, fakeRange) => {
    const children = node.childNodes;
    let l = children.length;
    const frags = [];
    while (l--) {
      const child = children[l];
      const prev = l ? children[l - 1] : null;
      if (prev && isInline(child) && areAlike(child, prev)) {
        if (fakeRange.startContainer === child) {
          fakeRange.startContainer = prev;
          fakeRange.startOffset += getLength(prev);
        }
        if (fakeRange.endContainer === child) {
          fakeRange.endContainer = prev;
          fakeRange.endOffset += getLength(prev);
        }
        if (fakeRange.startContainer === node) {
          if (fakeRange.startOffset > l) {
            --fakeRange.startOffset;
          } else if (fakeRange.startOffset === l) {
            fakeRange.startContainer = prev;
            fakeRange.startOffset = getLength(prev);
          }
        }
        if (fakeRange.endContainer === node) {
          if (fakeRange.endOffset > l) {
            --fakeRange.endOffset;
          } else if (fakeRange.endOffset === l) {
            fakeRange.endContainer = prev;
            fakeRange.endOffset = getLength(prev);
          }
        }
        detach(child);
        if (child instanceof Text) {
          prev.appendData(child.data);
        } else {
          frags.push(empty(child));
        }
      } else if (child instanceof Element) {
        let frag;
        while (frag = frags.pop()) {
          child.append(frag);
        }
        _mergeInlines(child, fakeRange);
      }
    }
  };
  var mergeInlines = (node, range) => {
    const element = node instanceof Text ? node.parentNode : node;
    if (element instanceof Element) {
      const fakeRange = {
        startContainer: range.startContainer,
        startOffset: range.startOffset,
        endContainer: range.endContainer,
        endOffset: range.endOffset
      };
      _mergeInlines(element, fakeRange);
      range.setStart(fakeRange.startContainer, fakeRange.startOffset);
      range.setEnd(fakeRange.endContainer, fakeRange.endOffset);
    }
  };
  var mergeWithBlock = (block, next, range, root) => {
    let container = next;
    let parent;
    let offset;
    while ((parent = container.parentNode) && parent !== root && parent instanceof Element && parent.childNodes.length === 1) {
      container = parent;
    }
    detach(container);
    offset = block.childNodes.length;
    const last = block.lastChild;
    if (last && last.nodeName === "BR") {
      last.remove();
      --offset;
    }
    block.append(empty(next));
    range.setStart(block, offset);
    range.collapse(true);
    mergeInlines(block, range);
  };
  var mergeContainers = (node, root) => {
    const prev = node.previousSibling;
    const first = node.firstChild;
    const isListItem = node.nodeName === "LI";
    if (isListItem && (!first || !/^[OU]L$/.test(first.nodeName))) {
      return;
    }
    if (prev && areAlike(prev, node)) {
      if (!isContainer(prev)) {
        if (!isListItem) {
          return;
        }
        const block = createElement("DIV");
        block.append(empty(prev));
        prev.append(block);
      }
      detach(node);
      const needsFix = !isContainer(node);
      prev.append(empty(node));
      needsFix && fixContainer(prev);
      first && mergeContainers(first, root);
    } else if (isListItem) {
      const block = createElement("DIV");
      node.insertBefore(block, first);
      fixCursor(block);
    }
  };

  // source/node/Block.ts
  var getBlockWalker = (node, root) => {
    const walker = createTreeWalker(root, SHOW_ELEMENT, isBlock);
    walker.currentNode = node;
    return walker;
  };
  var getPreviousBlock = (node, root) => {
    const block = getBlockWalker(node, root).previousNode();
    return block !== root ? block : null;
  };
  var getNextBlock = (node, root) => {
    const block = getBlockWalker(node, root).nextNode();
    return block !== root ? block : null;
  };
  var isEmptyBlock = (block) => {
    return !block.textContent && !block.querySelector("IMG");
  };

  // source/range/Block.ts
  var getStartBlockOfRange = (range, root) => {
    const container = range.startContainer;
    let block;
    if (isInline(container)) {
      block = getPreviousBlock(container, root);
    } else if (container !== root && container instanceof HTMLElement && isBlock(container)) {
      block = container;
    } else {
      const node = getNodeBeforeOffset(container, range.startOffset);
      block = getNextBlock(node, root);
    }
    return block && isNodeContainedInRange(range, block, true) ? block : null;
  };
  var getEndBlockOfRange = (range, root) => {
    const container = range.endContainer;
    let block;
    if (isInline(container)) {
      block = getPreviousBlock(container, root);
    } else if (container !== root && container instanceof HTMLElement && isBlock(container)) {
      block = container;
    } else {
      let node = getNodeAfterOffset(container, range.endOffset);
      if (!node || !root.contains(node)) {
        node = root;
        let child;
        while (child = node.lastChild) {
          node = child;
        }
      }
      block = getPreviousBlock(node, root);
    }
    return block && isNodeContainedInRange(range, block, true) ? block : null;
  };
  var isContent = (node) => {
    return node instanceof Text ? notWS.test(node.data) : node.nodeName === "IMG";
  };
  var rangeDoesStartAtBlockBoundary = (range, root) => {
    const startContainer = range.startContainer;
    const startOffset = range.startOffset;
    let nodeAfterCursor;
    if (startContainer instanceof Text) {
      const text = startContainer.data;
      for (let i = startOffset; i > 0; --i) {
        if (text.charAt(i - 1) !== ZWS) {
          return false;
        }
      }
      nodeAfterCursor = startContainer;
    } else {
      nodeAfterCursor = getNodeAfterOffset(startContainer, startOffset);
      if (nodeAfterCursor && !root.contains(nodeAfterCursor)) {
        nodeAfterCursor = null;
      }
      if (!nodeAfterCursor) {
        nodeAfterCursor = getNodeBeforeOffset(startContainer, startOffset);
        if (nodeAfterCursor instanceof Text && nodeAfterCursor.length) {
          return false;
        }
      }
    }
    const block = getStartBlockOfRange(range, root);
    if (!block) {
      return false;
    }
    const contentWalker = createTreeWalker(
      block,
      SHOW_ELEMENT_OR_TEXT,
      isContent
    );
    contentWalker.currentNode = nodeAfterCursor;
    return !contentWalker.previousNode();
  };
  var rangeDoesEndAtBlockBoundary = (range, root) => {
    const endContainer = range.endContainer;
    const endOffset = range.endOffset;
    let currentNode;
    if (endContainer instanceof Text) {
      const text = endContainer.data;
      const length = text.length;
      for (let i = endOffset; i < length; ++i) {
        if (text.charAt(i) !== ZWS) {
          return false;
        }
      }
      currentNode = endContainer;
    } else {
      currentNode = getNodeBeforeOffset(endContainer, endOffset);
    }
    const block = getEndBlockOfRange(range, root);
    if (!block) {
      return false;
    }
    const contentWalker = createTreeWalker(
      block,
      SHOW_ELEMENT_OR_TEXT,
      isContent
    );
    contentWalker.currentNode = currentNode;
    return !contentWalker.nextNode();
  };
  var expandRangeToBlockBoundaries = (range, root) => {
    const start = getStartBlockOfRange(range, root);
    const end = getEndBlockOfRange(range, root);
    let parent;
    if (start && end) {
      parent = start.parentNode;
      range.setStart(parent, Array.from(parent.childNodes).indexOf(start));
      parent = end.parentNode;
      range.setEnd(parent, Array.from(parent.childNodes).indexOf(end) + 1);
    }
  };

  // source/range/InsertDelete.ts
  function createRange(startContainer, startOffset, endContainer, endOffset) {
    const range = document.createRange();
    range.setStart(startContainer, startOffset);
    if (endContainer && typeof endOffset === "number") {
      range.setEnd(endContainer, endOffset);
    } else {
      range.setEnd(startContainer, startOffset);
    }
    return range;
  }
  var insertNodeInRange = (range, node) => {
    let { startContainer, startOffset, endContainer, endOffset } = range;
    let children;
    if (startContainer instanceof Text) {
      const parent = startContainer.parentNode;
      children = parent.childNodes;
      if (startOffset === startContainer.length) {
        startOffset = Array.from(children).indexOf(startContainer) + 1;
        if (range.collapsed) {
          endContainer = parent;
          endOffset = startOffset;
        }
      } else {
        if (startOffset) {
          const afterSplit = startContainer.splitText(startOffset);
          if (endContainer === startContainer) {
            endOffset -= startOffset;
            endContainer = afterSplit;
          } else if (endContainer === parent) {
            ++endOffset;
          }
          startContainer = afterSplit;
        }
        startOffset = Array.from(children).indexOf(
          startContainer
        );
      }
      startContainer = parent;
    } else {
      children = startContainer.childNodes;
    }
    const childCount = children.length;
    if (startOffset === childCount) {
      startContainer.append(node);
    } else {
      startContainer.insertBefore(node, children[startOffset]);
    }
    if (startContainer === endContainer) {
      endOffset += children.length - childCount;
    }
    range.setStart(startContainer, startOffset);
    range.setEnd(endContainer, endOffset);
  };
  var extractContentsOfRange = (range, common, root) => {
    const frag = document.createDocumentFragment();
    if (range.collapsed) {
      return frag;
    }
    if (!common) {
      common = range.commonAncestorContainer;
    }
    if (common instanceof Text) {
      common = common.parentNode;
    }
    const startContainer = range.startContainer;
    const startOffset = range.startOffset;
    let endContainer = split(range.endContainer, range.endOffset, common, root);
    let endOffset = 0;
    let node = split(startContainer, startOffset, common, root);
    while (node && node !== endContainer) {
      const next = node.nextSibling;
      frag.append(node);
      node = next;
    }
    node = endContainer && endContainer.previousSibling;
    if (node && node instanceof Text && endContainer instanceof Text) {
      endOffset = node.length;
      node.appendData(endContainer.data);
      detach(endContainer);
      endContainer = node;
    }
    range.setStart(startContainer, startOffset);
    if (endContainer) {
      range.setEnd(endContainer, endOffset);
    } else {
      range.setEnd(common, common.childNodes.length);
    }
    fixCursor(common);
    return frag;
  };
  var getAdjacentInlineNode = (iterator, method, node) => {
    iterator.currentNode = node;
    let nextNode;
    while (nextNode = iterator[method]()) {
      if (nextNode instanceof Text || isLeaf(nextNode)) {
        return nextNode;
      }
      if (!isInline(nextNode)) {
        return null;
      }
    }
    return null;
  };
  var deleteContentsOfRange = (range, root) => {
    const startBlock = getStartBlockOfRange(range, root);
    let endBlock = getEndBlockOfRange(range, root);
    const needsMerge = startBlock !== endBlock;
    if (startBlock && endBlock) {
      moveRangeBoundariesDownTree(range);
      moveRangeBoundariesUpTree(range, startBlock, endBlock, root);
    }
    const frag = extractContentsOfRange(range, null, root);
    moveRangeBoundariesDownTree(range);
    if (needsMerge) {
      endBlock = getEndBlockOfRange(range, root);
      if (startBlock && endBlock && startBlock !== endBlock) {
        mergeWithBlock(startBlock, endBlock, range, root);
      }
    }
    if (startBlock) {
      fixCursor(startBlock);
    }
    const child = root.firstChild;
    if (!child || child.nodeName === "BR") {
      fixCursor(root);
      if (root.firstChild) {
        range.selectNodeContents(root.firstChild);
      }
    }
    range.collapse(true);
    const startContainer = range.startContainer;
    const startOffset = range.startOffset;
    const iterator = createTreeWalker(root, SHOW_ELEMENT_OR_TEXT);
    let afterNode = startContainer;
    let afterOffset = startOffset;
    if (!(afterNode instanceof Text) || afterOffset === afterNode.length) {
      afterNode = getAdjacentInlineNode(iterator, "nextNode", afterNode);
      afterOffset = 0;
    }
    let beforeNode = startContainer;
    let beforeOffset = startOffset - 1;
    if (!(beforeNode instanceof Text) || beforeOffset === -1) {
      beforeNode = getAdjacentInlineNode(
        iterator,
        "previousPONode",
        afterNode || (startContainer instanceof Text ? startContainer : startContainer.childNodes[startOffset] || startContainer)
      );
      if (beforeNode instanceof Text) {
        beforeOffset = beforeNode.length;
      }
    }
    let node = null;
    let offset = 0;
    if (afterNode instanceof Text && afterNode.data.charAt(afterOffset) === " " && rangeDoesStartAtBlockBoundary(range, root)) {
      node = afterNode;
      offset = afterOffset;
    } else if (beforeNode instanceof Text && beforeNode.data.charAt(beforeOffset) === " ") {
      if (afterNode instanceof Text && afterNode.data.charAt(afterOffset) === " " || rangeDoesEndAtBlockBoundary(range, root)) {
        node = beforeNode;
        offset = beforeOffset;
      }
    }
    if (node) {
      node.replaceData(offset, 1, "\xA0");
    }
    range.setStart(startContainer, startOffset);
    range.collapse(true);
    return frag;
  };
  var insertTreeFragmentIntoRange = (range, frag, root) => {
    const firstInFragIsInline = frag.firstChild && isInline(frag.firstChild);
    let node;
    fixContainer(frag);
    node = frag;
    while (node = getNextBlock(node, root)) {
      fixCursor(node);
    }
    if (!range.collapsed) {
      deleteContentsOfRange(range, root);
    }
    moveRangeBoundariesDownTree(range);
    range.collapse(false);
    const stopPoint = getClosest(range.endContainer, root, "BLOCKQUOTE") || root;
    let block = getStartBlockOfRange(range, root);
    let blockContentsAfterSplit = null;
    const firstBlockInFrag = getNextBlock(frag, frag);
    const replaceBlock = !firstInFragIsInline && !!block && isEmptyBlock(block);
    if (block && firstBlockInFrag && !replaceBlock && // Don't merge table cells or PRE elements into block
    !getClosest(firstBlockInFrag, frag, "PRE") && !getClosest(firstBlockInFrag, frag, "TABLE")) {
      moveRangeBoundariesUpTree(range, block, block, root);
      range.collapse(true);
      let container = range.endContainer;
      let offset = range.endOffset;
      cleanupBRs(block);
      if (isInline(container)) {
        const nodeAfterSplit = split(
          container,
          offset,
          getPreviousBlock(container, root) || root,
          root
        );
        container = nodeAfterSplit.parentNode;
        offset = Array.from(container.childNodes).indexOf(
          nodeAfterSplit
        );
      }
      if (
        /*isBlock( container ) && */
        offset !== getLength(container)
      ) {
        blockContentsAfterSplit = document.createDocumentFragment();
        while (node = container.childNodes[offset]) {
          blockContentsAfterSplit.append(node);
        }
      }
      mergeWithBlock(container, firstBlockInFrag, range, root);
      offset = Array.from(container.parentNode.childNodes).indexOf(
        container
      ) + 1;
      container = container.parentNode;
      range.setEnd(container, offset);
    }
    if (getLength(frag)) {
      if (replaceBlock && block) {
        range.setEndBefore(block);
        range.collapse(false);
        detach(block);
      }
      moveRangeBoundariesUpTree(range, stopPoint, stopPoint, root);
      let nodeAfterSplit = split(
        range.endContainer,
        range.endOffset,
        stopPoint,
        root
      );
      const nodeBeforeSplit = nodeAfterSplit ? nodeAfterSplit.previousSibling : stopPoint.lastChild;
      stopPoint.insertBefore(frag, nodeAfterSplit);
      if (nodeAfterSplit) {
        range.setEndBefore(nodeAfterSplit);
      } else {
        range.setEnd(stopPoint, getLength(stopPoint));
      }
      block = getEndBlockOfRange(range, root);
      moveRangeBoundariesDownTree(range);
      const container = range.endContainer;
      const offset = range.endOffset;
      if (nodeAfterSplit && isContainer(nodeAfterSplit)) {
        mergeContainers(nodeAfterSplit, root);
      }
      nodeAfterSplit = nodeBeforeSplit && nodeBeforeSplit.nextSibling;
      if (nodeAfterSplit && isContainer(nodeAfterSplit)) {
        mergeContainers(nodeAfterSplit, root);
      }
      range.setEnd(container, offset);
    }
    if (blockContentsAfterSplit && block) {
      const tempRange = range.cloneRange();
      fixCursor(blockContentsAfterSplit);
      mergeWithBlock(block, blockContentsAfterSplit, tempRange, root);
      range.setEnd(tempRange.endContainer, tempRange.endOffset);
    }
    moveRangeBoundariesDownTree(range);
  };

  // source/range/Contents.ts
  var getTextContentsOfRange = (range) => {
    if (range.collapsed) {
      return "";
    }
    const startContainer = range.startContainer;
    const endContainer = range.endContainer;
    const walker = createTreeWalker(
      range.commonAncestorContainer,
      SHOW_ELEMENT_OR_TEXT,
      (node2) => {
        return isNodeContainedInRange(range, node2, true);
      }
    );
    walker.currentNode = startContainer;
    let node = startContainer;
    let textContent = "";
    let addedTextInBlock = false;
    let value;
    if (!(node instanceof Element) && !(node instanceof Text) || FILTER_ACCEPT !== walker.filter.acceptNode(node)) {
      node = walker.nextNode();
    }
    while (node) {
      if (node instanceof Text) {
        value = node.data;
        if (value && /\S/.test(value)) {
          if (node === endContainer) {
            value = value.slice(0, range.endOffset);
          }
          if (node === startContainer) {
            value = value.slice(range.startOffset);
          }
          textContent += value;
          addedTextInBlock = true;
        }
      } else if (node.nodeName === "BR" || addedTextInBlock && !isInline(node)) {
        textContent += "\n";
        addedTextInBlock = false;
      }
      node = walker.nextNode();
    }
    textContent = textContent.replace(/ /g, " ");
    return textContent;
  };

  // source/Clipboard.ts
  var indexOf = Array.prototype.indexOf;
  var extractRangeToClipboard = (event, range, root, removeRangeFromDocument, toCleanHTML, toPlainText, plainTextOnly) => {
    const clipboardData = event.clipboardData;
    if (!clipboardData) {
      return false;
    }
    let text = toPlainText ? "" : getTextContentsOfRange(range);
    const startBlock = getStartBlockOfRange(range, root);
    const endBlock = getEndBlockOfRange(range, root);
    let copyRoot = root;
    if (startBlock === endBlock && startBlock?.contains(range.commonAncestorContainer)) {
      copyRoot = startBlock;
    }
    let contents;
    if (removeRangeFromDocument) {
      contents = deleteContentsOfRange(range, root);
    } else {
      range = range.cloneRange();
      moveRangeBoundariesDownTree(range);
      moveRangeBoundariesUpTree(range, copyRoot, copyRoot, root);
      contents = range.cloneContents();
    }
    let parent = range.commonAncestorContainer;
    if (parent instanceof Text) {
      parent = parent.parentNode;
    }
    while (parent && parent !== copyRoot) {
      const newContents = parent.cloneNode(false);
      newContents.append(contents);
      contents = newContents;
      parent = parent.parentNode;
    }
    let html;
    if (contents.childNodes.length === 1 && contents.childNodes[0] instanceof Text) {
      text = contents.childNodes[0].data.replace(/ /g, " ");
      plainTextOnly = true;
    } else {
      const node = createElement("DIV");
      node.append(contents);
      html = node.innerHTML;
      if (toCleanHTML) {
        html = toCleanHTML(html);
      }
    }
    if (toPlainText && html !== void 0) {
      text = toPlainText(html);
    }
    if (isWin) {
      text = text.replace(/\r?\n/g, "\r\n");
    }
    if (!plainTextOnly && html && text !== html) {
      html = "<!-- squire -->" + html;
      clipboardData.setData("text/html", html);
    }
    clipboardData.setData("text/plain", text);
    event.preventDefault();
    return true;
  };
  var _onCut = function(event) {
    const range = this.getSelection();
    const root = this._root;
    if (range.collapsed) {
      event.preventDefault();
      return;
    }
    this.saveUndoState(range);
    const handled = extractRangeToClipboard(
      event,
      range,
      root,
      true,
      this._config.willCutCopy,
      this._config.toPlainText,
      false
    );
    if (!handled) {
      setTimeout(() => {
        try {
          this._ensureBottomLine();
        } catch (error) {
          this._config.didError(error);
        }
      }, 0);
    }
    this.setSelection(range);
  };
  var _onCopy = function(event) {
    extractRangeToClipboard(
      event,
      this.getSelection(),
      this._root,
      false,
      this._config.willCutCopy,
      this._config.toPlainText,
      false
    );
  };
  var _monitorShiftKey = function(event) {
    this._isShiftDown = event.shiftKey;
  };
  var _onPaste = function(event) {
    const clipboardData = event.clipboardData;
    const items = clipboardData.items;
    const choosePlain = this._isShiftDown;
    let hasRTF = false;
    let hasImage = false;
    let plainItem = null;
    let htmlItem = null;
    let l = items.length;
    while (l--) {
      const item = items[l];
      const type = item.type;
      if (type === "text/html") {
        htmlItem = item;
      } else if (type === "text/plain" || type === "text/uri-list") {
        plainItem = item;
      } else if (type === "text/rtf") {
        hasRTF = true;
      } else if (/^image\/.*/.test(type)) {
        hasImage = true;
      }
    }
    if (hasImage && !(hasRTF && htmlItem)) {
      event.preventDefault();
      this.fireEvent("pasteImage", {
        clipboardData
      });
      return;
    }
    event.preventDefault();
    if (htmlItem && (!choosePlain || !plainItem)) {
      htmlItem.getAsString((html) => {
        this.insertHTML(html, true);
      });
    } else if (plainItem) {
      plainItem.getAsString((text) => {
        let isLink = false;
        const range = this.getSelection();
        if (!range.collapsed && notWS.test(range.toString())) {
          const match = this.linkRegExp.exec(text);
          isLink = !!match && match[0].length === text.length;
        }
        if (isLink) {
          this.makeLink(text);
        } else {
          this.insertPlainText(text, true);
        }
      });
    }
  };
  var _onDrop = function(event) {
    if (!event.dataTransfer) {
      return;
    }
    const types = event.dataTransfer.types;
    let l = types.length;
    let hasPlain = false;
    let hasHTML = false;
    while (l--) {
      switch (types[l]) {
        case "text/plain":
          hasPlain = true;
          break;
        case "text/html":
          hasHTML = true;
          break;
        default:
          return;
      }
    }
    if (hasHTML || hasPlain && this.saveUndoState) {
      this.saveUndoState();
    }
  };

  // source/keyboard/KeyHelpers.ts
  var afterDelete = (self, range) => {
    try {
      if (!range) {
        range = self.getSelection();
      }
      let node = range.startContainer;
      if (node instanceof Text) {
        node = node.parentNode;
      }
      let parent = node;
      while (isInline(parent) && (!parent.textContent || parent.textContent === ZWS)) {
        node = parent;
        parent = node.parentNode;
      }
      if (node !== parent) {
        range.setStart(
          parent,
          Array.from(parent.childNodes).indexOf(node)
        );
        range.collapse(true);
        parent.removeChild(node);
        if (!isBlock(parent)) {
          parent = getPreviousBlock(parent, self._root) || self._root;
        }
        fixCursor(parent);
        moveRangeBoundariesDownTree(range);
      }
      if (node === self._root && (node = node.firstChild) && node.nodeName === "BR") {
        detach(node);
      }
      self._ensureBottomLine();
      self.setSelection(range);
      self._updatePath(range, true);
    } catch (error) {
      self._config.didError(error);
    }
  };
  var detachUneditableNode = (node, root) => {
    let parent;
    while (parent = node.parentNode) {
      if (parent === root || parent.isContentEditable) {
        break;
      }
      node = parent;
    }
    detach(node);
  };
  var linkifyText = (self, textNode, offset) => {
    if (getClosest(textNode, self._root, "A")) {
      return;
    }
    const data = textNode.data || "";
    const searchFrom = Math.max(
      data.lastIndexOf(" ", offset - 1),
      data.lastIndexOf("\xA0", offset - 1)
    ) + 1;
    const searchText = data.slice(searchFrom, offset);
    const match = self.linkRegExp.exec(searchText);
    if (match) {
      const selection = self.getSelection();
      self._docWasChanged();
      self._recordUndoState(selection);
      self._getRangeAndRemoveBookmark(selection);
      const index = searchFrom + match.index;
      const endIndex = index + match[0].length;
      const needsSelectionUpdate = selection.startContainer === textNode;
      const newSelectionOffset = selection.startOffset - endIndex;
      if (index) {
        textNode = textNode.splitText(index);
      }
      const defaultAttributes = self._config.tagAttributes.a;
      const link = createElement(
        "A",
        Object.assign(
          {
            href: match[1] ? /^(?:ht|f)tps?:/i.test(match[1]) ? match[1] : "http://" + match[1] : "mailto:" + match[0]
          },
          defaultAttributes
        )
      );
      link.textContent = data.slice(index, endIndex);
      textNode.parentNode.insertBefore(link, textNode);
      textNode.data = data.slice(endIndex);
      if (needsSelectionUpdate) {
        selection.setStart(textNode, newSelectionOffset);
        selection.setEnd(textNode, newSelectionOffset);
      }
      self.setSelection(selection);
    }
  };

  // source/keyboard/Backspace.ts
  var Backspace = (self, event, range) => {
    const root = self._root;
    self._removeZWS();
    self.saveUndoState(range);
    if (!range.collapsed) {
      event.preventDefault();
      deleteContentsOfRange(range, root);
      afterDelete(self, range);
    } else if (rangeDoesStartAtBlockBoundary(range, root)) {
      event.preventDefault();
      const startBlock = getStartBlockOfRange(range, root);
      if (!startBlock) {
        return;
      }
      let current = startBlock;
      fixContainer(current.parentNode);
      const previous = getPreviousBlock(current, root);
      if (previous) {
        if (!previous.isContentEditable) {
          detachUneditableNode(previous, root);
          return;
        }
        mergeWithBlock(previous, current, range, root);
        current = previous.parentNode;
        while (current !== root && !current.nextSibling) {
          current = current.parentNode;
        }
        if (current !== root && (current = current.nextSibling)) {
          mergeContainers(current, root);
        }
        self.setSelection(range);
      } else if (current) {
        if (getClosest(current, root, "UL") || getClosest(current, root, "OL")) {
          self.decreaseListLevel(range);
          return;
        } else if (getClosest(current, root, "BLOCKQUOTE")) {
          self.removeQuote(range);
          return;
        }
        self.setSelection(range);
        self._updatePath(range, true);
      }
    } else {
      moveRangeBoundariesDownTree(range);
      const text = range.startContainer;
      const offset = range.startOffset;
      const a = text.parentNode;
      if (text instanceof Text && a instanceof HTMLAnchorElement && offset && a.href.includes(text.data)) {
        text.deleteData(offset - 1, 1);
        self.setSelection(range);
        self.removeLink();
        event.preventDefault();
      } else {
        self.setSelection(range);
        setTimeout(() => {
          afterDelete(self);
        }, 0);
      }
    }
  };

  // source/keyboard/Delete.ts
  var Delete = (self, event, range) => {
    const root = self._root;
    let current;
    let next;
    let originalRange;
    let cursorContainer;
    let cursorOffset;
    let nodeAfterCursor;
    self._removeZWS();
    self.saveUndoState(range);
    if (!range.collapsed) {
      event.preventDefault();
      deleteContentsOfRange(range, root);
      afterDelete(self, range);
    } else if (rangeDoesEndAtBlockBoundary(range, root)) {
      event.preventDefault();
      current = getStartBlockOfRange(range, root);
      if (!current) {
        return;
      }
      fixContainer(current.parentNode);
      next = getNextBlock(current, root);
      if (next) {
        if (!next.isContentEditable) {
          detachUneditableNode(next, root);
          return;
        }
        mergeWithBlock(current, next, range, root);
        next = current.parentNode;
        while (next !== root && !next.nextSibling) {
          next = next.parentNode;
        }
        if (next !== root && (next = next.nextSibling)) {
          mergeContainers(next, root);
        }
        self.setSelection(range);
        self._updatePath(range, true);
      }
    } else {
      originalRange = range.cloneRange();
      moveRangeBoundariesUpTree(range, root, root, root);
      cursorContainer = range.endContainer;
      cursorOffset = range.endOffset;
      if (cursorContainer instanceof Element) {
        nodeAfterCursor = cursorContainer.childNodes[cursorOffset];
        if (nodeAfterCursor && nodeAfterCursor.nodeName === "IMG") {
          event.preventDefault();
          detach(nodeAfterCursor);
          moveRangeBoundariesDownTree(range);
          afterDelete(self, range);
          return;
        }
      }
      self.setSelection(originalRange);
      setTimeout(() => {
        afterDelete(self);
      }, 0);
    }
  };

  // source/keyboard/Tab.ts
  var Tab = (self, event, range) => {
    const root = self._root;
    self._removeZWS();
    if (range.collapsed && rangeDoesStartAtBlockBoundary(range, root)) {
      getClosest(range.startContainer, root, "UL,OL,BLOCKQUOTE") && self.changeIndentationLevel("increase") && event.preventDefault();
    }
  };
  var ShiftTab = (self, event, range) => {
    const root = self._root;
    self._removeZWS();
    if (range.collapsed && rangeDoesStartAtBlockBoundary(range, root)) {
      decreaseLevel(self, range, range.startContainer) && event.preventDefault();
    }
  };

  // source/keyboard/Space.ts
  var Space = (self, event, range) => {
    let node;
    const root = self._root;
    self._recordUndoState(range);
    self._getRangeAndRemoveBookmark(range);
    if (!range.collapsed) {
      deleteContentsOfRange(range, root);
      self._ensureBottomLine();
      self.setSelection(range);
      self._updatePath(range, true);
    } else if (rangeDoesEndAtBlockBoundary(range, root)) {
      const block = getStartBlockOfRange(range, root);
      if (block && block.nodeName !== "PRE") {
        const text = block.textContent?.trimEnd().replace(ZWS, "");
        if (text === "*" || text === "1.") {
          event.preventDefault();
          self.insertPlainText(" ", false);
          self._docWasChanged();
          self.saveUndoState(range);
          const walker = createTreeWalker(block, SHOW_TEXT);
          let textNode;
          while (textNode = walker.nextNode()) {
            detach(textNode);
          }
          if (text === "*") {
            self.makeUnorderedList();
          } else {
            self.makeOrderedList();
          }
          return;
        }
      }
    }
    node = range.endContainer;
    if (range.endOffset === getLength(node)) {
      do {
        if (node.nodeName === "A") {
          range.setStartAfter(node);
          break;
        }
      } while (!node.nextSibling && (node = node.parentNode) && node !== root);
    }
    if (self._config.addLinks) {
      const linkRange = range.cloneRange();
      moveRangeBoundariesDownTree(linkRange);
      const textNode = linkRange.startContainer;
      const offset = linkRange.startOffset;
      setTimeout(() => {
        linkifyText(self, textNode, offset);
      }, 0);
    }
    self.setSelection(range);
  };

  // source/keyboard/KeyHandlers.ts
  var _onKey = function(event) {
    if (event.defaultPrevented || event.isComposing) {
      return;
    }
    let key = event.key;
    let modifiers = "";
    const code = event.code;
    if (/^Digit\d$/.test(code)) {
      key = code.slice(-1);
    }
    if (key !== "Backspace" && key !== "Delete") {
      if (event.altKey) {
        modifiers += "Alt-";
      }
      if (event.ctrlKey) {
        modifiers += "Ctrl-";
      }
      if (event.metaKey) {
        modifiers += "Meta-";
      }
      if (event.shiftKey) {
        modifiers += "Shift-";
      }
    }
    if (isWin && event.shiftKey && key === "Delete") {
      modifiers += "Shift-";
    }
    key = modifiers + key;
    const range = this.getSelection();
    if (this._keyHandlers[key]) {
      this._keyHandlers[key](this, event, range);
    } else if (!range.collapsed && !event.ctrlKey && !event.metaKey && key.length === 1) {
      this.saveUndoState(range);
      deleteContentsOfRange(range, this._root);
      this._ensureBottomLine();
      this.setSelection(range);
      this._updatePath(range, true);
    }
  };
  var keyHandlers = {
    "Backspace": Backspace,
    "Delete": Delete,
    "Tab": Tab,
    "Shift-Tab": ShiftTab,
    " ": Space,
    "ArrowLeft"(self) {
      self._removeZWS();
    },
    "ArrowRight"(self, event, range) {
      self._removeZWS();
      const root = self.getRoot();
      if (rangeDoesEndAtBlockBoundary(range, root)) {
        moveRangeBoundariesDownTree(range);
        let node = range.endContainer;
        do {
          if (node.nodeName === "CODE") {
            let next = node.nextSibling;
            if (!(next instanceof Text)) {
              const textNode = document.createTextNode("\xA0");
              node.parentNode.insertBefore(textNode, next);
              next = textNode;
            }
            range.setStart(next, 1);
            self.setSelection(range);
            event.preventDefault();
            break;
          }
        } while (!node.nextSibling && (node = node.parentNode) && node !== root);
      }
    }
  };
  if (!isMac && !isIOS) {
    keyHandlers.PageUp = (self) => {
      self.moveCursorToStart();
    };
    keyHandlers.PageDown = (self) => {
      self.moveCursorToEnd();
    };
  }
  var mapKeyToFormat = (tag, remove) => {
    remove = remove || null;
    return (self, event) => {
      event.preventDefault();
      const range = self.getSelection();
      if (self.hasFormat(tag, null, range)) {
        self.changeFormat(null, { tag }, range);
      } else {
        self.changeFormat({ tag }, remove, range);
      }
    };
  };
  keyHandlers[ctrlKey + "b"] = mapKeyToFormat("B");
  keyHandlers[ctrlKey + "i"] = mapKeyToFormat("I");
  keyHandlers[ctrlKey + "u"] = mapKeyToFormat("U");
  keyHandlers[ctrlKey + "Shift-7"] = mapKeyToFormat("S");
  keyHandlers[ctrlKey + "Shift-5"] = mapKeyToFormat("SUB", { tag: "SUP" });
  keyHandlers[ctrlKey + "Shift-6"] = mapKeyToFormat("SUP", { tag: "SUB" });
  keyHandlers[ctrlKey + "Shift-8"] = (self, event) => {
    event.preventDefault();
    const path = self.getPath();
    if (!/(?:^|>)UL/.test(path)) {
      self.makeUnorderedList();
    } else {
      self.removeList();
    }
  };
  keyHandlers[ctrlKey + "Shift-9"] = (self, event) => {
    event.preventDefault();
    const path = self.getPath();
    if (!/(?:^|>)OL/.test(path)) {
      self.makeOrderedList();
    } else {
      self.removeList();
    }
  };
  keyHandlers[ctrlKey + "["] = (self, event) => {
    event.preventDefault();
    const path = self.getPath();
    if (/(?:^|>)BLOCKQUOTE/.test(path) || !/(?:^|>)[OU]L/.test(path)) {
      self.decreaseQuoteLevel();
    } else {
      self.decreaseListLevel();
    }
  };
  keyHandlers[ctrlKey + "]"] = (self, event) => {
    event.preventDefault();
    const path = self.getPath();
    if (/(?:^|>)BLOCKQUOTE/.test(path) || !/(?:^|>)[OU]L/.test(path)) {
      self.increaseQuoteLevel();
    } else {
      self.increaseListLevel();
    }
  };
  keyHandlers[ctrlKey + "d"] = (self, event) => {
    event.preventDefault();
    self.toggleCode();
  };
  keyHandlers[ctrlKey + "z"] = (self, event) => {
    event.preventDefault();
    self.undo();
  };
  keyHandlers[ctrlKey + "y"] = // Depending on platform, the Shift may cause the key to come through as
  // upper case, but sometimes not. Just add both as shortcuts — the browser
  // will only ever fire one or the other.
  keyHandlers[ctrlKey + "Shift-z"] = keyHandlers[ctrlKey + "Shift-Z"] = (self, event) => {
    event.preventDefault();
    self.redo();
  };

  // source/Editor.ts
  var Squire = class {
    constructor(root, config) {
      /**
       * Subscribing to these events won't automatically add a listener to the
       * document node, since these events are fired in a custom manner by the
       * editor code.
       */
      this.customEvents = /* @__PURE__ */ new Set([
        "pathChange",
        "select",
        "input",
        "pasteImage",
        "undoStateChange"
      ]);
      // ---
      this.startSelectionId = "squire-selection-start";
      this.endSelectionId = "squire-selection-end";
      /*
      linkRegExp = new RegExp(
          // Only look on boundaries
          '\\b(?:' +
          // Capture group 1: URLs
          '(' +
              // Add links to URLS
              // Starts with:
              '(?:' +
                  // http(s):// or ftp://
                  '(?:ht|f)tps?:\\/\\/' +
                  // or
                  '|' +
                  // www.
                  'www\\d{0,3}[.]' +
                  // or
                  '|' +
                  // foo90.com/
                  '[a-z0-9][a-z0-9.\\-]*[.][a-z]{2,}\\/' +
              ')' +
              // Then we get one or more:
              '(?:' +
                  // Run of non-spaces, non ()<>
                  '[^\\s()<>]+' +
                  // or
                  '|' +
                  // balanced parentheses (one level deep only)
                  '\\([^\\s()<>]+\\)' +
              ')+' +
              // And we finish with
              '(?:' +
                  // Not a space or punctuation character
                  '[^\\s?&`!()\\[\\]{};:\'".,<>«»“”‘’]' +
                  // or
                  '|' +
                  // Balanced parentheses.
                  '\\([^\\s()<>]+\\)' +
              ')' +
          // Capture group 2: Emails
          ')|(' +
              // Add links to emails
              '[\\w\\-.%+]+@(?:[\\w\\-]+\\.)+[a-z]{2,}\\b' +
              // Allow query parameters in the mailto: style
              '(?:' +
                  '[?][^&?\\s]+=[^\\s?&`!()\\[\\]{};:\'".,<>«»“”‘’]+' +
                  '(?:&[^&?\\s]+=[^\\s?&`!()\\[\\]{};:\'".,<>«»“”‘’]+)*' +
              ')?' +
          '))',
          'i'
      );
      */
      this.linkRegExp = /\b(?:((?:(?:ht|f)tps?:\/\/|www\d{0,3}[.]|[a-z0-9][a-z0-9.\-]*[.][a-z]{2,}\/)(?:[^\s()<>]+|\([^\s()<>]+\))+(?:[^\s?&`!()\[\]{};:'".,<>«»“”‘’]|\([^\s()<>]+\)))|([\w\-.%+]+@(?:[\w\-]+\.)+[a-z]{2,}\b(?:[?][^&?\s]+=[^\s?&`!()\[\]{};:'".,<>«»“”‘’]+(?:&[^&?\s]+=[^\s?&`!()\[\]{};:'".,<>«»“”‘’]+)*)?))/i;
      this.tagAfterSplit = {
        DT: "DD",
        DD: "DT",
        LI: "LI",
        PRE: "PRE"
      };
      this._root = root;
      this._config = this._makeConfig(config);
      this._isFocused = false;
      this._lastSelection = createRange(root, 0);
      this._willRestoreSelection = false;
      this._mayHaveZWS = false;
      this._lastAnchorNode = null;
      this._lastFocusNode = null;
      this._path = "";
      this._events = /* @__PURE__ */ new Map();
      this._undoIndex = -1;
      this._undoStack = [];
      this._undoStackLength = 0;
      this._isInUndoState = false;
      this._ignoreChange = false;
      this._ignoreAllChanges = false;
      this.addEventListener("selectionchange", this._updatePathOnEvent);
      this.addEventListener("blur", this._enableRestoreSelection);
      this.addEventListener("mousedown", this._disableRestoreSelection);
      this.addEventListener("touchstart", this._disableRestoreSelection);
      this.addEventListener("focus", this._restoreSelection);
      this.addEventListener("blur", this._removeZWS);
      this._isShiftDown = false;
      this.addEventListener("cut", _onCut);
      this.addEventListener("copy", _onCopy);
      this.addEventListener("paste", _onPaste);
      this.addEventListener("drop", _onDrop);
      this.addEventListener(
        "keydown",
        _monitorShiftKey
      );
      this.addEventListener("keyup", _monitorShiftKey);
      this.addEventListener("keydown", _onKey);
      this._keyHandlers = Object.create(keyHandlers);
      const mutation = new MutationObserver(() => this._docWasChanged());
      mutation.observe(root, {
        childList: true,
        attributes: true,
        characterData: true,
        subtree: true
      });
      this._mutation = mutation;
      root.setAttribute("contenteditable", "true");
      this.addEventListener(
        "beforeinput",
        this._beforeInput
      );
      this.setHTML("");
    }
    destroy() {
      this._events.forEach((_, type) => {
        this.removeEventListener(type);
      });
      this._mutation.disconnect();
      this._undoIndex = -1;
      this._undoStack = [];
      this._undoStackLength = 0;
    }
    _makeConfig(userConfig) {
      const config = {
        blockTag: "DIV",
        classNames: {
          color: "color",
          fontFamily: "font",
          fontSize: "size",
          highlight: "highlight"
        },
        undo: {
          documentSizeThreshold: -1,
          // -1 means no threshold
          undoLimit: -1
          // -1 means no limit
        },
        addLinks: true,
        willCutCopy: null,
        toPlainText: null,
        sanitizeToDOMFragment: (html) => {
          const frag = DOMPurify.sanitize(html, {
            ALLOW_UNKNOWN_PROTOCOLS: true,
            WHOLE_DOCUMENT: false,
            RETURN_DOM: true,
            RETURN_DOM_FRAGMENT: true,
            FORCE_BODY: false
          });
          return frag ? document.importNode(frag, true) : document.createDocumentFragment();
        },
        didError: (error) => console.log(error)
      };
      if (userConfig) {
        Object.assign(config, userConfig);
        config.blockTag = config.blockTag.toUpperCase();
      }
      return config;
    }
    setKeyHandler(key, fn) {
      this._keyHandlers[key] = fn;
      return this;
    }
    _beforeInput(event) {
      switch (event.inputType) {
        case "insertLineBreak":
          event.preventDefault();
          this.splitBlock(true);
          break;
        case "insertParagraph":
          event.preventDefault();
          this.splitBlock(false);
          break;
        case "insertOrderedList":
          event.preventDefault();
          this.makeOrderedList();
          break;
        case "insertUnoderedList":
          event.preventDefault();
          this.makeUnorderedList();
          break;
        case "historyUndo":
          event.preventDefault();
          this.undo();
          break;
        case "historyRedo":
          event.preventDefault();
          this.redo();
          break;
        case "formatBold":
          event.preventDefault();
          this.bold();
          break;
        case "formaItalic":
          event.preventDefault();
          this.italic();
          break;
        case "formatUnderline":
          event.preventDefault();
          this.underline();
          break;
        case "formatStrikeThrough":
          event.preventDefault();
          this.strikethrough();
          break;
        case "formatSuperscript":
          event.preventDefault();
          this.superscript();
          break;
        case "formatSubscript":
          event.preventDefault();
          this.subscript();
          break;
        case "formatJustifyFull":
        case "formatJustifyCenter":
        case "formatJustifyRight":
        case "formatJustifyLeft": {
          event.preventDefault();
          let alignment = event.inputType.slice(13).toLowerCase();
          if (alignment === "full") {
            alignment = "justify";
          }
          this.setTextAlignment(alignment);
          break;
        }
        case "formatRemove":
          event.preventDefault();
          this.setStyle();
          break;
        case "formatSetBlockTextDirection": {
          event.preventDefault();
          let dir = event.data;
          if (dir === "null") {
            dir = null;
          }
          this.setTextDirection(dir);
          break;
        }
        case "formatBackColor":
          event.preventDefault();
          this.setStyle({ backgroundColor: event.data });
          break;
        case "formatFontColor":
          event.preventDefault();
          this.setStyle({ color: event.data });
          break;
        case "formatFontName":
          event.preventDefault();
          this.setStyle({ fontFamily: event.data });
          break;
      }
    }
    // --- Events
    handleEvent(event) {
      this.fireEvent(event.type, event);
    }
    fireEvent(type, detail) {
      let handlers = this._events.get(type);
      if (/^(?:focus|blur)/.test(type)) {
        const isFocused = this._root === document.activeElement;
        if (type === "focus") {
          if (!isFocused || this._isFocused) {
            return this;
          }
          this._isFocused = true;
        } else {
          if (isFocused || !this._isFocused) {
            return this;
          }
          this._isFocused = false;
        }
      }
      if (handlers) {
        const event = detail instanceof Event ? detail : new CustomEvent(type, {
          detail
        });
        handlers = handlers.slice();
        for (const handler of handlers) {
          try {
            if ("handleEvent" in handler) {
              handler.handleEvent(event);
            } else {
              handler.call(this, event);
            }
          } catch (error) {
            this._config.didError(error);
          }
        }
      }
      return this;
    }
    addEventListener(type, fn) {
      let handlers = this._events.get(type);
      let target = this._root;
      if (!handlers) {
        handlers = [];
        this._events.set(type, handlers);
        if (!this.customEvents.has(type)) {
          if (type === "selectionchange") {
            target = document;
          }
          target.addEventListener(type, this, true);
        }
      }
      handlers.push(fn);
      return this;
    }
    removeEventListener(type, fn) {
      const handlers = this._events.get(type);
      let target = this._root;
      if (handlers) {
        if (fn) {
          let l = handlers.length;
          while (l--) {
            if (handlers[l] === fn) {
              handlers.splice(l, 1);
            }
          }
        } else {
          handlers.length = 0;
        }
        if (!handlers.length) {
          this._events.delete(type);
          if (!this.customEvents.has(type)) {
            if (type === "selectionchange") {
              target = document;
            }
            target.removeEventListener(type, this, true);
          }
        }
      }
      return this;
    }
    // --- Focus
    focus() {
      this._root.focus({ preventScroll: true });
      return this;
    }
    blur() {
      this._root.blur();
      return this;
    }
    // --- Selection and bookmarking
    _enableRestoreSelection() {
      this._willRestoreSelection = true;
    }
    _disableRestoreSelection() {
      this._willRestoreSelection = false;
    }
    _restoreSelection() {
      if (this._willRestoreSelection) {
        this.setSelection(this._lastSelection);
      }
    }
    // ---
    _removeZWS() {
      if (!this._mayHaveZWS) {
        return;
      }
      removeZWS(this._root);
      this._mayHaveZWS = false;
    }
    _saveRangeToBookmark(range) {
      let startNode = createElement("INPUT", {
        id: this.startSelectionId,
        type: "hidden"
      });
      let endNode = createElement("INPUT", {
        id: this.endSelectionId,
        type: "hidden"
      });
      let temp;
      insertNodeInRange(range, startNode);
      range.collapse(false);
      insertNodeInRange(range, endNode);
      if (startNode.compareDocumentPosition(endNode) & Node.DOCUMENT_POSITION_PRECEDING) {
        startNode.id = this.endSelectionId;
        endNode.id = this.startSelectionId;
        temp = startNode;
        startNode = endNode;
        endNode = temp;
      }
      range.setStartAfter(startNode);
      range.setEndBefore(endNode);
    }
    _getRangeAndRemoveBookmark(range) {
      const root = this._root;
      const start = root.querySelector("#" + this.startSelectionId);
      const end = root.querySelector("#" + this.endSelectionId);
      if (start && end) {
        let startContainer = start.parentNode;
        let endContainer = end.parentNode;
        const startOffset = Array.from(startContainer.childNodes).indexOf(
          start
        );
        let endOffset = Array.from(endContainer.childNodes).indexOf(end);
        if (startContainer === endContainer) {
          --endOffset;
        }
        start.remove();
        end.remove();
        if (!range) {
          range = document.createRange();
        }
        range.setStart(startContainer, startOffset);
        range.setEnd(endContainer, endOffset);
        mergeInlines(startContainer, range);
        if (startContainer !== endContainer) {
          mergeInlines(endContainer, range);
        }
        if (range.collapsed) {
          startContainer = range.startContainer;
          if (startContainer instanceof Text) {
            endContainer = startContainer.childNodes[range.startOffset];
            if (!endContainer || !(endContainer instanceof Text)) {
              endContainer = startContainer.childNodes[range.startOffset - 1];
            }
            if (endContainer && endContainer instanceof Text) {
              range.setStart(endContainer, 0);
              range.collapse(true);
            }
          }
        }
      }
      return range || null;
    }
    getSelection() {
      const selection = window.getSelection();
      const root = this._root;
      let range = null;
      if (this._isFocused && selection && selection.rangeCount) {
        range = selection.getRangeAt(0).cloneRange();
        const startContainer = range.startContainer;
        const endContainer = range.endContainer;
        if (startContainer && isLeaf(startContainer)) {
          range.setStartBefore(startContainer);
        }
        if (endContainer && isLeaf(endContainer)) {
          range.setEndBefore(endContainer);
        }
      }
      if (range && root.contains(range.commonAncestorContainer)) {
        this._lastSelection = range;
      } else {
        range = this._lastSelection;
        if (!document.contains(range.commonAncestorContainer)) {
          range = null;
        }
      }
      return range || createRange(root.firstElementChild || root, 0);
    }
    setSelection(range) {
      this._lastSelection = range;
      if (!this._isFocused) {
        this._enableRestoreSelection();
      } else {
        const selection = window.getSelection();
        if (selection) {
          if ("setBaseAndExtent" in Selection.prototype) {
            selection.setBaseAndExtent(
              range.startContainer,
              range.startOffset,
              range.endContainer,
              range.endOffset
            );
          } else {
            selection.removeAllRanges();
            selection.addRange(range);
          }
        }
      }
      return this;
    }
    // ---
    _moveCursorTo(toStart) {
      const root = this._root;
      const range = createRange(root, toStart ? 0 : root.childNodes.length);
      moveRangeBoundariesDownTree(range);
      this.setSelection(range);
      return this;
    }
    moveCursorToStart() {
      return this._moveCursorTo(true);
    }
    moveCursorToEnd() {
      return this._moveCursorTo(false);
    }
    // ---
    getCursorPosition() {
      const range = this.getSelection();
      let rect = range.getBoundingClientRect();
      if (rect && !rect.top) {
        this._ignoreChange = true;
        const node = createElement("SPAN");
        node.textContent = ZWS;
        insertNodeInRange(range, node);
        rect = node.getBoundingClientRect();
        const parent = node.parentNode;
        parent.removeChild(node);
        mergeInlines(parent, range);
      }
      return rect;
    }
    // --- Path
    getPath() {
      return this._path;
    }
    _updatePathOnEvent() {
      if (this._isFocused) {
        this._updatePath(this.getSelection());
      }
    }
    _updatePath(range, force) {
      const anchor = range.startContainer;
      const focus = range.endContainer;
      let newPath;
      if (force || anchor !== this._lastAnchorNode || focus !== this._lastFocusNode) {
        this._lastAnchorNode = anchor;
        this._lastFocusNode = focus;
        newPath = anchor && focus ? anchor === focus ? this._getPath(focus) : "(selection)" : "";
        if (this._path !== newPath || anchor !== focus) {
          this._path = newPath;
          this.fireEvent("pathChange", {
            path: newPath
          });
        }
      }
      this.fireEvent(range.collapsed ? "cursor" : "select", {
        range
      });
    }
    _getPath(node) {
      const root = this._root;
      const config = this._config;
      let path = "";
      if (node && node !== root) {
        const parent = node.parentNode;
        path = parent ? this._getPath(parent) : "";
        if (node instanceof HTMLElement) {
          const id = node.id;
          const classList = node.classList;
          const classNames = Array.from(classList).sort();
          const dir = node.dir;
          const styleNames = config.classNames;
          path += (path ? ">" : "") + node.nodeName;
          if (id) {
            path += "#" + id;
          }
          if (classNames.length) {
            path += ".";
            path += classNames.join(".");
          }
          if (dir) {
            path += "[dir=" + dir + "]";
          }
          if (classList.contains(styleNames.highlight)) {
            path += "[backgroundColor=" + node.style.backgroundColor.replace(/ /g, "") + "]";
          }
          if (classList.contains(styleNames.color)) {
            path += "[color=" + node.style.color.replace(/ /g, "") + "]";
          }
          if (classList.contains(styleNames.fontFamily)) {
            path += "[fontFamily=" + node.style.fontFamily.replace(/ /g, "") + "]";
          }
          if (classList.contains(styleNames.fontSize)) {
            path += "[fontSize=" + node.style.fontSize + "]";
          }
        }
      }
      return path;
    }
    // --- History
    modifyDocument(modificationFn) {
      const mutation = this._mutation;
      if (mutation) {
        if (mutation.takeRecords().length) {
          this._docWasChanged();
        }
        mutation.disconnect();
      }
      this._ignoreAllChanges = true;
      modificationFn();
      this._ignoreAllChanges = false;
      if (mutation) {
        mutation.observe(this._root, {
          childList: true,
          attributes: true,
          characterData: true,
          subtree: true
        });
        this._ignoreChange = false;
      }
      return this;
    }
    _docWasChanged() {
      resetNodeCategoryCache();
      this._mayHaveZWS = true;
      if (this._ignoreAllChanges) {
        return;
      }
      if (this._ignoreChange) {
        this._ignoreChange = false;
        return;
      }
      if (this._isInUndoState) {
        this._isInUndoState = false;
        this.fireEvent("undoStateChange", {
          canUndo: true,
          canRedo: false
        });
      }
      this.fireEvent("input");
    }
    /**
     * Leaves bookmark.
     */
    _recordUndoState(range, replace) {
      const isInUndoState = this._isInUndoState;
      if (!isInUndoState || replace) {
        let undoIndex = this._undoIndex + 1;
        const undoStack = this._undoStack;
        const undoConfig = this._config.undo;
        const undoThreshold = undoConfig.documentSizeThreshold;
        const undoLimit = undoConfig.undoLimit;
        if (undoIndex < this._undoStackLength) {
          undoStack.length = this._undoStackLength = undoIndex;
        }
        if (range) {
          this._saveRangeToBookmark(range);
        }
        if (isInUndoState) {
          return this;
        }
        const html = this._getRawHTML();
        if (replace) {
          --undoIndex;
        }
        if (undoThreshold > -1 && html.length * 2 > undoThreshold) {
          if (undoLimit > -1 && undoIndex > undoLimit) {
            undoStack.splice(0, undoIndex - undoLimit);
            undoIndex = undoLimit;
            this._undoStackLength = undoLimit;
          }
        }
        undoStack[undoIndex] = html;
        this._undoIndex = undoIndex;
        ++this._undoStackLength;
        this._isInUndoState = true;
      }
      return this;
    }
    saveUndoState(range) {
      range || (range = this.getSelection());
      this._recordUndoState(range, this._isInUndoState);
      this._getRangeAndRemoveBookmark(range);
      return this;
    }
    undo() {
      if (this._undoIndex !== 0 || !this._isInUndoState) {
        this._recordUndoState(this.getSelection(), false);
        --this._undoIndex;
        this._setRawHTML(this._undoStack[this._undoIndex]);
        const range = this._getRangeAndRemoveBookmark();
        if (range) {
          this.setSelection(range);
        }
        this._isInUndoState = true;
        this.fireEvent("undoStateChange", {
          canUndo: this._undoIndex !== 0,
          canRedo: true
        });
        this.fireEvent("input");
      }
      return this.focus();
    }
    redo() {
      const undoIndex = this._undoIndex;
      const undoStackLength = this._undoStackLength;
      if (undoIndex + 1 < undoStackLength && this._isInUndoState) {
        ++this._undoIndex;
        this._setRawHTML(this._undoStack[this._undoIndex]);
        const range = this._getRangeAndRemoveBookmark();
        if (range) {
          this.setSelection(range);
        }
        this.fireEvent("undoStateChange", {
          canUndo: true,
          canRedo: undoIndex + 2 < undoStackLength
        });
        this.fireEvent("input");
      }
      return this.focus();
    }
    // --- Get and set data
    getRoot() {
      return this._root;
    }
    _getRawHTML() {
      return this._root.innerHTML;
    }
    _setRawHTML(html) {
      if (html !== void 0) {
        const root = this._root;
        let node = root;
        root.innerHTML = html;
        do {
          fixCursor(node);
        } while (node = getNextBlock(node, root));
        this._ignoreChange = true;
      }
      return this;
    }
    getHTML(withBookmark) {
      let range;
      if (withBookmark) {
        range = this.getSelection();
        this._saveRangeToBookmark(range);
      }
      const html = this._getRawHTML().replace(/\u200B/g, "");
      if (withBookmark) {
        this._getRangeAndRemoveBookmark(range);
      }
      return html;
    }
    setHTML(html) {
      const frag = this._config.sanitizeToDOMFragment(html, this);
      const root = this._root;
      cleanTree(frag, this._config);
      cleanupBRs(frag);
      fixContainer(frag);
      let node = frag;
      let child = node.firstChild;
      if (!child || child.nodeName === "BR") {
        const block = this.createDefaultBlock();
        if (child) {
          node.replaceChild(block, child);
        } else {
          node.append(block);
        }
      } else {
        while (node = getNextBlock(node, root)) {
          fixCursor(node);
        }
      }
      this._ignoreChange = true;
      while (child = root.lastChild) {
        root.removeChild(child);
      }
      root.append(frag);
      this._undoIndex = -1;
      this._undoStack.length = 0;
      this._undoStackLength = 0;
      this._isInUndoState = false;
      const range = this._getRangeAndRemoveBookmark() || createRange(root.firstElementChild || root, 0);
      this.saveUndoState(range);
      this.setSelection(range);
      this._updatePath(range, true);
      return this;
    }
    /**
     * Insert HTML at the cursor location. If the selection is not collapsed
     * insertTreeFragmentIntoRange will delete the selection so that it is
     * replaced by the html being inserted.
     */
    insertHTML(html, isPaste) {
      const config = this._config;
      let frag = config.sanitizeToDOMFragment(html, this);
      const range = this.getSelection();
      this.saveUndoState(range);
      try {
        const root = this._root;
        if (config.addLinks) {
          this.addDetectedLinks(frag, frag);
        }
        cleanTree(frag, this._config);
        cleanupBRs(frag);
        removeEmptyInlines(frag);
        frag.normalize();
        let node = frag;
        while (node = getNextBlock(node, frag)) {
          fixCursor(node);
        }
        let doInsert = true;
        if (isPaste) {
          const event = new CustomEvent("willPaste", {
            cancelable: true,
            detail: {
              html,
              fragment: frag
            }
          });
          this.fireEvent("willPaste", event);
          frag = event.detail.fragment;
          doInsert = !event.defaultPrevented;
        }
        if (doInsert) {
          insertTreeFragmentIntoRange(range, frag, root);
          range.collapse(false);
          moveRangeBoundaryOutOf(range, "A", root);
          this._ensureBottomLine();
        }
        this.setSelection(range);
        this._updatePath(range, true);
        if (isPaste) {
          this.focus();
        }
      } catch (error) {
        this._config.didError(error);
      }
      return this;
    }
    insertElement(el, range) {
      if (!range) {
        range = this.getSelection();
      }
      range.collapse(true);
      if (isInline(el)) {
        insertNodeInRange(range, el);
        range.setStartAfter(el);
      } else {
        const root = this._root;
        const startNode = getStartBlockOfRange(
          range,
          root
        );
        let splitNode = startNode || root;
        let nodeAfterSplit = null;
        while (splitNode !== root && !splitNode.nextSibling) {
          splitNode = splitNode.parentNode;
        }
        if (splitNode !== root) {
          const parent = splitNode.parentNode;
          nodeAfterSplit = split(
            parent,
            splitNode.nextSibling,
            root,
            root
          );
        }
        if (startNode && isEmptyBlock(startNode)) {
          detach(startNode);
        }
        root.insertBefore(el, nodeAfterSplit);
        const blankLine = this.createDefaultBlock();
        root.insertBefore(blankLine, nodeAfterSplit);
        range.setStart(blankLine, 0);
        range.setEnd(blankLine, 0);
        moveRangeBoundariesDownTree(range);
      }
      this.focus();
      this.setSelection(range);
      this._updatePath(range);
      return this;
    }
    insertImage(src, attributes) {
      const img = createElement(
        "IMG",
        Object.assign(
          {
            src
          },
          attributes
        )
      );
      this.insertElement(img);
      return img;
    }
    insertPlainText(plainText, isPaste) {
      const range = this.getSelection();
      if (range.collapsed && getClosest(range.startContainer, this._root, "PRE")) {
        const startContainer = range.startContainer;
        let offset = range.startOffset;
        let textNode;
        if (!startContainer || !(startContainer instanceof Text)) {
          const text = document.createTextNode("");
          startContainer.insertBefore(
            text,
            startContainer.childNodes[offset]
          );
          textNode = text;
          offset = 0;
        } else {
          textNode = startContainer;
        }
        let doInsert = true;
        if (isPaste) {
          const event = new CustomEvent("willPaste", {
            cancelable: true,
            detail: {
              text: plainText
            }
          });
          this.fireEvent("willPaste", event);
          plainText = event.detail.text;
          doInsert = !event.defaultPrevented;
        }
        if (doInsert) {
          textNode.insertData(offset, plainText);
          range.setStart(textNode, offset + plainText.length);
          range.collapse(true);
        }
        this.setSelection(range);
        return this;
      }
      const lines = plainText.split("\n");
      const config = this._config;
      const tag = config.blockTag;
      const closeBlock = "</" + tag + ">";
      const openBlock = "<" + tag + ">";
      for (let i = 0, l = lines.length; i < l; ++i) {
        let line = lines[i];
        line = escapeHTML(line).replace(/ (?=(?: |$))/g, "&nbsp;");
        if (i) {
          line = openBlock + (line || "<BR>") + closeBlock;
        }
        lines[i] = line;
      }
      return this.insertHTML(lines.join(""), isPaste);
    }
    getSelectedText(range) {
      return getTextContentsOfRange(range || this.getSelection());
    }
    // --- Inline formatting
    /**
     * Extracts the font-family and font-size (if any) of the element
     * holding the cursor. If there's a selection, returns an empty object.
     */
    getFontInfo(range) {
      const fontInfo = {
        color: void 0,
        backgroundColor: void 0,
        fontFamily: void 0,
        fontSize: void 0
      };
      if (!range) {
        range = this.getSelection();
      }
      moveRangeBoundariesDownTree(range);
      let seenAttributes = 0;
      let element = range.commonAncestorContainer;
      if (range.collapsed || element instanceof Text) {
        if (element instanceof Text) {
          element = element.parentNode;
        }
        while (seenAttributes < 4 && element) {
          const style = element.style;
          if (style) {
            const color = style.color;
            if (!fontInfo.color && color) {
              fontInfo.color = color;
              ++seenAttributes;
            }
            const backgroundColor = style.backgroundColor;
            if (!fontInfo.backgroundColor && backgroundColor) {
              fontInfo.backgroundColor = backgroundColor;
              ++seenAttributes;
            }
            const fontFamily = style.fontFamily;
            if (!fontInfo.fontFamily && fontFamily) {
              fontInfo.fontFamily = fontFamily;
              ++seenAttributes;
            }
            const fontSize = style.fontSize;
            if (!fontInfo.fontSize && fontSize) {
              fontInfo.fontSize = fontSize;
              ++seenAttributes;
            }
          }
          element = element.parentNode;
        }
      }
      return fontInfo;
    }
    /**
     * Looks for matching tag and attributes, so won't work if <strong>
     * instead of <b> etc.
     */
    hasFormat(tag, attributes, range) {
      tag = tag.toUpperCase();
      attributes || (attributes = {});
      range || (range = this.getSelection());
      if (!range.collapsed && range.startContainer instanceof Text && range.startOffset === range.startContainer.length && range.startContainer.nextSibling) {
        range.setStartBefore(range.startContainer.nextSibling);
      }
      if (!range.collapsed && range.endContainer instanceof Text && range.endOffset === 0 && range.endContainer.previousSibling) {
        range.setEndAfter(range.endContainer.previousSibling);
      }
      const root = this._root;
      const common = range.commonAncestorContainer;
      if (getNearest(common, root, tag, attributes)) {
        return true;
      }
      if (common instanceof Text) {
        return false;
      }
      const walker = createTreeWalker(
        common,
        SHOW_TEXT,
        (node2) => isNodeContainedInRange(range, node2, true)
      );
      let seenNode = false;
      let node;
      while (node = walker.nextNode()) {
        if (!getNearest(node, root, tag, attributes)) {
          return false;
        }
        seenNode = true;
      }
      return seenNode;
    }
    changeFormat(add, remove, range, partial) {
      if (!range) {
        range = this.getSelection();
      }
      this.saveUndoState(range);
      if (remove) {
        range = this._removeFormat(
          remove.tag.toUpperCase(),
          remove.attributes || {},
          range,
          partial
        );
      }
      if (add) {
        range = this._addFormat(
          add.tag.toUpperCase(),
          add.attributes || {},
          range
        );
      }
      this.setSelection(range);
      this._updatePath(range, true);
      return this.focus();
    }
    _addFormat(tag, attributes, range) {
      const root = this._root;
      if (range.collapsed) {
        const el = fixCursor(createElement(tag, attributes));
        insertNodeInRange(range, el);
        const focusNode = el.firstChild || el;
        const focusOffset = focusNode instanceof Text ? focusNode.length : 0;
        range.setStart(focusNode, focusOffset);
        range.collapse(true);
        let block = el;
        while (isInline(block)) {
          block = block.parentNode;
        }
        removeZWS(block, el);
      } else {
        const walker = createTreeWalker(
          range.commonAncestorContainer,
          SHOW_ELEMENT_OR_TEXT,
          (node) => {
            return (node instanceof Text || node.nodeName === "BR" || node.nodeName === "IMG") && isNodeContainedInRange(range, node, true);
          }
        );
        let { startContainer, startOffset, endContainer, endOffset } = range;
        walker.currentNode = startContainer;
        if (!(startContainer instanceof Element) && !(startContainer instanceof Text) || FILTER_ACCEPT !== walker.filter.acceptNode(startContainer)) {
          const next = walker.nextNode();
          if (!next) {
            return range;
          }
          startContainer = next;
          startOffset = 0;
        }
        do {
          let node = walker.currentNode;
          const needsFormat = !getNearest(node, root, tag, attributes);
          if (needsFormat) {
            if (node === endContainer && node.length > endOffset) {
              node.splitText(endOffset);
            }
            if (node === startContainer && startOffset) {
              node = node.splitText(startOffset);
              if (endContainer === startContainer) {
                endContainer = node;
                endOffset -= startOffset;
              } else if (endContainer === startContainer.parentNode) {
                ++endOffset;
              }
              startContainer = node;
              startOffset = 0;
            }
            const el = createElement(tag, attributes);
            replaceWith(node, el);
            el.append(node);
          }
        } while (walker.nextNode());
        range = createRange(
          startContainer,
          startOffset,
          endContainer,
          endOffset
        );
      }
      return range;
    }
    _removeFormat(tag, attributes, range, partial) {
      this._saveRangeToBookmark(range);
      let fixer;
      if (range.collapsed) {
        if (cantFocusEmptyTextNodes) {
          fixer = document.createTextNode(ZWS);
        } else {
          fixer = document.createTextNode("");
        }
        insertNodeInRange(range, fixer);
      }
      let root = range.commonAncestorContainer;
      while (isInline(root)) {
        root = root.parentNode;
      }
      const startContainer = range.startContainer;
      const startOffset = range.startOffset;
      const endContainer = range.endContainer;
      const endOffset = range.endOffset;
      const toWrap = [];
      const examineNode = (node, exemplar) => {
        if (isNodeContainedInRange(range, node, false)) {
          return;
        }
        let child;
        let next;
        if (!isNodeContainedInRange(range, node, true)) {
          if (!(node instanceof HTMLInputElement) && (!(node instanceof Text) || node.data)) {
            toWrap.push([exemplar, node]);
          }
          return;
        }
        if (node instanceof Text) {
          if (node === endContainer && endOffset !== node.length) {
            toWrap.push([exemplar, node.splitText(endOffset)]);
          }
          if (node === startContainer && startOffset) {
            node.splitText(startOffset);
            toWrap.push([exemplar, node]);
          }
        } else {
          for (child = node.firstChild; child; child = next) {
            next = child.nextSibling;
            examineNode(child, exemplar);
          }
        }
      };
      const formatTags = Array.from(
        root.getElementsByTagName(tag)
      ).filter((el) => {
        return isNodeContainedInRange(range, el, true) && hasTagAttributes(el, tag, attributes);
      });
      partial || formatTags.forEach((node) => examineNode(node, node));
      toWrap.forEach(([el, node]) => {
        el = el.cloneNode(false);
        replaceWith(node, el);
        el.append(node);
      });
      formatTags.forEach((el) => replaceWith(el, empty(el)));
      if (cantFocusEmptyTextNodes && fixer) {
        fixer = fixer.parentNode;
        let block = fixer;
        while (block && isInline(block)) {
          block = block.parentNode;
        }
        block && removeZWS(block, fixer);
      }
      this._getRangeAndRemoveBookmark(range);
      fixer && range.collapse(false);
      mergeInlines(root, range);
      return range;
    }
    // ---
    bold() {
      this.toggleTag("B");
    }
    italic() {
      this.toggleTag("I");
    }
    underline() {
      this.toggleTag("U");
    }
    strikethrough() {
      this.toggleTag("S");
    }
    subscript() {
      this.toggleTag("SUB", "SUP");
    }
    superscript() {
      this.toggleTag("SUP", "SUB");
    }
    // ---
    makeLink(url, attributes) {
      const range = this.getSelection();
      if (range.collapsed) {
        let protocolEnd = url.indexOf(":") + 1;
        if (protocolEnd) {
          while (url[protocolEnd] === "/") {
            ++protocolEnd;
          }
        }
        insertNodeInRange(
          range,
          document.createTextNode(url.slice(protocolEnd))
        );
      }
      attributes = Object.assign(
        {
          href: url
        },
        attributes
      );
      return this.changeFormat(
        {
          tag: "A",
          attributes
        },
        {
          tag: "A"
        },
        range
      );
    }
    removeLink() {
      return this.changeFormat(
        null,
        {
          tag: "A"
        },
        this.getSelection(),
        true
      );
    }
    addDetectedLinks(searchInNode, root) {
      const walker = createTreeWalker(
        searchInNode,
        SHOW_TEXT,
        (node2) => !getClosest(node2, root || this._root, "A")
      );
      const linkRegExp = this.linkRegExp;
      let node;
      while (node = walker.nextNode()) {
        const parent = node.parentNode;
        let data = node.data;
        let match;
        while (match = linkRegExp.exec(data)) {
          const index = match.index;
          const endIndex = index + match[0].length;
          if (index) {
            parent.insertBefore(
              document.createTextNode(data.slice(0, index)),
              node
            );
          }
          const child = createElement(
            "A",
            {
              href: match[1] ? /^(?:ht|f)tps?:/i.test(match[1]) ? match[1] : "http://" + match[1] : "mailto:" + match[0]
            }
          );
          child.textContent = data.slice(index, endIndex);
          parent.insertBefore(child, node);
          node.data = data = data.slice(endIndex);
        }
      }
      return this;
    }
    // --- Block formatting
    _ensureBottomLine() {
      const root = this._root;
      const last = root.lastElementChild;
      if (!last || last.nodeName !== this._config.blockTag || !isBlock(last)) {
        root.append(this.createDefaultBlock());
      }
    }
    createDefaultBlock(children) {
      const config = this._config;
      return fixCursor(
        createElement(config.blockTag, null, children)
      );
    }
    splitBlock(lineBreakOnly, range) {
      if (!range) {
        range = this.getSelection();
      }
      const root = this._root;
      let block;
      let parent;
      let node;
      let nodeAfterSplit;
      this._recordUndoState(range);
      this._removeZWS();
      this._getRangeAndRemoveBookmark(range);
      if (!range.collapsed) {
        deleteContentsOfRange(range, root);
      }
      if (this._config.addLinks) {
        moveRangeBoundariesDownTree(range);
        const textNode = range.startContainer;
        const offset2 = range.startOffset;
        setTimeout(() => {
          linkifyText(this, textNode, offset2);
        }, 0);
      }
      block = getStartBlockOfRange(range, root);
      if (block && (parent = getClosest(block, root, "PRE"))) {
        moveRangeBoundariesDownTree(range);
        node = range.startContainer;
        const offset2 = range.startOffset;
        if (!(node instanceof Text)) {
          node = document.createTextNode("");
          parent.insertBefore(node, parent.firstChild);
        }
        if (!lineBreakOnly && node instanceof Text && (node.data.charAt(offset2 - 1) === "\n" || rangeDoesStartAtBlockBoundary(range, root)) && (node.data.charAt(offset2) === "\n" || rangeDoesEndAtBlockBoundary(range, root))) {
          node.deleteData(offset2 && offset2 - 1, offset2 ? 2 : 1);
          nodeAfterSplit = split(
            node,
            offset2 && offset2 - 1,
            root,
            root
          );
          node = nodeAfterSplit.previousSibling;
          if (!node.textContent) {
            detach(node);
          }
          node = this.createDefaultBlock();
          nodeAfterSplit.parentNode.insertBefore(node, nodeAfterSplit);
          if (!nodeAfterSplit.textContent) {
            detach(nodeAfterSplit);
          }
          range.setStart(node, 0);
        } else {
          node.insertData(offset2, "\n");
          fixCursor(parent);
          if (node.length === offset2 + 1) {
            range.setStartAfter(node);
          } else {
            range.setStart(node, offset2 + 1);
          }
        }
        range.collapse(true);
        this.setSelection(range);
        this._updatePath(range, true);
        this._docWasChanged();
        return this;
      }
      if (!block || lineBreakOnly || /^T[HD]$/.test(block.nodeName)) {
        moveRangeBoundaryOutOf(range, "A", root);
        insertNodeInRange(range, createElement("BR"));
        range.collapse(false);
        this.setSelection(range);
        this._updatePath(range, true);
        return this;
      }
      if (parent = getClosest(block, root, "LI")) {
        block = parent;
      }
      if (isEmptyBlock(block)) {
        if (getClosest(block, root, "UL") || getClosest(block, root, "OL")) {
          this.decreaseListLevel(range);
          return this;
        } else if (getClosest(block, root, "BLOCKQUOTE")) {
          this.replaceWithBlankLine(range);
          return this;
        }
      }
      node = range.startContainer;
      const offset = range.startOffset;
      let splitTag = this.tagAfterSplit[block.nodeName] || this._config.blockTag;
      nodeAfterSplit = split(
        node,
        offset,
        block.parentNode,
        this._root
      );
      if (!hasTagAttributes(nodeAfterSplit, splitTag)) {
        block = createElement(splitTag);
        if (nodeAfterSplit.dir) {
          block.dir = nodeAfterSplit.dir;
        }
        replaceWith(nodeAfterSplit, block);
        block.append(empty(nodeAfterSplit));
        nodeAfterSplit = block;
      }
      removeZWS(block);
      removeEmptyInlines(block);
      fixCursor(block);
      while (nodeAfterSplit instanceof Element) {
        let child = nodeAfterSplit.firstChild;
        let next;
        if (nodeAfterSplit.nodeName === "A" && (!nodeAfterSplit.textContent || nodeAfterSplit.textContent === ZWS)) {
          child = document.createTextNode("");
          replaceWith(nodeAfterSplit, child);
          nodeAfterSplit = child;
          break;
        }
        while (child && child instanceof Text && !child.length) {
          next = child.nextSibling;
          if (!next || next.nodeName === "BR") {
            break;
          }
          detach(child);
          child = next;
        }
        if (!child || child.nodeName === "BR" || child instanceof Text) {
          break;
        }
        nodeAfterSplit = child;
      }
      range = createRange(nodeAfterSplit, 0);
      this.setSelection(range);
      this._updatePath(range, true);
      return this;
    }
    forEachBlock(fn, mutates, range) {
      if (!range) {
        range = this.getSelection();
      }
      if (mutates) {
        this.saveUndoState(range);
      }
      const root = this._root;
      let start = getStartBlockOfRange(range, root);
      const end = getEndBlockOfRange(range, root);
      if (start && end) {
        do {
          if (fn(start) || start === end) {
            break;
          }
        } while (start = getNextBlock(start, root));
      }
      if (mutates) {
        this.setSelection(range);
        this._updatePath(range, true);
      }
      return this;
    }
    modifyBlocks(modify, range) {
      if (!range) {
        range = this.getSelection();
      }
      this._recordUndoState(range, this._isInUndoState);
      const root = this._root;
      expandRangeToBlockBoundaries(range, root);
      moveRangeBoundariesUpTree(range, root, root, root);
      const frag = extractContentsOfRange(range, root, root);
      if (!range.collapsed) {
        let node = range.endContainer;
        if (node === root) {
          range.collapse(false);
        } else {
          while (node.parentNode !== root) {
            node = node.parentNode;
          }
          range.setStartBefore(node);
          range.collapse(true);
        }
      }
      insertNodeInRange(range, modify.call(this, frag));
      if (range.endOffset < range.endContainer.childNodes.length) {
        mergeContainers(
          range.endContainer.childNodes[range.endOffset],
          root
        );
      }
      mergeContainers(
        range.startContainer.childNodes[range.startOffset],
        root
      );
      this._getRangeAndRemoveBookmark(range);
      this.setSelection(range);
      this._updatePath(range, true);
      return this;
    }
    // ---
    setTextAlignment(alignment) {
      this.forEachBlock((block) => {
        const className = block.className.split(/\s+/).filter((klass) => {
          return !!klass && !/^align/.test(klass);
        }).join(" ");
        if (alignment) {
          block.className = className + " align-" + alignment;
          block.style.textAlign = alignment;
        } else {
          block.className = className;
          block.style.textAlign = "";
        }
      }, true);
      return this.focus();
    }
    setTextDirection(direction) {
      this.forEachBlock((block) => {
        if (direction) {
          block.dir = direction;
        } else {
          block.removeAttribute("dir");
        }
      }, true);
      return this.focus();
    }
    // ---
    _getListSelection(range, root) {
      let list = range.commonAncestorContainer;
      let startLi = range.startContainer;
      let endLi = range.endContainer;
      while (list && list !== root && !/^[OU]L$/.test(list.nodeName)) {
        list = list.parentNode;
      }
      if (!list || list === root) {
        return null;
      }
      if (startLi === list) {
        startLi = startLi.childNodes[range.startOffset];
      }
      if (endLi === list) {
        endLi = endLi.childNodes[range.endOffset];
      }
      while (startLi && startLi.parentNode !== list) {
        startLi = startLi.parentNode;
      }
      while (endLi && endLi.parentNode !== list) {
        endLi = endLi.parentNode;
      }
      return [list, startLi, endLi];
    }
    increaseListLevel(range) {
      if (!range) {
        range = this.getSelection();
      }
      const root = this._root;
      const listSelection = this._getListSelection(range, root);
      if (!listSelection) {
        return this.focus();
      }
      let [list, startLi, endLi] = listSelection;
      if (!startLi || startLi === list.firstChild) {
        return this.focus();
      }
      this._recordUndoState(range, this._isInUndoState);
      const type = list.nodeName;
      let newParent = startLi.previousSibling;
      let next;
      if (newParent.nodeName !== type) {
        newParent = createElement(type);
        list.insertBefore(newParent, startLi);
      }
      do {
        next = startLi === endLi ? null : startLi.nextSibling;
        newParent.append(startLi);
      } while (startLi = next);
      next = newParent.nextSibling;
      if (next) {
        mergeContainers(next, root);
      }
      this._getRangeAndRemoveBookmark(range);
      this.setSelection(range);
      this._updatePath(range, true);
      return this.focus();
    }
    decreaseListLevel(range) {
      if (!range) {
        range = this.getSelection();
      }
      const root = this._root;
      const listSelection = this._getListSelection(range, root);
      if (!listSelection) {
        return this.focus();
      }
      let [list, startLi, endLi] = listSelection;
      if (!startLi) {
        startLi = list.firstChild;
      }
      if (!endLi) {
        endLi = list.lastChild;
      }
      this._recordUndoState(range, this._isInUndoState);
      let next;
      let insertBefore = null;
      if (startLi) {
        let newParent = list.parentNode;
        insertBefore = !endLi.nextSibling ? list.nextSibling : split(list, endLi.nextSibling, newParent, root);
        if (newParent !== root && newParent.nodeName === "LI") {
          newParent = newParent.parentNode;
          while (insertBefore) {
            next = insertBefore.nextSibling;
            endLi.append(insertBefore);
            insertBefore = next;
          }
          insertBefore = list.parentNode.nextSibling;
        }
        const makeNotList = !/^[OU]L$/.test(newParent.nodeName);
        do {
          next = startLi === endLi ? null : startLi.nextSibling;
          list.removeChild(startLi);
          if (makeNotList && startLi.nodeName === "LI") {
            startLi = this.createDefaultBlock([empty(startLi)]);
          }
          newParent.insertBefore(startLi, insertBefore);
        } while (startLi = next);
      }
      if (!list.firstChild) {
        detach(list);
      }
      if (insertBefore) {
        mergeContainers(insertBefore, root);
      }
      this._getRangeAndRemoveBookmark(range);
      this.setSelection(range);
      this._updatePath(range, true);
      return this.focus();
    }
    _makeList(frag, type) {
      const walker = getBlockWalker(frag, this._root);
      let node;
      while (node = walker.nextNode()) {
        if (node.parentNode instanceof HTMLLIElement) {
          node = node.parentNode;
          walker.currentNode = node.lastChild;
        }
        if (!(node instanceof HTMLLIElement)) {
          const newLi = createElement("LI");
          if (node.dir) {
            newLi.dir = node.dir;
          }
          const prev = node.previousSibling;
          if (prev && prev.nodeName === type) {
            prev.append(newLi);
            detach(node);
          } else {
            replaceWith(node, createElement(type, null, [newLi]));
          }
          newLi.append(empty(node));
          walker.currentNode = newLi;
        } else {
          node = node.parentNode;
          const tag = node.nodeName;
          if (tag !== type && /^[OU]L$/.test(tag)) {
            replaceWith(
              node,
              createElement(type, null, [empty(node)])
            );
          }
        }
      }
      return frag;
    }
    makeUnorderedList() {
      this.modifyBlocks((frag) => this._makeList(frag, "UL"));
      return this.focus();
    }
    makeOrderedList() {
      this.modifyBlocks((frag) => this._makeList(frag, "OL"));
      return this.focus();
    }
    removeList() {
      this.modifyBlocks((frag) => {
        const lists = frag.querySelectorAll("UL, OL");
        const items = frag.querySelectorAll("LI");
        const root = this._root;
        for (let i = 0, l = lists.length; i < l; ++i) {
          const list = lists[i];
          const listFrag = empty(list);
          fixContainer(listFrag);
          replaceWith(list, listFrag);
        }
        for (let i = 0, l = items.length; i < l; ++i) {
          const item = items[i];
          if (isBlock(item)) {
            replaceWith(item, this.createDefaultBlock([empty(item)]));
          } else {
            fixContainer(item);
            replaceWith(item, empty(item));
          }
        }
        return frag;
      });
      return this.focus();
    }
    // ---
    increaseQuoteLevel(range) {
      this.modifyBlocks(
        (frag) => createElement(
          "BLOCKQUOTE",
          null,
          [frag]
        ),
        range
      );
      return this.focus();
    }
    decreaseQuoteLevel(range) {
      this.modifyBlocks((frag) => {
        Array.from(frag.querySelectorAll("blockquote")).filter((el) => {
          return !getClosest(el.parentNode, frag, "BLOCKQUOTE");
        }).forEach((el) => {
          replaceWith(el, empty(el));
        });
        return frag;
      }, range);
      return this.focus();
    }
    removeQuote(range) {
      this.modifyBlocks((frag) => {
        Array.from(frag.querySelectorAll("blockquote")).forEach(
          (el) => {
            replaceWith(el, empty(el));
          }
        );
        return frag;
      }, range);
      return this.focus();
    }
    replaceWithBlankLine(range) {
      this.modifyBlocks(
        () => this.createDefaultBlock([
          createElement("INPUT", {
            id: this.startSelectionId,
            type: "hidden"
          }),
          createElement("INPUT", {
            id: this.endSelectionId,
            type: "hidden"
          })
        ]),
        range
      );
      return this.focus();
    }
    // ---
    code() {
      const range = this.getSelection();
      if (range.collapsed || isContainer(range.commonAncestorContainer)) {
        this.modifyBlocks((frag) => {
          const root = this._root;
          const output = document.createDocumentFragment();
          const blockWalker = getBlockWalker(frag, root);
          let node;
          while (node = blockWalker.nextNode()) {
            let nodes = node.querySelectorAll("BR");
            const brBreaksLine = [];
            let l = nodes.length;
            for (let i = 0; i < l; ++i) {
              brBreaksLine[i] = isLineBreak(nodes[i]);
            }
            while (l--) {
              const br = nodes[l];
              if (!brBreaksLine[l]) {
                detach(br);
              } else {
                replaceWith(br, document.createTextNode("\n"));
              }
            }
            nodes = node.querySelectorAll("CODE");
            l = nodes.length;
            while (l--) {
              replaceWith(nodes[l], empty(nodes[l]));
            }
            if (output.childNodes.length) {
              output.append(document.createTextNode("\n"));
            }
            output.append(empty(node));
          }
          const textWalker = createTreeWalker(output, SHOW_TEXT);
          while (node = textWalker.nextNode()) {
            node.data = node.data.replace(/ /g, " ");
          }
          output.normalize();
          return fixCursor(
            createElement("PRE", null, [
              output
            ])
          );
        }, range);
        this.focus();
      } else {
        this.changeFormat(
          {
            tag: "CODE",
            attributes: null
          },
          null,
          range
        );
      }
      return this;
    }
    removeCode() {
      const range = this.getSelection();
      const ancestor = range.commonAncestorContainer;
      const inPre = getClosest(ancestor, this._root, "PRE");
      if (inPre) {
        this.modifyBlocks((frag) => {
          const root = this._root;
          const pres = frag.querySelectorAll("PRE");
          let l = pres.length;
          while (l--) {
            const pre = pres[l];
            const walker = createTreeWalker(pre, SHOW_TEXT);
            let node;
            while (node = walker.nextNode()) {
              let value = node.data;
              value = value.replace(/ (?= )/g, "\xA0");
              const contents = document.createDocumentFragment();
              let index;
              while ((index = value.indexOf("\n")) > -1) {
                contents.append(
                  document.createTextNode(value.slice(0, index))
                );
                contents.append(createElement("BR"));
                value = value.slice(index + 1);
              }
              node.parentNode.insertBefore(contents, node);
              node.data = value;
            }
            fixContainer(pre);
            replaceWith(pre, empty(pre));
          }
          return frag;
        }, range);
        this.focus();
      } else {
        this.changeFormat(null, { tag: "CODE" }, range);
      }
      return this;
    }
    toggleCode() {
      if (this.hasFormat("PRE") || this.hasFormat("CODE")) {
        this.removeCode();
      } else {
        this.code();
      }
      return this;
    }
    /**
     * SnappyMail
     */
    changeIndentationLevel(direction) {
      let parent = this.getSelectionClosest("UL,OL,BLOCKQUOTE");
      if (parent || "increase" === direction) {
        direction += !parent || "BLOCKQUOTE" === parent.nodeName ? "Quote" : "List";
        return this[direction + "Level"]();
      }
    }
    getSelectionClosest(selector) {
      return getClosest(this.getSelection().commonAncestorContainer, this._root, selector);
    }
    setAttribute(name, value) {
      let range = this.getSelection();
      let start = range?.startContainer || {};
      let end = range?.endContainer || {};
      if ("dir" == name || start instanceof Text && 0 === range.startOffset && start === end && end.length === range.endOffset) {
        this._recordUndoState(range);
        setAttributes(start.parentNode, { [name]: value });
        this._docWasChanged();
      } else if (null == value) {
        this._recordUndoState(range);
        let node = getClosest(range.commonAncestorContainer, this._root, "*");
        range.collapsed ? setAttributes(node, { [name]: value }) : node.querySelectorAll("*").forEach((el) => setAttributes(el, { [name]: value }));
        this._docWasChanged();
      } else {
        this.changeFormat({
          tag: "SPAN",
          attributes: { [name]: value }
        }, null, range);
      }
      return this.focus();
    }
    setStyle(style) {
      this.setAttribute("style", style);
    }
    toggleTag(name, remove) {
      let range = this.getSelection();
      if (this.hasFormat(name, null, range)) {
        this.changeFormat(null, { tag: name }, range);
      } else {
        this.changeFormat({ tag: name }, remove ? { tag: remove } : null, range);
      }
    }
    setRange(range) {
      this.setSelection(range);
      this._updatePath(range, true);
    }
    setConfig(config) {
      this._config = mergeObjects({
        addLinks: true
      }, config, true);
      return this;
    }
  };

  // source/Legacy.ts
  window.Squire = Squire;
})();

/**
 * Modified version of https://github.com/mathiasbynens/punycode.js
 */

(() => {

'use strict';

const
	/** Highest positive signed 32-bit float value */
	maxInt = 2147483647, // aka. 0x7FFFFFFF or 2^31-1

	/** Bootstring parameters */
	base = 36,
	tMin = 1,
	tMax = 26,
	skew = 38,
	damp = 700,
	initialBias = 72,
	initialN = 128, // 0x80
	delimiter = '-', // '\x2D'

	/** Regular expressions */
	regexPunycode = /^xn--/,
	regexNonASCII = /[^\0-\x7F]/, // Note: U+007F DEL is excluded too.
	regexSeparators = /[\x2E\u3002\uFF0E\uFF61]/g, // RFC 3490 separators

	/** Error messages */
	errors = {
		'overflow': 'Overflow: input needs wider integers to process',
		'not-basic': 'Illegal input >= 0x80 (not a basic code point)',
		'invalid-input': 'Invalid input'
	},

	/** Convenience shortcuts */
	baseMinusTMin = base - tMin,
	floor = Math.floor,
	stringFromCharCode = String.fromCharCode,

	/*--------------------------------------------------------------------------*/

	/**
	 * A generic error utility function.
	 * @private
	 * @param {String} type The error type.
	 * @returns {Error} Throws a `RangeError` with the applicable error message.
	 */
	error = type => {
		throw new RangeError(errors[type])
	},

	/**
	 * A simple `Array#map`-like wrapper to work with domain name strings or email
	 * addresses.
	 * @private
	 * @param {String} domain The domain name or email address.
	 * @param {Function} callback The function that gets called for every
	 * character.
	 * @returns {String} A new string of characters returned by the callback
	 * function.
	 */
	mapDomain = (domain, callback) => {
		// In email addresses, only the domain name should be punycoded.
		// Leave the local part (i.e. everything up to `@`) intact.
		const parts = (domain || '').split('@');
		parts.push(
			parts.pop()
			.split(regexSeparators)
			.map(label => callback(label))
			.join('.')
		);
		return parts.join('@');
	},

	/**
	 * Creates an array containing the numeric code points of each Unicode
	 * character in the string. While JavaScript uses UCS-2 internally,
	 * this function will convert a pair of surrogate halves (each of which
	 * UCS-2 exposes as separate characters) into a single code point,
	 * matching UTF-16.
	 * @see <https://mathiasbynens.be/notes/javascript-encoding>
	 * @name decode
	 * @param {String} string The Unicode input string (UCS-2).
	 * @returns {Array} The new array of code points.
	 */
	ucs2decode = string => {
		const output = [];
		let counter = 0;
		const length = string.length;
		while (counter < length) {
			const value = string.charCodeAt(counter++);
			if (value >= 0xD800 && value <= 0xDBFF && counter < length) {
				// It's a high surrogate, and there is a next character.
				const extra = string.charCodeAt(counter++);
				if ((extra & 0xFC00) == 0xDC00) { // Low surrogate.
					output.push(((value & 0x3FF) << 10) + (extra & 0x3FF) + 0x10000);
				} else {
					// It's an unmatched surrogate; only append this code unit, in case the
					// next code unit is the high surrogate of a surrogate pair.
					output.push(value);
					counter--;
				}
			} else {
				output.push(value);
			}
		}
		return output;
	},

	/**
	 * Converts a basic code point into a digit/integer.
	 * @see `digitToBasic()`
	 * @private
	 * @param {Number} codePoint The basic numeric code point value.
	 * @returns {Number} The numeric value of a basic code point (for use in
	 * representing integers) in the range `0` to `base - 1`, or `base` if
	 * the code point does not represent a value.
	 */
	basicToDigit = codePoint => {
		if (codePoint >= 0x30 && codePoint < 0x3A) {
			return 26 + (codePoint - 0x30);
		}
		if (codePoint >= 0x41 && codePoint < 0x5B) {
			return codePoint - 0x41;
		}
		if (codePoint >= 0x61 && codePoint < 0x7B) {
			return codePoint - 0x61;
		}
		return base;
	},

	/**
	 * Converts a digit/integer into a basic code point.
	 * @see `basicToDigit()`
	 * @private
	 * @param {Number} digit The numeric value of a basic code point.
	 * @returns {Number} The basic code point whose value (when used for
	 * representing integers) is `digit`, which needs to be in the range
	 * `0` to `base - 1`. If `flag` is non-zero, the uppercase form is
	 * used; else, the lowercase form is used. The behavior is undefined
	 * if `flag` is non-zero and `digit` has no uppercase form.
	 */
	digitToBasic = (digit, flag) =>
		//  0..25 map to ASCII a..z or A..Z
		// 26..35 map to ASCII 0..9
		digit + 22 + 75 * (digit < 26) - ((flag != 0) << 5),

	/**
	 * Bias adaptation function as per section 3.4 of RFC 3492.
	 * https://tools.ietf.org/html/rfc3492#section-3.4
	 * @private
	 */
	adapt = (delta, numPoints, firstTime) => {
		let k = 0;
		delta = firstTime ? floor(delta / damp) : delta >> 1;
		delta += floor(delta / numPoints);
		for (/* no initialization */; delta > baseMinusTMin * tMax >> 1; k += base) {
			delta = floor(delta / baseMinusTMin);
		}
		return floor(k + (baseMinusTMin + 1) * delta / (delta + skew));
	},

	/**
	 * Converts a Punycode string of ASCII-only symbols to a string of Unicode
	 * symbols.
	 * @memberOf punycode
	 * @param {String} input The Punycode string of ASCII-only symbols.
	 * @returns {String} The resulting string of Unicode symbols.
	 */
	decode = input => {
		// Don't use UCS-2.
		const output = [];
		const inputLength = input.length;
		let i = 0;
		let n = initialN;
		let bias = initialBias;

		// Handle the basic code points: let `basic` be the number of input code
		// points before the last delimiter, or `0` if there is none, then copy
		// the first basic code points to the output.

		let basic = input.lastIndexOf(delimiter);
		if (basic < 0) {
			basic = 0;
		}

		for (let j = 0; j < basic; ++j) {
			// if it's not a basic code point
			if (input.charCodeAt(j) >= 0x80) {
				error('not-basic');
			}
			output.push(input.charCodeAt(j));
		}

		// Main decoding loop: start just after the last delimiter if any basic code
		// points were copied; start at the beginning otherwise.

		for (let index = basic > 0 ? basic + 1 : 0; index < inputLength; /* no final expression */) {

			// `index` is the index of the next character to be consumed.
			// Decode a generalized variable-length integer into `delta`,
			// which gets added to `i`. The overflow checking is easier
			// if we increase `i` as we go, then subtract off its starting
			// value at the end to obtain `delta`.
			const oldi = i;
			for (let w = 1, k = base; /* no condition */; k += base) {

				if (index >= inputLength) {
					error('invalid-input');
				}

				const digit = basicToDigit(input.charCodeAt(index++));

				if (digit >= base) {
					error('invalid-input');
				}
				if (digit > floor((maxInt - i) / w)) {
					error('overflow');
				}

				i += digit * w;
				const t = k <= bias ? tMin : (k >= bias + tMax ? tMax : k - bias);

				if (digit < t) {
					break;
				}

				const baseMinusT = base - t;
				if (w > floor(maxInt / baseMinusT)) {
					error('overflow');
				}

				w *= baseMinusT;

			}

			const out = output.length + 1;
			bias = adapt(i - oldi, out, oldi == 0);

			// `i` was supposed to wrap around from `out` to `0`,
			// incrementing `n` each time, so we'll fix that now:
			if (floor(i / out) > maxInt - n) {
				error('overflow');
			}

			n += floor(i / out);
			i %= out;

			// Insert `n` at position `i` of the output.
			output.splice(i++, 0, n);

		}

		return String.fromCodePoint(...output);
	},

	/**
	 * Converts a string of Unicode symbols (e.g. a domain name label) to a
	 * Punycode string of ASCII-only symbols.
	 * @memberOf punycode
	 * @param {String} input The string of Unicode symbols.
	 * @returns {String} The resulting Punycode string of ASCII-only symbols.
	 */
	encode = input => {
		const output = [];

		// Convert the input in UCS-2 to an array of Unicode code points.
		input = ucs2decode(input);

		// Cache the length.
		const inputLength = input.length;

		// Initialize the state.
		let n = initialN;
		let delta = 0;
		let bias = initialBias;

		// Handle the basic code points.
		for (const currentValue of input) {
			if (currentValue < 0x80) {
				output.push(stringFromCharCode(currentValue));
			}
		}

		const basicLength = output.length;
		let handledCPCount = basicLength;

		// `handledCPCount` is the number of code points that have been handled;
		// `basicLength` is the number of basic code points.

		// Finish the basic string with a delimiter unless it's empty.
		if (basicLength) {
			output.push(delimiter);
		}

		// Main encoding loop:
		while (handledCPCount < inputLength) {

			// All non-basic code points < n have been handled already. Find the next
			// larger one:
			let m = maxInt;
			for (const currentValue of input) {
				if (currentValue >= n && currentValue < m) {
					m = currentValue;
				}
			}

			// Increase `delta` enough to advance the decoder's <n,i> state to <m,0>,
			// but guard against overflow.
			const handledCPCountPlusOne = handledCPCount + 1;
			if (m - n > floor((maxInt - delta) / handledCPCountPlusOne)) {
				error('overflow');
			}

			delta += (m - n) * handledCPCountPlusOne;
			n = m;

			for (const currentValue of input) {
				if (currentValue < n && ++delta > maxInt) {
					error('overflow');
				}
				if (currentValue === n) {
					// Represent delta as a generalized variable-length integer.
					let q = delta;
					for (let k = base; /* no condition */; k += base) {
						const t = k <= bias ? tMin : (k >= bias + tMax ? tMax : k - bias);
						if (q < t) {
							break;
						}
						const qMinusT = q - t;
						const baseMinusT = base - t;
						output.push(
							stringFromCharCode(digitToBasic(t + qMinusT % baseMinusT, 0))
						);
						q = floor(qMinusT / baseMinusT);
					}

					output.push(stringFromCharCode(digitToBasic(q, 0)));
					bias = adapt(delta, handledCPCountPlusOne, handledCPCount === basicLength);
					delta = 0;
					++handledCPCount;
				}
			}

			++delta;
			++n;

		}
		return output.join('');
	};

	/*--------------------------------------------------------------------------*/

	/** Define the public API */
	window.IDN = {
		/**
		 * A string representing the current Punycode.js version number.
		 * @memberOf punycode
		 * @type String
		 */
		version: '2.3.1',

		/**
		 * Converts a Punycode string representing a domain name or an email address
		 * to Unicode. Only the Punycoded parts of the input will be converted, i.e.
		 * it doesn't matter if you call it on a string that has already been
		 * converted to Unicode.
		 * @memberOf punycode
		 * @param {String} input The Punycoded domain name or email address to
		 * convert to Unicode.
		 * @returns {String} The Unicode representation of the given Punycode
		 * string.
		 */
		toUnicode: input => mapDomain(
			input,
			string => regexPunycode.test(string) ? decode(string.slice(4).toLowerCase()) : string
		),

		/**
		 * Converts a Unicode string representing a domain name or an email address to
		 * Punycode. Only the non-ASCII parts of the domain name will be converted,
		 * i.e. it doesn't matter if you call it with a domain that's already in
		 * ASCII.
		 * @memberOf punycode
		 * @param {String} input The domain name or email address to convert, as a
		 * Unicode string.
		 * @returns {String} The Punycode representation of the given domain name or
		 * email address.
		 */
		toASCII: input => mapDomain(
			input,
			string => (regexNonASCII.test(string) ? 'xn--' + encode(string) : string).toLowerCase()
		)
	};
})();

/**
 * https://github.com/mixmark-io/turndown
 * v7.2.0 modified by SnappyMail to be ES2020
 */

const TurndownService = (() => {

  const repeat = (character, count) => Array(count + 1).join(character),

  trimLeadingNewlines = string => string.replace(/^\n*/, ''),

  trimTrailingNewlines = string => {
    // avoid match-at-end regexp bottleneck, see #370
    var indexEnd = string.length;
    while (indexEnd > 0 && string[indexEnd - 1] === '\n') indexEnd--;
    return string.substring(0, indexEnd)
  },

  blockElements = [
    'ADDRESS', 'ARTICLE', 'ASIDE', 'AUDIO', 'BLOCKQUOTE', 'BODY', 'CANVAS',
    'CENTER', 'DD', 'DIR', 'DIV', 'DL', 'DT', 'FIELDSET', 'FIGCAPTION', 'FIGURE',
    'FOOTER', 'FORM', 'FRAMESET', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'HEADER',
    'HGROUP', 'HR', 'HTML', 'ISINDEX', 'LI', 'MAIN', 'MENU', 'NAV', 'NOFRAMES',
    'NOSCRIPT', 'OL', 'OUTPUT', 'P', 'PRE', 'SECTION', 'TABLE', 'TBODY', 'TD',
    'TFOOT', 'TH', 'THEAD', 'TR', 'UL'
  ],

  isBlock = node => is(node, blockElements),

  voidElements = [
    'AREA', 'BASE', 'BR', 'COL', 'COMMAND', 'EMBED', 'HR', 'IMG', 'INPUT',
    'KEYGEN', 'LINK', 'META', 'PARAM', 'SOURCE', 'TRACK', 'WBR'
  ],

  isVoid = node => is(node, voidElements),

  hasVoid = node => has(node, voidElements),

  meaningfulWhenBlankElements = [
    'A', 'TABLE', 'THEAD', 'TBODY', 'TFOOT', 'TH', 'TD', 'IFRAME', 'SCRIPT',
    'AUDIO', 'VIDEO'
  ],

  isMeaningfulWhenBlank = node => is(node, meaningfulWhenBlankElements),

  hasMeaningfulWhenBlank = node => has(node, meaningfulWhenBlankElements),

  is = (node, tagNames) => tagNames.indexOf(node.nodeName) >= 0,

  has = (node, tagNames) =>
    (
      node.getElementsByTagName &&
      tagNames.some(tagName => node.getElementsByTagName(tagName).length)
    ),

  rules = {

    paragraph: {
      filter: 'p',

      replacement: content => '\n\n' + content + '\n\n'
    },

    lineBreak: {
      filter: 'br',

      replacement: (content, node, options) => options.br + '\n'
    },

    heading: {
      filter: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'],

      replacement: (content, node, options) => {
        var hLevel = Number(node.nodeName.charAt(1));

        if (options.headingStyle === 'setext' && hLevel < 3) {
          var underline = repeat((hLevel === 1 ? '=' : '-'), content.length);
          return '\n\n' + content + '\n' + underline + '\n\n'
        }
        return '\n\n' + repeat('#', hLevel) + ' ' + content + '\n\n'
      }
    },

    blockquote: {
      filter: 'blockquote',

      replacement: (content) => {
        content = content.replace(/^\n+|\n+$/g, '');
        content = content.replace(/^/gm, '> ');
        return '\n\n' + content + '\n\n'
      }
    },

    list: {
      filter: ['ul', 'ol'],

      replacement: (content, node) => {
        var parent = node.parentNode;
        if (parent.nodeName === 'LI' && parent.lastElementChild === node) {
          return '\n' + content
        }
        return '\n\n' + content + '\n\n'
      }
    },

    listItem: {
      filter: 'li',

      replacement: (content, node, options) => {
        content = content
          .replace(/^\n+/, '') // remove leading newlines
          .replace(/\n+$/, '\n') // replace trailing newlines with just a single one
          .replace(/\n/gm, '\n    '); // indent
        var prefix = options.bulletListMarker + '   ';
        var parent = node.parentNode;
        if (parent.nodeName === 'OL') {
          var start = parent.getAttribute('start');
          var index = Array.prototype.indexOf.call(parent.children, node);
          prefix = (start ? Number(start) + index : index + 1) + '.  ';
        }
        return (
          prefix + content + (node.nextSibling && !/\n$/.test(content) ? '\n' : '')
        )
      }
    },

    indentedCodeBlock: {
      filter: (node, options) =>
        (
          options.codeBlockStyle === 'indented' &&
          node.nodeName === 'PRE' &&
          node.firstChild &&
          node.firstChild.nodeName === 'CODE'
        )
      ,

      replacement: (content, node) =>
        (
          '\n\n    ' +
          node.firstChild.textContent.replace(/\n/g, '\n    ') +
          '\n\n'
        )
    },

    fencedCodeBlock: {
      filter: (node, options) =>
        (
          options.codeBlockStyle === 'fenced' &&
          node.nodeName === 'PRE' &&
          node.firstChild &&
          node.firstChild.nodeName === 'CODE'
        )
      ,

      replacement: (content, node, options) => {
        var className = node.firstChild.getAttribute('class') || '';
        var language = (className.match(/language-(\S+)/) || [null, ''])[1];
        var code = node.firstChild.textContent;

        var fenceChar = options.fence.charAt(0);
        var fenceSize = 3;
        var fenceInCodeRegex = new RegExp('^' + fenceChar + '{3,}', 'gm');

        var match;
        while ((match = fenceInCodeRegex.exec(code))) {
          if (match[0].length >= fenceSize) {
            fenceSize = match[0].length + 1;
          }
        }

        var fence = repeat(fenceChar, fenceSize);

        return (
          '\n\n' + fence + language + '\n' +
          code.replace(/\n$/, '') +
          '\n' + fence + '\n\n'
        )
      }
    },

    horizontalRule: {
      filter: 'hr',

      replacement: (content, node, options) => '\n\n' + options.hr + '\n\n'
    },

    inlineLink: {
      filter: (node, options) =>
        (
          options.linkStyle === 'inlined' &&
          node.nodeName === 'A' &&
          node.getAttribute('href')
        )
      ,

      replacement: (content, node) => {
        var href = node.getAttribute('href');
        if (href) href = href.replace(/([()])/g, '\\$1');
        var title = cleanAttribute(node.getAttribute('title'));
        if (title) title = ' "' + title.replace(/"/g, '\\"') + '"';
        return '[' + content + '](' + href + title + ')'
      }
    },

    referenceLink: {
      filter: (node, options) =>
        (
          options.linkStyle === 'referenced' &&
          node.nodeName === 'A' &&
          node.getAttribute('href')
        )
      ,

      replacement(content, node, options) {
        var href = node.getAttribute('href');
        var title = cleanAttribute(node.getAttribute('title'));
        if (title) title = ' "' + title + '"';
        var replacement;
        var reference;

        switch (options.linkReferenceStyle) {
          case 'collapsed':
            replacement = '[' + content + '][]';
            reference = '[' + content + ']: ' + href + title;
            break
          case 'shortcut':
            replacement = '[' + content + ']';
            reference = '[' + content + ']: ' + href + title;
            break
          default:
            var id = this.references.length + 1;
            replacement = '[' + content + '][' + id + ']';
            reference = '[' + id + ']: ' + href + title;
        }

        this.references.push(reference);
        return replacement
      },

      references: [],

      append() {
        var references = '';
        if (this.references.length) {
          references = '\n\n' + this.references.join('\n') + '\n\n';
          this.references = []; // Reset references
        }
        return references
      }
    },

    emphasis: {
      filter: ['em', 'i'],

      replacement: (content, node, options) => {
        if (!content.trim()) return ''
        return options.emDelimiter + content + options.emDelimiter
      }
    },

    strong: {
      filter: ['strong', 'b'],

      replacement: (content, node, options) => {
        if (!content.trim()) return ''
        return options.strongDelimiter + content + options.strongDelimiter
      }
    },

    code: {
      filter: (node) => {
        var hasSiblings = node.previousSibling || node.nextSibling;
        var isCodeBlock = node.parentNode.nodeName === 'PRE' && !hasSiblings;

        return node.nodeName === 'CODE' && !isCodeBlock
      },

      replacement: (content) => {
        if (!content) return ''
        content = content.replace(/\r?\n|\r/g, ' ');

        var extraSpace = /^`|^ .*?[^ ].* $|`$/.test(content) ? ' ' : '';
        var delimiter = '`';
        var matches = content.match(/`+/gm) || [];
        while (matches.indexOf(delimiter) !== -1) delimiter = delimiter + '`';

        return delimiter + extraSpace + content + extraSpace + delimiter
      }
    },

    image: {
      filter: 'img',

      replacement: (content, node) => {
        var alt = cleanAttribute(node.getAttribute('alt'));
        var src = node.getAttribute('src') || '';
        var title = cleanAttribute(node.getAttribute('title'));
        var titlePart = title ? ' "' + title + '"' : '';
        return src ? '![' + alt + ']' + '(' + src + titlePart + ')' : ''
      }
    },

    style: {
      filter: 'style',
      replacement: () => ''
    }
  },

  cleanAttribute = (attribute) => attribute ? attribute.replace(/(\n+\s*)+/g, '\n') : '';

  /**
   * Manages a collection of rules used to convert HTML to Markdown
   */

  class Rules
  {
    constructor(options) {
      this.options = options;
      this._keep = [];
      this._remove = [];

      this.blankRule = {
        replacement: options.blankReplacement
      };

      this.keepReplacement = options.keepReplacement;

      this.defaultRule = {
        replacement: options.defaultReplacement
      };

      this.array = [];
      for (var key in options.rules) this.array.push(options.rules[key]);
    }

    add(key, rule) {
      this.array.unshift(rule);
    }

    keep(filter) {
      this._keep.unshift({
        filter: filter,
        replacement: this.keepReplacement
      });
    }

    remove(filter) {
      this._remove.unshift({
        filter: filter,
        replacement: () => ''
      });
    }

    forNode(node) {
      if (node.isBlank) return this.blankRule
      return findRule(this.array, node, this.options)
        || findRule(this._keep, node, this.options)
        || findRule(this._remove, node, this.options)
        || this.defaultRule
    }

    forEach(fn) {
      for (var i = 0; i < this.array.length; i++) fn(this.array[i], i);
    }
  }

  const findRule = (rules, node, options) => {
    for (var i = 0; i < rules.length; i++) {
      var rule = rules[i];
      if (filterValue(rule, node, options)) return rule
    }
    return void 0
  },

  filterValue = (rule, node, options) => {
    var filter = rule.filter;
    if (typeof filter === 'string') {
      return (filter === node.nodeName.toLowerCase())
    } else if (Array.isArray(filter)) {
      return (filter.indexOf(node.nodeName.toLowerCase()) > -1)
    } else if (typeof filter === 'function') {
      return !!filter.call(rule, node, options)
    }
    throw new TypeError('`filter` needs to be a string, array, or function')
  },

  /**
   * The collapseWhitespace function is adapted from collapse-whitespace
   * by Luc Thevenard.
   *
   * The MIT License (MIT)
   *
   * Copyright (c) 2014 Luc Thevenard <lucthevenard@gmail.com>
   *
   * Permission is hereby granted, free of charge, to any person obtaining a copy
   * of this software and associated documentation files (the "Software"), to deal
   * in the Software without restriction, including without limitation the rights
   * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
   * copies of the Software, and to permit persons to whom the Software is
   * furnished to do so, subject to the following conditions:
   *
   * The above copyright notice and this permission notice shall be included in
   * all copies or substantial portions of the Software.
   *
   * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
   * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
   * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
   * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
   * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
   * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
   * THE SOFTWARE.
   */

  /**
   * collapseWhitespace(options) removes extraneous whitespace from an the given element.
   *
   * @param {Object} options
   */
  collapseWhitespace = (options) => {
    var element = options.element;
    var isBlock = options.isBlock;
    var isVoid = options.isVoid;
    var isPre = options.isPre || ((node) => node.nodeName === 'PRE');

    if (!element.firstChild || isPre(element)) return

    var prevText = null;
    var keepLeadingWs = false;

    var prev = null;
    var node = next(prev, element, isPre);

    while (node !== element) {
      if (node.nodeType === 3 || node.nodeType === 4) { // Node.TEXT_NODE or Node.CDATA_SECTION_NODE
        var text = node.data.replace(/[ \r\n\t]+/g, ' ');

        if ((!prevText || / $/.test(prevText.data)) &&
            !keepLeadingWs && text[0] === ' ') {
          text = text.substr(1);
        }

        // `text` might be empty at this point.
        if (!text) {
          node = remove(node);
          continue
        }

        node.data = text;

        prevText = node;
      } else if (node.nodeType === 1) { // Node.ELEMENT_NODE
        if (isBlock(node) || node.nodeName === 'BR') {
          if (prevText) {
            prevText.data = prevText.data.replace(/ $/, '');
          }

          prevText = null;
          keepLeadingWs = false;
        } else if (isVoid(node) || isPre(node)) {
          // Avoid trimming space around non-block, non-BR void elements and inline PRE.
          prevText = null;
          keepLeadingWs = true;
        } else if (prevText) {
          // Drop protection if set previously.
          keepLeadingWs = false;
        }
      } else {
        node = remove(node);
        continue
      }

      var nextNode = next(prev, node, isPre);
      prev = node;
      node = nextNode;
    }

    if (prevText) {
      prevText.data = prevText.data.replace(/ $/, '');
      if (!prevText.data) {
        remove(prevText);
      }
    }
  },

  /**
   * remove(node) removes the given node from the DOM and returns the
   * next node in the sequence.
   *
   * @param {Node} node
   * @return {Node} node
   */
  remove = (node) => {
    var next = node.nextSibling || node.parentNode;

    node.parentNode.removeChild(node);

    return next
  },

  /**
   * next(prev, current, isPre) returns the next node in the sequence, given the
   * current and previous nodes.
   *
   * @param {Node} prev
   * @param {Node} current
   * @param {Function} isPre
   * @return {Node}
   */
  next = (prev, current, isPre) => {
    if ((prev && prev.parentNode === current) || isPre(current)) {
      return current.nextSibling || current.parentNode
    }

    return current.firstChild || current.nextSibling || current.parentNode
  },

  /*
   * Parsing HTML strings
   */

  RootNode = (input, options) => {
    var root;
    if (typeof input === 'string') {
      var doc = htmlParser().parseFromString(
        // DOM parsers arrange elements in the <head> and <body>.
        // Wrapping in a custom element ensures elements are reliably arranged in
        // a single element.
        '<x-turndown id="turndown-root">' + input + '</x-turndown>',
        'text/html'
      );
      root = doc.getElementById('turndown-root');
    } else {
      root = input.cloneNode(true);
    }
    collapseWhitespace({
      element: root,
      isBlock: isBlock,
      isVoid: isVoid,
      isPre: options.preformattedCode ? isPreOrCode : null
    });

    return root
  };

  var _htmlParser;
  const htmlParser = () => {
    _htmlParser = _htmlParser || new DOMParser();
    return _htmlParser
  },

  isPreOrCode = (node) => node.nodeName === 'PRE' || node.nodeName === 'CODE',

  Node = (node, options) => {
    node.isBlock = isBlock(node);
    node.isCode = node.nodeName === 'CODE' || node.parentNode.isCode;
    node.isBlank = isBlank(node);
    node.flankingWhitespace = flankingWhitespace(node, options);
    return node
  },

  isBlank = (node) =>
    (
      !isVoid(node) &&
      !isMeaningfulWhenBlank(node) &&
      /^\s*$/i.test(node.textContent) &&
      !hasVoid(node) &&
      !hasMeaningfulWhenBlank(node)
    )
  ,

  flankingWhitespace = (node, options) => {
    if (node.isBlock || (options.preformattedCode && node.isCode)) {
      return { leading: '', trailing: '' }
    }

    var edges = edgeWhitespace(node.textContent);

    // abandon leading ASCII WS if left-flanked by ASCII WS
    if (edges.leadingAscii && isFlankedByWhitespace('left', node, options)) {
      edges.leading = edges.leadingNonAscii;
    }

    // abandon trailing ASCII WS if right-flanked by ASCII WS
    if (edges.trailingAscii && isFlankedByWhitespace('right', node, options)) {
      edges.trailing = edges.trailingNonAscii;
    }

    return { leading: edges.leading, trailing: edges.trailing }
  },

  edgeWhitespace = (string) => {
    var m = string.match(/^(([ \t\r\n]*)(\s*))(?:(?=\S)[\s\S]*\S)?((\s*?)([ \t\r\n]*))$/);
    return {
      leading: m[1], // whole string for whitespace-only strings
      leadingAscii: m[2],
      leadingNonAscii: m[3],
      trailing: m[4], // empty for whitespace-only strings
      trailingNonAscii: m[5],
      trailingAscii: m[6]
    }
  },

  isFlankedByWhitespace = (side, node, options) => {
    var sibling;
    var regExp;
    var isFlanked;

    if (side === 'left') {
      sibling = node.previousSibling;
      regExp = / $/;
    } else {
      sibling = node.nextSibling;
      regExp = /^ /;
    }

    if (sibling) {
      if (sibling.nodeType === 3) {
        isFlanked = regExp.test(sibling.nodeValue);
      } else if (options.preformattedCode && sibling.nodeName === 'CODE') {
        isFlanked = false;
      } else if (sibling.nodeType === 1 && !isBlock(sibling)) {
        isFlanked = regExp.test(sibling.textContent);
      }
    }
    return isFlanked
  },

  reduce = Array.prototype.reduce,
  escapes = [
    [/\\/g, '\\\\'],
    [/\*/g, '\\*'],
    [/^-/g, '\\-'],
    [/^\+ /g, '\\+ '],
    [/^(=+)/g, '\\$1'],
    [/^(#{1,6}) /g, '\\$1 '],
    [/`/g, '\\`'],
    [/^~~~/g, '\\~~~'],
    [/\[/g, '\\['],
    [/\]/g, '\\]'],
    [/^>/g, '\\>'],
    [/_/g, '\\_'],
    [/^(\d+)\. /g, '$1\\. ']
  ];

  class TurndownService
  {
    constructor(options) {
      this.options = Object.assign({
        rules: rules,
        headingStyle: 'setext',
        hr: '* * *',
        bulletListMarker: '*',
        codeBlockStyle: 'indented',
        fence: '```',
        emDelimiter: '_',
        strongDelimiter: '**',
        linkStyle: 'inlined',
        linkReferenceStyle: 'full',
        br: '  ',
        preformattedCode: false,
        blankReplacement: (content, node) => node.isBlock ? '\n\n' : '',
        keepReplacement: (content, node) => node.isBlock ? '\n\n' + node.outerHTML + '\n\n' : node.outerHTML,
        defaultReplacement: (content, node) => node.isBlock ? '\n\n' + content + '\n\n' : content
      }, options);
      this.rules = new Rules(this.options);
    }

    /**
     * The entry point for converting a string or DOM node to Markdown
     * @public
     * @param {String|HTMLElement} input The string or DOM node to convert
     * @returns A Markdown representation of the input
     * @type String
     */

    turndown(input) {
      if (!canConvert(input)) {
        throw new TypeError(
          input + ' is not a string, or an element/document/fragment node.'
        )
      }

      if (input === '') return ''

      var output = this.process(RootNode(input, this.options));
      return this.postProcess(output)
    }

    /**
     * Add one or more plugins
     * @public
     * @param {Function|Array} plugin The plugin or array of plugins to add
     * @returns The Turndown instance for chaining
     * @type Object
     */

    use(plugin) {
      if (Array.isArray(plugin)) {
        for (var i = 0; i < plugin.length; i++) this.use(plugin[i]);
      } else if (typeof plugin === 'function') {
        plugin(this);
      } else {
        throw new TypeError('plugin must be a Function or an Array of Functions')
      }
      return this
    }

    /**
     * Adds a rule
     * @public
     * @param {String} key The unique key of the rule
     * @param {Object} rule The rule
     * @returns The Turndown instance for chaining
     * @type Object
     */

    addRule(key, rule) {
      this.rules.add(key, rule);
      return this
    }

    /**
     * Keep a node (as HTML) that matches the filter
     * @public
     * @param {String|Array|Function} filter The unique key of the rule
     * @returns The Turndown instance for chaining
     * @type Object
     */

    keep(filter) {
      this.rules.keep(filter);
      return this
    }

    /**
     * Remove a node that matches the filter
     * @public
     * @param {String|Array|Function} filter The unique key of the rule
     * @returns The Turndown instance for chaining
     * @type Object
     */

    remove(filter) {
      this.rules.remove(filter);
      return this
    }

    /**
     * Escapes Markdown syntax
     * @public
     * @param {String} string The string to escape
     * @returns A string with Markdown syntax escaped
     * @type String
     */

    escape(string) {
      return escapes.reduce((accumulator, escape) => accumulator.replace(escape[0], escape[1]), string)
    }

    /**
     * Reduces a DOM node down to its Markdown string equivalent
     * @private
     * @param {HTMLElement} parentNode The node to convert
     * @returns A Markdown representation of the node
     * @type String
     */

    process(parentNode) {
      var self = this;
      return reduce.call(parentNode.childNodes, (output, node) => {
        node = Node(node, self.options);

        var replacement = '';
        if (node.nodeType === 3) {
          replacement = node.isCode ? node.nodeValue : self.escape(node.nodeValue);
        } else if (node.nodeType === 1) {
          replacement = self.replacementForNode(node);
        }

        return join(output, replacement)
      }, '')
    }

    /**
     * Appends strings as each rule requires and trims the output
     * @private
     * @param {String} output The conversion output
     * @returns A trimmed version of the ouput
     * @type String
     */

    postProcess(output) {
      var self = this;
      this.rules.forEach((rule) => {
        if (typeof rule.append === 'function') {
          output = join(output, rule.append(self.options));
        }
      });

      return output.replace(/^[\t\r\n]+/, '').replace(/[\t\r\n\s]+$/, '')
    }

    /**
     * Converts an element node to its Markdown equivalent
     * @private
     * @param {HTMLElement} node The node to convert
     * @returns A Markdown representation of the node
     * @type String
     */

    replacementForNode(node) {
      var rule = this.rules.forNode(node);
      var content = this.process(node);
      var whitespace = node.flankingWhitespace;
      if (whitespace.leading || whitespace.trailing) content = content.trim();
      return (
        whitespace.leading +
        rule.replacement(content, node, this.options) +
        whitespace.trailing
      )
    }
  }

  /**
   * Joins replacement to the current output with appropriate number of new lines
   * @private
   * @param {String} output The current conversion output
   * @param {String} replacement The string to append to the output
   * @returns Joined output
   * @type String
   */

  const join = (output, replacement) => {
    var s1 = trimTrailingNewlines(output);
    var s2 = trimLeadingNewlines(replacement);
    var nls = Math.max(output.length - s1.length, replacement.length - s2.length);
    var separator = '\n\n'.substring(0, nls);

    return s1 + separator + s2
  },

  /**
   * Determines whether an input can be converted
   * @private
   * @param {String|HTMLElement} input Describe this parameter
   * @returns Describe what it returns
   * @type String|Object|Array|Boolean|Number
   */

  canConvert = (input) =>
    (
      input != null && (
        typeof input === 'string' ||
        (input.nodeType && (
          input.nodeType === 1 || input.nodeType === 9 || input.nodeType === 11
        ))
      )
    )
  ;

  return TurndownService;

})();

/* eslint max-len: 0 */

(doc => {

const
	i18n = (str, def) => rl.i18n(str) || def,

	ctrlKey = shortcuts.getMetaKey() + ' + ',

	createElement = name => doc.createElement(name),

	tpl = createElement('template'),

	trimLines = html => html.trim().replace(/^(<div>\s*<br\s*\/?>\s*<\/div>)+/, '').trim(),
	htmlToPlain = html => rl.Utils.htmlToPlain(html).trim(),
	plainToHtml = text => rl.Utils.plainToHtml(text),

	forEachObjectValue = (obj, fn) => Object.values(obj).forEach(fn),

	SquireDefaultConfig = {
/*
		addLinks: true // allow_smart_html_links
*/
		sanitizeToDOMFragment: (html, isPaste/*, squire*/) => {
			html = (html||'')
				.replace(/<\/?(BODY|HTML)[^>]*>/gi,'')
				.replace(/<!--[^>]+-->/g,'')
				.replace(/<span[^>]*>\s*<\/span>/gi,'')
				.trim();
			tpl.innerHTML =  isPaste ? rl.Utils.cleanHtml(html).html : html;
			return tpl.content;
		}
	};

class SquireUI
{
	constructor(container) {
		const
			clr = createElement('input'),
			doClr = name => input => {
				// https://github.com/the-djmaze/snappymail/issues/826
				clr.style.left = (input.offsetLeft + input.parentNode.offsetLeft) + 'px';
				clr.style.width = input.offsetWidth + 'px';

				clr.value = '';
				clr.onchange = () => squire.setStyle({[name]:clr.value});
				// Chrome 110+ https://github.com/the-djmaze/snappymail/issues/1199
//				clr.oninput = () => squire.setStyle({[name]:clr.value});
				setTimeout(()=>clr.click(),1);
			},

			actions = {
				mode: {
					plain: {
//						html: '〈〉',
//						cmd: () => this.setMode('plain' == this.mode ? 'wysiwyg' : 'plain'),
						select: [
							[i18n('SETTINGS_GENERAL/EDITOR_HTML'),'wysiwyg'],
							[i18n('SETTINGS_GENERAL/EDITOR_PLAIN'),'plain']
						],
						cmd: s => this.setMode('plain' == s.value ? 'plain' : 'wysiwyg')
					}
				},
				font: {
					fontFamily: {
						select: {
							'sans-serif': {
								Arial: "'Nimbus Sans L', 'Liberation sans', 'Arial Unicode MS', Arial, Helvetica, Garuda, Utkal, FreeSans, sans-serif",
								Tahoma: "'Luxi Sans', Tahoma, Loma, Geneva, Meera, sans-serif",
								Trebuchet: "'DejaVu Sans Condensed', Trebuchet, 'Trebuchet MS', sans-serif",
								Lucida: "'Lucida Sans Unicode', 'Lucida Sans', 'DejaVu Sans', 'Bitstream Vera Sans', 'DejaVu LGC Sans', sans-serif",
								Verdana: "'DejaVu Sans', Verdana, Geneva, 'Bitstream Vera Sans', 'DejaVu LGC Sans', sans-serif"
							},
							monospace: {
								Courier: "'Liberation Mono', 'Courier New', FreeMono, Courier, monospace",
								Lucida: "'DejaVu Sans Mono', 'DejaVu LGC Sans Mono', 'Bitstream Vera Sans Mono', 'Lucida Console', Monaco, monospace"
							},
							sans: {
								Times: "'Nimbus Roman No9 L', 'Times New Roman', Times, FreeSerif, serif",
								Palatino: "'Bitstream Charter', 'Palatino Linotype', Palatino, Palladio, 'URW Palladio L', 'Book Antiqua', Times, serif",
								Georgia: "'URW Palladio L', Georgia, Times, serif"
							}
						},
						cmd: s => squire.setStyle({ fontFamily: s.value })
					},
					fontSize: {
						select: [[i18n('GLOBAL/DEFAULT'),''],'11px','13px','16px','20px','24px','30px'],
						defaultValueIndex: 0,
						cmd: s => squire.setStyle({ fontSize: s.value })
						// TODO: maybe consider using https://developer.mozilla.org/en-US/docs/Web/CSS/font-size#values
						// example:
						// select: ['','xx-small', 'x-small',' small',' medium', 'large', 'x-large', 'xx-large', 'xxx-large'],
						// defaultValueIndex: 0,
					},
// 					dir: {
// 						select: [
// 							[i18n('EDITOR/DIR_LTR', 'LTR'),'ltr'],
// 							[i18n('EDITOR/DIR_RTL', 'RTL'),'rtl'],
// 							[i18n('EDITOR/DIR_AUTO', 'Auto'),'auto'],
// 							['',''],
// 						],
// 						cmd: s => {
// 							squire.setAttribute('dir', s.value || null);
// //							squire.setStyle({ 'unicode-bidi': 'plaintext' });
// 						}
// 					}
				},
				dir: {
					dir_ltr: {
						html: '⁋',
						cmd: () => squire.setTextDirection('ltr')
					},
					dir_rtl: {
						html: '¶',
						cmd: () => squire.setTextDirection('rtl')
					}
				},
				colors: {
					textColor: {
						html: 'A<sub>▾</sub>',
						cmd: doClr('color')
					},
					backgroundColor: {
						html: '🎨', /* ▧ */
						cmd: doClr('backgroundColor')
					},
				},
				inline: {
					bold: {
						html: 'B',
						cmd: () => this.doAction('bold'),
						key: 'B',
						matches: 'B,STRONG'
					},
					italic: {
						html: 'I',
						cmd: () => this.doAction('italic'),
						key: 'I',
						matches: 'I'
					},
					underline: {
						html: '<u>U</u>',
						cmd: () => this.doAction('underline'),
						key: 'U',
						matches: 'U'
					},
					strike: {
						html: '<s>S</s>',
						cmd: () => this.doAction('strikethrough'),
						key: 'Shift + 7',
						matches: 'S'
					},
					sub: {
						html: 'Xₙ',
						cmd: () => this.doAction('subscript'),
						key: 'Shift + 5',
						matches: 'SUB'
					},
					sup: {
						html: 'Xⁿ',
						cmd: () => this.doAction('superscript'),
						key: 'Shift + 6',
						matches: 'SUP'
					}
				},
				block: {
					ol: {
						html: '#',
						cmd: () => this.doList('OL'),
						key: 'Shift + 8',
						matches: 'OL'
					},
					ul: {
						html: '⋮',
						cmd: () => this.doList('UL'),
						key: 'Shift + 9',
						matches: 'UL'
					},
					quote: {
						html: '"',
						cmd: () => {
							let parent = squire.getSelectionClosest('UL,OL,BLOCKQUOTE')?.nodeName;
							('BLOCKQUOTE' == parent) ? squire.decreaseQuoteLevel() : squire.increaseQuoteLevel();
						},
						matches: 'BLOCKQUOTE'
					},
					indentDecrease: {
						html: '⇤',
						cmd: () => squire.changeIndentationLevel('decrease'),
						key: ']'
					},
					indentIncrease: {
						html: '⇥',
						cmd: () => squire.changeIndentationLevel('increase'),
						key: '['
					}
				},
				targets: {
					link: {
						html: '🔗',
						cmd: () => {
							let node = squire.getSelectionClosest('A'),
								url = prompt("Link", node?.href || "https://");
							if (url != null) {
								url.length ? squire.makeLink(url) : (node && squire.removeLink());
							}
						},
						matches: 'A'
					},
					imageUrl: {
						html: '🖼️',
						cmd: () => {
							let node = squire.getSelectionClosest('IMG'),
								src = prompt("Image", node?.src || "https://");
							src?.length ? squire.insertImage(src) : node?.remove();
						},
						matches: 'IMG'
					},
					imageUpload: {
						html: '📂️',
						cmd: () => browseImage.click(),
						matches: 'IMG'
					}
				},
/*
				table: {
					// TODO
				},
*/
				changes: {
					undo: {
						html: '↶',
						cmd: () => squire.undo(),
						key: 'Z'
					},
					redo: {
						html: '↷',
						cmd: () => squire.redo(),
						key: 'Y'
					},
					source: {
						html: '👁',
						cmd: btn => {
							this.setMode('source' == this.mode ? 'wysiwyg' : 'source');
							btn.classList.toggle('active', 'source' == this.mode);
						}
					}
				},

				clear: {
					removeStyle: {
						html: '⎚',
						cmd: () => squire.setStyle()
					}
				}
			},

			plain = createElement('textarea'),
			wysiwyg = createElement('div'),
			toolbar = createElement('div'),
			browseImage = createElement('input'),
			squire = new Squire(wysiwyg, SquireDefaultConfig);

		clr.type = 'color';
		toolbar.append(clr);
		// Chrome https://github.com/the-djmaze/snappymail/issues/1199
		let clrid = 'squire-colors',
			colorlist = doc.getElementById(clrid),
			add = hex => colorlist.append(new Option(hex));
		if (!colorlist) {
			colorlist = createElement('datalist');
			colorlist.id = clrid;
			// Color blind safe Tableau 10 by Maureen Stone
			add('#4E79A7');
			add('#F28E2B');
			add('#E15759');
			add('#76B7B2');
			add('#59A14F');
			add('#EDC948');
			add('#B07AA1');
			add('#FF9DA7');
			add('#9C755F');
			add('#BAB0AC');
			doc.body.append(colorlist);
		}
		clr.setAttribute('list', clrid);

		browseImage.type = 'file';
		browseImage.accept = 'image/*';
		browseImage.style.display = 'none';
		browseImage.onchange = () => {
			if (browseImage.files.length) {
				let reader = new FileReader();
				reader.readAsDataURL(browseImage.files[0]);
				reader.onloadend = () => reader.result && squire.insertImage(reader.result);
			}
		}

		plain.className = 'squire-plain';
		wysiwyg.className = 'squire-wysiwyg';
		wysiwyg.dir = 'auto';
		this.mode = ''; // 'plain' | 'wysiwyg'
		this.container = container;
		this.squire = squire;
		this.plain = plain;
		this.wysiwyg = wysiwyg;

		dispatchEvent(new CustomEvent('squire-toolbar', {detail:{squire:this,actions:actions}}));

		toolbar.className = 'squire-toolbar btn-toolbar';
		let group, action/*, touchTap*/;
		for (group in actions) {
			let toolgroup = createElement('div');
			toolgroup.className = 'btn-group';
			toolgroup.id = 'squire-toolgroup-'+group;
			for (action in actions[group]) {
				let cfg = actions[group][action], input, ev = 'click';
				if (cfg.input) {
					input = createElement('input');
					input.type = cfg.input;
					ev = 'change';
				} else if (cfg.select) {
					input = createElement('select');
					input.className = 'btn';
					if (Array.isArray(cfg.select)) {
						cfg.select.forEach(value => {
							value = Array.isArray(value) ? value : [value, value];
							var option = new Option(value[0], value[1]);
							option.style[action] = value[1];
							input.append(option);
						});
					} else {
						input.add(new Option(i18n('GLOBAL/DEFAULT'), ''));
						Object.entries(cfg.select).forEach(([label, options]) => {
							let group = createElement('optgroup');
							group.label = label;
							Object.entries(options).forEach(([text, value]) => {
								var option = new Option(text, value);
								option.style[action] = value;
								group.append(option);
							});
							input.add(group);
						});
					}
					ev = 'input';
				} else {
					input = createElement('button');
					input.type = 'button';
					input.className = 'btn';
					input.innerHTML = cfg.html;
					input.action_cmd = cfg.cmd;
/*
					input.addEventListener('pointerdown', () => touchTap = input, {passive:true});
					input.addEventListener('pointermove', () => touchTap = null, {passive:true});
					input.addEventListener('pointercancel', () => touchTap = null);
					input.addEventListener('pointerup', e => {
						if (touchTap === input) {
							e.preventDefault();
							cfg.cmd(input);
						}
						touchTap = null;
					});
*/
				}
				input.addEventListener(ev, () => cfg.cmd(input));
				cfg.hint = i18n('EDITOR/' + action.toUpperCase());
				if (cfg.hint) {
					input.title = cfg.key ? cfg.hint + ' (' + ctrlKey + cfg.key + ')' : cfg.hint;
				} else if (cfg.key) {
					input.title = ctrlKey + cfg.key;
				}
				input.dataset.action = action;
				input.tabIndex = -1;
				cfg.input = input;
				toolgroup.append(input);
			}
			toolgroup.children.length && toolbar.append(toolgroup);
		}

		this.modeSelect = actions.mode.plain.input;

		let changes = actions.changes;
		changes.undo.input.disabled = changes.redo.input.disabled = true;
		squire.addEventListener('undoStateChange', e => {
			changes.undo.input.disabled = !e.detail.canUndo;
			changes.redo.input.disabled = !e.detail.canRedo;
		});

		squire.addEventListener('pasteImage', e => {
			const items = e.detail.clipboardData.items;
			let l = items.length;
			while (l--) {
				const item = items[l];
				if (/^image\/(png|jpeg|webp)/.test(item.type)) {
					let reader = new FileReader();
					reader.onload = event => {
						let img = createElement("img"),
							canvas = createElement("canvas"),
							ctx = canvas.getContext('2d');
						img.onload = ()=>{
							ctx.drawImage(img, 0, 0);
							let width = img.width, height = img.height;
							if (width > height) {
								// Landscape
								if (width > 1024) {
									height = height * 1024 / width;
									width = 1024;
								}
							} else if (height > 1024) {
								// Portrait
								width = width * 1024 / height;
								height = 1024;
							}
							canvas.width = width;
							canvas.height = height;
							ctx.drawImage(img, 0, 0, width, height);
							squire.insertHTML('<img alt="" style="width:100%;max-width:'+width+'px" src="'+canvas.toDataURL()+'">', true);
						};
						img.src = event.target.result;
					}
					reader.readAsDataURL(item.getAsFile());
					break;
				}
			}
		});

		actions.font.fontSize.input.selectedIndex = actions.font.fontSize.defaultValueIndex;

//		squire.addEventListener('focus', () => shortcuts.off());
//		squire.addEventListener('blur', () => shortcuts.on());

		container.append(toolbar, wysiwyg, plain);

		/**
		 * @param {string} fontName
		 * @return {string}
		 */
		const normalizeFontName = (fontName) => fontName.trim().replace(/(^["']*|["']*$)/g, '').trim().toLowerCase();

		/** @type {string[]} - lower cased array of available font families*/
		const fontFamiliesLowerCase = Object.values(actions.font.fontFamily.input.options).map(option => option.value.toLowerCase());

		/**
		 * A theme might have CSS like div.squire-wysiwyg[contenteditable="true"] {
		 * font-family: 'Times New Roman', Times, serif; }
		 * so let's find the best match squire.getRoot()'s font
		 * it will also help to properly handle generic font names like 'sans-serif'
		 * @type {number}
		 */
		let defaultFontFamilyIndex = 0;
		const squireRootFonts = getComputedStyle(squire.getRoot()).fontFamily.split(',').map(normalizeFontName);
		fontFamiliesLowerCase.some((family, index) => {
			const matchFound = family.split(',').some(availableFontName => {
				const normalizedFontName = normalizeFontName(availableFontName);
				return squireRootFonts.some(squireFontName => squireFontName === normalizedFontName);
			});
			if (matchFound) {
				defaultFontFamilyIndex = index;
			}
			return matchFound;
		});

		/**
		 * Instead of comparing whole 'font-family' strings,
		 * we are going to look for individual font names, because we might be
		 * editing a Draft started in another email client for example
		 *
		 * @type {Object.<string,number>}
		 */
		const fontNamesMap = {};
		/**
		 * @param {string} fontFamily
		 * @param {number} index
		 */
		const processFontFamilyString = (fontFamily, index) => {
			fontFamily.split(',').forEach(fontName => {
				const key = normalizeFontName(fontName);
				if (fontNamesMap[key] === undefined) {
					fontNamesMap[key] = index;
				}
			});
		};
		// first deal with the default font family
		processFontFamilyString(fontFamiliesLowerCase[defaultFontFamilyIndex], defaultFontFamilyIndex);
		// and now with the rest of the font families
		fontFamiliesLowerCase.forEach((fontFamily, index) => {
			if (index !== defaultFontFamilyIndex) {
				processFontFamilyString(fontFamily, index);
			}
		});

		// -----

		squire.addEventListener('pathChange', () => {

			const squireRoot = squire.getRoot();
			let range = squire.getSelection(),
				collapsed = range.collapsed,
				elm = collapsed ? range.endContainer : range?.commonAncestorContainer;
			if (elm && !(elm instanceof Element)) {
				elm = elm.parentElement;
			}
			forEachObjectValue(actions, entries => {
				forEachObjectValue(entries, cfg => {
					// Check if selection has a matching parent or contains a matching element
					cfg.matches && cfg.input.classList.toggle('active', !!(elm && (
						(!collapsed && [...elm.querySelectorAll(cfg.matches)].some(node => range.intersectsNode(node)))
						 || elm.closestWithin(cfg.matches, squireRoot)
					)));
				});
			});

			if (elm) {
				// try to find font-family and/or font-size and set "select" elements' values

				let sizeSelectedIndex = actions.font.fontSize.defaultValueIndex;
				let familySelectedIndex = defaultFontFamilyIndex;

				let familyFound = false;
				let sizeFound = false;
				do {
					if (!familyFound && elm.style.fontFamily) {
						familyFound = true;
						familySelectedIndex = -1; // show empty select if we don't know the font
						const fontNames = elm.style.fontFamily.split(',');
						for (let i = 0; i < fontNames.length; i++) {
							const index = fontNamesMap[normalizeFontName(fontNames[i])];
							if (index !== undefined) {
								familySelectedIndex = index;
								break;
							}
						}
					}

					if (!sizeFound && elm.style.fontSize) {
						sizeFound = true;
						// -1 is ok because it will just show a black <select>
						sizeSelectedIndex = actions.font.fontSize.select.indexOf(elm.style.fontSize);
					}

					elm = elm.parentElement;
				} while ((!familyFound || !sizeFound) && elm && elm !== squireRoot);

				actions.font.fontFamily.input.selectedIndex = familySelectedIndex;
				actions.font.fontSize.input.selectedIndex = sizeSelectedIndex;
			}
		});
/*
		squire.addEventListener('cursor', e => {
			console.dir({cursor:e.detail.range});
		});
		squire.addEventListener('select', e => {
			console.dir({select:e.detail.range});
		});
*/
	}

	doAction(name) {
		this.squire[name]();
		this.squire.focus();
	}

	doList(type) {
		let parent = this.squire.getSelectionClosest('UL,OL')?.nodeName,
			fn = {UL:'makeUnorderedList',OL:'makeOrderedList'};
		(parent == type) ? this.squire.removeList() : this.squire[fn[type]]();
	}
/*
	testPresenceinSelection(format, validation) {
		return validation.test(this.squire.getPath()) || this.squire.hasFormat(format);
	}
*/
	setMode(mode) {
		if (this.mode != mode) {
			let cl = this.container.classList, source = 'source' == this.mode;
			cl.remove('squire-mode-'+this.mode);
			if ('plain' == mode) {
				this.plain.value = htmlToPlain(source ? this.plain.value : this.squire.getHTML(), true);
			} else if ('source' == mode) {
				this.plain.value = this.squire.getHTML();
			} else {
				this.setData(source ? this.plain.value : plainToHtml(this.plain.value, true));
				mode = 'wysiwyg';
			}
			this.mode = mode; // 'wysiwyg' or 'plain'
			cl.add('squire-mode-'+mode);
			this.onModeChange?.();
			setTimeout(()=>this.focus(),1);
		}
		this.modeSelect.selectedIndex = 'plain' == this.mode ? 1 : 0;
	}

	on(type, fn) {
		if ('mode' == type) {
			this.onModeChange = fn;
		} else {
			this.squire.addEventListener(type, fn);
			this.plain.addEventListener(type, fn);
		}
	}

	execCommand(cmd, cfg) {
		if ('insertSignature' == cmd) {
			cfg = Object.assign({
				clearCache: false,
				isHtml: false,
				insertBefore: false,
				signature: ''
			}, cfg);

			if (cfg.clearCache) {
				this._prev_txt_sig = null;
			} else try {
				const signature = cfg.isHtml ? htmlToPlain(cfg.signature) : cfg.signature;
				if ('plain' === this.mode) {
					let
						text = this.plain.value,
						prevSignature = this._prev_txt_sig;
					if (prevSignature) {
						text = text.replace(prevSignature, '').trim();
					}
					this.plain.value = cfg.insertBefore ? '\n\n' + signature + '\n\n' + text : text + '\n\n' +  signature;
				} else {
					const squire = this.squire,
						root = squire.getRoot(),
						br = createElement('br'),
						div = createElement('div');
					div.className = 'rl-signature';
					div.innerHTML = cfg.isHtml ? cfg.signature : plainToHtml(cfg.signature);
					root.querySelectorAll('div.rl-signature').forEach(node => node.remove());
					cfg.insertBefore ? root.prepend(div) : root.append(div);
					// Move cursor above signature
					div.before(br);
					div.before(br.cloneNode());
//					squire._docWasChanged();
				}
				this._prev_txt_sig = signature;
			} catch (e) {
				console.error(e);
			}
		}
	}

	getData() {
		return 'source' == this.mode ? this.plain.value : trimLines(this.squire.getHTML());
	}

	setData(html) {
//		this.plain.value = html;
		const squire = this.squire;
		squire.setHTML(trimLines(html));
		const node = squire.getRoot(),
			range = squire.getSelection();
		range.setStart(node, 0);
		range.setEnd(node, 0);
		squire.setSelection( range );
	}

	getPlainData() {
		return this.plain.value;
	}

	setPlainData(text) {
		this.plain.value = text;
	}

	blur() {
		this.squire.blur();
	}

	focus() {
		if ('plain' == this.mode) {
			this.plain.focus();
			this.plain.setSelectionRange(0, 0);
		} else {
			this.squire.focus();
		}
	}
}

this.SquireUI = SquireUI;

})(document);
