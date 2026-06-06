/* SnappyMail Webmail (c) SnappyMail | Licensed under AGPL v3 */
(function () {
	'use strict';

	/* eslint quote-props: 0 */

	const /**
	 * @enum {number}
	 */
	SaveSettingStatus = {
		Saving: -2,
		Idle: -1,
		Success: 1,
		Failed: 0
	},

	/**
	 * @enum {number}
	 */
	Notifications = {
		RequestError: 1,
		RequestAborted: 2,
		RequestTimeout: 3,

		// Global
		InvalidToken: 101,
		AuthError: 102,

		// User
		ConnectionError: 104,
		DomainNotAllowed: 109,
		AccountNotAllowed: 110,
		CryptKeyError: 111,

		ContactsSyncError: 140,

		CantGetMessageList: 201,
		CantGetMessage: 202,
		CantDeleteMessage: 203,
		CantMoveMessage: 204,
		CantCopyMessage: 205,

		CantSaveMessage: 301,
		CantSendMessage: 302,
		InvalidRecipients: 303,

		CantSaveFilters: 351,
		CantGetFilters: 352,
		CantActivateFiltersScript: 353,
		CantDeleteFiltersScript: 354,
	//	FiltersAreNotCorrect: 355,

		CantCreateFolder: 400,
		CantRenameFolder: 401,
		CantDeleteFolder: 402,
		CantSubscribeFolder: 403,
		CantUnsubscribeFolder: 404,
		CantDeleteNonEmptyFolder: 405,

	//	CantSaveSettings: 501,

		DomainAlreadyExists: 601,

		DemoSendMessageError: 750,
		DemoAccountError: 751,

		AccountAlreadyExists: 801,
		AccountDoesNotExist: 802,
		AccountSwitchFailed: 803,

		MailServerError: 901,
		ClientViewError: 902,
		InvalidInputArgument: 903,

		JsonFalse: 950,
		JsonParse: 952,
	//	JsonTimeout: 953,

		UnknownError: 999,

		// Admin
		CantInstallPackage: 701,
		CantDeletePackage: 702,
		InvalidPluginPackage: 703,
		UnsupportedPluginPackage: 704,
		CantSavePluginSettings: 705
	};

	const isArray = Array.isArray,
		arrayLength = array => isArray(array) && array.length,
		isFunction = v => typeof v === 'function',
		pString = value => null != value ? '' + value : '',

		forEachObjectEntry = (obj, fn) => Object.entries(obj).forEach(([key, value]) => fn(key, value)),

		pInt = (value, defaultValue = 0) => {
			value = parseInt(value, 10);
			return isFinite(value) ? value : defaultValue;
		},

		defaultOptionsAfterRender = (domItem, item) =>
			item && undefined !== item.disabled && domItem?.classList.toggle('disabled', domItem.disabled = item.disabled),

		getKeyByValue = (o, v) => Object.keys(o).find(key => o[key] === v);

	let keyScopeFake = 'all';

	const ScopeMenu = 'Menu',

		doc = document,

		$htmlCL = doc.documentElement.classList,

		elementById = id => doc.getElementById(id),

		appEl = elementById('rl-app'),

		Settings = rl.settings,
		SettingsGet = Settings.get,
		SettingsAdmin = name => (SettingsGet('Admin') || {})[name],
		SettingsCapa = name => name && !!(SettingsGet('Capa') || {})[name],

		dropdownVisibility = ko.observable(false).extend({ rateLimit: 0 }),

		leftPanelDisabled = ko.observable(false),
		toggleLeftPanel = () => leftPanelDisabled(!leftPanelDisabled()),

		createElement = (name, attr) => {
			let el = doc.createElement(name);
			attr && Object.entries(attr).forEach(([k,v]) => el.setAttribute(k,v));
			return el;
		},

		fireEvent = (name, detail, cancelable) => dispatchEvent(
			new CustomEvent(name, {detail:detail, cancelable: !!cancelable})
		),

		addShortcut = (...args) => shortcuts.add(...args),

		// keys / shortcuts
		keyScopeReal = ko.observable('all'),
		keyScope = value => {
			if (!value) {
				return keyScopeFake;
			}
			if (ScopeMenu !== value) {
				keyScopeFake = value;
				if (dropdownVisibility()) {
					value = ScopeMenu;
				}
			}
			keyScopeReal(value);
			shortcuts.setScope(value);
		};

	dropdownVisibility.subscribe(value => {
		if (value) {
			keyScope(ScopeMenu);
		} else if (ScopeMenu === shortcuts.getScope()) {
			keyScope(keyScopeFake);
		}
	});

	leftPanelDisabled.subscribe(value => $htmlCL.toggle('rl-left-panel-disabled', value));

	const
		BASE = doc.location.pathname.replace(/\/+$/,'') + '/',
		HASH_PREFIX = '#/',

		adminPath = () => rl.adminArea() && !SettingsAdmin('host'),

		prefix = () => BASE + '?' + (adminPath() ? SettingsAdmin('path') : '');

	const SUB_QUERY_PREFIX = '&q[]=',

		/**
		 * @param {string=} startupUrl
		 * @returns {string}
		 */
		root = () => HASH_PREFIX,

		/**
		 * @returns {string}
		 */
		logoutLink = () => adminPath() ? prefix() : BASE,

		/**
		 * @param {string} type
		 * @param {string} hash
		 * @param {string=} customSpecSuffix
		 * @returns {string}
		 */
		serverRequestRaw = (type, hash) =>
			BASE + '?/Raw/' + SUB_QUERY_PREFIX + '/'
			+ '0/' // Settings.get('accountHash') ?
			+ (type
				? type + '/' + (hash ? SUB_QUERY_PREFIX + '/' + hash : '')
				: ''),

		//			+ b64EncodeJSONSafe(url.replace(/ /g, '%20')),

		/**
		 * @param {string} type
		 * @returns {string}
		 */
		serverRequest = type => prefix() + '/' + type + '/' + SUB_QUERY_PREFIX + '/0/',

		// Is '?/Css/0/Admin' needed?
		cssLink = theme => BASE + '?/Css/0/User/-/' + encodeURI(theme) + '/-/' + Date.now() + '/Hash/-/Json/',

		/**
		 * @param {string} lang
		 * @param {boolean} isAdmin
		 * @returns {string}
		 */
		langLink = (lang, isAdmin) =>
			BASE + '?/Lang/0/' + (isAdmin ? 'Admin' : 'App')
				+ '/' + encodeURI(lang)
				+ '/' + Settings.app('version') + '/',

		/**
		 * @param {string=} screenName = ''
		 * @returns {string}
		 */
		settings = (screenName = '') => HASH_PREFIX + 'settings' + (screenName ? '/' + screenName : '');

	const LanguageStore = {
		language: ko.observable(''),
		languages: ko.observableArray(),
		userLanguage: ko.observable(''),
		hourCycle: ko.observable(''),

		populate: function() {
			const aLanguages = Settings.app('languages');
			this.languages(isArray(aLanguages) ? aLanguages : []);
			this.language(SettingsGet('language'));
			this.userLanguage(SettingsGet('clientLanguage'));
			this.hourCycle(SettingsGet('hourCycle'));
		}
	};

	let I18N_DATA = {};

	const init = () => {
			if (rl.I18N) {
				I18N_DATA = rl.I18N;
				rl.I18N = null;
				doc.documentElement.dir = I18N_DATA.LANG_DIR;
				return 1;
			}
		},

		getNotificationMessage = code => {
			let key = getKeyByValue(Notifications, code);
			return key ? I18N_DATA.NOTIFICATIONS[key] : '';
		};

	const translateTrigger = ko.observable(false),

		/**
		 * @param {string} key
		 * @param {Object=} valueList
		 * @param {string=} defaulValue
		 * @returns {string}
		 */
		i18n = (key, valueList, defaulValue) => {
			let result = defaulValue ?? key;
			let path = key.split('/');
			if (I18N_DATA[path[0]] && path[1]) {
				result = I18N_DATA[path[0]][path[1]] || result;
			}
			valueList && forEachObjectEntry(valueList, (key, value) => {
				result = result.replace('%' + key + '%', value);
			});
			return result;
		},

		/**
		 * @param {Object} elements
		 * @param {boolean=} animate = false
		 */
		i18nToNodes = element =>
			setTimeout(() =>
				element.querySelectorAll('[data-i18n]').forEach(element => {
					const key = element.dataset.i18n;
					if ('[' === key[0]) {
						switch (key.slice(1, 6)) {
							case 'html]':
								element.innerHTML = i18n(key.slice(6));
								break;
							case 'place':
								element.placeholder = i18n(key.slice(13));
								break;
							case 'title':
								element.title = i18n(key.slice(7));
								break;
							// no default
						}
					} else {
						element.textContent = i18n(key);
					}
				})
			, 1),

		/**
		 * @param {Function} startCallback
		 * @param {Function=} langCallback = null
		 */
		initOnStartOrLangChange = (startCallback, langCallback) => {
			startCallback?.();
			startCallback && translateTrigger.subscribe(startCallback);
			langCallback && translateTrigger.subscribe(langCallback);
		},

		/**
		 * @param {number} code
		 * @param {*=} message = ''
		 * @param {*=} defCode = null
		 * @returns {string}
		 */
		getNotification = (code, message = '', defCode = 0) => {
			code = pInt(code);
			if (Notifications.ClientViewError === code && message) {
				return message;
			}

			return getNotificationMessage(code)
				|| getNotificationMessage(pInt(defCode))
				|| '';
		},

		/**
		 * @param {boolean} admin
		 * @param {string} language
		 */
		translatorReload = (language, admin) =>
			new Promise((resolve, reject) => {
				const script = createElement('script');
				script.onload = () => {
					// reload the data
					if (init()) {
						i18nToNodes(doc);
						translateTrigger(!translateTrigger());
	//					admin || reloadTime();
					}
					script.remove();
					resolve();
				};
				script.onerror = () => reject(Error('Language '+language+' failed'));
				script.src = langLink(language, admin);
		//		script.async = true;
				doc.head.append(script);
			}),

		/**
		 * @param {string} language
		 * @param {boolean=} isEng = false
		 * @returns {string}
		 */
		convertLangName = (language, isEng = false) =>
			i18n(
				'LANGS_NAMES' + (true === isEng ? '_EN' : '') + '/' + language,
				null,
				language
			);

	init();

	var bootstrap = App => {

		rl.app = App;
		rl.logoutReload = App.logoutReload;

		rl.i18n = i18n;

		rl.Enums = {
			StorageResultType: {
				Success: 0,
				Error: 1,
				Abort: 2
			}
		};

		rl.route = {
			root: () => {
				rl.route.off();
				hasher.setHash(root());
			},
			reload: () => {
				rl.route.root();
				setTimeout(() => location.reload(), 100);
			},
			off: () => hasher.active = false,
			on: () => hasher.active = true
		};

	};

	const errorTip = (element, value) => value
				? setTimeout(() => element.setAttribute('data-rainloopErrorTip', value), 100)
				: element.removeAttribute('data-rainloopErrorTip'),

		/**
		 * The value of the pureComputed observable shouldn’t vary based on the
		 * number of evaluations or other “hidden” information. Its value should be
		 * based solely on the values of other observables in the application
		 */
		koComputable = fn => ko.computed(fn, {'pure':true}),

		addObservablesTo = (target, observables) =>
			forEachObjectEntry(observables, (key, value) =>
				target[key] || (target[key] = /*isArray(value) ? ko.observableArray(value) :*/ ko.observable(value)) ),

		addComputablesTo = (target, computables) =>
			forEachObjectEntry(computables, (key, fn) => target[key] = koComputable(fn)),

		addSubscribablesTo = (target, subscribables) =>
			forEachObjectEntry(subscribables, (key, fn) => target[key].subscribe(fn)),

		dispose = disposable => isFunction(disposable?.dispose) && disposable.dispose(),

		onEvent = (element, event, fn) => {
			element.addEventListener(event, fn);
			ko.utils.domNodeDisposal.addDisposeCallback(element, () => element.removeEventListener(event, fn));
		},

		onKey = (key, element, fValueAccessor, fAllBindings, model) => {
			let fn = event => {
				if (key == event.key) {
	//				stopEvent(event);
	//				element.dispatchEvent(new Event('change'));
					fValueAccessor().call(model);
				}
			};
			onEvent(element, 'keydown', fn);
		};

	Object.assign(ko.bindingHandlers, {
		tooltipErrorTip: {
			init: (element, fValueAccessor) => {
				doc.addEventListener('click', () => {
					let value = fValueAccessor();
					ko.isObservable(value) && !ko.isComputed(value) && value('');
					errorTip(element);
				});
			},
			update: (element, fValueAccessor) => {
				let value = ko.unwrap(fValueAccessor());
				errorTip(element, isFunction(value) ? value() : value);
			}
		},

		onEnter: {
			init: (element, fValueAccessor, fAllBindings, model) =>
				onKey('Enter', element, fValueAccessor, fAllBindings, model)
		},

		onEsc: {
			init: (element, fValueAccessor, fAllBindings, model) =>
				onKey('Escape', element, fValueAccessor, fAllBindings, model)
		},

		onSpace: {
			init: (element, fValueAccessor, fAllBindings, model) =>
				onKey(' ', element, fValueAccessor, fAllBindings, model)
		},

		toggle: {
			init: (element, fValueAccessor) => {
				let observable = fValueAccessor(),
					fn = () => observable(!observable());
				onEvent(element, 'click', fn);
				onEvent(element, 'keydown', event => ' ' == event.key && fn());
			}
		},

		i18nUpdate: {
			update: (element, fValueAccessor) => {
				ko.unwrap(fValueAccessor());
				i18nToNodes(element);
			}
		},

		command: {
			init: (element, fValueAccessor, fAllBindings, viewModel, bindingContext) => {
				const command = fValueAccessor();

				if (!command || !command.canExecute) {
					throw Error('Value should be a command');
				}

				ko.bindingHandlers['FORM'==element.nodeName ? 'submit' : 'click'].init(
					element,
					fValueAccessor,
					fAllBindings,
					viewModel,
					bindingContext
				);
			},
			update: (element, fValueAccessor) => {
				let disabled = !fValueAccessor().canExecute();
				element.classList.toggle('disabled', disabled);

				if (element.matches('INPUT,TEXTAREA,BUTTON')) {
					element.disabled = disabled;
				}
			}
		},

		saveTrigger: {
			init: (element) => {
				let icon = element;
				if (element.matches('input,select,textarea')) {
					element.classList.add('settings-save-trigger-input');
					element.after(element.saveTriggerIcon = icon = createElement('span'));
				}
				icon.classList.add('settings-save-trigger');
			},
			update: (element, fValueAccessor) => {
				const value = parseInt(ko.unwrap(fValueAccessor()),10);
				let cl = (element.saveTriggerIcon || element).classList;
				if (element.saveTriggerIcon) {
					cl.toggle('saving', value === SaveSettingStatus.Saving);
					cl.toggle('success', value === SaveSettingStatus.Success);
					cl.toggle('error', value === SaveSettingStatus.Failed);
				}
				cl = element.classList;
				cl.toggle('success', value === SaveSettingStatus.Success);
				cl.toggle('error', value === SaveSettingStatus.Failed);
			}
		}
	});

	// extenders

	ko.extenders.toggleSubscribeProperty = (target, options) => {
		const prop = options[1];
		if (prop) {
			target.subscribe(
				prev => prev?.[prop]?.(false),
				options[0],
				'beforeChange'
			);

			target.subscribe(next => next?.[prop]?.(true), options[0]);
		}

		return target;
	};

	ko.extenders.falseTimeout = (target, option) => {
		target.subscribe((() => target(false)).debounce(parseInt(option, 10) || 0));
		return target;
	};

	// functions

	ko.observable.fn.askDeleteHelper = function() {
		return this.extend({ falseTimeout: 3000, toggleSubscribeProperty: [this, 'askDelete'] });
	};

	let __themeTimer = 0;

	const
		// Also see Styles/_Values.less @maxMobileWidth
		isMobile = matchMedia('(max-width: 799px)'),
		// https://github.com/the-djmaze/snappymail/issues/1150
	//	isSmall = matchMedia('(max-width: 1400px)'),

		ThemeStore = {
			theme: ko.observable(''),
			themes: ko.observableArray(),
			userBackgroundName: ko.observable(''),
			userBackgroundHash: ko.observable(''),
			fontSansSerif: ko.observable(''),
			fontSerif: ko.observable(''),
			fontMono: ko.observable(''),
			isMobile: ko.observable(false)
		},

		initThemes = () => {
			const theme = SettingsGet('Theme'),
				themes = Settings.app('themes');

			ThemeStore.themes(isArray(themes) ? themes : []);
			ThemeStore.theme(theme);
			changeTheme(theme);
			if (!ThemeStore.isMobile()) {
				ThemeStore.userBackgroundName(SettingsGet('userBackgroundName'));
				ThemeStore.userBackgroundHash(SettingsGet('userBackgroundHash'));
			}
			ThemeStore.fontSansSerif(SettingsGet('fontSansSerif'));
			ThemeStore.fontSerif(SettingsGet('fontSerif'));
			ThemeStore.fontMono(SettingsGet('fontMono'));

			leftPanelDisabled(ThemeStore.isMobile());
		},

		changeTheme = (value, themeTrigger = ()=>0) => {
			const themeStyle = elementById('app-theme-style'),
				clearTimer = () => {
					__themeTimer = setTimeout(() => themeTrigger(SaveSettingStatus.Idle), 1000);
				},
				url = cssLink(value);

			if (themeStyle.dataset.name != value) {
				clearTimeout(__themeTimer);

				themeTrigger(SaveSettingStatus.Saving);

				rl.app.Remote.abort('theme').get('theme', url)
					.then(data => {
						if (2 === arrayLength(data)) {
							themeStyle.textContent = data[1];
							themeStyle.dataset.name = value;
							themeTrigger(SaveSettingStatus.Success);
						}
						clearTimer();
					}, clearTimer);
			}
		},

		convertThemeName = theme => theme.replace(/@[a-z]+$/, '').replace(/([A-Z])/g, ' $1').trim();

	addSubscribablesTo(ThemeStore, {
		fontSansSerif: value => {
			if (null != value) {
				let cl = appEl.classList;
				cl.forEach(name => {
					if (name.startsWith('font') && !/font(Serif|Mono)/.test(name)) {
						cl.remove(name);
					}
				});
				value && cl.add('font'+value);
			}
		},

		fontSerif: value => {
			if (null != value) {
				let cl = appEl.classList;
				cl.forEach(name => name.startsWith('fontSerif') && cl.remove(name));
				value && cl.add('fontSerif'+value);
			}
		},

		fontMono: value => {
			if (null != value) {
				let cl = appEl.classList;
				cl.forEach(name => name.startsWith('fontMono') && cl.remove(name));
				value && cl.add('fontMono'+value);
			}
		},

		userBackgroundHash: value => {
			appEl.classList.toggle('UserBackground', !!value);
			appEl.style.backgroundImage = value ? "url("+serverRequestRaw('UserBackground', value)+")" : null;
		}
	});

	isMobile.onchange = e => {
		ThemeStore.isMobile(e.matches);
		$htmlCL.toggle('rl-mobile', e.matches);
		/*$htmlCL.contains('sm-msgView-side') || */leftPanelDisabled(e.matches);
	};
	isMobile.onchange(isMobile);

	//isSmall.onchange = e => $htmlCL.contains('sm-msgView-side') && leftPanelDisabled(e.matches);
	//isSmall.onchange(isSmall);

	let iJsonErrorCount = 0;

	const getURL = (add = '') => serverRequest('Json') + pString(add),

	checkResponseError = data => {
		const err = data ? data.code : null;
		if (Notifications.InvalidToken === err) {
			console.error(getNotification(err) + ` (${data.messageAdditional})`);
	//		alert(getNotification(err));
			setTimeout(rl.logoutReload, 5000);
		} else if ([
				Notifications.AuthError,
				Notifications.ConnectionError,
				Notifications.DomainNotAllowed,
				Notifications.AccountNotAllowed,
				Notifications.MailServerError,
				Notifications.UnknownError
			].includes(err)
		) {
			if (7 < ++iJsonErrorCount) {
				rl.logoutReload();
			}
		}
	},

	oRequests = {},

	abort = (sAction, sReason, bClearOnly) => {
		let controller = oRequests[sAction];
		oRequests[sAction] = null;
		if (controller) {
			clearTimeout(controller.timeoutId);
			bClearOnly || controller.abort(new DOMException(sAction, sReason || 'AbortError'));
		}
	},

	fetchJSON = (action, sUrl, params, timeout, jsonCallback) => {
		if (params) {
			if (params instanceof FormData) {
				params.set('Action', action);
			} else {
				params.Action = action;
			}
		}
		// Don't abort, read https://github.com/the-djmaze/snappymail/issues/487
	//	abort(action, 0, 1);
		const controller = new AbortController(),
			signal = controller.signal;
		oRequests[action] = controller;
		// Currently there is no way to combine multiple signals, so AbortSignal.timeout() not possible
		controller.timeoutId = timeout && setTimeout(() => abort(action, 'TimeoutError'), timeout);
		return rl.fetchJSON(sUrl, {signal: signal}, params).then(data => {
			abort(action, 0, 1);
			return jsonCallback ? jsonCallback(data) : Promise.resolve(data);
		}).catch(err => {
			clearTimeout(controller.timeoutId);
			err.aborted = signal.aborted;
			return Promise.reject(err);
		});
	};

	class FetchError extends Error
	{
		constructor(code, message) {
			super(message);
			this.code = code || Notifications.JsonFalse;
		}
	}

	class AbstractFetchRemote
	{
		abort(sAction, sReason) {
			abort(sAction, sReason);
			return this;
		}

		/**
		 * Allows quicker visual responses to the user.
		 * Can be used to stream lines of json encoded data, but does not work on all servers.
		 * Apache needs 'flushpackets' like in <Proxy "fcgi://...." flushpackets=on></Proxy>
		 */
		streamPerLine(fCallback, sGetAdd, postData) {
			rl.fetch(getURL(sGetAdd), {}, postData)
			.then(response => response.body)
			.then(body => {
				let buffer = '';
				const
					// Firefox TextDecoderStream is not defined
	//				reader = body.pipeThrough(new TextDecoderStream()).getReader();
					reader = body.getReader(),
					re = /\r\n|\n|\r/gm,
					utf8decoder = new TextDecoder(),
					processText = ({ done, value }) => {
						buffer += value ? utf8decoder.decode(value, {stream: true}) : '';
						for (;;) {
							let result = re.exec(buffer);
							if (!result) {
								if (done) {
									break;
								}
								reader.read().then(processText);
								return;
							}
							fCallback(buffer.slice(0, result.index));
							buffer = buffer.slice(result.index + 1);
							re.lastIndex = 0;
						}
						// last line didn't end in a newline char
						buffer.length && fCallback(buffer);
					};
				reader.read().then(processText);
			});
		}

		/**
		 * @param {?Function} fCallback
		 * @param {string} sAction
		 * @param {Object=} oParameters
		 * @param {?number=} iTimeout
		 * @param {string=} sGetAdd = ''
		 */
		request(sAction, fCallback, params, iTimeout, sGetAdd) {
			params = params || {};

			const start = Date.now();

			fetchJSON(sAction, getURL(sGetAdd),
				sGetAdd ? null : (params || {}),
				pInt(iTimeout ?? 30000),
				async data => {
					let iError = 0;
					if (data) {
	/*
						if (sAction !== data.Action) {
							console.log(sAction + ' !== ' + data.Action);
						}
	*/
						if (data.Result) {
							iJsonErrorCount = 0;
						} else {
							checkResponseError(data);
							iError = data.code || Notifications.UnknownError;
						}
					}

					if (111 === iError && rl.app.ask && await rl.app.ask.cryptkey()) {
						return this.request(sAction, fCallback, params, iTimeout, sGetAdd);
					}

					fCallback && fCallback(
						iError,
						data,
						/**
						 * Responses like "304 Not Modified" are returned as "200 OK"
						 * This is an attempt to detect if the request comes from cache.
						 * But when client has wrong date/time, it will fail.
						 */
						data?.epoch && data.epoch < Math.floor(start / 1000) - 60
					);
				}
			)
			.catch(err => {
				console.error({fetchError:err});
				fCallback && fCallback(
					'TimeoutError' == err.name ? 3 : (err.name == 'AbortError' ? 2 : 1),
					err
				);
			});
		}

		setTrigger(trigger, value) {
			if (trigger) {
				value = !!value;
				(isArray(trigger) ? trigger : [trigger]).forEach(fTrigger => {
					fTrigger?.(value);
				});
			}
		}

		get(action, url) {
			return fetchJSON(action, url);
		}

		post(action, fTrigger, params, timeOut) {
			this.setTrigger(fTrigger, true);
			return fetchJSON(action, getURL(), params || {}, pInt(timeOut, 30000),
				async data => {
					abort(action, 0, 1);

					if (!data) {
						return Promise.reject(new FetchError(Notifications.JsonParse));
					}

					if (111 === data?.code && rl.app.ask && await rl.app.ask.cryptkey()) {
						return this.post(action, fTrigger, params, timeOut);
					}
	/*
					let isCached = false, type = '';
					if (data?.epoch) {
						isCached = data.epoch > microtime() - start;
					}
					// backward capability
					switch (true) {
						case 'success' === textStatus && data?.Result && action === data.Action:
							type = AbstractFetchRemote.SUCCESS;
							break;
						case 'abort' === textStatus && (!data || !data.__aborted__):
							type = AbstractFetchRemote.ABORT;
							break;
						default:
							type = AbstractFetchRemote.ERROR;
							break;
					}
	*/
					this.setTrigger(fTrigger, false);

					if (!data.Result || action !== data.Action) {
						checkResponseError(data);
						return Promise.reject(new FetchError(
							data ? data.code : 0,
							data ? (data.messageAdditional || data.message) : ''
						));
					}

					return data;
				}
			);
		}
	}

	Object.assign(AbstractFetchRemote.prototype, {
		SUCCESS : 0,
		ERROR : 1,
		ABORT : 2
	});

	class RemoteAdminFetch extends AbstractFetchRemote {

		/**
		 * @param {string} key
		 * @param {?scalar} value
		 * @param {?Function} fCallback
		 */
		saveSetting(key, value, fCallback) {
			this.request('AdminSettingsUpdate', fCallback, {[key]: value});
		}

	}

	var Remote = new RemoteAdminFetch();

	class AbstractScreen {
		constructor(screenName, viewModels = []) {
			this.__cross = null;
			this.screenName = screenName;
			this.viewModels = isArray(viewModels) ? viewModels : [];
		}

		/**
		 * @returns {?Array)}
		 */
		routes() {
			return null;
		}

	/*
		onBuild(viewModelDom) {}
		onShow() {}
		onHide() {}
		__started
		__builded
	*/

		/**
		 * @returns {void}
		 */
		onStart() {
			const routes = this.routes();
			if (arrayLength(routes)) {
				let route = new Crossroads(),
					fMatcher = (this.onRoute || (()=>0)).bind(this);

				routes.forEach(item => item && (route.addRoute(item[0], fMatcher).rules = item[1]));

				this.__cross = route;
			}
		}
	}

	const VIEW_MODELS = [];

	class AbstractSettingsScreen extends AbstractScreen {
		/**
		 * @param {Array} viewModels
		 */
		constructor(viewModels) {
			super('settings', viewModels);

			this.menu = ko.observableArray();

			this.oCurrentSubScreen = null;
		}

		onRoute(subName) {
			let settingsScreen = null,
				viewModelDom = null,
				RoutedSettingsViewModel = VIEW_MODELS.find(
					SettingsViewModel => subName === SettingsViewModel.route
				);

			if (RoutedSettingsViewModel) {
	//			const vmPlace = elementById('V-SettingsPane') || elementById('V-AdminPane);
				const vmPlace = this.viewModels[1].__vm.viewModelDom,
					SettingsViewModelClass = RoutedSettingsViewModel.vmc;
				if (SettingsViewModelClass.__vm) {
					settingsScreen = SettingsViewModelClass.__vm;
					viewModelDom = settingsScreen.viewModelDom;
				} else if (vmPlace) {
					viewModelDom = createElement('div',{
						id: 'V-Settings-' + SettingsViewModelClass.name.replace(/(User|Admin)Settings/,''),
						hidden: ''
					});
					vmPlace.append(viewModelDom);

					settingsScreen = new SettingsViewModelClass();
					settingsScreen.viewModelDom = viewModelDom;
					settingsScreen.viewModelTemplateID = RoutedSettingsViewModel.template;

					SettingsViewModelClass.__vm = settingsScreen;

					fireEvent('rl-view-model.create', settingsScreen);

					ko.applyBindingAccessorsToNode(
						viewModelDom,
						{
							template: () => ({ name: RoutedSettingsViewModel.template })
						},
						settingsScreen
					);

					settingsScreen.onBuild?.(viewModelDom);

					fireEvent('rl-view-model', settingsScreen);
				} else {
					console.log('Cannot find sub settings view model position: SettingsSubScreen');
				}

				if (settingsScreen) {
					setTimeout(() => {
						// hide
						this.onHide();
						// --

						this.oCurrentSubScreen = settingsScreen;

						// show
						settingsScreen.beforeShow?.();
						i18nToNodes(viewModelDom);
						viewModelDom.hidden = false;
						settingsScreen.onShow?.();

						this.menu.forEach(item => {
							item.selected(
								item.route === RoutedSettingsViewModel.route
							);
						});

						(vmPlace || {}).scrollTop = 0;
						// --
					}, 1);
				}
			} else {
				hasher.replaceHash(settings());
			}
		}

		onHide() {
			let subScreen = this.oCurrentSubScreen;
			if (subScreen) {
				subScreen.onHide?.();
				subScreen.viewModelDom.hidden = true;
			}
		}

		onBuild() {
			// TODO: issue on account switch
			// When current domain has sieve but the new has not, or current has not and the new has
			// SettingsViewModel.disabled() || this.menu.push()
			VIEW_MODELS.forEach(SettingsViewModel => this.menu.push(SettingsViewModel));
		}

		routes() {
			const DefaultViewModel = VIEW_MODELS.find(
					SettingsViewModel => SettingsViewModel.isDefault
				),
				defaultRoute = DefaultViewModel?.route || 'general',
				rules = {
					subname: /^(.*)$/,
					normalize_: (rquest, vals) => {
						vals.subname = pString(vals.subname ?? defaultRoute);
						return [vals.subname];
					}
				};

			return [
				['{subname}/', rules],
				['{subname}', rules],
				['', rules]
			];
		}
	}

	/**
	 * @param {Function} SettingsViewModelClass
	 * @param {string} template
	 * @param {string} labelName
	 * @param {string} route
	 * @param {boolean=} isDefault = false
	 * @returns {void}
	 */
	function settingsAddViewModel(SettingsViewModelClass, template, labelName, route, isDefault = false) {
		let name = SettingsViewModelClass.name.replace(/(User|Admin)Settings/, '');
		VIEW_MODELS.push({
			vmc: SettingsViewModelClass,
			label: labelName || 'SETTINGS_LABELS/' + name.toUpperCase(),
			route: route || name.toLowerCase(),
			selected: ko.observable(false),
			template: template || SettingsViewModelClass.name,
			isDefault: !!isDefault
		});
	}

	let
		currentScreen = null,
		defaultScreenName = '';

	const
		SCREENS = new Map,

		autofocus = dom => dom.querySelector('[autofocus]')?.focus(),

		visiblePopups = new Set,

		/**
		 * @param {string} screenName
		 * @returns {?Object}
		 */
		screen = screenName => (screenName && SCREENS.get(screenName)) || null,

		/**
		 * Creates the extended AbstractView model
		 * @param {Function} ViewModelClass
		 * @param {Object=} vmScreen
		 * @returns {*}
		 */
		buildViewModel = (ViewModelClass, vmScreen) => {
			if (ViewModelClass && !ViewModelClass.__vm) {
				const
					vm = new ViewModelClass(vmScreen),
					id = vm.viewModelTemplateID,
					position = 'rl-' + vm.viewType,
					dialog = ViewTypePopup === vm.viewType,
					vmPlace = doc.getElementById(position);

				if (vmPlace) {
					ViewModelClass.__vm = vm;

					let vmDom = dialog
						? createElement('dialog',{id:'V-'+id})
						: createElement('div',{id:'V-'+id,hidden:''});
					vmPlace.append(vmDom);

					vm.viewModelDom = vmDom;

					if (dialog) {
						// Firefox < 98 / Safari < 15.4 HTMLDialogElement not defined
						if (!vmDom.showModal) {
							vmDom.className = 'polyfill';
							vmDom.showModal = () => {
								vmDom.backdrop ||
									vmDom.before(vmDom.backdrop = createElement('div',{class:'dialog-backdrop'}));
								vmDom.setAttribute('open','');
								vmDom.open = true;
								vmDom.backdrop.hidden = false;
							};
							vmDom.close = () => {
	//							if (vmDom.dispatchEvent(new CustomEvent('cancel', {cancelable:true}))) {
									vmDom.backdrop.hidden = true;
									vmDom.removeAttribute('open', null);
									vmDom.open = false;
	//								vmDom.dispatchEvent(new CustomEvent('close'));
	//							}
							};
						}
						// https://developer.mozilla.org/en-US/docs/Web/API/HTMLDialogElement/cancel_event
	//					vmDom.addEventListener('cancel', event => (false === vm.onClose() && event.preventDefault()));
	//					vmDom.addEventListener('close', () => vm.modalVisible(false));

						// show/hide popup/modal
						// transitionend is called for each property, so we only listen to `opacity`
						// as defined in CSS by `dialog:not(.animate)`
						const endShowHide = e => {
							if (e.target === vmDom && 'opacity' === e.propertyName) {
								if (vmDom.classList.contains('animate')) {
									vm.afterShow?.();
									fireEvent('rl-vm-visible', vm);
								} else {
									vmDom.close();
									vm.afterHide?.();
	//								fireEvent('rl-vm-hidden', vm);
								}
							}
						};

						vm.modalVisible.subscribe(value => {
							if (value) {
								i18nToNodes(vmDom);
								visiblePopups.add(vm);
								vmDom.style.zIndex = 3001 + (visiblePopups.size * 2);
								vmDom.showModal();
								if (vmDom.backdrop) {
									vmDom.backdrop.style.zIndex = 3000 + (visiblePopups.size * 2);
								}
								vm.keyScope.set();
								setTimeout(()=>autofocus(vmDom),1);
								requestAnimationFrame(() => { // wait just before the next paint
									vmDom.offsetHeight; // force a reflow
									vmDom.classList.add('animate'); // trigger the transitions
								});
							} else {
								visiblePopups.delete(vm);
								vm.onHide?.();
								vm.keyScope.unset();
								vmDom.classList.remove('animate'); // trigger the transitions
							}
							arePopupsVisible(0 < visiblePopups.size);
						});
						vmDom.addEventListener('transitionend', endShowHide);
					}

					fireEvent('rl-view-model.create', vm);

					ko.applyBindingAccessorsToNode(
						vmDom,
						{
							template: () => ({ name: id })
						},
						vm
					);

					vm.onBuild?.(vmDom);

					fireEvent('rl-view-model', vm);
				} else {
					console.log('Cannot find view model position: ' + position);
				}
			}

			return ViewModelClass?.__vm;
		},

		forEachViewModel = (screen, fn) => {
			screen.viewModels.forEach(ViewModelClass => {
				if (
					ViewModelClass.__vm &&
					ViewTypePopup !== ViewModelClass.__vm.viewType
				) {
					fn(ViewModelClass.__vm, ViewModelClass.__vm.viewModelDom);
				}
			});
		},

		hideScreen = (screenToHide, destroy) => {
			screenToHide.onHide?.();
			forEachViewModel(screenToHide, (vm, dom) => {
				dom.hidden = true;
				vm.onHide?.();
				destroy && dom.remove();
			});
			ThemeStore.isMobile() && leftPanelDisabled(true);
		},

		/**
		 * @param {string} screenName
		 * @param {string} subPart
		 * @returns {void}
		 */
		screenOnRoute = (screenName, subPart) => {
			screenName = screenName || defaultScreenName;
			if (screenName && fireEvent('sm-show-screen', screenName + (subPart ?  '/' + subPart : ''), 1)) {
				// Close all popups
				for (let vm of visiblePopups) {
					vm.tryToClose();
				}

				let vmScreen = screen(screenName);
				if (!vmScreen) {
					vmScreen = screen(defaultScreenName);
					if (vmScreen) {
						subPart = screenName + '/' + subPart;
						screenName = defaultScreenName;
					}
				}

				if (vmScreen?.__started) {
					let isSameScreen = currentScreen && vmScreen === currentScreen;

					if (!vmScreen.__builded) {
						vmScreen.__builded = true;

						vmScreen.viewModels.forEach(ViewModelClass =>
							buildViewModel(ViewModelClass, vmScreen)
						);

						vmScreen.onBuild?.();
					}

					setTimeout(() => {
						// hide screen
						currentScreen && !isSameScreen && hideScreen(currentScreen);
						// --

						currentScreen = vmScreen;

						// show screen
						if (!isSameScreen) {
							vmScreen.onShow?.();

							forEachViewModel(vmScreen, (vm, dom) => {
								vm.beforeShow?.();
								i18nToNodes(dom);
								dom.hidden = false;
								vm.onShow?.();
								autofocus(dom);
							});
						}
						// --

						vmScreen.__cross?.parse(subPart);
					}, 1);
				}
			}
		};


	const
		ViewTypePopup = 'popups',

		/**
		 * @param {Function} ViewModelClassToShow
		 * @param {Array=} params
		 * @returns {void}
		 */
		showScreenPopup = (ViewModelClassToShow, params = []) => {
			const vm = buildViewModel(ViewModelClassToShow);
			if (vm) {
				params = params || [];
				vm.beforeShow?.(...params);
				vm.modalVisible(true);
				vm.onShow?.(...params);
			}
		},

		arePopupsVisible = ko.observable(false),

		/**
		 * @param {Array} screensClasses
		 * @returns {void}
		 */
		startScreens = screensClasses => {
			hasher.clear();
			SCREENS.forEach(screen => hideScreen(screen, 1));
			SCREENS.clear();
			currentScreen = null,
			defaultScreenName = '';

			screensClasses.forEach(CScreen => {
				const vmScreen = new CScreen(),
					screenName = vmScreen.screenName;
				defaultScreenName || (defaultScreenName = screenName);
				SCREENS.set(screenName, vmScreen);
			});

			SCREENS.forEach(vmScreen => {
				if (!vmScreen.__started) {
					vmScreen.onStart();
					vmScreen.__started = true;
				}
			});

			const cross = new Crossroads();
			cross.addRoute(/^([^/]*)\/?(.*)$/, screenOnRoute);

			hasher.add(cross.parse.bind(cross));
			hasher.init();

			setTimeout(() => $htmlCL.remove('rl-started-trigger'), 100);

			const c = elementById('rl-content'), l = elementById('rl-loading');
			c && (c.hidden = false);
			l?.remove();
		},

		/**
		 * Used by ko.bindingHandlers.command (template data-bind="command: ")
		 * to enable/disable click/submit action.
		 */
		decorateKoCommands = (thisArg, commands) =>
			forEachObjectEntry(commands, (key, canExecute) => {
				let command = thisArg[key],
					fn = (...args) => fn.canExecute() && command.apply(thisArg, args);

				fn.canExecute = koComputable(() => canExecute.call(thisArg, thisArg));

				thisArg[key] = fn;
			});

	ko.decorateCommands = decorateKoCommands;

	class AbstractView {
		constructor(templateID, type)
		{
	//		Object.defineProperty(this, 'viewModelTemplateID', { value: templateID });
			this.viewModelTemplateID = templateID || this.constructor.name.replace('UserView', '');
			this.viewType = type;
			this.viewModelDom = null;

			this.keyScope = {
				scope: 'none',
				previous: 'none',
				set: function() {
					this.previous = keyScope();
					keyScope(this.scope);
				},
				unset: function() {
					keyScope(this.previous);
				}
			};
		}

	/*
		onBuild() {}
		beforeShow() {} // Happens before: hidden = false
		onShow() {}       // Happens after: hidden = false
		onHide() {}
	*/

		querySelector(selectors) {
			return this.viewModelDom.querySelector(selectors);
		}

		addObservables(observables) {
			addObservablesTo(this, observables);
		}

		addComputables(computables) {
			addComputablesTo(this, computables);
		}

		addSubscribables(subscribables) {
			addSubscribablesTo(this, subscribables);
		}

	}

	class AbstractViewPopup extends AbstractView
	{
		constructor(name)
		{
			super('Popups' + name, ViewTypePopup);
			this.keyScope.scope = name;
			this.modalVisible = ko.observable(false).extend({ rateLimit: 0 });
			this.close = () => this.modalVisible(false);
			this.tryToClose = () => (false === this.onClose()) || this.close();
			addShortcut('escape,close', '', name, () => {
				this.modalVisible() && this.tryToClose();
				return false;
	//			return true; Issue with supported modal close
			});
		}

		// Happens when user hits Escape or Close key
		// return false to prevent closing
		onClose() {}

	/*
		beforeShow() {} // Happens before showModal()
		onShow() {}     // Happens after  showModal()
		afterShow() {}  // Happens after  showModal() animation transitionend
		onHide() {}     // Happens before animation transitionend
		afterHide() {}  // Happens after  animation transitionend
	*/
	}

	AbstractViewPopup.showModal = function(params = []) {
		showScreenPopup(this, params);
	};

	AbstractViewPopup.hidden = function() {
		return !this.__vm || !this.__vm.modalVisible();
	};

	class AbstractViewLeft extends AbstractView
	{
		constructor(templateID)
		{
			super(templateID, 'left');
			this.toggleLeftPanel = toggleLeftPanel;
		}
	}

	class AbstractViewRight extends AbstractView
	{
		constructor(templateID)
		{
			super(templateID, 'right');
		}
	}

	class AbstractViewSettings
	{
	/*
		onBuild(viewModelDom) {}
		beforeShow() {}
		onShow() {}
		onHide() {}
		viewModelDom
	*/
		/**
		 * When this[name] does not exists, create as observable with value of SettingsGet(name)
		 * When this[name+'Trigger'] does not exists, create as observable
		 * Subscribe to this[name], and handle saving the setting
		 */
		addSetting(name, valueCb)
		{
			let prop = name[0].toLowerCase() + name.slice(1),
				trigger = prop + 'Trigger';
			addObservablesTo(this, {
				[prop]: SettingsGet(name),
				[trigger]: SaveSettingStatus.Idle,
			});
			addSubscribablesTo(this, {
				[prop]: (value => {
					this[trigger](SaveSettingStatus.Saving);
					valueCb?.(value);
					rl.app.Remote.saveSetting(name, value,
						iError => {
							this[trigger](iError ? SaveSettingStatus.Failed : SaveSettingStatus.Success);
	//						iError || Settings.set(name, value);
							setTimeout(() => this[trigger](SaveSettingStatus.Idle), 1000);
						}
					);
				}).debounce(999),
			});
		}

		/**
		 * Foreach name if this[name] does not exists, create as observable with value of SettingsGet(name)
		 * Subscribe to this[name], for saving the setting
		 */
		addSettings(names)
		{
			names.forEach(name => {
				let prop = name[0].toLowerCase() + name.slice(1);
				this[prop] || (this[prop] = ko.observable(SettingsGet(name)));
				this[prop].subscribe(value => rl.app.Remote.saveSetting(name, value));
			});
		}
	}

	class AbstractViewLogin extends AbstractView {
		constructor(templateID) {
			super(templateID, 'content');
			this.formError = ko.observable(false).extend({ falseTimeout: 500 });
		}

		onBuild(dom) {
			dom.classList.add('LoginView');
		}

		onShow() {
			elementById('rl-left').hidden = true;
			elementById('rl-right').hidden = true;
			rl.route.off();
		}

		onHide() {
			elementById('rl-left').hidden = false;
			elementById('rl-right').hidden = false;
		}

		submitForm() {
	//		return false;
		}
	}

	const USER_VIEW_MODELS_HOOKS = [],
		ADMIN_VIEW_MODELS_HOOKS = [];

	/**
	 * @param {Function} callback
	 * @param {string} action
	 * @param {Object=} parameters
	 * @param {?number=} timeout
	 */
	rl.pluginRemoteRequest = (callback, action, parameters, timeout) => {
		rl.app.Remote.request('Plugin' + action, callback, parameters, timeout);
	};

	/**
	 * @param {Function} SettingsViewModelClass
	 * @param {string} labelName
	 * @param {string} template
	 * @param {string} route
	 */
	rl.addSettingsViewModel = (SettingsViewModelClass, template, labelName, route) => {
		USER_VIEW_MODELS_HOOKS.push([SettingsViewModelClass, template, labelName, route]);
	};

	/**
	 * @param {Function} SettingsViewModelClass
	 * @param {string} labelName
	 * @param {string} template
	 * @param {string} route
	 */
	rl.addSettingsViewModelForAdmin = (SettingsViewModelClass, template, labelName, route) => {
		ADMIN_VIEW_MODELS_HOOKS.push([SettingsViewModelClass, template, labelName, route]);
	};

	/**
	 * @param {boolean} admin
	 */
	function runSettingsViewModelHooks(admin) {
		(admin ? ADMIN_VIEW_MODELS_HOOKS : USER_VIEW_MODELS_HOOKS).forEach(view =>
			settingsAddViewModel(...view)
		);
	}

	/**
	 * @param {string} pluginSection
	 * @param {string} name
	 * @returns {?}
	 */
	rl.pluginSettingsGet = (pluginSection, name) =>
		SettingsGet('Plugins')?.[pluginSection]?.[name];

	rl.pluginPopupView = AbstractViewPopup;

	class LanguagesPopupView extends AbstractViewPopup {
		constructor() {
			super('Languages');
			this.fLang = null;
			this.languages = ko.observableArray();
		}

		onShow(fLanguage, langs, userLanguage) {
			this.fLang = fLanguage;
			this.languages(langs.map(language => ({
				key: language,
				user: userLanguage === language,
				selected: fLanguage?.() === language,
				fullName: convertLangName(language),
				title: convertLangName(language, true)
			})));
		}

		changeLanguage(lang) {
			this.fLang?.(lang);
			this.close();
		}
	}

	class AdminSettingsGeneral extends AbstractViewSettings {
		constructor() {
			super();

			this.language = LanguageStore.language;
			this.languageAdmin = ko.observable(SettingsAdmin('language'));

			this.theme = ThemeStore.theme;
			this.themes = ThemeStore.themes;

			this.addSettings(['allowLanguagesOnSettings']);

			addObservablesTo(this, {
				capaThemes: SettingsCapa('Themes'),
				capaUserBackground: SettingsCapa('UserBackground'),
				capaAdditionalAccounts: SettingsCapa('AdditionalAccounts'),
				capaIdentities: SettingsCapa('Identities'),
				capaAttachmentThumbnails: SettingsCapa('AttachmentThumbnails'),
				dataFolderAccess: false
			});

			this.weakPassword = rl.app.weakPassword;

			/** https://github.com/RainLoop/rainloop-webmail/issues/1924
			if (this.weakPassword) {
				fetch('./data/VERSION?' + Math.random()).then(response => this.dataFolderAccess(response.ok));
			}
			*/

			this.attachmentLimit = ko
				.observable(SettingsGet('attachmentLimit') / (1024 * 1024))
				.extend({ debounce: 500 });

			this.addSetting('language');
			this.addSetting('attachmentLimit');
			this.addSetting('Theme', value => changeTheme(value, this.themeTrigger));

			this.uploadData = SettingsGet('phpUploadSizes');
			this.uploadDataDesc =
				(this.uploadData?.upload_max_filesize || this.uploadData?.post_max_size)
					? [
							this.uploadData.upload_max_filesize
								? 'upload_max_filesize = ' + this.uploadData.upload_max_filesize + '; '
								: '',
							this.uploadData.post_max_size ? 'post_max_size = ' + this.uploadData.post_max_size : ''
					  ].join('')
					: '';

			addComputablesTo(this, {
				themesOptions: () => this.themes.map(theme => ({ optValue: theme, optText: convertThemeName(theme) })),

				languageFullName: () => convertLangName(this.language()),
				languageAdminFullName: () => convertLangName(this.languageAdmin())
			});

			this.languageAdminTrigger = ko.observable(SaveSettingStatus.Idle).extend({ debounce: 100 });

			const fReloadLanguageHelper = (saveSettingsStep) => () => {
					this.languageAdminTrigger(saveSettingsStep);
					setTimeout(() => this.languageAdminTrigger(SaveSettingStatus.Idle), 1000);
				},
				fSaveHelper = key => value => Remote.saveSetting(key, value);

			addSubscribablesTo(this, {
				languageAdmin: value => {
					this.languageAdminTrigger(SaveSettingStatus.Saving);
					translatorReload(value, 1)
						.then(fReloadLanguageHelper(SaveSettingStatus.Success), fReloadLanguageHelper(SaveSettingStatus.Failed))
						.then(() => Remote.saveSetting('languageAdmin', value));
				},

				capaAdditionalAccounts: fSaveHelper('CapaAdditionalAccounts'),

				capaIdentities: fSaveHelper('CapaIdentities'),

				capaAttachmentThumbnails: fSaveHelper('CapaAttachmentThumbnails'),

				capaThemes: fSaveHelper('CapaThemes'),

				capaUserBackground: fSaveHelper('CapaUserBackground')
			});
		}

		selectLanguage() {
			showScreenPopup(LanguagesPopupView, [
				this.language,
				LanguageStore.languages,
				LanguageStore.userLanguage()
			]);
		}

		selectLanguageAdmin() {
			showScreenPopup(LanguagesPopupView, [
				this.languageAdmin,
				SettingsAdmin('languages'),
				SettingsAdmin('clientLanguage')
			]);
		}
	}

	const DomainAdminStore = ko.observableArray();

	DomainAdminStore.loading = ko.observable(false);

	DomainAdminStore.fetch = () => {
		DomainAdminStore.loading(true);
		Remote.request('AdminDomainList',
			(iError, data) => {
				DomainAdminStore.loading(false);
				if (!iError) {
					DomainAdminStore(
						data.Result.map(item => {
							item.name = IDN.toUnicode(item.name);
							item.disabled = ko.observable(item.disabled);
							item.askDelete = ko.observable(false);
							return item;
						})
					);
				}
			}, {
				includeAliases: 1
			});
	};

	class AskPopupView extends AbstractViewPopup {
		constructor() {
			super('Ask');

			addObservablesTo(this, {
				askDesc: '',
				yesButton: '',
				noButton: '',
				username: '',
				askUsername: false,
				passphrase: '',
				askPass: false,
				remember: true,
				askRemeber: false
			});

			this.fYesAction = null;
			this.fNoAction = null;

			this.focusOnShow = true;
		}

		yesClick() {
			this.close();

			isFunction(this.fYesAction) && this.fYesAction(this);
		}

		noClick() {
			this.close();

			isFunction(this.fNoAction) && this.fNoAction(this);
		}

		/**
		 * @param {string} sAskDesc
		 * @param {Function=} fYesFunc
		 * @param {Function=} fNoFunc
		 * @param {boolean=} focusOnShow = true
		 * @returns {void}
		 */
		onShow(sAskDesc, fYesFunc = null, fNoFunc = null, focusOnShow = true, ask = 0, btnText = '') {
			this.askDesc(sAskDesc || '');
			this.askUsername(ask & 2);
			this.askPass(ask & 1);
			this.askRemeber(ask & 4);
			this.username('');
			this.passphrase('');
			this.remember(true);
			this.yesButton(i18n(btnText || 'GLOBAL/YES'));
			this.noButton(i18n(ask ? 'GLOBAL/CANCEL' : 'GLOBAL/NO'));
			this.fYesAction = fYesFunc;
			this.fNoAction = fNoFunc;
			this.focusOnShow = focusOnShow
				? (ask ? 'input[type="'+(ask&2?'text':'password')+'"]' : '.buttonYes')
				: '';
		}

		afterShow() {
			this.focusOnShow && this.querySelector(this.focusOnShow).focus();
		}

		onClose() {
			this.noClick();
			return false;
		}

		onBuild() {
	//		shortcuts.add('tab', 'shift', 'Ask', () => {
			shortcuts.add('tab,arrowright,arrowleft', '', 'Ask', () => {
				let yes = this.querySelector('.buttonYes'),
					no = this.querySelector('.buttonNo');
				if (yes.matches(':focus')) {
					no.focus();
					return false;
				} else if (no.matches(':focus')) {
					yes.focus();
					return false;
				}
			});
		}
	}

	const
		capitalize = string => string.charAt(0).toUpperCase() + string.slice(1),
		domainDefaults = {
			enableSmartPorts: false,

			savingError: '',

			name: '',

			imapHost: '',
			imapPort: 143,
			imapType: 0,
			imapTimeout: 300,
			imapShortLogin: false,
			imapLowerLogin: true,
			// SSL
			imapSslVerify_peer: false,
			imapSslAllow_self_signed: false,
			// Options
			imapExpunge_all_on_delete: false,
			imapFast_simple_search: true,
			imapFetch_new_messages: true,
			imapForce_select: false,
			imapFolder_list_limit: 200,
			imapMessage_all_headers: false,
			imapMessage_list_limit: 10000,
			imapSearch_filter: '',
			imapSpam_headers: '',
			imapVirus_headers: '',

			sieveEnabled: false,
			sieveHost: '',
			sievePort: 4190,
			sieveType: 0,
			sieveTimeout: 10,
			sieveAuthLiteral: true,

			smtpHost: '',
			smtpPort: 25,
			smtpType: 0,
			smtpTimeout: 60,
			smtpShortLogin: false,
			smtpLowerLogin: true,
			smtpUseAuth: true,
			smtpSetSender: false,
			smtpAuthPlainLine: false,
			smtpUsePhpMail: false,
			// SSL
			smtpSslVerify_peer: false,
			smtpSslAllow_self_signed: false,

			whiteList: '',
			aliasName: ''
		},
		domainToParams = oDomain => ({
			name: oDomain.name,
			IMAP: {
				host: oDomain.imapHost,
				port: oDomain.imapPort,
				secure: pInt(oDomain.imapType()),
				timeout: oDomain.imapTimeout,
				shortLogin: !!oDomain.imapShortLogin(),
				lowerLogin: !!oDomain.imapLowerLogin(),
				ssl: {
					verify_peer: !!oDomain.imapSslVerify_peer(),
					verify_peer_name: !!oDomain.imapSslVerify_peer(),
					allow_self_signed: !!oDomain.imapSslAllow_self_signed()
				},
				disabled_capabilities:  oDomain.imapDisabled_capabilities(),
				folder_list_limit: pInt(oDomain.imapFolder_list_limit()),
				message_list_limit: pInt(oDomain.imapMessage_list_limit()),
	/*
				expunge_all_on_delete: ,
				fast_simple_search: ,
				fetch_new_messages: ,
				force_select: ,
				message_all_headers: ,
	*/
				search_filter: oDomain.imapSearch_filter(),
				spam_headers: oDomain.imapSpam_headers(),
				virus_headers: oDomain.imapVirus_headers()
			},
			SMTP: {
				host: oDomain.smtpHost,
				port: oDomain.smtpPort,
				secure: pInt(oDomain.smtpType()),
				timeout: oDomain.smtpTimeout,
				shortLogin: !!oDomain.smtpShortLogin(),
				lowerLogin: !!oDomain.smtpLowerLogin(),
				ssl: {
					verify_peer: !!oDomain.smtpSslVerify_peer(),
					verify_peer_name: !!oDomain.smtpSslVerify_peer(),
					allow_self_signed: !!oDomain.smtpSslAllow_self_signed()
				},
				setSender: !!oDomain.smtpSetSender(),
				authPlainLine: !!oDomain.smtpAuthPlainLine(),
				useAuth: !!oDomain.smtpUseAuth(),
				usePhpMail: !!oDomain.smtpUsePhpMail()
			},
			Sieve: {
				enabled: !!oDomain.sieveEnabled(),
				authLiteral: !!oDomain.sieveAuthLiteral(),
				host: oDomain.sieveHost,
				port: oDomain.sievePort,
				secure: pInt(oDomain.sieveType()),
				timeout: oDomain.sieveTimeout,
				shortLogin: !!oDomain.imapShortLogin(),
				lowerLogin: !!oDomain.imapLowerLogin(),
				ssl: {
					verify_peer: !!oDomain.imapSslVerify_peer(),
					verify_peer_name: !!oDomain.imapSslVerify_peer(),
					allow_self_signed: !!oDomain.imapSslAllow_self_signed()
				}
			},
			whiteList: oDomain.whiteList
		});

	class DomainPopupView extends AbstractViewPopup {
		constructor() {
			super('Domain');

			addObservablesTo(this, domainDefaults);
			addObservablesTo(this, {
				edit: false,

				saving: false,

				testing: false,
				testingDone: false,
				testingImapError: false,
				testingSieveError: false,
				testingSmtpError: false,

				imapHostFocus: false,
				sieveHostFocus: false,
				smtpHostFocus: false,

				detectingConfig: false
			});
			this.imapDisabled_capabilities = ko.observableArray();
			this.imapCapabilities = ko.observableArray();

			addComputablesTo(this, {
				headerText: () => {
					const name = this.name(),
						aliasName = this.aliasName();
					return this.edit()
						? i18n('POPUPS_DOMAIN/TITLE_EDIT_DOMAIN', { NAME: name }) + (aliasName ? ' ⫘ ' + aliasName : '')
						: (name
							? i18n('POPUPS_DOMAIN/TITLE_ADD_DOMAIN_WITH_NAME', { NAME: name })
							: i18n('POPUPS_DOMAIN/TITLE_ADD_DOMAIN'));
				},

				domainDesc: () => {
					const name = this.name();
					return !this.edit() && name ? i18n('POPUPS_DOMAIN/NEW_DOMAIN_DESC', { NAME: '*@' + name }) : '';
				},

				domainIsComputed: () => {
					const usePhpMail = this.smtpUsePhpMail(),
						sieveEnabled = this.sieveEnabled();

					return (
						this.name() &&
						this.imapHost() &&
						this.imapPort() &&
						(sieveEnabled ? this.sieveHost() && this.sievePort() : true) &&
						((this.smtpHost() && this.smtpPort()) || usePhpMail)
					);
				},

				canBeTested: () => !this.testing() && this.domainIsComputed(),
				canBeSaved: () => !this.saving() && this.domainIsComputed()
			});

			addSubscribablesTo(this, {
				// smart form improvements
				imapHostFocus: value =>
					value && this.name() && !this.imapHost() && this.imapHost(this.name().replace(/[.]?[*][.]?/g, '')),

				sieveHostFocus: value =>
					value && this.imapHost() && !this.sieveHost() && this.sieveHost(this.imapHost()),

				smtpHostFocus: value => value && this.imapHost() && !this.smtpHost()
					&& this.smtpHost(this.imapHost().replace(/imap/gi, 'smtp')),

				imapType: value => {
					if (this.enableSmartPorts()) {
						const port = pInt(this.imapPort());
						switch (pInt(value)) {
							case 0:
							case 2:
								if (993 === port) {
									this.imapPort(143);
								}
								break;
							case 1:
								if (143 === port) {
									this.imapPort(993);
								}
								break;
							// no default
						}
					}
				},

				smtpType: value => {
					if (this.enableSmartPorts()) {
						const port = pInt(this.smtpPort());
						switch (pInt(value)) {
							case 0:
								if (465 === port || 587 === port) {
									this.smtpPort(25);
								}
								break;
							case 1:
								if (25 === port || 587 === port) {
									this.smtpPort(465);
								}
								break;
							case 2:
								if (25 === port || 465 === port) {
									this.smtpPort(587);
								}
								break;
							// no default
						}
					}
				}
			});

			decorateKoCommands(this, {
				createOrAddCommand: self => self.canBeSaved(),
				testConnectionCommand: self => self.canBeTested()
			});
		}

		createOrAddCommand() {
			this.saving(true);
			Remote.request('AdminDomainSave',
				iError => {
					this.saving(false);
					if (iError) {
						this.savingError(getNotification(iError));
					} else {
						DomainAdminStore.fetch();
						this.close();
					}
				},
				Object.assign(domainToParams(this), {
					create: this.edit() ? 0 : 1
				})
			);
		}

		testConnectionCommand() {
			this.clearTesting();
			// https://github.com/the-djmaze/snappymail/issues/477
			AskPopupView.credentials('IMAP', 'GLOBAL/TEST').then(credentials => {
				if (credentials) {
					this.testing(true);
					const params = domainToParams(this);
					params.auth = {
						user: credentials.username,
						pass: credentials.password
					};
					Remote.request('AdminDomainTest',
						(iError, oData) => {
							this.testing(false);
							if (iError) {
								this.testingImapError(getNotification(iError));
								this.testingSieveError(getNotification(iError));
								this.testingSmtpError(getNotification(iError));
							} else {
								const result = oData.Result;
								this.testingDone(true);
								this.testingImapError(true !== result.Imap ? result.Imap : false);
								this.testingSieveError(true !== result.Sieve ? result.Sieve : false);
								this.testingSmtpError(true !== result.Smtp ? result.Smtp : false);
								// result.ImapResult.connectCapa
								if (true === result.Imap) {
									let capa = result.ImapResult.authCapa
										|| ['LIST-STATUS','METADATA','MOVE','SORT','THREAD','BINARY','STATUS=SIZE','PREVIEW'];
									capa = capa.concat(result.ImapResult.connectCapa).unique();
									capa.sort();
									this.imapCapabilities(capa);
								}
								// result.SmtpResult.connectCapa
								// result.SmtpResult.authCapa
								// result.SieveResult.connectCapa
								// result.SieveResult.authCapa
							}
						},
						params
					);
				}
			});
		}

		clearTesting() {
			this.testing(false);
			this.testingDone(false);
			this.testingImapError(false);
			this.testingSieveError(false);
			this.testingSmtpError(false);
		}

		autoconfig() {
			this.detectingConfig(true);
			let domain = this.name();
			Remote.request('AdminDomainAutoconfig', (iError, oData) => {
				if (oData?.Result?.config) {
					let server = oData.Result.config.incomingServer[0];
					this.imapHost(server.hostname);
					this.imapPort(server.port);
					this.imapType('STARTTLS' === server.socketType ? 2 : ('SSL' === server.socketType ? 1 : 0));
					this.imapShortLogin('%EMAILADDRESS%' !== server.username);

					server = oData.Result.config.outgoingServer[0];
					this.smtpHost(server.hostname);
					this.smtpPort(server.port);
					this.smtpType('STARTTLS' === server.socketType ? 2 : ('SSL' === server.socketType ? 1 : 0));
					this.smtpShortLogin('%EMAILADDRESS%' !== server.username);
					this.smtpUseAuth(!!server.authentication);
					this.smtpUsePhpMail(false);
				}
				this.detectingConfig(false);
			}, {domain});
		}

		onShow(oDomain) {
			this.saving(false);
			this.clearTesting();
			this.edit(false);
			this.imapCapabilities([
				'BINARY',
				'LIST-STATUS',
				'METADATA',
				'MOVE',
				'NAMESPACE',
				'PREVIEW',
				'SORT',
				'STATUS=SIZE',
				'THREAD'
			]);
			this.imapDisabled_capabilities(['METADATA','OBJECTID','PREVIEW','STATUS=SIZE']);
			forEachObjectEntry(domainDefaults, (key, value) => this[key](value));
			this.enableSmartPorts(true);
			if (oDomain) {
				this.enableSmartPorts(false);
				this.edit(true);
				forEachObjectEntry(oDomain, (key, value) => {
					if ('IMAP' === key || 'SMTP' === key || 'Sieve' === key) {
						key = key.toLowerCase();
						forEachObjectEntry(value, (skey, value) => {
							skey = capitalize(skey);
							if ('Ssl' == skey) {
								forEachObjectEntry(value, (sslkey, value) => {
									this[key + skey + capitalize(sslkey)]?.(value);
								});
							} else {
								this[key + skey]?.(value);
							}
						});
					} else {
						this[key]?.(value);
					}
				});
				this.name(IDN.toUnicode(this.name()));
				this.aliasName(IDN.toUnicode(this.aliasName()));
				this.imapCapabilities(this.imapCapabilities.concat(this.imapDisabled_capabilities()).unique());
				this.enableSmartPorts(true);
			}
		}
	}

	class DomainAliasPopupView extends AbstractViewPopup {
		constructor() {
			super('DomainAlias');

			addObservablesTo(this, {
				saving: false,
				savingError: '',

				name: '',

				alias: ''
			});

			addComputablesTo(this, {
				domains: () => DomainAdminStore.filter(item => item && !item.alias),

				domainsOptions: () => this.domains().map(item => ({ optValue: item.name, optText: item.name })),

				canBeSaved: () => !this.saving() && this.name() && this.alias()
			});

			decorateKoCommands(this, {
				createCommand: self => self.canBeSaved()
			});
		}

		createCommand() {
			this.saving(true);
			Remote.request('AdminDomainAliasSave',
				iError => {
					this.saving(false);
					if (iError) {
						this.savingError(getNotification(iError));
					} else {
						DomainAdminStore.fetch();
						this.close();
					}
				}, {
					name: this.name,
					alias: this.alias
				});
		}

		onShow() {
			this.saving(false);
			this.savingError('');
			this.name('');
			this.alias('');
		}
	}

	class AdminSettingsDomains /*extends AbstractViewSettings*/ {
		constructor() {
			this.domains = DomainAdminStore;
			this.username = ko.observable('');
			this.domainForDeletion = ko.observable(null).askDeleteHelper();
		}

		testUsername() {
			Remote.request('AdminDomainMatch',
				(iError, oData) => {
					if (oData?.Result?.domain) {
						alert(`${oData.Result.email} matched domain: ${oData.Result.domain.name}`);
					} else {
						alert('No domain match');
					}
				},
				{
					username: this.username
				}
			);
		}

		createDomain() {
			showScreenPopup(DomainPopupView);
		}

		createDomainAlias() {
			showScreenPopup(DomainAliasPopupView);
		}

		deleteDomain(domain) {
			DomainAdminStore.remove(domain);
			Remote.request('AdminDomainDelete', DomainAdminStore.fetch, {
				name: domain.name
			});
		}

		disableDomain(domain) {
			domain.disabled(!domain.disabled());
			Remote.request('AdminDomainDisable', DomainAdminStore.fetch, {
				name: domain.name,
				disabled: domain.disabled() ? 1 : 0
			});
		}

		onBuild(oDom) {
			oDom.addEventListener('click', event => {
				let el = event.target.closestWithin('.b-admin-domains-list-table .e-action', oDom);
				el && ko.dataFor(el) && Remote.request('AdminDomainLoad',
					(iError, oData) => iError || showScreenPopup(DomainPopupView, [oData.Result]),
					{
						name: ko.dataFor(el).name
					}
				);

			});

			DomainAdminStore.fetch();
		}
	}

	class AdminSettingsLogin extends AbstractViewSettings {
		constructor() {
			super();
			this.addSetting('loginDefaultDomain');
			this.addSettings(['determineUserLanguage','determineUserDomain','allowLanguagesOnLogin']);
		}
	}

	class AdminSettingsContacts extends AbstractViewSettings {
		constructor() {
			super();
			this.defaultOptionsAfterRender = defaultOptionsAfterRender;

			this.addSetting('contactsPdoDsn');
			this.addSetting('contactsPdoUser');
			this.addSetting('contactsPdoPassword');
			this.addSetting('contactsPdoType', () => {
				this.testContactsSuccess(false);
				this.testContactsError(false);
				this.testContactsErrorMessage('');
			});

			this.addSettings(['contactsEnable','contactsSync']);

			this.addSetting('contactsMySQLSSLCA');
			this.addSetting('contactsMySQLSSLVerify');
			this.addSetting('contactsMySQLSSLCiphers');

			this.addSetting('contactsSQLiteGlobal');

			addObservablesTo(this, {
				testing: false,
				testContactsSuccess: false,
				testContactsError: false,
				testContactsErrorMessage: ''
			});

			this.addSetting('contactsSuggestionsLimit');

			const supportedTypes = SettingsGet('supportedPdoDrivers') || [],
				types = [{
					id:'sqlite',
					name:'SQLite'
				},{
					id:'mysql',
					name:'MySQL'
				},{
					id:'pgsql',
					name:'PostgreSQL'
				}].filter(type => supportedTypes.includes(type.id));

			this.contactsSupported = 0 < types.length;

			this.contactsTypesOptions = types;

			this.mainContactsType = ko
				.computed({
					read: this.contactsPdoType,
					write: value => {
						if (value !== this.contactsPdoType()) {
							if (supportedTypes.includes(value)) {
								this.contactsPdoType(value);
							} else if (types.length) {
								this.contactsPdoType('');
							}
						} else {
							this.contactsPdoType.valueHasMutated();
						}
					}
				})
				.extend({ notify: 'always' });

			decorateKoCommands(this, {
				testContactsCommand: self => self.contactsPdoDsn() && self.contactsPdoUser()
			});
		}

		testContactsCommand() {
			this.testContactsSuccess(false);
			this.testContactsError(false);
			this.testContactsErrorMessage('');
			this.testing(true);

			Remote.request('AdminContactsTest',
				(iError, data) => {
					this.testContactsSuccess(false);
					this.testContactsError(false);
					this.testContactsErrorMessage('');

					if (!iError && data.Result.Result) {
						this.testContactsSuccess(true);
					} else {
						this.testContactsError(true);
						this.testContactsErrorMessage(data?.Result?.Message || '');
					}

					this.testing(false);
				}, {
					PdoType: this.contactsPdoType(),
					PdoDsn: this.contactsPdoDsn(),
					PdoUser: this.contactsPdoUser(),
					PdoPassword: this.contactsPdoPassword(),
					MySQLSSLCA: this.contactsMySQLSSLCA(),
					MySQLSSLVerify: this.contactsMySQLSSLVerify(),
					MySQLSSLCiphers: this.contactsMySQLSSLCiphers(),
					SQLiteGlobal: this.contactsSQLiteGlobal()
				}
			);
		}

		onShow() {
			this.testContactsSuccess(false);
			this.testContactsError(false);
			this.testContactsErrorMessage('');
		}
	}

	class AdminSettingsSecurity extends AbstractViewSettings {
		constructor() {
			super();

			this.addSettings(['proxyExternalImages', 'autoVerifySignatures']);

			this.weakPassword = rl.app.weakPassword;

			addObservablesTo(this, {
				adminLogin: SettingsGet('adminLogin'),
				adminLoginError: false,
				adminPassword: '',
				adminPasswordNew: '',
				adminPasswordNew2: '',
				adminPasswordNewError: false,
				adminTOTP: '',

				saveError: false,
				saveSuccess: false,

				viewQRCode: '',

				capaGnuPG: SettingsCapa('GnuPG'),
				capaOpenPGP: SettingsCapa('OpenPGP')
			});

			this.gnuPGversion = 'GnuPG v' + SettingsGet('gnupg');

			const reset = () => {
				this.saveError(false);
				this.saveSuccess(false);
				this.adminPasswordNewError(false);
			};

			addSubscribablesTo(this, {
				adminPassword: () => {
					this.saveError(false);
					this.saveSuccess(false);
				},

				adminLogin: () => this.adminLoginError(false),

				adminTOTP: value => {
					if (/[A-Z2-7]{16,}/.test(value) && 0 == value.length * 5 % 8) {
						Remote.request('AdminQRCode', (iError, data) => {
							if (!iError) {
								console.dir({data:data});
								this.viewQRCode(data.Result);
							}
						}, {
							'username': this.adminLogin(),
							'TOTP': this.adminTOTP()
						});
					} else {
						this.viewQRCode('');
					}
				},

				adminPasswordNew: reset,

				adminPasswordNew2: reset,

				capaGnuPG: value => Remote.saveSetting('capaGnuPG', value),
				capaOpenPGP: value => Remote.saveSetting('capaOpenPGP', value)
			});

			this.adminTOTP(SettingsGet('adminTOTP'));

			decorateKoCommands(this, {
				saveAdminUserCommand: self => self.adminLogin().trim() && self.adminPassword()
			});
		}

		generateTOTP() {
			let CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567',
				length = 16,
				secret = '';
			while (0 < length--) {
				secret += CHARS[Math.floor(Math.random() * 32)];
			}
			this.adminTOTP(secret);
		}

		saveAdminUserCommand() {
			if (!this.adminLogin().trim()) {
				this.adminLoginError(true);
				return false;
			}

			if (this.adminPasswordNew() !== this.adminPasswordNew2()) {
				this.adminPasswordNewError(true);
				return false;
			}

			this.saveError(false);
			this.saveSuccess(false);

			Remote.request('AdminPasswordUpdate', (iError, data) => {
				if (iError) {
					this.saveError(true);
				} else {
					this.adminPassword('');
					this.adminPasswordNew('');
					this.adminPasswordNew2('');

					this.saveSuccess(true);

					this.weakPassword(!!data.Result.Weak);
				}
			}, {
				Login: this.adminLogin(),
				Password: this.adminPassword(),
				newPassword: this.adminPasswordNew(),
				TOTP: this.adminTOTP()
			});

			return true;
		}

		onHide() {
			this.adminPassword('');
			this.adminPasswordNew('');
			this.adminPasswordNew2('');
		}
	}

	const PackageAdminStore = ko.observableArray();

	PackageAdminStore.real = ko.observable(true);

	PackageAdminStore.loading = ko.observable(false);

	PackageAdminStore.error = ko.observable('');

	PackageAdminStore.fetch = () => {
		PackageAdminStore.loading(true);
		Remote.request('AdminPackagesList', (iError, data) => {
			PackageAdminStore.loading(false);
			if (iError) {
				PackageAdminStore.real(false);
				PackageAdminStore.error(getNotification(iError));
	//			let error = getNotification(iError);
	//			if (data.message) { error = data.message + error; }
	//			if (data.reason) { error = data.reason + " " + error; }
	//			PackageAdminStore.error(error);
			} else {
				PackageAdminStore.real(!!data.Result.Real);
				PackageAdminStore.error(data.Result.Error);

				const loading = {};
				PackageAdminStore.forEach(item => {
					if (item?.loading()) {
						loading[item.file] = item;
					}
				});

				let list = [];
				if (isArray(data.Result.List)) {
					list = data.Result.List.filter(v => v).map(item => {
						item.loading = ko.observable(loading[item.file] !== undefined);
						item.enabled = ko.observable(item.enabled);
						return item;
					});
				}

				PackageAdminStore(list);
			}
		});
	};

	class PluginPopupView extends AbstractViewPopup {
		constructor() {
			super('Plugin');

			addObservablesTo(this, {
				saveError: '',
				id: '',
				name: '',
				readme: '',
				author: '',
				url: '',
				version: '',
				released: ''
			});

			this.config = ko.observableArray();

			addComputablesTo(this, {
				hasReadme: () => !!this.readme(),
				hasConfiguration: () => 0 < this.config().length
			});

			this.keyScope.scope = 'all';

			decorateKoCommands(this, {
				saveCommand: self => self.hasConfiguration()
			});
		}

		hideError() {
			this.saveError('');
		}

		saveCommand() {
			const oConfig = {
				id: this.id,
				settings: {}
			},
			setItem = item => {
				let value = item.value();
				if (false === value || true === value) {
					value = value ? 1 : 0;
				}
				oConfig.settings[item.name] = value;
			};

			this.config.forEach(oItem => {
				if (7 == oItem.type) {
					// Group
					oItem.config.forEach(oSubItem => setItem(oSubItem));
				} else {
					setItem(oItem);
				}
			});

			this.saveError('');
			Remote.request('AdminPluginSettingsUpdate',
				iError => iError
					? this.saveError(getNotification(iError))
					: this.close(),
				oConfig);
		}

		onShow(oPlugin) {
			this.id('');
			this.name('');
			this.readme('');
			this.author('');
			this.url('');
			this.version('');
			this.released('');
			this.config([]);

			if (oPlugin) {
				this.id(oPlugin.id);
				this.name(oPlugin.name);
				this.readme(oPlugin.readme);
				this.author(oPlugin.author);
				this.url(oPlugin.url);
				this.version(oPlugin.version);
				this.released(oPlugin.released);

				const config = oPlugin.config;
				if (arrayLength(config)) {
					this.config(
						config.map(item => {
							if (7 == item.type) {
								// Group
								item.config.forEach(subItem => {
									subItem.value = ko.observable(subItem.value);
								});
							} else {
								item.value = ko.observable(item.value);
							}
							return item;
						})
					);
				}
			}
		}

		onClose() {
			if (AskPopupView.hidden()) {
				showScreenPopup(AskPopupView, [
					i18n('POPUPS_ASK/DESC_WANT_CLOSE_THIS_WINDOW'),
					() => this.close()
				]);
			}
			return false;
		}
	}

	class AdminSettingsPackages extends AbstractViewSettings {
		constructor() {
			super();

			this.addSettings(['pluginsEnable']);

			addObservablesTo(this, {
				packagesError: '',
				search: ''
			});

			this.packages = PackageAdminStore;

			addComputablesTo(this, {
				packagesCurrent: () => PackageAdminStore().filter(item => item?.installed && !item.canBeUpdated),
				packagesUpdate: () => PackageAdminStore().filter(item => item?.installed && item.canBeUpdated),
				packagesAvailable: () => PackageAdminStore().filter(item => !item?.installed),

				visibility: () => (PackageAdminStore.loading() ? 'visible' : 'hidden')
			});

			this.search.subscribe(value => {
				const v = value.toLowerCase(),
					qsa = (node, selector, fn) => node.querySelectorAll(selector).forEach(fn),
					match = node => node.textContent.toLowerCase().includes(v);
				if (v.length) {
					qsa(this.viewModelDom, 'td:first-child', td => {
						td.parentNode.hidden = !match(td);
					});
				} else {
					qsa(this.viewModelDom, 'tr[hidden]', n => n.hidden = false);
				}
			});
		}

		onShow() {
			this.packagesError('');
		}

		onBuild(oDom) {
			PackageAdminStore.fetch();

			oDom.addEventListener('click', event => {
				// configurePlugin
				let el = event.target.closestWithin('.package-configure', oDom),
					data = el && ko.dataFor(el);
				data && Remote.request('AdminPluginLoad',
					(iError, data) => iError || showScreenPopup(PluginPopupView, [data.Result]),
					{
						id: data.id
					}
				);
				// disablePlugin
				el = event.target.closestWithin('.package-active', oDom);
				data = el && ko.dataFor(el);
				data && this.disablePlugin(data);
			});
		}

		requestHelper(packageToRequest, install) {
			return (iError, data) => {
				PackageAdminStore.forEach(item => {
					if (packageToRequest && item?.loading?.() && packageToRequest.file === item.file) {
						packageToRequest.loading(false);
						item.loading(false);
					}
				});

				if (iError) {
					this.packagesError(
						getNotification(install ? Notifications.CantInstallPackage : Notifications.CantDeletePackage)
						+ (data.message ? ':\n' + data.message : '')
					);
				} else if (data.Result.Reload) {
					location.reload();
				} else {
					PackageAdminStore.fetch();
				}
			};
		}

		deletePackage(packageToDelete) {
			if (packageToDelete) {
				packageToDelete.loading(true);
				Remote.request('AdminPackageDelete',
					this.requestHelper(packageToDelete, false),
					{
						id: packageToDelete.id
					}
				);
			}
		}

		installPackage(packageToInstall) {
			if (packageToInstall) {
				packageToInstall.loading(true);
				Remote.request('AdminPackageInstall',
					this.requestHelper(packageToInstall, true),
					{
						id: packageToInstall.id,
						type: packageToInstall.type,
						file: packageToInstall.file
					},
					60000
				);
			}
		}

		disablePlugin(plugin) {
			let disable = plugin.enabled();
			plugin.enabled(!disable);
			Remote.request('AdminPluginDisable',
				(iError, data) => {
					if (iError) {
						plugin.enabled(disable);
						this.packagesError(
							(Notifications.UnsupportedPluginPackage === iError && data?.message)
							? data.message
							: getNotification(iError)
						);
					}
	//				PackageAdminStore.fetch();
				}, {
					id: plugin.id,
					disabled: disable ? 1 : 0
				}
			);
		}

	}

	class AdminSettingsAbout /*extends AbstractViewSettings*/ {
		constructor() {
			this.version = Settings.app('version');
			this.phpextensions = ko.observableArray();

			addObservablesTo(this, {
				coreReal: true,
				coreUpdatable: true,
				coreWarning: false,
				coreVersion: '',
				coreVersionCompare: -2,
				php64: true,
				load1: 0,
				load5: 0,
				load15: 0,
				errorDesc: ''
			});
			this.coreChecking = ko.observable(false).extend({ throttle: 100 });
			this.coreUpdating = ko.observable(false).extend({ throttle: 100 });

			this.coreVersionHtmlDesc = ko.computed(() => {
				translateTrigger();
				return i18n('TAB_ABOUT/HTML_NEW_VERSION', { 'VERSION': this.coreVersion() });
			});

			this.statusType = ko.computed(() => {
				let type = '';
				const versionToCompare = this.coreVersionCompare(),
					isChecking = this.coreChecking(),
					isUpdating = this.coreUpdating(),
					isReal = this.coreReal();

				if (isChecking) {
					type = 'checking';
				} else if (isUpdating) {
					type = 'updating';
				} else if (!isReal) {
					type = 'error';
					this.errorDesc('Cannot access the repository at the moment.');
				} else if (0 === versionToCompare) {
					type = 'up-to-date';
				} else if (-1 === versionToCompare) {
					type = 'available';
				}

				return type;
			});
		}

		onBuild() {
	//	beforeShow() {
			this.coreChecking(true);
			Remote.request('AdminInfo', (iError, data) => {
				this.coreChecking(false);
				data = data?.Result;
				if (!iError && data) {
					this.load1(data.system.load?.[0]);
					this.load5(data.system.load?.[1]);
					this.load15(data.system.load?.[2]);
					this.phpextensions(data.php);
					this.coreReal(true);
					this.coreUpdatable(!!data.core.updatable);
					this.coreWarning(!!data.core.warning);
					this.coreVersion(data.core.version || '');
					this.coreVersionCompare(data.core.versionCompare);
					this.php64(data.php[1].loaded);
				} else {
					this.coreReal(false);
					this.coreWarning(false);
					this.coreVersion('');
					this.coreVersionCompare(-2);
				}
			});
		}

		clearCache() {
			Remote.request('AdminClearCache');
		}

		updateCoreData() {
			if (!this.coreUpdating()) {
				this.coreUpdating(true);
				Remote.request('AdminUpgradeCore', (iError, data) => {
					this.coreUpdating(false);
					this.coreVersion('');
					this.coreVersionCompare(-2);
					if (!iError && data?.Result) {
						this.coreReal(true);
						window.location.reload();
					} else {
						this.coreReal(false);
					}
				}, {}, 90000);
			}
		}
	}

	class AdminSettingsBranding extends AbstractViewSettings {
		constructor() {
			super();
			this.addSetting('title');
			this.addSetting('loadingDescription');
			this.addSetting('faviconUrl');
		}
	}

	class AdminSettingsConfig /*extends AbstractViewSettings*/ {

		constructor() {
			this.config = ko.observableArray();
			this.search = ko.observable('');
			this.saved = ko.observable(false).extend({ falseTimeout: 5000 });

			this.search.subscribe(value => {
				const v = value.toLowerCase(),
					qsa = (node, selector, fn) => node.querySelectorAll(selector).forEach(fn),
					match = node => node.textContent.toLowerCase().includes(v);
				if (v.length) {
					qsa(this.viewModelDom, 'tbody', tbody => {
						let show = match(tbody.querySelector('th'));
						if (show) {
							qsa(tbody, '[hidden]', n => n.hidden = false);
						} else {
							qsa(tbody, 'tbody td:first-child', td => {
								let hide = !match(td);
								show = show || !hide;
	//							td.closest('tr').hidden = hide;
								td.parentNode.hidden = hide;
							});
						}
						tbody.hidden = !show;
					});
				} else {
					qsa(this.viewModelDom, 'table [hidden]', n => n.hidden = false);
				}
			});
		}

		beforeShow() {
			Remote.request('AdminSettingsGet', (iError, data) => {
				if (!iError) {
					const cfg = [],
						getInputType = (value, pass) => {
							switch (typeof value)
							{
							case 'boolean': return 'checkbox';
							case 'number': return 'number';
							}
							return pass ? 'password' : 'text';
						};
					forEachObjectEntry(data.Result, (key, items) => {
						const section = {
							name: key,
							items: []
						};
						forEachObjectEntry(items, (skey, item) => {
							if ('language' === skey) {
								item[2] = ('webmail' === key) ? LanguageStore.languages : SettingsAdmin('languages');
							} else if ('theme' === skey) {
								item[2] = ThemeStore.themes;
							}
							'admin_password' === skey ||
							section.items.push({
								key: `config[${key}][${skey}]`,
								name: skey,
								value: item[0],
								type: getInputType(item[0], skey.includes('password')),
								comment: item[1],
								options: item[2]
							});
						});
						cfg.push(section);
					});
					this.config(cfg);
				}
			});
		}

		saveConfig(form) {
			const data = new FormData(form),
				config = {};
			this.config.forEach(section => {
				if (!config[section.name]) {
					config[section.name] = {};
				}
				section.items.forEach(item => {
					let value = data.get(item.key);
					switch (typeof item.value) {
						case 'boolean':
							value = 'on' == value;
							break;
						case 'number':
							value = parseInt(value, 10);
							break;
					}
					config[section.name][item.name] = value;
				});
			});
			Remote.post('AdminSettingsSet', null, {config:config}).then(result => {
				result.Result && this.saved(true);
			});
		}
	}

	class MenuSettingsAdminView extends AbstractViewLeft {
		/**
		 * @param {?} screen
		 */
		constructor(screen) {
			super('AdminMenu');

			this.menu = screen.menu;
		}

		link(route) {
			return '#/' + route;
		}
	}

	class PaneSettingsAdminView extends AbstractViewRight {
		constructor() {
			super('AdminPane');
			this.toggleLeftPanel = toggleLeftPanel;
		}

		logoutClick() {
			Remote.request('AdminLogout', () => rl.logoutReload());
		}
	}

	class SettingsAdminScreen extends AbstractSettingsScreen {
		constructor() {
			super([MenuSettingsAdminView, PaneSettingsAdminView]);

			[
				AdminSettingsGeneral,
				AdminSettingsDomains,
				AdminSettingsLogin,
				AdminSettingsBranding,
				AdminSettingsContacts,
				AdminSettingsSecurity,
				AdminSettingsPackages,
				AdminSettingsConfig,
				AdminSettingsAbout
			].forEach((item, index) =>
				settingsAddViewModel(item, 0, 0, 0, 0 === index)
			);

			runSettingsViewModelHooks(true);
		}

		onShow() {
			rl.setTitle();
		}
	}

	class AdminLoginView extends AbstractViewLogin {
		constructor() {
			super('AdminLogin');

			addObservablesTo(this, {
				login: '',
				password: '',
				totp: '',

				loginError: false,
				passwordError: false,

				submitRequest: false,
				submitError: ''
			});

			addSubscribablesTo(this, {
				login: () => this.loginError(false),
				password: () => this.passwordError(false)
			});

			decorateKoCommands(this, {
				submitCommand: self => !self.submitRequest()
			});
		}

		hideError() {
			this.submitError('');
		}

		submitCommand(self, event) {
			let form = event.target.form,
				data = new FormData(form),
				valid = form.reportValidity() && fireEvent('sm-admin-login', data, 1);

			this.loginError(!this.login());
			this.passwordError(!this.password());
			this.formError(!valid);

			if (valid) {
				this.submitRequest(true);

				Remote.request('AdminLogin',
					(iError, oData) => {
						fireEvent('sm-admin-login-response', {
							error: iError,
							data: oData
						});
						if (iError) {
							this.submitRequest(false);
							this.submitError(getNotification(iError));
						} else {
							rl.setData(oData.Result);
						}
					},
					data
				);
			}

			return valid;
		}
	}

	class LoginAdminScreen extends AbstractScreen {
		constructor() {
			super('login', [AdminLoginView]);
		}

		onShow() {
			rl.setTitle();
		}
	}

	class SelectComponent {
		/**
		 * @param {Object} params
		 */
		constructor(params) {
			this.value = params.value;
			this.label = params.label;
			this.trigger = params.trigger?.subscribe ? params.trigger : null;
			this.placeholder = params.placeholder;
			this.options = params.options;
			this.optionsText = params.optionsText;
			this.optionsValue = params.optionsValue;

			let size = 0 < params.size ? 'span' + params.size : '';
			if (this.trigger) {
				const
					classForTrigger = ko.observable(''),
					setTriggerState = value => {
						switch (value) {
							case SaveSettingStatus.Success:
								classForTrigger('success');
								break;
							case SaveSettingStatus.Failed:
								classForTrigger('error');
								break;
							default:
								classForTrigger('');
								break;
						}
					};

				setTriggerState(this.trigger());

				this.className = koComputable(() =>
					(size + ' settings-save-trigger-input ' + classForTrigger()).trim()
				);

				this.disposables = [
					this.trigger.subscribe(setTriggerState, this),
					this.className
				];
			} else {
				this.className = size;
			}

			this.defaultOptionsAfterRender = defaultOptionsAfterRender;
		}

		dispose() {
			this.disposables?.forEach(dispose);
		}
	}

	class CheckboxComponent {
		constructor(params = {}) {
			this.name = params.name;

			this.value = ko.isObservable(params.value) ? params.value
				: ko.observable(!!params.value);

			this.enable = ko.isObservable(params.enable) ? params.enable
				: ko.observable(params.enable ?? 1);

			this.label = params.label;
		}

		click() {
			this.enable() && this.value(!this.value());
		}
	}

	class AbstractApp {
		/**
		 * @param {RemoteStorage|AdminRemoteStorage} Remote
		 */
		constructor(Remote) {
			this.Remote = Remote;
		}

		logoutReload(url) {
			arePopupsVisible(false);
			url = url || logoutLink();
			if (location.href !== url) {
				setTimeout(() => location.href = url, 100);
			} else {
				rl.route.reload();
			}
			// this does not work due to ViewModelClass.__builded = true;
	//		rl.settings.set('Auth', false);
	//		rl.app.start();
		}

		bootstart() {
			const register = (name, ClassObject) => ko.components.register(name, {
					template: { element: ClassObject.name },
					viewModel: {
						createViewModel: (params, componentInfo) => {
							params = params || {};
							i18nToNodes(componentInfo.element);
							return new ClassObject(params);
						}
					}
				});
			register('Select', SelectComponent);
			register('Checkbox', CheckboxComponent);

			initOnStartOrLangChange();

			LanguageStore.populate();
			initThemes();

			this.start();
		}
	}

	class AdminApp extends AbstractApp {
		constructor() {
			super(Remote);
			this.weakPassword = ko.observable(false);
		}

		refresh() {
			initThemes();
			this.start();
		}

		start() {
	//		if (!Settings.app('adminAllowed')) {
			if (!SettingsAdmin('allowed')) {
				rl.route.root();
				setTimeout(() => location.href = '/', 1);
			} else if (SettingsGet('Auth')) {
				this.weakPassword(SettingsGet('weakPassword'));
				startScreens([SettingsAdminScreen]);
			} else {
				startScreens([LoginAdminScreen]);
			}
		}
	}

	AskPopupView.credentials = function(sAskDesc, btnText) {
		return new Promise(resolve => {
			this.showModal([
				sAskDesc,
				view => resolve({username:view.username(), password:view.passphrase()}),
				() => resolve(null),
				true,
				3,
				btnText
			]);
		});
	};

	bootstrap(new AdminApp);

})();
