
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
				img._x = xOffset == null ? src.clientWidth / 2 : xOffset;
				img._y = yOffset == null ? src.clientHeight / 2 : yOffset;
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

(V=>{function P(a,b){return null===a||da[typeof a]?a===b:!1}function ea(a,b){var d;return()=>{d||(d=setTimeout(()=>{d=0;a()},b))}}function fa(a,b){var d;return()=>{clearTimeout(d);d=setTimeout(a,b)}}function ha(a,b){b?.A?.()}function ia(a,b){var d=this.$b,f=d[y];f.$||(this.Za&&this.za[b]?(d.vb(b,a,this.za[b]),this.za[b]=null,--this.Za):f.B[b]||d.vb(b,a,f.C?{X:a}:d.Sb(a)),a.ja&&a.Wb())}function W(a){a=c.g.j.get(a,K);var b=a?.I;b&&(a.I=null,b.Mb())}function X(a,b){for(var d,f=c.m.firstChild(b);d=f;)f=
c.m.nextSibling(d),Y(a,d);c.l.notify(b,c.l.H)}function Y(a,b){var d=a;if(1===b.nodeType||c.Ab.nc(b))d=Z(b,null,a).bindingContextForDescendants;d&&!b.matches?.("SCRIPT,TEXTAREA,TEMPLATE")&&X(d,b)}function ja(a){var b=[],d={},f=[];c.g.P(a,function e(l){if(!d[l]){var g=c.h[l];g&&(g.after&&(f.push(l),g.after.forEach(h=>{if(a[h]){if(f.includes(h))throw Error("Cannot combine the following bindings, because they have a cyclic dependency: "+f.join(", "));e(h)}}),f.length--),b.push({key:l,Ib:g}));d[l]=!0}});
return b}function Z(a,b,d){var f=c.g.j.fb(a,K,{}),k=f.Xb;if(!b){if(k)throw Error("You cannot apply bindings multiple times to the same element.");f.Xb=!0}k||(f.context=d);f.hb||(f.hb={});if(b&&"function"!==typeof b)var l=b;else{var e=c.u(()=>{if(l=b?b(d,a):c.Ab.cc(a,d))d[L]?.(),d[aa]?.();return l},{s:a});l&&e.isActive()||(e=null)}var g=d,h;if(l){var n=e?m=>()=>e()[m]():m=>l[m],p={get:m=>l[m]&&n(m)(),has:m=>m in l};c.l.H in l&&c.l.subscribe(a,c.l.H,()=>{var m=l[c.l.H]();if(m){var r=c.m.childNodes(a);
r.length&&m(r,c.Eb(r[0]))}});c.l.ga in l&&(g=c.l.mb(a,d),c.l.subscribe(a,c.l.ga,()=>{var m=l[c.l.ga]();m&&c.m.firstChild(a)&&m(a)}));ja(l).forEach(m=>{var r=m.Ib.init,q=m.Ib.update,t=m.key;if(8===a.nodeType&&!c.m.ca[t])throw Error("The binding '"+t+"' cannot be used with virtual elements");try{"function"==typeof r&&c.o.M(()=>{var u=r(a,n(t),p,g.$data,g);if(u&&u.controlsDescendantBindings){if(void 0!==h)throw Error("Multiple bindings ("+h+" and "+t+") are trying to control descendant bindings of the same element. You cannot use these bindings together on the same element.");
h=t}}),"function"==typeof q&&c.u(()=>q(a,n(t),p,g.$data,g),{s:a})}catch(u){throw u.message='Unable to process binding "'+t+": "+l[t]+'"\nMessage: '+u.message,u;}})}f=void 0===h;return{shouldBindDescendants:f,bindingContextForDescendants:f&&g}}function Q(a,b){return a&&a instanceof c.ea?a:new c.ea(a,void 0,void 0,b)}var M=V.document,R={},c="undefined"!==typeof R?R:{};c.v=(a,b)=>{a=a.split(".");for(var d=c,f=0,k=a.length-1;f<k;f++)d=d[a[f]];d[a[k]]=b};c.ha=(a,b,d)=>{a[b]=d};c.v("version","3.5.1-sm");
c.g={extend:(a,b)=>b?Object.assign(a,b):a,P:(a,b)=>a&&Object.entries(a).forEach(d=>b(d[0],d[1])),cb:a=>[...a.childNodes].forEach(b=>c.removeNode(b)),Lb:a=>{a=[...a];var b=(a[0]?.ownerDocument||M).createElement("div");a.forEach(d=>b.append(c.fa(d)));return b},ya:(a,b)=>Array.prototype.map.call(a,b?d=>c.fa(d.cloneNode(!0)):d=>d.cloneNode(!0)),ua:(a,b)=>{c.g.cb(a);b&&a.append(...b)},Ba:(a,b)=>{if(a.length){for(b=8===b.nodeType&&b.parentNode||b;a.length&&a[0].parentNode!==b;)a.splice(0,1);for(;1<a.length&&
a[a.length-1].parentNode!==b;)--a.length;if(1<a.length){b=a[0];var d=a[a.length-1];for(a.length=0;b!==d;)a.push(b),b=b.nextSibling;a.push(d)}}return a},Rb:a=>null==a?"":a.trim?a.trim():a.toString().replace(/^[\s\xa0]+|[\s\xa0]+$/g,""),bb:a=>a.ownerDocument.documentElement.contains(1!==a.nodeType?a.parentNode:a),Tb:(a,b)=>{if(!a?.nodeType)throw Error("element must be a DOM node when calling triggerEvent");a.dispatchEvent(new Event(b))},i:a=>c.T(a)?a():a,lb:(a,b)=>a.textContent=c.g.i(b)||""};c.v("utils",
c.g);c.v("unwrap",c.g.i);(()=>{let a=0,b="__ko__"+Date.now(),d=new WeakMap;c.g.j={get:(f,k)=>(d.get(f)||{})[k],set:(f,k,l)=>{d.has(f)?d.get(f)[k]=l:d.set(f,{[k]:l});return l},fb:function(f,k,l){return this.get(f,k)||this.set(f,k,l)},clear:f=>d.delete(f),Z:()=>a++ +b}})();c.g.K=(()=>{var a=c.g.j.Z(),b={1:1,8:1,9:1},d={1:1,9:1};const f=(e,g)=>{var h=c.g.j.get(e,a);g&&!h&&(h=new Set,c.g.j.set(e,a,h));return h},k=e=>{var g=f(e);g&&(new Set(g)).forEach(h=>h(e));c.g.j.clear(e);d[e.nodeType]&&l(e.childNodes,
!0)},l=(e,g)=>{for(var h=[],n,p=0;p<e.length;p++)if(!g||8===e[p].nodeType)if(k(h[h.length]=n=e[p]),e[p]!==n)for(;p--&&!h.includes(e[p]););};return{ma:(e,g)=>{if("function"!=typeof g)throw Error("Callback must be a function");f(e,1).add(g)},kb:(e,g)=>{var h=f(e);h&&(h.delete(g),h.size||c.g.j.set(e,a,null))},fa:e=>{c.o.M(()=>{b[e.nodeType]&&(k(e),d[e.nodeType]&&l(e.getElementsByTagName("*")))});return e},removeNode:e=>{c.fa(e);e.parentNode&&e.parentNode.removeChild(e)}}})();c.fa=c.g.K.fa;c.removeNode=
c.g.K.removeNode;c.v("utils.domNodeDisposal",c.g.K);c.v("utils.domNodeDisposal.addDisposeCallback",c.g.K.ma);c.eb={debounce:(a,b)=>a.Ja(d=>fa(d,b)),rateLimit:(a,b)=>{if("number"==typeof b)var d=b;else{d=b.timeout;var f=b.method}var k="function"==typeof f?f:ea;a.Ja(l=>k(l,d,b))},notify:(a,b)=>{a.pa="always"==b?null:P}};var da={undefined:1,"boolean":1,number:1,string:1};c.v("extenders",c.eb);class ka{constructor(a,b,d){this.X=a;this.pb=b;this.Da=d;this.Ra=!1;this.L=this.ia=null;c.ha(this,"dispose",
this.A)}A(){this.Ra||(this.L&&c.g.K.kb(this.ia,this.L),this.Ra=!0,this.Da(),this.X=this.pb=this.Da=this.ia=this.L=null)}s(a){this.ia=a;c.g.K.ma(a,this.L=this.A.bind(this))}}c.V=function(){Object.setPrototypeOf(this,D);D.Fa(this)};var D={Fa:a=>{a.W=new Map;a.W.set("change",new Set);a.ub=1},subscribe:function(a,b,d){var f=this;d=d||"change";var k=new ka(f,b?a.bind(b):a,()=>{f.W.get(d).delete(k);f.Sa?.(d)});f.Ua?.(d);f.W.has(d)||f.W.set(d,new Set);f.W.get(d).add(k);return k},D:function(a,b){b=b||"change";
"change"===b&&this.Na();if(this.ra(b)){b="change"===b&&this.Ub||new Set(this.W.get(b));try{c.o.zb(),b.forEach(d=>{d.Ra||d.pb(a)})}finally{c.o.end()}}},Ca:function(){return this.ub},fc:function(a){return this.Ca()!==a},Na:function(){++this.ub},Ja:function(a){var b=this,d=c.T(b),f,k,l,e,g;b.wa||(b.wa=b.D,b.D=(n,p)=>{p&&"change"!==p?"beforeChange"===p?b.rb(n):b.wa(n,p):b.sb(n)});var h=a(()=>{b.ja=!1;d&&e===b&&(e=b.qb?b.qb():b());var n=k||g&&b.Ha(l,e);g=k=f=!1;n&&b.wa(l=e)});b.sb=(n,p)=>{p&&b.ja||(g=
!p);b.Ub=new Set(b.W.get("change"));b.ja=f=!0;e=n;h()};b.rb=n=>{f||(l=n,b.wa(n,"beforeChange"))};b.tb=()=>{g=!0};b.Wb=()=>{b.Ha(l,b.R(!0))&&(k=!0)}},ra:function(a){return(this.W.get(a)||[]).size},Ha:function(a,b){return!this.pa||!this.pa(a,b)},toString:()=>"[object Object]",extend:function(a){var b=this;a&&c.g.P(a,(d,f)=>{d=c.eb[d];"function"==typeof d&&(b=d(b,f)||b)});return b}};c.ha(D,"init",D.Fa);c.ha(D,"subscribe",D.subscribe);c.ha(D,"extend",D.extend);c.V.fn=Object.setPrototypeOf(D,Function.prototype);
c.kc=a=>"function"==typeof a?.subscribe&&"function"==typeof a.D;(()=>{var a=[],b,d=0;c.o={zb:f=>{a.push(b);b=f},end:()=>b=a.pop(),Pb:f=>{if(b){if(!c.kc(f))throw Error("Only subscribable things can act as dependencies");b.Yb.call(b.Zb,f,f.Vb||(f.Vb=++d))}},M:(f,k,l)=>{try{return a.push(b),b=void 0,f.apply(k,l||[])}finally{b=a.pop()}},qa:()=>b?.u.qa(),Ia:()=>b?.Ia,u:()=>b?.u}})();const B=Symbol("_latestValue");c.ba=a=>{function b(){if(0<arguments.length)return b.Ha(b[B],arguments[0])&&(b.ob(),b[B]=
arguments[0],b.Oa()),this;c.o.Pb(b);return b[B]}b[B]=a;Object.defineProperty(b,"length",{get:()=>null==b[B]?void 0:b[B].length});c.V.fn.Fa(b);return Object.setPrototypeOf(b,F)};var F={toJSON:function(){let a=this[B];return a?.toJSON?.()||a},pa:P,R:function(){return this[B]},Oa:function(){this.D(this[B],"spectate");this.D(this[B])},ob:function(){this.D(this[B],"beforeChange")}};Object.setPrototypeOf(F,c.V.fn);var G=c.ba.qc="__ko_proto__";F[G]=c.ba;c.T=a=>{if((a="function"==typeof a&&a[G])&&a!==F[G]&&
a!==c.u.fn[G])throw Error("Invalid object that looks like an observable; possibly from another Knockout instance");return!!a};c.lc=a=>"function"==typeof a&&(a[G]===F[G]||a[G]===c.u.fn[G]&&a.hc);c.v("observable",c.ba);c.v("isObservable",c.T);c.v("observable.fn",F);c.ha(F,"valueHasMutated",F.Oa);c.ta=a=>{a=a||[];if("object"!=typeof a||!("length"in a))throw Error("The argument passed when initializing an observable array must be an array, or null, or undefined.");return Object.setPrototypeOf(c.ba(a),
c.ta.fn).extend({trackArrayChanges:!0})};c.ta.fn=Object.setPrototypeOf({remove:function(a){for(var b=this.R(),d=!1,f="function"!=typeof a||c.T(a)?e=>e===a:a,k=b.length;k--;){var l=b[k];if(f(l)){if(b[k]!==l)throw Error("Array modified during remove; cannot remove item");d||this.ob();d=!0;b.splice(k,1)}}d&&this.Oa()}},c.ba.fn);Object.getOwnPropertyNames(Array.prototype).forEach(a=>{"function"===typeof Array.prototype[a]&&"constructor"!=a&&("copyWithin fill pop push reverse shift sort splice unshift".split(" ").includes(a)?
c.ta.fn[a]=function(...b){var d=this.R();this.ob();this.Bb(d,a,b);b=d[a](...b);this.Oa();return b===d?this:b}:c.ta.fn[a]=function(...b){return this()[a](...b)})});c.Jb=a=>c.T(a)&&"function"==typeof a.remove&&"function"==typeof a.push;c.v("observableArray",c.ta);c.v("isObservableArray",c.Jb);c.eb.trackArrayChanges=(a,b)=>{function d(){function m(){if(g){var r=[].concat(a.R()||[]);if(a.ra("arrayChange")){if(!k||1<g)k=c.g.Cb(h,r,a.Wa);var q=k}h=r;k=null;g=0;q?.length&&a.D(q,"arrayChange")}}f?m():(f=
!0,e=a.subscribe(()=>++g,null,"spectate"),h=[].concat(a.R()||[]),k=null,l=a.subscribe(m))}a.Wa={};"object"==typeof b&&c.g.extend(a.Wa,b);a.Wa.sparse=!0;if(!a.Bb){var f=!1,k=null,l,e,g=0,h,n=a.Ua,p=a.Sa;a.Ua=m=>{n?.call(a,m);"arrayChange"===m&&d()};a.Sa=m=>{p?.call(a,m);"arrayChange"!==m||a.ra("arrayChange")||(l?.A(),e?.A(),e=l=null,f=!1,h=void 0)};a.Bb=(m,r,q)=>{function t(A,x,I){return u[u.length]={status:A,value:x,index:I}}if(f&&!g){var u=[],w=m.length,v=q.length,z=0;switch(r){case "push":z=w;case "unshift":for(m=
0;m<v;m++)t("added",q[m],z+m);break;case "pop":z=w-1;case "shift":w&&t("deleted",m[z],z);break;case "splice":z=Math.min(Math.max(0,0>q[0]?w+q[0]:q[0]),w);w=1===v?w:Math.min(z+(q[1]||0),w);v=z+v-2;r=Math.max(w,v);for(var C=[],H=[],O=2;z<r;++z,++O)z<w&&H.push(t("deleted",m[z],z)),z<v&&C.push(t("added",q[O],z));c.g.Hb(H,C);break;default:return}k=u}}}};var y=Symbol("_state");c.u=(a,b)=>{function d(){if(0<arguments.length){if("function"!==typeof f)throw Error("Cannot write a value to a ko.computed unless you specify a 'write' option. If you wish to read the current value, don't pass any parameters.");
f(...arguments);return this}k.$||c.o.Pb(d);(k.Y||k.C&&d.sa())&&d.U();return k.N}"object"===typeof a?b=a:(b=b||{},a&&(b.read=a));if("function"!=typeof b.read)throw Error("Pass a function that returns the value of the ko.computed");var f=b.write,k={N:void 0,aa:!0,Y:!0,Ga:!1,nb:!1,$:!1,jb:!1,C:!1,Ob:b.read,s:b.disposeWhenNodeIsRemoved||b.s||null,na:b.disposeWhen||b.na,ab:null,B:{},J:0,Gb:null};d[y]=k;d.hc="function"===typeof f;c.V.fn.Fa(d);Object.setPrototypeOf(d,J);b.pure&&(k.jb=!0,k.C=!0,c.g.extend(d,
la));k.s&&(k.nb=!0,k.s.nodeType||(k.s=null));k.C||d.U();k.s&&d.isActive()&&c.g.K.ma(k.s,k.ab=()=>{d.A()});return d};var J={pa:P,qa:function(){return this[y].J},dc:function(){var a=[];c.g.P(this[y].B,(b,d)=>a[d.ka]=d.X);return a},gb:function(a){if(!this[y].J)return!1;var b=this.dc();return b.includes(a)||!!b.find(d=>d.gb&&d.gb(a))},vb:function(a,b,d){if(this[y].jb&&b===this)throw Error("A 'pure' computed must not be called recursively");this[y].B[a]=d;d.ka=this[y].J++;d.la=b.Ca()},sa:function(){var a,
b=this[y].B;for(a in b)if(Object.prototype.hasOwnProperty.call(b,a)){var d=b[a];if(this.va&&d.X.ja||d.X.fc(d.la))return!0}},vc:function(){this[y].Ga||this.va?.(!1)},isActive:function(){var a=this[y];return a.Y||0<a.J},wc:function(){this.ja?this[y].Y&&(this[y].aa=!0):this.Fb()},Sb:function(a){return a.subscribe(this.Fb,this)},Fb:function(){var a=this,b=a.throttleEvaluation;0<=b?(clearTimeout(this[y].Gb),this[y].Gb=setTimeout(()=>a.U(!0),b)):a.va?a.va(!0):a.U(!0)},U:function(a){var b=this[y],d=b.na,
f=!1;if(!b.Ga&&!b.$){if(b.s&&!c.g.bb(b.s)||d?.()){if(!b.nb){this.A();return}}else b.nb=!1;try{b.Ga=!0,f=this.bc(a)}finally{b.Ga=!1}return f}},bc:function(a){var b=this[y],d=b.jb?void 0:!b.J;var f={$b:this,za:b.B,Za:b.J};c.o.zb({Zb:f,Yb:ia,u:this,Ia:d});b.B={};b.J=0;a:{try{var k=b.Ob();break a}finally{c.o.end(),f.Za&&!b.C&&c.g.P(f.za,ha),b.aa=b.Y=!1}k=void 0}b.J?f=this.Ha(b.N,k):(this.A(),f=!0);f&&(b.C?this.Na():this.D(b.N,"beforeChange"),b.N=k,this.D(b.N,"spectate"),!b.C&&a&&this.D(b.N),this.tb&&
this.tb());d&&this.D(b.N,"awake");return f},R:function(a){var b=this[y];(b.Y&&(a||!b.J)||b.C&&this.sa())&&this.U();return b.N},Ja:function(a){var b=this;c.V.fn.Ja.call(b,a);b.qb=()=>{b[y].C||(b[y].aa?b.U():b[y].Y=!1);return b[y].N};b.va=d=>{b.rb(b[y].N);b[y].Y=!0;d&&(b[y].aa=!0);b.sb(b,!d)}},A:function(){var a=this[y];!a.C&&a.B&&c.g.P(a.B,(b,d)=>d.A?.());a.s&&a.ab&&c.g.K.kb(a.s,a.ab);a.B=void 0;a.J=0;a.$=!0;a.aa=!1;a.Y=!1;a.C=!1;a.s=void 0;a.na=void 0;a.Ob=void 0}},la={Ua:function(a){var b=this,d=
b[y];if(!d.$&&d.C&&"change"==a){d.C=!1;if(d.aa||b.sa())d.B=null,d.J=0,b.U()&&b.Na();else{var f=[];c.g.P(d.B,(k,l)=>f[l.ka]=k);f.forEach((k,l)=>{var e=d.B[k],g=b.Sb(e.X);g.ka=l;g.la=e.la;d.B[k]=g});b.sa()&&b.U()&&b.Na()}d.$||b.D(d.N,"awake")}},Sa:function(a){var b=this[y];b.$||"change"!=a||this.ra("change")||(c.g.P(b.B,(d,f)=>{f.A&&(b.B[d]={X:f.X,ka:f.ka,la:f.la},f.A())}),b.C=!0,this.D(void 0,"asleep"))},Ca:function(){var a=this[y];a.C&&(a.aa||this.sa())&&this.U();return c.V.fn.Ca.call(this)}};Object.setPrototypeOf(J,
c.V.fn);var S=c.ba.qc;J[S]=c.u;c.v("computed",c.u);c.v("isComputed",a=>"function"==typeof a&&a[S]===J[S]);c.v("computed.fn",J);c.ha(J,"dispose",J.A);c.Nb=a=>{if("function"===typeof a)return c.u(a,{pure:!0});a={...a,pure:!0};return c.u(a)};c.F={S:a=>{switch(a.nodeName){case "OPTION":return!0===a.__ko__hasDomDataOptionValue__?c.g.j.get(a,c.h.options.ib):a.value;case "SELECT":return 0<=a.selectedIndex?c.F.S(a.options[a.selectedIndex]):void 0;default:return a.value}},Pa:(a,b,d)=>{switch(a.nodeName){case "OPTION":"string"===
typeof b?(c.g.j.set(a,c.h.options.ib,void 0),delete a.__ko__hasDomDataOptionValue__,a.value=b):(c.g.j.set(a,c.h.options.ib,b),a.__ko__hasDomDataOptionValue__=!0,a.value="number"===typeof b?b:"");break;case "SELECT":for(var f=-1,k=""===b||null==b,l=a.options.length,e;l--;)if(e=c.F.S(a.options[l]),e==b||""===e&&k){f=l;break}if(d||0<=f||k&&1<a.size)a.selectedIndex=f;break;default:a.value=null==b?"":b}}};c.G=(()=>{var a=["true","false","null","undefined"],b=/^(?:[$_a-z][$\w]*|(.+)(\.\s*[$_a-z][$\w]*|\[.+\]))$/i,
d=RegExp("\"(?:\\\\.|[^\"])*\"|'(?:\\\\.|[^'])*'|`(?:\\\\.|[^`])*`|/\\*(?:[^*]|\\*+[^*/])*\\*+/|//.*\n|/(?:\\\\.|[^/])+/w*|[^\\s:,/][^,\"'`{}()/:[\\]]*[^\\s,\"'`{}()/:[\\]]|[^\\s]","g"),f=/[\])"'A-Za-z0-9_$]+$/,k={"in":1,"return":1,"typeof":1},l=g=>{g=c.g.Rb(g);123===g.charCodeAt(0)&&(g=g.slice(1,-1));g+="\n,";var h=[],n=g.match(d),p=[],m=0;if(1<n.length){for(var r=0,q;q=n[r++];){var t=q.charCodeAt(0);if(44===t){if(0>=m){h.push(u&&p.length?{key:u,value:p.join("")}:{unknown:u||p.join("")});var u=m=
0;p=[];continue}}else if(58===t){if(!m&&!u&&1===p.length){u=p.pop();continue}}else if(47===t&&1<q.length&&(47===q.charCodeAt(1)||42===q.charCodeAt(1)))continue;else 47===t&&r&&1<q.length?(t=n[r-1].match(f))&&!k[t[0]]&&(g=g.slice(g.indexOf(q)+1),n=g.match(d),r=-1,q="/"):40===t||123===t||91===t?++m:41===t||125===t||93===t?--m:u||p.length||34!==t&&39!==t||(q=q.slice(1,-1));p.push(q)}if(0<m)throw Error("Unbalanced parentheses, braces, or brackets");}return h},e=new Set;return{Va:[],Ma:e,oc:l,pc:(g,h)=>
{var n=[],p=[],m=h?.valueAccessors,r=h?.bindingParams,q=(t,u)=>{if(!r){var w=c.h[t];if(w?.preprocess&&!(u=w.preprocess(u,t,q)))return;if(w=e.has(t)){var v=u;a.includes(v)?v=!1:(w=v.match(b),v=null===w?!1:w[1]?"Object("+w[1]+")"+w[2]:v);w=v}w&&p.push("'"+t+"':function(_z){"+v+"=_z}")}m&&(u="function(){return "+u+" }");n.push("'"+t+"':"+u)};("string"===typeof g?l(g):g).forEach(t=>q(t.key||t.unknown,t.value));p.length&&q("_ko_property_writers","{"+p.join(",")+" }");return n.join(",")},mc:(g,h)=>-1<g.findIndex(n=>
n.key==h),Qa:(g,h,n,p,m)=>{if(g&&c.T(g))!c.lc(g)||m&&g.R()===p||g(p);else h.get("_ko_property_writers")?.[n]?.(p)}}})();(()=>{function a(e){return 8==e.nodeType&&f.test(e.nodeValue)}function b(e){return 8==e.nodeType&&k.test(e.nodeValue)}function d(e,g){for(var h=e,n=1,p=[];h=h.nextSibling;){if(b(h)&&(c.g.j.set(h,l,!0),!--n))return p;p.push(h);a(h)&&++n}if(!g)throw Error("Cannot find closing comment tag to match: "+e.nodeValue);return null}var f=/^\s*ko(?:\s+([\s\S]+))?\s*$/,k=/^\s*\/ko\s*$/,l="__ko_matchedEndComment__";
c.m={ca:{},childNodes:e=>a(e)?d(e):e.childNodes,oa:e=>{a(e)?(e=d(e))&&[...e].forEach(g=>c.removeNode(g)):c.g.cb(e)},ua:(e,g)=>{a(e)?(c.m.oa(e),e.after(...g)):c.g.ua(e,g)},prepend:(e,g)=>{a(e)?e.nextSibling.before(g):e.prepend(g)},jc:(e,g,h)=>{h?h.after(g):c.m.prepend(e,g)},firstChild:e=>{if(a(e))return e=e.nextSibling,!e||b(e)?null:e;let g=e.firstChild;if(g&&b(g))throw Error("Found invalid end comment, as the first child of "+e);return g},nextSibling:e=>{if(a(e)){var g=d(e,void 0);e=g?(g.length?g[g.length-
1]:e).nextSibling:null}if((g=e.nextSibling)&&b(g)){if(b(g)&&!c.g.j.get(g,l))throw Error("Found end comment without a matching opening comment, as child of "+e);return null}return g},ec:a,uc:e=>(e=e.nodeValue.match(f))?e[1]:null}})();const ba=new Map;c.Ab=new class{nc(a){switch(a.nodeType){case 1:return null!=a.getAttribute("data-bind");case 8:return c.m.ec(a)}return!1}cc(a,b){a:{switch(a.nodeType){case 1:var d=a.getAttribute("data-bind");break a;case 8:d=c.m.uc(a);break a}d=null}if(d)try{let k={valueAccessors:!0},
l=ba.get(d);if(!l){var f="with($context){with($data||{}){return{"+c.G.pc(d,k)+"}}}";l=new Function("$context","$element",f);ba.set(d,l)}return l(b,a)}catch(k){throw k.message="Unable to parse bindings.\nBindings value: "+d+"\nMessage: "+k.message,k;}return null}};const L=Symbol("_subscribable"),N=Symbol("_ancestorBindingInfo"),aa=Symbol("_dataDependency"),ca={},K=c.g.j.Z();c.h={};c.ea=class{constructor(a,b,d,f,k){var l=this,e=a===ca,g=e?void 0:a,h="function"==typeof g&&!c.T(g),n=k?.dataDependency;
a=()=>{var m=h?g():g,r=c.g.i(m);b?(c.g.extend(l,b),N in b&&(l[N]=b[N])):(l.$parents=[],l.$root=r,l.ko=c);l[L]=p;e?r=l.$data:(l.$rawData=m,l.$data=r);d&&(l[d]=r);f?.(l,b,r);if(b?.[L]&&!c.o.u().gb(b[L]))b[L]();n&&(l[aa]=n);return l.$data};if(k?.exportDependencies)a();else{var p=c.Nb(a);p.R();p.isActive()?p.pa=null:l[L]=void 0}}createChildContext(a,b,d,f){!f&&b&&"object"==typeof b&&(f=b,b=f.as,d=f.extend);return new c.ea(a,this,b,(k,l)=>{k.$parentContext=l;k.$parent=l.$data;k.$parents=(l.$parents||[]).slice(0);
k.$parents.unshift(k.$parent);d&&d(k)},f)}extend(a,b){return new c.ea(ca,this,null,d=>c.g.extend(d,"function"==typeof a?a(d):a),b)}};class ma{constructor(a,b,d){this.L=a;this.ia=b;this.xa=new Set;this.H=!1;b.I||c.g.K.ma(a,W);d?.I&&(d.I.xa.add(a),this.Da=d)}Mb(){this.Da?.I?.ac(this.L)}ac(a){this.xa.delete(a);this.xa.size||this.Db?.()}Db(){this.H=!0;this.ia.I&&!this.xa.size&&(this.ia.I=null,c.g.K.kb(this.L,W),c.l.notify(this.L,c.l.ga),this.Mb())}}c.l={H:"childrenComplete",ga:"descendantsComplete",subscribe:(a,
b,d,f,k)=>{var l=c.g.j.fb(a,K,{});l.Aa||(l.Aa=new c.V);k?.notifyImmediately&&l.hb[b]&&c.o.M(d,f,[a]);return l.Aa.subscribe(d,f,b)},notify:(a,b)=>{var d=c.g.j.get(a,K);if(d&&(d.hb[b]=!0,d.Aa?.D(a,b),b==c.l.H))if(d.I)d.I.Db();else if(void 0===d.I&&d.Aa?.ra(c.l.ga))throw Error("descendantsComplete event not supported for bindings on this node");},mb:(a,b)=>{var d=c.g.j.fb(a,K,{});d.I||(d.I=new ma(a,d,b[N]));return b[N]==d?b:b.extend(f=>{f[N]=d})}};c.tc=a=>(a=c.g.j.get(a,K))&&a.context;c.wb=(a,b,d)=>
Z(a,b,Q(d));c.yb=(a,b)=>{1!==b.nodeType&&8!==b.nodeType||X(Q(a),b)};c.xb=function(a,b,d){if(2>arguments.length){if(b=M.body,!b)throw Error("ko.applyBindings: could not find document.body; has the document been loaded?");}else if(!b||1!==b.nodeType&&8!==b.nodeType)throw Error("ko.applyBindings: first parameter should be your view model; second parameter should be a DOM node");Y(Q(a,d),b)};c.Eb=a=>(a=a&&[1,8].includes(a.nodeType)&&c.tc(a))?a.$data:void 0;c.v("bindingHandlers",c.h);c.v("applyBindings",
c.xb);c.v("applyBindingAccessorsToNode",c.wb);c.v("dataFor",c.Eb);(()=>{var a=Object.create(null),b=new Map;c.Xa={get:(l,e)=>{if(b.has(l))e(b.get(l));else{var g=a[l];g?g.subscribe(e):(g=a[l]=new c.V,g.subscribe(e),k(l,h=>{b.set(l,h);delete a[l];g.D(h)}))}},register:(l,e)=>{if(!e)throw Error("Invalid configuration for "+l);if(d[l])throw Error("Component "+l+" is already registered");d[l]=e}};var d=Object.create(null),f=(l,e)=>{throw Error(`Component '${l}': ${e}`);},k=(l,e)=>{var g={},h=d[l]||{},n=
h.template;h=h.viewModel;if(n){n.element||f(l,"Unknown template value: "+n);n=n.element;var p=M.getElementById(n);p||f(l,"Cannot find element with ID "+n);p.matches("TEMPLATE")||f(l,"Template Source Element not a <template>");g.template=c.g.ya(p.content.childNodes)}h&&("function"!==typeof h.createViewModel&&f(l,"Unknown viewModel value: "+h),g.createViewModel=h.createViewModel);e(g.template&&g.createViewModel?g:null)};c.v("components",c.Xa);c.v("components.register",c.Xa.register)})();(()=>{var a=
0;c.h.component={init:(b,d,f,k,l)=>{var e,g,h,n=()=>{var m=e&&e.dispose;"function"===typeof m&&m.call(e);h&&h.A();g=e=h=null},p=[...c.m.childNodes(b)];c.m.oa(b);c.g.K.ma(b,n);c.u(()=>{var m=c.g.i(d());if("string"!==typeof m){var r=c.g.i(m.params);m=c.g.i(m.name)}if(!m)throw Error("No component name specified");var q=c.l.mb(b,l),t=g=++a;c.Xa.get(m,u=>{if(g===t){n();if(!u)throw Error("Unknown component '"+m+"'");var w=u.template;if(!w)throw Error("Component '"+m+"' has no template");c.m.ua(b,c.g.ya(w));
e=u.createViewModel(r,{element:b,templateNodes:p});c.yb(q.createChildContext(e,{extend:v=>{v.$component=e;v.$componentTemplateNodes=p}}),b)}})},{s:b});return{controlsDescendantBindings:!0}}};c.m.ca.component=!0})();c.h.attr={update:(a,b)=>{b=c.g.i(b())||{};c.g.P(b,function(d,f){f=c.g.i(f);var k=d.indexOf(":");k="lookupNamespaceURI"in a&&0<k&&a.lookupNamespaceURI(d.slice(0,k));var l=!1===f||null==f;l?k?a.removeAttributeNS(k,d):a.removeAttribute(d):(f=f.toString(),k?a.setAttributeNS(k,d,f):a.setAttribute(d,
f));"name"===d&&(a.name=l?"":f)})}};(()=>{c.h.checked={after:["value","attr"],init:function(a,b,d){var f="checkbox"==a.type,k="radio"==a.type;if(f||k){const l=c.Nb(()=>{if(k)return d.has("value")?c.g.i(d.get("value")):a.value});a.addEventListener("click",()=>{if(!c.o.Ia()){var e=a.checked;if(e||!k&&!c.o.qa()){e=f?e:l();var g=c.o.M(b);c.G.Qa(g,d,"checked",e,!0)}}});c.u(()=>{var e=c.g.i(b());a.checked=f?!!e:l()===e},null,{s:a})}}};c.G.Ma.checked=!0})();var T=(a,b,d)=>b&&b.split(/\s+/).forEach(f=>a.classList.toggle(f,
d));c.h.css={update:(a,b)=>{b=c.g.i(b());"object"==typeof b?c.g.P(b,(d,f)=>{f=c.g.i(f);T(a,d,!!f)}):(b=c.g.Rb(b),T(a,a.__ko__cssValue,!1),a.__ko__cssValue=b,T(a,b,!0))}};c.h.enable={update:(a,b)=>{(b=c.g.i(b()))&&a.disabled?a.removeAttribute("disabled"):b||a.disabled||(a.disabled=!0)}};c.h.disable={update:(a,b)=>c.h.enable.update(a,()=>!c.g.i(b()))};c.h.event={init:(a,b,d,f,k)=>{c.g.P(b()||{},l=>{"string"==typeof l&&a.addEventListener(l,(...e)=>{var g=b()[l];if(g)try{f=k.$data;var h=g.apply(f,[f,
...e])}finally{!0!==h&&e[0].preventDefault()}})})}};c.h.foreach={Kb:a=>()=>{var b=a(),d=c.T(b)?b.R():b;if(!d||"number"==typeof d.length)return{foreach:b};c.g.i(b);return{foreach:d.data,as:d.as,beforeRemove:d.beforeRemove}},init:(a,b)=>c.h.template.init(a,c.h.foreach.Kb(b)),update:(a,b,d,f,k)=>c.h.template.update(a,c.h.foreach.Kb(b),d,f,k)};c.G.Va.foreach=!1;c.m.ca.foreach=!0;c.h.hasfocus={init:(a,b,d)=>{var f=l=>{a.__ko_hasfocusUpdating=!0;l=a.ownerDocument.activeElement===a;c.G.Qa(b(),d,"hasfocus",
l,!0);a.__ko_hasfocusLastValue=l;a.__ko_hasfocusUpdating=!1},k=f.bind(null,!0);f=f.bind(null,!1);a.addEventListener("focus",k);a.addEventListener("focusin",k);a.addEventListener("blur",f);a.addEventListener("focusout",f);a.__ko_hasfocusLastValue=!1},update:(a,b)=>{b=!!c.g.i(b());a.__ko_hasfocusUpdating||a.__ko_hasfocusLastValue===b||(b?a.focus():a.blur())}};c.G.Ma.add("hasfocus");c.h.html={init:()=>({controlsDescendantBindings:!0}),update:(a,b)=>{c.g.cb(a);b=c.g.i(b());if(null!=b){const d=M.createElement("template");
d.innerHTML="string"!=typeof b?b.toString():b;a.appendChild(d.content)}}};(()=>{function a(b,d,f){c.h[b]={init:(k,l,e,g,h)=>{var n,p={};d&&(p={as:e.get("as"),exportDependencies:!0});var m=e.has(c.l.ga);c.u(()=>{var r=c.g.i(l()),q=!f!==!r,t=!n;m&&(h=c.l.mb(k,h));if(q){p.dataDependency=c.o.u();var u=d?h.createChildContext("function"==typeof r?r:l,p):c.o.qa()?h.extend(null,p):h}t&&c.o.qa()&&(n=c.g.ya(c.m.childNodes(k),!0));q?(t||c.m.ua(k,c.g.ya(n)),c.yb(u,k)):(c.m.oa(k),c.l.notify(k,c.l.H))},{s:k});
return{controlsDescendantBindings:!0}}};c.G.Va[b]=!1;c.m.ca[b]=!0}a("if");a("ifnot",!1,!0);a("with",!0)})();var U={};c.h.options={init:a=>{if(!a.matches("SELECT"))throw Error("options binding applies only to SELECT elements");let b=a.length;for(;b--;)a.remove(b);return{controlsDescendantBindings:!0}},update:(a,b,d)=>{var f=a.multiple,k=0!=a.length&&f?a.scrollTop:null,l=c.g.i(b()),e=d.get("valueAllowUnset")&&d.has("value"),g={},h=[];b=()=>Array.from(a.options).filter(q=>q.selected);var n=(q,t,u)=>
{var w=typeof t;return"function"==w?t(q):"string"==w?q[t]:u},p=(q,t)=>{r&&e?c.l.notify(a,c.l.H):h.length&&(q=h.includes(c.F.S(t[0])),t[0].selected=q,r&&!q&&c.o.M(c.g.Tb,null,[a,"change"]))};e||(f?h=b().map(c.F.S):0<=a.selectedIndex&&h.push(c.F.S(a.options[a.selectedIndex])));if(l){"undefined"==typeof l.length&&(l=[l]);var m=l.filter(q=>q||null==q);d.has("optionsCaption")&&(l=c.g.i(d.get("optionsCaption")),null!=l&&m.unshift(U))}var r=!1;g.beforeRemove=q=>a.removeChild(q);l=p;d.has("optionsAfterRender")&&
"function"==typeof d.get("optionsAfterRender")&&(l=(q,t)=>{p(q,t);c.o.M(d.get("optionsAfterRender"),null,[t[0],q!==U?q:void 0])});c.g.Qb(a,m,(q,t,u)=>{u.length&&(h=!e&&u[0].selected?[c.F.S(u[0])]:[],r=!0);t=a.ownerDocument.createElement("option");q===U?(c.g.lb(t,d.get("optionsCaption")),c.F.Pa(t,void 0)):(u=n(q,d.get("optionsValue"),q),c.F.Pa(t,c.g.i(u)),q=n(q,d.get("optionsText"),u),c.g.lb(t,q));return[t]},g,l);e||(m=h.length,(f?m&&b().length<m:m&&0<=a.selectedIndex?c.F.S(a.options[a.selectedIndex])!==
h[0]:m||0<=a.selectedIndex)&&c.o.M(c.g.Tb,null,[a,"change"]));(e||c.o.Ia())&&c.l.notify(a,c.l.H);k&&20<Math.abs(k-a.scrollTop)&&(a.scrollTop=k)}};c.h.options.ib=c.g.j.Z();c.h.style={update:(a,b)=>{c.g.P(c.g.i(b()||{}),(d,f)=>{f=c.g.i(f);if(null==f||!1===f)f="";if(/^--/.test(d))a.style.setProperty(d,f);else{d=d.replace(/-(\w)/g,(l,e)=>e.toUpperCase());var k=a.style[d];a.style[d]=f;f===k||a.style[d]!=k||isNaN(f)||(a.style[d]=f+"px")}})}};c.h.submit={init:(a,b,d,f,k)=>{if("function"!=typeof b())throw Error("The value for a submit binding must be a function");
a.addEventListener("submit",l=>{var e=b();try{var g=e.call(k.$data,a)}finally{!0!==g&&l.preventDefault()}})}};c.h.text={init:()=>({controlsDescendantBindings:!0}),update:(a,b)=>{8===a.nodeType&&(a.text||a.after(a.text=M.createTextNode("")),a=a.text);c.g.lb(a,b())}};c.m.ca.text=!0;c.h.textInput={init:(a,b,d)=>{var f=a.value,k,l,e=()=>{clearTimeout(k);l=k=void 0;var h=a.value;f!==h&&(f=h,c.G.Qa(b(),d,"textInput",h))},g=()=>{var h=c.g.i(b());null==h&&(h="");void 0!==l&&h===l?setTimeout(g,4):a.value!==
h&&(a.value=h,f=a.value)};a.addEventListener("input",e);a.addEventListener("change",e);a.addEventListener("blur",e);c.u(g,{s:a})}};c.G.Ma.add("textInput");c.h.textinput={preprocess:(a,b,d)=>d("textInput",a)};c.h.value={init:(a,b,d)=>{var f=a.matches("SELECT"),k=a.matches("INPUT");if(!k||"checkbox"!=a.type&&"radio"!=a.type){var l=new Set,e=d.get("valueUpdate"),g=null,h=()=>{g=null;var m=b(),r=c.F.S(a);c.G.Qa(m,d,"value",r)};e&&("string"==typeof e?l.add(e):e.forEach(m=>l.add(m)),l.delete("change"));
l.forEach(m=>{var r=h;(m||"").startsWith("after")&&(r=()=>{g=c.F.S(a);setTimeout(h,0)},m=m.slice(5));a.addEventListener(m,r)});var n=k&&"file"==a.type?()=>{var m=c.g.i(b());null==m||""===m?a.value="":c.o.M(h)}:()=>{var m=c.g.i(b()),r=c.F.S(a);if(null!==g&&m===g)setTimeout(n,0);else if(m!==r||void 0===r)f?(r=d.get("valueAllowUnset"),c.F.Pa(a,m,r),r||m===c.F.S(a)||c.o.M(h)):c.F.Pa(a,m)};if(f){var p;c.l.subscribe(a,c.l.H,()=>{p?d.get("valueAllowUnset")?n():h():(a.addEventListener("change",h),p=c.u(n,
{s:a}))},null,{notifyImmediately:!0})}else a.addEventListener("change",h),c.u(n,{s:a})}else c.wb(a,{checkedValue:b})},update:()=>{}};c.G.Ma.add("value");c.h.visible={update:(a,b)=>{b=c.g.i(b());var d="none"!=a.style.display;b&&!d?a.style.display="":d&&!b&&(a.style.display="none")}};c.h.hidden={update:(a,b)=>a.hidden=!!c.g.i(b())};(function(a){c.h[a]={init:function(b,d,f,k,l){return c.h.event.init.call(this,b,()=>({[a]:d()}),f,k,l)}}})("click");(()=>{let a=c.g.j.Z();class b{constructor(f){this.$a=
f}Ka(...f){let k=this.$a;if(!f.length)return c.g.j.get(k,a)||(11===this.L?k.content:1===this.L?k:void 0);c.g.j.set(k,a,f[0])}}class d extends b{constructor(f){super(f);f&&(this.L=f.matches("TEMPLATE")&&f.content?f.content.nodeType:1)}}c.La={$a:d,Ta:b}})();(()=>{var a=(e,g,h)=>{var n;for(g=c.m.nextSibling(g);e&&(n=e)!==g;)e=c.m.nextSibling(n),h(n,e)},b=(e,g)=>{if(e.length){var h=e[0],n=h.parentNode;a(h,e[e.length-1],p=>{1!==p.nodeType&&8!==p.nodeType||c.xb(g,p)});c.g.Ba(e,n)}},d=(e,g,h,n)=>{var p=
(e&&(e.nodeType?e:0<e.length?e[0]:null)||h||{}).ownerDocument;if("string"==typeof h){p=p||M;p=p.getElementById(h);if(!p)throw Error("Cannot find template with ID "+h);h=new c.La.$a(p)}else if([1,8].includes(h.nodeType))h=new c.La.Ta(h);else throw Error("Unknown template type: "+h);h=(h=h.Ka?h.Ka():null)?[...h.cloneNode(!0).childNodes]:null;if("number"!=typeof h.length||0<h.length&&"number"!=typeof h[0].nodeType)throw Error("Template engine must return an array of DOM nodes");p=!1;switch(g){case "replaceChildren":c.m.ua(e,
h);p=!0;break;case "ignoreTargetNode":break;default:throw Error("Unknown renderMode: "+g);}p&&(b(h,n),"replaceChildren"==g&&c.l.notify(e,c.l.H));return h},f=(e,g,h)=>c.T(e)?e():"function"===typeof e?e(g,h):e;c.rc=function(e,g,h,n){h=h||{};var p=p||"replaceChildren";if(n){var m=n.nodeType?n:0<n.length?n[0]:null;return c.u(()=>{var r=g instanceof c.ea?g:new c.ea(g,null,null,null,{exportDependencies:!0}),q=f(e,r.$data,r);d(n,p,q,r,h)},{na:()=>!m||!c.g.bb(m),s:m})}console.log("no targetNodeOrNodeArray")};
c.sc=(e,g,h,n,p)=>{function m(v,z){c.o.M(c.g.Qb,null,[n,v,t,h,u,z]);c.l.notify(n,c.l.H)}var r,q=h.as,t=(v,z)=>{r=p.createChildContext(v,{as:q,extend:C=>{C.$index=z;q&&(C[q+"Index"]=z)}});v=f(e,v,r);return d(n,"ignoreTargetNode",v,r,h)},u=(v,z)=>{b(z,r);r=null};if(!h.beforeRemove&&c.Jb(g)){m(g.R());var w=g.subscribe(v=>{m(g(),v)},null,"arrayChange");w.s(n);return w}return c.u(()=>{var v=c.g.i(g)||[];"undefined"==typeof v.length&&(v=[v]);m(v)},{s:n})};var k=c.g.j.Z(),l=c.g.j.Z();c.h.template={init:(e,
g)=>{g=c.g.i(g());if("string"==typeof g||"name"in g)c.m.oa(e);else if("nodes"in g){g=g.nodes||[];if(c.T(g))throw Error('The "nodes" option must be a plain, non-observable array.');let h=g[0]?.parentNode;h&&c.g.j.get(h,l)||(h=c.g.Lb(g),c.g.j.set(h,l,!0));(new c.La.Ta(e)).Ka(h)}else if(g=c.m.childNodes(e),g.length)g=c.g.Lb(g),(new c.La.Ta(e)).Ka(g);else throw Error("Anonymous template defined, but no template content was provided");return{controlsDescendantBindings:!0}},update:(e,g,h,n,p)=>{var m=g();
g=c.g.i(m);h=!0;n=null;"string"==typeof g?g={}:(m="name"in g?g.name:e,"if"in g&&(h=c.g.i(g["if"])),h&&"ifnot"in g&&(h=!c.g.i(g.ifnot)),h&&!m&&(h=!1));"foreach"in g?n=c.sc(m,h&&g.foreach||[],g,e,p):h?(h=p,"data"in g&&(h=p.createChildContext(g.data,{as:g.as,exportDependencies:!0})),n=c.rc(m,h,g,e)):c.m.oa(e);p=n;c.g.j.get(e,k)?.A?.();c.g.j.set(e,k,!p||p.isActive&&!p.isActive()?void 0:p)}};c.G.Va.template=e=>{e=c.G.oc(e);return 1==e.length&&e[0].unknown||c.G.mc(e,"name")?null:"This template engine does not support anonymous templates nested within its templates"};
c.m.ca.template=!0})();c.g.Hb=(a,b,d)=>{var f=0,k,l=b.length;l&&a.every(e=>{k=b.findIndex(g=>e.value===g.value);0<=k&&(e.moved=b[k].index,b[k].moved=e.index,b.splice(k,1),f=k=0,--l);f+=l;return l&&(!d||f<d)})};c.g.Cb=(()=>{var a=(b,d,f,k,l)=>{for(var e=Math.min,g=Math.max,h=[],n=-1,p=b.length,m,r=d.length,q=r-p||1,t=p+r+1,u,w,v;++n<=p;)for(w=u,h.push(u=[]),v=e(r,n+q),m=g(0,n-1);m<=v;m++)u[m]=m?n?b[n-1]===d[m-1]?w[m-1]:e(w[m]||t,u[m-1]||t)+1:m+1:n+1;e=[];g=[];q=[];n=p;for(m=r;n||m;)r=h[n][m]-1,m&&
r===h[n][m-1]?g.push(e[e.length]={status:f,value:d[--m],index:m}):n&&r===h[n-1][m]?q.push(e[e.length]={status:k,value:b[--n],index:n}):(--m,--n,l.sparse||e.push({status:"retained",value:d[m]}));c.g.Hb(q,g,!l.dontLimitMoves&&10*p);return e.reverse()};return(b,d,f)=>{f="boolean"===typeof f?{dontLimitMoves:f}:f||{};b=b||[];d=d||[];return b.length<d.length?a(b,d,"added","deleted",f):a(d,b,"deleted","added",f)}})();(()=>{function a(f,k,l,e,g){var h=[],n=c.u(()=>{var p=k(l,g,c.g.Ba(h,f))||[];if(0<h.length){var m=
h.nodeType?[h]:h;if(0<m.length){var r=m[0],q=r.parentNode;p.forEach(t=>q.insertBefore(t,r));m.forEach(t=>c.removeNode(t))}e&&c.o.M(e,null,[l,p,g])}h.length=0;h.push(...p)},{s:f,na:()=>!!h.find(c.g.bb)});return{O:h,Ya:n.isActive()?n:void 0}}var b=c.g.j.Z(),d=c.g.j.Z();c.g.Qb=(f,k,l,e,g,h)=>{k=k||[];"undefined"==typeof k.length&&(k=[k]);e=e||{};var n=c.g.j.get(f,b),p=[],m=0,r=0,q=[],t=[],u=[],w=0,v=x=>{A={da:x,Ea:c.ba(r++)};p.push(A)},z=x=>{A=n[x];A.Ea(r++);c.g.Ba(A.O,f);p.push(A)};if(n){if(!h||n&&
n._countWaitingForRemove)h=c.g.Cb(Array.prototype.map.call(n,E=>E.da),k,{dontLimitMoves:e.dontLimitMoves,sparse:!0});let x,I;for(h.forEach(E=>{x=E.moved;I=E.index;switch(E.status){case "deleted":for(;m<I;)z(m++);void 0===x&&(A=n[m],A.Ya&&(A.Ya.A(),A.Ya=void 0),c.g.Ba(A.O,f).length&&(e.beforeRemove&&(p.push(A),w++,A.da===d?A=null:u[A.Ea.R()]=A),A&&q.push.apply(q,A.O)));m++;break;case "added":for(;r<I;)z(m++);void 0!==x?(t.push(p.length),z(x)):v(E.value)}});r<k.length;)z(m++);p._countWaitingForRemove=
w}else k.forEach(v);c.g.j.set(f,b,p);q.forEach(e.beforeRemove?c.fa:c.removeNode);var C,H,O=x=>{c.m.jc(f,x,H);H=x};h=f.ownerDocument.activeElement;if(t.length)for(;void 0!=(C=t.shift());){var A=p[C];for(H=void 0;C;)if(k=p[--C].O,k?.length){H=k[k.length-1];break}A.O.forEach(O)}p.forEach(x=>{x.O||c.g.extend(x,a(f,l,x.da,g,x.Ea));x.O.forEach(O);!x.ic&&g&&(g(x.da,x.O,x.Ea),x.ic=!0,H=x.O[x.O.length-1])});f.ownerDocument.activeElement!=h&&h?.focus();((x,I)=>{x&&I.forEach(E=>E?.O.forEach(na=>x(na,C,E.da)))})(e.beforeRemove,
u);u.forEach(x=>x&&(x.da=d))}})();V.ko=R})(this);

/* Copyright © 2011-2015 by Neil Jenkins. MIT Licensed. */
/* eslint max-len: 0 */

/**
	TODO: modifyBlocks function doesn't work very good.
	For example you have: UL > LI > [cursor here in text]
	Then create blockquote at cursor, the result is: BLOCKQUOTE > UL > LI
	not UL > LI > BLOCKQUOTE
*/

(doc => {

const
	blockTag = 'DIV',
	DOCUMENT_POSITION_PRECEDING = 2, // Node.DOCUMENT_POSITION_PRECEDING
	ELEMENT_NODE = 1,                // Node.ELEMENT_NODE,
	TEXT_NODE = 3,                   // Node.TEXT_NODE,
	DOCUMENT_FRAGMENT_NODE = 11,     // Node.DOCUMENT_FRAGMENT_NODE,
	SHOW_ELEMENT = 1,                // NodeFilter.SHOW_ELEMENT,
	SHOW_TEXT = 4,                   // NodeFilter.SHOW_TEXT,
	SHOW_ELEMENT_OR_TEXT = 5,

	START_TO_START = 0, // Range.START_TO_START
	START_TO_END = 1,   // Range.START_TO_END
	END_TO_END = 2,     // Range.END_TO_END
	END_TO_START = 3,   // Range.END_TO_START

	ZWS = '\u200B',
	NBSP = '\u00A0',

	win = doc.defaultView,

	ua = navigator.userAgent,

	isMac = /Mac OS X/.test(ua),
	isIOS = /iP(?:ad|hone|od)/.test(ua) || (isMac && !!navigator.maxTouchPoints),

	isWebKit = /WebKit\//.test(ua),

	ctrlKey = isMac ? 'meta-' : 'ctrl-',
	osKey = isMac ? 'metaKey' : 'ctrlKey',

	// Use [^ \t\r\n] instead of \S so that nbsp does not count as white-space
	notWS = /[^ \t\r\n]/,

	indexOf = (array, value) => Array.prototype.indexOf.call(array, value),

	filterAccept = NodeFilter.FILTER_ACCEPT,
/*
	typeToBitArray = {
		// ELEMENT_NODE
		1: 1,
		// ATTRIBUTE_NODE
		2: 2,
		// TEXT_NODE
		3: 4,
		// COMMENT_NODE
		8: 128,
		// DOCUMENT_NODE
		9: 256,
		// DOCUMENT_FRAGMENT_NODE
		11: 1024
	},
*/
	inlineNodeNames = /^(?:#text|A|ABBR|ACRONYM|B|BR|BD[IO]|CITE|CODE|DATA|DEL|DFN|EM|FONT|HR|I|IMG|INPUT|INS|KBD|Q|RP|RT|RUBY|S|SAMP|SMALL|SPAN|STR(IKE|ONG)|SU[BP]|TIME|U|VAR|WBR)$/,
//	phrasingElements = 'ABBR,AUDIO,B,BDO,BR,BUTTON,CANVAS,CITE,CODE,COMMAND,DATA,DATALIST,DFN,EM,EMBED,I,IFRAME,IMG,INPUT,KBD,KEYGEN,LABEL,MARK,MATH,METER,NOSCRIPT,OBJECT,OUTPUT,PROGRESS,Q,RUBY,SAMP,SCRIPT,SELECT,SMALL,SPAN,STRONG,SUB,SUP,SVG,TEXTAREA,TIME,VAR,VIDEO,WBR',

	leafNodeNames = {
		BR: 1,
		HR: 1,
		IMG: 1
	},

	UNKNOWN = 0,
	INLINE = 1,
	BLOCK = 2,
	CONTAINER = 3,

	isElement = node => node.nodeType === ELEMENT_NODE,
	isLeaf = node => isElement(node) && !!leafNodeNames[ node.nodeName ],

	getNodeCategory = node => {
		switch (node.nodeType) {
		case TEXT_NODE:
			return INLINE;
		case ELEMENT_NODE:
		case DOCUMENT_FRAGMENT_NODE:
			if (nodeCategoryCache.has(node)) {
				return nodeCategoryCache.get(node);
			}
			break;
		default:
			return UNKNOWN;
		}

		let nodeCategory =
			Array.prototype.every.call(node.childNodes, isInline)
			? (inlineNodeNames.test(node.nodeName) ? INLINE : BLOCK)
			// Malformed HTML can have block tags inside inline tags. Need to treat
			// these as containers rather than inline. See #239.
			: CONTAINER;
		nodeCategoryCache.set(node, nodeCategory);
		return nodeCategory;
	},
	isInline = node => getNodeCategory(node) === INLINE,
	isBlock = node => getNodeCategory(node) === BLOCK,
	isContainer = node => getNodeCategory(node) === CONTAINER,
	createTreeWalker = (root, whatToShow, filter) => doc.createTreeWalker(root, whatToShow, filter ? {
			acceptNode: node => filter(node) ? filterAccept : NodeFilter.FILTER_SKIP
		} : null
	),
	getBlockWalker = (node, root) => {
		let walker = createTreeWalker(root, SHOW_ELEMENT, isBlock);
		walker.currentNode = node;
		return walker;
	},
	getPreviousBlock = (node, root) => {
//		node = getClosest(node, root, blockElementNames);
		node = getBlockWalker(node, root).previousNode();
		return node !== root ? node : null;
	},
	getNextBlock = (node, root) => {
//		node = getClosest(node, root, blockElementNames);
		node = getBlockWalker(node, root).nextNode();
		return node !== root ? node : null;
	},

	isEmptyBlock = block => !block.textContent && !block.querySelector('IMG'),

	areAlike = (node, node2) => {
		return !isLeaf(node) && (
			node.nodeType === node2.nodeType &&
			node.nodeName === node2.nodeName &&
			node.nodeName !== 'A' &&
			node.className === node2.className &&
			node.style?.cssText === node2.style?.cssText
		);
	},
	hasTagAttributes = (node, tag, attributes) => {
		return node.nodeName === tag && Object.entries(attributes || {}).every(([k,v]) => node.getAttribute(k) === v);
	},
	getClosest = (node, root, selector) => {
		node = (node && !node.closest) ? node.parentElement : node;
		node = node?.closest(selector);
		return (node && root.contains(node)) ? node : null;
	},
	getNearest = (node, root, tag, attributes) => {
		while (node && node !== root) {
			if (hasTagAttributes(node, tag, attributes)) {
				return node;
			}
			node = node.parentNode;
		}
		return null;
	},

	getPath = (node, root) => {
		let path = '', style;
		if (node && node !== root) {
			path = getPath(node.parentNode, root);
			if (isElement(node)) {
				path += (path ? '>' : '') + node.nodeName;
				if (node.id) {
					path += '#' + node.id;
				}
				if (node.classList.length) {
					path += '.' + [...node.classList].sort().join('.');
				}
				if (node.dir) {
					path += '[dir=' + node.dir + ']';
				}
				if (style = node.style.cssText) {
					path += '[style=' + style + ']';
				}
			}
		}
		return path;
	},

	getLength = node => {
		let nodeType = node.nodeType;
		return nodeType === ELEMENT_NODE || nodeType === DOCUMENT_FRAGMENT_NODE ?
			node.childNodes.length : node.length || 0;
	},

	detach = node => {
//		node.remove();
		node.parentNode?.removeChild(node);
		return node;
	},

	empty = node => {
		let frag = doc.createDocumentFragment(),
			childNodes = node.childNodes;
		childNodes && frag.append(...childNodes);
		return frag;
	},

	setStyle = (node, style) => {
		if (typeof style === 'object') {
			Object.entries(style).forEach(([k,v]) => node.style[k] = v);
		} else if (style !== undefined) {
			node.setAttribute('style', style);
		}
	},

	createElement = (tag, props, children) => {
		let el = doc.createElement(tag);
		if (props instanceof Array) {
			children = props;
			props = null;
		}
		props && Object.entries(props).forEach(([k,v]) => {
			if ('style' === k) {
				setStyle(el, v);
			} else if (v !== undefined) {
				el.setAttribute(k, v);
			}
		});
		children && el.append(...children);
		return el;
	},

	fixCursor = (node, root) => {
		// In Webkit and Gecko, block level elements are collapsed and
		// unfocusable if they have no content (:empty). To remedy this, a <BR> must be
		// inserted. In Opera and IE, we just need a textnode in order for the
		// cursor to appear.
		let self = root.__squire__;
		let originalNode = node;
		let fixer, child;

		if (node === root) {
			if (!(child = node.firstChild) || child.nodeName === 'BR') {
				fixer = self.createDefaultBlock();
				if (child) {
					child.replaceWith(fixer);
				}
				else {
					node.append(fixer);
				}
				node = fixer;
				fixer = null;
			}
		}

		if (node.nodeType === TEXT_NODE) {
			return originalNode;
		}

		if (isInline(node)) {
			child = node.firstChild;
			while (isWebKit && child?.nodeType === TEXT_NODE && !child.data) {
				child.remove();
				child = node.firstChild;
			}
			if (!child) {
				fixer = self._addZWS();
			}
//		} else if (!node.querySelector('BR')) {
//		} else if (!node.innerText.trim().length) {
		} else if (node.matches(':empty')) {
			fixer = createElement('BR');
			while ((child = node.lastElementChild) && !isInline(child)) {
				node = child;
			}
		}
		if (fixer) {
			try {
				node.append(fixer);
			} catch (error) {
				didError({
					name: 'Squire: fixCursor – ' + error,
					message: 'Parent: ' + node.nodeName + '/' + node.innerHTML +
						' appendChild: ' + fixer.nodeName
				});
			}
		}

		return originalNode;
	},

	// Recursively examine container nodes and wrap any inline children.
	fixContainer = (container, root) => {
		let wrapper, isBR;
		// Not live, and fast
		[...container.childNodes].forEach(child => {
			isBR = child.nodeName === 'BR';
			if (!isBR && isInline(child)
//			 && (blockTag !== 'DIV' || (child.matches && !child.matches(phrasingElements)))
			) {
				wrapper = wrapper || createElement('div');
				wrapper.append(child);
			} else if (isBR || wrapper) {
				wrapper = wrapper || createElement('div');
				fixCursor(wrapper, root);
				child[isBR ? 'replaceWith' : 'before'](wrapper);
				wrapper = null;
			}
			isContainer(child) && fixContainer(child, root);
		});
		wrapper && container.append(fixCursor(wrapper, root));
		return container;
	},

	split = (node, offset, stopNode, root) => {
		let nodeType = node.nodeType,
			parent, clone, next;
		if (nodeType === TEXT_NODE && node !== stopNode) {
			return split(
				node.parentNode, node.splitText(offset), stopNode, root);
		}
		if (nodeType === ELEMENT_NODE) {
			if (typeof(offset) === 'number') {
				offset = offset < node.childNodes.length ?
					node.childNodes[ offset ] : null;
			}
			if (node === stopNode) {
				return offset;
			}

			// Clone node without children
			parent = node.parentNode;
			clone = node.cloneNode(false);

			// Add right-hand siblings to the clone
			while (offset) {
				next = offset.nextSibling;
				clone.append(offset);
				offset = next;
			}

			// Maintain li numbering if inside a quote.
			if (node.nodeName === 'OL' &&
					getClosest(node, root, 'BLOCKQUOTE')) {
				clone.start = (+node.start || 1) + node.childNodes.length - 1;
			}

			// DO NOT NORMALISE. This may undo the fixCursor() call
			// of a node lower down the tree!

			// We need something in the element in order for the cursor to appear.
			fixCursor(node, root);
			fixCursor(clone, root);

			// Inject clone after original node
			node.after(clone);

			// Keep on splitting up the tree
			return split(parent, clone, stopNode, root);
		}
		return offset;
	},

	_mergeInlines = (node, fakeRange) => {
		let children = node.childNodes,
			l = children.length,
			frags = [],
			child, prev;
		while (l--) {
			child = children[l];
			prev = l && children[ l - 1 ];
			if (l && isInline(child) && areAlike(child, prev) &&
					!leafNodeNames[ child.nodeName ]) {
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
					}
					else if (fakeRange.startOffset === l) {
						fakeRange.startContainer = prev;
						fakeRange.startOffset = getLength(prev);
					}
				}
				if (fakeRange.endContainer === node) {
					if (fakeRange.endOffset > l) {
						--fakeRange.endOffset;
					}
					else if (fakeRange.endOffset === l) {
						fakeRange.endContainer = prev;
						fakeRange.endOffset = getLength(prev);
					}
				}
				detach(child);
				if (child.nodeType === TEXT_NODE) {
					prev.appendData(child.data);
				}
				else {
					frags.push(empty(child));
				}
			}
			else if (isElement(child)) {
				child.append(...frags.reverse());
				frags = [];
				_mergeInlines(child, fakeRange);
			}
		}
	},

	mergeInlines = (node, range) => {
		if (node.nodeType === TEXT_NODE) {
			node = node.parentNode;
		}
		if (isElement(node)) {
			let fakeRange = {
				startContainer: range.startContainer,
				startOffset: range.startOffset,
				endContainer: range.endContainer,
				endOffset: range.endOffset
			};
			_mergeInlines(node, fakeRange);
			range.setStart(fakeRange.startContainer, fakeRange.startOffset);
			range.setEnd(fakeRange.endContainer, fakeRange.endOffset);
		}
	},

	mergeWithBlock = (block, next, range, root) => {
		let container = next;
		let parent, last, offset;
		while ((parent = container.parentNode) &&
				parent !== root &&
				isElement(parent) &&
				parent.childNodes.length === 1) {
			container = parent;
		}
		detach(container);

		offset = block.childNodes.length;

		// Remove extra <BR> fixer if present.
		last = block.lastChild;
		if (last?.nodeName === 'BR') {
			last.remove();
			--offset;
		}

		block.append(empty(next));

		range.setStart(block, offset);
		range.collapse(true);
		mergeInlines(block, range);
	},

	mergeContainers = (node, root) => {
		let prev = node.previousSibling,
			first = node.firstChild,
			isListItem = (node.nodeName === 'LI'),
			needsFix, block;

		// Do not merge LIs, unless it only contains a UL
		if (isListItem && (!first || !/^[OU]L$/.test(first.nodeName))) {
			return;
		}

		if (prev && areAlike(prev, node)) {
			if (!isContainer(prev)) {
				if (!isListItem) {
					return;
				}
				block = createElement('DIV');
				block.append(empty(prev));
				prev.append(block);
			}
			detach(node);
			needsFix = !isContainer(node);
			prev.append(empty(node));
			if (needsFix) {
				fixContainer(prev, root);
			}
			if (first) {
				mergeContainers(first, root);
			}
		} else if (isListItem) {
			prev = createElement('DIV');
			node.insertBefore(prev, first);
			fixCursor(prev, root);
		}
	},

	getNodeBefore = (node, offset) => {
		let children = node.childNodes;
		while (offset && isElement(node)) {
			node = children[ offset - 1 ];
			children = node.childNodes;
			offset = children.length;
		}
		return node;
	},

	getNodeAfter = (node, offset) => {
		if (isElement(node)) {
			let children = node.childNodes;
			if (offset < children.length) {
				node = children[ offset ];
			} else {
				while (node && !node.nextSibling) {
					node = node.parentNode;
				}
				if (node) { node = node.nextSibling; }
			}
		}
		return node;
	},

	insertNodeInRange = (range, node) => {
		// Insert at start.
		let startContainer = range.startContainer,
			startOffset = range.startOffset,
			endContainer = range.endContainer,
			endOffset = range.endOffset,
			parent, children, childCount, afterSplit;

		// If part way through a text node, split it.
		if (startContainer.nodeType === TEXT_NODE) {
			parent = startContainer.parentNode;
			children = parent.childNodes;
			if (startOffset === startContainer.length) {
				startOffset = indexOf(children, startContainer) + 1;
				if (range.collapsed) {
					endContainer = parent;
					endOffset = startOffset;
				}
			} else {
				if (startOffset) {
					afterSplit = startContainer.splitText(startOffset);
					if (endContainer === startContainer) {
						endOffset -= startOffset;
						endContainer = afterSplit;
					}
					else if (endContainer === parent) {
						++endOffset;
					}
					startContainer = afterSplit;
				}
				startOffset = indexOf(children, startContainer);
			}
			startContainer = parent;
		} else {
			children = startContainer.childNodes;
		}

		childCount = children.length;

		if (startOffset === childCount) {
			startContainer.append(node);
		} else {
			startContainer.insertBefore(node, children[ startOffset ]);
		}

		if (startContainer === endContainer) {
			endOffset += children.length - childCount;
		}

		range.setStart(startContainer, startOffset);
		range.setEnd(endContainer, endOffset);
	},

	extractContentsOfRange = (range, common, root) => {
		let startContainer = range.startContainer,
			startOffset = range.startOffset,
			endContainer = range.endContainer,
			endOffset = range.endOffset;

		if (!common) {
			common = range.commonAncestorContainer;
		}

		if (common.nodeType === TEXT_NODE) {
			common = common.parentNode;
		}

		let endNode = split(endContainer, endOffset, common, root),
			startNode = split(startContainer, startOffset, common, root),
			frag = doc.createDocumentFragment(),
			next, before, after, beforeText, afterText;

		// End node will be null if at end of child nodes list.
		while (startNode !== endNode) {
			next = startNode.nextSibling;
			frag.append(startNode);
			startNode = next;
		}

		startContainer = common;
		startOffset = endNode ?
			indexOf(common.childNodes, endNode) :
			common.childNodes.length;

		// Merge text nodes if adjacent. IE10 in particular will not focus
		// between two text nodes
		after = common.childNodes[ startOffset ];
		before = after?.previousSibling;
		if (before?.nodeType === TEXT_NODE && after.nodeType === TEXT_NODE) {
			startContainer = before;
			startOffset = before.length;
			beforeText = before.data;
			afterText = after.data;

			// If we now have two adjacent spaces, the second one needs to become
			// a nbsp, otherwise the browser will swallow it due to HTML whitespace
			// collapsing.
			if (beforeText.charAt(beforeText.length - 1) === ' ' &&
					afterText.charAt(0) === ' ') {
				afterText = NBSP + afterText.slice(1); // nbsp
			}
			before.appendData(afterText);
			detach(after);
		}

		range.setStart(startContainer, startOffset);
		range.collapse(true);

		fixCursor(common, root);

		return frag;
	},

	deleteContentsOfRange = (range, root) => {
		let startBlock = getStartBlockOfRange(range, root);
		let endBlock = getEndBlockOfRange(range, root);
		let needsMerge = (startBlock !== endBlock);
		let frag, child;

		// Move boundaries up as much as possible without exiting block,
		// to reduce need to split.
		moveRangeBoundariesDownTree(range);
		moveRangeBoundariesUpTree(range, startBlock, endBlock, root);

		// Remove selected range
		frag = extractContentsOfRange(range, null, root);

		// Move boundaries back down tree as far as possible.
		moveRangeBoundariesDownTree(range);

		// If we split into two different blocks, merge the blocks.
		if (needsMerge) {
			// endBlock will have been split, so need to refetch
			endBlock = getEndBlockOfRange(range, root);
			if (startBlock && endBlock && startBlock !== endBlock) {
				mergeWithBlock(startBlock, endBlock, range, root);
			}
		}

		// Ensure block has necessary children
		if (startBlock) {
			fixCursor(startBlock, root);
		}

		// Ensure root has a block-level element in it.
		child = root.firstChild;
		if (child && child.nodeName !== 'BR') {
			range.collapse(true);
		} else {
			fixCursor(root, root);
			range.selectNodeContents(root.firstChild);
		}
		return frag;
	},

	// Contents of range will be deleted.
	// After method, range will be around inserted content
	insertTreeFragmentIntoRange = (range, frag, root) => {
		let firstInFragIsInline = frag.firstChild && isInline(frag.firstChild);
		let node, block, blockContentsAfterSplit, stopPoint, container, offset;
		let replaceBlock, firstBlockInFrag, nodeAfterSplit, nodeBeforeSplit;
		let tempRange;

		// Fixup content: ensure no top-level inline, and add cursor fix elements.
		fixContainer(frag, root);
		node = frag;
		while ((node = getNextBlock(node, root))) {
			fixCursor(node, root);
		}

		// Delete any selected content.
		if (!range.collapsed) {
			deleteContentsOfRange(range, root);
		}

		// Move range down into text nodes.
		moveRangeBoundariesDownTree(range);
		range.collapse(false); // collapse to end

		// Where will we split up to? First blockquote parent, otherwise root.
		stopPoint = getClosest(range.endContainer, root, 'BLOCKQUOTE') || root;

		// Merge the contents of the first block in the frag with the focused block.
		// If there are contents in the block after the focus point, collect this
		// up to insert in the last block later. This preserves the style that was
		// present in this bit of the page.
		//
		// If the block being inserted into is empty though, replace it instead of
		// merging if the fragment had block contents.
		// e.g. <blockquote><p>Foo</p></blockquote>
		// This seems a reasonable approximation of user intent.

		block = getStartBlockOfRange(range, root);
		firstBlockInFrag = getNextBlock(frag, frag);
		replaceBlock = !firstInFragIsInline && !!block && isEmptyBlock(block);
		if (block && firstBlockInFrag && !replaceBlock &&
				// Don't merge table cells or PRE elements into block
				!getClosest(firstBlockInFrag, frag, 'PRE,TABLE')) {
			moveRangeBoundariesUpTree(range, block, block, root);
			range.collapse(true); // collapse to start
			container = range.endContainer;
			offset = range.endOffset;
			// Remove trailing <br> – we don't want this considered content to be
			// inserted again later
			cleanupBRs(block, root, false);
			if (isInline(container)) {
				// Split up to block parent.
				nodeAfterSplit = split(
					container, offset, getPreviousBlock(container, root), root);
				container = nodeAfterSplit.parentNode;
				offset = indexOf(container.childNodes, nodeAfterSplit);
			}
			if (/*isBlock(container) && */offset !== getLength(container)) {
				// Collect any inline contents of the block after the range point
				blockContentsAfterSplit = doc.createDocumentFragment();
				while ((node = container.childNodes[ offset ])) {
					blockContentsAfterSplit.append(node);
				}
			}
			// And merge the first block in.
			mergeWithBlock(container, firstBlockInFrag, range, root);

			// And where we will insert
			offset = indexOf(container.parentNode.childNodes, container) + 1;
			container = container.parentNode;
			range.setEnd(container, offset);
		}

		// Is there still any content in the fragment?
		if (getLength(frag)) {
			if (replaceBlock) {
				range.setEndBefore(block);
				range.collapse(false);
				detach(block);
			}
			moveRangeBoundariesUpTree(range, stopPoint, stopPoint, root);
			// Now split after block up to blockquote (if a parent) or root
			nodeAfterSplit = split(
				range.endContainer, range.endOffset, stopPoint, root);
			nodeBeforeSplit = nodeAfterSplit ?
				nodeAfterSplit.previousSibling :
				stopPoint.lastChild;
			stopPoint.insertBefore(frag, nodeAfterSplit);
			if (nodeAfterSplit) {
				range.setEndBefore(nodeAfterSplit);
			} else {
				range.setEnd(stopPoint, getLength(stopPoint));
			}
			block = getEndBlockOfRange(range, root);

			// Get a reference that won't be invalidated if we merge containers.
			moveRangeBoundariesDownTree(range);
			container = range.endContainer;
			offset = range.endOffset;

			// Merge inserted containers with edges of split
			if (nodeAfterSplit && isContainer(nodeAfterSplit)) {
				mergeContainers(nodeAfterSplit, root);
			}
			nodeAfterSplit = nodeBeforeSplit?.nextSibling;
			if (nodeAfterSplit && isContainer(nodeAfterSplit)) {
				mergeContainers(nodeAfterSplit, root);
			}
			range.setEnd(container, offset);
		}

		// Insert inline content saved from before.
		if (blockContentsAfterSplit) {
			tempRange = range.cloneRange();
			mergeWithBlock(block, blockContentsAfterSplit, tempRange, root);
			range.setEnd(tempRange.endContainer, tempRange.endOffset);
		}
		moveRangeBoundariesDownTree(range);
	},

	isNodeContainedInRange = (range, node, partial = true) => {
		let nodeRange = doc.createRange();

		nodeRange.selectNode(node);

		return partial
			// Node must not finish before range starts or start after range finishes.
			? range.compareBoundaryPoints(END_TO_START, nodeRange) < 0
				&& range.compareBoundaryPoints(START_TO_END, nodeRange) > 0
			// Node must start after range starts and finish before range finishes
			: range.compareBoundaryPoints(START_TO_START, nodeRange) < 1
				&& range.compareBoundaryPoints(END_TO_END, nodeRange) > -1;
	},

	moveRangeBoundariesDownTree = range => {
		let startContainer = range.startContainer,
			startOffset = range.startOffset,
			endContainer = range.endContainer,
			endOffset = range.endOffset,
			maySkipBR = true,
			child;

		while (startContainer.nodeType !== TEXT_NODE) {
			child = startContainer.childNodes[ startOffset ];
			if (!child || isLeaf(child)) {
				break;
			}
			startContainer = child;
			startOffset = 0;
		}
		if (endOffset) {
			while (endContainer.nodeType !== TEXT_NODE) {
				child = endContainer.childNodes[ endOffset - 1 ];
				if (!child || isLeaf(child)) {
					if (maySkipBR && child?.nodeName === 'BR') {
						--endOffset;
						maySkipBR = false;
						continue;
					}
					break;
				}
				endContainer = child;
				endOffset = getLength(endContainer);
			}
		} else {
			while (endContainer.nodeType !== TEXT_NODE) {
				child = endContainer.firstChild;
				if (!child || isLeaf(child)) {
					break;
				}
				endContainer = child;
			}
		}

		// If collapsed, this algorithm finds the nearest text node positions
		// *outside* the range rather than inside, but also it flips which is
		// assigned to which.
		if (range.collapsed) {
			range.setStart(endContainer, endOffset);
			range.setEnd(startContainer, startOffset);
		} else {
			range.setStart(startContainer, startOffset);
			range.setEnd(endContainer, endOffset);
		}
	},

	moveRangeBoundariesUpTree = (range, startMax, endMax, root) => {
		let startContainer = range.startContainer;
		let startOffset = range.startOffset;
		let endContainer = range.endContainer;
		let endOffset = range.endOffset;
		let maySkipBR = true;
		let parent;

		if (!startMax) {
			startMax = range.commonAncestorContainer;
		}
		if (!endMax) {
			endMax = startMax;
		}

		while (!startOffset &&
				startContainer !== startMax &&
				startContainer !== root) {
			parent = startContainer.parentNode;
			startOffset = indexOf(parent.childNodes, startContainer);
			startContainer = parent;
		}

		while (endContainer !== endMax && endContainer !== root) {
			if (maySkipBR &&
					endContainer.nodeType !== TEXT_NODE &&
					endContainer.childNodes[ endOffset ] &&
					endContainer.childNodes[ endOffset ].nodeName === 'BR') {
				++endOffset;
				maySkipBR = false;
			}
			if (endOffset !== getLength(endContainer)) {
				break;
			}
			parent = endContainer.parentNode;
			endOffset = indexOf(parent.childNodes, endContainer) + 1;
			endContainer = parent;
		}

		range.setStart(startContainer, startOffset);
		range.setEnd(endContainer, endOffset);
	},

	moveRangeBoundaryOutOf = (range, nodeName, root) => {
		let parent = getClosest(range.endContainer, root, 'A');
		if (parent) {
			let clone = range.cloneRange();
			parent = parent.parentNode;
			moveRangeBoundariesUpTree(clone, parent, parent, root);
			if (clone.endContainer === parent) {
				range.setStart(clone.endContainer, clone.endOffset);
				range.setEnd(clone.endContainer, clone.endOffset);
			}
		}
		return range;
	},

	// Returns the first block at least partially contained by the range,
	// or null if no block is contained by the range.
	getStartBlockOfRange = (range, root) => {
		let container = range.startContainer,
			block;

		// If inline, get the containing block.
		if (isInline(container)) {
			block = getPreviousBlock(container, root);
		} else if (container !== root && isBlock(container)) {
			block = container;
		} else {
			block = getNextBlock(getNodeBefore(container, range.startOffset), root);
		}
		// Check the block actually intersects the range
		return block && isNodeContainedInRange(range, block) ? block : null;
	},

	// Returns the last block at least partially contained by the range,
	// or null if no block is contained by the range.
	getEndBlockOfRange = (range, root) => {
		let container = range.endContainer,
			block, child;

		// If inline, get the containing block.
		if (isInline(container)) {
			block = getPreviousBlock(container, root);
		} else if (container !== root && isBlock(container)) {
			block = container;
		} else {
			block = getNodeAfter(container, range.endOffset);
			if (!block || !root.contains(block)) {
				block = root;
				while (child = block.lastChild) {
					block = child;
				}
			}
			block = getPreviousBlock(block, root);
		}
		// Check the block actually intersects the range
		return block && isNodeContainedInRange(range, block) ? block : null;
	},

	newContentWalker = root => createTreeWalker(root,
		SHOW_ELEMENT_OR_TEXT,
		node => node.nodeType === TEXT_NODE ? notWS.test(node.data) : node.nodeName === 'IMG'
	),

	rangeDoesStartAtBlockBoundary = (range, root) => {
		let startContainer = range.startContainer;
		let startOffset = range.startOffset;
		let startBlock = getStartBlockOfRange(range, root);
		let nodeAfterCursor;

		if (!startBlock) {
			return false;
		}

		// If in the middle or end of a text node, we're not at the boundary.
		if (startContainer.nodeType === TEXT_NODE) {
			if (startOffset) {
				return false;
			}
			nodeAfterCursor = startContainer;
		} else {
			nodeAfterCursor = getNodeAfter(startContainer, startOffset);
			if (nodeAfterCursor && !root.contains(nodeAfterCursor)) {
				nodeAfterCursor = null;
			}
			// The cursor was right at the end of the document
			if (!nodeAfterCursor) {
				nodeAfterCursor = getNodeBefore(startContainer, startOffset);
				if (nodeAfterCursor.nodeType === TEXT_NODE &&
						nodeAfterCursor.length) {
					return false;
				}
			}
		}

		// Otherwise, look for any previous content in the same block.
		contentWalker = newContentWalker(getStartBlockOfRange(range, root));
		contentWalker.currentNode = nodeAfterCursor;

		return !contentWalker.previousNode();
	},

	rangeDoesEndAtBlockBoundary = (range, root) => {
		let endContainer = range.endContainer,
			endOffset = range.endOffset,
			length;

		// Otherwise, look for any further content in the same block.
		contentWalker = newContentWalker(getStartBlockOfRange(range, root));

		// If in a text node with content, and not at the end, we're not
		// at the boundary
		if (endContainer.nodeType === TEXT_NODE) {
			length = endContainer.data.length;
			if (length && endOffset < length) {
				return false;
			}
			contentWalker.currentNode = endContainer;
		} else {
			contentWalker.currentNode = getNodeBefore(endContainer, endOffset);
		}

		return !contentWalker.nextNode();
	},

	expandRangeToBlockBoundaries = (range, root) => {
		let start = getStartBlockOfRange(range, root),
			end = getEndBlockOfRange(range, root);

		if (start && end) {
			range.setStart(start, 0);
			range.setEnd(end, end.childNodes.length);
//			parent = start.parentNode;
//			range.setStart(parent, indexOf(parent.childNodes, start));
//			parent = end.parentNode;
//			range.setEnd(parent, indexOf(parent.childNodes, end) + 1);
		}
	},

	didError = error => console.error(error),

	createRange = (range, startOffset, endContainer, endOffset) => {
		if (range instanceof Range) {
			return range.cloneRange();
		}
		let domRange = doc.createRange();
		domRange.setStart(range, startOffset);
		if (endContainer) {
			domRange.setEnd(endContainer, endOffset);
		} else {
			domRange.setEnd(range, startOffset);
		}
		return domRange;
	},

	mapKeyTo = method => (self, event) => {
		event.preventDefault();
		self[ method ]();
	},

	mapKeyToFormat = (tag, remove) => {
		return (self, event) => {
			event.preventDefault();
			self.toggleTag(tag, remove);
		};
	},

	// If you delete the content inside a span with a font styling, Webkit will
	// replace it with a <font> tag (!). If you delete all the text inside a
	// link in Opera, it won't delete the link. Let's make things consistent. If
	// you delete all text inside an inline tag, remove the inline tag.
	afterDelete = (self, range) => {
		try {
			if (!range) { range = self.getSelection(); }
			let node = range.startContainer,
				parent;
			// Climb the tree from the focus point while we are inside an empty
			// inline element
			if (node.nodeType === TEXT_NODE) {
				node = node.parentNode;
			}
			parent = node;
			while (isInline(parent) && (!parent.textContent || parent.textContent === ZWS)) {
				node = parent;
				parent = node.parentNode;
			}
			// If focused in empty inline element
			if (node !== parent) {
				// Move focus to just before empty inline(s)
				range.setStart(parent,
					indexOf(parent.childNodes, node));
				range.collapse(true);
				// Remove empty inline(s)
				node.remove();
				// Fix cursor in block
				if (!isBlock(parent)) {
					parent = getPreviousBlock(parent, self._root);
				}
				fixCursor(parent, self._root);
				// Move cursor into text node
				moveRangeBoundariesDownTree(range);
			}
			// If you delete the last character in the sole <div> in Chrome,
			// it removes the div and replaces it with just a <br> inside the
			// root. Detach the <br>; the _ensureBottomLine call will insert a new
			// block.
			if (node === self._root && (node = node.firstChild) && node.nodeName === 'BR') {
				detach(node);
			}
			self._ensureBottomLine();
			self.setSelection(range);
			self._updatePath(range, true);
		} catch (error) {
			didError(error);
		}
	},

	detachUneditableNode = (node, root) => {
		let parent;
		while ((parent = node.parentNode)) {
			if (parent === root || parent.isContentEditable) {
				break;
			}
			node = parent;
		}
		detach(node);
	},

	handleEnter = (self, shiftKey, range) => {
		let root = self._root;
		let block, parent, node, offset, nodeAfterSplit;

		// Save undo checkpoint and add any links in the preceding section.
		// Remove any zws so we don't think there's content in an empty
		// block.
		self._recordUndoState(range, false);
		self._config.addLinks && addLinks(range.startContainer, root, self);
		self._removeZWS();
		self._getRangeAndRemoveBookmark(range);

		// Selected text is overwritten, therefore delete the contents
		// to collapse selection.
		if (!range.collapsed) {
			deleteContentsOfRange(range, root);
		}

		block = getStartBlockOfRange(range, root);

		// Inside a PRE, insert literal newline, unless on blank line.
		if (block && (parent = getClosest(block, root, 'PRE'))) {
			moveRangeBoundariesDownTree(range);
			node = range.startContainer;
			offset = range.startOffset;
			if (node.nodeType !== TEXT_NODE) {
				node = doc.createTextNode('');
				parent.insertBefore(node, parent.firstChild);
			}
			// If blank line: split and insert default block
			if (!shiftKey &&
					(node.data.charAt(offset - 1) === '\n' ||
						rangeDoesStartAtBlockBoundary(range, root)) &&
					(node.data.charAt(offset) === '\n' ||
						rangeDoesEndAtBlockBoundary(range, root))) {
				node.deleteData(offset && offset - 1, offset ? 2 : 1);
				nodeAfterSplit =
					split(node, offset && offset - 1, root, root);
				node = nodeAfterSplit.previousSibling;
				if (!node.textContent) {
					detach(node);
				}
				node = self.createDefaultBlock();
				nodeAfterSplit.before(node);
				if (!nodeAfterSplit.textContent) {
					detach(nodeAfterSplit);
				}
				range.setStart(node, 0);
			} else {
				node.insertData(offset, '\n');
				fixCursor(parent, root);
				// Firefox bug: if you set the selection in the text node after
				// the new line, it draws the cursor before the line break still
				// but if you set the selection to the equivalent position
				// in the parent, it works.
				if (node.length === offset + 1) {
					range.setStartAfter(node);
				} else {
					range.setStart(node, offset + 1);
				}
			}
			range.collapse(true);
			self.setSelection(range);
			self._updatePath(range, true);
			self._docWasChanged();
			return;
		}

		// If this is a malformed bit of document or in a table;
		// just play it safe and insert a <br>.
		if (!block || shiftKey || /^T[HD]$/.test(block.nodeName)) {
			// If inside an <a>, move focus out
			moveRangeBoundaryOutOf(range, 'A', root);
			insertNodeInRange(range, createElement('BR'));
			range.collapse(false);
			self.setSelection(range);
			self._updatePath(range, true);
			return;
		}

		// If in a list, we'll split the LI instead.
		block = getClosest(block, root, 'LI') || block;

		if (isEmptyBlock(block) && (parent = getClosest(block, root, 'UL,OL,BLOCKQUOTE'))) {
			return 'BLOCKQUOTE' === parent.nodeName
				// Break blockquote
				? self.modifyBlocks((/* frag */) => self.createDefaultBlock(createBookmarkNodes(self)), range)
				// Break list
				: self.decreaseListLevel(range);
		}

		// Otherwise, split at cursor point.
		nodeAfterSplit = splitBlock(self, block,
			range.startContainer, range.startOffset);

		// Clean up any empty inlines if we hit enter at the beginning of the block
		removeZWS(block);
		removeEmptyInlines(block);
		fixCursor(block, root);

		// Focus cursor
		// If there's a <b>/<i> etc. at the beginning of the split
		// make sure we focus inside it.
		while (isElement(nodeAfterSplit)) {
			let child = nodeAfterSplit.firstChild,
				next;

			// Don't continue links over a block break; unlikely to be the
			// desired outcome.
			if (nodeAfterSplit.nodeName === 'A' && (!nodeAfterSplit.textContent || nodeAfterSplit.textContent === ZWS)) {
				child = doc.createTextNode('');
				nodeAfterSplit.replaceWith(child);
				nodeAfterSplit = child;
				break;
			}

			while (child?.nodeType === TEXT_NODE && !child.data) {
				next = child.nextSibling;
				if (!next || next.nodeName === 'BR') {
					break;
				}
				detach(child);
				child = next;
			}

			// 'BR's essentially don't count; they're a browser hack.
			// If you try to select the contents of a 'BR', FF will not let
			// you type anything!
			if (!child || child.nodeName === 'BR' ||
					child.nodeType === TEXT_NODE) {
				break;
			}
			nodeAfterSplit = child;
		}
		range = createRange(nodeAfterSplit, 0);
		self.setSelection(range);
		self._updatePath(range, true);
	},


	changeIndentationLevel = direction => (self, event) => {
		event.preventDefault();
		self.changeIndentationLevel(direction);
	},

	toggleList = (type, methodIfNotInList) => (self, event) => {
		event.preventDefault();
		let parent = self.getSelectionClosest('UL,OL');
		if (type == parent?.nodeName) {
			self.removeList();
		} else {
			self[ methodIfNotInList ]();
		}
	},

	fontSizes = {
		1: 'x-small',
		2: 'small',
		3: 'medium',
		4: 'large',
		5: 'x-large',
		6: 'xx-large',
		7: 'xxx-large',
		'-1': 'smaller',
		'+1': 'larger'
	},

	styleToSemantic = {
		fontWeight: {
			regexp: /^bold|^700/i,
			replace: () => createElement('B')
		},
		fontStyle: {
			regexp: /^italic/i,
			replace: () => createElement('I')
		},
		fontFamily: {
			regexp: notWS,
			replace: (doc, family) => createElement('SPAN', {
				style: 'font-family:' + family
			})
		},
		fontSize: {
			regexp: notWS,
			replace: (doc, size) => createElement('SPAN', {
				style: 'font-size:' + size
			})
		},
		textDecoration: {
			regexp: /^underline/i,
			replace: () => createElement('U')
		}
	/*
		textDecoration: {
			regexp: /^line-through/i,
			replace: doc => createElement('S')
		}
	*/
	},

	replaceWithTag = tag => node => {
		let el = createElement(tag);
		Array.prototype.forEach.call(node.attributes, attr => el.setAttribute(attr.name, attr.value));
		node.replaceWith(el);
		el.append(empty(node));
		return el;
	},

	replaceStyles = node => {
		let style = node.style;
		let css, newTreeBottom, newTreeTop, el;

		Object.entries(styleToSemantic).forEach(([attr,converter])=>{
			css = style[ attr ];
			if (css && converter.regexp.test(css)) {
				el = converter.replace(doc, css);
				if (el.nodeName === node.nodeName &&
						el.className === node.className) {
					return;
				}
				if (!newTreeTop) {
					newTreeTop = el;
				}
				if (newTreeBottom) {
					newTreeBottom.append(el);
				}
				newTreeBottom = el;
				node.style[ attr ] = '';
			}
		});

		if (newTreeTop) {
			newTreeBottom.append(empty(node));
			node.append(newTreeTop);
		}

		return newTreeBottom || node;
	},

	stylesRewriters = {
		SPAN: replaceStyles,
		STRONG: replaceWithTag('B'),
		EM: replaceWithTag('I'),
		INS: replaceWithTag('U'),
		STRIKE: replaceWithTag('S'),
		FONT: node => {
			let face = node.face,
				size = node.size,
				color = node.color,
				newTag = createElement('SPAN'),
				css = newTag.style;
			if (face) {
				css.fontFamily = face;
			}
			if (size) {
				css.fontSize = fontSizes[ size ];
			}
			if (color && /^#?([\dA-F]{3}){1,2}$/i.test(color)) {
				if (color.charAt(0) !== '#') {
					color = '#' + color;
				}
				css.color = color;
			}
			node.replaceWith(newTag);
			newTag.append(empty(node));
			return newTag;
		},
	//	KBD:
	//	VAR:
	//	CODE:
	//	SAMP:
		TT: node => {
			let el = createElement('SPAN', {
				style: 'font-family:menlo,consolas,"courier new",monospace'
			});
			node.replaceWith(el);
			el.append(empty(node));
			return el;
		}
	},

	allowedBlock = /^(?:A(?:DDRESS|RTICLE|SIDE|UDIO)|BLOCKQUOTE|CAPTION|D(?:[DLT]|IV)|F(?:IGURE|IGCAPTION|OOTER)|H[1-6]|HEADER|L(?:ABEL|EGEND|I)|O(?:L|UTPUT)|P(?:RE)?|SECTION|T(?:ABLE|BODY|D|FOOT|H|HEAD|R)|COL(?:GROUP)?|UL)$/,

	blacklist = /^(?:HEAD|META|STYLE)/,
/*
	// Previous node in post-order.
	previousPONode = walker => {
		let current = walker.currentNode,
			root = walker.root,
			nodeType = walker.nodeType, // whatToShow?
			filter = walker.filter,
			node;
		while (current) {
			node = current.lastChild;
			while (!node && current && current !== root) {
				node = current.previousSibling;
				if (!node) { current = current.parentNode; }
			}
			if (node && (typeToBitArray[ node.nodeType ] & nodeType) && filter(node)) {
				walker.currentNode = node;
				return node;
			}
			current = node;
		}
		return null;
	},
*/
	/*
		Two purposes:

		1. Remove nodes we don't want, such as weird <o:p> tags, comment nodes
		   and whitespace nodes.
		2. Convert inline tags into our preferred format.
	*/
	cleanTree = (node, preserveWS) => {
		let children = node.childNodes,
			nonInlineParent, i, l, child, nodeName, nodeType, childLength;
//			startsWithWS, endsWithWS, data, sibling;

		nonInlineParent = node;
		while (isInline(nonInlineParent)) {
			nonInlineParent = nonInlineParent.parentNode;
		}
//		let walker = createTreeWalker(nonInlineParent, SHOW_ELEMENT_OR_TEXT);

		for (i = 0, l = children.length; i < l; ++i) {
			child = children[i];
			nodeName = child.nodeName;
			nodeType = child.nodeType;
			if (nodeType === ELEMENT_NODE) {
				childLength = child.childNodes.length;
				if (stylesRewriters[ nodeName ]) {
					child = stylesRewriters[ nodeName ](child);
				} else if (blacklist.test(nodeName)) {
					child.remove();
					--i;
					--l;
					continue;
				} else if (!allowedBlock.test(nodeName) && !isInline(child)) {
					--i;
					l += childLength - 1;
					child.replaceWith(empty(child));
					continue;
				}
				if (childLength) {
					cleanTree(child, preserveWS || (nodeName === 'PRE'));
				}
/*
			} else {
				if (nodeType === TEXT_NODE) {
					data = child.data;
					startsWithWS = !notWS.test(data.charAt(0));
					endsWithWS = !notWS.test(data.charAt(data.length - 1));
					if (preserveWS || (!startsWithWS && !endsWithWS)) {
						continue;
					}
					// Iterate through the nodes; if we hit some other content
					// before the start of a new block we don't trim
					if (startsWithWS) {
						walker.currentNode = child;
						while (sibling = previousPONode(walker)) {
							nodeName = sibling.nodeName;
							if (nodeName === 'IMG' || (nodeName === '#text' && notWS.test(sibling.data))) {
								break;
							}
							if (!isInline(sibling)) {
								sibling = null;
								break;
							}
						}
						data = data.replace(/^[ \r\n]+/g, sibling ? ' ' : '');
					}
					if (endsWithWS) {
						walker.currentNode = child;
						while (sibling = walker.nextNode()) {
							if (nodeName === 'IMG' || (nodeName === '#text' && notWS.test(sibling.data))) {
								break;
							}
							if (!isInline(sibling)) {
								sibling = null;
								break;
							}
						}
						data = data.replace(/[ \r\n]+$/g, sibling ? ' ' : '');
					}
					if (data) {
						child.data = data;
						continue;
					}
				}
				child.remove();
				--i;
				--l;
*/
			}
		}
		return node;
	},

	// ---

	removeEmptyInlines = node => {
		let children = node.childNodes,
			l = children.length,
			child;
		while (l--) {
			child = children[l];
			if (isElement(child) && !isLeaf(child)) {
				removeEmptyInlines(child);
				if (!child.firstChild && isInline(child)) {
					child.remove();
				}
			} else if (child.nodeType === TEXT_NODE && !child.data) {
				child.remove();
			}
		}
	},

	// ---

	notWSTextNode = node => isElement(node) ? node.nodeName === 'BR' : notWS.test(node.data),
	isLineBreak = (br, isLBIfEmptyBlock) => {
		let walker, block = br.parentNode;
		while (isInline(block)) {
			block = block.parentNode;
		}
		walker = createTreeWalker(block, SHOW_ELEMENT_OR_TEXT, notWSTextNode);
		walker.currentNode = br;
		return !!walker.nextNode() || (isLBIfEmptyBlock && !walker.previousNode());
	},

	// <br> elements are treated specially, and differently depending on the
	// browser, when in rich text editor mode. When adding HTML from external
	// sources, we must remove them, replacing the ones that actually affect
	// line breaks by wrapping the inline text in a <div>. Browsers that want <br>
	// elements at the end of each block will then have them added back in a later
	// fixCursor method call.
	cleanupBRs = (node, root, keepForBlankLine) => {
		let brs = node.querySelectorAll('BR');
		let l = brs.length;
		let br, parent;
		while (l--) {
			br = brs[l];
			// Cleanup may have removed it
			parent = br.parentNode;
			if (!parent) { continue; }
			// If it doesn't break a line, just remove it; it's not doing
			// anything useful. We'll add it back later if required by the
			// browser. If it breaks a line, wrap the content in div tags
			// and replace the brs.
			if (!isLineBreak(br, keepForBlankLine)) {
				detach(br);
			} else if (!isInline(parent)) {
				fixContainer(parent, root);
			}
		}
	},

	// The (non-standard but supported enough) innerText property is based on the
	// render tree in Firefox and possibly other browsers, so we must insert the
	// DOM node into the document to ensure the text part is correct.
	setClipboardData = (event, contents, root) => {
		let clipboardData = event.clipboardData;
		let body = doc.body;
		let node = createElement('div');
		let html, text;

		node.append(contents);

		html = node.innerHTML;

		// Firefox will add an extra new line for BRs at the end of block when
		// calculating innerText, even though they don't actually affect
		// display, so we need to remove them first.
		cleanupBRs(node, root, true);
		node.setAttribute('style',
			'position:fixed;overflow:hidden;bottom:100%;right:100%;');
		body.append(node);
		text = (node.innerText || node.textContent).replace(NBSP, ' '); // Replace nbsp with regular space
		node.remove();

		if (text !== html) {
			clipboardData.setData('text/html', html);
		}
		clipboardData.setData('text/plain', text);
		event.preventDefault();
	},

	mergeObjects = (base, extras, mayOverride) => {
		base = base || {};
		extras && Object.entries(extras).forEach(([prop,value])=>{
			if (mayOverride || !(prop in base)) {
				base[ prop ] = (value?.constructor === Object) ?
					mergeObjects(base[ prop ], value, mayOverride) :
					value;
			}
		});
		return base;
	},

	// --- Events ---

	// Subscribing to these events won't automatically add a listener to the
	// document node, since these events are fired in a custom manner by the
	// editor code.
	customEvents = {
		pathChange: 1, select: 1, input: 1, undoStateChange: 1
	},

	// --- Workaround for browsers that can't focus empty text nodes ---

	// WebKit bug: https://bugs.webkit.org/show_bug.cgi?id=15256

	// Walk down the tree starting at the root and remove any ZWS. If the node only
	// contained ZWS space then remove it too. We may want to keep one ZWS node at
	// the bottom of the tree so the block can be selected. Define that node as the
	// keepNode.
	removeZWS = (root, keepNode) => {
		let walker = createTreeWalker(root, SHOW_TEXT);
		let parent, node, index;
		while (node = walker.nextNode()) {
			while ((index = node.data.indexOf(ZWS)) > -1  && (!keepNode || node.parentNode !== keepNode)) {
				if (node.length === 1) {
					do {
						parent = node.parentNode;
						node.remove();
						node = parent;
						walker.currentNode = parent;
					} while (isInline(node) && !getLength(node));
					break;
				} else {
					node.deleteData(index, 1);
				}
			}
		}
	},

	// --- Bookmarking ---

	startSelectionId = 'squire-selection-start',
	endSelectionId = 'squire-selection-end',

	createBookmarkNodes = () => [
		createElement('INPUT', {
			id: startSelectionId,
			type: 'hidden'
		}),
		createElement('INPUT', {
			id: endSelectionId,
			type: 'hidden'
		})
	],

	// --- Block formatting ---

	tagAfterSplit = {
		DT:  'DD',
		DD:  'DT',
		LI:  'LI',
		PRE: 'PRE'
	},

	splitBlock = (self, block, node, offset) => {
		let splitTag = tagAfterSplit[ block.nodeName ] || blockTag,
			nodeAfterSplit = split(node, offset, block.parentNode, self._root);

		// Make sure the new node is the correct type.
		if (!hasTagAttributes(nodeAfterSplit, splitTag)) {
			block = createElement(splitTag);
			if (nodeAfterSplit.dir) {
				block.dir = nodeAfterSplit.dir;
			}
			nodeAfterSplit.replaceWith(block);
			block.append(empty(nodeAfterSplit));
			nodeAfterSplit = block;
		}
		return nodeAfterSplit;
	},

	getListSelection = (range, root) => {
		// Get start+end li in single common ancestor
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
			startLi = startLi.childNodes[ range.startOffset ];
		}
		if (endLi === list) {
			endLi = endLi.childNodes[ range.endOffset ];
		}
		while (startLi && startLi.parentNode !== list) {
			startLi = startLi.parentNode;
		}
		while (endLi && endLi.parentNode !== list) {
			endLi = endLi.parentNode;
		}
		return [ list, startLi, endLi ];
	},

	makeList = (self, frag, type) => {
		let walker = getBlockWalker(frag, self._root),
			node, tag, prev, newLi;

		while (node = walker.nextNode()) {
			if (node.parentNode.nodeName === 'LI') {
				node = node.parentNode;
				walker.currentNode = node.lastChild;
			}
			if (node.nodeName !== 'LI') {
				newLi = createElement('LI');
				if (node.dir) {
					newLi.dir = node.dir;
				}

				// Have we replaced the previous block with a new <ul>/<ol>?
				if ((prev = node.previousSibling) && prev.nodeName === type) {
					prev.append(newLi);
					detach(node);
				}
				// Otherwise, replace this block with the <ul>/<ol>
				else {
					node.replaceWith(
						createElement(type, null, [
							newLi
						])
					);
				}
				newLi.append(empty(node));
				walker.currentNode = newLi;
			} else {
				node = node.parentNode;
				tag = node.nodeName;
				if (tag !== type && (/^[OU]L$/.test(tag))) {
					node.replaceWith(
						createElement(type, null, [ empty(node) ])
					);
				}
			}
		}

		return frag;
	},

	linkRegExp = /\b(?:((https?:\/\/)?(?:www\d{0,3}\.|[a-z0-9][a-z0-9.-]*\.[a-z]{2,}\/)(?:[^\s()<>]+|\([^\s()<>]+\))+(?:[^\s?&`!()[\]{};:'".,<>«»“”‘’]|\([^\s()<>]+\)))|([\w\-.%+]+@(?:[\w-]+\.)+[a-z]{2,}\b(?:\?[^&?\s]+=[^\s?&`!()[\]{};:'".,<>«»“”‘’]+(?:&[^&?\s]+=[^\s?&`!()[\]{};:'".,<>«»“”‘’]+)*)?))/i,

	addLinks = (frag, root) => {
		let walker = createTreeWalker(frag, SHOW_TEXT, node => !getClosest(node, root, 'A'));
		let node, data, parent, match, index, endIndex, child;
		while ((node = walker.nextNode())) {
			data = node.data;
			parent = node.parentNode;
			while ((match = linkRegExp.exec(data))) {
				index = match.index;
				endIndex = index + match[0].length;
				if (index) {
					child = doc.createTextNode(data.slice(0, index));
					parent.insertBefore(child, node);
				}
				child = createElement('A', {
					href: match[1]
						? (match[2] ? match[1] : 'https://' + match[1])
						: 'mailto:' + match[0]
				}, [data.slice(index, endIndex)]);
				parent.insertBefore(child, node);
				node.data = data = data.slice(endIndex);
			}
		}
	},

	escapeHTML = text => text.replace('&', '&amp;')
	   .replace('<', '&lt;')
	   .replace('>', '&gt;')
	   .replace('"', '&quot;');

let contentWalker,
	nodeCategoryCache = new WeakMap();

function onKey(event) {
	if (event.defaultPrevented) {
		return;
	}

	let key = event.key.toLowerCase(),
		modifiers = '',
		range = this.getSelection();

	// We need to apply the backspace/delete handlers regardless of
	// control key modifiers.
	if (key !== 'backspace' && key !== 'delete') {
		if (event.altKey) { modifiers += 'alt-'; }
		if (event[osKey]) { modifiers += ctrlKey; }
		if (event.shiftKey) { modifiers += 'shift-'; }
	}

	key = modifiers + key;

	if (this._keyHandlers[ key ]) {
		this._keyHandlers[ key ](this, event, range);
	// !event.isComposing stops us from blatting Kana-Kanji conversion in Safari
	} else if (!range.collapsed && !event.isComposing && !event[osKey] && key.length === 1) {
		// Record undo checkpoint.
		this.saveUndoState(range);
		// Delete the selection
		deleteContentsOfRange(range, this._root);
		this._ensureBottomLine();
		this.setSelection(range);
		this._updatePath(range, true);
	}
}

function onCut(event) {
	let range = this.getSelection();
	let root = this._root;
	let self = this;
	let startBlock, endBlock, copyRoot, contents, parent, newContents;

	// Nothing to do
	if (range.collapsed) {
		event.preventDefault();
		return;
	}

	// Save undo checkpoint
	this.saveUndoState(range);

	// Edge only seems to support setting plain text as of 2016-03-11.
	if (event.clipboardData) {
		// Clipboard content should include all parents within block, or all
		// parents up to root if selection across blocks
		startBlock = getStartBlockOfRange(range, root);
		endBlock = getEndBlockOfRange(range, root);
		copyRoot = ((startBlock === endBlock) && startBlock) || root;
		// Extract the contents
		contents = deleteContentsOfRange(range, root);
		// Add any other parents not in extracted content, up to copy root
		parent = range.commonAncestorContainer;
		if (parent.nodeType === TEXT_NODE) {
			parent = parent.parentNode;
		}
		while (parent && parent !== copyRoot) {
			newContents = parent.cloneNode(false);
			newContents.append(contents);
			contents = newContents;
			parent = parent.parentNode;
		}
		// Set clipboard data
		setClipboardData(event, contents, root);
	} else {
		setTimeout(() => {
			try {
				// If all content removed, ensure div at start of root.
				self._ensureBottomLine();
			} catch (error) {
				didError(error);
			}
		}, 0);
	}

	this.setSelection(range);
}

function onCopy(event) {
	// Edge only seems to support setting plain text as of 2016-03-11.
	if (event.clipboardData) {
		let range = this.getSelection(), root = this._root,
			// Clipboard content should include all parents within block, or all
			// parents up to root if selection across blocks
			startBlock = getStartBlockOfRange(range, root),
			endBlock = getEndBlockOfRange(range, root),
			copyRoot = ((startBlock === endBlock) && startBlock) || root,
			contents, parent, newContents;
		// Clone range to mutate, then move up as high as possible without
		// passing the copy root node.
		range = range.cloneRange();
		moveRangeBoundariesDownTree(range);
		moveRangeBoundariesUpTree(range, copyRoot, copyRoot, root);
		// Extract the contents
		contents = range.cloneContents();
		// Add any other parents not in extracted content, up to copy root
		parent = range.commonAncestorContainer;
		if (parent.nodeType === TEXT_NODE) {
			parent = parent.parentNode;
		}
		while (parent && parent !== copyRoot) {
			newContents = parent.cloneNode(false);
			newContents.append(contents);
			contents = newContents;
			parent = parent.parentNode;
		}
		// Set clipboard data
		setClipboardData(event, contents, root);
	}
}

function onPaste(event) {
	let clipboardData = event.clipboardData;
	let items = clipboardData?.items;
	let imageItem = null;
	let plainItem = null;
	let htmlItem = null;
	let self = this;
	let type;

	// Current HTML5 Clipboard interface
	// ---------------------------------
	// https://html.spec.whatwg.org/multipage/interaction.html
	if (items) {
		[...items].forEach(item => {
			type = item.type;
			if (type === 'text/html') {
				htmlItem = item;
			// iOS copy URL gives you type text/uri-list which is just a list
			// of 1 or more URLs separated by new lines. Can just treat as
			// plain text.
			} else if (type === 'text/plain' || type === 'text/uri-list') {
				plainItem = item;
			} else if (item.kind === 'file' && /^image\/(png|jpeg|webp)/.test(type)) {
				imageItem = item;
			}
		});
		if (htmlItem || plainItem || imageItem) {
			event.preventDefault();
			if (imageItem) {
				let reader = new FileReader();
				reader.onload = event => {
					let img = createElement('img', {src: event.target.result}),
						canvas = createElement('canvas'),
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
						self.insertHTML('<img alt="" style="width:100%;max-width:'+width+'px" src="'+canvas.toDataURL()+'">', true);
					};
				}
				reader.readAsDataURL(imageItem.getAsFile());
			} else if (htmlItem && (!self.isShiftDown || !plainItem)) {
				htmlItem.getAsString(html => self.insertHTML(html, true));
			} else if (plainItem) {
				plainItem.getAsString(text => self.insertPlainText(text, true));
			}
		}
	}
}

// On Windows you can drag an drop text. We can't handle this ourselves, because
// as far as I can see, there's no way to get the drop insertion point. So just
// save an undo state and hope for the best.
function onDrop(event) {
	let types = event.dataTransfer.types;
	if (types.includes('text/plain') || types.includes('text/html')) {
		this.saveUndoState();
	}
}

let keyHandlers = {
	// This song and dance is to force iOS to do enable the shift key
	// automatically on enter. When you do the DOM split manipulation yourself,
	// WebKit doesn't reset the IME state and so presents auto-complete options
	// as though you were continuing to type on the previous line, and doesn't
	// auto-enable the shift key. The old trick of blurring and focussing
	// again no longer works in iOS 13, and I tried various execCommand options
	// but they didn't seem to do anything. The only solution I've found is to
	// let iOS handle the enter key, then after it's done that reset the HTML
	// to what it was before and handle it properly in Squire; the IME state of
	// course doesn't reset so you end up in the correct state!
	enter: isIOS ? (self, event, range) => {
		self._saveRangeToBookmark(range);
		let html = self._getHTML();
		let restoreAndDoEnter = () => {
			self.removeEventListener('keyup', restoreAndDoEnter);
			self._setHTML(html);
			range = self._getRangeAndRemoveBookmark();
			// Ignore the shift key on iOS, as this is for auto-capitalisation.
			handleEnter(self, false, range);
		};
		self.addEventListener('keyup', restoreAndDoEnter);
	} : (self, event, range) => {
		event.preventDefault();
		handleEnter(self, event.shiftKey, range);
	},

	'shift-enter': (self, event, range) => self._keyHandlers.enter(self, event, range),

	backspace: (self, event, range) => {
		let root = self._root;
		self._removeZWS();
		// Record undo checkpoint.
		self.saveUndoState(range);
		// If not collapsed, delete contents
		if (!range.collapsed) {
			event.preventDefault();
			deleteContentsOfRange(range, root);
			afterDelete(self, range);
		}
		// If at beginning of block, merge with previous
		else if (rangeDoesStartAtBlockBoundary(range, root)) {
			event.preventDefault();
			let current = getStartBlockOfRange(range, root);
			let previous;
			if (!current) {
				return;
			}
			// In case inline data has somehow got between blocks.
			fixContainer(current.parentNode, root);
			// Now get previous block
			previous = getPreviousBlock(current, root);
			// Must not be at the very beginning of the text area.
			if (previous) {
				// If not editable, just delete whole block.
				if (!previous.isContentEditable) {
					detachUneditableNode(previous, root);
					return;
				}
				// Otherwise merge.
				mergeWithBlock(previous, current, range, root);
				// If deleted line between containers, merge newly adjacent
				// containers.
				current = previous.parentNode;
				while (current !== root && !current.nextSibling) {
					current = current.parentNode;
				}
				if (current !== root && (current = current.nextSibling)) {
					mergeContainers(current, root);
				}
				self.setSelection(range);
			}
			// If at very beginning of text area, allow backspace
			// to break lists/blockquote.
			else if (current) {
				let parent = getClosest(current, root, 'UL,OL,BLOCKQUOTE');
				if (parent) {
					return ('BLOCKQUOTE' === parent.nodeName)
						// Break blockquote
						? self.decreaseQuoteLevel(range)
						// Break list
						: self.decreaseListLevel(range);
				}
				self.setSelection(range);
				self._updatePath(range, true);
			}
		}
		// Otherwise, leave to browser but check afterwards whether it has
		// left behind an empty inline tag.
		else {
			self.setSelection(range);
			setTimeout(() => afterDelete(self), 0);
		}
	},
	'delete': (self, event, range) => {
		let root = self._root;
		let current, next, originalRange,
			cursorContainer, cursorOffset, nodeAfterCursor;
		self._removeZWS();
		// Record undo checkpoint.
		self.saveUndoState(range);
		// If not collapsed, delete contents
		if (!range.collapsed) {
			event.preventDefault();
			deleteContentsOfRange(range, root);
			afterDelete(self, range);
		}
		// If at end of block, merge next into this block
		else if (rangeDoesEndAtBlockBoundary(range, root)) {
			event.preventDefault();
			if (current = getStartBlockOfRange(range, root)) {
				// In case inline data has somehow got between blocks.
				fixContainer(current.parentNode, root);
				// Now get next block
				// Must not be at the very end of the text area.
				if (next = getNextBlock(current, root)) {
					// If not editable, just delete whole block.
					if (!next.isContentEditable) {
						detachUneditableNode(next, root);
						return;
					}
					// Otherwise merge.
					mergeWithBlock(current, next, range, root);
					// If deleted line between containers, merge newly adjacent
					// containers.
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
			}
		}
		// Otherwise, leave to browser but check afterwards whether it has
		// left behind an empty inline tag.
		else {
			// But first check if the cursor is just before an IMG tag. If so,
			// delete it ourselves, because the browser won't if it is not
			// inline.
			originalRange = range.cloneRange();
			moveRangeBoundariesUpTree(range, root, root, root);
			cursorContainer = range.endContainer;
			cursorOffset = range.endOffset;
			if (isElement(cursorContainer)) {
				nodeAfterCursor = cursorContainer.childNodes[ cursorOffset ];
				if (nodeAfterCursor?.nodeName === 'IMG') {
					event.preventDefault();
					detach(nodeAfterCursor);
					moveRangeBoundariesDownTree(range);
					afterDelete(self, range);
					return;
				}
			}
			self.setSelection(originalRange);
			setTimeout(() => afterDelete(self), 0);
		}
	},
	tab: (self, event, range) => {
		let root = self._root;
		let node, parent;
		self._removeZWS();
		// If no selection and at start of block
		if (range.collapsed && rangeDoesStartAtBlockBoundary(range, root)) {
			node = getStartBlockOfRange(range, root);
			// Iterate through the block's parents
			while ((parent = node.parentNode)) {
				// If we find a UL or OL (so are in a list, node must be an LI)
				if (parent.nodeName === 'UL' || parent.nodeName === 'OL') {
					// Then increase the list level
					event.preventDefault();
					self.increaseListLevel(range);
					break;
				}
				node = parent;
			}
		}
	},
	'shift-tab': (self, event, range) => {
		let root = self._root;
		let node;
		self._removeZWS();
		// If no selection and at start of block
		if (range.collapsed && rangeDoesStartAtBlockBoundary(range, root)) {
			// Break list
			node = range.startContainer;
			if (getClosest(node, root, 'UL,OL')) {
				event.preventDefault();
				self.decreaseListLevel(range);
			}
		}
	},
	space: (self, _, range) => {
		let root = self._root;
		self._recordUndoState(range, false);
		self._config.addLinks && addLinks(range.startContainer, root, self);
		self._getRangeAndRemoveBookmark(range);
/*
		// If the cursor is at the end of a link (<a>foo|</a>) then move it
		// outside of the link (<a>foo</a>|) so that the space is not part of
		// the link text.
		// SnappyMail: disabled as it fails in Firefox
		let node = range.endContainer;
		if (range.collapsed && range.endOffset === getLength(node)) {
			do {
				if (node.nodeName === 'A') {
					range.setStartAfter(node);
					break;
				}
			} while (!node.nextSibling && (node = node.parentNode) && node !== root);
		}
*/
		// Delete the selection if not collapsed
		if (!range.collapsed) {
			deleteContentsOfRange(range, root);
			self._ensureBottomLine();
			self.setSelection(range);
			self._updatePath(range, true);
		}

		self.setSelection(range);
	},
	arrowleft: self => self._removeZWS(),
	arrowright: self => self._removeZWS()
};

// System standard for page up/down on Mac is to just scroll, not move the
// cursor. On Linux/Windows, it should move the cursor, but some browsers don't
// implement this natively. Override to support it.
function _moveCursorTo(self, toStart) {
	let root = self._root,
		range = createRange(root, toStart ? 0 : root.childNodes.length);
	moveRangeBoundariesDownTree(range);
	self.setSelection(range);
	return self;
}
if (!isMac) {
	keyHandlers.pageup = self => _moveCursorTo(self, true);
	keyHandlers.pagedown = self => _moveCursorTo(self, false);
}

keyHandlers[ ctrlKey + 'b' ] = mapKeyToFormat('B');
keyHandlers[ ctrlKey + 'i' ] = mapKeyToFormat('I');
keyHandlers[ ctrlKey + 'u' ] = mapKeyToFormat('U');
keyHandlers[ ctrlKey + 'shift-7' ] = mapKeyToFormat('S');
keyHandlers[ ctrlKey + 'shift-5' ] = mapKeyToFormat('SUB', 'SUP');
keyHandlers[ ctrlKey + 'shift-6' ] = mapKeyToFormat('SUP', 'SUB');
keyHandlers[ ctrlKey + 'shift-8' ] = toggleList('UL', 'makeUnorderedList');
keyHandlers[ ctrlKey + 'shift-9' ] = toggleList('OL', 'makeOrderedList');
keyHandlers[ ctrlKey + '[' ] = changeIndentationLevel('decrease');
keyHandlers[ ctrlKey + ']' ] = changeIndentationLevel('increase');
keyHandlers[ ctrlKey + 'd' ] = mapKeyTo('toggleCode');
keyHandlers[ ctrlKey + 'y' ] = mapKeyTo('redo');
keyHandlers[ 'redo' ] = mapKeyTo('redo');
keyHandlers[ ctrlKey + 'z' ] = mapKeyTo('undo');
keyHandlers[ 'undo' ] = mapKeyTo('undo');
keyHandlers[ ctrlKey + 'shift-z' ] = mapKeyTo('redo');

class EditStack extends Array
{
	constructor(squire) {
		super();
		this.squire = squire;
		this.index = -1;
		this.inUndoState = false;

		this.threshold = -1; // -1 means no threshold
		this.limit = -1; // -1 means no limit
	}

	clear() {
		this.index = -1;
		this.length = 0;
	}

	stateChanged(/*canUndo, canRedo*/) {
		this.squire.fireEvent('undoStateChange', {
			canUndo: this.index > 0,
			canRedo: this.index + 1 < this.length
		});
		this.squire.fireEvent('input');
	}

	docWasChanged() {
		if (this.inUndoState) {
			this.inUndoState = false;
			this.stateChanged (/*true, false*/);
		} else
			this.squire.fireEvent('input');
	}

	// Leaves bookmark
	recordUndoState(range, replace) {
		replace = replace !== false && this.inUndoState;
		// Don't record if we're already in an undo state
		if (!this.inUndoState || replace) {
			// Advance pointer to new position
			let undoIndex = this.index;
			let undoThreshold = this.threshold;
			let undoLimit = this.limit;
			let squire = this.squire;
			let html;

			if (!replace) {
				++undoIndex;
			}
			undoIndex = Math.max(0, undoIndex);

			// Truncate stack if longer (i.e. if has been previously undone)
			this.length = Math.min(undoIndex + 1, this.length);

			// Get data
			if (range) {
				squire._saveRangeToBookmark(range);
			}
			html = squire._getHTML();

			// If this document is above the configured size threshold,
			// limit the number of saved undo states.
			// Threshold is in bytes, JS uses 2 bytes per character
			if (undoThreshold > -1 && html.length * 2 > undoThreshold
			 && undoLimit > -1 && undoIndex > undoLimit) {
				this.splice(0, undoIndex - undoLimit);
			}

			// Save data
			this[ undoIndex ] = html;
			this.index = undoIndex;
			this.inUndoState = true;
		}
	}

	saveUndoState(range) {
		let squire = this.squire;
		if (range === undefined) {
			range = squire.getSelection();
		}
		this.recordUndoState(range);
		squire._getRangeAndRemoveBookmark(range);
	}

	undo() {
		let squire = this.squire,
			undoIndex = this.index - 1;
		// Sanity check: must not be at beginning of the history stack
		if (undoIndex >= 0 || !this.inUndoState) {
			// Make sure any changes since last checkpoint are saved.
			this.recordUndoState(squire.getSelection(), false);
			this.index = undoIndex;
			squire._setHTML(this[ undoIndex ]);
			let range = squire._getRangeAndRemoveBookmark();
			if (range) {
				squire.setSelection(range);
			}
			this.inUndoState = true;
			this.stateChanged (/*undoIndex > 0, true*/);
		}
	}

	redo() {
		// Sanity check: must not be at end of stack and must be in an undo state.
		let squire = this.squire,
			undoIndex = this.index + 1;
		if (undoIndex < this.length && this.inUndoState) {
			this.index = undoIndex;
			squire._setHTML(this[ undoIndex ]);
			let range = squire._getRangeAndRemoveBookmark();
			if (range) {
				squire.setSelection(range);
			}
			this.stateChanged (/*true, undoIndex + 1 < this.length*/);
		}
	}
}

class Squire
{
	constructor(root, config) {
		this._root = root;

		this._events = {};

		this._isFocused = false;
		this._lastRange = null;

		this._hasZWS = false;

		this._lastAnchorNode = null;
		this._lastFocusNode = null;
		this._path = '';

		let _willUpdatePath;
		const selectionchange = () => {
			if (root.contains(doc.activeElement)) {
				if (this._isFocused && !_willUpdatePath) {
					_willUpdatePath = setTimeout(() => {
						_willUpdatePath = 0;
						this._updatePath(this.getSelection());
					}, 0);
				}
			} else {
				this.removeEventListener('selectionchange', selectionchange);
			}
		};
		this.addEventListener('selectstart', () => this.addEventListener('selectionchange', selectionchange));

		this.editStack = new EditStack(this);
		this._ignoreChange = false;
		this._ignoreAllChanges = false;

		this._mutation = new MutationObserver(()=>this._docWasChanged());
		this._mutation.observe(root, {
			childList: true,
			attributes: true,
			characterData: true,
			subtree: true
		});

		// On blur, restore focus except if the user taps or clicks to focus a
		// specific point. Can't actually use click event because focus happens
		// before click, so use mousedown/touchstart
		this._restoreSelection = false;
		// https://caniuse.com/mdn-api_document_pointerup_event
		this.addEventListener('blur', () => this._restoreSelection = true)
			.addEventListener('pointerdown mousedown touchstart', () => this._restoreSelection = false)
			.addEventListener('focus', () => this._restoreSelection && this.setSelection(this._lastRange))
			.addEventListener('cut', onCut)
			.addEventListener('copy', onCopy)
			// Need to monitor for shift key like this, as event.shiftKey is not available in paste event.
			.addEventListener('keydown keyup', event => this.isShiftDown = event.shiftKey)
			.addEventListener('paste', onPaste)
			.addEventListener('drop', onDrop)
			.addEventListener('keydown', onKey)
			.addEventListener('pointerup keyup mouseup touchend', ()=>this.getSelection());

		// Add key handlers
		this._keyHandlers = Object.create(keyHandlers);

		// Override default properties
		this.setConfig(config);

		root.setAttribute('contenteditable', 'true');
		// Grammarly breaks the editor, *sigh*
		root.setAttribute('data-gramm', 'false');

		// Remove Firefox's built-in controls
		try {
			doc.execCommand('enableObjectResizing', false, 'false');
			doc.execCommand('enableInlineTableEditing', false, 'false');
		} catch (error) {}

		root.__squire__ = this;

		// Need to register instance before calling setHTML, so that the fixCursor
		// function can lookup any default block tag options set.
		this.setHTML('');
	}

	setConfig(config) {
		this._config = mergeObjects({
			addLinks: true
		}, config, true);
		return this;
	}

	createDefaultBlock(children) {
		return fixCursor(
			createElement(blockTag, null, children),
			this._root
		);
	}

	getRoot() {
		return this._root;
	}

	// --- Events ---

	fireEvent(type, event) {
		let handlers = this._events[ type ];
		let isFocused, l, obj;
		// UI code, especially modal views, may be monitoring for focus events and
		// immediately removing focus. In certain conditions, this can cause the
		// focus event to fire after the blur event, which can cause an infinite
		// loop. So we detect whether we're actually focused/blurred before firing.
		if (/^(?:focus|blur)/.test(type)) {
			isFocused = this._root === doc.activeElement;
			if (type === 'focus') {
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
			event = event || {};
			if (event.type !== type) {
				event.type = type;
			}
			// Clone handlers array, so any handlers added/removed do not affect it.
			handlers = handlers.slice();
			l = handlers.length;
			while (l--) {
				obj = handlers[l];
				try {
					obj.handleEvent ? obj.handleEvent(event) : obj.call(this, event);
				} catch (error) {
					error.details = 'Squire: fireEvent error. Event type: ' + type;
					didError(error);
				}
			}
		}
		return this;
	}

	handleEvent(event) {
		this.fireEvent(event.type, event);
	}

	addEventListener(type, fn) {
		type.split(/\s+/).forEach(type=>{
			if (!fn) {
				didError({
					name: 'Squire: addEventListener with null or undefined fn',
					message: 'Event type: ' + type
				});
				return this;
			}
			let handlers = this._events[ type ];
			if (!handlers) {
				handlers = this._events[ type ] = [];
				customEvents[ type ]
				|| (type === 'selectionchange' ? doc : this._root)
					.addEventListener(type, this, {capture:true,passive:'touchstart'===type});
			}
			handlers.push(fn);
		});
		return this;
	}

	removeEventListener(type, fn) {
		let handlers = this._events[ type ];
		let l;
		if (handlers) {
			if (fn) {
				l = handlers.length;
				while (l--) {
					if (handlers[l] === fn) {
						handlers.splice(l, 1);
					}
				}
			} else {
				handlers.length = 0;
			}
			if (!handlers.length) {
				delete this._events[ type ];
				customEvents[ type ]
				|| (type === 'selectionchange' ? doc : this._root)
					.removeEventListener(type, this, true);
			}
		}
		return this;
	}

	// --- Selection and Path ---

	setSelection(range) {
		if (range) {
			this._lastRange = range;
			// If we're setting selection, that automatically, and synchronously, // triggers a focus event. So just store the selection and mark it as
			// needing restore on focus.
			if (this._isFocused) {
				// iOS bug: if you don't focus the iframe before setting the
				// selection, you can end up in a state where you type but the input
				// doesn't get directed into the contenteditable area but is instead
				// lost in a black hole. Very strange.
				if (isIOS) {
					win.focus();
				}
				let sel = win.getSelection();
				if (sel?.setBaseAndExtent) {
					sel.setBaseAndExtent(
						range.startContainer,
						range.startOffset,
						range.endContainer,
						range.endOffset,
					);
				} else if (sel) {
					// This is just for IE11
					sel.removeAllRanges();
					sel.addRange(range);
				}
			} else {
				this._restoreSelection = true;
			}
		}
		return this;
	}

	getSelection() {
		let sel = win.getSelection();
		let root = this._root;
		let range, startContainer, endContainer;
		// If not focused, always rely on cached range; another function may
		// have set it but the DOM is not modified until focus again
		if (this._isFocused && sel?.rangeCount) {
			range = sel.getRangeAt(0).cloneRange();
			startContainer = range.startContainer;
			endContainer = range.endContainer;
			// FF can return the range as being inside an <img>. WTF?
			if (startContainer && isLeaf(startContainer)) {
				range.setStartBefore(startContainer);
			}
			if (endContainer && isLeaf(endContainer)) {
				range.setEndBefore(endContainer);
			}
		}
		if (range && root.contains(range.commonAncestorContainer)) {
			this._lastRange = range;
		} else {
			range = this._lastRange;
			// Check the editor is in the live document; if not, the range has
			// probably been rewritten by the browser and is bogus
			if (!doc.contains(range.commonAncestorContainer)) {
				range = null;
			}
		}
		return range || createRange(root.firstChild, 0);
	}

	getSelectionClosest(selector) {
		let range = this.getSelection();
		return range && getClosest(range.commonAncestorContainer, this._root, selector);
	}

	getPath() {
		return this._path;
	}

	// --- Workaround for browsers that can't focus empty text nodes ---

	// WebKit bug: https://bugs.webkit.org/show_bug.cgi?id=15256

	_addZWS () {
		this._hasZWS = isWebKit;
		return doc.createTextNode(isWebKit ? ZWS : '');
	}
	_removeZWS () {
		if (this._hasZWS) {
			removeZWS(this._root);
			this._hasZWS = false;
		}
	}

	// --- Path change events ---

	_updatePath (range, force) {
		if (range) {
			let anchor = range.startContainer,
				focus = range.endContainer,
				newPath, node;
			if (force || anchor !== this._lastAnchorNode || focus !== this._lastFocusNode) {
				this._lastAnchorNode = anchor;
				this._lastFocusNode = focus;
				node = anchor === focus ? focus : null;
				newPath = (anchor && focus) ? (node ? getPath(focus, this._root) : '(selection)') : '';
				if (this._path !== newPath) {
					this._path = newPath;
					this.fireEvent('pathChange', { path: newPath, element: (!node || isElement(node)) ? node : node.parentElement });
				}
			}
			this.fireEvent(range.collapsed ? 'cursor' : 'select', {
				range: range
			});
		}
	}

	// --- Focus ---

	focus() {
		this._root.focus({ preventScroll: true });
		return this;
	}

	blur() {
		this._root.blur();
		return this;
	}

	// --- Bookmarking ---

	_saveRangeToBookmark (range) {
		let [startNode, endNode] = createBookmarkNodes(this),
			temp;

		insertNodeInRange(range, startNode);
		range.collapse(false);
		insertNodeInRange(range, endNode);

		// In a collapsed range, the start is sometimes inserted after the end!
		if (startNode.compareDocumentPosition(endNode) & DOCUMENT_POSITION_PRECEDING) {
			startNode.id = endSelectionId;
			endNode.id = startSelectionId;
			temp = startNode;
			startNode = endNode;
			endNode = temp;
		}

		range.setStartAfter(startNode);
		range.setEndBefore(endNode);
	}

	_getRangeAndRemoveBookmark (range) {
		let root = this._root,
			start = root.querySelector('#' + startSelectionId),
			end = root.querySelector('#' + endSelectionId);

		if (start && end) {
			let startContainer = start.parentNode,
				endContainer = end.parentNode,
				startOffset = indexOf(startContainer.childNodes, start),
				endOffset = indexOf(endContainer.childNodes, end);

			if (startContainer === endContainer) {
				--endOffset;
			}

			detach(start);
			detach(end);

			if (!range) {
				range = doc.createRange();
			}
			range.setStart(startContainer, startOffset);
			range.setEnd(endContainer, endOffset);

			// Merge any text nodes we split
			mergeInlines(startContainer, range);
			if (startContainer !== endContainer) {
				mergeInlines(endContainer, range);
			}

			// If we didn't split a text node, we should move into any adjacent
			// text node to current selection point
			if (range.collapsed) {
				startContainer = range.startContainer;
				if (startContainer.nodeType === TEXT_NODE) {
					endContainer = startContainer.childNodes[ range.startOffset ];
					if (!endContainer || endContainer.nodeType !== TEXT_NODE) {
						endContainer =
							startContainer.childNodes[ range.startOffset - 1 ];
					}
					if (endContainer?.nodeType === TEXT_NODE) {
						range.setStart(endContainer, 0);
						range.collapse(true);
					}
				}
			}
		}
		return range || null;
	}

	// --- Undo ---

	_docWasChanged () {
		nodeCategoryCache = new WeakMap();
		if (!this._ignoreAllChanges) {
			if (this._ignoreChange) {
				this._ignoreChange = false;
			} else {
				this.editStack.docWasChanged();
			}
		}
	}

	_recordUndoState (range, replace) {
		this.editStack.recordUndoState(range, replace);
	}

	saveUndoState(range) {
		this.editStack.saveUndoState(range);
	}

	undo() {
		this.editStack.undo();
	}

	redo() {
		this.editStack.redo();
	}

	// --- Inline formatting ---

	// Looks for matching tag and attributes, so won't work
	// if <strong> instead of <b> etc.
	hasFormat(tag, attributes, range) {
		// 1. Normalise the arguments and get selection
		tag = tag.toUpperCase();
		if (!range && !(range = this.getSelection())) {
			return false;
		}

		// Sanitize range to prevent weird IE artifacts
		if (!range.collapsed &&
				range.startContainer.nodeType === TEXT_NODE &&
				range.startOffset === range.startContainer.length &&
				range.startContainer.nextSibling) {
			range.setStartBefore(range.startContainer.nextSibling);
		}
		if (!range.collapsed &&
				range.endContainer.nodeType === TEXT_NODE &&
				range.endOffset === 0 &&
				range.endContainer.previousSibling) {
			range.setEndAfter(range.endContainer.previousSibling);
		}

		// If the common ancestor is inside the tag we require, we definitely
		// have the format.
		let root = this._root;
		let common = range.commonAncestorContainer;
		let walker, node;
		if (getNearest(common, root, tag, attributes)) {
			return true;
		}

		// If common ancestor is a text node and doesn't have the format, we
		// definitely don't have it.
		if (common.nodeType === TEXT_NODE) {
			return false;
		}

		// Otherwise, check each text node at least partially contained within
		// the selection and make sure all of them have the format we want.
		walker = createTreeWalker(common, SHOW_TEXT, node => isNodeContainedInRange(range, node));

		let seenNode = false;
		while (node = walker.nextNode()) {
			if (!getNearest(node, root, tag, attributes)) {
				return false;
			}
			seenNode = true;
		}

		return seenNode;
	}

	// Extracts the font-family and font-size (if any) of the element
	// holding the cursor. If there's a selection, returns an empty object.
	getFontInfo(range) {
		let fontInfo = {
			color: undefined,
			backgroundColor: undefined,
			family: undefined,
			size: undefined
		};
		let seenAttributes = 0;
		let element, style, attr;

		if (!range && !(range = this.getSelection())) {
			return fontInfo;
		}

		element = range.commonAncestorContainer;
		if (range.collapsed || element.nodeType === TEXT_NODE) {
			if (element.nodeType === TEXT_NODE) {
				element = element.parentNode;
			}
			while (seenAttributes < 4 && element) {
				if (style = element.style) {
					if (!fontInfo.color && (attr = style.color)) {
						fontInfo.color = attr;
						++seenAttributes;
					}
					if (!fontInfo.backgroundColor && (attr = style.backgroundColor)) {
						fontInfo.backgroundColor = attr;
						++seenAttributes;
					}
					if (!fontInfo.family && (attr = style.fontFamily)) {
						fontInfo.family = attr;
						++seenAttributes;
					}
					if (!fontInfo.size && (attr = style.fontSize)) {
						fontInfo.size = attr;
						++seenAttributes;
					}
				}
				element = element.parentNode;
			}
		}
		return fontInfo;
	}

	_addFormat (tag, attributes, range) {
		// If the range is collapsed we simply insert the node by wrapping
		// it round the range and focus it.
		let root = this._root;
		let el, walker, startContainer, endContainer, startOffset, endOffset,
			node, block;

		if (range.collapsed) {
			el = fixCursor(createElement(tag, attributes), root);
			insertNodeInRange(range, el);
			range.setStart(el.firstChild, el.firstChild.length);
			range.collapse(true);

			// Clean up any previous formats that may have been set on this block
			// that are unused.
			block = el;
			while (isInline(block)) {
				block = block.parentNode;
			}
			removeZWS(block, el);
		}
		// Otherwise we find all the textnodes in the range (splitting
		// partially selected nodes) and if they're not already formatted
		// correctly we wrap them in the appropriate tag.
		else {
			// Create an iterator to walk over all the text nodes under this
			// ancestor which are in the range and not already formatted
			// correctly.
			//
			// In Blink/WebKit, empty blocks may have no text nodes, just a <br>.
			// Therefore we wrap this in the tag as well, as this will then cause it
			// to apply when the user types something in the block, which is
			// presumably what was intended.
			//
			// IMG tags are included because we may want to create a link around
			// them, and adding other styles is harmless.
			walker = createTreeWalker(
				range.commonAncestorContainer,
				SHOW_ELEMENT_OR_TEXT,
				node => (node.nodeType === TEXT_NODE ||
							node.nodeName === 'BR' ||
							node.nodeName === 'IMG'
						) && isNodeContainedInRange(range, node)
			);

			// Start at the beginning node of the range and iterate through
			// all the nodes in the range that need formatting.
			startContainer = range.startContainer;
			startOffset = range.startOffset;
			endContainer = range.endContainer;
			endOffset = range.endOffset;

			// Make sure we start with a valid node.
			walker.currentNode = startContainer;
			if (filterAccept != walker.filter.acceptNode(startContainer)) {
				startContainer = walker.nextNode();
				startOffset = 0;
			}

			// If there are interesting nodes in the selection
			if (startContainer) {
				do {
					node = walker.currentNode;
					if (!getNearest(node, root, tag, attributes)) {
						// <br> can never be a container node, so must have a text node
						// if node == (end|start)Container
						if (node === endContainer && node.length > endOffset) {
							node.splitText(endOffset);
						}
						if (node === startContainer && startOffset) {
							node = node.splitText(startOffset);
							if (endContainer === startContainer) {
								endContainer = node;
								endOffset -= startOffset;
							}
							startContainer = node;
							startOffset = 0;
						}
						el = createElement(tag, attributes);
						node.replaceWith(el);
						el.append(node);
					}
				} while (walker.nextNode());

				// If we don't finish inside a text node, offset may have changed.
				if (endContainer.nodeType !== TEXT_NODE) {
					if (node.nodeType === TEXT_NODE) {
						endContainer = node;
						endOffset = node.length;
					} else {
						// If <br>, we must have just wrapped it, so it must have only
						// one child
						endContainer = node.parentNode;
						endOffset = 1;
					}
				}

				// Now set the selection to as it was before
				range = createRange(
					startContainer, startOffset, endContainer, endOffset);
			}
		}
		return range;
	}

	_removeFormat (tag, attributes, range, partial) {
		// Add bookmark
		this._saveRangeToBookmark(range);

		// We need a node in the selection to break the surrounding
		// formatted text.
		let fixer;
		if (range.collapsed) {
			fixer = this._addZWS();
			insertNodeInRange(range, fixer);
		}

		// Find block-level ancestor of selection
		let root = range.commonAncestorContainer;
		while (isInline(root)) {
			root = root.parentNode;
		}

		// Find text nodes inside formatTags that are not in selection and
		// add an extra tag with the same formatting.
		let startContainer = range.startContainer,
			startOffset = range.startOffset,
			endContainer = range.endContainer,
			endOffset = range.endOffset,
			toWrap = [],
			examineNode = (node, exemplar) => {
				// If the node is completely contained by the range then
				// we're going to remove all formatting so ignore it.
				if (isNodeContainedInRange(range, node, false)) {
					return;
				}

				let isText = (node.nodeType === TEXT_NODE),
					child, next;

				// If not at least partially contained, wrap entire contents
				// in a clone of the tag we're removing and we're done.
				if (!isNodeContainedInRange(range, node)) {
					// Ignore bookmarks and empty text nodes
					if (node.nodeName !== 'INPUT' && (!isText || node.data)) {
						toWrap.push([ exemplar, node ]);
					}
					return;
				}

				// Split any partially selected text nodes.
				if (isText) {
					if (node === endContainer && endOffset !== node.length) {
						toWrap.push([ exemplar, node.splitText(endOffset) ]);
					}
					if (node === startContainer && startOffset) {
						node.splitText(startOffset);
						toWrap.push([ exemplar, node ]);
					}
				}
				// If not a text node, recurse onto all children.
				// Beware, the tree may be rewritten with each call
				// to examineNode, hence find the next sibling first.
				else {
					for (child = node.firstChild; child; child = next) {
						next = child.nextSibling;
						examineNode(child, exemplar);
					}
				}
			},
			formatTags = Array.prototype.filter.call(
				root.getElementsByTagName(tag),
				el => isNodeContainedInRange(range, el) && hasTagAttributes(el, tag, attributes)
			);

		partial || formatTags.forEach(node => examineNode(node, node));

		// Now wrap unselected nodes in the tag
		toWrap.forEach(([exemplar, node]) => {
			let el = exemplar.cloneNode(false);
			node.replaceWith(el);
			el.append(node);
		});
		// and remove old formatting tags.
		formatTags.forEach(el => el.replaceWith(empty(el)));

		// Merge adjacent inlines:
		this._getRangeAndRemoveBookmark(range);
		fixer && range.collapse(false);
		mergeInlines(root, range);

		return range;
	}

	toggleTag(name, remove) {
		let range = this.getSelection();
		if (this.hasFormat(name, null, range)) {
			this.changeFormat (null, { tag: name }, range);
		} else {
			this.changeFormat ({ tag: name }, remove ? { tag: remove } : null, range);
		}
	}

	changeFormat(add, remove, range, partial) {
		// Normalise the arguments and get selection
		if (range || (range = this.getSelection())) {
			// Save undo checkpoint
			this.saveUndoState(range);

			if (remove) {
				range = this._removeFormat(remove.tag.toUpperCase(),
					remove.attributes || {}, range, partial);
			}

			if (add) {
				range = this._addFormat(add.tag.toUpperCase(),
					add.attributes || {}, range);
			}

			this.setSelection(range);
			this._updatePath(range, true);
		}
		return this;
	}

	// --- Block formatting ---

	forEachBlock(fn, range) {
		if (range || (range = this.getSelection())) {
			// Save undo checkpoint
			this.saveUndoState(range);

			let root = this._root;
			let start = getStartBlockOfRange(range, root);
			let end = getEndBlockOfRange(range, root);
			if (start && end) {
				do {
					if (fn(start) || start === end) { break; }
				} while (start = getNextBlock(start, root));
			}

			this.setSelection(range);

			// Path may have changed
			this._updatePath(range, true);
		}
		return this;
	}

	modifyBlocks(modify, range) {
		if (range || (range = this.getSelection())) {
			// 1. Save undo checkpoint and bookmark selection
			this._recordUndoState(range);

			let root = this._root;
			let frag;

			// 2. Expand range to block boundaries
			expandRangeToBlockBoundaries(range, root);

			// 3. Remove range.
			moveRangeBoundariesUpTree(range, root, root, root);
			frag = extractContentsOfRange(range, root, root);

			// 4. Modify tree of fragment and reinsert.
			insertNodeInRange(range, modify.call(this, frag));

			// 5. Merge containers at edges
			if (range.endOffset < range.endContainer.childNodes.length) {
				mergeContainers(range.endContainer.childNodes[ range.endOffset ], root);
			}
			mergeContainers(range.startContainer.childNodes[ range.startOffset ], root);

			// 6. Restore selection
			this._getRangeAndRemoveBookmark(range);
			this.setSelection(range);
			this._updatePath(range, true);
		}
		return this;
	}

	increaseListLevel(range) {
		if (range || (range = this.getSelection())) {
			let root = this._root;
			let listSelection = getListSelection(range, root);
			if (listSelection) {
				let list = listSelection[0];
				let startLi = listSelection[1];
				let endLi = listSelection[2];
				if (startLi && startLi !== list.firstChild) {
					// Save undo checkpoint and bookmark selection
					this._recordUndoState(range);

					// Increase list depth
					let type = list.nodeName;
					let newParent = startLi.previousSibling;
					let next;
					if (newParent.nodeName !== type) {
						newParent = createElement(type);
						startLi.before(newParent);
					}
					do {
						next = startLi === endLi ? null : startLi.nextSibling;
						newParent.append(startLi);
					} while ((startLi = next));
					next = newParent.nextSibling;
					next && mergeContainers(next, root);

					// Restore selection
					this._getRangeAndRemoveBookmark(range);
					this.setSelection(range);
					this._updatePath(range, true);
				}
			}
		}
		return this.focus();
	}

	decreaseListLevel(range) {
		if (range || (range = this.getSelection())) {
			let root = this._root;
			let listSelection = getListSelection(range, root);
			if (listSelection) {
				let list = listSelection[0];
				let startLi = listSelection[1] || list.firstChild;
				let endLi = listSelection[2] || list.lastChild;
				let newParent, next, insertBefore, makeNotList;

				// Save undo checkpoint and bookmark selection
				this._recordUndoState(range);

				if (startLi) {
					// Find the new parent list node
					newParent = list.parentNode;

					// Split list if necesary
					insertBefore = !endLi.nextSibling ?
						list.nextSibling :
						split(list, endLi.nextSibling, newParent, root);

					if (newParent !== root && newParent.nodeName === 'LI') {
						newParent = newParent.parentNode;
						while (insertBefore) {
							next = insertBefore.nextSibling;
							endLi.append(insertBefore);
							insertBefore = next;
						}
						insertBefore = list.parentNode.nextSibling;
					}

					makeNotList = !/^[OU]L$/.test(newParent.nodeName);
					do {
						next = startLi === endLi ? null : startLi.nextSibling;
						startLi.remove();
						if (makeNotList && startLi.nodeName === 'LI') {
							startLi = this.createDefaultBlock([ empty(startLi) ]);
						}
						newParent.insertBefore(startLi, insertBefore);
					} while ((startLi = next));
				}

				list.firstChild || detach(list);

				insertBefore && mergeContainers(insertBefore, root);

				// Restore selection
				this._getRangeAndRemoveBookmark(range);
				this.setSelection(range);
				this._updatePath(range, true);
			}
		}
		return this.focus();
	}

	_ensureBottomLine () {
		let root = this._root;
		let last = root.lastElementChild;
		if (!last || last.nodeName !== blockTag || !isBlock(last)) {
			root.append(this.createDefaultBlock());
		}
	}

	// --- Get/Set data ---

	_getHTML () {
		return this._root.innerHTML;
	}

	_setHTML (html) {
		let root = this._root;
		let node = root;
		empty(root);
		root.appendChild(this._config.sanitizeToDOMFragment(html, false));
		do {
			fixCursor(node, root);
		} while (node = getNextBlock(node, root));
		this._ignoreChange = true;
	}

	getHTML(withBookMark) {
		let html, range;
		if (withBookMark && (range = this.getSelection())) {
			this._saveRangeToBookmark(range);
		}
		html = this._getHTML().replace(/\u200B/g, '');
		range && this._getRangeAndRemoveBookmark(range);
		return html;
	}

	setHTML(html) {
		let root = this._root,
			// Parse HTML into DOM tree
			frag = this._config.sanitizeToDOMFragment(html, false),
			child;

		cleanTree(frag);
		cleanupBRs(frag, root, false);

		fixContainer(frag, root);

		// Fix cursor
		let node, walker = getBlockWalker(frag, root);
		while ((node = walker.nextNode()) && node !== root) {
			fixCursor(node, root);
		}

		// Don't fire an input event
		this._ignoreChange = true;

		// Remove existing root children
		while (child = root.lastChild) {
			child.remove();
		}

		// And insert new content
		root.append(frag);
		fixCursor(root, root);

		// Reset the undo stack
		this.editStack.clear();

		// Record undo state
		let range = this._getRangeAndRemoveBookmark() ||
			createRange(root.firstChild, 0);
		this.saveUndoState(range);
		// IE will also set focus when selecting text so don't use
		// setSelection. Instead, just store it in lastSelection, so if
		// anything calls getSelection before first focus, we have a range
		// to return.
		this._lastRange = range;
		this._restoreSelection = true;
		this._updatePath(range, true);

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
			// Get containing block node.
			let root = this._root;
			let splitNode = getStartBlockOfRange(range, root) || root;
			let parent, nodeAfterSplit;
			// While at end of container node, move up DOM tree.
			while (splitNode !== root && !splitNode.nextSibling) {
				splitNode = splitNode.parentNode;
			}
			// If in the middle of a container node, split up to root.
			if (splitNode !== root) {
				parent = splitNode.parentNode;
				nodeAfterSplit = split(parent, splitNode.nextSibling, root, root);
			}
			if (nodeAfterSplit) {
				nodeAfterSplit.before(el);
			} else {
				root.append(el);
				// Insert blank line below block.
				nodeAfterSplit = this.createDefaultBlock();
				root.append(nodeAfterSplit);
			}
			range.setStart(nodeAfterSplit, 0);
			range.setEnd(nodeAfterSplit, 0);
			moveRangeBoundariesDownTree(range);
		}
		this.focus();
		this.setSelection(range);
		this._updatePath(range);

		return this;
	}

	insertImage(src, attributes) {
		let img = createElement('IMG', mergeObjects({
			src: src
		}, attributes, true));
		this.insertElement(img);
		return img;
	}

	// Insert HTML at the cursor location. If the selection is not collapsed
	// insertTreeFragmentIntoRange will delete the selection so that it is replaced
	// by the html being inserted.
	insertHTML(html, isPaste) {
		let range = this.getSelection();

		// Edge doesn't just copy the fragment, but includes the surrounding guff
		// including the full <head> of the page. Need to strip this out.
		if (isPaste) {
			let startFragmentIndex = html.indexOf('<!--StartFragment-->'),
				endFragmentIndex = html.lastIndexOf('<!--EndFragment-->');
			if (startFragmentIndex > -1 && endFragmentIndex > -1) {
				html = html.slice(startFragmentIndex + 20, endFragmentIndex);
			}
		}

		let frag = this._config.sanitizeToDOMFragment(html, isPaste);

		// Record undo checkpoint
		this.saveUndoState(range);

		try {
			let root = this._root, node = frag;

			addLinks(frag, frag, this);
			cleanTree(frag);
			cleanupBRs(frag, root, false);
			removeEmptyInlines(frag);
			frag.normalize();

			while (node = getNextBlock(node, frag)) {
				fixCursor(node, root);
			}

			insertTreeFragmentIntoRange(range, frag, root);
			range.collapse(false);

			// After inserting the fragment, check whether the cursor is inside
			// an <a> element and if so if there is an equivalent cursor
			// position after the <a> element. If there is, move it there.
			moveRangeBoundaryOutOf(range, 'A', root);

			this._ensureBottomLine();

			this.setSelection(range);
			this._updatePath(range, true);
			// Safari sometimes loses focus after paste. Weird.
			isPaste && this.focus();
		} catch (error) {
			didError(error);
		}
		return this;
	}

	insertPlainText(plainText, isPaste) {
		let range = this.getSelection();
		if (range.collapsed && getClosest(range.startContainer, this._root, 'PRE')) {
			let node = range.startContainer;
			let offset = range.startOffset;
			let text;
			if (node?.nodeType !== TEXT_NODE) {
				text = doc.createTextNode('');
				node?.childNodes[ offset ].before(text);
				node = text;
				offset = 0;
			}

			node.insertData(offset, plainText);
			range.setStart(node, offset + plainText.length);
			range.collapse(true);
			this.setSelection(range);
			return this;
		}
		let lines = plainText.split(/\r?\n/),
			closeBlock = '</' + blockTag + '>',
			openBlock = '<' + blockTag + '>';

		lines.forEach((line, i) => {
			line = escapeHTML(line).replace(/ (?=(?: |$))/g, NBSP);
			// We don't wrap the first line in the block, so if it gets inserted
			// into a blank line it keeps that line's formatting.
			// Wrap each line in <div></div>
			lines[i] = i ? openBlock + (line || '<BR>') + closeBlock : line;
		});
		return this.insertHTML(lines.join(''), isPaste);
	}

	// --- Formatting ---

	makeLink(url, attributes) {
		let range = this.getSelection();
		if (range.collapsed) {
			insertNodeInRange(
				range,
				doc.createTextNode(url.replace(/^[^:]*:\/*/, ''))
			);
		}
		attributes = mergeObjects(
			mergeObjects({
				href: url
			}, attributes, true),
			null,
			false
		);

		this.changeFormat({
			tag: 'A',
			attributes: attributes
		}, {
			tag: 'A'
		}, range);
		return this.focus();
	}

	removeLink() {
		this.changeFormat(null, {
			tag: 'A'
		}, this.getSelection(), true);
		return this.focus();
	}

	setStyle(style) {
		let range = this.getSelection();
		let start = range?.startContainer || {};
		let end = range ? range.endContainer : 0;
		// When the selection is all the text inside an element, set style on the element itself
		if (TEXT_NODE === start?.nodeType && 0 === range.startOffset && start === end && end.length === range.endOffset) {
			this.saveUndoState(range);
			setStyle(start.parentNode, style);
			this.setSelection(range);
			this._updatePath(range, true);
		}
		// Else create a span element
		else {
			this.changeFormat({
				tag: 'SPAN',
				attributes: {
					style: style
				}
			}, null, range);
		}
		return this.focus();
	}

	// ---

	code() {
		let range = this.getSelection();
		if (range.collapsed || isContainer(range.commonAncestorContainer)) {
			this.modifyBlocks(frag => {
				let root = this._root;
				let output = doc.createDocumentFragment();
				let walker = getBlockWalker(frag, root);
				let node;
				// 1. Extract inline content; drop all blocks and contains.
				while ((node = walker.nextNode())) {
					// 2. Replace <br> with \n in content
					node.querySelectorAll('BR').forEach(br => {
						if (!isLineBreak(br, false)) {
							detach(br);
						} else {
							br.replaceWith(doc.createTextNode('\n'));
						}
					});
					// 3. Remove <code>; its format clashes with <pre>
					node.querySelectorAll('CODE').forEach(el => detach(el));
					if (output.childNodes.length) {
						output.append(doc.createTextNode('\n'));
					}
					output.append(empty(node));
				}
				// 4. Replace nbsp with regular sp
				walker = createTreeWalker(output, SHOW_TEXT);
				while ((node = walker.nextNode())) {
					node.data = node.data.replace(NBSP, ' '); // nbsp -> sp
				}
				output.normalize();
				return fixCursor(createElement('PRE',
					null, [
						output
					]), root);
			}, range);
		} else {
			this.changeFormat({
				tag: 'CODE'
			}, null, range);
		}
		return this.focus();
	}

	removeCode() {
		let range = this.getSelection();
		let ancestor = range.commonAncestorContainer;
		let inPre = getClosest(ancestor, this._root, 'PRE');
		if (inPre) {
			this.modifyBlocks(frag => {
				let root = this._root;
				let pres = frag.querySelectorAll('PRE');
				let l = pres.length;
				let pre, walker, node, value, contents, index;
				while (l--) {
					pre = pres[l];
					walker = createTreeWalker(pre, SHOW_TEXT);
					while ((node = walker.nextNode())) {
						value = node.data;
						value = value.replace(/ (?=)/g, NBSP); // sp -> nbsp
						contents = doc.createDocumentFragment();
						while ((index = value.indexOf('\n')) > -1) {
							contents.append(
								doc.createTextNode(value.slice(0, index))
							);
							contents.append(createElement('BR'));
							value = value.slice(index + 1);
						}
						node.before(contents);
						node.data = value;
					}
					fixContainer(pre, root);
					pre.replaceWith(empty(pre));
				}
				return frag;
			}, range);
		} else {
			this.changeFormat(null, { tag: 'CODE' }, range);
		}
		return this.focus();
	}

	toggleCode() {
		return (this.hasFormat('PRE') || this.hasFormat('CODE'))
			? this.removeCode()
			: this.code();
	}

	// ---

	changeIndentationLevel(direction) {
		let parent = this.getSelectionClosest('UL,OL,BLOCKQUOTE');
		if (parent || 'increase' === direction) {
			let method = (!parent || 'BLOCKQUOTE' === parent.nodeName) ? 'Quote' : 'List';
			this[ direction + method + 'Level' ]();
		}
	}

	increaseQuoteLevel(range) {
		this.modifyBlocks(
			frag => createElement('BLOCKQUOTE', null, [ frag ]),
			range
		);
		return this.focus();
	}

	decreaseQuoteLevel(range) {
		this.modifyBlocks(
			frag => {
				Array.prototype.filter.call(frag.querySelectorAll('blockquote'), el =>
					!getClosest(el.parentNode, frag, 'BLOCKQUOTE')
				).forEach(el => el.replaceWith(empty(el)));
				return frag;
			},
			range
		);
		return this.focus();
	}

	makeUnorderedList() {
		this.modifyBlocks(frag => makeList(this, frag, 'UL'));
		return this.focus();
	}

	makeOrderedList() {
		this.modifyBlocks(frag => makeList(this, frag, 'OL'));
		return this.focus();
	}

	removeList() {
		this.modifyBlocks(frag => {
			let root = this._root,
				listFrag;
			frag.querySelectorAll('UL, OL').forEach(list => {
				listFrag = empty(list);
				fixContainer(listFrag, root);
				list.replaceWith(listFrag);
			});

			frag.querySelectorAll('LI').forEach(item => {
				if (isBlock(item)) {
					item.replaceWith(
						this.createDefaultBlock([ empty(item) ])
					);
				} else {
					fixContainer(item, root);
					item.replaceWith(empty(item));
				}
			});

			return frag;
		});
		return this.focus();
	}

	bold() { this.toggleTag('B'); }
	italic() { this.toggleTag('I'); }
	underline() { this.toggleTag('U'); }
	strikethrough() { this.toggleTag('S'); }
	subscript() { this.toggleTag('SUB', 'SUP'); }
	superscript() { this.toggleTag('SUP', 'SUB'); }
}

win.Squire = Squire;

})(document);

/* eslint max-len: 0 */

(doc => {

const
	removeElements = 'HEAD,LINK,META,NOSCRIPT,SCRIPT,TEMPLATE,TITLE',
	allowedElements = 'A,B,BLOCKQUOTE,BR,DIV,FONT,H1,H2,H3,H4,H5,H6,HR,IMG,LI,OL,P,SPAN,STRONG,TABLE,TD,TH,TR,U,UL',
	allowedAttributes = 'abbr,align,background,bgcolor,border,cellpadding,cellspacing,class,color,colspan,dir,face,frame,height,href,hspace,id,lang,rowspan,rules,scope,size,src,style,target,type,usemap,valign,vspace,width'.split(','),

	i18n = (str, def) => rl.i18n(str) || def,

	ctrlKey = shortcuts.getMetaKey() + ' + ',

	createElement = name => doc.createElement(name),

	tpl = createElement('template'),

	trimLines = html => html.trim().replace(/^(<div>\s*<br\s*\/?>\s*<\/div>)+/, '').trim(),
	htmlToPlain = html => rl.Utils.htmlToPlain(html).trim(),
	plainToHtml = text => rl.Utils.plainToHtml(text),

	forEachObjectValue = (obj, fn) => Object.values(obj).forEach(fn),

	getFragmentOfChildren = parent => {
		let frag = doc.createDocumentFragment();
		frag.append(...parent.childNodes);
		return frag;
	},

	SquireDefaultConfig = {
/*
		addLinks: true // allow_smart_html_links
*/
		sanitizeToDOMFragment: (html, isPaste/*, squire*/) => {
			tpl.innerHTML = (html||'')
				.replace(/<\/?(BODY|HTML)[^>]*>/gi,'')
				.replace(/<!--[^>]+-->/g,'')
				.replace(/<span[^>]*>\s*<\/span>/gi,'')
				.trim();
			tpl.querySelectorAll('a:empty,span:empty').forEach(el => el.remove());
			if (isPaste) {
				tpl.querySelectorAll(removeElements).forEach(el => el.remove());
				tpl.querySelectorAll('*').forEach(el => {
					if (!el.matches(allowedElements)) {
						el.replaceWith(getFragmentOfChildren(el));
					} else if (el.hasAttributes()) {
						[...el.attributes].forEach(attr => {
							let name = attr.name.toLowerCase();
							if (!allowedAttributes.includes(name)) {
								el.removeAttribute(name);
							}
						});
					}
				});
			}
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
						cmd: s => this.setMode('plain' == s.value ? 'plain' : 'wysiwyg'),
						hint: i18n('EDITOR/TEXT_SWITCHER_PLAIN_TEXT', 'Plain')
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
						select: ['11px','13px','16px','20px','24px','30px'],
						cmd: s => squire.setStyle({ fontSize: s.value })
					}
				},
				colors: {
					textColor: {
						html: 'A<sub>▾</sub>',
						cmd: doClr('color'),
						hint: 'Text color'
					},
					backgroundColor: {
						html: '🎨', /* ▧ */
						cmd: doClr('backgroundColor'),
						hint: 'Background color'
					},
				},
				inline: {
					bold: {
						html: 'B',
						cmd: () => this.doAction('bold'),
						key: 'B',
						hint: 'Bold',
						matches: 'B,STRONT'
					},
					italic: {
						html: 'I',
						cmd: () => this.doAction('italic'),
						key: 'I',
						hint: 'Italic',
						matches: 'I'
					},
					underline: {
						html: '<u>U</u>',
						cmd: () => this.doAction('underline'),
						key: 'U',
						hint: 'Underline',
						matches: 'U'
					},
					strike: {
						html: '<s>S</s>',
						cmd: () => this.doAction('strikethrough'),
						key: 'Shift + 7',
						hint: 'Strikethrough',
						matches: 'S'
					},
					sub: {
						html: 'Xₙ',
						cmd: () => this.doAction('subscript'),
						key: 'Shift + 5',
						hint: 'Subscript',
						matches: 'SUB'
					},
					sup: {
						html: 'Xⁿ',
						cmd: () => this.doAction('superscript'),
						key: 'Shift + 6',
						hint: 'Superscript',
						matches: 'SUP'
					}
				},
				block: {
					ol: {
						html: '#',
						cmd: () => this.doList('OL'),
						key: 'Shift + 8',
						hint: 'Ordered list',
						matches: 'OL'
					},
					ul: {
						html: '⋮',
						cmd: () => this.doList('UL'),
						key: 'Shift + 9',
						hint: 'Unordered list',
						matches: 'UL'
					},
					quote: {
						html: '"',
						cmd: () => {
							let parent = squire.getSelectionClosest('UL,OL,BLOCKQUOTE')?.nodeName;
							('BLOCKQUOTE' == parent) ? squire.decreaseQuoteLevel() : squire.increaseQuoteLevel();
						},
						hint: 'Blockquote',
						matches: 'BLOCKQUOTE'
					},
					indentDecrease: {
						html: '⇤',
						cmd: () => squire.changeIndentationLevel('decrease'),
						key: ']',
						hint: 'Decrease indent'
					},
					indentIncrease: {
						html: '⇥',
						cmd: () => squire.changeIndentationLevel('increase'),
						key: '[',
						hint: 'Increase indent'
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
						hint: 'Link',
						matches: 'A'
					},
					imageUrl: {
						html: '🖼️',
						cmd: () => {
							let node = squire.getSelectionClosest('IMG'),
								src = prompt("Image", node?.src || "https://");
							src?.length ? squire.insertImage(src) : (node && squire.detach(node));
						},
						hint: 'Image URL',
						matches: 'IMG'
					},
					imageUpload: {
						html: '📂️',
						cmd: () => browseImage.click(),
						hint: 'Image select',
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
						key: 'Z',
						hint: 'Undo'
					},
					redo: {
						html: '↷',
						cmd: () => squire.redo(),
						key: 'Y',
						hint: 'Redo'
					},
					source: {
						html: '👁',
						cmd: btn => {
							this.setMode('source' == this.mode ? 'wysiwyg' : 'source');
							btn.classList.toggle('active', 'source' == this.mode);
						},
						hint: i18n('EDITOR/TEXT_SWITCHER_SOURCE', 'Source')
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
		this.mode = ''; // 'plain' | 'wysiwyg'
		this.__plain = {
			getRawData: () => this.plain.value,
			setRawData: plain => this.plain.value = plain
		};

		this.container = container;
		this.squire = squire;
		this.plain = plain;
		this.wysiwyg = wysiwyg;

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
						Object.entries(cfg.select).forEach(([label, options]) => {
							let group = createElement('optgroup');
							group.label = label;
							Object.entries(options).forEach(([text, value]) => {
								var option = new Option(text, value);
								option.style[action] = value;
								group.append(option);
							});
							input.append(group);
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
		squire.addEventListener('undoStateChange', state => {
			changes.undo.input.disabled = !state.canUndo;
			changes.redo.input.disabled = !state.canRedo;
		});

//		squire.addEventListener('focus', () => shortcuts.off());
//		squire.addEventListener('blur', () => shortcuts.on());

		container.append(toolbar, wysiwyg, plain);

		squire.addEventListener('pathChange', e => {
			forEachObjectValue(actions, entries => {
				forEachObjectValue(entries, cfg => {
//					cfg.matches && cfg.input.classList.toggle('active', e.element && e.element.matches(cfg.matches));
					cfg.matches && cfg.input.classList.toggle('active', e.element && e.element.closestWithin(cfg.matches, squire.getRoot()));
				});
			});
		});
/*
		squire.addEventListener('cursor', e => {
			console.dir({cursor:e.range});
		});
		squire.addEventListener('select', e => {
			console.dir({select:e.range});
		});
*/

		// CKEditor gimmicks used by HtmlEditor
		this.plugins = {
			plain: true
		};
		this.focusManager = {
			hasFocus: () => squire._isFocused,
			blur: () => squire.blur()
		};
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

	// CKeditor gimmicks used by HtmlEditor
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
