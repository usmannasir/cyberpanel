/* SnappyMail Webmail (c) SnappyMail | Licensed under AGPL v3 */
(function () {
	'use strict';

	/* eslint quote-props: 0 */

	const

	/**
	 * @enum {string}
	 */
	ScopeMessageList = 'MessageList',
	ScopeFolderList = 'FolderList',
	ScopeMessageView = 'MessageView',
	ScopeSettings = 'Settings',

	/**
	 * @enum {number}
	 */
	UploadErrorCode = {
		Normal: 0,
		FileIsTooBig: 1,
		FilePartiallyUploaded: 3,
		NoFileUploaded: 4,
		MissingTempFolder: 6,
		OnSavingFile: 7,
		FileType: 98,
		Unknown: 99
	},

	/**
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

	const
		isArray = Array.isArray,
		arrayLength = array => isArray(array) && array.length,
		isFunction = v => typeof v === 'function',
		pString = value => null != value ? '' + value : '',

		forEachObjectValue = (obj, fn) => Object.values(obj).forEach(fn),

		forEachObjectEntry = (obj, fn) => Object.entries(obj).forEach(([key, value]) => fn(key, value)),

		pInt = (value, defaultValue = 0) => {
			value = parseInt(value, 10);
			return isFinite(value) ? value : defaultValue;
		},

		defaultOptionsAfterRender = (domItem, item) =>
			item && undefined !== item.disabled && domItem?.classList.toggle('disabled', domItem.disabled = item.disabled),

		// unescape(encodeURIComponent()) makes the UTF-16 DOMString to an UTF-8 string
		b64Encode = data => btoa(unescape(encodeURIComponent(data))),
	/* 	// Without deprecated 'unescape':
		b64Encode = data => btoa(encodeURIComponent(data).replace(
			/%([0-9A-F]{2})/g, (match, p1) => String.fromCharCode('0x' + p1)
		)),
	*/

		b64EncodeJSON = data => b64Encode(JSON.stringify(data)),

		b64EncodeJSONSafe = data => b64EncodeJSON(data).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''),

		getKeyByValue = (o, v) => Object.keys(o).find(key => o[key] === v);

	let keyScopeFake = 'all';

	const
		ScopeMenu = 'Menu',

		doc = document,

		$htmlCL = doc.documentElement.classList,

		elementById = id => doc.getElementById(id),

		appEl = elementById('rl-app'),

		Settings = rl.settings,
		SettingsGet = Settings.get,
		SettingsAdmin = name => (SettingsGet('Admin') || {})[name],
		SettingsCapa = name => name && !!(SettingsGet('Capa') || {})[name],

		dropdowns = [],
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

		stopEvent = event => {
			event.preventDefault();
			event.stopPropagation();
		},

		formFieldFocused = () => doc.activeElement?.matches('input,textarea'),

		addShortcut = (...args) => shortcuts.add(...args),

		registerShortcut = (keys, modifiers, scopes, method) =>
			addShortcut(keys, modifiers, scopes, event => formFieldFocused() ? true : method(event)),

		addEventsListener = (element, events, fn, options) =>
			events.forEach(event => element.addEventListener(event, fn, options)),

		addEventsListeners = (element, events) =>
			Object.entries(events).forEach(([event, fn]) => element.addEventListener(event, fn)),

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

		/**
		 * @param {string} download
		 * @returns {string}
		 */
		attachmentDownload = (download) =>
			serverRequestRaw('Download', download),

		proxy = url =>
			BASE + '?/ProxyExternal/'
	//			+ btoa(JSON.stringify([token,url]).replace(/ /g, '%20')).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''),
				+ btoa(url.replace(/ /g, '%20')).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''),
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
		 * @param {string} path
		 * @returns {string}
		 */
		staticLink = path => Settings.app('webVersionPath') + 'static/' + path,

		/**
		 * @param {string} theme
		 * @returns {string}
		 */
		themePreviewLink = theme => {
			if (theme.endsWith('@nextcloud')) {
				theme = theme.slice(0, theme.length - 10).trim();
				return parent.OC.webroot + '/themes/' + encodeURI(theme) + '/snappymail/preview.png';
			}
			let path = 'webVersionPath';
			if (theme.endsWith('@custom')) {
				theme = theme.slice(0, theme.length - 7).trim();
				path = 'webPath';
			}
			return Settings.app(path) + 'themes/' + encodeURI(theme) + '/images/preview.png';
		},

		/**
		 * @param {string} inboxFolderName = 'INBOX'
		 * @returns {string}
		 */
		mailbox = (inboxFolderName = 'INBOX') => HASH_PREFIX + 'mailbox/' + inboxFolderName,

		/**
		 * @param {string=} screenName = ''
		 * @returns {string}
		 */
		settings = (screenName = '') => HASH_PREFIX + 'settings' + (screenName ? '/' + screenName : ''),

		/**
		 * @param {string} folder
		 * @param {number=} page = 1
		 * @param {string=} search = ''
		 * @param {number=} threadUid = 0
		 * @returns {string}
		 */
		mailBox = (folder, page, search, threadUid, messageUid) => {
			let result = [HASH_PREFIX + 'mailbox'];

			if (folder) {
				result.push(folder + (threadUid ? '~' + threadUid : ''));
			}

			if (messageUid) {
				result.push('m' + messageUid);
			} else {
				page = pInt(page, 1);
				if (1 < page) {
					result.push('p' + page);
				}
				search && result.push(encodeURI(search));
			}

			return result.join('/');
		};

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

	const
		init = () => {
			if (rl.I18N) {
				I18N_DATA = rl.I18N;
				rl.I18N = null;
				doc.documentElement.dir = I18N_DATA.LANG_DIR;
				return 1;
			}
		},

		i18nKey = key => key.replace(/([a-z])([A-Z])/g, '$1_$2').toUpperCase(),

		getNotificationMessage = code => {
			let key = getKeyByValue(Notifications, code);
			return key ? I18N_DATA.NOTIFICATIONS[key] : '';
		},

		fromNow = date => relativeTime(Math.round((date.getTime() - Date.now()) / 1000));

	const
		translateTrigger = ko.observable(false),

		// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/RelativeTimeFormat
		// see /snappymail/v/0.0.0/app/localization/relativetimeformat/
		relativeTime = seconds => {
			let unit = 'second',
				t = [[60,'minute'],[3600,'hour'],[86400,'day'],[2628000,'month'],[31536000,'year']],
				i = 5,
				abs = Math.abs(seconds);
			while (i--) {
				if (t[i][0] <= abs) {
					seconds = Math.round(seconds / t[i][0]);
					unit = t[i][1];
					break;
				}
			}
			if (Intl.RelativeTimeFormat) {
				return (new Intl.RelativeTimeFormat(doc.documentElement.lang)).format(seconds, unit);
			}
			// Safari < 14
			abs = Math.abs(seconds);
			let rtf = rl.relativeTime.long[unit][0 > seconds ? 'past' : 'future'],
				plural = rl.relativeTime.plural(abs);
			return (rtf[plural] || rtf).replace('{0}', abs);
		},

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

		timestampToString = (timeStampInUTC, formatStr) => {
			const now = Date.now(),
				time = 0 < timeStampInUTC ? timeStampInUTC * 1000 : (0 === timeStampInUTC ? now : 0);
			if (31536000000 < time) {
				const m = new Date(time), h = LanguageStore.hourCycle();
				switch (formatStr) {
					case 'FROMNOW':
						return fromNow(m);
					case 'AUTO': {
						// 4 hours
						if (14400000 >= now - time)
							return fromNow(m);
						const date = new Date,
							dt = date.setHours(0,0,0,0);
						return (time > dt - 86400000)
							? i18n(
								time > dt ? 'MESSAGE_LIST/TODAY_AT' : 'MESSAGE_LIST/YESTERDAY_AT',
								{TIME: m.format('LT',0,h)}
							)
							: m.format(
								date.getFullYear() === m.getFullYear()
									? {day: '2-digit', month: 'short', hour: 'numeric', minute: 'numeric'}
									: {dateStyle: 'medium', timeStyle: 'short'}
								, 0, h);
					}
					case 'FULL':
						return m.format('LLL',0,h);
					default:
						return m.format(formatStr,0,h);
				}
			}

			return '';
		},

		timeToNode = (element, time) => {
			try {
				if (time) {
					element.dateTime = new Date(time * 1000).toISOString();
				} else {
					time = Date.parse(element.dateTime) / 1000;
				}

				let key = element.dataset.timeFormat;
				if (key) {
					element.textContent = timestampToString(time, key);
					if ('FULL' !== key && 'FROMNOW' !== key) {
						element.title = timestampToString(time, 'FULL');
					}
				}
			} catch (e) {
				// prevent knockout crashes
				console.error(e);
			}
		},

		reloadTime = () => doc.querySelectorAll('time').forEach(element => timeToNode(element)),

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

		getErrorMessage = (code, data) =>
			getNotification(code) || data?.messageAdditional || data?.message || data,

		/**
		 * @param {*} code
		 * @returns {string}
		 */
		getUploadErrorDescByCode = code => {
			let key = getKeyByValue(UploadErrorCode, parseInt(code, 10));
			return i18n('UPLOAD/ERROR_' + (key ? i18nKey(key) : 'UNKNOWN'));
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
			),

		baseCollator = numeric => new Intl.Collator(doc.documentElement.lang, {numeric: !!numeric, sensitivity: 'base'});

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

	const
		errorTip = (element, value) => value
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
		},

		// With this we don't need delegateRunOnDestroy
		koArrayWithDestroy = data => {
			data = ko.observableArray(data);
			data.subscribe(changes =>
				changes.forEach(item =>
					'deleted' === item.status && null == item.moved && item.value.onDestroy?.()
				)
			, data, 'arrayChange');
			return data;
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

	/* eslint key-spacing: 0 */

	const RFC822 = 'message/rfc822';

	const
		cache = {},
		app = 'application/',
		msOffice = app+'vnd.openxmlformats-officedocument.',
		openDoc = app+'vnd.oasis.opendocument.',
		sizes = ['B', 'KiB', 'MiB', 'GiB', 'TiB'],
		lowerCase = text => text.toLowerCase().trim(),

		exts = {
			eml: RFC822,
			mime: RFC822,
			vcard: 'text/vcard',
			vcf: 'text/vcard',
			htm: 'text/html',
			html: 'text/html',
			csv: 'text/csv',
			ics: 'text/calendar',
			xml: 'text/xml',
			json: app+'json',
	//		asc: app+'pgp-signature',
	//		asc: app+'pgp-keys',
			p10: app+'pkcs10',
			p7c: app+'pkcs7-mime',
			p7m: app+'pkcs7-mime',
			p7s: app+'pkcs7-signature',
			p12: app+'pkcs12',
			pfx: app+'x-pkcs12',
			torrent: app+'x-bittorrent',

			// scripts
			js: app+'javascript',
			pl: 'text/perl',
			css: 'text/css',
			asp: 'text/asp',
			php: app+'x-php',

			// images
			jpg: 'image/jpeg',
			ico: 'image/x-icon',
			tif: 'image/tiff',
			svg: 'image/svg+xml',
			svgz: 'image/svg+xml',

			// archives
			zip: app+'zip',
			'7z': app+'x-7z-compressed',
			rar: app+'x-rar-compressed',
			cab: app+'vnd.ms-cab-compressed',
			gz: app+'x-gzip',
			tgz: app+'x-gzip',
			bz: app+'x-bzip',
			bz2: app+'x-bzip2',
			deb: app+'x-debian-package',

			// audio
			mp3: 'audio/mpeg',
			wav: 'audio/x-wav',
			mp4a: 'audio/mp4',
			weba: 'audio/webm',
			m3u: 'audio/x-mpegurl',

			// video
			qt: 'video/quicktime',
			mov: 'video/quicktime',
			wmv: 'video/windows-media',
			avi: 'video/x-msvideo',
			'3gp': 'video/3gpp',
			'3g2': 'video/3gpp2',
			mp4v: 'video/mp4',
			mpg4: 'video/mp4',
			ogv: 'video/ogg',
			m4v: 'video/x-m4v',
			asf: 'video/x-ms-asf',
			asx: 'video/x-ms-asf',
			wm: 'video/x-ms-wm',
			wmx: 'video/x-ms-wmx',
			wvx: 'video/x-ms-wvx',
			movie: 'video/x-sgi-movie',

			// adobe
			pdf: app+'pdf',
			psd: 'image/vnd.adobe.photoshop',
			ai: app+'postscript',
			eps: app+'postscript',
			ps: app+'postscript',

			// ms office
			doc: app+'msword',
			rtf: app+'rtf',
			xls: app+'vnd.ms-excel',
			ppt: app+'vnd.ms-powerpoint',
			docx: msOffice+'wordprocessingml.document',
			xlsx: msOffice+'spreadsheetml.sheet',
			dotx: msOffice+'wordprocessingml.template',
			pptx: msOffice+'presentationml.presentation',

			// open office
			odt: openDoc+'text',
			ods: openDoc+'spreadsheet',
			odp: openDoc+'presentation'
		};

	const FileType = {
		Unknown: 'unknown',
		Text: 'text',
		Code: 'code',
		Eml: 'eml',
		Word: 'word',
		Pdf: 'pdf',
		Image: 'image',
		Audio: 'audio',
		Video: 'video',
		Spreadsheet: 'spreadsheet',
		Presentation: 'presentation',
		Certificate: 'certificate',
		Archive: 'archive',
		Calendar: 'calendar'
	};

	const FileInfo = {
		/**
		 * @param {string} fileName
		 * @returns {string}
		 */
		getExtension: fileName => {
			fileName = lowerCase(fileName);
			const result = fileName.split('.').pop();
			return result === fileName ? '' : result;
		},

		getContentType: fileName => {
			fileName = lowerCase(fileName);
			if ('winmail.dat' === fileName) {
				return app + 'vnd.ms-tnef';
			}
			let ext = fileName.split('.').pop();
			if (/^(txt|text|def|list|in|ini|log|sql|cfg|conf)$/.test(ext))
				return 'text/plain';
			if (/^(mpe?g|mpe|m1v|m2v)$/.test(ext))
				return 'video/mpeg';
			if (/^aif[cf]?$/.test(ext))
				return 'audio/aiff';
			if (/^(aac|flac|midi|ogg)$/.test(ext))
				return 'audio/'+ext;
			if (/^(h26[134]|jpgv|mp4|webm)$/.test(ext))
				return 'video/'+ext;
			if (/^(otf|sfnt|ttf|woff2?)$/.test(ext))
				return 'font/'+ext;
			if (/^(png|jpeg|gif|tiff|webp)$/.test(ext))
				return 'image/'+ext;

			return exts[ext] || app+'octet-stream';
		},

		/**
		 * @param {string} sExt
		 * @param {string} sMimeType
		 * @returns {string}
		 */
		getType: (ext, mimeType) => {
			ext = lowerCase(ext);
			mimeType = lowerCase(mimeType).replace('csv/plain', 'text/csv').replace('x-','');

			let key = ext + mimeType;
			if (cache[key]) {
				return cache[key];
			}

			let result = FileType.Unknown;
			const mimeTypeParts = mimeType.split('/'),
				type = mimeTypeParts[1].replace('-compressed',''),
				match = str => mimeType.includes(str),
				archive = /^(zip|7z|tar|rar|gzip|bzip|bzip2)$/;

			switch (true) {
				case 'image' == mimeTypeParts[0] || ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext):
					result = FileType.Image;
					break;
				case 'audio' == mimeTypeParts[0] || ['mp3', 'ogg', 'oga', 'wav'].includes(ext):
					result = FileType.Audio;
					break;
				case 'video' == mimeTypeParts[0] || 'mkv' == ext || 'avi' == ext:
					result = FileType.Video;
					break;
				case ['php', 'js', 'css', 'xml', 'html'].includes(ext) || 'text/html' == mimeType:
					result = FileType.Code;
					break;
				case 'eml' == ext || ['message/delivery-status', RFC822].includes(mimeType):
					result = FileType.Eml;
					break;
				case 'ics' == ext || mimeType == 'text/calendar':
					result = FileType.Calendar;
					break;
				case 'text' == mimeTypeParts[0] || 'txt' == ext || 'log' == ext:
					result = FileType.Text;
					break;
				case archive.test(type) || archive.test(ext):
					result = FileType.Archive;
					break;
				case 'pdf' == type || 'pdf' == ext:
					result = FileType.Pdf;
					break;
				case [app+'pgp-signature', app+'pgp-keys', exts.p7m, exts.p7s, exts.p12, exts.pfx].includes(mimeType)
					|| ['asc', 'pem', 'ppk', 'p7s', 'p7m', 'p12', 'pfx'].includes(ext):
					result = FileType.Certificate;
					break;
				case match(msOffice+'.wordprocessingml') || match(openDoc+'.text') || match('vnd.ms-word')
					|| ['rtf', 'msword', 'vnd.msword'].includes(type):
					result = FileType.Word;
					break;
				case match(msOffice+'.spreadsheetml') || match(openDoc+'.spreadsheet') || match('ms-excel'):
					result = FileType.Spreadsheet;
					break;
				case match(msOffice+'.presentationml') || match(openDoc+'.presentation') || match('ms-powerpoint'):
					result = FileType.Presentation;
					break;
				// no default
			}

			return cache[key] = result;
		},

		/**
		 * @param {string} sFileType
		 * @returns {string}
		 */
		getTypeIconClass: fileType => {
			let result = 'icon-file';
			switch (fileType) {
				case FileType.Text:
				case FileType.Eml:
				case FileType.Pdf:
				case FileType.Word:
					return result + '-text';
				case FileType.Code:
				case FileType.Image:
				case FileType.Audio:
				case FileType.Video:
				case FileType.Archive:
				case FileType.Certificate:
				case FileType.Spreadsheet:
				case FileType.Presentation:
				case FileType.Calendar:
					return result + '-' + fileType;
			}
			return result;
		},

		getIconClass: (ext, mime) => FileInfo.getTypeIconClass(FileInfo.getType(ext, mime)),

		/**
		 * @param {string} sFileType
		 * @returns {string}
		 */
		getAttachmentsIconClass: data => {
			if (arrayLength(data)) {
				let icons = data
					.map(item => item ? FileInfo.getIconClass(FileInfo.getExtension(item.fileName), item.mimeType) : '')
					.validUnique();

				return (1 === icons?.length && 'icon-file' !== icons[0])
					 ? icons[0]
					 : 'icon-attachment';
			}

			return '';
		},

		friendlySize: bytes => {
			bytes = pInt(bytes);
			let i = bytes ? Math.floor(Math.log(bytes) / Math.log(1024)) : 0;
			return (bytes / Math.pow(1024, i)).toFixed(2>i ? 0 : 1) + ' ' + sizes[i];
		}

	};

	/* eslint quote-props: 0 */

	/**
	 * @enum {number}
	 */
	const FolderType = {
		Inbox: 1,
		Sent: 2,
		Drafts: 3,
		Junk: 4, // Spam
		Trash: 5,
		Archive: 6
	/*
		IMPORTANT : 10;
		FLAGGED : 11;
		ALL : 13;
		// TODO: SnappyMail
		TEMPLATES : 19;
		// Kolab
		CONFIGURATION : 20;
		CALENDAR : 21;
		CONTACTS : 22;
		TASKS    : 23;
		NOTES    : 24;
		FILES    : 25;
		JOURNAL  : 26;
	*/
	},

	/**
	 * @enum {string}
	 */
	FolderMetadataKeys = {
		// RFC 5464
		Comment: '/private/comment',
		CommentShared: '/shared/comment',
		// RFC 6154
		SpecialUse: '/private/specialuse',
		// Kolab
		KolabFolderType: '/private/vendor/kolab/folder-type',
		KolabFolderTypeShared: '/shared/vendor/kolab/folder-type'
	},

	/**
	 * @enum {string}
	 */
	ComposeType = {
		Empty: 0,
		Reply: 1,
		ReplyAll: 2,
		Forward: 3,
		ForwardAsAttachment: 4,
		Draft: 5,
		EditAsNew: 6
	},

	/**
	 * @enum {number}
	 */
	ClientSideKeyNameExpandedFolders = 3,
	ClientSideKeyNameFolderListSize = 4,
	ClientSideKeyNameMessageListSize = 5,
	ClientSideKeyNameLastSignMe = 7,
	ClientSideKeyNameMessageHeaderFullInfo = 9,
	ClientSideKeyNameMessageAttachmentControls = 10,

	/**
	 * @enum {number}
	 */
	MessageSetAction = {
		SetSeen: 0,
		UnsetSeen: 1,
		SetFlag: 2,
		UnsetFlag: 3,
		SetDeleted: 4,
		UnsetDeleted: 5
	},

	/**
	 * @enum {number}
	 */
	//LayoutNoView = 0,
	LayoutSideView = 1,
	LayoutBottomView = 2
	;

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

	const SettingsUserStore = new class {
		constructor() {
			const self = this;

			self.messagesPerPage = ko.observable(25).extend({ debounce: 999 });
			self.checkMailInterval = ko.observable(15).extend({ debounce: 999 });
			self.messageReadDelay = ko.observable(5).extend({ debounce: 999 });

			addObservablesTo(self, {
				viewHTML: 1,
				viewImages: 0,
				viewImagesWhitelist: '',
				removeColors: 0,
				allowStyles: 0,
				collapseBlockquotes: 1,
				maxBlockquotesLevel: 0,
				listInlineAttachments: 0,
				simpleAttachmentsList: 0,
				useCheckboxesInList: 1,
				listGrouped: 0,
				showNextMessage: 0,
				allowDraftAutosave: 1,
				useThreads: 0,
				threadAlgorithm: '',
				replySameFolder: 0,
				hideUnsubscribed: 0,
				hideDeleted: 1,
				unhideKolabFolders: 0,
				autoLogout: 0,
				keyPassForget: 15,
				showUnreadCount: 0,
				messageNewWindow: 0,
				messageReadAuto: 0,

				requestReadReceipt: 0,
				requestDsn: 0,
				requireTLS: 0,
				pgpSign: 0,
				pgpEncrypt: 0,
				allowSpellcheck: 0,

				layout: 1,
				editorDefaultType: 'Html',
				editorWysiwyg: 'Squire',
				markdown: 0,
				msgDefaultAction: 1
			});

			self.init();

			self.usePreviewPane = koComputable(() => ThemeStore.isMobile() ? 0 : self.layout());

			const toggleLayout = () => {
				const value = self.usePreviewPane();
				$htmlCL.toggle('sm-msgView-side', LayoutSideView === value);
				$htmlCL.toggle('sm-msgView-bottom', LayoutBottomView === value);
				fireEvent('rl-layout', value);
			};
			self.layout.subscribe(toggleLayout);
			ThemeStore.isMobile.subscribe(toggleLayout);
			toggleLayout();

			let iAutoLogoutTimer;
			self.delayLogout = (() => {
				clearTimeout(iAutoLogoutTimer);
				if (0 < self.autoLogout() && !SettingsGet('accountSignMe')) {
					iAutoLogoutTimer = setTimeout(
						rl.app.logout,
						self.autoLogout() * 60000
					);
				}
			}).throttle(5000);
		}

		init() {
			const self = this;

			[
				'EditorDefaultType',
				'editorWysiwyg',
				'messageNewWindow',
				'messageReadAuto',
				'MsgDefaultAction',
				'ViewHTML',
				'ViewImages',
				'ViewImagesWhitelist',
				'RemoveColors',
				'AllowStyles',
				'CollapseBlockquotes',
				'MaxBlockquotesLevel',
				'ListInlineAttachments',
				'simpleAttachmentsList',
				'UseCheckboxesInList',
				'listGrouped',
				'showNextMessage',
				'AllowDraftAutosave',
				'useThreads',
				'threadAlgorithm',
				'ReplySameFolder',
				'HideUnsubscribed',
				'HideDeleted',
				'ShowUnreadCount',
				'UnhideKolabFolders',
				'requestReadReceipt',
				'requestDsn',
				'requireTLS',
				'pgpSign',
				'pgpEncrypt',
				'allowSpellcheck',
				'markdown'
	/*
				'MessagesPerPage',
				'MessageReadDelay',
				'SoundNotification',
				'NotificationSound',
				'DesktopNotifications',
				'Layout',
				'AutoLogout',
				'ContactsAutosave',
				'contactsAllowed',
				'CheckMailInterval',
				'SentFolder',
				'DraftsFolder',
				'JunkFolder',
				'TrashFolder',
				'ArchiveFolder',
				'hourCycle',
				'Resizer4Width',
				'Resizer5Width',
				'Resizer5Height',
				'fontSansSerif',
				'fontSerif',
				'fontMono',
				'userBackgroundName',
				'userBackgroundHash',
				'autoVerifySignatures',
				'allowLanguagesOnSettings',
				'attachmentLimit',
				'Theme',
				'language',
				'clientLanguage',
				'StaticLibsJs',
	*/
			].forEach(name => {
				let value = SettingsGet(name);
				name = name[0].toLowerCase() + name.slice(1);
				self[name](value);
			});

			self.layout(pInt(SettingsGet('Layout')));
			self.messagesPerPage(pInt(SettingsGet('MessagesPerPage')));
			self.checkMailInterval(pInt(SettingsGet('CheckMailInterval')));
			self.messageReadDelay(pInt(SettingsGet('MessageReadDelay')));
			self.autoLogout(pInt(SettingsGet('AutoLogout')));
			self.keyPassForget(pInt(SettingsGet('keyPassForget')));
		}
	};

	const
		WYSIWYGS = ko.observableArray();

	WYSIWYGS.push({
		name: 'Squire',
		construct: (owner, container, onReady) => onReady(new SquireUI(container))
	});

	rl.registerWYSIWYG = (name, construct) => WYSIWYGS.push({name, construct});

	class HtmlEditor {
		/**
		 * @param {Object} element
		 * @param {Function=} onBlur
		 * @param {Function=} onReady
		 * @param {Function=} onModeChange
		 */
		constructor(element, onReady = null, onModeChange = null, onBlur = null) {
			this.blurTimer = 0;

			this.onBlur = onBlur;
			this.onModeChange = onModeChange;

			if (element) {
				onReady = onReady ? [onReady] : [];
				this.onReady = fn => onReady.push(fn);
				const which = SettingsUserStore.editorWysiwyg(),
					wysiwyg = WYSIWYGS.find(item => which == item.name) || WYSIWYGS.find(item => 'Squire' == item.name);
				wysiwyg.construct(this, element, editor => setTimeout(()=>{
					this.editor = editor;
					editor.on('blur', () => this.blurTrigger());
					editor.on('focus', () => clearTimeout(this.blurTimer));
					editor.on('mode', () => {
						this.blurTrigger();
						this.onModeChange?.(!this.isPlain());
					});
					this.onReady = fn => fn();
					onReady.forEach(fn => fn());
				},1));
			}
		}

		blurTrigger() {
			if (this.onBlur) {
				clearTimeout(this.blurTimer);
				this.blurTimer = setTimeout(() => this.onBlur?.(), 200);
			}
		}

		/**
		 * @returns {boolean}
		 */
		isHtml() {
			return this.editor ? !this.isPlain() : false;
		}

		/**
		 * @returns {boolean}
		 */
		isPlain() {
			return this.editor ? 'plain' === this.editor.mode : false;
		}

		/**
		 * @returns {void}
		 */
		clearCachedSignature() {
			this.onReady(() => this.editor.execCommand('insertSignature', {
				clearCache: true
			}));
		}

		/**
		 * @param {string} signature
		 * @param {bool} html
		 * @param {bool} insertBefore
		 * @returns {void}
		 */
		setSignature(signature, html, insertBefore = false) {
			this.onReady(() => this.editor.execCommand('insertSignature', {
				isHtml: html,
				insertBefore: insertBefore,
				signature: signature
			}));
		}

		/**
		 * @param {boolean=} wrapIsHtml = false
		 * @returns {string}
		 */
		getData() {
			let result = '';
			if (this.editor) {
				try {
					if (this.isPlain()) {
						result = this.editor.getPlainData();
					} else {
						result = this.editor.getData();
					}
				} catch (e) {} // eslint-disable-line no-empty
			}
			return result;
		}

		/**
		 * @returns {string}
		 */
		getDataWithHtmlMark() {
			return (this.isHtml() ? ':HTML:' : '') + this.getData();
		}

		modeWysiwyg() {
			this.onReady(() => this.editor.setMode('wysiwyg'));
		}
		modePlain() {
			this.onReady(() => this.editor.setMode('plain'));
		}

		setHtmlOrPlain(text) {
			text.startsWith(':HTML:')
				? this.setHtml(text.slice(6))
				: this.setPlain(text);
		}

		setData(mode, data) {
			this.onReady(() => {
				const editor = this.editor;
				this.clearCachedSignature();
				try {
					editor.setMode(mode);
					if (this.isPlain()) {
						editor.setPlainData(data);
					} else {
						editor.setData(data);
					}
				} catch (e) { console.error(e); }
			});
		}

		setHtml(html) {
			this.setData('wysiwyg', html/*.replace(/<p[^>]*><\/p>/gi, '')*/);
		}

		setPlain(txt) {
			this.setData('plain', txt);
		}

		focus() {
			this.onReady(() => this.editor.focus());
		}

		blur() {
			this.onReady(() => this.editor.blur());
		}

		clear() {
			this.onReady(() => this.isPlain() ? this.setPlain('') : this.setHtml(''));
		}
	}

	const
		tmpl = createElement('template'),

		turndown = new TurndownService(),

		htmlre = /[&<>"']/g,
		httpre = /^(https?:)?\/\//i,
		htmlmap = {
			'&': '&amp;',
			'<': '&lt;',
			'>': '&gt;',
			'"': '&quot;',
			"'": '&#x27;'
		},

		keepTagContent = 'form,button,data', // font

		allowedTags = [
			// Structural Elements:
			'blockquote','br','div','figcaption','figure','h1','h2','h3','h4','h5','h6','hgroup','hr','p','wbr',
			'article','aside','header','footer','main','section',
			'details','summary','nav',
			// List Elements
			'dd','dl','dt','li','ol','ul',
			// Text Formatting Elements
			'a','abbr','address','b','bdi','bdo','cite','code','del','dfn',
			'em','i','ins','kbd','mark','pre','q','rp','rt','ruby','s','samp','small',
			'span','strong','sub','sup','time','u','var',
			// Deprecated by HTML Standard
			'acronym','big','center','dir','font','marquee',
			'nobr','plaintext','rb','rtc','strike','tt',
			// Media Elements
			'img',//'picture','source',
			// Table Elements
			'caption','col','colgroup','table','tbody','td','tfoot','th','thead','tr',
			// Disallowed but converted later
			'style','xmp'
		].join(','),

		nonEmptyTags = [
			'A','B','EM','I','SPAN','STRONG'
		],

		blockquoteSwitcher = () => {
			SettingsUserStore.collapseBlockquotes() &&
	//		tmpl.content.querySelectorAll('blockquote').forEach(node => {
			[...tmpl.content.querySelectorAll('blockquote')].reverse().forEach(node => {
				const el = createElement('details', {class:'sm-bq-switcher'});
				el.innerHTML = '<summary>•••</summary>';
				node.replaceWith(el);
				el.append(node);
			});
		},

		replaceWithChildren = node => node.replaceWith(...[...node.childNodes]),

		urlRegExp = /https?:\/\/[^\p{C}\p{Z}]+[^\p{C}\p{Z}.]/gu,
		// eslint-disable-next-line max-len
		email = /(^|\r|\n|\p{C}\p{Z})((?:[^"(),.:;<>@[\]\\\p{C}\p{Z}]+(?:\.[^"(),.:;<>@[\]\\\p{C}\p{Z}]+)*|"(?:\\?[^"\\\p{C}\p{Z}])*")@[^@\p{C}\p{Z}]+[^@\p{C}\p{Z}.])/gui,
		// rfc3966
		tel = /(tel:(\+[0-9().-]+|[0-9*#().-]+(;phone-context=\+[0-9+().-]+)?))/g,

		// Strip tracking
		/** TODO: implement other url strippers like from
		 * https://www.bleepingcomputer.com/news/security/new-firefox-privacy-feature-strips-urls-of-tracking-parameters/
		 * https://github.com/newhouse/url-tracking-stripper
		 * https://github.com/svenjacobs/leon
		 * https://maxchadwick.xyz/tracking-query-params-registry/
		 * https://github.com/M66B/FairEmail/blob/master/app/src/main/java/eu/faircode/email/UriHelper.java
		 */
		// eslint-disable-next-line max-len
		stripParams = /^(utm_|ec_|fbclid|mc_eid|mkt_tok|_hsenc|vero_id|oly_enc_id|oly_anon_id|__s|Referrer|mailing|elq|bch|trc|ref|correlation_id|pd_|pf_|email_hash)$/i,
		urlGetParam = (url, name) => new URL(url).searchParams.get(name) || url,
		base64Url = data => atob(data.replace(/_/g,'/').replace(/-/g,'+')),
		decode = decodeURIComponent,
		stripTracking = url => {
			try {
				let nurl = url
					// Copernica
					.replace(/^.+\/(https%253A[^/?&]+).*$/i, (...m) => decode(decode(m[1])))
					.replace(/tracking\.(printabout\.nl[^?]+)\?.*/i, (...m) => m[1])
					.replace(/(zalando\.nl[^?]+)\?.*/i, (...m) => m[1])
					.replace(/^.+(awstrack\.me|redditmail\.com)\/.+(https:%2F%2F[^/]+).*/i, (...m) => decode(m[2]))
					.replace(/^.+(www\.google|safelinks\.protection\.outlook\.com|mailchimp\.com).+url=.+$/i,
						() => urlGetParam(url, 'url'))
					.replace(/^.+click\.godaddy\.com.+$/i, () => urlGetParam(url, 'redir'))
					.replace(/^.+delivery-status\.com.+$/i, () => urlGetParam(url, 'fb'))
					.replace(/^.+go\.dhlparcel\.nl.+\/([A-Za-z0-9_-]+)$/i, (...m) => base64Url(m[1]))
					.replace(/^(.+mopinion\.com.+)\?.*$/i, (...m) => m[1])
					.replace(/^.+sellercentral\.amazon\.com\/nms\/redirect.+$/i, () => base64Url(urlGetParam(url, 'u')))
					.replace(/^.+amazon\.com\/gp\/r\.html.+$/i, () => urlGetParam(url, 'U'))
					// Mandrill
					.replace(/^.+\/track\/click\/.+\?p=.+$/i, () => {
						let d = urlGetParam(url, 'p');
						try {
							d = JSON.parse(base64Url(d));
							if (d?.p) {
								d = JSON.parse(d.p);
							}
						} catch (e) {
							console.error(e);
						}
						return d?.url || url;
					})
					// Remove invalid URL characters
					.replace(/[\s<>]+/gi, '');
				nurl = new URL(nurl);
				let s = nurl.searchParams;
				[...s.keys()].forEach(key => stripParams.test(key) && s.delete(key));
				return nurl.toString();
			} catch (e) {
				console.dir({
					error:e,
					url:url
				});
			}
			return url;
		},

		cleanCSS = source =>
			source.trim()
				.replace(/;\s*-[^;]+/g, '')
				.replace(/^\s*-[^;]+(;|$)/g, '')
				.replace(/white-space[^;]+/g, '')
				// Drop Microsoft Office style properties
	//			.replace(/mso-[^:;]+:[^;]+/gi, '')
		,

		/*
			Parses given css string, and returns css object
			keys as selectors and values are css rules
			eliminates all css comments before parsing

			@param source css string to be parsed

			@return object css
		*/
		parseCSS = source => {
			const css = [];
			css.toString = () => css.reduce(
				(ret, tmp) =>
					ret + tmp.selector + ' {\n'
						+ (tmp.type === 'media' ? tmp.subStyles.toString() : tmp.rules)
						+ '}\n'
				,
				''
			);
			/**
			 * Given css array, parses it and then for every selector,
			 * prepends namespace to prevent css collision issues
			 */
			css.applyNamespace = namespace => css.forEach(obj => {
				if (obj.type === 'media') {
					obj.subStyles.applyNamespace(namespace);
				} else {
					obj.selector = obj.selector.split(',').map(selector =>
						(namespace + ' .mail-body ' + selector.replace(/\./g, '.msg-'))
						.replace(/\sbody/gi, '')
					).join(',');
				}
			});

			if (source) {
				source = source
					// strip comments
					.replace(/\/\*[\s\S]*?\*\//gi, '')
					// strip MS Word comments
					.replace(/<!--[\s\S]*?-->/gi, '')
					// strip HTML, as < is no CSS combinator anyway
					.replace(/<[\s\S]*/gi, '');
	//				.replace(/<\/?[a-z][\s\S]*?>/gi, '');

				// unified regex to match css & media queries together
				let unified = /(?:(\s*?@(?:media)[\s\S]*?){([\s\S]*?)}\s*?})|(?:([\s\S]*?){([\s\S]*?)})/gi,
					arr;

				while (true) {
					arr = unified.exec(source);
					if (arr === null) {
						break;
					}

					let selector = arr[arr[2] === undefined ? 3 : 1].split('\r\n').join('\n').trim()
						// Never have more than a single line break in a row
						.replace(/\n+/, "\n")
						// Remove :root and html
						.split(/\s+/g).map(item => item.replace(/^(:root|html)$/, '')).join(' ').trim();

					// determine the type
					if (selector.includes('@media')) {
						// we have a media query
						css.push({
							selector: selector,
							type: 'media',
							subStyles: parseCSS(arr[2] + '\n}') //recursively parse media query inner css
						});
					} else if (selector && !selector.includes('@')) {
						// we have standard css
						// ignores @import, @keyframe, @font-face statements
						css.push({
							selector: selector,
							rules: cleanCSS(arr[4])
						});
					}
				}
			}

			return css;
		};

	const

		/**
		 * @param {string} text
		 * @returns {string}
		 */
		encodeHtml = text => (text?.toString?.() || '' + text).replace(htmlre, m => htmlmap[m]),

		/**
		 * Clears the Message Html for viewing
		 * @param {string} text
		 * @returns {string}
		 */
		cleanHtml = (html, oAttachments, msgId) => {
			let aColor;
			const bqLevel = parseInt(SettingsUserStore.maxBlockquotesLevel()),

				result = {
					hasExternals: false,
					tracking: false,
					linkedData: []
				},

				isMsg = !!msgId,

				findAttachmentByCid = cId => oAttachments.findByCid(cId),
				findLocationByCid = cId => {
					const attachment = findAttachmentByCid(cId);
					return attachment?.contentLocation ? attachment : 0;
				},

				// convert body attributes to CSS
				tasks = {
					link: value => aColor = value,
					text: (value, node) => node.style.color = value,
					topmargin: (value, node) => node.style.marginTop = pInt(value) + 'px',
					leftmargin: (value, node) => node.style.marginLeft = pInt(value) + 'px',
					bottommargin: (value, node) => node.style.marginBottom = pInt(value) + 'px',
					rightmargin: (value, node) => node.style.marginRight = pInt(value) + 'px'
				},
				allowedAttributes = [
					// defaults
					'name',
					'dir', 'lang', 'style', 'title',
					'background', 'bgcolor', 'alt', 'height', 'width', 'src', 'href',
					'border', 'bordercolor', 'charset', 'direction',
					// a
					'download', 'hreflang',
					// body
					'alink', 'bottommargin', 'leftmargin', 'link', 'rightmargin', 'text', 'topmargin', 'vlink',
					// col
					'align', 'valign',
					// font
					'color', 'face', 'size',
					// hr
					'noshade',
					// img
					'hspace', 'sizes', 'srcset', 'vspace',
					// meter
					'low', 'high', 'optimum', 'value',
					// ol
					'reversed', 'start',
					// table
					'cols', 'rows', 'frame', 'rules', 'summary', 'cellpadding', 'cellspacing',
					// th
					'abbr', 'scope',
					// td
					'colspan', 'rowspan', 'headers'
					// others
					//'class', 'id', 'target'
				];

			if (SettingsUserStore.allowStyles()) {
				allowedAttributes.push('class');
			} else {
				msgId = 0;
			}

			tmpl.innerHTML = html
	//			.replace(/<pre[^>]*>[\s\S]*?<\/pre>/gi, pre => pre.replace(/\n/g, '\n<br>'))
				// Not supported by <template> element
	//			.replace(/<!doctype[^>]*>/gi, '')
	//			.replace(/<\?xml[^>]*\?>/gi, '')
				.replace(/<(\/?)head(\s[^>]*)?>/gi, '')
				.replace(/<(\/?)body(\s[^>]*)?>/gi, '<$1div class="mail-body"$2>')
	//			.replace(/<\/?(html|head)[^>]*>/gi, '')
				// Fix Reddit https://github.com/the-djmaze/snappymail/issues/540
				.replace(/<span class="preview-text"[\s\S]+?<\/span>/, '')
				// https://github.com/the-djmaze/snappymail/issues/900
				.replace(/\u2028/g,' ')
				// https://github.com/the-djmaze/snappymail/issues/1415
				.replace(/<br>\s*<\/p>/gi,'</p>')
				.trim();
			html = '';

			// Strip all comments
			const nodeIterator = document.createNodeIterator(tmpl.content, NodeFilter.SHOW_COMMENT);
			while (nodeIterator.nextNode()) {
				nodeIterator.referenceNode.remove();
			}

			/**
			 * Basic support for Linked Data (Structured Email)
			 * https://json-ld.org/
			 * https://structured.email/
			 **/
			tmpl.content.querySelectorAll('script[type="application/ld+json"]').forEach(oElement => {
				// Could be array of objects or single object
				try {
					const data = JSON.parse(oElement.textContent);
					(isArray(data) ? data : [data]).forEach(entry => result.linkedData.push(entry));
				} catch (e) {
					console.error(e, oElement.textContent);
				}
			});

			// https://github.com/the-djmaze/snappymail/issues/1125
			tmpl.content.querySelectorAll(keepTagContent).forEach(oElement => replaceWithChildren(oElement));

			tmpl.content.querySelectorAll(
				':not('+allowedTags+'),a:empty,span:empty'
				+ (0 < bqLevel ? ',' + (new Array(1 + bqLevel).fill('blockquote').join(' ')) : '')
			).forEach(oElement => oElement.remove());
	/*		// Is this slower or faster?
			).forEach(oElement => {
				if (!node || !node.contains(oElement)) {
					oElement.remove();
					node = oElement;
				}
			});
	*/

			// https://github.com/the-djmaze/snappymail/issues/1641
			let body = tmpl.content.querySelector('.mail-body');
			[...tmpl.content.querySelectorAll('.mail-body + .mail-body')]
				.forEach(oElement => body.append(...oElement.childNodes));
	/*
				.forEach(oElement => {
					let bq = createElement('blockquote');
					bq.append(...oElement.childNodes);
					body.replaceWith(bq);
				});
	*/

			[...tmpl.content.querySelectorAll('*')].forEach(oElement => {
				const name = oElement.tagName,
					oStyle = oElement.style;

				if ('STYLE' === name) {
					let css = msgId ? parseCSS(oElement.textContent) : [];
					if (css.length) {
						css.applyNamespace(msgId);
						css = css.toString();
						if (SettingsUserStore.removeColors()) {
							css = css.replace(/(background-)?color:[^};]+;?/g, '');
						}
						oElement.textContent = css;
					} else {
						oElement.remove();
					}
					return;
				}

				if ('XMP' === name) {
					const pre = createElement('pre');
					pre.innerHTML = encodeHtml(oElement.innerHTML);
					oElement.replaceWith(pre);
					return;
				}

				// \MailSo\Base\HtmlUtils::ClearTags()
				if ('none' == oStyle.display
				 || 'hidden' == oStyle.visibility
	//			 || (oStyle.lineHeight && 1 > parseFloat(oStyle.lineHeight)
	//			 || (oStyle.maxHeight && 1 > parseFloat(oStyle.maxHeight)
	//			 || (oStyle.maxWidth && 1 > parseFloat(oStyle.maxWidth)
	//			 || ('0' === oStyle.opacity
				) {
					oElement.remove();
					return;
				}

				const className = oElement.className,
					hasAttribute = name => oElement.hasAttribute(name),
					getAttribute = name => hasAttribute(name) ? oElement.getAttribute(name).trim() : '',
					setAttribute = (name, value) => oElement.setAttribute(name, value),
					delAttribute = name => {
						let value = getAttribute(name);
						oElement.removeAttribute(name);
						return value;
					};

				if ('mail-body' === className) {
					forEachObjectEntry(tasks, (name, cb) =>
						hasAttribute(name) && cb(delAttribute(name), oElement)
					);
				} else if (msgId && className) {
					oElement.className = className.replace(/(^|\s+)/g, '$1msg-');
				}

				if (oElement.hasAttributes()) {
					let i = oElement.attributes.length;
					while (i--) {
						let sAttrName = oElement.attributes[i].name.toLowerCase();
						if (!allowedAttributes.includes(sAttrName) && ('class' !== sAttrName || 'mail-body' !== className)) {
							delAttribute(sAttrName);
						}
					}
				}

				let value;

	//			if ('TABLE' === name || 'TD' === name || 'TH' === name) {
				if (!oStyle.backgroundImage) {
					if ('TD' !== name && 'TH' !== name) {
						['width','height'].forEach(key => {
							if (hasAttribute(key)) {
								value = delAttribute(key);
								oStyle[key] || (oStyle[key] = value.includes('%') ? value : value + 'px');
							}
						});
						// Make width responsive
						value = oStyle.width;
						if (100 < parseInt(value,10) && !oStyle.maxWidth) {
							oStyle.maxWidth = value;
							oStyle.width = '100%';
						}
						// Make height responsive
						value = oStyle.removeProperty('height');
						if (value && !oStyle.maxHeight) {
							oStyle.maxHeight = value;
						}
					}
				}
	//			} else
				if ('A' === name) {
					value = oElement.href;
					if (!/^([a-z]+):/i.test(value)) {
						setAttribute('data-x-href-broken', value);
						delAttribute('href');
					} else {
						oElement.href = stripTracking(value);
						if (oElement.href != value) {
							result.tracking = true;
							setAttribute('data-x-href-tracking', value);
						}
						setAttribute('target', '_blank');
	//					setAttribute('rel', 'external nofollow noopener noreferrer');
					}
					setAttribute('tabindex', '-1');
					aColor && !oElement.style.color && (oElement.style.color = aColor);
				}

	//			if (['CENTER','FORM'].includes(name)) {
				if (nonEmptyTags.includes(name) && ('' == oElement.textContent.trim())) {
					('A' !== name || !oElement.querySelector('IMG')) && replaceWithChildren(oElement);
					return;
				}

				// SVG xlink:href
				/*
				if (hasAttribute('xlink:href')) {
					delAttribute('xlink:href');
				}
				*/

				let skipStyle = false;
				if (isMsg) {
					value = isMsg && delAttribute('src');
					if (value) {
						if ('IMG' === name) {
							oElement.loading = 'lazy';
							let attachment;
							if (value.startsWith('cid:'))
							{
								value = value.slice(4);
								setAttribute('data-x-src-cid', value);
								attachment = findAttachmentByCid(value);
								if (attachment?.download) {
									oElement.src = attachment.linkPreview();
									oElement.title += ' ('+attachment.fileName+')';
									attachment.isInline(true);
									attachment.isLinked(true);
								}
							}
							else if ((attachment = findLocationByCid(value)))
							{
								if (attachment.download) {
									oElement.src = attachment.linkPreview();
									attachment.isLinked(true);
								}
							}
							else if (((oStyle.maxHeight && 3 > pInt(oStyle.maxHeight)) // TODO: issue with 'in'
									|| (oStyle.maxWidth && 3 > pInt(oStyle.maxWidth)) // TODO: issue with 'in'
									|| (oStyle.width && 2 > pInt(oStyle.width))
									|| [
										'email.microsoftemail.com/open',
										'github.com/notifications/beacon/',
										'/track/open', // mandrillapp.com list-manage.com
										'google-analytics.com'
									].filter(uri => value.toLowerCase().includes(uri)).length
							)) {
								skipStyle = true;
								oStyle.display = 'none';
		//						setAttribute('style', 'display:none');
								setAttribute('data-x-src-hidden', value);
		//						result.tracking = true;
							}
							else if (httpre.test(value))
							{
								let src = stripTracking(value);
								if (src != value) {
									result.tracking = true;
									setAttribute('data-x-src-tracking', value);
								}
								setAttribute('data-x-src', src);
								result.hasExternals = true;
								oElement.alt || (oElement.alt = src.replace(/^.+\/([^/?]+).*$/, '$1').slice(-20));
							}
							else if (value.startsWith('data:image/'))
							{
								oElement.src = value;
							}
							else
							{
								setAttribute('data-x-src-broken', value);
							}
						}
						else
						{
							setAttribute('data-x-src-broken', value);
						}
					}
				}

				if (hasAttribute('background')) {
					oStyle.backgroundImage = 'url("' + delAttribute('background') + '")';
				}

				if (hasAttribute('bgcolor')) {
					oStyle.backgroundColor = delAttribute('bgcolor');
				}

				if (hasAttribute('color')) {
					oStyle.color = delAttribute('color');
				}

				if (!skipStyle) {
	/*
					if ('fixed' === oStyle.position) {
						oStyle.position = 'absolute';
					}
	*/
					oStyle.removeProperty('behavior');
					oStyle.removeProperty('cursor');
					oStyle.removeProperty('min-width');

					const
						urls_remote = [], // 'data-x-style-url'
						urls_broken = []; // 'data-x-broken-style-src'
					['backgroundImage', 'listStyleImage', 'content'].forEach(property => {
						if (oStyle[property]) {
							let value = oStyle[property],
								found = value.match(/url\s*\(([^)]+)\)/i);
							if (found) {
								oStyle[property] = null;
								found = found[1].replace(/^["'\s]+|["'\s]+$/g, '');
								let lowerUrl = found.toLowerCase();
								if (lowerUrl.startsWith('cid:')) {
									const attachment = findAttachmentByCid(found);
									if (attachment?.linkPreview && name) {
										oStyle[property] = "url('" + attachment.linkPreview() + "')";
										attachment.isInline(true);
										attachment.isLinked(true);
									}
								} else if (httpre.test(lowerUrl)) {
									result.hasExternals = true;
									urls_remote.push([property, found]);
								} else if (lowerUrl.startsWith('data:image/')) {
									oStyle[property] = value;
								} else {
									urls_broken.push([property, found]);
								}
							}
						}
					});
	//				oStyle.removeProperty('background-image');
	//				oStyle.removeProperty('list-style-image');

					if (urls_remote.length) {
						setAttribute('data-x-style-url', JSON.stringify(urls_remote));
					}
					if (urls_broken.length) {
						setAttribute('data-x-style-broken-urls', JSON.stringify(urls_broken));
					}
	/*
					// https://github.com/the-djmaze/snappymail/issues/1082
					if (11 > pInt(oStyle.fontSize)) {
						oStyle.removeProperty('font-size');
					}
	*/
					// Removes background and color
					// Many e-mails incorrectly only define one, not both
					// And in dark theme mode this kills the readability
					if (SettingsUserStore.removeColors()) {
						oStyle.removeProperty('background-color');
						oStyle.removeProperty('background-image');
						oStyle.removeProperty('color');
					}

					oStyle.cssText && (oStyle.cssText = cleanCSS(oStyle.cssText));
				}
			});

			isMsg && blockquoteSwitcher();

	//		return tmpl.content.firstChild;
			result.html = tmpl.innerHTML.trim();
			return result;
		},

		/**
		 * @param {string} html
		 * @returns {string}
		 */
		htmlToPlain = html => {
			if (SettingsUserStore.markdown()) {
				return htmlToMarkdown(html);
			}
			const
				hr = '⎯'.repeat(64),
				forEach = (selector, fn) => tmpl.content.querySelectorAll(selector).forEach(fn),
				blockquotes = node => {
					let bq;
					while ((bq = node.querySelector('blockquote'))) {
						// Convert child blockquote first
						blockquotes(bq);
						// Convert blockquote
	//					bq.innerHTML = '\n' + ('\n' + bq.innerHTML.replace(/\n{3,}/gm, '\n\n').trim() + '\n').replace(/^/gm, '&gt; ');
	//					replaceWithChildren(bq);
						bq.replaceWith(
							'\n' + ('\n' + bq.textContent.replace(/\n{3,}/g, '\n\n').trim() + '\n').replace(/^/gm, '> ')
						);
					}
				};

			html = html
				.replace(/<pre[^>]*>([\s\S]*?)<\/pre>/gim, (...args) =>
					1 < args.length ? args[1].toString().replace(/\n/g, '<br>') : '')
				// Remove line duplication
				.replace(/<br><\/div>/gi, '</div>')
				.replace(/\r?\n/g, '')
				.replace(/\s+/gm, ' ');

			while (/<(div|tr)[\s>]/i.test(html)) {
				html = html.replace(/\n*<(div|tr)(\s[\s\S]*?)?>\n*/gi, '\n');
			}
			while (/<\/(div|tr)[\s>]/i.test(html)) {
				html = html.replace(/\n*<\/(div|tr)(\s[\s\S]*?)?>\n*/gi, '\n');
			}

			tmpl.innerHTML = html
				.replace(/<t[dh](\s[\s\S]*?)?>/gi, '\t')
				.replace(/<\/tr(\s[\s\S]*?)?>/gi, '\n');

			forEach('style', node => node.remove());

			// lines
			forEach('hr', node => node.replaceWith(`\n\n${hr}\n\n`));

			// headings
			forEach('h1,h2,h3,h4,h5,h6', h => h.replaceWith(`\n\n${'#'.repeat(h.tagName[1])} ${h.textContent}\n\n`));

			// paragraphs
			forEach('p', node => {
				node.prepend('\n\n');
				if ('' == node.textContent.trim()) {
					node.remove();
				} else {
					node.after('\n\n');
				}
			});

			// proper indenting and numbering of (un)ordered lists
			forEach('ol,ul', node => {
				let prefix = '',
					parent = node,
					ordered = 'OL' == node.tagName,
					i = 0;
				while ((parent = parent?.parentNode?.closest?.('ol,ul'))) {
					prefix = '    ' + prefix;
				}
				node.querySelectorAll(':scope > li').forEach(li => {
					li.prepend('\n' + prefix + (ordered ? `${++i}. ` : ' * '));
				});
				node.prepend('\n\n');
				node.after('\n\n');
			});

			// Convert anchors
			forEach('a', a => {
				let txt = a.textContent, href = a.href;
				return a.replaceWith(
					txt.replace(/[\s()-]+/g, '').includes(href.replace(/^[a-z]:/, '').replace(/[\s()-]+/g, ''))
					? txt
					: txt + ' ' + href + ' '
				);
			});

			// Bold
			forEach('b,strong', b => b.replaceWith(`**${b.textContent}**`));
			// Italic
			forEach('i,em', i => i.replaceWith(`*${i.textContent}*`));

			// Convert line-breaks
			tmpl.innerHTML = tmpl.innerHTML
				.replace(/\n{3,}/gm, '\n\n')
				.replace(/\n<br[^>]*>/g, '\n')
				.replace(/<br[^>]*>\n/g, '\n');
			forEach('br', br => br.replaceWith('\n'));

			// Blockquotes must be last
			blockquotes(tmpl.content);

			return (tmpl.content.textContent || '').trim();
		},

		htmlToMarkdown = html => {
			tmpl.innerHTML = html;
			return turndown.turndown(tmpl.content);
		},

		/**
		 * @param {string} plain
		 * @param {boolean} findEmailAndLinksInText = false
		 * @returns {string}
		 */
		plainToHtml = plain => {
			plain = plain.toString()
				.replace(/\r/g, '')
				.replace(/^>[> ]>+/gm, ([match]) => (match ? match.replace(/[ ]+/g, '') : match))
				// https://github.com/the-djmaze/snappymail/issues/900
				.replace(/\u2028/g,' ');

			let bIn = false,
				bDo = true,
				bStart = true,
				aNextText = [],
				aText = plain.split('\n');

			do {
				bDo = false;
				aNextText = [];
				aText.forEach(sLine => {
					bStart = '>' === sLine.slice(0, 1);
					if (bStart && !bIn) {
						bDo = true;
						bIn = true;
						aNextText.push('~~~blockquote~~~');
						aNextText.push(sLine.slice(1));
					} else if (!bStart && bIn) {
						if (sLine) {
							bIn = false;
							aNextText.push('~~~/blockquote~~~');
							aNextText.push(sLine);
						} else {
							aNextText.push(sLine);
						}
					} else if (bStart && bIn) {
						aNextText.push(sLine.slice(1));
					} else {
						aNextText.push(sLine);
					}
				});

				if (bIn) {
					bIn = false;
					aNextText.push('~~~/blockquote~~~');
				}

				aText = aNextText;
			} while (bDo);

			tmpl.innerHTML = aText.join('\n')
				// .replace(/~~~\/blockquote~~~\n~~~blockquote~~~/g, '\n')
				.replace(/&/g, '&amp;')
				.replace(/>/g, '&gt;')
				.replace(/</g, '&lt;')
				.replace(urlRegExp, (...m) => {
					m[0] = stripTracking(m[0]);
					return `<a href="${m[0]}" target="_blank">${m[0]}</a>`;
				})
				.replace(email, '$1<a href="mailto:$2">$2</a>')
				.replace(tel, '<a href="$1">$1</a>')
				.replace(/~~~blockquote~~~\s*/g, '<blockquote>')
				.replace(/\s*~~~\/blockquote~~~/g, '</blockquote>')
				.replace(/\n/g, '<br>');
			blockquoteSwitcher();
			return tmpl.innerHTML.trim();
		};

	rl.Utils = {
		cleanHtml: cleanHtml,
		htmlToPlain: htmlToPlain,
		plainToHtml: plainToHtml,
		htmlToMarkdown: htmlToMarkdown
	//	markdownToHtml: md => marked.parse(md)
	};

	function typeCast(curValue, newValue) {
		if (null != curValue) {
			switch (typeof curValue)
			{
			case 'boolean':
				return 0 != newValue && !!newValue;
			case 'number':
				newValue = parseFloat(newValue);
				return isFinite(newValue) ? newValue : 0;
			case 'string':
				return null != newValue ? '' + newValue : '';
			case 'object':
				if (curValue.constructor.reviveFromJson) {
					return curValue.constructor.reviveFromJson(newValue);
				}
				if (isArray(curValue) && !isArray(newValue))
					return [];
			}
		}
		return newValue;
	}

	class AbstractModel {
		constructor() {
	/*
			if (new.target === AbstractModel) {
				throw Error("Can't instantiate AbstractModel!");
			}
	*/
			Object.defineProperty(this, 'disposables', {value: []});
		}

		addObservables(observables) {
			addObservablesTo(this, observables);
		}

		addComputables(computables) {
			addComputablesTo(this, computables);
		}

		addSubscribables(subscribables) {
	//		addSubscribablesTo(this, subscribables);
			forEachObjectEntry(subscribables, (key, fn) => this.disposables.push( this[key].subscribe(fn) ) );
		}

		/** Called by delegateRunOnDestroy */
		onDestroy() {
			/** dispose ko subscribables */
			this.disposables.forEach(dispose);
			/** clear object entries */
	//		forEachObjectEntry(this, (key, value) => {
			forEachObjectValue(this, value => {
				/** clear CollectionModel */
				(ko.isObservableArray(value) ? value() : value)?.onDestroy?.();
				/** destroy ko.observable/ko.computed? */
	//			dispose(value);
				/** clear object value */
	//			this[key] = null; // TODO: issue with Contacts view
			});
	//		this.disposables = [];
		}

		/**
		 * @static
		 * @param {FetchJson} json
		 * @returns {boolean}
		 */
		static validJson(json) {
			return !!(json && ('Object/'+this.name.replace('Model', '') === json['@Object']));
		}

		/**
		 * @static
		 * @param {FetchJson} json
		 * @returns {*Model}
		 */
		static reviveFromJson(json) {
			let obj = this.validJson(json) ? new this() : null;
			obj?.revivePropertiesFromJson(json);
			return obj;
		}

		revivePropertiesFromJson(json) {
			const model = this.constructor,
				valid = model.validJson(json);
			valid && forEachObjectEntry(json, (key, value) => {
				if ('@' !== key[0]) try {
	//				key = key[0].toLowerCase() + key.slice(1);
					switch (typeof this[key])
					{
					case 'function':
						if (ko.isObservable(this[key])) {
							this[key](typeCast(this[key](), value));
	//						console.log('Observable ' + (typeof this[key]()) + ' ' + (model.name) + '.' + key + ' revived');
						}
	//					else console.log(model.name + '.' + key + ' is a function');
						break;
					case 'boolean':
					case 'number':
					case 'object':
					case 'string':
						this[key] = typeCast(this[key], value);
						break;
					case 'undefined':
						console.log(`Undefined ${model.name}.${key} set`);
						this[key] = value;
						break;
	//				default:
	//					console.log((typeof this[key])+` ${model.name}.${key} not revived`);
	//					console.log((typeof this[key])+' '+(model.name)+'.'+key+' not revived');
					}
				} catch (e) {
					console.log(model.name + '.' + key);
					console.error(e);
				}
			});
			return valid;
		}

	}

	class EmailModel extends AbstractModel {
		/**
		 * @param {string=} email = ''
		 * @param {string=} name = ''
		 * @param {string=} dkimStatus = 'none'
		 */
		constructor(email, name, dkimStatus = 'none') {
			super();
			this.email = email || '';
			this.name = name || '';
			this.dkimStatus = dkimStatus;
			this.cleanup();
		}

		/**
		 * @static
		 * @param {FetchJsonEmail} json
		 * @returns {?EmailModel}
		 */
		static reviveFromJson(json) {
			const email = super.reviveFromJson(json);
			email?.cleanup();
			return email?.valid() ? email : null;
		}

		/**
		 * @returns {boolean}
		 */
		valid() {
			return this.name || this.email;
		}

		/**
		 * @returns {void}
		 */
		cleanup() {
			if (this.name === this.email) {
				this.name = '';
			}
		}

		/**
		 * @param {boolean} friendlyView = false
		 * @param {boolean} wrapWithLink = false
		 * @returns {string}
		 */
		toLine(friendlyView, wrapWithLink) {
			let name = this.name,
				result = this.email,
				toLink = text =>
					'<a href="mailto:'
					+ encodeHtml(result) + (name ? '?to=' + encodeURIComponent('"' + name + '" <' + result + '>') : '')
					+ '" target="_blank" tabindex="-1">'
					+ encodeHtml(text || result)
					+ '</a>';
			if (result) {
				if (name) {
					result = friendlyView
						? (wrapWithLink ? toLink(name) : name)
						: (wrapWithLink
							? encodeHtml('"' + name + '" <') + toLink() + encodeHtml('>')
							: '"' + name + '" <' + result + '>'
						);
				} else if (wrapWithLink) {
					result = toLink();
				}
			}
			return result || name;
		}
	}

	const
		QPDecodeParams = [/=([0-9A-F]{2})/g, (...args) => String.fromCharCode(parseInt(args[1], 16))];

	const
		// https://datatracker.ietf.org/doc/html/rfc2045#section-6.8
		BDecode = atob,

		// unescape(encodeURIComponent()) makes the UTF-16 DOMString to an UTF-8 string
		BEncode = data => btoa(unescape(encodeURIComponent(data))),
	/* 	// Without deprecated 'unescape':
		BEncode = data => btoa(encodeURIComponent(data).replace(
			/%([0-9A-F]{2})/g, (match, p1) => String.fromCharCode('0x' + p1)
		)),
	*/

		// https://datatracker.ietf.org/doc/html/rfc2045#section-6.7
		QPDecode = data => data.replace(/=\r?\n/g, '').replace(...QPDecodeParams),

		// https://datatracker.ietf.org/doc/html/rfc2047#section-4.1
		// https://datatracker.ietf.org/doc/html/rfc2047#section-4.2
		// encoded-word = "=?" charset "?" encoding "?" encoded-text "?="
		decodeEncodedWords = data =>
			data.replace(/=\?([^?]+)\?(B|Q)\?(.+?)\?=/g, (m, charset, encoding, text) =>
				decodeText(charset, 'B' == encoding ? BDecode(text) : QPDecode(text))
			)
		,

		decodeText = (charset, data) => {
			try {
				// https://developer.mozilla.org/en-US/docs/Web/API/Encoding_API/Encodings
				return new TextDecoder(charset).decode(Uint8Array.from(data, c => c.charCodeAt(0)));
			} catch (e) {
				console.error({charset:charset,error:e});
			}
		};

	/**
	 * Parses structured e-mail addresses from an address/mailbox(-list) field
	 * https://datatracker.ietf.org/doc/html/rfc2822#section-3.4
	 *
	 * Example:
	 *
	 *    "Name <address@domain>"
	 *
	 * will be converted to
	 *
	 *     [{name: "Name", email: "address@domain"}]
	 *
	 * @param {String} str Address field
	 * @return {Array} An array of address objects
	 */
	function addressparser(str) {
		str = (str || '').toString();

		let
			endOperator = '',
			node = {
				type: 'text',
				value: ''
			},
			escaped = false,
			address = [],
			addresses = [];

		const
			/*
			 * Operator tokens and which tokens are expected to end the sequence
			 */
			OPERATORS = {
			  '"': '"',
			  '(': ')',
			  '<': '>',
			  ',': '',
			  // Groups are ended by semicolons
			  ':': ';',
			  // Semicolons are not a legal delimiter per the RFC2822 grammar other
			  // than for terminating a group, but they are also not valid for any
			  // other use in this context.  Given that some mail clients have
			  // historically allowed the semicolon as a delimiter equivalent to the
			  // comma in their UI, it makes sense to treat them the same as a comma
			  // when used outside of a group.
			  ';': ''
			},
			pushToken = token => {
				token.value = (token.value || '').toString().trim();
				token.value.length && address.push(token);
				node = {
					type: 'text',
					value: ''
				},
				escaped = false;
			},
			pushAddress = () => {
				if (address.length) {
					address = _handleAddress(address);
					if (address.length) {
						addresses = addresses.concat(address);
					}
				}
				address = [];
			};

		[...str].forEach(chr => {
			if (!escaped && (chr === endOperator || (!endOperator && chr in OPERATORS))) {
				pushToken(node);
				if (',' === chr || ';' === chr) {
					pushAddress();
				} else {
					endOperator = endOperator ? '' : OPERATORS[chr];
					if ('<' === chr) {
						node.type = 'email';
					} else if ('(' === chr) {
						node.type = 'comment';
					} else if (':' === chr) {
						node.type = 'group';
					}
				}
			} else {
				node.value += chr;
				escaped = !escaped && '\\' === chr;
			}
		});
		pushToken(node);

		pushAddress();

		return addresses;
	}

	/**
	 * Converts tokens for a single address into an address object
	 *
	 * @param {Array} tokens Tokens object
	 * @return {Object} Address object
	 */
	function _handleAddress(tokens) {
		let
			isGroup = false,
			address = {},
			addresses = [],
			data = {
				email: [],
				comment: [],
				group: [],
				text: []
			};

		tokens.forEach(token => {
			isGroup = isGroup || 'group' === token.type;
			data[token.type].push(token.value);
		});

		// If there is no text but a comment, replace the two
		if (!data.text.length && data.comment.length) {
			data.text = data.comment;
			data.comment = [];
		}

		if (isGroup) {
			// http://tools.ietf.org/html/rfc2822#appendix-A.1.3
	/*
			addresses.push({
				email: '',
				name: data.text.join(' ').trim(),
				group: addressparser(data.group.join(','))
	//			,comment: data.comment.join(' ').trim()
			});
	*/
			addresses = addresses.concat(addressparser(data.group.join(',')));
		} else {
			// If no address was found, try to detect one from regular text
			if (!data.email.length && data.text.length) {
				var i = data.text.length;
				while (i--) {
					if (data.text[i].match(/^[^@\s]+@[^@\s]+$/)) {
						data.email = data.text.splice(i, 1);
						break;
					}
				}

				// still no address
				if (!data.email.length) {
					i = data.text.length;
					while (i--) {
						data.text[i] = data.text[i].replace(/\s*\b[^@\s]+@[^@\s]+\b\s*/, address => {
							if (!data.email.length) {
								data.email = [address.trim()];
								return '';
							}
							return address.trim();
						});
						if (data.email.length) {
							break;
						}
					}
				}
			}

			// If there's still no text but a comment exists, replace the two
			if (!data.text.length && data.comment.length) {
				data.text = data.comment;
				data.comment = [];
			}

			// Keep only the first address occurence, push others to regular text
			if (data.email.length > 1) {
				data.text = data.text.concat(data.email.splice(1));
			}

			address = {
				// Join values with spaces
				email: decodeEncodedWords(data.email.join(' ').trim()),
				name: decodeEncodedWords(data.text.join(' ').trim())
	//			,comment: data.comment.join(' ').trim()
			};

			if (address.email === address.name) {
				if (address.email.includes('@')) {
					address.name = '';
				} else {
					address.email = '';
				}
			}

	//		address.email = address.email.replace(/^[<]+(.*)[>]+$/g, '$1');

			addresses.push(address);
		}

		return addresses;
	}

	const contentType = 'snappymail/emailaddress',
		getAddressKey = li => li?.emailaddress?.key,

		parseEmailLine = line => addressparser(line).map(item =>
				(item.name || item.email)
					? new EmailModel(item.email, item.name) : null
			).filter(v => v),
		splitEmailLine = line => {
			const result = [];
			let exists = false;
			addressparser(line).forEach(item => {
				const address = (item.name || item.email)
					? new EmailModel(item.email, item.name)
					: null;

				if (address?.email) {
					exists = true;
				}

				result.push(address ? address.toLine() : item.name);
			});
			return exists ? result : null;
		};

	let dragAddress, datalist;

	// mailbox-list
	class EmailAddressesComponent {

		constructor(element, options) {

			if (!datalist) {
				datalist = createElement('datalist',{id:"emailaddresses-datalist"});
				doc.body.append(datalist);
			}

			const self = this,
				input = createElement('input',{type:"text", list:datalist.id,
					autocomplete:"off", autocorrect:"off", autocapitalize:"off"}),
				// In Chrome we have no access to dataTransfer.getData unless it's the 'drop' event
				// In Chrome Mobile dataTransfer.types.includes(contentType) fails, only text/plain is set
				validDropzone = () => dragAddress?.li.parentNode !== self.ul,
				fnDrag = e => validDropzone() && e.preventDefault();

			self.element = element;

			self.options = Object.assign({

				focusCallback : null,

				// simply passing an autoComplete source (array, string or function) will instantiate autocomplete functionality
				autoCompleteSource : '',

				onChange : null
			}, options);

			self._chosenValues = [];

			self._lastEdit = '';

			// Create the elements
			self.ul = createElement('ul',{class:"emailaddresses"});

			addEventsListeners(self.ul, {
				click: e => self._focus(e),
				dblclick: e => self._editTag(e),
				dragenter: fnDrag,
				dragover: fnDrag,
				drop: e => {
					if (validDropzone() && dragAddress.value) {
						e.preventDefault();
						dragAddress.source._removeDraggedTag(dragAddress.li);
						self._parseValue(dragAddress.value);
					}
				}
			});

			self.input = input;

			addEventsListeners(input, {
				focus: () => {
					self._focusTrigger(true);
					input.value || self._resetDatalist();
				},
				blur: () => {
					// prevent autoComplete menu click from causing a false 'blur'
					self._parseInput(true);
					self._focusTrigger(false);
				},
				keydown: e => {
					if ('Backspace' === e.key || 'ArrowLeft' === e.key) {
						// if our input contains no value and backspace has been pressed, select the last tag
						var lastTag = self.inputCont.previousElementSibling;
						if (lastTag && (!input.value
							|| (('selectionStart' in input) && input.selectionStart === 0 && input.selectionEnd === 0))
						) {
							e.preventDefault();
							lastTag.querySelector('a').focus();
						}
						self._updateDatalist();
					} else if (e.key == 'Enter') {
						e.preventDefault();
						self._parseInput(true);
					}
				},
				input: () => {
					self._parseInput();
					self._updateDatalist();
				}
			});

			// define starting placeholder
			if (element.placeholder) {
				input.placeholder = element.placeholder;
			}

			self.inputCont = createElement('li',{class:"emailaddresses-input"});
			self.inputCont.append(input);
			self.ul.append(self.inputCont);

			element.replaceWith(self.ul);

			// if instantiated input already contains a value, parse that junk
			if (element.value.trim()) {
				self._parseValue(element.value);
			}

			self._updateDatalist = self.options.autoCompleteSource
				? (() => {
					let value = input.value.trim();
					if (datalist.inputValue !== value) {
						datalist.inputValue = value;
						value.length && self.options.autoCompleteSource(
							value,
							items => {
								self._resetDatalist();
								let chars = value.length;
								items?.forEach(item => {
									datalist.append(new Option(item));
									chars = Math.max(chars, item.length);
								});
								// https://github.com/the-djmaze/snappymail/issues/368 and #513
								chars *= 8;
								if (input.clientWidth < chars) {
									input.style.width = chars + 'px';
								}
							}
						);
					}
				}).throttle(500)
				: () => 0;
		}

		_focusTrigger(bValue) {
			this.ul.classList.toggle('emailaddresses-focused', bValue);
			this.options.focusCallback(bValue);
		}

		_resetDatalist() {
			datalist.textContent = '';
		}

		_parseInput(force) {
			let val = this.input.value;
			if ((force || val.includes(',') || val.includes(';')
					|| (val.charAt(val.length-1)===' ' && this._simpleEmailMatch(val)))
				&& this._parseValue(val)) {
				this.input.value = '';
			}
			this._resizeInput();
		}

		_parseValue(val) {
			if (val) {
				const self = this,
					v = val.trim(),
					hook = (v && [',', ';', '\n'].includes(v.slice(-1))) ? splitEmailLine(val) : null,
					values = (hook || [val]).map(value => parseEmailLine(value))
							.flat(Infinity)
							.map(item => (item.toLine ? [item.toLine(), item] : [item, null]));

				if (values.length) {
					values.forEach(a => {
						var v = a[0].trim(),
							exists = false,
							lastIndex = -1,
							obj = {
								key : '',
								obj : null,
								value : ''
							};

						self._chosenValues.forEach((vv, kk) => {
							if (vv.value === self._lastEdit) {
								lastIndex = kk;
							}

							exists |= vv.value === v;
						});

						if (v !== '' && a[1] && !exists) {

							obj.key = 'mi_' + Math.random().toString( 16 ).slice( 2, 10 );
							obj.value = v;
							obj.obj = a[1];

							if (-1 < lastIndex) {
								self._chosenValues.splice(lastIndex, 0, obj);
							} else {
								self._chosenValues.push(obj);
							}

							self._lastEdit = '';
							self._renderTags();
						}
					});

					if (1 === values.length && '' === values[0] && '' !== self._lastEdit) {
						self._lastEdit = '';
						self._renderTags();
					}

					self._setValue(self._buildValue());

					return true;
				}
			}
		}

		// the input dynamically resizes based on the length of its value
		_resizeInput() {
			let input = this.input;
			if (input.clientWidth < input.scrollWidth) {
				input.style.width = (input.scrollWidth + 20) + 'px';
			}
		}

		_editTag(ev) {
			var li = ev.target.closest('li'),
				tagKey = getAddressKey(li);

			if (!tagKey) {
				return true;
			}

			var self = this,
				tagName = '',
				oPrev = null,
				next = false
			;

			self._chosenValues.forEach(v => {
				if (v.key === tagKey) {
					tagName = v.value;
					next = true;
				} else if (next && !oPrev) {
					oPrev = v;
				}
			});

			if (oPrev)
			{
				self._lastEdit = oPrev.value;
			}

			li.after(self.inputCont);

			self.input.value = tagName;
			setTimeout(() => self.input.select(), 100);

			self._removeTag(ev, li);
			self._resizeInput(ev);
		}

		_buildValue() {
			return this._chosenValues.map(v => v.value).join(',');
		}

		_setValue(value) {
			if (this.element.value !== value) {
				this.element.value = value;
				this.options.onChange(value);
			}
		}

		_simpleEmailMatch(value) {
			// A very SIMPLE test to check if the value might be an email
			const val = value.trim();
			return /^[^@]*<[^\s@]{1,128}@[^\s@]{1,256}\.[\w]{2,32}>$/g.test(val)
				|| /^[^\s@]{1,128}@[^\s@]{1,256}\.[\w]{2,32}$/g.test(val);
		}

		_renderTags() {
			let self = this;
			[...self.ul.children].forEach(node => node !== self.inputCont && node.remove());

			self._chosenValues.forEach(v => {
				if (v.obj) {
					let li = createElement('li',{title:v.obj.toLine(),draggable:'true'}),
						el = createElement('span');
					el.append(v.obj.toLine(true));
					li.append(el);

					el = createElement('a',{href:'#', class:'ficon'});
					el.append('✖');
					addEventsListeners(el, {
						click: e => self._removeTag(e, li),
						focus: () => li.className = 'emailaddresses-selected',
						blur: () => li.className = null,
						keydown: e => {
							switch (e.key) {
								case 'Delete':
								case 'Backspace':
									self._removeTag(e, li);
									break;

								// 'e' - edit tag (removes tag and places value into visible input
								case 'e':
								case 'Enter':
									self._editTag(e);
									break;

								case 'ArrowLeft':
									// select the previous tag or input if no more tags exist
									var previous = el.closest('li').previousElementSibling;
									if (previous.matches('li')) {
										previous.querySelector('a').focus();
									} else {
										self.focus();
									}
									break;

								case 'ArrowRight':
									// select the next tag or input if no more tags exist
									var next = el.closest('li').nextElementSibling;
									if (next !== this.inputCont) {
										next.querySelector('a').focus();
									} else {
										this.focus();
									}
									break;

								case 'ArrowDown':
									self._focus(e);
									break;
							}
						}
					});
					li.append(el);

					li.emailaddress = v;

					addEventsListeners(li, {
						dragstart: e => {
							dragAddress = {
								source: self,
								li: li,
								value: li.emailaddress.obj.toLine()
							};
	//						e.dataTransfer.setData(contentType, li.emailaddress.obj.toLine());
							e.dataTransfer.setData('text/plain', contentType);
	//						e.dataTransfer.setDragImage(li, 0, 0);
							e.dataTransfer.effectAllowed = 'move';
							li.style.opacity = 0.25;
						},
						dragend: () => {
							dragAddress = null;
							li.style.cssText = '';
						}
					});

					self.inputCont.before(li);
				}
			});
		}

		_removeTag(ev, li) {
			ev.preventDefault();

			var key = getAddressKey(li),
				self = this,
				indexFound = self._chosenValues.findIndex(v => key === v.key);

			indexFound > -1 && self._chosenValues.splice(indexFound, 1);

			self._setValue(self._buildValue());

			li.remove();
			setTimeout(() => self.input.focus(), 100);
		}

		_removeDraggedTag(li) {
			var
				key = getAddressKey(li),
				self = this,
				indexFound = self._chosenValues.findIndex(v => key === v.key)
			;
			if (-1 < indexFound) {
				self._chosenValues.splice(indexFound, 1);
				self._setValue(self._buildValue());
			}

			li.remove();
		}

		focus () {
			this.input.focus();
		}

		blur() {
			this.input.blur();
		}

		_focus(ev) {
			var li = ev.target.closest('li');
			if (getAddressKey(li)) {
				li.querySelector('a').focus();
			} else {
				this.focus();
			}
		}

		set value(value) {
			var self = this;
			if (self.element.value !== value) {
	//			self.input.value = '';
	//			self._resizeInput();
				self._chosenValues = [];
				self._renderTags();
				self._parseValue(self.element.value = value);
			}
		}
	}

	let FOLDERS_CACHE = new Map,
		FOLDERS_HASH_MAP = new Map,
		inboxFolderName = 'INBOX';

	const
		/**
		 * @returns {void}
		 */
		clearCache = () => {
			FOLDERS_CACHE.clear();
			FOLDERS_HASH_MAP.clear();
		},

		/**
		 * @returns {string}
		 */
		getFolderInboxName = () => inboxFolderName,

		/**
		 * @returns {string}
		 */
		setFolderInboxName = name => inboxFolderName = name,

		/**
		 * @param {string} fullNameHash
		 * @returns {string}
		 */
		getFolderFromHashMap = fullNameHash => getFolderFromCacheList(FOLDERS_HASH_MAP.get(fullNameHash)),

		/**
		 * @param {?FolderModel} folder
		 */
		setFolder = folder => {
			folder.etag = '';
			FOLDERS_CACHE.set(folder.fullName, folder);
			FOLDERS_HASH_MAP.set(folder.fullNameHash, folder.fullName);
		},

		/**
		 * @param {string} folderFullName
		 * @param {string} folderETag
		 */
		setFolderETag = (folderFullName, folderETag) =>
			FOLDERS_CACHE.has(folderFullName) && (FOLDERS_CACHE.get(folderFullName).etag = folderETag),

		/**
		 * @param {string} folderFullName
		 * @returns {?FolderModel}
		 */
		getFolderFromCacheList = folderFullName =>
			FOLDERS_CACHE.get(folderFullName),

		/**
		 * @param {string} folderFullName
		 */
		removeFolderFromCacheList = folderFullName => FOLDERS_CACHE.delete(folderFullName);

	const UNUSED_OPTION_VALUE = '__UNUSE__';

	//import Remote from 'Remote/User/Fetch'; // Circular dependency

	const

	ignoredKeywords = [
		// rfc5788
		'$forwarded',
		'$mdnsent',
		'$submitpending',
		'$submitted',
		// rfc9051
		'$junk',
		'$notjunk',
		'$phishing',
		// Mailo
		'sent',
		// KMail
		'$encrypted',
		'$error',
		'$ignored',
		'$invitation',
		'$queued',
		'$sent',
		'$signed',
		'$todo',
		'$watched',
		// GMail
		'$notphishing',
		'junk',
		'nonjunk',
		// KMail & GMail
		'$attachment',
		'$replied',
		// Others
		'$readreceipt',
		'$notdelivered'
	],

	isAllowedKeyword = value => '\\' != value[0] && !ignoredKeywords.includes(value.toLowerCase()),

	FolderUserStore = new class {
		constructor() {
			const self = this;
			addObservablesTo(self, {
				/**
				 * To use "checkable" option in /#/settings/folders
				 * When true, getNextFolderNames only lists system and "checkable" folders
				 * and affects the update of unseen count
				 * Auto set to true when amount of folders > folderSpecLimit to prevent requests overload,
				 * see application.ini [labs] folders_spec_limit
				 */
				displaySpecSetting: false,

				sortMode: '',

				quotaLimit: 0,
				quotaUsage: 0,

				sentFolder: '',
				draftsFolder: '',
				spamFolder: '',
				trashFolder: '',
				archiveFolder: '',

				optimized: false,
				error: '',

				foldersLoading: false,
				foldersCreating: false,
				foldersDeleting: false,
				foldersRenaming: false,

				foldersInboxUnreadCount: 0
			});

			self.namespace = '';

			self.folderList = ko.observableArray(/*new FolderCollectionModel*/);

			self.capabilities = ko.observableArray();

			self.currentFolder = ko.observable(null).extend({ toggleSubscribeProperty: [self, 'selected'] });

			addComputablesTo(self, {

				draftsFolderNotEnabled: () => !self.draftsFolder() || UNUSED_OPTION_VALUE === self.draftsFolder(),

				currentFolderFullName: () => (self.currentFolder() ? self.currentFolder().fullName : ''),
				currentFolderFullNameHash: () => (self.currentFolder() ? self.currentFolder().fullNameHash : ''),

				foldersChanging: () =>
					self.foldersLoading() | self.foldersCreating() | self.foldersDeleting() | self.foldersRenaming(),

				systemFoldersNames: () => {
					const list = [getFolderInboxName()],
					others = [self.sentFolder(), self.draftsFolder(), self.spamFolder(), self.trashFolder(), self.archiveFolder()];

					self.folderList().length &&
						others.forEach(name => name && UNUSED_OPTION_VALUE !== name && list.push(name));

					return list;
				},

				systemFolders: () =>
					self.systemFoldersNames().map(name => getFolderFromCacheList(name)).filter(v => v)
			});

			const
				subscribeRemoveSystemFolder = observable => {
					observable.subscribe(() => getFolderFromCacheList(observable())?.type(0), self, 'beforeChange');
				},
				fSetSystemFolderType = type => value => getFolderFromCacheList(value)?.type(type);

			subscribeRemoveSystemFolder(self.sentFolder);
			subscribeRemoveSystemFolder(self.draftsFolder);
			subscribeRemoveSystemFolder(self.spamFolder);
			subscribeRemoveSystemFolder(self.trashFolder);
			subscribeRemoveSystemFolder(self.archiveFolder);

			addSubscribablesTo(self, {
				sentFolder: fSetSystemFolderType(FolderType.Sent),
				draftsFolder: fSetSystemFolderType(FolderType.Drafts),
				spamFolder: fSetSystemFolderType(FolderType.Junk),
				trashFolder: fSetSystemFolderType(FolderType.Trash),
				archiveFolder: fSetSystemFolderType(FolderType.Archive)
			});

			self.quotaPercentage = koComputable(() => {
				const quota = self.quotaLimit(), usage = self.quotaUsage();
				return 0 < quota ? Math.ceil((usage / quota) * 100) : 0;
			});
		}

		/**
		 * If the IMAP server supports SORT, METADATA
		 */
		hasCapability(name) {
			return this.capabilities().includes(name);
		}

		allowKolab() {
			return FolderUserStore.hasCapability('METADATA') && SettingsCapa('Kolab');
		}

		/**
		 * @returns {Array}
		 */
		getNextFolderNames(ttl) {
			const result = [],
				limit = 10,
				utc = Date.now(),
				timeout = utc - ttl,
				timeouts = [],
				bDisplaySpecSetting = this.displaySpecSetting(),
				fSearchFunction = (list) => {
					list.forEach(folder => {
						if (
							folder?.selectable() &&
							folder.exists &&
							timeout > folder.expires &&
							(folder.isSystemFolder() || (folder.isSubscribed() && (folder.checkable() || !bDisplaySpecSetting)))
						) {
							timeouts.push([folder.expires, folder.fullName]);
						}

						if (folder?.subFolders.length) {
							fSearchFunction(folder.subFolders());
						}
					});
				};

			fSearchFunction(this.folderList());

			timeouts.sort((a, b) => (a[0] < b[0]) ? -1 : (a[0] > b[0] ? 1 : 0));

			timeouts.find(aItem => {
				const folder = getFolderFromCacheList(aItem[1]);
				if (folder) {
					folder.expires = utc;
	//				result.indexOf(aItem[1]) ||
					result.push(aItem[1]);
				}

				return limit <= result.length;
			});

			return result;
		}

		saveSystemFolders(folders) {
			folders = folders || {
				sent: FolderUserStore.sentFolder(),
				drafts: FolderUserStore.draftsFolder(),
				junk: FolderUserStore.spamFolder(),
				trash: FolderUserStore.trashFolder(),
				archive: FolderUserStore.archiveFolder()
			};
			forEachObjectEntry(folders, (k,v)=>Settings.set(k+'Folder',v));
			rl.app.Remote.request('SystemFoldersUpdate', null, folders);
		}
	};

	let notificator = null,
		player = null,
		canPlay = type => !!player?.canPlayType(type).replace('no', ''),

		audioCtx = window.AudioContext || window.webkitAudioContext,

		play = (url, name) => {
			if (player) {
				player.src = url;
				player.play();
				name = name.trim();
				fireEvent('audio.start', name.replace(/\.([a-z0-9]{3})$/, '') || 'audio');
			}
		},

		createNewObject = () => {
			try {
				const player = new Audio;
				if (player.canPlayType && player.pause && player.play) {
					player.preload = 'none';
					player.loop = false;
					player.autoplay = false;
					player.muted = false;
					return player;
				}
			} catch (e) {
				console.error(e);
			}
			return null;
		},

		// The AudioContext is not allowed to start.
		// It must be resumed (or created) after a user gesture on the page. https://goo.gl/7K7WLu
		// Setup listeners to attempt an unlock
		unlockEvents = [
			'click','dblclick',
			'contextmenu',
			'auxclick',
			'mousedown','mouseup',
			'pointerup',
			'touchstart','touchend',
			'keydown','keyup'
		],
		unlock = () => {
			unlockEvents.forEach(type => doc.removeEventListener(type, unlock, true));
			if (audioCtx) {
				console.log('AudioContext ' + audioCtx.state);
				audioCtx.resume();
			}
	//		setTimeout(()=>SMAudio.playNotification(0,1),1);
		};

	if (audioCtx) {
		audioCtx = audioCtx ? new audioCtx : null;
		audioCtx.onstatechange = unlock;
	}
	unlockEvents.forEach(type => doc.addEventListener(type, unlock, true));

	/**
	 * Browsers can't play without user interaction
	 */

	const SMAudio = new class {
		constructor() {
			player || (player = createNewObject());

			this.supported = !!player;
			this.supportedMp3 = canPlay('audio/mpeg;');
			this.supportedWav = canPlay('audio/wav; codecs="1"');
			this.supportedOgg = canPlay('audio/ogg; codecs="vorbis"');
			if (player) {
				const stopFn = () => this.pause();
				addEventsListener(player, ['ended','error'], stopFn);
				addEventListener('audio.api.stop', stopFn);
			}

			addObservablesTo(this, {
				notifications: false
			});
		}

		paused() {
			return !player || player.paused;
		}

		stop() {
			this.pause();
		}

		pause() {
			player?.pause();
			fireEvent('audio.stop');
		}

		playMp3(url, name) {
			this.supportedMp3 && play(url, name);
		}

		playOgg(url, name) {
			this.supportedOgg && play(url, name);
		}

		playWav(url, name) {
			this.supportedWav && play(url, name);
		}

		/**
		 * Used with SoundNotification setting
		 */
		playNotification(force, silent) {
			if (force || this.notifications()) {
				if ('running' == audioCtx.state && (this.supportedMp3 || this.supportedOgg)) {
					notificator = notificator || createNewObject();
					if (notificator) {
	//					SettingsGet('NotificationSound').startsWith('custom@')
						notificator.src = staticLink('sounds/'
							+ SettingsGet('NotificationSound')
							+ (this.supportedMp3 ? '.mp3' : '.ogg'));
						notificator.volume = silent ? 0.01 : 1;
						notificator.play();
					}
				} else {
					console.log('No audio: ' + audioCtx.state);
				}
			}
		}
	};

	class AbstractCollectionModel extends Array
	{
		constructor() {
	/*
			if (new.target === AbstractCollectionModel) {
				throw Error("Can't instantiate AbstractCollectionModel!");
			}
	*/
			super();
		}

		onDestroy() {
			this.forEach(item => item.onDestroy?.());
		}

		/**
		 * @static
		 * @param {FetchJson} json
		 * @returns {*CollectionModel}
		 */
		static reviveFromJson(json, itemCallback) {
			const result = new this();
			if (json) {
				if ('Collection/'+this.name.replace('Model', '') === json['@Object']) {
					forEachObjectEntry(json, (key, value) => '@' !== key[0] && (result[key] = value));
					json = json['@Collection'];
				}
				isArray(json) && json.forEach(item => {
					item && itemCallback && (item = itemCallback(item, result));
					item && result.push(item);
				});
			}
			return result;
		}

	}

	class EmailCollectionModel extends AbstractCollectionModel
	{
		/**
		 * @param {?Array} json
		 * @returns {EmailCollectionModel}
		 */
		static reviveFromJson(items) {
			return super.reviveFromJson(items, email => EmailModel.reviveFromJson(email));
		}

		/**
		 * @param {string} text
		 * @returns {EmailCollectionModel}
		 */
		static fromString(str) {
			let list = new this();
			list.fromString(str);
			return list;
		}

		/**
		 * @param {boolean=} friendlyView = false
		 * @param {boolean=} wrapWithLink = false
		 * @returns {string}
		 */
		toString(friendlyView, wrapWithLink) {
			return this.map(email => email.toLine(friendlyView, wrapWithLink)).join(', ');
		}

		/**
		 * @param {string} text
		 */
		fromString(str) {
			if (str) {
				let items = {}, key;
				addressparser(str).forEach(item => {
					item = new EmailModel(item.email, item.name);
					// Make them unique
					key = item.email || item.name;
					if (key && (item.name || !items[key])) {
						items[key] = item;
					}
				});
				forEachObjectValue(items, item => this.push(item));
			}
		}

		/**
		 * @param {array} [{name: "Name", email: "address@domain"}]
		 */
	/*
		static fromArray(addresses) {
			let list = new this();
			list.fromArray(addresses);
			return list;
		}
		fromArray(addresses) {
			addresses.forEach(item => {
				item = new EmailModel(item.email, item.name);
				// Make them unique
				if (item.email && item.name || !this.find(address => address.email == item.email)) {
					this.push(item);
				}
			});
		}
	*/

	}

	class AttachmentModel extends AbstractModel {
		constructor() {
			super();

			this.checked = ko.observable(true);

			this.mimeType = '';
	//		this.mimeTypeParams = '';
			this.fileName = '';
			this.fileNameExt = '';
			this.fileType = FileType.Unknown;
			this.cId = '';
			this.contentLocation = '';
			this.folder = '';
			this.uid = '';
			this.url = '';
			this.mimeIndex = '';
			this.estimatedSize = 0;

			addObservablesTo(this, {
				isInline: false,
				isLinked: false
			});
		}

		/**
		 * @static
		 * @param {FetchJsonAttachment} json
		 * @returns {?AttachmentModel}
		 */
		static reviveFromJson(json) {
			const attachment = super.reviveFromJson(json);
			if (attachment) {
				attachment.fileNameExt = FileInfo.getExtension(attachment.fileName);
				attachment.fileType = FileInfo.getType(attachment.fileNameExt, attachment.mimeType);
			}
			return attachment;
		}

		toggleChecked(self, event) {
			stopEvent(event);
			self.checked(!self.checked());
		}

		friendlySize() {
			return FileInfo.friendlySize(this.estimatedSize) + (this.isLinked() ? ' 🔗' : '');
		}

		contentId() {
			return this.cId.replace(/^<+|>+$/g, '');
		}

		/**
		 * @returns {boolean}
		 */
		isImage() {
			return FileType.Image === this.fileType;
		}

		/**
		 * @returns {boolean}
		 */
		isMp3() {
			return FileType.Audio === this.fileType && 'mp3' === this.fileNameExt;
		}

		/**
		 * @returns {boolean}
		 */
		isOgg() {
			return FileType.Audio === this.fileType && ('oga' === this.fileNameExt || 'ogg' === this.fileNameExt);
		}

		/**
		 * @returns {boolean}
		 */
		isWav() {
			return FileType.Audio === this.fileType && 'wav' === this.fileNameExt;
		}

		/**
		 * @returns {boolean}
		 */
		isText() {
			return FileType.Text === this.fileType || FileType.Eml === this.fileType;
		}

		/**
		 * @returns {boolean}
		 */
		pdfPreview() {
			return null != navigator.mimeTypes['application/pdf'] && FileType.Pdf === this.fileType;
		}

		/**
		 * @returns {boolean}
		 */
		hasPreview() {
			return this.isImage() || this.pdfPreview() || this.isText();
		}

		/**
		 * @returns {boolean}
		 */
		hasPreplay() {
			return (
				(SMAudio.supportedMp3 && this.isMp3()) ||
				(SMAudio.supportedOgg && this.isOgg()) ||
				(SMAudio.supportedWav && this.isWav())
			);
		}

		get download() {
			return b64EncodeJSONSafe(this.url ? {
				fileName: this.fileName,
				data: this.url.replace(/^.+,/, '')
			} : {
				folder: this.folder,
				uid: this.uid,
				mimeIndex: this.mimeIndex,
				mimeType: this.mimeType,
				fileName: this.fileName,
				accountHash: SettingsGet('accountHash')
			});
		}

		/**
		 * @returns {string}
		 */
		linkDownload() {
			return this.url || attachmentDownload(this.download);
		}

		/**
		 * @returns {string}
		 */
		linkPreview() {
			return this.url || serverRequestRaw('View', this.download);
		}

		/**
		 * @returns {boolean}
		 */
		hasThumbnail() {
			return SettingsCapa('AttachmentThumbnails') && this.isImage() && !this.isLinked();
		}

		/**
		 * @returns {string}
		 */
		thumbnailStyle() {
			return this.hasThumbnail()
				? 'background:url(' + serverRequestRaw('ViewThumbnail', this.download) + ')'
				: null;
		}

		/**
		 * @returns {string}
		 */
		linkPreviewMain() {
			let result = '';
			switch (true) {
				case this.isImage():
				case this.pdfPreview():
					result = this.linkPreview();
					break;
				case this.isText():
					result = serverRequestRaw('ViewAsPlain', this.download);
					break;
				// no default
			}

			return result;
		}

		/**
		 * @param {AttachmentModel} attachment
		 * @param {*} event
		 * @returns {boolean}
		 */
		eventDragStart(attachment, event) {
			const localEvent = event.originalEvent || event;
			if (attachment && localEvent && localEvent.dataTransfer && localEvent.dataTransfer.setData) {
				let link = this.linkDownload();
				if (!link.startsWith('http')) {
					link = location.protocol + '//' + location.host + location.pathname + link;
				}
				localEvent.dataTransfer.setData('DownloadURL', this.mimeType + ':' + this.fileName + ':' + link);
			}

			return true;
		}

		/**
		 * @returns {string}
		 */
		iconClass() {
			return FileInfo.getTypeIconClass(this.fileType);
		}
	}

	class AttachmentCollectionModel extends AbstractCollectionModel
	{
		/**
		 * @param {?Array} json
		 * @returns {AttachmentCollectionModel}
		 */
		static reviveFromJson(items) {
			const attachments = super.reviveFromJson(items, attachment => AttachmentModel.reviveFromJson(attachment));
			let collator = baseCollator(true);
			attachments.sort((a, b) => {
				if (a.isInline()) {
					if (!b.isInline()) {
						return 1;
					}
				} else if (!b.isInline()) {
					return -1;
				}
				return collator.compare(a.fileName, b.fileName);
			});
	/*
			if (attachments) {
				attachments.InlineCount = attachments.reduce((accumulator, a) => accumulator + (a.isInline ? 1 : 0), 0);
			}
	*/
			return attachments;
		}

		/**
		 * @param {string} cId
		 * @returns {*}
		 */
		findByCid(cId) {
			cId = cId.replace(/^<+|>+$/g, '');
			return this.find(item => cId === item.contentId());
		}
	}

	class MimeHeaderModel extends AbstractModel
	{
		constructor() {
			super();
			this.name = '';
			this.value = '';
			this.parameters = ko.observableArray();
		}
	}

	class MimeHeaderCollectionModel extends AbstractCollectionModel
	{
		/**
		 * @param {?Array} json
		 * @returns {MimeHeaderCollectionModel}
		 */
		static reviveFromJson(items) {
			return super.reviveFromJson(items, header => MimeHeaderModel.reviveFromJson(header));
		}

		/**
		 * @param {string} name
		 * @returns {?MimeHeader}
		 */
		getByName(name)
		{
			name = name.toLowerCase();
			return this.find(header => header.name.toLowerCase() === name);
		}

		valueByName(name)
		{
			const header = this.getByName(name);
			return header ? header.value : '';
		}

		valuesByName(name)
		{
			name = name.toLowerCase();
			return this.filter(header => header.name.toLowerCase() === name).map(header => header.value);
		}

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

	const AppUserStore = {
		allowContacts: () => !!SettingsGet('contactsAllowed')
	};

	addObservablesTo(AppUserStore, {
		focusedState: 'none',

		threadsAllowed: false
	});

	AppUserStore.focusedState.subscribe(value => {
		['FolderList','MessageList','MessageView'].forEach(name => {
			if (name === value) {
				arePopupsVisible() || keyScope(value);
				ThemeStore.isMobile() && leftPanelDisabled('FolderList' !== value);
			}
			elementById('V-Mail'+name).classList.toggle('focused', name === value);
		});
	});

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

	class RemoteUserFetch extends AbstractFetchRemote {

		/**
		 * @param {?Function} fCallback
		 * @param {string} sFolderFullName
		 * @param {number} iUid
		 * @returns {boolean}
		 */
		message(fCallback, sFolderFullName, iUid) {
			sFolderFullName = pString(sFolderFullName);
			iUid = pInt(iUid);

			if (getFolderFromCacheList(sFolderFullName) && 0 < iUid) {
				this.abort('Message').request('Message',
					fCallback,
					{},
					null,
					'Message/' +
						SUB_QUERY_PREFIX +
						'/' +
						b64EncodeJSONSafe([
							sFolderFullName,
							iUid,
							AppUserStore.threadsAllowed() && SettingsUserStore.useThreads() ? 1 : 0,
							SettingsGet('accountHash')
						])
				);

				return true;
			}

			return false;
		}

		/**
		 * @param {?Function} fCallback
		 * @param {Object} oData
		 */
		saveSettings(fCallback, oData) {
			this.request('SettingsUpdate', fCallback, oData);
		}

		/**
		 * @param {string} key
		 * @param {?scalar} value
		 * @param {?Function} fCallback
		 */
		saveSetting(key, value, fCallback) {
			this.saveSettings(fCallback, {
				[key]: value
			});
		}
	}

	var Remote = new RemoteUserFetch();

	function ParseMime(text)
	{
		class MimePart
		{
	/*
			constructor() {
				this.id = 0;
				this.start = 0;
				this.end = 0;
				this.parts = [];
				this.bodyStart = 0;
				this.bodyEnd = 0;
				this.boundary = '';
				this.bodyText = '';
				// https://datatracker.ietf.org/doc/html/rfc2822#section-3.6
				// https://datatracker.ietf.org/doc/html/rfc4021
				this.headers = {
					// Required
					date = null,
					from = [], // mailbox-list
					// Optional
					sender          = [], // mailbox MUST occur with multi-address
					'reply-to'      = [], // address-list
					to              = [], // address-list
					cc              = [], // address-list
					bcc             = [], // address-list
					'message-id'    = '', // msg-id SHOULD be present
					'in-reply-to'   = '', // 1*msg-id SHOULD occur in some replies
					references      = '', // 1*msg-id SHOULD occur in some replies
					subject         = '', // unstructured
					// Optional unlimited
					comments        = [], // unstructured
					keywords        = [], // phrase *("," phrase)
					// https://datatracker.ietf.org/doc/html/rfc2822#section-3.6.6
					'resent-date'   = [],
					'resent-from'   = [],
					'resent-sender' = [],
					'resent-to'     = [],
					'resent-cc'     = [],
					'resent-bcc'    = [],
					'resent-msg-id' = [],
					// https://datatracker.ietf.org/doc/html/rfc2822#section-3.6.7
					trace           = [],
					'return-path'   = '', // angle-addr
					received        = [],
					// optional others outside RFC2822
					'mime-version'              = '', // RFC2045
					'content-transfer-encoding' = '',
					'content-type'              = '',
					'delivered-to'              = [], // RFC9228 addr-spec
					'authentication-results'    = '', // dkim, spf, dmarc
					'dkim-signature'            = '',
					'x-rspamd-queue-id'         = '',
					'x-rspamd-action'           = '',
					'x-spamd-bar'               = '',
					'x-rspamd-server'           = '',
					'x-spamd-result'            = '',
					'x-remote-address'          = '',
					// etc.
				};
			}
	*/

			header(name) {
				return this.headers?.[name];
			}

			headerValue(name) {
				return this.header(name)?.value;
			}

			get raw() {
				return text.slice(this.start, this.end);
			}

			get bodyRaw() {
				return text.slice(this.bodyStart, this.bodyEnd);
			}

			get body() {
				let body = this.bodyRaw,
					charset = this.header('content-type')?.params.charset,
					encoding = this.headerValue('content-transfer-encoding')?.toLowerCase();
				if ('quoted-printable' == encoding) {
					body = QPDecode(body);
				} else if ('base64' == encoding) {
					body = BDecode(body.replace(/\r?\n/g, ''));
				}
				return decodeText(charset, body);
			}

			get dataUrl() {
				let body = this.bodyRaw,
					encoding = this.headerValue('content-transfer-encoding')?.toLowerCase();
				if ('base64' == encoding) {
					body = body.replace(/\r?\n/g, '');
				} else {
					if ('quoted-printable' == encoding) {
						body = QPDecode(body);
					}
					body = BEncode(body);
				}
				return 'data:' + this.headerValue('content-type') + ';base64,' + body;
			}

			forEach(fn) {
				fn(this);
				this.parts.forEach(part => part.forEach(fn));
			}

			getByContentType(type) {
				if (type == this.headerValue('content-type')?.toLowerCase()) {
					return this;
				}
				let i = 0, p = this.parts, part;
				for (i; i < p.length; ++i) {
					if ((part = p[i].getByContentType(type))) {
						return part;
					}
				}
			}
		}

		// mailbox-list or address-list
		const lists = ['from','reply-to','to','cc','bcc'];

		const ParsePart = (mimePart, start_pos = 0, id = '') =>
		{
			let part = new MimePart,
				head = mimePart.match(/^[\s\S]+?\r?\n\r?\n/)?.[0],
				headers = {};
			if (id) {
				part.id = id;
				part.start = start_pos;
				part.end = start_pos + mimePart.length;
			}
			part.parts = [];

			// get headers
			if (head) {
				head.replace(/\r?\n\s+/g, ' ').split(/\r?\n/).forEach(header => {
					let match = header.match(/^([^:]+):\s*([^;]+)/),
						params = {};
					if (match) {
						[...header.matchAll(/;\s*([^;=]+)=\s*"?([^;"]+)"?/g)].forEach(param =>
							params[param[1].trim().toLowerCase()] = param[2].trim()
						);
						let field = match[1].trim().toLowerCase();
						if (lists.includes(field)) {
							match[2] = addressparser(match[2]);
						} else if ('keywords' === field) {
							match[2] = match[2].split(',').forEach(entry => decodeEncodedWords(entry.trim()));
							match[2] = (headers[field]?.value || []).concat(match[2]);
						} else {
							match[2] = decodeEncodedWords(match[2].trim());
							if ('comments' === field) {
								match[2] = (headers[field]?.value || []).push(match[2]);
							}
						}
						headers[field] = {
							value: match[2],
							params: params
						};
					}
				});

				// get body
				part.bodyStart = start_pos + head.length;
				part.bodyEnd = start_pos + mimePart.length;

				// get child parts
				let boundary = headers['content-type']?.params.boundary;
				if (boundary) {
					part.boundary = boundary;
					let regex = new RegExp('(?:^|\r?\n)--' + RegExp.escape(boundary) + '(?:--)?(?:\r?\n|$)', 'g'),
						body = mimePart.slice(head.length),
						bodies = body.split(regex),
						pos = part.bodyStart;
					[...body.matchAll(regex)].forEach(([boundary], index) => {
						if (!index) {
							// Mostly something like: "This is a multi-part message in MIME format."
							part.bodyText = bodies[0];
						}
						// Not the end?
						if ('--' != boundary.trim().slice(-2)) {
							pos += bodies[index].length + boundary.length;
							part.parts.push(ParsePart(bodies[1+index], pos, ((id ? id + '.' : '') + (1+index))));
						}
					});
				}

				part.headers = headers;
			}

			return part;
		};

		return ParsePart(text);
	}

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

	class OpenPgpKeyPopupView extends AbstractViewPopup {
		constructor() {
			super('OpenPgpKey');

			addObservablesTo(this, {
				key: '',
				keyDom: null
			});
		}

		selectKey() {
			const el = this.keyDom();
			if (el) {
				let sel = getSelection(),
					range = doc.createRange();
				sel.removeAllRanges();
				range.selectNodeContents(el);
				sel.addRange(range);
			}
			if (navigator.clipboard) {
				navigator.clipboard.writeText(this.key()).then(
					() => console.log('Copied to clipboard'),
					err => console.error(err)
				);
			}
		}

		onShow(openPgpKey) {
			// TODO: show more info
			this.key(openPgpKey ? openPgpKey.armor : '');
	/*
			this.key = key;
			const aEmails = [];
			if (key.users) {
				key.users.forEach(user => user.userID.email && aEmails.push(user.userID.email));
			}
			this.id = key.getKeyID().toHex();
			this.fingerprint = key.getFingerprint();
			this.can_encrypt = !!key.getEncryptionKey();
			this.can_sign = !!key.getSigningKey();
			this.emails = aEmails;
			this.armor = armor;
			this.askDelete = ko.observable(false);
			this.openForDeletion = ko.observable(null).askDeleteHelper();

			key.id = key.subkeys[0].keyid;
			key.fingerprint = key.subkeys[0].fingerprint;
			key.uids.forEach(uid => uid.email && aEmails.push(uid.email));
			key.emails = aEmails;
			"disabled": false,
			"expired": false,
			"revoked": false,
			"is_secret": true,
			"can_sign": true,
			"can_decrypt": true
			"can_verify": true
			"can_encrypt": true,
			"uids": [
				{
					"name": "demo",
					"comment": "",
					"email": "demo@snappymail.eu",
					"uid": "demo <demo@snappymail.eu>",
					"revoked": false,
					"invalid": false
				}
			],
			"subkeys": [
				{
					"fingerprint": "2C223F20EA2ADB4CB68F81D95F3A5CDC09AD8AE3",
					"keyid": "5F3A5CDC09AD8AE3",
					"timestamp": 1643381672,
					"expires": 0,
					"is_secret": false,
					"invalid": false,
					"can_encrypt": false,
					"can_sign": true,
					"disabled": false,
					"expired": false,
					"revoked": false,
					"can_certify": true,
					"can_authenticate": false,
					"is_qualified": false,
					"is_de_vs": false,
					"pubkey_algo": 303,
					"length": 256,
					"keygrip": "5A1A6C7310D0508C68E8E74F15068301E83FD1AE",
					"is_cardkey": false,
					"curve": "ed25519"
				},
				{
					"fingerprint": "3CD720549D8833872C267D08F1230DCE2A561ADE",
					"keyid": "F1230DCE2A561ADE",
					"timestamp": 1643381672,
					"expires": 0,
					"is_secret": false,
					"invalid": false,
					"can_encrypt": true,
					"can_sign": false,
					"disabled": false,
					"expired": false,
					"revoked": false,
					"can_certify": false,
					"can_authenticate": false,
					"is_qualified": false,
					"is_de_vs": false,
					"pubkey_algo": 302,
					"length": 256,
					"keygrip": "886921A7E06BE56F8E8C51797BB476BB26DF21BF",
					"is_cardkey": false,
					"curve": "cv25519"
				}
			]
	*/
		}

		onBuild() {
			addShortcut('a', 'meta', 'OpenPgpKey', () => {
				this.selectKey();
				return false;
			});
		}
	}

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

	const Passphrases = new WeakMap();

	Passphrases.ask = async (key, sAskDesc, btnText) =>
		Passphrases.has(key)
			? {password:Passphrases.handle(key)/*, remember:false*/}
			: await AskPopupView.password(sAskDesc, btnText, 5);

	const timeouts = {};
	// get/set accessor to control deletion after N minutes of inactivity
	Passphrases.handle = (key, pass) => {
		const timeout = SettingsUserStore.keyPassForget();
		if (timeout && !timeouts[key]) {
			timeouts[key] = (()=>Passphrases.delete(key)).debounce(timeout * 1000);
		}
		pass && Passphrases.set(key, pass);
		timeout && timeouts[key]();
		return Passphrases.get(key);
	};

	const
		findGnuPGKey = (keys, query/*, sign*/) =>
			keys.find(key =>
	//			key[sign ? 'can_sign' : 'can_decrypt']
				(key.can_sign || key.can_decrypt)
				&& (key.for(query) || key.subkeys.find(key => query == key.keyid || query == key.fingerprint))
			);

	const GnuPGUserStore = new class {
		constructor() {
			/**
			 * PECL gnupg / PEAR Crypt_GPG
			 * [ {email, can_encrypt, can_sign}, ... ]
			 */
			this.keyring;
			this.publicKeys = ko.observableArray();
			this.privateKeys = ko.observableArray();
		}

		loadKeyrings() {
			this.keyring = null;
			this.publicKeys([]);
			this.privateKeys([]);
			SettingsCapa('GnuPG')
			&& Remote.request('GnupgGetKeys',
				(iError, oData) => {
					if (oData?.Result) {
						this.keyring = oData.Result;
						const initKey = (key, isPrivate) => {
							const aEmails = [];
							key.id = key.subkeys[0].keyid;
							key.fingerprint = key.subkeys[0].fingerprint;
							key.uids.forEach(uid => uid.email && aEmails.push(uid.email));
							key.emails = aEmails;
							key.for = email => aEmails.includes(IDN.toASCII(email));
							key.askDelete = ko.observable(false);
							key.openForDeletion = ko.observable(null).askDeleteHelper();
							key.remove = () => {
								if (key.askDelete()) {
									Remote.request('GnupgDeleteKey',
										(iError, oData) => {
											if (oData) {
												if (iError) {
													alert(oData.message);
												} else if (oData.Result) {
													isPrivate
														? this.privateKeys.remove(key)
														: this.publicKeys.remove(key);
												}
											}
										}, {
											keyId: key.id,
											isPrivate: isPrivate
										}
									);
								}
							};
							if (isPrivate) {
								key.password = async btnTxt => {
									const pass = await Passphrases.ask(key,
										'GnuPG key<br>' + key.id + ' ' + key.emails[0],
										btnTxt
									);
									pass && pass.remember && Passphrases.handle(key, pass.password);
									return pass?.password;
								};
							}
							key.fetch = async callback => {
								if (key.armor) {
									callback && callback();
								} else {
									let pass = isPrivate ? await key.password('OPENPGP/POPUP_VIEW_TITLE') : '';
									if (null != pass) try {
										const result = await Remote.post('GnupgExportKey', null, {
												keyId: key.id,
												isPrivate: isPrivate,
												passphrase: pass
											});
										if (result?.Result) {
											key.armor = result.Result;
											callback && callback();
										} else {
											Passphrases.delete(key);
										}
									} catch (e) {
										Passphrases.delete(key);
										alert(e.message);
									}
								}
								return key.armor;
							};
							key.view = () => key.fetch(() => showScreenPopup(OpenPgpKeyPopupView, [key]));
							return key;
						},
						collator = baseCollator(),
						sort = keys => keys.sort(
							(a, b) => collator.compare(a.emails[0], b.emails[0]) || collator.compare(a.id, b.id)
						);
						this.publicKeys(sort(oData.Result.public.map(key => initKey(key, 0))));
						this.privateKeys(sort(oData.Result.private.map(key => initKey(key, 1))));
						console.log('gnupg ready');
					}
				}
			);
		}

		/**
		 * @returns {boolean}
		 */
		isSupported() {
			return SettingsCapa('GnuPG');
		}

		/**
			keyPair.privateKey
			keyPair.publicKey
			keyPair.revocationCertificate
			keyPair.onServer
			keyPair.inGnuPG
		 */
		storeKeyPair(keyPair, callback) {
			Remote.request('PgpStoreKeyPair',
				(iError, oData) => {
					if (oData?.Result) ;
					callback?.(iError, oData);
				}, keyPair
			);
		}

		/**
		 * Checks if verifying/encrypting a message is possible with given email addresses.
		 */
		hasPublicKeyForEmails(recipients) {
			const count = recipients.length,
				length = count ? recipients.filter(email =>
	//				(key.can_verify || key.can_encrypt) &&
					this.publicKeys.find(key => key.for(email))
				).length : 0;
			return length && length === count;
		}

		getPublicKeyFingerprints(recipients) {
			const fingerprints = [];
			recipients.forEach(email => {
				fingerprints.push(this.publicKeys.find(key => key.for(email)).fingerprint);
			});
			return fingerprints;
		}

		getPrivateKeyFor(query/*, sign*/) {
			return findGnuPGKey(this.privateKeys, query/*, sign*/);
		}

		async decrypt(message) {
			const
				pgpInfo = message.pgpEncrypted();
			if (pgpInfo) {
				let ids = [message.to[0].email].concat(pgpInfo.keyIds),
					i = ids.length, key;
				while (i--) {
					key = findGnuPGKey(this.privateKeys, ids[i]);
					if (key) {
						break;
					}
				}
				if (key) {
					// Also check message.from[0].email
					let params = {
						folder: message.folder,
						uid: message.uid,
						partId: pgpInfo.partId,
						keyId: key.id,
						passphrase: await key.password('CRYPTO/DECRYPT'),
						data: '' // message.plain() optional
					};
					if (null != params.passphrase) {
						try {
							const response = await Remote.post('GnupgDecrypt', null, params);
							if (response?.Result?.data) {
								return response.Result;
							}
							throw response;
						} catch (e) {
							Passphrases.delete(key);
							throw e;
						}
					}
				}
			}
		}

		async verify(message) {
			let data = message.pgpSigned(); // { partId: "1", sigPartId: "2", micAlg: "pgp-sha256" }
			if (data) {
				data = { ...data }; // clone
	//			const sender = message.from[0].email;
	//			let mode = await this.hasPublicKeyForEmails([sender]);
				data.folder = message.folder;
				data.uid = message.uid;
				if (data.bodyPart) {
					data.bodyPart = data.bodyPart.raw;
					data.sigPart = data.sigPart.body;
				}
				let response = await Remote.post('PgpVerifyMessage', null, data);
				if (response?.Result) {
					return {
						fingerprint: response.Result.fingerprint,
						success: 0 == response.Result.status, // GOODSIG
						error: response.Result.message
					};
				}
			}
		}

		async sign(privateKey) {
			return await privateKey.password('CRYPTO/SIGN');
		}

	};

	/**
	 * OpenPGP.js
	 */

	const
		loaded = () => !!window.openpgp,

		findOpenPGPKey = (keys, query/*, sign*/) =>
			keys.find(key =>
				key.for(query) || query == key.id || query == key.fingerprint
			),

		decryptKey = async (privateKey, btnTxt = 'SIGN') => {
			if (privateKey.key.isDecrypted()) {
				return privateKey.key;
			}
			const key = privateKey.id,
				pass = await Passphrases.ask(privateKey,
					'OpenPGP.js key<br>' + key + ' ' + privateKey.emails[0],
					'CRYPTO/'+btnTxt
				);
			if (pass) {
				const passphrase = pass.password,
					result = await openpgp.decryptKey({
						privateKey: privateKey.key,
						passphrase
					});
				result && pass.remember && Passphrases.handle(privateKey, passphrase);
				return result;
			}
		},

		collator = baseCollator(),
		sort = keys => keys.sort(
	//		(a, b) => collator.compare(a.emails[0], b.emails[0]) || collator.compare(a.fingerprint, b.fingerprint)
			(a, b) => collator.compare(a.emails[0], b.emails[0]) || collator.compare(a.id, b.id)
		),
		dedup = keys => sort((keys || [])
			.filter((v, i, a) => a.findIndex(entry => entry.fingerprint == v.fingerprint) === i)
		),

		/**
		 * OpenPGP.js v5 removed the localStorage (keyring)
		 * This should be compatible with the old OpenPGP.js v2
		 */
		publicKeysItem = 'openpgp-public-keys',
		privateKeysItem = 'openpgp-private-keys',
		storage = window.localStorage,
		loadOpenPgpKeys = async itemname => {
			let keys = [], key,
				armoredKeys = JSON.parse(storage.getItem(itemname)),
				i = arrayLength(armoredKeys);
			while (i--) try {
				key = await openpgp.readKey({armoredKey:armoredKeys[i]});
				key.err || keys.push(new OpenPgpKeyModel(armoredKeys[i], key));
			} catch (e) {
				console.error(e);
			}
			return keys;
		},
		storeOpenPgpKeys = (keys, section) => {
			let armoredKeys = keys.map(item => item.armor);
			if (armoredKeys.length) {
				storage.setItem(section, JSON.stringify(armoredKeys));
			} else {
				storage.removeItem(section);
			}
		};

	class OpenPgpKeyModel {
		constructor(armor, key) {
			this.key = key;
			this.id = key.getKeyID().toHex().toUpperCase();
			this.fingerprint = key.getFingerprint();
			this.can_encrypt = !!key.getEncryptionKey();
			this.can_sign = !!key.getSigningKey();
			this.emails = key.users.map(user => IDN.toASCII(user.userID.email)).filter(email => email);
			this.armor = armor;
			this.askDelete = ko.observable(false);
			this.openForDeletion = ko.observable(null).askDeleteHelper();
	//		key.getUserIDs()
	//		key.getPrimaryUser()
		}

	/*
		get id() { return this.key.getKeyID().toHex().toUpperCase(); }
		get fingerprint() { return this.key.getFingerprint(); }
		get can_encrypt() { return !!this.key.getEncryptionKey(); }
		get can_sign() { return !!this.key.getSigningKey(); }
		get emails() { return this.key.users.map(user => IDN.toASCII(user.userID.email)).filter(email => email); }
		get armor() { return this.key.armor(); }
	*/
		for(email) {
			return this.emails.includes(IDN.toASCII(email));
		}

		view() {
			showScreenPopup(OpenPgpKeyPopupView, [this]);
		}

		remove() {
			if (this.askDelete()) {
				if (this.key.isPrivate()) {
					OpenPGPUserStore.privateKeys.remove(this);
					storeOpenPgpKeys(OpenPGPUserStore.privateKeys, privateKeysItem);
				} else {
					OpenPGPUserStore.publicKeys.remove(this);
					storeOpenPgpKeys(OpenPGPUserStore.publicKeys, publicKeysItem);
				}
			}
		}
	/*
		toJSON() {
			return this.armor;
		}
	*/
	}

	const OpenPGPUserStore = new class {
		constructor() {
			this.publicKeys = ko.observableArray();
			this.privateKeys = ko.observableArray();
		}

		loadKeyrings() {
			if (loaded()) {
				loadOpenPgpKeys(publicKeysItem)
				.then(keys => {
					this.publicKeys(dedup(keys));
					console.log('openpgp.js public keys loaded');
				})
				.finally(() => {
					loadOpenPgpKeys(privateKeysItem)
					.then(keys => {
						this.privateKeys(dedup(keys));
						console.log('openpgp.js private keys loaded');
					})
					.finally(() => {
						/*SettingsGet('loadBackupKeys') && */this.loadBackupKeys();
					});
				});
			}
		}

		loadBackupKeys() {
			Remote.request('GetPGPKeys',
				(iError, oData) => !iError && oData.Result && this.importKeys(oData.Result)
			);
		}

		/**
		 * @returns {boolean}
		 */
		isSupported() {
			return loaded();
		}

		importKey(armoredKey) {
			this.importKeys([armoredKey]);
		}

		async importKeys(keys) {
			if (loaded()) {
				const privateKeys = this.privateKeys(),
					publicKeys = this.publicKeys();
				for (const armoredKey of keys) try {
					let key = await openpgp.readKey({armoredKey:armoredKey});
					if (!key.err) {
						key = new OpenPgpKeyModel(armoredKey, key);
						const keys = key.key.isPrivate() ? privateKeys : publicKeys;
						keys.find(entry => entry.fingerprint == key.fingerprint)
						|| keys.push(key);
					}
				} catch (e) {
					console.error(e, armoredKey);
				}
				this.privateKeys(sort(privateKeys));
				this.publicKeys(sort(publicKeys));
				storeOpenPgpKeys(privateKeys, privateKeysItem);
				storeOpenPgpKeys(publicKeys, publicKeysItem);
			}
		}

		/**
			keyPair.privateKey
			keyPair.publicKey
			keyPair.revocationCertificate
		 */
		storeKeyPair(keyPair) {
			if (loaded()) {
				openpgp.readKey({armoredKey:keyPair.publicKey}).then(key => {
					this.publicKeys.push(new OpenPgpKeyModel(keyPair.publicKey, key));
					storeOpenPgpKeys(this.publicKeys, publicKeysItem);
				});
				openpgp.readKey({armoredKey:keyPair.privateKey}).then(key => {
					this.privateKeys.push(new OpenPgpKeyModel(keyPair.privateKey, key));
					storeOpenPgpKeys(this.privateKeys, privateKeysItem);
				});
			}
		}

		/**
		 * Checks if verifying/encrypting a message is possible with given email addresses.
		 */
		hasPublicKeyForEmails(recipients) {
			const count = recipients.length,
				length = count ? recipients.filter(email =>
					this.publicKeys().find(key => key.for(email))
				).length : 0;
			return length && length === count;
		}

		getPrivateKeyFor(query/*, sign*/) {
			return findOpenPGPKey(this.privateKeys, query/*, sign*/);
		}

		/**
		 * https://docs.openpgpjs.org/#encrypt-and-decrypt-string-data-with-pgp-keys
		 */
		async decrypt(armoredText, sender)
		{
			const message = await openpgp.readMessage({ armoredMessage: armoredText }),
				privateKeys = this.privateKeys(),
				msgEncryptionKeyIDs = message.getEncryptionKeyIDs().map(key => key.bytes);
			// Find private key that can decrypt message
			let i = privateKeys.length, privateKey;
			while (i--) {
				if ((await privateKeys[i].key.getDecryptionKeys()).find(
					key => msgEncryptionKeyIDs.includes(key.getKeyID().bytes)
				)) {
					privateKey = privateKeys[i];
					break;
				}
			}
			if (privateKey) try {
				const decryptedKey = await decryptKey(privateKey, 'DECRYPT');
				if (decryptedKey) {
					const publicKey = findOpenPGPKey(this.publicKeys, sender/*, sign*/);
					return await openpgp.decrypt({
						message,
						verificationKeys: publicKey?.key,
	//					expectSigned: true,
	//					signature: '', // Detached signature
						decryptionKeys: decryptedKey
					});
				}
			} catch (err) {
				alert(err);
				console.error(err);
			}
		}

		/**
		 * https://docs.openpgpjs.org/#sign-and-verify-cleartext-messages
		 */
		async verify(message) {
			const data = message.pgpSigned(), // { partId: "1", sigPartId: "2", micAlg: "pgp-sha256" }
				publicKey = this.publicKeys().find(key => key.for(message.from[0].email));
			if (data && publicKey) {
				data.folder = message.folder;
				data.uid = message.uid;
				data.tryGnuPG = 0;
				let response;
				if (data.sigPartId) {
					response = await Remote.post('PgpVerifyMessage', null, data);
				} else if (data.bodyPart) {
					// MimePart
					response = { Result: { text: data.bodyPart.raw, signature: data.sigPart.body } };
				} else {
					response = { Result: { text: message.plain(), signature: null } };
				}
				if (response) {
					const signature = response.Result.signature
						? await openpgp.readSignature({ armoredSignature: response.Result.signature })
						: null;
					const signedMessage = signature
						? await openpgp.createMessage({ text: response.Result.text })
						: await openpgp.readCleartextMessage({ cleartextMessage: response.Result.text });
	//				(signature||signedMessage).getSigningKeyIDs();
					let result = await openpgp.verify({
						message: signedMessage,
						verificationKeys: publicKey.key,
	//					expectSigned: true, // !!detachedSignature
						signature: signature
					});
					return {
						fingerprint: publicKey.fingerprint,
						success: result && !!result.signatures.length
					};
				}
			}
		}

		/**
		 * https://docs.openpgpjs.org/global.html#sign
		 */
		async sign(text, privateKey, detached) {
			const signingKey = await decryptKey(privateKey);
			if (signingKey) {
				const message = detached
					? await openpgp.createMessage({ text: text })
					: await openpgp.createCleartextMessage({ text: text });
				return await openpgp.sign({
					message: message,
					signingKeys: signingKey,
					detached: !!detached
				});
			}
			throw 'Sign cancelled';
		}

		/**
		 * https://docs.openpgpjs.org/global.html#encrypt
		 */
		async encrypt(text, recipients, signPrivateKey) {
			const count = recipients.length;
			recipients = recipients.map(email => this.publicKeys().find(key => key.for(email))).filter(key => key);
			if (count === recipients.length) {
				if (signPrivateKey) {
					signPrivateKey = await decryptKey(signPrivateKey);
					if (!signPrivateKey) {
						return;
					}
				}
				return await openpgp.encrypt({
					message: await openpgp.createMessage({ text: text }),
					encryptionKeys: recipients.map(pkey => pkey.key),
					signingKeys: signPrivateKey
	//				signature
				});
			}
			throw 'Encrypt failed';
		}

	};

	// https://mailvelope.github.io/mailvelope/Keyring.html
	let mailvelopeKeyring = null;

	const MailvelopeUserStore = {
		keyring: null,

		loadKeyring(identifier) {
			identifier = identifier || SettingsGet('Email');
			if (window.mailvelope) {
				const fn = keyring => {
						mailvelopeKeyring = keyring;
						console.log('mailvelope ready');
					};
				mailvelope.getKeyring().then(fn, err => {
					if (identifier) {
						// attempt to create a new keyring for this app/user
						mailvelope.createKeyring(identifier).then(fn, err => console.error(err));
					} else {
						console.error(err);
					}
				});
				addEventListener('mailvelope-disconnect', event => {
					alert('Mailvelope is updated to version ' + event.detail.version + '. Reload page');
				}, false);
			} else {
				addEventListener('mailvelope', () => this.loadKeyring(identifier));
			}
		},

		async hasPublicKeyForEmails(recipients) {
			const
				mailvelope = mailvelopeKeyring && await mailvelopeKeyring.validKeyForAddress(recipients)
					/*.then(LookupResult => Object.entries(LookupResult))*/,
				entries = mailvelope && Object.entries(mailvelope);
			return entries && entries.filter(value => value[1]).length === recipients.length;
		},

		async getPrivateKeyFor(email/*, sign*/) {
			if (mailvelopeKeyring && await mailvelopeKeyring.hasPrivateKey({email:email})) {
				return ['mailvelope', email];
			}
			return false;
		},

		async decrypt(message) {
			// Try Mailvelope (does not support inline images)
			if (mailvelopeKeyring) {
				const sender = message.from[0].email,
					armoredText = message.plain();
				try {
					let emails = [...message.from,...message.to,...message.cc].validUnique(),
						i = emails.length;
					while (i--) {
						if (await this.getPrivateKeyFor(emails[i].email)) {
							/**
							* https://mailvelope.github.io/mailvelope/Mailvelope.html#createEncryptedFormContainer
							* Creates an iframe to display an encrypted form
							*/
		//					mailvelope.createEncryptedFormContainer('#mailvelope-form');
							/**
							* https://mailvelope.github.io/mailvelope/Mailvelope.html#createDisplayContainer
							* Creates an iframe to display the decrypted content of the encrypted mail.
							*/
							const body = message.body;
							body.textContent = '';
							let result = await mailvelope.createDisplayContainer(
								'#'+body.id,
								armoredText,
								mailvelopeKeyring,
								{
									senderAddress: sender
									// emails[i].email
								}
							);
							if (result) {
								if (result.error?.message) {
									if ('PWD_DIALOG_CANCEL' !== result.error.code) {
										alert(result.error.code + ': ' + result.error.message);
									}
								} else {
									body.classList.add('mailvelope');
									return true;
								}
							}
							break;
						}
					}
				} catch (err) {
					console.error(err);
				}
			}
		}
		/**
		 * Returns headers that should be added to an outgoing email.
		 * So far this is only the autocrypt header.
		 */
	/*
		mailvelopeKeyring.additionalHeadersForOutgoingEmail(from: 'abc@web.de')
		.then(function(additional) {
			console.log('additionalHeadersForOutgoingEmail', additional);
			// logs: {autocrypt: "addr=abc@web.de; prefer-encrypt=mutual; keydata=..."}
		});

		mailvelopeKeyring.addSyncHandler(syncHandlerObj)
		mailvelopeKeyring.createKeyBackupContainer(selector, options)
		mailvelopeKeyring.createKeyGenContainer(selector, {
	//		userIds: [],
			keySize: 4096
		})

		mailvelopeKeyring.exportOwnPublicKey(emailAddr).then(<AsciiArmored, Error>)
		mailvelopeKeyring.importPublicKey(armored)

		// https://mailvelope.github.io/mailvelope/global.html#SyncHandlerObject
		mailvelopeKeyring.addSyncHandler({
			uploadSync
			downloadSync
			backup
			restore
		});
	*/
	};

	const
		BEGIN_PGP_MESSAGE = '-----BEGIN PGP MESSAGE-----',
	//	BEGIN_PGP_SIGNATURE = '-----BEGIN PGP SIGNATURE-----',
	//	BEGIN_PGP_SIGNED = '-----BEGIN PGP SIGNED MESSAGE-----',
	//	BEGIN_PGP_PUBLIC_KEY = '-----BEGIN PGP PUBLIC KEY BLOCK-----',
	//	END_PGP_PUBLIC_KEY = '-----END PGP PUBLIC KEY BLOCK-----',

		PgpUserStore = new class {
			init() {
				if (SettingsCapa('OpenPGP') && window.crypto && crypto.getRandomValues) {
					rl.loadScript(SettingsGet('StaticLibsJs').replace('/libs.', '/openpgp.'))
	//				rl.loadScript(staticLink('js/min/openpgp.min.js'))
						.then(() => this.loadKeyrings())
						.catch(e => {
							this.loadKeyrings();
							console.error(e);
						});
				} else {
					this.loadKeyrings();
				}
			}

			loadKeyrings(identifier) {
				MailvelopeUserStore.loadKeyring(identifier);
				OpenPGPUserStore.loadKeyrings();
				GnuPGUserStore.loadKeyrings();
			}

			/**
			 * @returns {boolean}
			 */
			isSupported() {
				return !!(OpenPGPUserStore.isSupported() || GnuPGUserStore.isSupported() || window.mailvelope);
			}

			/**
			 * @returns {boolean}
			 */
			isEncrypted(text) {
				return 0 === text.trim().indexOf(BEGIN_PGP_MESSAGE);
			}

			importKey(key, gnuPG, backup) {
				if (gnuPG || backup) {
					Remote.request('PgpImportKey',
						(iError, oData) => {
							if (gnuPG && oData?.Result/* && (oData.Result.imported || oData.Result.secretimported)*/) {
								GnuPGUserStore.loadKeyrings();
							}
							iError && alert(oData.message);
						}, {
							key, gnuPG, backup
						}
					);
				}
				OpenPGPUserStore.importKey(key);
			}

			/**
			 * Checks if verifying/encrypting a message is possible with given email addresses.
			 * Returns the first library that can.
			 */
			hasPublicKeyForEmails(recipients) {
				if (recipients.length) {
					if (GnuPGUserStore.hasPublicKeyForEmails(recipients)) {
						return 'gnupg';
					}
					if (OpenPGPUserStore.hasPublicKeyForEmails(recipients)) {
						return 'openpgp';
					}
				}
				return false;
			}

			async decrypt(message) {
				const armoredText = message.plain();
				if (!this.isEncrypted(armoredText)) {
					throw Error('Not armored text');
				}

				// Try OpenPGP.js
				if (OpenPGPUserStore.isSupported()) {
					const sender = message.from[0].email;
					let result = await OpenPGPUserStore.decrypt(armoredText, sender);
					if (result) {
						return result;
					}
				}

				// Try Mailvelope (does not support inline images)
				return (await MailvelopeUserStore.decrypt(message))
					// Or try GnuPG
					|| GnuPGUserStore.decrypt(message);
			}

			async verify(message) {
				const signed = message.pgpSigned(),
					sender = message.from[0].email;
				if (signed) {
					// OpenPGP only when inline, else we must download the whole message
					if (!signed.sigPartId && OpenPGPUserStore.hasPublicKeyForEmails([sender])) {
						return OpenPGPUserStore.verify(message);
					}
					if (GnuPGUserStore.hasPublicKeyForEmails([sender])) {
						return GnuPGUserStore.verify(message);
					}
					// Mailvelope can't
					// https://github.com/mailvelope/mailvelope/issues/434
				}
			}

			getPublicKeyOfEmails(recipients) {
				if (recipients.length) {
					let result = {};
					recipients.forEach(email => {
						OpenPGPUserStore.publicKeys().forEach(key => {
							if (key.for(email)) {
								result[email] = key.armor;
							}
						});
						GnuPGUserStore.publicKeys.map(async key => {
							if (!result[email] && key.for(email)) {
								result[email] = await key.fetch();
							}
						});
					});
					return result;
				}
				return false;
			}
		};

	/**
	 * @param string data
	 * @param MessageModel message
	 */
	function MimeToMessage(data, message)
	{
		const struct = ParseMime(data);
		if (struct.headers) {
			let html = struct.getByContentType('text/html'),
				subject = struct.headerValue('subject');
			html = html ? html.body : '';

			// Content-Type: ...; protected-headers="v1"
			subject && message.subject(subject);

			// EmailCollectionModel
			['from','to'].forEach(name => {
				const items = message[name];
				struct.headerValue(name)?.forEach(item => {
					item = new EmailModel(item.email, item.name);
					// Make them unique
					if (item.email && item.name || !items.find(address => address.email == item.email)) {
						items.push(item);
					}
				});
			});

			struct.forEach(part => {
				let cd = part.header('content-disposition'),
					cId = part.header('content-id'),
					type = part.header('content-type');
				if (cId || cd) {
					// if (cd && 'attachment' === cd.value) {
					let attachment = new AttachmentModel;
					attachment.mimeType = type.value;
					attachment.fileName = type.name || (cd && cd.params.filename) || '';
					attachment.fileNameExt = attachment.fileName.replace(/^.+(\.[a-z]+)$/, '$1');
					attachment.fileType = FileInfo.getType('', type.value);
					attachment.url = part.dataUrl;
					attachment.estimatedSize = part.body.length;
	/*
					attachment.contentLocation = '';
					attachment.folder = '';
					attachment.uid = '';
					attachment.mimeIndex = part.id;
	*/
					attachment.cId = cId ? cId.value : '';
					if (cId && html) {
						let cid = 'cid:' + attachment.contentId(),
							found = html.includes(cid);
						attachment.isInline(found);
						attachment.isLinked(found);
						found && (html = html
							.replace('src="' + cid + '"', 'src="' + attachment.url + '"')
							.replace("src='" + cid + "'", "src='" + attachment.url + "'")
						);
					} else {
						message.attachments.push(attachment);
					}
				} else if ('multipart/signed' === type.value) {
					let protocol = type.params.protocol;
					if ('application/pgp-signature' === protocol) {
						message.pgpSigned({
							micAlg: type.micalg,
							bodyPart: part.parts[0],
							sigPart: part.parts[1]
						});
					} else if ('application/pkcs7-signature' === protocol.replace('x-')) {
						message.smimeSigned({
							micAlg: type.micalg,
							bodyPart: part,
							sigPart: part.parts[1], // For importing
							detached: true
						});
					}
				} else if ('application/pkcs7-mime' === type.value /*&& 'signed-data' === type.params['smime-type']=*/) {
					message.smimeSigned({
						micAlg: type.micalg,
						bodyPart: part,
						detached: false
					});
				}
			});

			const text = struct.getByContentType('text/plain');
			message.plain(text ? text.body : '');
			message.html(html);
		} else {
			message.plain(data);
		}

		if (message.plain().includes(BEGIN_PGP_MESSAGE)) {
			message.pgpSigned(true);
		}
	}

	const
		PreviewHTML = `<html>
<head>
	<meta charset="utf-8">
	<title></title>
	<style>
html, body {
	margin: 0;
	padding: 0;
}

header {
	background: rgba(125,128,128,0.3);
	border-bottom: 1px solid #888;
}

header h1 {
	font-size: 120%;
}

header * {
	margin: 5px 0;
}

header time {
	float: right;
}

blockquote {
	border-left: 2px solid rgba(125,128,128,0.5);
	margin: 0;
	padding: 0 0 0 10px;
}

pre {
	white-space: pre-wrap;
	word-wrap: break-word;
	word-break: normal;
}

body > * {
	padding: 0.5em 1em;
}

#attachments > * {
	border: 1px solid rgba(125,128,128,0.5);
	padding: 0.25em;
	margin-right: 1em;
}
#attachments > *::before {
	content: '📎 ';
}
	</style>
</head>
<body></body>
</html>`,

		msgHtml = msg => cleanHtml(msg.html(), msg.attachments(), '#rl-msg-' + msg.hash),

		toggleTag = (message, keyword) => {
			const lower = keyword.toLowerCase(),
				flags = message.flags,
				isSet = flags.includes(lower);
			Remote.request('MessageSetKeyword', iError => {
				if (!iError) {
					isSet ? flags.remove(lower) : flags.push(lower);
				}
			}, {
				folder: message.folder,
				uids: message.uid,
				keyword: keyword,
				setAction: isSet ? 0 : 1
			});
		},

		/**
		 * @param {EmailCollectionModel} emails
		 * @param {Object} unic
		 * @param {Map} localEmails
		 */
		replyHelper = (emails, unic, localEmails) =>
			emails.forEach(email =>
				unic[email.email] || localEmails.has(email.email) || localEmails.set(email.email, email)
			);

	class MessageModel extends AbstractModel {
		constructor() {
			super();

			Object.assign(this, {
				folder: '',
				uid: 0,
				hash: '',
				from: new EmailCollectionModel,
				to: new EmailCollectionModel,
				cc: new EmailCollectionModel,
				bcc: new EmailCollectionModel,
				sender: new EmailCollectionModel,
				replyTo: new EmailCollectionModel,
				deliveredTo: new EmailCollectionModel,
				body: null,
				draftInfo: [],
				dkim: [],
				spf: [],
				dmarc: [],
				messageId: '',
				inReplyTo: '',
				references: '',
	//			autocrypt: ko.observableArray(),
				hasVirus: null, // or boolean when scanned
				priority: 3, // Normal
				senderEmailsString: '',
				senderClearEmailsString: '',
				isSpam: false,
				spamScore: 0,
				spamResult: '',
				size: 0,
				readReceipt: '',
				preview: null,

				attachments: ko.observableArray(new AttachmentCollectionModel),
				threads: ko.observableArray(),
				threadUnseen: ko.observableArray(),
				unsubsribeLinks: ko.observableArray(),
				flags: ko.observableArray(),
				headers: ko.observableArray(new MimeHeaderCollectionModel)
			});

			addObservablesTo(this, {
				subject: '',
				plain: '',
				html: '',
				dateTimestamp: 0,
				dateTimestampSource: 0,

				// Also used by Selector
				focused: false,
				selected: false,
				checked: false,

				isHtml: false,
				hasImages: false,
				hasExternals: false,
				hasTracking: false,

				encrypted: false,

				pgpSigned: null,
				pgpEncrypted: null,
				pgpDecrypted: false,

				smimeSigned: null,
				smimeEncrypted: null,
				smimeDecrypted: false,

				// rfc8621
				id: '',
	//			threadId: ''

				/**
				 * Basic support for Linked Data (Structured Email)
				 * https://json-ld.org/
				 * https://structured.email/
				 **/
				linkedData: []
			});

			addComputablesTo(this, {
				attachmentIconClass: () =>
					this.encrypted() ? 'icon-lock' : FileInfo.getAttachmentsIconClass(this.attachments()),
				threadsLen: () => rl.app.messageList.threadUid() ? 0 : this.threads().length,
				threadUnseenLen: () => rl.app.messageList.threadUid() ? 0 : this.threadUnseen().length,

				threadsLenText: () => {
					const unseenLen = this.threadUnseenLen();
					return this.threadsLen() + (unseenLen > 0 ? '/' + unseenLen : '');
				},

				isUnseen: () => !this.flags().includes('\\seen'),
				isFlagged: () => this.flags().includes('\\flagged'),
				isDeleted: () => this.flags().includes('\\deleted'),
	//			isJunk: () => this.flags().includes('$junk') && !this.flags().includes('$nonjunk'),
	//			isPhishing: () => this.flags().includes('$phishing'),

				tagOptions: () => {
					const tagOptions = [];
					FolderUserStore.currentFolder().optionalTags().forEach(value => {
						let lower = value.toLowerCase();
						tagOptions.push({
							css: 'msgflag-' + lower,
							value: value,
							checked: this.flags().includes(lower),
							label: i18n('MESSAGE_TAGS/'+lower, 0, value),
							toggle: (/*obj*/) => toggleTag(this, value)
						});
					});
					return tagOptions
				},

				whitelistOptions: () => {
					let options = [];
					if ('match' === SettingsUserStore.viewImages()) {
						let from = this.from[0],
							list = SettingsUserStore.viewImagesWhitelist(),
							counts = {};
						this.html().match(/src=["'][^"']+/g)?.forEach(m => {
							m = m.replace(/^.+(:\/\/[^/]+).+$/, '$1');
							if (counts[m]) {
								++counts[m];
							} else {
								counts[m] = 1;
								options.push(m);
							}
						});
						options = options.filter(txt => !list.includes(txt)).sort((a,b) => (counts[a] < counts[b])
							? 1
							: (counts[a] > counts[b] ? -1 : a.localeCompare(b))
						);
						from && options.unshift(from.email);
					}
					return options;
				}
			});

			this.smimeSigned.subscribe(value =>
				value?.body && MimeToMessage(value.body, this)
			);
		}

		get requestHash() {
			return b64EncodeJSONSafe({
				folder: this.folder,
				uid: this.uid,
				mimeType: RFC822,
				fileName: (this.subject() || 'message') + '-' + this.hash + '.eml',
				accountHash: SettingsGet('accountHash')
			});
		}

		toggleTag(keyword) {
			toggleTag(this, keyword);
		}

		spamStatus() {
			let spam = this.spamResult;
			return spam ? i18n(this.isSpam ? 'GLOBAL/SPAM' : 'GLOBAL/NOT_SPAM') + ': ' + spam : '';
		}

		/**
		 * @returns {string}
		 */
		friendlySize() {
			return FileInfo.friendlySize(this.size);
		}

		computeSenderEmail() {
			const list = this[
				[FolderUserStore.sentFolder(), FolderUserStore.draftsFolder()].includes(this.folder) ? 'to' : 'from'
			];
			this.senderEmailsString = list.toString(true);
			this.senderClearEmailsString = list.map(email => email?.email).filter(email => email).join(', ');
		}

		/**
		 * @param {FetchJsonMessage} json
		 * @returns {boolean}
		 */
		revivePropertiesFromJson(json) {
			if (super.revivePropertiesFromJson(json)) {
	//			this.foundCIDs = isArray(json.FoundCIDs) ? json.FoundCIDs : [];
	//			this.attachments(AttachmentCollectionModel.reviveFromJson(json.attachments, this.foundCIDs));
	//			this.headers(MimeHeaderCollectionModel.reviveFromJson(json.headers));

				this.computeSenderEmail();

				let value, headers = this.headers();
	/*			// These could be by Envelope or MIME
				this.messageId = headers.valueByName('Message-Id');
				this.subject(headers.valueByName('Subject'));
				this.sender = EmailCollectionModel.fromString(headers.valueByName('Sender'));
				this.from = EmailCollectionModel.fromArray(headers.valueByName('From'));
				this.replyTo = EmailCollectionModel.fromArray(headers.valueByName('Reply-To'));
				this.to = EmailCollectionModel.fromArray(headers.valueByName('To'));
				this.cc = EmailCollectionModel.fromArray(headers.valueByName('Cc'));
				this.bcc = EmailCollectionModel.fromArray(headers.valueByName('Bcc'));
				this.inReplyTo = headers.valueByName('In-Reply-To');

				this.deliveredTo = EmailCollectionModel.fromString(headers.valueByName('Delivered-To'));
	*/
				// Priority
				value = headers.valueByName('X-MSMail-Priority')
					|| headers.valueByName('Importance')
					|| headers.valueByName('X-Priority');
				if (value) {
					if (/[h12]/.test(value[0])) {
						this.priority = 1;
					} else if (/[l45]/.test(value[0])) {
						this.priority = 5;
					}
				}

				// Unsubscribe links
				if (value = headers.valueByName('List-Unsubscribe')) {
					this.unsubsribeLinks(value.split(',').map(
						link => link.replace(/^[ <>]+|[ <>]+$/g, '')
					));
				}

				if (headers.valueByName('X-Virus')) {
					this.hasVirus = true;
				}
				if (value = headers.valueByName('X-Virus-Status')) {
					if (value.includes('infected')) {
						this.hasVirus = true;
					} else if (value.includes('clean')) {
						this.hasVirus = false;
					}
				}
	/*
				if (value = headers.valueByName('X-Virus-Scanned')) {
					this.virusScanned(value);
				}

				// https://autocrypt.org/level1.html#the-autocrypt-header
				headers.valuesByName('Autocrypt').forEach(value => {
					this.autocrypt.push(new MimeHeaderAutocryptModel(value));
				});
	*/
				return true;
			}
		}

		/**
		 * @return string
		 */
		lineAsCss(flags=1) {
			let classes = [];
			forEachObjectEntry({
				selected: this.selected(),
				checked: this.checked(),
				unseen: this.isUnseen(),
				focused: this.focused(),
				priorityHigh: this.priority === 1,
				withAttachments: !!this.attachments().length,
				// hasChildrenMessage: 1 < this.threadsLen()
			}, (key, value) => value && classes.push(key));
			flags && this.flags().forEach(value => classes.push('msgflag-'+value));
			return classes.join(' ');
		}

		indent() {
			return this.level ? 'margin-left:'+this.level+'em' : null;
		}

		/**
		 * @returns {string}
		 */
		viewRaw() {
			return serverRequestRaw('ViewAsPlain', this.requestHash);
		}

		/**
		 * @returns {string}
		 */
		downloadLink() {
			return serverRequestRaw('Download', this.requestHash);
		}

		/**
		 * @param {Object} excludeEmails
		 * @returns {Array}
		 */
		replyEmails(excludeEmails) {
			const
				result = new Map(),
				unic = excludeEmails || {};
			replyHelper(this.replyTo, unic, result);
			result.size || replyHelper(this.from, unic, result);
			return result.size ? [...result.values()] : [this.to[0]];
		}

		/**
		 * @param {Object} excludeEmails
		 * @returns {Array.<Array>}
		 */
		replyAllEmails(excludeEmails) {
			const
				toResult = new Map(),
				ccResult = new Map(),
				unic = excludeEmails || {};

			replyHelper(this.replyTo, unic, toResult);
			toResult.size || replyHelper(this.from, unic, toResult);

			replyHelper(this.to, unic, toResult);

			replyHelper(this.cc, unic, ccResult);

			return [[...toResult.values()], [...ccResult.values()]];
		}

		viewBody(html) {
			const body = this.body;
			if (body) {
				if (html) {
					let result = msgHtml(this);
					this.hasExternals(result.hasExternals);
					this.hasImages(!!result.hasExternals);
					this.hasTracking(!!result.tracking);
					this.linkedData(result.linkedData);
					body.innerHTML = result.html;
					if (!this.isSpam && FolderUserStore.spamFolder() != this.folder) {
						if ('always' === SettingsUserStore.viewImages()) {
							this.showExternalImages();
						}
						if ('match' === SettingsUserStore.viewImages()) {
							this.showExternalImages(1);
						}
					}
				} else {
					body.innerHTML = plainToHtml(
						(this.plain()
							? this.plain()
								.replace(/-----BEGIN PGP (SIGNED MESSAGE-----(\r?\n[^\r\n]+)+|SIGNATURE-----[\s\S]*)/sg, '')
								.trim()
							: htmlToPlain(body.innerHTML || msgHtml(this).html)
						)
					);
					this.hasImages(false);
				}
				body.classList.toggle('html', html);
				body.classList.toggle('plain', !html);
				this.isHtml(html);
				return true;
			}

		}

		viewHtml() {
			return this.html() && this.viewBody(true);
		}

		viewPlain() {
			return this.viewBody(false);
		}

		swapColors() {
			const cl = this.body?.classList;
			cl && cl.toggle('swapColors');
		}

		/**
		 * @param {boolean=} print = false
		 */
		popupMessage(print) {
			const
				timeStampInUTC = this.dateTimestamp() || 0,
				ccLine = this.cc.toString(),
				bccLine = this.bcc.toString(),
				m = 0 < timeStampInUTC ? new Date(timeStampInUTC * 1000) : null,
				win = open('', 'sm-msg-'+this.requestHash
					,SettingsUserStore.messageNewWindow() ? 'innerWidth=' + elementById('V-MailMessageView').clientWidth : ''
				),
				sdoc = win.document,
				subject = encodeHtml(this.subject()),
				mode = this.isHtml() ? 'div' : 'pre',
				to = `<div>${encodeHtml(i18n('GLOBAL/TO'))}: ${encodeHtml(this.to)}</div>`
					+ (ccLine ? `<div>${encodeHtml(i18n('GLOBAL/CC'))}: ${encodeHtml(ccLine)}</div>` : '')
					+ (bccLine ? `<div>${encodeHtml(i18n('GLOBAL/BCC'))}: ${encodeHtml(bccLine)}</div>` : ''),
				style = getComputedStyle(doc.querySelector('.messageView')),
				prop = property => style.getPropertyValue(property);
			let attachments = '';
			this.attachments.forEach(attachment => {
				attachments += `<a href="${attachment.linkDownload()}">${attachment.fileName}</a>`;
			});
			sdoc.write(PreviewHTML
				.replace('<title>', '<title>'+subject)
				// eslint-disable-next-line max-len
				.replace('<body>', `<body style="background-color:${prop('background-color')};color:${prop('color')}"><header><h1>${subject}</h1><time>${encodeHtml(m ? m.format('LLL',0,LanguageStore.hourCycle()) : '')}</time><div>${encodeHtml(this.from)}</div>${to}</header><${mode}>${this.bodyAsHTML()}</${mode}>`)
				.replace('</body>', `<div id="attachments">${attachments}</div></body>`)
			);
			sdoc.close();
			(true === print) && setTimeout(() => win.print(), 100);
		}

		printMessage() {
			this.popupMessage(true);
		}

		/**
		 * @returns {MessageModel}
		 *//*
		clone() {
			let self = new MessageModel();
			// Clone message values
			forEachObjectEntry(this, (key, value) => {
				if (ko.isObservable(value)) {
					ko.isComputed(value) || self[key](value());
				} else if (!isFunction(value)) {
					self[key] = value;
				}
			});
			self.computeSenderEmail();
			return self;
		}*/

		showExternalImages(regex) {
			const body = this.body;
			if (body && this.hasImages()) {
				if (regex) {
					regex = [];
					SettingsUserStore.viewImagesWhitelist().trim().split(/[\s\r\n,;]+/g).forEach(rule => {
						rule = rule.split('+');
						rule[0] = rule[0].trim();
						if (rule[0]
						 && (!rule.includes('spf') || 'pass' === this.spf[0]?.[0])
						 && (!rule.includes('dkim') || 'pass' === this.dkim[0]?.[0])
						 && (!rule.includes('dmarc') || 'pass' === this.dmarc[0]?.[0])
						) {
							regex.push(rule[0].replace(/[/\-\\^$*+?.()|[\]{}]/g, '\\$&'));
						}
					});
					regex = regex.join('|').replace(/\|+/g, '|');
					if (regex) {
						console.log('whitelist images = '+regex);
						regex = new RegExp(regex);
						if (this.from[0]?.email.match(regex)) {
							regex = null;
						}
					}
				}
				let hasImages = false,
					isValid = src => {
						if (null == regex || (regex && src.match(regex))) {
							return true;
						}
						hasImages = true;
					},
					attr = 'data-x-src',
					src, useProxy = !!SettingsGet('proxyExternalImages');
				body.querySelectorAll('img[' + attr + ']').forEach(node => {
					src = node.getAttribute(attr);
					if (isValid(src)) {
						node.src = useProxy ? proxy(src) : src;
					}
				});

				body.querySelectorAll('[data-x-style-url]').forEach(node => {
					JSON.parse(node.dataset.xStyleUrl).forEach(data => {
						if (isValid(data[1])) {
							node.style[data[0]] = "url('" + (useProxy ? proxy(data[1]) : data[1]) + "')";
						}
					});
				});

				this.hasImages(hasImages);
			}
		}

		/**
		 * @returns {string}
		 */
		bodyAsHTML() {
			if (this.body) {
				let clone = this.body.cloneNode(true);
				clone.querySelectorAll('.sm-bq-switcher').forEach(
					node => node.replaceWith(node.lastElementChild)
				);
				return (clone.querySelector('.mail-body') || clone).innerHTML;
			}
			let result = msgHtml(this);
			return result.html || plainToHtml(this.plain());
		}

	}

	// Fullscreen must be on app, else other popups fail
	const
		appFullscreen = () => (doc.fullscreenElement || doc.webkitFullscreenElement) === appEl,
		exitFullscreen = () => appFullscreen() && (doc.exitFullscreen || doc.webkitExitFullscreen).call(doc),
		isFullscreen = ko.observable(false),
		toggleFullscreen = () => isFullscreen() ? exitFullscreen() : appEl.requestFullscreen();

	if (appEl) {
		let event = 'fullscreenchange';
		if (!appEl.requestFullscreen && appEl.webkitRequestFullscreen) {
			appEl.requestFullscreen = appEl.webkitRequestFullscreen;
			event = 'webkit'+event;
		}
		if (appEl.requestFullscreen) {
			doc.addEventListener(event, () => {
				isFullscreen(appFullscreen());
				$htmlCL.toggle('rl-fullscreen', appFullscreen());
			});
		}
	}

	const MessageUserStore = new class {
		constructor() {
			addObservablesTo(this, {
				// message viewer
				message: null,
				error: '',
				loading: false,

				// Cache mail bodies
				bodiesDom: null
			});

			// Subscribers

			addSubscribablesTo(this, {
				message: message => {
					clearTimeout(this.MessageSeenTimer);
					elementById('rl-right').classList.toggle('message-selected', !!message);
					if (message) {
						SettingsUserStore.usePreviewPane() || AppUserStore.focusedState(ScopeMessageView);
					} else {
						AppUserStore.focusedState(ScopeMessageList);
						exitFullscreen();
					}
					[...(this.bodiesDom()?.children || [])].forEach(el => el.hidden = true);
				},
			});

			this.purgeCache = this.purgeCache.throttle(30000);
		}

		purgeCache(all) {
			const children = this.bodiesDom()?.children || [];
			let i = Math.max(0, children.length - (all ? 0 : 15));
			while (i--) {
				children[i].remove();
				if (children[i].message) {
					children[i].message.body = null;
				}
			}
		}
	};

	class MessageCollectionModel extends AbstractCollectionModel
	{
	/*
		constructor() {
			super();
			this.filtered
			this.folder
			this.totalEmails
			this.totalThreads
			this.threadUid
			this.newMessages
			this.offset
			this.limit
			this.search
			this.limited
		}
	*/

		/**
		 * @param {?Object} json
		 * @returns {MessageCollectionModel}
		 */
		static reviveFromJson(object/*, cached*/) {
			let msg = MessageUserStore.message();
			return super.reviveFromJson(object, message => {
				// If message is currently viewed, use that.
				if (msg && msg.hash === message.hash) {
					msg.revivePropertiesFromJson(message);
					message = msg;
				} else {
					message = MessageModel.reviveFromJson(message);
				}
				return message;
			});
		}
	}

	const AccountUserStore = koArrayWithDestroy();

	addObservablesTo(AccountUserStore, {
		email: '',
		loading: false
	});

	/**
	 * Might not work due to the new ServiceWorkerRegistration.showNotification
	 */
	const HTML5Notification = window.Notification,
		HTML5NotificationStatus = () => HTML5Notification?.permission || 'denied',
		NotificationsDenied = () => 'denied' === HTML5NotificationStatus(),
		NotificationsGranted = () => 'granted' === HTML5NotificationStatus(),
		dispatchMessage = data => {
			focus();
			if (data.folder && data.uid) {
				fireEvent('mailbox.message.show', data);
			} else if (data.Url) {
				hasher.setHash(data.Url);
			}
		};

	let DesktopNotifications = false,
		WorkerNotifications = navigator.serviceWorker;

	// Are Notifications supported in the service worker?
	if (WorkerNotifications) {
		if (ServiceWorkerRegistration && ServiceWorkerRegistration.prototype.showNotification) {
			/* Listen for close requests from the ServiceWorker */
			WorkerNotifications.addEventListener('message', event => {
				const obj = JSON.parse(event.data);
				'notificationclick' === obj?.action && dispatchMessage(obj.data);
			});
		} else {
			console.log('ServiceWorkerRegistration.showNotification undefined');
			WorkerNotifications = null;
		}
	} else {
		console.log('ServiceWorker undefined');
	}

	const NotificationUserStore = new class {
		constructor() {
			addObservablesTo(this, {
				enabled: false,/*.extend({ notify: 'always' })*/
				allowed: !NotificationsDenied()
			});

			this.enabled.subscribe(value => {
				DesktopNotifications = !!value;
				if (value && HTML5Notification && !NotificationsGranted()) {
					HTML5Notification.requestPermission(() =>
						this.allowed(!NotificationsDenied())
					);
				}
			});
		}

		/**
		 * Used with DesktopNotifications setting
		 */
		display(title, text, messageData, imageSrc) {
			if (DesktopNotifications && NotificationsGranted()) {
				const options = {
					body: text,
					icon: imageSrc || staticLink('images/icon-message-notification.png'),
					data: messageData
				};
				if (messageData?.uid) {
					options.tag = messageData.uid;
				}
				if (WorkerNotifications) {
					// Service-Worker-Allowed HTTP header to allow the scope.
					WorkerNotifications.register(staticLink('js/serviceworker.js'), {scope:'/'})
					.then(() =>
						WorkerNotifications.ready.then(registration =>
							/* Show the notification */
							registration
								.showNotification(title, options)
								.then(() =>
									registration.getNotifications().then((/*notifications*/) => {
										/* Send an empty message so the Worker knows who the client is */
										registration.active.postMessage('');
									})
								)
						)
					)
					.catch(e => {
						console.error(e);
						WorkerNotifications = null;
					});
				} else {
					const notification = new HTML5Notification(title, options);
					notification.show?.();
					notification.onclick = messageData ? () => dispatchMessage(messageData) : null;
					setTimeout(() => notification.close(), 7000);
				}
			}
		}
	};

	const
		isChecked = item => item.checked(),
		isDeleted = item => item.isDeleted(),
		replaceHash = hash => {
			rl.route.off();
			hasher.replaceHash(hash);
			rl.route.on();
		},
		disableAutoSelect = ko.observable(false).extend({ falseTimeout: 500 });

	const MessagelistUserStore = ko.observableArray().extend({ debounce: 0 });

	addObservablesTo(MessagelistUserStore, {
		count: 0,
		listSearch: '',
		listLimited: 0,
		threadUid: 0,
		page: 1,
		pageBeforeThread: 1,
		error: '',
	//	folder: '',

		endHash: '',
		endThreadUid: 0,

		loading: false,
		// Happens when message(s) removed from list
		isIncomplete: false,

		selectedMessage: null,
		focusedMessage: null
	});

	// Computed Observables

	addComputablesTo(MessagelistUserStore, {
		isLoading: () => {
			const value = MessagelistUserStore.loading() | MessagelistUserStore.isIncomplete();
			$htmlCL.toggle('list-loading', value);
			return value;
		},

		isArchiveFolder: () => FolderUserStore.archiveFolder() === MessagelistUserStore().folder,

		isDraftFolder: () => FolderUserStore.draftsFolder() === MessagelistUserStore().folder,

		isSentFolder: () => FolderUserStore.sentFolder() === MessagelistUserStore().folder,

		isSpamFolder: () => FolderUserStore.spamFolder() === MessagelistUserStore().folder,

		isTrashFolder: () => FolderUserStore.trashFolder() === MessagelistUserStore().folder,

		archiveAllowed: () => ![UNUSED_OPTION_VALUE, MessagelistUserStore().folder].includes(FolderUserStore.archiveFolder())
			&& !MessagelistUserStore.isDraftFolder(),

		canMarkAsSpam: () => !(UNUSED_OPTION_VALUE === FolderUserStore.spamFolder()
	//		| MessagelistUserStore.isArchiveFolder()
			| MessagelistUserStore.isSentFolder()
			| MessagelistUserStore.isDraftFolder()
			| MessagelistUserStore.isSpamFolder()),

		pageCount: () => Math.max(1, Math.ceil(MessagelistUserStore.count() / SettingsUserStore.messagesPerPage())),

		mainSearch: {
			read: MessagelistUserStore.listSearch,
			write: value => hasher.setHash(
				mailBox(FolderUserStore.currentFolderFullNameHash(), 1,
					value.toString().trim(), MessagelistUserStore.threadUid())
			)
		},

		listCheckedOrSelected: () => {
			const
				selectedMessage = MessagelistUserStore.selectedMessage(),
				checked = MessagelistUserStore.filter(item => isChecked(item));
			return checked.length ? checked : (selectedMessage ? [selectedMessage] : []);
		},

		listCheckedOrSelectedUidsWithSubMails: () => {
			let result = new Set;
			MessagelistUserStore.listCheckedOrSelected().forEach(message => {
				result.add(message.uid);
				result.folder = message.folder;
				if (1 < message.threadsLen()) {
					message.threads().forEach(result.add, result);
				}
			});
			return result;
		}
	});

	MessagelistUserStore.listChecked = koComputable(
		() => MessagelistUserStore.filter(isChecked)
	).extend({ rateLimit: 0 });

	// Also used by Selector
	MessagelistUserStore.hasChecked = koComputable(
		// Issue: not all are observed?
		() => !!MessagelistUserStore.find(isChecked)
	).extend({ rateLimit: 0 });

	MessagelistUserStore.hasCheckedOrSelected = koComputable(() =>
		!!MessagelistUserStore.selectedMessage()
		// Issue: not all are observed?
		| !!MessagelistUserStore.find(isChecked)
	).extend({ rateLimit: 50 });

	MessagelistUserStore.hasCheckedOrSelectedAndDeleted = koComputable(
		() => !!MessagelistUserStore.listCheckedOrSelected().find(isDeleted)
	).extend({ rateLimit: 50 });

	MessagelistUserStore.hasCheckedOrSelectedAndUndeleted = koComputable(
		() => !!MessagelistUserStore.listCheckedOrSelected().find(item => !item?.isDeleted())
	).extend({ rateLimit: 50 });

	MessagelistUserStore.notifyNewMessages = (folder, newMessages) => {
		if (getFolderInboxName() === folder && arrayLength(newMessages)) {

			SMAudio.playNotification();

			const len = newMessages.length;
			if (3 < len) {
				NotificationUserStore.display(
					AccountUserStore.email(),
					i18n('MESSAGE_LIST/NEW_MESSAGE_NOTIFICATION', {
						COUNT: len
					}),
					{ Url: mailBox(newMessages[0].folder) }
				);
			} else {
				newMessages.forEach(item => {
					NotificationUserStore.display(
						EmailCollectionModel.reviveFromJson(item.from).toString(),
						item.subject,
						{ folder: item.folder, uid: item.uid }
					);
				});
			}
		}
	};

	MessagelistUserStore.canSelect = () =>
		!disableAutoSelect()
		&& SettingsUserStore.usePreviewPane();
	//	&& !SettingsUserStore.showNextMessage();

	let prevFolderName;

	/**
	 * @param {boolean=} bDropPagePosition = false
	 * @param {boolean=} bDropCurrentFolderCache = false
	 */
	MessagelistUserStore.reload = (bDropPagePosition = false, bDropCurrentFolderCache = false) => {
		let iOffset = (MessagelistUserStore.page() - 1) * SettingsUserStore.messagesPerPage(),
			folderName = FolderUserStore.currentFolderFullName();
	//		folderName = FolderUserStore.currentFolder() ? self.currentFolder().fullName : '');

		if (bDropCurrentFolderCache) {
			setFolderETag(folderName, '');
		}

		if (bDropPagePosition) {
			MessagelistUserStore.page(1);
			MessagelistUserStore.pageBeforeThread(1);
			iOffset = 0;

			replaceHash(
				mailBox(
					FolderUserStore.currentFolderFullNameHash(),
					MessagelistUserStore.page(),
					MessagelistUserStore.listSearch(),
					MessagelistUserStore.threadUid()
				)
			);
		}

		if (prevFolderName != folderName) {
			prevFolderName = folderName;
			MessagelistUserStore([]);
		}

		MessagelistUserStore.loading(true);

		let sGetAdd = '',
	//		folder = getFolderFromCacheList(folderName.fullName),
			folder = getFolderFromCacheList(folderName),
			folderETag = folder?.etag || '',
			params = {
				folder: folderName,
				offset: iOffset,
				limit: SettingsUserStore.messagesPerPage(),
				uidNext: folder?.uidNext || 0, // Used to check for new messages
				sort: FolderUserStore.sortMode(),
				search: MessagelistUserStore.listSearch()
			},
			fCallback = (iError, oData, bCached) => {
				let error = '';
				if (iError) {
					if ('reload' != oData?.name) {
						error = getNotification(iError);
						MessagelistUserStore.loading(false);
	//					if (Notifications.RequestAborted !== iError) {
	//						MessagelistUserStore([]);
	//					}
	//					if (oData.message) { error = oData.message + error; }
					}
				} else {
					const collection = MessageCollectionModel.reviveFromJson(oData.Result, bCached);
					if (collection) {
						const
							folderInfo = collection.folder,
							folder = getFolderFromCacheList(folderInfo.name);
						collection.folder = folderInfo.name;
						if (folder && !bCached) {
	//						folder.revivePropertiesFromJson(result);
							folder.expires = Date.now();
							folder.uidNext = folderInfo.uidNext;
							folder.etag = folderInfo.etag;

							if (null != folderInfo.totalEmails) {
								folder.totalEmails(folderInfo.totalEmails);
							}

							if (null != folderInfo.unreadEmails) {
								folder.unreadEmails(folderInfo.unreadEmails);
							}

							let flags = folderInfo.permanentFlags || [];
							if (flags.includes('\\*')) {
								/** Add Thunderbird labels */
								let i = 6;
								while (--i) {
									flags.includes('$label'+i) || flags.push('$label'+i);
								}
								/** TODO: add others by default? */
							}
							folder.permanentFlags(flags.sort(baseCollator().compare));

							MessagelistUserStore.notifyNewMessages(folder.fullName, collection.newMessages);
						}

						MessagelistUserStore.count(collection.totalEmails);
						MessagelistUserStore.listSearch(pString(collection.search));
						MessagelistUserStore.listLimited(!!collection.limited);
						MessagelistUserStore.page(Math.ceil(collection.offset / SettingsUserStore.messagesPerPage() + 1));
						MessagelistUserStore.threadUid(collection.threadUid);

						MessagelistUserStore.endHash(
							folderInfo.name +
							'|' + collection.search +
							'|' + MessagelistUserStore.threadUid() +
							'|' + MessagelistUserStore.page()
						);
						MessagelistUserStore.endThreadUid(collection.threadUid);
						const message = MessageUserStore.message();
						if (message && folderInfo.name !== message.folder) {
							MessageUserStore.message(null);
						}

						disableAutoSelect(true);

						if (collection.threadUid) {
							let refs = {};
							collection.forEach(msg => {
								msg.level = 0;
								if (msg.inReplyTo && refs[msg.inReplyTo]) {
									msg.level = 1 + refs[msg.inReplyTo].level;
								}
								refs[msg.messageId] = msg;
							});
						}

						MessagelistUserStore(collection);
						MessagelistUserStore.isIncomplete(false);
					} else {
						MessagelistUserStore.count(0);
						MessagelistUserStore([]);
						error = getNotification(Notifications.CantGetMessageList);
					}
					MessagelistUserStore.loading(false);
				}
				MessagelistUserStore.error(error);
			};

		if (AppUserStore.threadsAllowed() && SettingsUserStore.useThreads()) {
			params.useThreads = 1;
			params.threadAlgorithm = SettingsUserStore.threadAlgorithm();
			params.threadUid = MessagelistUserStore.threadUid();
		} else {
			params.threadUid = 0;
		}
		if (folderETag) {
			params.hash = folderETag + '-' + SettingsGet('accountHash');
			sGetAdd = 'MessageList/' + SUB_QUERY_PREFIX + '/' + b64EncodeJSONSafe(params);
			params = {};
		}

		Remote.abort('MessageList', 'reload').request('MessageList',
			fCallback,
			params,
			60000, // 60 seconds before aborting
			sGetAdd
		);
	};

	/**
	 * @param {string} sFolderFullName
	 * @param {number} iSetAction
	 * @param {Array=} messages = null
	 */
	MessagelistUserStore.setAction = (sFolderFullName, iSetAction, messages) => {
		messages = messages || MessagelistUserStore.listChecked();

		let folder,
			rootUids = [],
			length;

		if (iSetAction == MessageSetAction.SetSeen) {
			messages.forEach(oMessage => {
				if (oMessage.isUnseen() && rootUids.push(oMessage.uid)) {
					oMessage.flags.push('\\seen');
					if (oMessage.threads().length > 0 && oMessage.threadUnseen().includes(oMessage.uid)) {
						oMessage.threadUnseen.remove(oMessage.uid);
					}
				}
			});
		} else if (iSetAction == MessageSetAction.UnsetSeen) {
			messages.forEach(oMessage => {
				if (!oMessage.isUnseen() && rootUids.push(oMessage.uid)) {
					oMessage.flags.remove('\\seen');
					if (oMessage.threads().length > 0 && !oMessage.threadUnseen().includes(oMessage.uid)) {
						oMessage.threadUnseen.push(oMessage.uid);
					}
				}
			});
		} else if (iSetAction == MessageSetAction.SetFlag) {
			messages.forEach(oMessage =>
				!oMessage.isFlagged() && rootUids.push(oMessage.uid) && oMessage.flags.push('\\flagged')
			);
		} else if (iSetAction == MessageSetAction.UnsetFlag) {
			messages.forEach(oMessage =>
				oMessage.isFlagged() && rootUids.push(oMessage.uid) && oMessage.flags.remove('\\flagged')
			);
		} else if (iSetAction == MessageSetAction.SetDeleted) {
			messages.forEach(oMessage =>
				!oMessage.isDeleted() && rootUids.push(oMessage.uid) && oMessage.flags.push('\\deleted')
			);
		} else if (iSetAction == MessageSetAction.UnsetDeleted) {
			messages.forEach(oMessage =>
				oMessage.isDeleted() && rootUids.push(oMessage.uid) && oMessage.flags.remove('\\deleted')
			);
		}
		rootUids = rootUids.validUnique();
		length = rootUids.length;

		if (sFolderFullName && length) {
			switch (iSetAction) {
				case MessageSetAction.SetSeen:
					length = -length;
					// fallthrough is intentionally
				case MessageSetAction.UnsetSeen:
					folder = getFolderFromCacheList(sFolderFullName);
					if (folder) {
						folder.unreadEmails(Math.max(0, folder.unreadEmails() + length));
					}
					Remote.request('MessageSetSeen', null, {
						folder: sFolderFullName,
						uids: rootUids.join(','),
						setAction: iSetAction == MessageSetAction.SetSeen ? 1 : 0
					});
					break;

				case MessageSetAction.SetFlag:
				case MessageSetAction.UnsetFlag:
					Remote.request('MessageSetFlagged', null, {
						folder: sFolderFullName,
						uids: rootUids.join(','),
						setAction: iSetAction == MessageSetAction.SetFlag ? 1 : 0
					});
					break;

				case MessageSetAction.SetDeleted:
				case MessageSetAction.UnsetDeleted:
					Remote.request('MessageSetDeleted', null, {
						folder: sFolderFullName,
						uids: rootUids.join(','),
						setAction: iSetAction == MessageSetAction.SetDeleted ? 1 : 0
					});
					break;
				// no default
			}
		}
	};

	/**
	 * @param {string} fromFolderFullName
	 * @param {Set} oUids
	 * @param {string=} toFolderFullName = ''
	 * @param {boolean=} copy = false
	 */
	MessagelistUserStore.moveMessages = (
		fromFolderFullName, oUids, toFolderFullName = '', copy = false
	) => {
		const fromFolder = getFolderFromCacheList(fromFolderFullName);

		if (!fromFolder || !oUids?.size) return;

		let unseenCount = 0,
			setPage = 0,
			currentMessage = MessageUserStore.message();

		const toFolder = toFolderFullName ? getFolderFromCacheList(toFolderFullName) : null,
			trashFolder = FolderUserStore.trashFolder(),
			spamFolder = FolderUserStore.spamFolder(),
			page = MessagelistUserStore.page(),
			messages =
				FolderUserStore.currentFolderFullName() === fromFolderFullName
					? MessagelistUserStore.filter(item => item && oUids.has(item.uid))
					: [],
			moveOrDeleteResponseHelper = (iError, oData) => {
				if (iError) {
					setFolderETag(FolderUserStore.currentFolderFullName(), '');
					alert(getNotification(iError));
				} else if (FolderUserStore.currentFolder()) {
					if (2 === arrayLength(oData.Result)) {
						setFolderETag(oData.Result[0], oData.Result[1]);
					} else {
						setFolderETag(FolderUserStore.currentFolderFullName(), '');
					}

					MessagelistUserStore.count(MessagelistUserStore.count() - oUids.size);
					if (page > MessagelistUserStore.pageCount()) {
						setPage = MessagelistUserStore.pageCount();
					}
					if (setPage) {
						MessagelistUserStore.page(setPage);
						replaceHash(
							mailBox(
								FolderUserStore.currentFolderFullNameHash(),
								setPage,
								MessagelistUserStore.listSearch(),
								MessagelistUserStore.threadUid()
							)
						);
					}

					MessagelistUserStore.reload(!MessagelistUserStore.count());
				}
			};

		messages.forEach(item => item?.isUnseen() && ++unseenCount);

		if (!copy) {
			fromFolder.etag = '';
			fromFolder.totalEmails(Math.max(0, fromFolder.totalEmails() - oUids.size));
			fromFolder.unreadEmails(Math.max(0, fromFolder.unreadEmails() - unseenCount));
		}

		if (toFolder) {
			toFolder.etag = '';
			toFolder.totalEmails(toFolder.totalEmails() + oUids.size);
			if (trashFolder !== toFolder.fullName && spamFolder !== toFolder.fullName) {
				toFolder.unreadEmails(toFolder.unreadEmails() + unseenCount);
			}
			toFolder.actionBlink(true);
		}

		if (messages.length) {
			disableAutoSelect(true);
			if (copy) {
				messages.forEach(item => item.checked(false));
			} else {
				MessagelistUserStore.isIncomplete(true);

				// Select next email https://github.com/the-djmaze/snappymail/issues/968
				if (currentMessage && 1 == messages.length && SettingsUserStore.showNextMessage()) {
					let next = MessagelistUserStore.indexOf(currentMessage) + 1;
					if (0 < next && (next = MessagelistUserStore()[next])) {
						currentMessage = null;
						fireEvent('mailbox.message.show', {
							folder: next.folder,
							uid: next.uid
						});
					}
				}

				messages.forEach(item => {
					if (currentMessage && currentMessage.hash === item.hash) {
						currentMessage = null;
						MessageUserStore.message(null);
					}
					MessagelistUserStore.remove(item);
				});
			}
		}

		if (toFolderFullName) {
			if (toFolder && fromFolderFullName != toFolderFullName) {
				const params =  {
					fromFolder: fromFolderFullName,
					toFolder: toFolderFullName,
					uids: [...oUids].join(',')
				};
				if (copy) {
					Remote.request('MessageCopy', null, params);
				} else {
					const
						isSpam = spamFolder === toFolderFullName,
						isHam = !isSpam && spamFolder === fromFolderFullName && getFolderInboxName() === toFolderFullName;
					params.markAsRead = (isSpam || FolderUserStore.trashFolder() === toFolderFullName) ? 1 : 0;
					params.learning = isSpam ? 'SPAM' : isHam ? 'HAM' : '';
					Remote.abort('MessageList', 'reload').request('MessageMove', moveOrDeleteResponseHelper, params);
				}
			}
		} else {
			Remote.abort('MessageList', 'reload').request('MessageDelete',
				moveOrDeleteResponseHelper,
				{
					folder: fromFolderFullName,
					uids: [...oUids].join(',')
				}
			);
		}
	};

	let refreshInterval,
		// Default every 15 minutes
		refreshFoldersInterval = 900000;

	const

	setRefreshFoldersInterval = minutes => {
		refreshFoldersInterval = Math.max(1, pInt(SettingsGet('minRefreshInterval')), pInt(minutes)) * 60000;
		clearInterval(refreshInterval);
		refreshInterval = setInterval(() => {
			const cF = FolderUserStore.currentFolderFullName(),
				iF = getFolderInboxName();
			folderInformation(iF);
			iF === cF || folderInformation(cF);
			folderInformationMultiply();
		}, refreshFoldersInterval);
	},

	sortFolders = folders => {
		try {
			let collator = baseCollator(true);
			folders.sort((a, b) =>
				a.isInbox() ? -1 : (b.isInbox() ? 1 : collator.compare(a.fullName, b.fullName))
			);
		} catch (e) {
			console.error(e);
		}
	},

	/**
	 * @param {Array=} aDisabled
	 * @param {Array=} aHeaderLines
	 * @param {Function=} fRenameCallback
	 * @param {Function=} fDisableCallback
	 * @param {boolean=} bNoSelectSelectable Used in FolderCreatePopupView
	 * @returns {Array}
	 */
	folderListOptionsBuilder = (
		aDisabled,
		aHeaderLines,
		fRenameCallback,
		fDisableCallback
	) => {
		const
			aResult = [],
			sDeepPrefix = '\u00A0\u00A0\u00A0',
			// FolderSystemPopupView should always be true
			showUnsubscribed = fRenameCallback ? !SettingsUserStore.hideUnsubscribed() : true,
			isDisabled = fDisableCallback || (item => !item.selectable() || aDisabled.includes(item.fullName)),

			foldersWalk = folders => {
				folders.forEach(oItem => {
					if (showUnsubscribed || oItem.hasSubscriptions() || !oItem.exists) {
						aResult.push({
							id: oItem.fullName,
							name:
								sDeepPrefix.repeat(oItem.deep) +
								fRenameCallback(oItem),
							system: false,
							disabled: isDisabled(oItem)
						});
					}
					foldersWalk(oItem.subFolders());
				});
			};


		fDisableCallback = fDisableCallback || (() => false);
		fRenameCallback = fRenameCallback || (oItem => oItem.name());
		isArray(aDisabled) || (aDisabled = []);

		isArray(aHeaderLines) && aHeaderLines.forEach(line =>
			aResult.push({
				id: line[0],
				name: line[1],
				system: false,
				disabled: false
			})
		);

		foldersWalk(FolderUserStore.folderList());

		return aResult;
	},

	/**
	 * @param {string} folder
	 * @param {Array=} list = []
	 */
	folderInformation = (folder, list) => {
		if (folder?.trim()) {
			let count = 1;
			const uids = [];

			if (arrayLength(list)) {
				list.forEach(messageListItem => {
					uids.push(messageListItem.uid);
					messageListItem.threads.forEach(uid => uids.push(uid));
				});
				count = uids.length;
			}

			if (count) {
				Remote.request('FolderInformation', (iError, data) => {
					if (!iError && data.Result) {
						const result = data.Result,
							folderFromCache = getFolderFromCacheList(result.name);
						if (folderFromCache) {
							const oldHash = folderFromCache.etag,
								unreadCountChange = (folderFromCache.unreadEmails() !== result.unreadEmails);

	//						folderFromCache.revivePropertiesFromJson(result);
							folderFromCache.expires = Date.now();
							folderFromCache.uidNext = result.uidNext;
							folderFromCache.etag = result.etag;
							folderFromCache.totalEmails(result.totalEmails);
							folderFromCache.unreadEmails(result.unreadEmails);

							MessagelistUserStore.notifyNewMessages(folderFromCache.fullName, result.newMessages);

							if (!oldHash || unreadCountChange || result.etag !== oldHash) {
								if (folderFromCache.fullName === FolderUserStore.currentFolderFullName()) {
									MessagelistUserStore.reload();
	/*
								} else if (getFolderInboxName() === folderFromCache.fullName) {
	//								Remote.messageList(null, {folder: getFolderFromCacheList(getFolderInboxName())}, true);
									Remote.messageList(null, {folder: getFolderInboxName()}, true);
	*/
								}
							}
						}
					}
				}, {
					folder: folder,
					flagsUids: uids,
					uidNext: getFolderFromCacheList(folder)?.uidNext || 0 // Used to check for new messages
				});
			}
		}
	},

	/**
	 * @param {boolean=} boot = false
	 */
	folderInformationMultiply = (boot = false) => {
		const folders = FolderUserStore.getNextFolderNames(refreshFoldersInterval);
		if (arrayLength(folders)) {
			Remote.request('FolderInformationMultiply', (iError, oData) => {
				if (!iError && arrayLength(oData.Result)) {
					const utc = Date.now();
					oData.Result.forEach(item => {
						const folder = getFolderFromCacheList(item.name);
						if (folder) {
							const oldHash = folder.etag,
								unreadCountChange = folder.unreadEmails() !== item.unreadEmails;

	//						folder.revivePropertiesFromJson(item);
							folder.expires = utc;
							folder.etag = item.etag;
							folder.totalEmails(item.totalEmails);
							folder.unreadEmails(item.unreadEmails);

							if (!oldHash || item.etag !== oldHash) {
								if (folder.fullName === FolderUserStore.currentFolderFullName()) {
									MessagelistUserStore.reload();
								}
							} else if (unreadCountChange
							 && folder.fullName === FolderUserStore.currentFolderFullName()
							 && MessagelistUserStore.length) {
								folderInformation(folder.fullName, MessagelistUserStore());
							}
						}
					});

					boot && setTimeout(() => folderInformationMultiply(true), 2000);
				}
			}, {
				folders: folders
			});
		}
	},

	dropFilesInFolder = (sFolderFullName, files) => {
		let count = files.length;
		for (const file of files) {
			if (RFC822 === file.type) {
				let data = new FormData;
				data.append('folder', sFolderFullName);
				data.append('appendFile', file);
				Remote.request('FolderAppend', (iError, data)=>{
					iError && console.error(data.message);
					0 == --count
					&& FolderUserStore.currentFolderFullName() == sFolderFullName
					&& MessagelistUserStore.reload(true, true);
				}, data);
			} else {
				--count;
			}
		}
	};

	const
		win = window,
		CLIENT_SIDE_STORAGE_INDEX_NAME = 'rlcsc',
		sName = 'localStorage',
		getStorage = () => {
			try {
				const value = localStorage.getItem(CLIENT_SIDE_STORAGE_INDEX_NAME);
				return value ? JSON.parse(value) : null;
			} catch (e) {
				return null;
			}
		};

	// Storage
	try {
		win[sName].setItem(sName, '');
		win[sName].getItem(sName);
		win[sName].removeItem(sName);
	} catch (e) {
		console.error(e);
		// initialise if there's already data
		let data = document.cookie.match(/(^|;) ?localStorage=([^;]+)/);
		data = data ? decodeURIComponent(data[2]) : null;
		data = data ? JSON.parse(data) : {};
		win[sName] = {
			getItem: key => data[key] ?? null,
			setItem: (key, value) => {
				data[key] = ''+value; // forces the value to a string
				document.cookie = sName+'='+encodeURIComponent(JSON.stringify(data))
					+";expires="+((new Date(Date.now()+(365*24*60*60*1000))).toGMTString())
					+";path=/;samesite=strict";
			}
		};
	}

	/**
	 * @param {number} key
	 * @param {*} data
	 * @returns {boolean}
	 */
	function set(key, data) {
		const storageResult = getStorage() || {};
		storageResult['p' + key] = data;

		try {
			localStorage.setItem(CLIENT_SIDE_STORAGE_INDEX_NAME, JSON.stringify(storageResult));
			return true;
		} catch (e) {
			return false;
		}
	}

	/**
	 * @param {number} key
	 * @returns {*}
	 */
	function get(key) {
		try {
			return (getStorage() || {})['p' + key];
		} catch (e) {
			return null;
		}
	}

	class FolderACLPopupView extends AbstractViewPopup {
		constructor() {
			super('FolderACL');
			addObservablesTo(this, {
				create: false,
				mine: false,
				folderName: '',
				identifier: ''
			});
			this.rights = ko.observableArray();
		}

		submitForm(/*form*/) {
			if (!this.mine()) {
				const rights = this.rights();
				Remote.request('FolderSetACL',
					(iError, data) => {
						if (!iError && data.Result) {
							const acl = this.acl;
							if (!acl.identifier) {
								this.folder.ACL.push(acl);
							}
							acl.rights = rights;
						}
					}, {
						folder: this.folderName(),
						identifier: this.identifier(),
						rights: rights.join('')
					}
				);
			}
			this.close();
		}

		beforeShow(folder, acl) {
			this.folder = folder;
			this.create(!acl.identifier());
			this.mine(acl.mine());
			this.acl = acl;
	/*
			this.ACLAllowed && Remote.request('FolderIdentifierRights', (iError, data) => {
				if (!iError && data.Result) {
					this.rights(data.Result.rights.split(''));
				}
			}, {
				folder: folder.fullName,
				identifier: acl.identifier
			});
	*/
			this.folderName(folder.fullName);
			this.identifier(acl.identifier());
			this.rights(acl.rights());
		}
	}

	class FolderACLModel extends AbstractCollectionModel
	{
		static reviveFromJson(json) {
			return super.reviveFromJson(json, rights => FolderACLRightsModel.reviveFromJson(rights));
		}
	}
	class FolderACLRightsModel extends AbstractModel {
		constructor() {
			super();
			addObservablesTo(this, {
				identifier: '',
				mine: false
			});
			// The "RIGHTS=" capability MUST NOT include any of the rights defined in RFC 2086.
			// That way we know it supports RFC 4314
	//		this.rights = ko.observableArray(/*'alrswipcd'.split('')*/);
			this.rights = ko.observableArray(/*'alrswipkxte'.split('')*/);
		}

		static reviveFromJson(json) {
			json.rights = json.rights.split('');
			return super.reviveFromJson(json);
		}
	/*
		get mayReadItems()   { return this.rights.includes('l') && this.rights.includes('r'); }
		get mayAddItems()    { return this.rights.includes('i'); }
		get mayRemoveItems() { return this.rights.includes('t') && this.rights.includes('e'); }
		get maySetSeen()     { return this.rights.includes('s'); }
		get maySetKeywords() { return this.rights.includes('w'); }
		get mayCreateChild() { return this.rights.includes('k'); }
		get mayRename()      { return this.rights.includes('x'); }
		get mayDelete()      { return this.rights.includes('x'); }
		get maySubmit()      { return this.rights.includes('p'); }
	*/
	}

	class FolderPopupView extends AbstractViewPopup {
		constructor() {
			super('Folder');
			addObservablesTo(this, {
				folder: null, // FolderModel
				parentFolder: '',
				name: '',
				editing: false,
				adminACL: false
			});
			this.ACLAllowed = FolderUserStore.hasCapability('ACL');

			this.parentFolderSelectList = koComputable(() =>
				folderListOptionsBuilder(
					[],
					[['', '']],
					oItem => oItem ? oItem.detailedName() : '',
					item => !item.subFolders.allow
						|| (FolderUserStore.namespace && !item.fullName.startsWith(FolderUserStore.namespace))
				)
			);

			this.displaySpecSetting = FolderUserStore.displaySpecSetting;

			this.showKolab = FolderUserStore.allowKolab();
			this.kolabTypeOptions = ko.observableArray();
			let i18nFilter = key => i18n('SETTINGS_FOLDERS/TYPE_' + key);
			initOnStartOrLangChange(()=>{
				this.kolabTypeOptions([
					{ id: '', name: '' },
					{ id: 'event', name: i18nFilter('CALENDAR') },
					{ id: 'contact', name: i18nFilter('CONTACTS') },
					{ id: 'task', name: i18nFilter('TASKS') },
					{ id: 'note', name: i18nFilter('NOTES') },
					{ id: 'file', name: i18nFilter('FILES') },
					{ id: 'journal', name: i18nFilter('JOURNAL') },
					{ id: 'configuration', name: i18nFilter('CONFIGURATION') }
				]);
			});

			this.defaultOptionsAfterRender = defaultOptionsAfterRender;
			this.editACL = this.editACL.bind(this);
			this.deleteACL = this.deleteACL.bind(this);
		}

		afterHide() {
			this.editing(false);
		}

		submitForm(/*form*/) {
			const
				folder = this.folder(),
				nameToEdit = this.name().trim(),
				newParentName = this.parentFolder(),
				oldParent = getFolderFromCacheList(folder.parentName),
				newParent = getFolderFromCacheList(newParentName),
				folderList = FolderUserStore.folderList,
				newFolderList = newParent ? newParent.subFolders : folderList,
				delimiter = (newParent || folder).delimiter,
				oldFullname = folder.fullName,
				newFullname = (newParent ? newParentName + delimiter : '') + nameToEdit;
			if (nameToEdit && newFullname != oldFullname) {
				Remote.abort('Folders').post('FolderRename', FolderUserStore.foldersRenaming, {
					oldName: oldFullname,
					newName: newFullname,
					// toggleFolderSubscription / FolderSubscribe
					subscribe: folder.isSubscribed() ? 1 : 0,
					// toggleFolderCheckable / FolderCheckable
					checkable: folder.checkable() ? 1 : 0,
					// toggleFolderKolabType / FolderSetMetadata
					kolab: {
						// TODO: append '.default' ?
						type: FolderMetadataKeys.KolabFolderType,
						value: folder.kolabType()
					}
				})
				.then(() => {
					const
						renameFolder = (folder, parent) => {
							removeFolderFromCacheList(folder.fullName);
							folder.parentName = (parent ? parent.fullName : '');
							folder.fullName = (parent ? parent.fullName + delimiter : '') + folder.name();
							folder.delimiter = delimiter;
							folder.deep = (parent ? parent.deep : -1) + 1;
							setFolder(folder);
						},
						renameChildren = folder => {
							folder.subFolders.forEach(child => {
								renameFolder(child, folder);
								renameChildren(child);
							});
						};
					folder.name(nameToEdit);
					renameFolder(folder, newParent);
					if (folder.subFolders.length || newParent != oldParent) {
						// Rename all subfolders to prevent reload
						renameChildren(folder);
					}
					(oldParent ? oldParent.subFolders : folderList).remove(folder);
					newFolderList.push(folder);
					sortFolders(newFolderList);
				})
				.catch(error => {
					console.error(error);
					FolderUserStore.error(
						getNotification(error.code, '', Notifications.CantRenameFolder) + '.\n' + error.message
					);
				});
			} else {
				Remote.request('FolderSettings', null, {
					folder: folder.fullName,
					// toggleFolderSubscription / FolderSubscribe
					subscribe: folder.isSubscribed() ? 1 : 0,
					// toggleFolderCheckable / FolderCheckable
					checkable: folder.checkable() ? 1 : 0,
					// toggleFolderKolabType / FolderSetMetadata
					kolab: {
						// TODO: append '.default' ?
						type: FolderMetadataKeys.KolabFolderType,
						value: folder.kolabType()
					}
				});
			}

			this.close();
		}

		createACL()
		{
			showScreenPopup(FolderACLPopupView, [this.folder(), new FolderACLRightsModel]);
		}

		editACL(acl)
		{
			showScreenPopup(FolderACLPopupView, [this.folder(), acl]);
		}

		deleteACL(acl)
		{
			Remote.request('FolderDeleteACL',
				(iError, data) => !iError && data.Result && this.folder().ACL.remove(acl),
				{
					folder: this.folder().fullName,
					identifier: acl.identifier
				}
			);
		}

		beforeShow(folder) {
			folder.ACL || (folder.ACL = ko.observableArray());
			this.adminACL(false);
			this.ACLAllowed && Remote.request('FolderACL', (iError, data) => {
				if (!iError && data.Result) {
					folder.ACL(FolderACLModel.reviveFromJson(data.Result));
	//				data.Result.map(aItem => FolderACLRightsModel.reviveFromJson(aItem)).filter(v => v)
					this.adminACL(folder.ACL()[0].rights.includes('a'));
				}
			}, {
				folder: folder.fullName
			});
			this.editing(!folder.type() && folder.exists && folder.selectable());
			this.name(folder.name()),
			this.parentFolder(folder.parentName);
			this.folder(folder);
		}
	}

	const
	//	isPosNumeric = value => null != value && /^[0-9]*$/.test(value.toString()),

		normalizeFolder = sFolderFullName => ('' === sFolderFullName
			|| UNUSED_OPTION_VALUE === sFolderFullName
			|| null !== getFolderFromCacheList(sFolderFullName))
				? sFolderFullName
				: '',

		SystemFolders = {
			Inbox:   0,
			Sent:    0,
			Drafts:  0,
			Junk:    0, // Spam
			Trash:   0,
			Archive: 0
		},

		kolabTypes = {
			configuration: 'CONFIGURATION',
			event: 'CALENDAR',
			contact: 'CONTACTS',
			task: 'TASKS',
			note: 'NOTES',
			file: 'FILES',
			journal: 'JOURNAL'
		},

		getKolabFolderName = type => kolabTypes[type] ? 'Kolab ' + i18n('SETTINGS_FOLDERS/TYPE_' + kolabTypes[type]) : '',

		getSystemFolderName = (type, def) => {
			switch (type) {
				case FolderType.Inbox:
				case FolderType.Sent:
				case FolderType.Drafts:
				case FolderType.Trash:
				case FolderType.Archive:
					return i18n('FOLDER_LIST/' + getKeyByValue(FolderType, type).toUpperCase() + '_NAME');
				case FolderType.Junk:
					return i18n('GLOBAL/SPAM');
				// no default
			}
			return def;
		};

	const
		/**
		 * @param {string} sFullName
		 * @param {boolean} bExpanded
		 */
		setExpandedFolder = (sFullName, bExpanded) => {
			let aExpandedList = get(ClientSideKeyNameExpandedFolders);
			aExpandedList = new Set(isArray(aExpandedList) ? aExpandedList : []);
			bExpanded ? aExpandedList.add(sFullName) : aExpandedList.delete(sFullName);
			set(ClientSideKeyNameExpandedFolders, [...aExpandedList]);
		},

		foldersFilter = ko.observable(''),

		/**
		 * @param {?Function} fCallback
		 */
		loadFolders = fCallback => {
	//		clearTimeout(this.foldersTimeout);
			Remote.abort('Folders')
				.post('Folders', FolderUserStore.foldersLoading)
				.then(data => {
					clearCache();
					FolderCollectionModel.reviveFromJson(data.Result)?.storeIt();
					fCallback?.(true);
					// Repeat every 15 minutes?
	//				this.foldersTimeout = setTimeout(loadFolders, 900000);
				})
				.catch(e => fCallback && setTimeout(fCallback, 1, false, e));
		};

	class FolderCollectionModel extends AbstractCollectionModel
	{
	/*
		constructor() {
			super();
			this.quotaUsage;
			this.quotaLimit;
			this.namespace;
			this.optimized
			this.capabilities
			this.allow; // allow adding
	//		this.exist;
		}
	*/

		/**
		 * @param {?Object} json
		 * @returns {FolderCollectionModel}
		 */
		static reviveFromJson(object) {
			const expandedFolders = get(ClientSideKeyNameExpandedFolders);

			forEachObjectEntry(SystemFolders, (key, value) =>
				value || (SystemFolders[key] = SettingsGet(key+'Folder'))
			);

			const result = super.reviveFromJson(object, oFolder => {
				let oCacheFolder = getFolderFromCacheList(oFolder.fullName);
				if (oCacheFolder) {
	//				oCacheFolder.revivePropertiesFromJson(oFolder);
					if (oFolder.etag) {
						oCacheFolder.etag = oFolder.etag;
					}
					if (null != oFolder.totalEmails) {
						oCacheFolder.totalEmails(oFolder.totalEmails);
					}
					if (null != oFolder.unreadEmails) {
						oCacheFolder.unreadEmails(oFolder.unreadEmails);
					}
				} else {
					oCacheFolder = FolderModel.reviveFromJson(oFolder);
					if (!oCacheFolder)
						return null;
					setFolder(oCacheFolder);
				}

				// JMAP RFC 8621
				let role = oFolder.role;
	/*
				if (!role) {
					// Kolab
					let type = oFolder.metadata[FolderMetadataKeys.KolabFolderType]
						|| oFolder.metadata[FolderMetadataKeys.KolabFolderTypeShared];
					switch (type) {
						case 'mail.inbox':
						case 'mail.drafts':
							role = type.replace('mail.', '');
							break;
	//					case 'mail.outbox':
						case 'mail.sentitems':
							role = 'sent';
							break;
						case 'mail.junkemail':
							role = 'spam';
							break;
						case 'mail.wastebasket':
							role = 'trash';
							break;
					}
					// Flags
					if (oFolder.attributes.includes('\\sentmail')) {
						role = 'sent';
					}
					if (oFolder.attributes.includes('\\spam')) {
						role = 'junk';
					}
					if (oFolder.attributes.includes('\\bin')) {
						role = 'trash';
					}
					if (oFolder.attributes.includes('\\important')) {
						role = 'important';
					}
					if (oFolder.attributes.includes('\\starred')) {
						role = 'flagged';
					}
					if (oFolder.attributes.includes('\\all') || oFolder.flags.includes('\\allmail')) {
						role = 'all';
					}
				}
	*/
				if (role) {
					role = role[0].toUpperCase() + role.slice(1);
					SystemFolders[role] || (SystemFolders[role] = oFolder.fullName);
				}

				oCacheFolder.type(FolderType[getKeyByValue(SystemFolders, oFolder.fullName)] || 0);

				oCacheFolder.collapsed(!expandedFolders
					|| !isArray(expandedFolders)
					|| !expandedFolders.includes(oCacheFolder.fullName));

				return oCacheFolder;
			});

			result.CountRec = result.length;
			setFolderInboxName(SystemFolders.Inbox);

			let i = result.length;
			if (i) {
				sortFolders(result);
				try {
					while (i--) {
						let folder = result[i], parent = getFolderFromCacheList(folder.parentName);
						if (!parent) {
							// Create NonExistent parent folders
							let delimiter = folder.delimiter;
							if (delimiter) {
								let parents = folder.fullName.split(delimiter);
								parents.pop();
								while (parents.length) {
									let parentName = parents.join(delimiter),
										name = parents.pop(),
										pfolder = getFolderFromCacheList(parentName);
									if (!pfolder) {
										console.log('Create nonexistent folder ' + parentName);
										pfolder = FolderModel.reviveFromJson({
											'@Object': 'Object/Folder',
											name: name,
											fullName: parentName,
											delimiter: delimiter,
											attributes: ['\\nonexistent']
										});
										setFolder(pfolder);
										result.splice(i, 0, pfolder);
										++i;
									}
								}
								parent = getFolderFromCacheList(folder.parentName);
							}
						}
						if (parent) {
							parent.subFolders.unshift(folder);
							result.splice(i,1);
						}
					}
				} catch (e) {
					console.error(e);
				}
			}

			return result;
		}

		visible() {
			return this.filter(folder => folder.visible());
		}

		storeIt() {
			FolderUserStore.displaySpecSetting(Settings.app('folderSpecLimit') < this.CountRec);

			if (!(
					SettingsGet('SentFolder') +
					SettingsGet('DraftsFolder') +
					SettingsGet('JunkFolder') +
					SettingsGet('TrashFolder') +
					SettingsGet('ArchiveFolder')
				)
			) {
				FolderUserStore.saveSystemFolders(SystemFolders);
			}

			FolderUserStore.folderList(this);

			FolderUserStore.namespace = this.namespace;

			// 'THREAD=REFS', 'THREAD=REFERENCES', 'THREAD=ORDEREDSUBJECT'
			AppUserStore.threadsAllowed(!!this.capabilities.some(capa => capa.startsWith('THREAD=')));

	//		FolderUserStore.optimized(!!this.optimized);
			FolderUserStore.quotaUsage(this.quotaUsage);
			FolderUserStore.quotaLimit(this.quotaLimit);
			FolderUserStore.capabilities(this.capabilities);

			FolderUserStore.sentFolder(normalizeFolder(SystemFolders.Sent));
			FolderUserStore.draftsFolder(normalizeFolder(SystemFolders.Drafts));
			FolderUserStore.spamFolder(normalizeFolder(SystemFolders.Junk));
			FolderUserStore.trashFolder(normalizeFolder(SystemFolders.Trash));
			FolderUserStore.archiveFolder(normalizeFolder(SystemFolders.Archive));

	//		FolderUserStore.folderList.valueHasMutated();
		}

	}

	class FolderModel extends AbstractModel {
		constructor() {
			super();

			this.fullName = '';
			this.parentName = '';
			this.delimiter = '';
			this.deep = 0;
			this.expires = 0;
			this.metadata = {};

			this.exists = true;

			this.etag = '';
			this.id = 0;
			this.uidNext = 0;
			this.size = 0;

			addObservablesTo(this, {
				name: '',
				type: 0,
				role: null,
				selectable: false,

				focused: false,
				selected: false,
				isSubscribed: true,
				checkable: false, // Check for new messages
				askDelete: false,

				errorMsg: '',

				totalEmails: 0,
				unreadEmails: 0,

				kolabType: null,

				collapsed: true,

				tagsAllowed: false
			});

			this.attributes = ko.observableArray();
			// For messages
			this.permanentFlags = ko.observableArray();

			this.addSubscribables({
				kolabType: sValue => this.metadata[FolderMetadataKeys.KolabFolderType] = sValue,
				permanentFlags: aValue => this.tagsAllowed(aValue.includes('\\*')),
				unreadEmails: unread => FolderType.Inbox === this.type() && fireEvent('mailbox.inbox-unread-count', unread)
			});

			this.subFolders = ko.observableArray(new FolderCollectionModel);
			this.actionBlink = ko.observable(false).extend({ falseTimeout: 1000 });
	/*
			this.totalEmails = koComputable({
					read: this.totalEmailsValue,
					write: iValue =>
						isPosNumeric(iValue) ? this.totalEmailsValue(iValue) : this.totalEmailsValue.valueHasMutated()
				})
				.extend({ notify: 'always' });

			this.unreadEmails = koComputable({
					read: this.unreadEmailsValue,
					write: value =>
						isPosNumeric(value) ? this.unreadEmailsValue(value) : this.unreadEmailsValue.valueHasMutated()
				})
				.extend({ notify: 'always' });
	*/
	/*
			// https://www.rfc-editor.org/rfc/rfc8621.html#section-2
			this.myRights = {
				'mayAddItems': true,
				'mayCreateChild': true,
				'mayDelete': true,
				'mayReadItems': true,
				'mayRemoveItems': true,
				'mayRename': true,
				'maySetKeywords': true,
				'maySetSeen': true,
				'maySubmit': true
			};
	*/
			this.addComputables({

				isInbox: () => FolderType.Inbox === this.type(),

				isFlagged: () => FolderUserStore.currentFolder() === this
					&& MessagelistUserStore.listSearch().includes('flagged'),

	//			isSubscribed: () => this.attributes().includes('\\subscribed'),

				hasVisibleSubfolders: () => !!this.subFolders().find(folder => folder.visible()),
				visibleSubfolders: () => this.subFolders().visible(),

				hasSubscriptions: () => this.isSubscribed() | !!this.subFolders().find(
						oFolder => {
							const subscribed = oFolder.hasSubscriptions();
							return !oFolder.isSystemFolder() && subscribed;
						}
					),

				isSystemFolder: () => this.type()
					| (FolderUserStore.allowKolab() && !!this.kolabType() & !SettingsUserStore.unhideKolabFolders()),

				canBeSelected: () => this.selectable() && !this.isSystemFolder(),

				canBeDeleted: () => this.canBeSelected() && this.exists,

				canBeSubscribed: () => this.selectable()
					&& !(this.isSystemFolder() | !SettingsUserStore.hideUnsubscribed()),

				optionalTags: () => this.permanentFlags.filter(isAllowedKeyword),

				/**
				 * Folder is visible when:
				 * - hasVisibleSubfolders()
				 * Or when all below conditions are true:
				 * - selectable()
				 * - isSubscribed() OR hideUnsubscribed = false
				 * - 0 == type()
				 * - not kolabType()
				 */
				visible: () => {
					const selectable = this.canBeSelected(),
						name = this.name(),
						filter = foldersFilter(),
						visible = (this.isSubscribed() | !SettingsUserStore.hideUnsubscribed())
							&& selectable
							&& (!filter || name.toLowerCase().includes(filter.toLowerCase()));
					return this.hasVisibleSubfolders() | visible;
				},

				unreadCount: () => this.unreadEmails() || null,
	/*
				{
					// TODO: make this optional in Settings
					// https://github.com/the-djmaze/snappymail/issues/457
					// https://github.com/the-djmaze/snappymail/issues/567
					const
						unread = this.unreadEmails(),
						type = this.type();
	//				return ((!this.isSystemFolder() || type == FolderType.Inbox) && unread) ? unread : null;
				},
	*/

				localName: () => {
					let name = this.name();
					if (this.isSystemFolder()) {
						translateTrigger();
						name = getSystemFolderName(this.type(), name);
					}
					return name;
				},

				nameInfo: () => {
					if (this.isSystemFolder()) {
						translateTrigger();
						let suffix = getSystemFolderName(this.type(), getKolabFolderName(this.kolabType()));
						if (this.name() !== suffix && 'inbox' !== suffix.toLowerCase()) {
							return ' (' + suffix + ')';
						}
					}
					return '';
				},

				friendlySize: () => FileInfo.friendlySize(this.size),

				detailedName: () => this.name() + ' ' + this.nameInfo(),

				icon: () => {
					switch (this.type())
					{
						case 1: return '📥'; // FolderType.Inbox
						case 2: return '📧'; // FolderType.Sent icon-paper-plane
						case 3: return '🗎'; // FolderType.Drafts
						case 4: return '⚠'; // FolderType.Junk
						case 5: return '🗑'; // FolderType.Trash
						case 6: return '🗄'; // FolderType.Archive
					}
					return null;
				},

				hasUnreadInSub: () =>
					this.subFolders().some(
						folder => folder.unreadEmails() | folder.hasUnreadInSub()
					),

				href: () => this.canBeSelected() && mailBox(this.fullNameHash)
			});
		}

		edit() {
			showScreenPopup(FolderPopupView, [this]);
		}

		/**
		 * For url safe '/#/mailbox/...' path
		 */
		get fullNameHash() {
			return this.fullName.replace(/[^a-z0-9._-]+/giu, b64EncodeJSONSafe);
	//		return /^[a-z0-9._-]+$/iu.test(this.fullName) ? this.fullName : b64EncodeJSONSafe(this.fullName);
		}

		/**
		 * @static
		 * @param {FetchJsonFolder} json
		 * @returns {?FolderModel}
		 */
		static reviveFromJson(json) {
			const folder = super.reviveFromJson(json);
			if (folder) {
				const path = folder.fullName.split(folder.delimiter),
					attr = name => folder.attributes.includes(name),
					type = (folder.metadata[FolderMetadataKeys.KolabFolderType]
						|| folder.metadata[FolderMetadataKeys.KolabFolderTypeShared]
						|| ''
					).split('.')[0];

				folder.deep = path.length - 1;
				path.pop();
				folder.parentName = path.join(folder.delimiter);

				folder.isSubscribed(attr('\\subscribed'));
				folder.exists = !attr('\\nonexistent');
				folder.subFolders.allow = !attr('\\noinferiors');
	//			folder.subFolders.exist = attr('\\haschildren') || !attr('\\hasnochildren');
				folder.selectable(folder.exists && !attr('\\noselect'));

				type && 'mail' != type && folder.kolabType(type);
			}
			return folder;
		}

		/**
		 * @returns {string}
		 */
		collapsedCss() {
			return 'e-collapsed-sign ' + (this.hasVisibleSubfolders()
				? (this.collapsed() ? 'icon-right-mini' : 'icon-down-mini')
				: 'icon-none'
			);
		}
	}

	const rlContentType = 'snappymail/action',

		// In Chrome we have no access to dataTransfer.getData unless it's the 'drop' event
		// In Chrome Mobile dataTransfer.types.includes(rlContentType) fails, only text/plain is set
		dragMessages = () => 'messages' === dragData?.action,
		dragSortable = () => 'sortable' === dragData?.action,
		setDragAction = (e, action, effect, data, img) => {
			dragData = {
				action: action,
				data: data
			};
	//		e.dataTransfer.setData(rlContentType, action);
			e.dataTransfer.setData('text/plain', rlContentType+'/'+action);
			e.dataTransfer.setDragImage(img, 0, 0);
			e.dataTransfer.effectAllowed = effect;
		},

		dragTimer = {
			id: 0
		},

		dragStop = (e, element) => {
			e.preventDefault();
			element?.classList.remove('droppableHover');
			if (dragTimer.node == element) {
				dragTimer.node = null;
				clearTimeout(dragTimer.id);
			}
		},
		dragEnter = (e, element, folder) => {
			let files = false;
	//		if (e.dataTransfer.types.includes('Files'))
			for (const item of e.dataTransfer.items) {
				files |= 'file' === item.kind && RFC822 === item.type;
			}
			if (files || dragMessages()) {
				e.stopPropagation();
				dragStop(e, dragTimer.node);
				e.dataTransfer.dropEffect = files ? 'copy' : (e.ctrlKey ? 'copy' : 'move');
				element.classList.add('droppableHover');
				if (folder.collapsed()) {
					dragTimer.node = element;
					dragTimer.id = setTimeout(() => {
						folder.collapsed(false);
						setExpandedFolder(folder.fullName, true);
					}, 500);
				}
			}
		},
		dragDrop = (e, element, folder, dragData) => {
			dragStop(e, element);
			if (dragMessages() && 'copyMove' == e.dataTransfer.effectAllowed) {
				MessagelistUserStore.moveMessages(
					FolderUserStore.currentFolderFullName(), dragData.data, folder.fullName, e.ctrlKey
				);
			} else if (e.dataTransfer.types.includes('Files')) {
				dropFilesInFolder(folder.fullName, e.dataTransfer.files);
			}
		},

		ttn = (element, fValueAccessor) => timeToNode(element, ko.unwrap(fValueAccessor()));

	let dragImage,
		dragData;

	Object.assign(ko.bindingHandlers, {

		editor: {
			init: (element, fValueAccessor) => {
				let editor = null;

				const fValue = fValueAccessor(),
					fUpdateEditorValue = () => fValue.__editor?.setHtmlOrPlain(fValue()),
					fUpdateKoValue = () => fValue.__editor && fValue(fValue.__editor.getDataWithHtmlMark()),
					fOnReady = () => {
						fValue.__editor = editor;
						fUpdateEditorValue();
					};

				if (ko.isObservable(fValue)) {
					editor = new HtmlEditor(element, fOnReady, fUpdateKoValue, fUpdateKoValue);

					fValue.__fetchEditorValue = fUpdateKoValue;

					fValue.subscribe(fUpdateEditorValue);

					// ko.utils.domNodeDisposal.addDisposeCallback(element, () => {
					// });
				}
			}
		},

		time: {
			init: ttn,
			update: ttn
		},

		emailsTags: {
			init: (element, fValueAccessor, fAllBindings) => {
				const fValue = fValueAccessor(),
					focused = fValue.focused;

				element.addresses = new EmailAddressesComponent(element, {
					focusCallback: value => focused?.(!!value),
					autoCompleteSource: fAllBindings.get('autoCompleteSource'),
					onChange: value => fValue(value)
				});

				focused?.subscribe(value =>
					element.addresses[value ? 'focus' : 'blur']()
				);
			},
			update: (element, fValueAccessor) => {
				element.addresses.value = ko.unwrap(fValueAccessor());
			}
		},

		// Start dragging checked messages
		dragmessages: {
			init: element => {
				element.addEventListener("dragstart", e => {
					dragImage || (dragImage = elementById('messagesDragImage'));
					if (dragImage && !ThemeStore.isMobile()) {
						ko.dataFor(doc.elementFromPoint(e.clientX, e.clientY))?.checked?.(true);

						const uids = MessagelistUserStore.listCheckedOrSelectedUidsWithSubMails();
						dragImage.querySelector('.text').textContent = uids.size;

						// Make sure Chrome shows it
						dragImage.style.left = e.clientX + 'px';
						dragImage.style.top = e.clientY + 'px';
						dragImage.style.right = 'auto';

						setDragAction(e, 'messages', 'copyMove', uids, dragImage);

						// Remove the Chrome visibility
						dragImage.style.cssText = '';

						leftPanelDisabled(false);
					} else {
						e.preventDefault();
					}

				}, false);
				element.addEventListener("dragend", () => dragData = null);
			}
		},

		// Drop selected messages on folder
		dropmessages: {
			init: (element, fValueAccessor) => {
				const folder = fValueAccessor(); // ko.dataFor(element)
				folder && addEventsListeners(element, {
					dragenter: e => dragEnter(e, element, folder),
					dragover: e => e.preventDefault(),
					dragleave: e => dragStop(e, element),
					drop: e => dragDrop(e, element, folder, dragData)
				});
			}
		},

		sortableItem: {
			init: (element, fValueAccessor) => {
				let options = ko.unwrap(fValueAccessor()) || {},
					parent = element.parentNode,
					fnHover = e => {
						if (dragSortable()) {
							e.preventDefault();
							let node = (e.target.closest ? e.target : e.target.parentNode).closest('[draggable]');
							if (node && node !== dragData.data && parent.contains(node)) {
								let rect = node.getBoundingClientRect();
								if (rect.top + (rect.height / 2) <= e.clientY) {
									if (node.nextElementSibling !== dragData.data) {
										node.after(dragData.data);
									}
								} else if (node.previousElementSibling !== dragData.data) {
									node.before(dragData.data);
								}
							}
						}
					};
				addEventsListeners(element, {
					dragstart: e => {
						setDragAction(e, 'sortable', 'move', element, element);
						element.style.opacity = 0.25;
					},
					dragend: () => {
						element.style.opacity = null;
						if (dragSortable()) {
							dragData.data.style.cssText = '';
							let row = parent.rows[options.list.indexOf(ko.dataFor(element))];
							if (row != dragData.data) {
								row.before(dragData.data);
							}
							dragData = null;
						}
					}
				});
				if (!parent.sortable) {
					parent.sortable = true;
					addEventsListeners(parent, {
						dragenter: fnHover,
						dragover: fnHover,
						drop: e => {
							if (dragSortable()) {
								e.preventDefault();
								let data = ko.dataFor(dragData.data),
									from = options.list.indexOf(data),
									to = [...parent.children].indexOf(dragData.data);
								if (from != to) {
									let arr = options.list();
									arr.splice(to, 0, ...arr.splice(from, 1));
									options.list(arr);
								}
								dragData = null;
								options.afterMove?.();
							}
						}
					});
				}
			}
		},

		initDom: {
			init: (element, fValueAccessor) => fValueAccessor()(element)
		},

		registerBootstrapDropdown: {
			init: element => {
				dropdowns.push(element);
				element.ddBtn = new BSN.Dropdown(element.querySelector('.dropdown-toggle'));
			}
		}
	});

	class AccountModel extends AbstractModel {
		/**
		 * @param {string} email
		 * @param {boolean=} canBeDelete = true
		 * @param {number=} count = 0
		 */
		constructor(email, name, isAdditional = true) {
			super();

			this.name = name;
			this.email = email;

			this.displayName = name ? name + ' <' + email + '>' : email;

			addObservablesTo(this, {
				unreadEmails: null,
				askDelete: false,
				isAdditional: isAdditional
			});

			// Load at random between 3 and 30 seconds
			SettingsUserStore.showUnreadCount() && isAdditional
			&& setTimeout(()=>this.fetchUnread(), (Math.ceil(Math.random() * 10)) * 3000);
		}

		label() {
			return this.name || IDN.toUnicode(this.email);
		}

		/**
		 * Get INBOX unread messages
		 */
		fetchUnread() {
			Remote.request('AccountUnread', (iError, oData) => {
				iError || this.unreadEmails(oData?.Result?.unreadEmails || null);
			}, {
				email: this.email
			});
		}

		/**
		 * Imports all mail to main account
		 *//*
		importAll(account) {
			Remote.streamPerLine(line => {
				try {
					line = JSON.parse(line);
					console.dir(line);
				} catch (e) {
					// OOPS
				}
			}, 'AccountImport', {
				Action: 'AccountImport',
				email: account.email
			});
		}
		*/

	}

	class IdentityModel extends AbstractModel {
		/**
		 * @param {string} id
		 * @param {string} email
		 */
		constructor() {
			super();

			addObservablesTo(this, {
				id: '',
				label: '',
				email: '',
				name: '',

				replyTo: '',
				bcc: '',
				sentFolder: '',

				signature: '',
				signatureInsertBefore: false,

				pgpSign: false,
				pgpEncrypt: false,

				smimeKey: '',
				smimeCertificate: '',

				askDelete: false,

				exists: false
			});

			addComputablesTo(this, {
				smimeKeyEncrypted: () => this.smimeKey().includes('-----BEGIN ENCRYPTED PRIVATE KEY-----'),
				smimeKeyValid: () => /^-----BEGIN (ENCRYPTED |RSA )?PRIVATE KEY-----/.test(this.smimeKey()),
				smimeCertificateValid: () => /^-----BEGIN CERTIFICATE-----/.test(this.smimeCertificate())
			});
		}

		/**
		 * @returns {string}
		 */
		formattedName() {
			const name = this.name(),
				email = this.email(),
				label = this.label();
			return (name ? `${name} ` : '') + `<${email}>` + (label ? ` (${label})` : '');
		}
	}

	const IdentityUserStore = koArrayWithDestroy();

	IdentityUserStore.loading = ko.observable(false).extend({ debounce: 100 });

	/** Returns main (login) identity */
	IdentityUserStore.main = koComputable(() => {
		const list = IdentityUserStore();
		return isArray(list) ? list.find(item => item && !item.id()) : null;
	});

	class IdentityPopupView extends AbstractViewPopup {
		constructor() {
			super('Identity');

			addObservablesTo(this, {
				identity: null,
				edit: false,
				labelFocused: false,
				nameFocused: false,
				submitRequest: false,
				submitError: ''
			});
	/*
			this.email.valueHasMutated();
			this.replyTo.valueHasMutated();
			this.bcc.valueHasMutated();
	*/
			this.folderSelectList = koComputable(() =>
				folderListOptionsBuilder(
					[],
					[['', '('+i18n('GLOBAL/DEFAULT')+')']]
				)
			);
			this.defaultOptionsAfterRender = defaultOptionsAfterRender;

			this.createSelfSigned = this.createSelfSigned.bind(this);
			this.setSMimeKeyPass = this.setSMimeKeyPass.bind(this);
		}

		createSelfSigned() {
			AskPopupView.password('', 'CRYPTO/CREATE_SELF_SIGNED').then(result => {
				if (result) {
					const identity = this.identity();
					Remote.request('SMimeCreateCertificate', (iError, oData) => {
						if (oData.Result.x509) {
							identity.smimeKey(oData.Result.pkey);
							identity.smimeCertificate(oData.Result.x509);
						} else {
							this.submitError(oData.message);
						}
					}, {
						name: identity.name(),
						email: identity.email(),
						privateKey: identity.smimeKey(),
						passphrase: result.password
					});
				}
			});
		}

		async setSMimeKeyPass() {
			const identity = this.identity();
			let old = null;
			if (identity.smimeKeyEncrypted()) {
				old = await AskPopupView.password(i18n('CRYPTO/CURRENT_PASS'), 'CRYPTO/DECRYPT');
				if (!old) {
					return;
				}
			}
			AskPopupView.password(i18n('CRYPTO/NEW_PASS'), 'GLOBAL/SAVE').then(result => {
				if (result) {
					Remote.request('SMimeExportPrivateKey', (iError, oData) => {
						if (oData.Result) {
							identity.smimeKey(oData.Result);
						} else {
							this.submitError(oData.message);
						}
					}, {
						privateKey: identity.smimeKey(),
						oldPassphrase: old?.password,
						newPassphrase: result.password
					});
				}
			});
		}

		submitForm(form) {
			if (!this.submitRequest() && form.reportValidity()) {
				let identity = this.identity();
				identity.signature?.__fetchEditorValue?.();
				this.submitRequest(true);
				const data = new FormData(form);
				data.set('Id', identity.id());
				data.set('Signature', identity.signature());
				Remote.request('IdentityUpdate', iError => {
						this.submitRequest(false);
						if (iError) {
							this.submitError(getNotification(iError));
						} else {
							rl.app.loadAccountsAndIdentities();
							this.close();
						}
					}, data
				);
			}
		}

		/**
		 * @param {?IdentityModel} oIdentity
		 */
		onShow(identity) {
			this.submitRequest(false);
			this.submitError('');
			if (identity) {
				this.edit(true);
			} else {
				this.edit(false);
				identity = new IdentityModel;
				identity.id(Jua.randomId());
			}
			this.identity(identity);
		}

		afterShow() {
			this.identity().id() ? this.labelFocused(true) : this.nameFocused(true);
		}

		onClose() {
			if (!this.identity().exists()) {
				showScreenPopup(AskPopupView, [
					i18n('POPUPS_ASK/DESC_WANT_CLOSE_THIS_WINDOW'),
					() => this.close()
				]);
				return false;
			}
		}
	}

	const

	// 1 = move, 2 = copy
	moveAction = ko.observable(0),

	dropdownsDetectVisibility = (() =>
		dropdownVisibility(!!dropdowns.find(item => item.classList.contains('show')))
	).debounce(50),


	editIdentity = Identity => showScreenPopup(IdentityPopupView, [Identity]),

	loadAccountsAndIdentities = () => {
		AccountUserStore.loading(true);
		IdentityUserStore.loading(true);

		Remote.request('AccountsAndIdentities', (iError, oData) => {
			AccountUserStore.loading(false);
			IdentityUserStore.loading(false);

			if (!iError) {
				let items = oData.Result.Accounts;
				AccountUserStore(isArray(items)
					? items.map(oValue => new AccountModel(oValue.email, oValue.name))
					: []
				);
				AccountUserStore.unshift(new AccountModel(SettingsGet('mainEmail'), '', false));

				items = oData.Result.Identities;
				IdentityUserStore(isArray(items)
					? items.map(identityData => IdentityModel.reviveFromJson(identityData))
					: []
				);

				// Invoke "Update Identity" pop up right after login
				// https://github.com/the-djmaze/snappymail/issues/1689
				const main = IdentityUserStore.main();
				main && !main.exists() && setTimeout(()=>editIdentity(main), 1000);
			}
		});
	},

	/**
	 * @param {string} link
	 * @returns {boolean}
	 */
	download = (link, name = "") => {
		console.log('download: '+link);
		// Firefox 98 issue https://github.com/the-djmaze/snappymail/issues/301
		if (ThemeStore.isMobile() || /firefox/i.test(navigator.userAgent)) {
			open(link, '_blank');
			focus();
		} else {
			const oLink = createElement('a', {
				href: link,
				target: '_blank',
				download: name
			});
			doc.body.appendChild(oLink).click();
			oLink.remove();
		}
	},

	downloadZip = (name, hashes, onError, fTrigger, folder) => {
		if (hashes.length) {
			let params = {
				target: 'zip',
				filename: name,
				hashes: hashes
			};
			if (!onError) {
				onError = () => alert('Download failed');
			}
			if (folder) {
				params.folder = folder;
	//			params.uids = uids;
			}
			Remote.post('AttachmentsActions', fTrigger || null, params)
			.then(result => {
				let hash = result?.Result?.fileHash;
				hash ? download(attachmentDownload(hash), hash+'.zip') : onError();
			})
			.catch(onError);
		}
	},

	/**
	 * @returns {function}
	 */
	computedPaginatorHelper = (koCurrentPage, koPageCount) => {
		return () => {
			const currentPage = koCurrentPage(),
				pageCount = koPageCount(),
				result = [],
				lang = doc.documentElement.lang,
				fAdd = (index, push = true, customName = '') => {
					const name = index.toLocaleString(lang),
						data = {
							current: index === currentPage,
							name: customName || name,
							title: customName ? name : '',
							value: index
						};

					push ? result.push(data) : result.unshift(data);
				};

			let prev = 0,
				next = 0,
				limit = 2;

			if (1 < pageCount) {
				if (pageCount < currentPage) {
					fAdd(pageCount);
					prev = pageCount;
					next = pageCount;
				} else {
					if (3 >= currentPage || pageCount - 2 <= currentPage) {
						limit += 2;
					}

					fAdd(currentPage);
					prev = currentPage;
					next = currentPage;
				}

				while (0 < limit) {
					--prev;
					++next;

					if (0 < prev) {
						fAdd(prev, false);
						--limit;
					}

					if (pageCount >= next) {
						fAdd(next, true);
						--limit;
					} else if (0 >= prev) {
						break;
					}
				}

				if (3 === prev) {
					fAdd(2, false);
				} else if (3 < prev) {
					fAdd(Math.round((prev - 1) / 2), false, '…');
				}

				if (pageCount - 2 === next) {
					fAdd(pageCount - 1, true);
				} else if (pageCount - 2 > next) {
					fAdd(Math.round((pageCount + next) / 2), true, '…');
				}

				// first and last
				if (1 < prev) {
					fAdd(1, false);
				}

				if (pageCount > next) {
					fAdd(pageCount, true);
				}
			}

			return result;
		};
	},

	/**
	 * @param {string} mailToUrl
	 * @returns {boolean}
	 */
	mailToHelper = mailToUrl => {
		if ('mailto:' === mailToUrl?.slice(0, 7).toLowerCase()) {
			mailToUrl = mailToUrl.slice(7).split('?');

			const
				email = decodeURIComponent(mailToUrl[0]),
				params = new URLSearchParams(mailToUrl[1]),
				to = params.get('to'),
				toEmailModel = value => EmailCollectionModel.fromString(value);

			showMessageComposer([
				ComposeType.Empty,
				null,
				toEmailModel(to ? email + ',' + to : email),
				toEmailModel(params.get('cc')),
				toEmailModel(params.get('bcc')),
				params.get('subject'),
				plainToHtml(params.get('body') || '')
			]);

			return true;
		}

		return false;
	},

	showMessageComposer = (params = []) =>
	{
		rl.app.showMessageComposer(params);
	},

	setLayoutResizer = (source, sClientSideKeyName, mode) =>
	{
		if (source.layoutResizer && source.layoutResizer.mode != mode) {
			source.removeAttribute('style');
		}
		source.observer?.disconnect();
	//	source.classList.toggle('resizable', mode);
		if (mode) {
			const length = get(sClientSideKeyName + mode) || SettingsGet('Resizer' + sClientSideKeyName + mode);
			if (length) {
				source.style[mode.toLowerCase()] = length + 'px';
			}
			if (!source.layoutResizer) {
				const resizer = createElement('div', {'class':'resizer'}),
					save = (data => Remote.saveSettings(0, data)).debounce(500),
					size = {},
					store = () => {
						const value = ('Width' == resizer.mode) ? source.offsetWidth : source.offsetHeight,
							prop = resizer.key + resizer.mode;
						(value == get(prop)) || set(prop, value);
						(value == SettingsGet('Resizer' + prop)) || save({['Resizer' + prop]: value});
					},
					cssint = s => {
						let value = getComputedStyle(source, null)[s].replace('px', '');
						if (value.includes('%')) {
							value = source.parentElement['offset'+resizer.mode]
								* value.replace('%', '') / 100;
						}
						return parseFloat(value);
					};
				source.layoutResizer = resizer;
				source.append(resizer);
				resizer.addEventListener('mousedown', {
					handleEvent: function(e) {
						if ('mousedown' == e.type) {
							const lmode = resizer.mode.toLowerCase();
							e.preventDefault();
							size.pos = ('width' == lmode) ? e.pageX : e.pageY;
							size.min = cssint('min-'+lmode);
							size.max = cssint('max-'+lmode);
							size.org = cssint(lmode);
							addEventListener('mousemove', this);
							addEventListener('mouseup', this);
						} else if ('mousemove' == e.type) {
							const lmode = resizer.mode.toLowerCase(),
								length = size.org + (('width' == lmode ? e.pageX : e.pageY) - size.pos);
							if (length >= size.min && length <= size.max ) {
								source.style[lmode] = length + 'px';
								source.observer || store();
							}
						} else if ('mouseup' == e.type) {
							removeEventListener('mousemove', this);
							removeEventListener('mouseup', this);
						}
					}
				});
				source.observer = window.ResizeObserver ? new ResizeObserver(store) : null;
			}
			source.layoutResizer.mode = mode;
			source.layoutResizer.key = sClientSideKeyName;
			source.observer?.observe(source, { box: 'border-box' });
		}
	},

	viewMessage = (oMessage, popup) => {
		if (popup) {
			oMessage.popupMessage();
		} else {
			MessageUserStore.error('');
			let id = 'rl-msg-' + oMessage.hash,
				body = oMessage.body || elementById(id);
			if (!body) {
				body = createElement('div',{
					id:id,
					hidden:'',
					class:'b-text-part'
						+ (oMessage.pgpSigned() ? ' openpgp-signed' : '')
						+ (oMessage.pgpEncrypted() ? ' openpgp-encrypted' : '')
						+ (oMessage.smimeSigned() ? ' smime-signed' : '')
						+ (oMessage.smimeEncrypted() ? ' smime-encrypted' : '')
				});
				MessageUserStore.purgeCache();
			}

			body.message = oMessage;
			oMessage.body = body;

			if (!SettingsUserStore.viewHTML() || !oMessage.viewHtml()) {
				oMessage.viewPlain();
			}

			MessageUserStore.bodiesDom().append(body);

			MessageUserStore.loading(false);
			oMessage.body.hidden = false;

			if (oMessage.isUnseen() && SettingsUserStore.messageReadAuto()) {
				MessageUserStore.MessageSeenTimer = setTimeout(
					() => MessagelistUserStore.setAction(oMessage.folder, MessageSetAction.SetSeen, [oMessage]),
					SettingsUserStore.messageReadDelay() * 1000 // seconds
				);
			}
		}
	},

	populateMessageBody = (oMessage, popup) => {
		if (oMessage) {
			popup || MessageUserStore.message(oMessage);
			if (oMessage.body) {
				viewMessage(oMessage, popup);
			} else {
				popup || MessageUserStore.loading(true);
				Remote.message((iError, oData/*, bCached*/) => {
					if (iError) {
						if (Notifications.RequestAborted !== iError && !popup) {
							MessageUserStore.message(null);
							MessageUserStore.error(getNotification(iError));
						}
					} else {
						let json = oData?.Result;
						if (json
							&& ((
									oMessage.hash && oMessage.hash === json.hash
								) || (
									!oMessage.hash
									&& oMessage.folder === json.folder
									&& oMessage.uid == json.uid)
							)
							&& oMessage.revivePropertiesFromJson(json)
						) {
	/*
							if (bCached) {
								delete json.flags;
							}
							oMessage.body.remove();
	*/
							viewMessage(oMessage, popup);
						}
					}
					popup || MessageUserStore.loading(false);
				}, oMessage.folder, oMessage.uid);
			}
		}
	};

	leftPanelDisabled.subscribe(value => value && moveAction(0));
	moveAction.subscribe(value => value && leftPanelDisabled(false));

	const ContactUserStore = koArrayWithDestroy();

	ContactUserStore.loading = ko.observable(false).extend({ debounce: 200 });
	ContactUserStore.importing = ko.observable(false).extend({ debounce: 200 });
	ContactUserStore.syncing = ko.observable(false).extend({ debounce: 200 });

	addObservablesTo(ContactUserStore, {
		allowSync: false, // Admin setting
		syncMode: 0,
		syncUrl: '',
		syncUser: '',
		syncPass: ''
	});

	// Also used by Selector
	ContactUserStore.hasChecked = koComputable(
		// Issue: not all are observed?
		() => !!ContactUserStore.find(item => item.checked())
	);

	/**
	 * @param {Function} fResultFunc
	 * @returns {void}
	 */
	ContactUserStore.sync = fResultFunc => {
		if (ContactUserStore.syncMode()
		 && !ContactUserStore.importing()
		 && !ContactUserStore.syncing()
		) {
			ContactUserStore.syncing(true);
			Remote.streamPerLine(line => {
				try {
					line = JSON.parse(line);
					if ('ContactsSync' === line.Action) {
						ContactUserStore.syncing(false);
						fResultFunc?.(line.code, line);
					}
				} catch (e) {
					ContactUserStore.syncing(false);
					console.error(e);
					fResultFunc?.(Notifications.UnknownError);
				}
			}, 'ContactsSync');
		}
	};

	ContactUserStore.init = () => {
		let config = SettingsGet('ContactsSync');
		ContactUserStore.allowSync(!!config);
		if (config) {
			ContactUserStore.syncMode(config.Mode);
			ContactUserStore.syncUrl(config.Url);
			ContactUserStore.syncUser(config.User);
			ContactUserStore.syncPass(config.Password);
			setTimeout(ContactUserStore.sync, 10000);
			setInterval(ContactUserStore.sync, config.Interval * 60000 + 5000);
		}
	};

	const SMimeUserStore = koArrayWithDestroy();

	addObservablesTo(SMimeUserStore, {
		loading: false
	});

	SMimeUserStore.loadCertificates = () => {
		SMimeUserStore([]);
		SMimeUserStore.loading(true);
		Remote.request('SMimeGetCertificates', (iError, oData) => {
			SMimeUserStore.loading(false);
			const collator = baseCollator();
			iError || SMimeUserStore(oData.Result.sort(
				(a, b) => collator.compare(a.emailAddress, b.emailAddress) || (b.validTo_time_t - a.validTo_time_t)
			));
		});
	};

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

	const
		SignMeOff = 0,
		SignMeOn = 1,
		SignMeUnused = 2;

	class LoginUserView extends AbstractViewLogin {
		constructor() {
			super();

			addObservablesTo(this, {
				loadingDesc: SettingsGet('loadingDescription'),

				email: SettingsGet('DevEmail'),
				password: SettingsGet('DevPassword'),
				signMe: false,

				emailError: false,
				passwordError: false,

				submitRequest: false,
				submitError: '',
				submitErrorAdditional: '',

				langRequest: false,

				signMeType: SignMeUnused
			});

			this.allowLanguagesOnLogin = !!SettingsGet('allowLanguagesOnLogin');

			this.language = LanguageStore.language;
			this.languages = LanguageStore.languages;

			this.bSendLanguage = false;

			addComputablesTo(this, {

				languageFullName: () => convertLangName(this.language()),

				signMeVisibility: () => SignMeUnused !== this.signMeType()
			});

			addSubscribablesTo(this, {
				email: () => this.emailError(false),

				password: () => this.passwordError(false),

				submitError: value => value || this.submitErrorAdditional(''),

				signMeType: iValue => this.signMe(SignMeOn === iValue),

				language: value => {
					this.langRequest(true);
					translatorReload(value).then(
						() => {
							this.langRequest(false);
							this.bSendLanguage = true;
						},
						() => this.langRequest(false)
					);
				}
			});

			if (SettingsGet('AdditionalLoginError') && !this.submitError()) {
				this.submitError(SettingsGet('AdditionalLoginError'));
			}

			decorateKoCommands(this, {
				submitCommand: self => !self.submitRequest()
			});
		}

		hideError() {
			this.submitError('');
		}

		submitCommand(self, event) {
			const email = this.email().trim();
			this.email(email);

			let form = event.target.form,
				data = new FormData(form),
				valid = form.reportValidity() && fireEvent('sm-user-login', data, 1);

			this.emailError(!email);
			this.passwordError(!this.password());
			this.formError(!valid);

			if (valid) {
				this.submitRequest(true);
				data.set('language', this.bSendLanguage ? this.language() : '');
				data.set('signMe', this.signMe() ? 1 : 0);
				Remote.request('Login',
					(iError, oData) => {
						fireEvent('sm-user-login-response', {
							error: iError,
							data: oData
						});
						if (iError) {
							this.submitRequest(false);
							if (Notifications.InvalidInputArgument == iError) {
								iError = Notifications.AuthError;
							}
							this.submitError(getNotification(iError, oData?.message,
								Notifications.UnknownError));
							this.submitErrorAdditional(oData?.messageAdditional || oData?.message);
						} else {
							rl.setData(oData.Result);
						}
					},
					data
				);

				set(ClientSideKeyNameLastSignMe, this.signMe() ? '-1-' : '-0-');
			}

			return valid;
		}

		onBuild(dom) {
			super.onBuild(dom);

			let signMe = SettingsGet('signMe');
			switch (signMe) {
				case SignMeOff:
				case SignMeOn:
					switch (get(ClientSideKeyNameLastSignMe)) {
						case '-1-':
							signMe = SignMeOn;
							break;
						case '-0-':
							signMe = SignMeOff;
							break;
						// no default
					}
					this.signMeType(signMe);
					break;
				default:
					this.signMeType(SignMeUnused);
					break;
			}
		}

		selectLanguage() {
			showScreenPopup(LanguagesPopupView, [this.language, this.languages(), LanguageStore.userLanguage()]);
		}
	}

	class LoginUserScreen extends AbstractScreen {
		constructor() {
			super('login', [LoginUserView]);
		}

		onShow() {
			rl.setTitle();
		}
	}

	class KeyboardShortcutsHelpPopupView extends AbstractViewPopup {
		constructor() {
			super('KeyboardShortcutsHelp');
			this.metaKey = shortcuts.getMetaKey();
		}

		onBuild(dom) {
			const tabs = dom.querySelectorAll('.tabs input'),
				last = tabs.length - 1;

	//		addShortcut('tab', 'shift',
			addShortcut('tab,arrowleft,arrowright', '',
				'KeyboardShortcutsHelp',
				event => {
					let next = 0;
					tabs.forEach((node, index) => {
						if (node.matches(':checked')) {
							if (['Tab','ArrowRight'].includes(event.key)) {
								next = index < last ? index+1 : 0;
							} else {
								next = index ? index-1 : last;
							}
						}
					});
					tabs[next].checked = true;
					return false;
				}
			);
		}
	}

	class AccountPopupView extends AbstractViewPopup {
		constructor() {
			super('Account');

			addObservablesTo(this, {
				isNew: true,

				name: '',
				email: '',
				password: '',

				submitRequest: false,
				submitError: '',
				submitErrorAdditional: ''
			});
		}

		hideError() {
			this.submitError('');
		}

		submitForm(form) {
			if (!this.submitRequest() && form.reportValidity()) {
				const data = new FormData(form);
				data.set('new', this.isNew() ? 1 : 0);
				this.submitRequest(true);
				Remote.request('AccountSetup', (iError, data) => {
						this.submitRequest(false);
						if (iError) {
							this.submitError(getNotification(iError));
							this.submitErrorAdditional(data?.messageAdditional);
						} else {
							loadAccountsAndIdentities();
							this.close();
						}
					}, data
				);
			}
		}

		onHide() {
			this.password('');
			this.submitRequest(false);
			this.submitError('');
			this.submitErrorAdditional('');
		}

		onShow(account) {
			let edit = account?.isAdditional();
			this.isNew(!edit);
			this.name(edit ? account.name : '');
			this.email(edit ? account.email : '');
		}
	}

	/*
		oCallbacks:
			ItemSelect
			MiddleClick
			canSelect
			ItemGetUid
			UpOrDown
	*/

	let shiftStart;

	class Selector {
		/**
		 * @param {koProperty} koList
		 * @param {koProperty} koSelectedItem
		 * @param {koProperty} koFocusedItem
		 * @param {string} sItemSelector
		 * @param {string} sItemCheckedSelector
		 */
		constructor(
			koList,
			koSelectedItem,
			koFocusedItem,
			sItemSelector,
			sItemCheckedSelector
		) {
			koFocusedItem = (koFocusedItem || ko.observable(null)).extend({ toggleSubscribeProperty: [this, 'focused'] });
			koSelectedItem = (koSelectedItem || ko.observable(null)).extend({ toggleSubscribeProperty: [null, 'selected'] });

			this.list = koList;
			this.listChecked = koComputable(() => koList.filter(item => item.checked())).extend({ rateLimit: 0 });

			this.focusedItem = koFocusedItem;
			this.selectedItem = koSelectedItem;

			this.iSelectNextHelper = 0;
			this.iFocusedNextHelper = 0;
	//		this.oContentScrollable = null;

			this.sItemSelector = sItemSelector;
			this.sItemCheckedSelector = sItemCheckedSelector;
			this.sItemFocusedSelector = sItemSelector + '.focused';

			this.sLastUid = '';
			this.oCallbacks = {};

			const
				itemSelected = item => {
					if (koList.hasChecked()) {
						item || this.oCallbacks.ItemSelect?.(null);
					} else if (item) {
						this.oCallbacks.ItemSelect?.(item);
					}
				},

				itemSelectedThrottle = (item => itemSelected(item)).debounce(300);

			this.listChecked.subscribe(items => {
				if (items.length) {
					koSelectedItem() ? koSelectedItem(null) : koSelectedItem.valueHasMutated?.();
				} else {
					this.autoSelect();
				}
			});

			let selectedItemUseCallback = true;

			koSelectedItem.subscribe(item => {
				if (item) {
	//				koList.forEach(subItem => subItem.checked(false));
					selectedItemUseCallback && itemSelectedThrottle(item);
				} else {
					selectedItemUseCallback && itemSelected();
				}
			});

			koFocusedItem.subscribe(item => item && (this.sLastUid = this.getItemUid(item)));

			/**
			 * Below code is used to keep checked/focused/selected states when array is refreshed.
			 */

			let aCheckedCache = [],
				mFocused = null,
				mSelected = null;

			// Before removing old list
			koList.subscribe(
				items => {
					if (isArray(items)) {
						items.forEach(item => {
							const uid = this.getItemUid(item);
							if (uid) {
								item.checked() && aCheckedCache.push(uid);
								if (!mFocused && item.focused()) {
									mFocused = uid;
								}
								if (!mSelected && item.selected()) {
									mSelected = uid;
								}
							}
						});
					}
				},
				this,
				'beforeChange'
			);

			koList.subscribe(aItems => {
				selectedItemUseCallback = false;

				this.unselect();

				if (isArray(aItems)) {
					let temp,
						isChecked,
						next = this.iFocusedNextHelper || this.iSelectNextHelper;

					aItems.forEach(item => {
						const uid = this.getItemUid(item);
						if (uid) {

							if (mFocused === uid) {
								koFocusedItem(item);
								mFocused = null;
							}

							if (aCheckedCache.includes(uid)) {
								item.checked(true);
								isChecked = true;
							}

							if (!isChecked && mSelected === uid) {
								koSelectedItem(item);
								mSelected = null;
							}
						}
					});

					selectedItemUseCallback = true;

					if (next && aItems.length && !koFocusedItem()) {
						temp = aItems[-1 === next ? aItems.length - 1 : 0];
						if (temp) {
							this.iSelectNextHelper && koSelectedItem(temp);

							koFocusedItem(temp);

							this.scrollToFocused();
							setTimeout(this.scrollToFocused, 100);
						}

						this.iSelectNextHelper = 0;
						this.iFocusedNextHelper = 0;
					}

					!isChecked && !koSelectedItem() && this.autoSelect();
				}

				aCheckedCache = [];
				mFocused = null;
				mSelected = null;
				selectedItemUseCallback = true;
			});
		}

		unselect() {
			this.selectedItem(null);
			this.focusedItem(null);
		}

		init(contentScrollable, keyScope = 'all') {
			this.oContentScrollable = contentScrollable;

			if (contentScrollable) {
				let getItem = selector => {
					let el = event.target.closestWithin(selector, contentScrollable);
					return el ? ko.dataFor(el) : null;
				};

				addEventsListeners(contentScrollable, {
					click: event => {
						const el = event.target.closestWithin(this.sItemSelector, contentScrollable);
						let item = el && ko.dataFor(el);
						el && (this.oCallbacks.click || (()=>1))(event, item) && this.actionClick(item, event);

						item = getItem(this.sItemCheckedSelector);
						if (item) {
							if (event.shiftKey) {
								this.actionClick(item, event);
							} else {
								this.focusedItem(item);
								item.checked(!item.checked());
							}
						}
					},
					auxclick: event => {
						if (1 == event.button) {
							const item = getItem(this.sItemSelector);
							if (item) {
								this.focusedItem(item);
								this.oCallbacks.MiddleClick?.(item);
							}
						}
					}
				});

				registerShortcut('enter,open', '', keyScope, () => {
					const focused = this.focusedItem();
					if (focused && !focused.selected()) {
						this.actionClick(focused);
						return false;
					}
				});

				addShortcut('arrowup,arrowdown', 'meta', keyScope, () => false);

				addShortcut('arrowup,arrowdown', 'shift', keyScope, event => {
					this.newSelectPosition(event.key, true);
					return false;
				});
				registerShortcut('arrowup,arrowdown,home,end,pageup,pagedown,space', '', keyScope, event => {
					this.newSelectPosition(event.key, false);
					return false;
				});
			}
		}

		/**
		 * @returns {boolean}
		 */
		autoSelect(bForce) {
			(bForce || (this.oCallbacks.canSelect || (()=>1))())
			&& this.focusedItem()
			&& this.selectedItem(this.focusedItem());
		}

		/**
		 * @param {Object} oItem
		 * @returns {string}
		 */
		getItemUid(item) {
			return (item && this.oCallbacks.ItemGetUid?.(item)?.toString()) || '';
		}

		/**
		 * @param {string} sEventKey
		 * @param {boolean} bShiftKey
		 * @param {boolean=} bForceSelect = false
		 */
		newSelectPosition(sEventKey, bShiftKey, bForceSelect) {
			let result;

			const up = 'ArrowUp' === sEventKey,
				isArrow = up || 'ArrowDown' === sEventKey,
				pageStep = 10,
				list = this.list(),
				listLen = list.length,
				focused = this.focusedItem();

			bShiftKey || (shiftStart = -1);

			if (' ' === sEventKey) {
				focused?.checked(!focused.checked());
			} else if (listLen) {
				if (focused) {
					if (isArrow) {
						let i = list.indexOf(focused);
						if (bShiftKey) {
							shiftStart = -1 < shiftStart ? shiftStart : i;
							shiftStart == i
								? focused.checked(true)
								: ((up ? shiftStart < i : shiftStart > i) && focused.checked(false));
						}
						if (up) {
							i > 0 && (result = list[--i]);
						} else if (++i < listLen) {
							result = list[i];
						}
						bShiftKey && result?.checked(true);
						result || this.oCallbacks.UpOrDown?.(up);
					} else if ('Home' === sEventKey) {
						result = list[0];
					} else if ('End' === sEventKey) {
						result = list[list.length - 1];
					} else if ('PageDown' === sEventKey) {
						let i = list.indexOf(focused);
						if (i < listLen - 1) {
							result = list[Math.min(i + pageStep, listLen - 1)];
						}
					} else if ('PageUp' === sEventKey) {
						let i = list.indexOf(focused);
						if (i > 0) {
							result = list[Math.max(0, i - pageStep)];
						}
					}
				} else if (
					'Home' == sEventKey ||
					'PageUp' == sEventKey
				) {
					result = list[0];
				} else if (
					'End' === sEventKey ||
					'PageDown' === sEventKey
				) {
					result = list[list.length - 1];
				}

				if (result) {
					this.focusedItem(result);
					!this.list.hasChecked() && this.autoSelect(bForceSelect);
					this.scrollToFocused();
				}
			}
		}

		/**
		 * @returns {boolean}
		 */
		scrollToFocused() {
			const scrollable = this.oContentScrollable;
			if (scrollable) {
				let focused = scrollable.querySelector(this.sItemFocusedSelector);
				if (focused) {
					const fRect = focused.getBoundingClientRect(),
						sRect = scrollable.getBoundingClientRect();
					if (fRect.top < sRect.top) {
						focused.scrollIntoView(true);
					} else if (fRect.bottom > sRect.bottom) {
						focused.scrollIntoView(false);
					}
				} else {
					scrollable.scrollTop = 0;
				}
			}
		}

		/**
		 * @returns {boolean}
		 */
		scrollToTop() {
			this.oContentScrollable && (this.oContentScrollable.scrollTop = 0);
		}

		/**
		 * @param {Object} item
		 * @param {Object=} event
		 */
		actionClick(item, event) {
			if (item) {
				let select = true;
				if (event && !event.altKey) {
					if (event.shiftKey && !event.ctrlKey && !event.metaKey) {
						const uid = this.getItemUid(item);
						if (uid && this.sLastUid && uid !== this.sLastUid) {
							let changeRange = false,
								isInRange = false,
								checked = !item.checked(),
								lineUid = '';
							this.list().forEach(listItem => {
								lineUid = this.getItemUid(listItem);
								changeRange = (lineUid === this.sLastUid || lineUid === uid);
								if (isInRange || changeRange) {
									if (changeRange) {
										isInRange = !isInRange;
									}
									listItem.checked(checked);
								}
							});
						}
						this.sLastUid = uid;
						this.focusedItem(item);
						return;
					}
					if (!event.shiftKey && (event.ctrlKey || event.metaKey)) {
						select = false;
						this.focusedItem(item);
						const selected = this.selectedItem();
						if (selected && item !== selected) {
							selected.checked(true);
						}
					}
				}

				select ? this.selectMessageItem(item) : item.checked(!item.checked());
			}
		}

		on(eventName, callback) {
			this.oCallbacks[eventName] = callback;
		}

		selectMessageItem(messageItem) {
			this.focusedItem(messageItem);
			this.selectedItem(messageItem);
			this.scrollToFocused();
		}
	}

	/**
	 * Inspired by https://github.com/mcpar-land/vcfer
	 */

	class VCardProperty {

		/**
		 * A class describing a single vCard property.
		 * Will almost always be a member of a
		 * {@link VCard}'s [props]{@link VCard.props} map.
		 *
		 * Accepts either 2-4 arguments, or 1 argument in jCard property format.
		 * @param arg the field, or a jCard property
		 * @param value
		 * @param params
		 * @param type
		 */
		constructor(arg, value, params, type = 'text')
		{
			this.field = '';

			/**
			 * the value of the property.
			 * @example '(123) 456 7890'
			 */
			this.value = '';

			/**
			 * the type of the property value.
			 * @example 'text'
			 */
			this.type = '';

			/**
			 * https://www.rfc-editor.org/rfc/rfc6350.html#section-5
			 * An jCard parameters object.
			 * @example
			 * {
			 * 	type: ['work', 'voice', 'pref'],
			 * 	value: 'uri'
			 * }
			 */
			this.params = {};

			// Construct from arguments
			if (value !== undefined && typeof arg === 'string') {
				this.field = arg;
				this.value = value;
				this.params = params || {};
				this.type = type;
			}
			// construct from jcard
			else if (value === undefined && params === undefined && typeof arg === 'object') {
				this.parseFromJCardProperty(arg);
			}
			// invalid property
			else {
				throw Error('invalid Property constructor');
			}
		}

		parseFromJCardProperty(jCardProp)
		{
			jCardProp = JSON.parse(JSON.stringify(jCardProp));
			this.field = jCardProp[0].toLowerCase();
			this.params = jCardProp[1];
			this.type = jCardProp[2];
			this.value = jCardProp[3];
		}

		addParam(key, value)
		{
			if (Array.isArray(this.params[key])) {
				this.params[key].push(value);
			}
			else if (this.params[key] != null) {
				this.params[key] = [this.params[key], value];
			}
			else {
				this.params[key] = value;
			}
		}

		/** Returns a copy of the Property's string value. */
		getValue()
		{
			return '' + this.value;
		}

		/**
		 * https://www.rfc-editor.org/rfc/rfc6350.html#section-5.3
		 */
		pref()
		{
			return this.params.pref || 100;
		}

		/**
		 * https://www.rfc-editor.org/rfc/rfc6350.html#section-5.6
		 */
		tags()
		{
			return this.params.type || [];
		}

		/** Returns `true` if all the following are true:
		 * - the property's value contains charactes other than `;`
		 * - the property has no parameters
		 */
		isEmpty()
		{
			return ((null == this.value || !/[^;]+/.test(this.value)) && !Object.keys(this.params).length);
		}

		notEmpty()
		{
			return !this.isEmpty();
		}

		/** Returns a readonly string copy of the property's field. */
		getField()
		{
			return '' + this.field;
		}

		/**
		 * Returns stringified JSON
		 */
		toString()
		{
			return JSON.stringify(this);
		}

		/**
		 * Returns a JSON array in a [jCard property]{@link JCardProperty} format
		 */
		toJSON()
		{
			return [
				this.field,
				this.params,
				this.type || 'text',
				this.value
			];
		}
	}

	/**
	 * https://datatracker.ietf.org/doc/html/rfc7095
	 *
	 * Inspired by https://github.com/mcpar-land/vcfer
	 */

	class JCard {

		constructor(input)
		{
			this.props = new Map();
			this.version = '4.0';
			if (input) {
				// read from jCard
				if (typeof input !== 'object') {
					throw Error('error reading vcard')
				}
				this.parseFromJCard(input);
			}
		}

		parseFromJCard(json)
		{
			json = JSON.parse(JSON.stringify(json));
			if (!/vcard/i.test(json[0])) {
				throw new SyntaxError('Incorrect jCard format');
			}
			json[1].forEach(jprop => this.add(new VCardProperty(jprop)));
		}

		/**
		 * Retrieve an array of {@link VCardProperty} objects under the specified field.
		 * Returns [] if there are no VCardProperty objects found.
		 * Properites are always stored in an array.
		 * @param field to get.
		 * @param type If provided, only return {@link VCardProperty}s with the specified
		 * type as a param.
		 */
		get(field, type)
		{
			if (type) {
				let props = this.props.get(field);
				return props
					? props.filter(prop => {
						let types = prop.type;
						return (Array.isArray(types) ? types : [types]).includes(type);
					})
					: [];
			}
			return this.props.get(field) || [];
			// TODO with type filter-er
		}

		/**
		 * Retrieve a _single_ VCardProperty of the specified field. Attempts to pick based
		 * on the following priorities, in order:
		 * - `TYPE={type}` of the value specified in the `type` argument. Ignored
		 * if the argument isn't supplied.
		 * - `TYPE=pref` is present.
		 * - is the VCardProperty at index 0 from get(field)
		 * @param field
		 * @param type
		 */
		getOne(field, type)
		{
			return this.get(field, type || 'pref')[0] || this.get(field)[0];
		}

		/**
		 * Set the contents of a field to contain a single {@link VCardProperty}.
		 *
		 * Accepts either 2-4 arguments to construct a VCardProperty,
		 * or 1 argument of a preexisting VCardProperty object.
		 *
		 * This will always overwrite all existing properties of the given
		 * field. For just adding a new VCardProperty, see {@link VCard#add}
		 * @param arg the field, or a VCardProperty object
		 * @param value the value for the VCardProperty object
		 * @param params the parameters for the VCardProperty object
		 * @param type the type for the VCardProperty object
		 */
		set(arg, value, params, type)
		{
			if (typeof arg === 'string') {
				arg = new VCardProperty(String(arg), value, params, type);
			}
			if (!(arg instanceof VCardProperty)) {
				throw Error('invalid argument of VCard.set(), expects string arguments or a VCardProperty');
			}
			let field = arg.getField();
			this.props.set(field, [arg]);
			return arg;
		}

		add(arg, value, params, type)
		{
			// string arguments
			if (typeof arg === 'string') {
				arg = new VCardProperty(String(arg), value, params, type);
			}
			if (!(arg instanceof VCardProperty)) {
				throw Error('invalid argument of VCard.add(), expects string arguments or a VCardProperty');
			}
			// VCardProperty arguments
			let field = arg.getField();
			if (this.props.get(field)) this.props.get(field)?.push(arg);
			else this.props.set(field, [arg]);
			return arg;
		}

		/**
		 * Removes a {@link VCardProperty}, or all properties of the supplied field.
		 * @param arg the field, or a {@link VCardProperty} object
		 * @param paramFilter (incomplete)
		 */
		remove(arg) {
			// string arguments
			if (typeof arg === 'string') {
				// TODO filter by param
				this.props.delete(arg);
			}
			// VCardProperty argument
			else if (arg instanceof VCardProperty) {
				let propArray = this.props.get(arg.getField());
				if (!propArray?.includes(arg))
					throw Error("Attempted to remove VCardProperty VCard does not have: ".concat(arg));
				propArray.splice(propArray.indexOf(arg), 1);
				if (propArray.length === 0)
					this.props.delete(arg.getField());
			}
			// incorrect arguments
			else
				throw Error('invalid argument of VCard.remove(), expects ' +
					'string and optional param filter or a VCardProperty');
		}

		/**
		 * Returns true if the vCard has at least one @{link VCardProperty}
		 * of the given field.
		 * @param field The field to query
		 */
		has(field)
		{
			return (!!this.props.get(field) && this.props.get(field).length > 0);
		}


		/**
		 * Returns stringified JSON
		 */
		toString()
		{
			return JSON.stringify(this);
		}

		/**
		 * Returns a {@link JCard} object as a JSON array.
		 */
		toJSON()
		{
			let data = [['version', {}, 'text', '4.0']];
	/*
			this.props.forEach((props, field) =>
				(field === 'version')  || props.forEach(prop => prop.isEmpty() || data.push(prop.toJSON()))
			);
	*/
			for (const [field, props] of this.props.entries()) {
				if ('version' !== field) {
					for (const prop of props) {
						prop.isEmpty() || data.push(prop.toJSON());
					}
				}
			}

			return ['vcard', data];
		}

		/**
		 * Automatically generate the 'fn' VCardProperty from the preferred 'n' VCardProperty.
		 *
		 * #### `set` (`boolean`)
		 *
		 * - `false`: (default) return the generated full name string without
		 * modifying the VCard.
		 *
		 * - `true`: modify the VCard's `fn` VCardProperty directly, as specified
		 * by `append`
		 *
		 * #### `append` (`boolean`)
		 *
		 * (ignored if `set` is `false`)
		 *
		 * - `false`: (default) replace the existing 'fn' VCardProperty/properties with
		 * a new one.
		 *
		 * - `true`: append a new `fn` VCardProperty to the array.
		 *
		 * see: [RFC 6350 section 6.2.1](https://tools.ietf.org/html/rfc6350#section-6.2.1)
		 */
		parseFullName(options) {
			let n = this.getOne('n');
			if (n === undefined) {
				throw Error('\'fn\' VCardProperty not present in card, cannot parse full name');
			}
			let fnString = '';
			// Position in n -> position in fn
			[3, 1, 2, 0, 4].forEach(pos => {
				let splitStr = n.value[pos];
				if (splitStr) {
					// comma separated values separated by spaces
					fnString += ' ' + splitStr.replace(',', ' ');
				}
			});
			fnString = fnString.trim();
			let fn = new VCardProperty('fn', fnString);
			if (options?.set) {
				if (options.append) {
					this.add(fn);
				} else {
					this.set(fn);
				}
			}
			return fn;
		}
	}

	//import { VCardProperty } from 'DAV/VCardProperty';

	const nProps = [
		'surName',
		'givenName',
		'middleName',
		'namePrefix',
		'nameSuffix'
	];

	/*
	const propertyMap = [
		// vCard 2.1 properties and up
		'N' => 'Text',
		'FN' => 'FlatText',
		'PHOTO' => 'Binary',
		'BDAY' => 'DateAndOrTime',
		'ADR' => 'Text',
		'TEL' => 'FlatText',
		'EMAIL' => 'FlatText',
		'GEO' => 'FlatText',
		'TITLE' => 'FlatText',
		'ROLE' => 'FlatText',
		'LOGO' => 'Binary',
		'ORG' => 'Text',
		'NOTE' => 'FlatText',
		'REV' => 'TimeStamp',
		'SOUND' => 'FlatText',
		'URL' => 'Uri',
		'UID' => 'FlatText',
		'VERSION' => 'FlatText',
		'KEY' => 'FlatText', // <uri>data:application/pgp-keys;base64,AZaz09==</uri>
		'TZ' => 'Text',

		// vCard 3.0 properties
		'CATEGORIES' => 'Text',
		'SORT-STRING' => 'FlatText',
		'PRODID' => 'FlatText',
		'NICKNAME' => 'Text',

		// rfc2739 properties
		'FBURL' => 'Uri',
		'CAPURI' => 'Uri',
		'CALURI' => 'Uri',
		'CALADRURI' => 'Uri',

		// rfc4770 properties
		'IMPP' => 'Uri',

		// vCard 4.0 properties
		'SOURCE' => 'Uri',
		'XML' => 'FlatText',
		'ANNIVERSARY' => 'DateAndOrTime',
		'CLIENTPIDMAP' => 'Text',
		'LANG' => 'LanguageTag',
		'GENDER' => 'Text',
		'KIND' => 'FlatText',
		'MEMBER' => 'Uri',
		'RELATED' => 'Uri',

		// rfc6474 properties
		'BIRTHPLACE' => 'FlatText',
		'DEATHPLACE' => 'FlatText',
		'DEATHDATE' => 'DateAndOrTime',

		// rfc6715 properties
		'EXPERTISE' => 'FlatText',
		'HOBBY' => 'FlatText',
		'INTEREST' => 'FlatText',
		'ORG-DIRECTORY' => 'FlatText
	];
	*/

	class ContactModel extends AbstractModel {
		constructor() {
			super();

			this.jCard = ['vcard',[]];

			addObservablesTo(this, {
				// Also used by Selector
				focused: false,
				selected: false,
				checked: false,
				sendToAll: true,

				deleted: false,
				readOnly: false,

				id: 0,
				givenName:  '', // FirstName
				surName:    '', // LastName
				middleName: '', // MiddleName
				namePrefix: '', // NamePrefix
				nameSuffix: '',  // NameSuffix
				nickname: null,
				note: null,

				// Business
				org: '',
				department: '',
				title: '',

				// Crypto
				encryptpref: '',
				signpref: ''
			});
	//		this.email = koArrayWithDestroy();
			this.email = ko.observableArray();
			this.tel   = ko.observableArray();
			this.url   = ko.observableArray();
			this.adr   = ko.observableArray();

			addComputablesTo(this, {
				fullName: () => [this.namePrefix(), this.givenName(), this.middleName(), this.surName()].join(' ').trim(),

				display: () => {
					let a = this.fullName(),
						b = this.email()[0]?.value(),
						c = this.nickname();
					return a || b || c;
				}
	/*
				fullName: {
					read: () => this.givenName() + " " + this.surName(),
					write: value => {
						this.jCard.set('fn', value/*, params, group* /)
					}
				}
	*/
			});
		}

		/**
		 * @static
		 * @param {jCard} json
		 * @returns {?ContactModel}
		 */
		static reviveFromJson(json) {
			const contact = super.reviveFromJson(json);
			if (contact) {
				let jCard = new JCard(json.jCard),
					props = jCard.getOne('n')?.value;
				props && props.forEach((value, index) =>
					value && contact[nProps[index]](value)
				);

				['nickname', 'note', 'title'].forEach(field => {
					props = jCard.getOne(field);
					props && contact[field](props.value);
				});

				if ((props = jCard.getOne('org')?.value)) {
					contact.org(props[0]);
					contact.department(props[1] || '');
				}

				['email', 'tel', 'url'].forEach(field => {
					props = jCard.get(field);
					props && props.forEach(prop => {
						contact[field].push({
							value: ko.observable(prop.value)
	//						type: prop.params.type
						});
					});
				});

				props = jCard.get('adr');
				props && props.forEach(prop => {
					contact.adr.push({
						street: ko.observable(prop.value[2]),
						street_ext: ko.observable(prop.value[1]),
						locality: ko.observable(prop.value[3]),
						region: ko.observable(prop.value[4]),
						postcode: ko.observable(prop.value[5]),
						pobox: ko.observable(prop.value[0]),
						country: ko.observable(prop.value[6]),
						preferred: ko.observable(prop.params.pref),
						type: ko.observable(prop.params.type) // HOME | WORK
					});
				});

				props = jCard.getOne('x-crypto');
				contact.signpref(props?.params.signpref || 'Ask');
				contact.encryptpref(props?.params.encryptpref || 'Ask');
	//			contact.encryptpref(props?.params.allowed || 'PGP/INLINE,PGP/MIME,S/MIME,S/MIMEOpaque');

				contact.jCard = json.jCard;
			}
			return contact;
		}

		addEmail() {
			// home, work
			this.email.push({
				value: ko.observable('')
	//			type: prop.params.type
			});

			if (this.sendToAllDisplayStatus())
				document.getElementById('send-to-all').style.display = 'block';
		}

		addTel() {
			// home, work, text, voice, fax, cell, video, pager, textphone, iana-token, x-name
			this.tel.push({
				value: ko.observable('')
	//			type: prop.params.type
			});
		}

		addUrl() {
			// home, work
			this.url.push({
				value: ko.observable('')
	//			type: prop.params.type
			});
		}

		addNickname() {
			// home, work
			this.nickname() || this.nickname('');
		}

		addNote() {
			this.note() || this.note('');
		}

		hasChanges()
		{
			return this.email().filter(v => v.length).length && this.toJSON().jCard != JSON.stringify(this.jCard);
		}

		toJSON()
		{
			let jCard = new JCard(this.jCard);
			jCard.set('n', [
				this.surName(),
				this.givenName(),
				this.middleName(),
				this.namePrefix(),
				this.nameSuffix()
			]/*, params, group*/);
			jCard.parseFullName({set:true});

			['nickname', 'note', 'title'].forEach(field =>
				this[field]() ? jCard.set(field, this[field]()/*, params, group*/) : jCard.remove(field)
			);

			if (this.org()) {
				let org = [this.org()];
				if (this.department()) {
					org.push(this.department());
				}
				let prop = jCard.getOne('org');
				prop ? prop.value = org : jCard.set('org', org);
			} else {
				jCard.remove('');
			}

			['email', 'tel', 'url'].forEach(field => {
				let values = this[field].map(item => item.value());
				jCard.get(field).forEach(prop => {
					let i = values.indexOf(prop.value);
					if (0 > i || !prop.value) {
						jCard.remove(prop);
					} else {
						values.splice(i, 1);
					}
				});
				values.forEach(value => value && jCard.add(field, value));
			});

			jCard.set('x-crypto', '', {
				allowed: 'PGP/INLINE,PGP/MIME,S/MIME,S/MIMEOpaque',
				signpref: this.signpref(),
				encryptpref: this.encryptpref()
			}, 'x-crypto');

			// Done by server
	//		jCard.set('rev', '2022-05-21T10:59:52Z')

			return {
				uid: this.id,
				jCard: JSON.stringify(jCard)
			};
		}

		/**
		 * @return string
		 */
		lineAsCss() {
			return (this.selected() ? 'selected' : '')
				+ (this.deleted() ? ' deleted' : '')
				+ (this.checked() ? ' checked' : '')
				+ (this.focused() ? ' focused' : '');
		}

		sendToAllDisplayStatus() {
			return this.email.length > 1
		}

	}

	const
		CONTACTS_PER_PAGE = 50,
		ScopeContacts = 'Contacts';

	let
		bOpenCompose = false,
		sComposeRecipientsField = '';

	class ContactsPopupView extends AbstractViewPopup {
		constructor() {
			super('Contacts');

			addObservablesTo(this, {
				search: '',
				contactsCount: 0,

				selectorContact: null,

				importButton: null,

				contactsPage: 1,

				isSaving: false,

				contact: null
			});

			this.contacts = ContactUserStore;

			this.useCheckboxesInList = SettingsUserStore.useCheckboxesInList;

			this.selector = new Selector(
				ContactUserStore,
				this.selectorContact,
				null,
				'.e-contact-item',
				'.e-contact-item .checkboxItem'
			);

			this.selector.on('ItemSelect', contact => this.populateViewContact(contact));

			this.selector.on('ItemGetUid', contact => contact ? contact.id() : '');

			addComputablesTo(this, {
				contactsPaginator: computedPaginatorHelper(
					this.contactsPage,
					() => Math.max(1, Math.ceil(this.contactsCount() / CONTACTS_PER_PAGE))
				),

				contactsCheckedOrSelected: () => {
					const checked = ContactUserStore.filter(item => item.checked()),
						selected = this.selectorContact();
					return checked.length ? checked : (selected ? [selected] : []);
				},

				contactsSyncEnabled: () => ContactUserStore.allowSync() && ContactUserStore.syncMode(),

				isBusy: () => ContactUserStore.syncing() | ContactUserStore.importing() | ContactUserStore.loading()
					| this.isSaving()
			});

			this.search.subscribe(() => this.reloadContactList());

			this.saveCommand = this.saveCommand.bind(this);

			decorateKoCommands(this, {
				deleteCommand: self => !self.isBusy() && 0 < self.contactsCheckedOrSelected().length,
				newMessageCommand: self => !self.isBusy() && 0 < self.contactsCheckedOrSelected().length,
				saveCommand: self => !self.isBusy(),
				syncCommand: self => !self.isBusy()
			});
		}

		newContact() {
			this.populateViewContact(new ContactModel);
			this.selectorContact(null);
		}

		deleteCommand() {
			const contacts = this.contactsCheckedOrSelected();
			if (contacts.length) {
				let selectorContact = this.selectorContact(),
					uids = [],
					count = 0;
				contacts.forEach(contact => {
					uids.push(contact.id());
					if (selectorContact && selectorContact.id() === contact.id()) {
						this.selectorContact(selectorContact = null);
					}
					contact.deleted(true);
					++count;
				});
				Remote.request('ContactsDelete',
					(iError, oData) => {
						if (iError) {
							alert(oData?.message || getNotification(iError));
						} else {
							const page = this.contactsPage();
							if (page > Math.max(1, Math.ceil((this.contactsCount() - count) / CONTACTS_PER_PAGE))) {
								this.contactsPage(page - 1);
							}
	//						contacts.forEach(contact => ContactUserStore.remove(contact));
						}
						this.reloadContactList();
					}, {
						uids: uids.join(',')
					}
				);
			}
		}

		newMessageCommand() {
			let aE = [],
				recipients = {to:null,cc:null,bcc:null};

			this.contactsCheckedOrSelected().forEach(oContact => {
				if (oContact) {
					let name = (oContact.givenName() + ' ' + oContact.surName()).trim(),
						email,
						addresses = oContact.email();
					if (!oContact.sendToAll()) {
						addresses = addresses.slice(0,1);
					}
					addresses.forEach(address => {
						email = new EmailModel(address.value(), name);
						email.valid() && aE.push(email);
					});
	/*
			//		oContact.jCard.getOne('fn')?.notEmpty() ||
					oContact.jCard.parseFullName({set:true});
			//		let name = oContact.jCard.getOne('nickname'),
					let name = oContact.jCard.getOne('fn'),
						email = [oContact.jCard.getOne('email')];
	*/
				}
			});

			if (arrayLength(aE)) {
				bOpenCompose = false;
				this.close();
				recipients[sComposeRecipientsField] = aE;
				showMessageComposer([ComposeType.Empty, null, recipients.to, recipients.cc, recipients.bcc]);
			}
		}

		clearSearch() {
			this.search('');
		}

		saveCommand() {
			this.saveContact(this.contact());
		}

		saveContact(contact) {
			const data = contact.toJSON();
			if (data.jCard != JSON.stringify(contact.jCard)) {
				this.isSaving(true);
				Remote.request('ContactSave',
					(iError, oData) => {
						if (iError) {
							alert(oData?.message || getNotification(iError));
						} else if (oData.Result.ResultID) {
							if (contact.id()) {
								contact.id(oData.Result.ResultID);
								contact.jCard = JSON.parse(data.jCard);
							} else {
								this.reloadContactList(); // TODO: remove when e-contact-foreach is dynamic
							}
						}
						this.isSaving(false);
					}, data
				);
			}
		}

		syncCommand() {
			ContactUserStore.sync(iError => {
				iError && alert(getNotification(iError));
				this.reloadContactList(true);
			});
		}

		exportVcf() {
			download(serverRequestRaw('ContactsVcf'), 'contacts.vcf');
		}

		exportCsv() {
			download(serverRequestRaw('ContactsCsv'), 'contacts.csv');
		}

		/**
		 * @param {?ContactModel} contact
		 */
		populateViewContact(contact) {
			const oldContact = this.contact(),
				fn = () => this.contact(contact);
			if (oldContact?.hasChanges()) {
				AskPopupView.showModal([
					i18n('GLOBAL/SAVE_CHANGES'),
					() => this.saveContact(oldContact) | fn(),
					fn
				]);
			} else fn();
		}

		/**
		 * @param {boolean=} dropPagePosition = false
		 */
		reloadContactList(dropPagePosition = false) {
			let offset = (this.contactsPage() - 1) * CONTACTS_PER_PAGE;

			if (dropPagePosition) {
				this.contactsPage(1);
				offset = 0;
			}

			ContactUserStore.loading(true);
			Remote.abort('Contacts').request('Contacts',
				(iError, data) => {
					let count = 0,
						list = [];

					if (iError) {
	//					console.error(data);
						alert(data?.message || getNotification(iError));
					} else if (arrayLength(data.Result.List)) {
						data.Result.List.forEach(item => {
							item = ContactModel.reviveFromJson(item);
							item && list.push(item);
						});
						count = pInt(data.Result.Count);
					}

					this.contactsCount(0 < count ? count : 0);

					ContactUserStore(list);

					ContactUserStore.loading(false);
				},
				{
					Offset: offset,
					Limit: CONTACTS_PER_PAGE,
					Search: this.search()
				}
			);
		}

		onBuild(dom) {
			this.selector.init(dom.querySelector('.b-list-content'), ScopeContacts);

			registerShortcut('delete', '', ScopeContacts, () => {
				this.deleteCommand();
				return false;
			});

			registerShortcut('c,w', '', ScopeContacts, () => {
				this.newMessageCommand();
				return false;
			});

			const self = this;

			dom.addEventListener('click', event => {
				let el = event.target.closestWithin('.e-paginator a', dom);
				if (el && (el = pInt(ko.dataFor(el)?.value))) {
					self.contactsPage(el);
					self.reloadContactList();
				}
			});

			// initUploader

			if (this.importButton()) {
				const j = new Jua({
					action: serverRequest('UploadContacts'),
					limit: 1,
					clickElement: this.importButton()
				});

				if (j) {
					j.on('onStart', () => {
						ContactUserStore.importing(true);
					}).on('onComplete', (id, result, data) => {
						ContactUserStore.importing(false);
						this.reloadContactList();
						if (!id || !result || !data || !data.Result) {
							alert(i18n('CONTACTS/ERROR_IMPORT_FILE'));
						}
					});
				}
			}
		}

		onClose() {
			const contact = this.contact();
			if (AskPopupView.hidden() && contact?.hasChanges()) {
				AskPopupView.showModal([
					i18n('GLOBAL/SAVE_CHANGES'),
					() => this.close() | this.saveContact(contact),
					() => this.close()
				]);
				return false;
			}
		}

		onShow(bBackToCompose, sRecipientsField) {
			bOpenCompose = !!bBackToCompose;
			sComposeRecipientsField = ['to','cc','bcc'].includes(sRecipientsField) ? sRecipientsField : 'to';
			this.reloadContactList(true);
		}

		onHide() {
			this.contact(null);
			this.selectorContact(null);
			this.search('');
			this.contactsCount(0);

			ContactUserStore([]);

			bOpenCompose && showMessageComposer();
		}
	}

	class SystemDropDownUserView extends AbstractViewRight {
		constructor() {
			super();

			this.allowAccounts = SettingsCapa('AdditionalAccounts');

			this.accountEmail = AccountUserStore.email;

			this.accounts = AccountUserStore;
			this.accountsLoading = AccountUserStore.loading;
	/*
			this.accountsUnreadCount = : koComputable(() => 0);
			this.accountsUnreadCount = : koComputable(() => AccountUserStore().reduce((result, item) => result + item.count(), 0));
	*/

			addObservablesTo(this, {
				currentAudio: '',
				// bootstrap dropdown
				accountMenu: null
			});

			this.allowContacts = AppUserStore.allowContacts();

			addEventListener('audio.stop', () => this.currentAudio(''));
			addEventListener('audio.start', e => this.currentAudio(e.detail));
		}

		stopPlay() {
			fireEvent('audio.api.stop');
		}

		accountClick(account, event) {
			let email = account?.email;
			if (email && 0 === event.button && AccountUserStore.email() != email) {
				AccountUserStore.loading(true);
				stopEvent(event);
				Remote.request('AccountSwitch',
					(iError/*, oData*/) => {
						if (iError) {
							AccountUserStore.loading(false);
							alert('Account error: ' + getNotification(iError).replace('%EMAIL%', email));
							if (account.isAdditional()) {
								showScreenPopup(AccountPopupView, [account]);
							}
						} else {
	/*						// Not working yet
							forEachObjectEntry(oData.Result, (key, value) => rl.settings.set(key, value));
	//						MessageUserStore.message();
	//						MessageUserStore.purgeCache();
							MessagelistUserStore([]);
	//						FolderUserStore.folderList([]);
							loadFolders(value => {
								if (value) {
	//								4. Change to INBOX = reload MessageList
	//								MessagelistUserStore.setMessageList();
								}
							});
							AccountUserStore.loading(false);
	*/
							rl.route.reload();
						}
					}, {Email:email}
				);
			}
			return true;
		}

		accountName() {
			const email = AccountUserStore.email();
			return AccountUserStore.find(account => account.email == email)?.label() || IDN.toUnicode(email);
		}

		settingsClick() {
			hasher.setHash(settings());
		}

		settingsHelp() {
			showScreenPopup(KeyboardShortcutsHelpPopupView);
		}

		addAccountClick() {
			this.allowAccounts && showScreenPopup(AccountPopupView);
		}

		contactsClick() {
			this.allowContacts && showScreenPopup(ContactsPopupView);
		}

		logoutClick() {
			rl.app.logout();
		}

		onBuild() {
			registerShortcut('m', '', [ScopeMessageList, ScopeMessageView, ScopeSettings], () => {
				if (!this.viewModelDom.hidden) {
	//				exitFullscreen();
					this.accountMenu().ddBtn.toggle();
					return false;
				}
			});

			// shortcuts help
			registerShortcut('?,f1,help', '', [ScopeMessageList, ScopeMessageView, ScopeSettings], () => {
				if (!this.viewModelDom.hidden) {
					showScreenPopup(KeyboardShortcutsHelpPopupView);
					return false;
				}
			});
		}
	}

	class FolderCreatePopupView extends AbstractViewPopup {
		constructor() {
			super('FolderCreate');

			addObservablesTo(this, {
				name: '',
				subscribe: true,
				parentFolder: ''
			});

			this.parentFolderSelectList = koComputable(() =>
				folderListOptionsBuilder(
					[],
					[['', '']],
					oItem => oItem ? oItem.detailedName() : '',
					item => !item.subFolders.allow
						|| (FolderUserStore.namespace && !item.fullName.startsWith(FolderUserStore.namespace))
				)
			);

			this.defaultOptionsAfterRender = defaultOptionsAfterRender;
		}

		submitForm(form) {
			if (form.reportValidity()) {
				const data = new FormData(form);

				let parentFolderName = this.parentFolder();
				if (!parentFolderName && 1 < FolderUserStore.namespace.length) {
					data.set('parent', FolderUserStore.namespace.slice(0, FolderUserStore.namespace.length - 1));
				}

				Remote.abort('Folders').post('FolderCreate', FolderUserStore.foldersCreating, data)
					.then(
						data => {
							const folder = getFolderFromCacheList(parentFolderName),
								subFolder = FolderModel.reviveFromJson(data.Result),
								folders = (folder ? folder.subFolders : FolderUserStore.folderList);
							setFolder(subFolder);
							folders.push(subFolder);
							sortFolders(folders);
	/*
							var collator = baseCollator(true);
							console.log((folder ? folder.subFolders : FolderUserStore.folderList).sort(collator.compare));
	*/
						},
						error => {
							FolderUserStore.error(
								getNotification(error.code, '', Notifications.CantCreateFolder)
								+ '.\n' + error.message);
						}
					);

				this.close();
			}
		}

		onShow() {
			this.name('');
			this.subscribe(true);
			this.parentFolder('');
		}
	}

	class ComposeAttachmentModel extends AbstractModel {
		/**
		 * @param {string} id
		 * @param {string} fileName
		 * @param {?number=} size = null
		 * @param {boolean=} isInline = false
		 * @param {boolean=} isLinked = false
		 * @param {string=} cId = ''
		 * @param {string=} contentLocation = ''
		 */
		constructor(id, fileName, size = null, isInline = false, isLinked = false, cId = '', contentLocation = '') {
			super();

			this.id = id;
			this.isInline = !!isInline;
			this.isLinked = !!isLinked;
			this.cId = cId;
			this.contentLocation = contentLocation;
			this.fromMessage = false;

			addObservablesTo(this, {
				fileName: fileName,
				size: size,
				tempName: '',
				type: '', // application/octet-stream

				progress: 0,
				error: '',
				waiting: true,
				uploading: false,
				enabled: true,
				complete: false
			});

			addComputablesTo(this, {
				progressText: () => {
					const p = this.progress();
					return 1 > p ? '' : (100 < p ? 100 : p) + '%';
				},

				progressStyle: () => {
					const p = this.progress();
					return 1 > p ? '' : 'width:' + (100 < p ? 100 : p) + '%';
				},

				title: () => this.error() || this.fileName(),

				friendlySize: () => {
					const localSize = this.size();
					return null === localSize ? '' : FileInfo.friendlySize(localSize);
				},

				mimeType: () => this.type() || FileInfo.getContentType(this.fileName()),
				fileExt: () => FileInfo.getExtension(this.fileName()),

				iconClass: () => FileInfo.getIconClass(this.fileExt(), this.mimeType())
			});
		}
	}

	//import { AbstractModel } from 'Knoin/AbstractModel';

	class MimeHeaderAutocryptModel/* extends AbstractModel*/
	{
		constructor(value) {
	//		super();
			this.addr = '';
			this.prefer_encrypt = 'nopreference', // nopreference or mutual
			this.keydata = '';

			if (value) {
				value.split(';').forEach(entry => {
					entry = entry.match(/^([^=]+)=(.*)$/);
					const trim = str => (str || '').trim().replace(/^["']|["']+$/g, '');
					this[trim(entry[1]).replace('-', '_')] = trim(entry[2]);
				});
				this.keydata = this.keydata.replace(/\s+/g, '\n');
			}
		}

		toString() {
			let result = `addr=${this.addr}; `;
			if ('mutual' === this.prefer_encrypt) {
				result += 'prefer-encrypt=mutual; ';
			}
			return result + 'keydata=' + this.keydata.replace(/\n/g, '\n ');
		}

		pem() {
			return '-----BEGIN PGP PUBLIC KEY BLOCK-----\n\n'
				+ this.keydata
				+ '\n-----END PGP PUBLIC KEY BLOCK-----';
		}
	}

	class FolderSystemPopupView extends AbstractViewPopup {
		constructor() {
			super('FolderSystem');

			this.notification = ko.observable('');

			this.folderSelectList = koComputable(() =>
				folderListOptionsBuilder(
					FolderUserStore.systemFoldersNames(),
					[
						['', i18n('POPUPS_SYSTEM_FOLDERS/SELECT_CHOOSE_ONE')],
						[UNUSED_OPTION_VALUE, i18n('POPUPS_SYSTEM_FOLDERS/SELECT_UNUSE_NAME')]
					]
				)
			);

			this.sentFolder = FolderUserStore.sentFolder;
			this.draftsFolder = FolderUserStore.draftsFolder;
			this.spamFolder = FolderUserStore.spamFolder;
			this.trashFolder = FolderUserStore.trashFolder;
			this.archiveFolder = FolderUserStore.archiveFolder;

			const fSaveSystemFolders = (()=>FolderUserStore.saveSystemFolders()).debounce(1000);

			addSubscribablesTo(FolderUserStore, {
				sentFolder: fSaveSystemFolders,
				draftsFolder: fSaveSystemFolders,
				spamFolder: fSaveSystemFolders,
				trashFolder: fSaveSystemFolders,
				archiveFolder: fSaveSystemFolders
			});

			this.defaultOptionsAfterRender = defaultOptionsAfterRender;
		}

		/**
		 * @param {number=} notificationType = 0
		 */
		onShow(notificationType = 0) {
			let notification = '', prefix = 'POPUPS_SYSTEM_FOLDERS/NOTIFICATION_';
			switch (notificationType) {
				case FolderType.Sent:
					notification = i18n(prefix + 'SENT');
					break;
				case FolderType.Drafts:
					notification = i18n(prefix + 'DRAFTS');
					break;
				case FolderType.Junk:
					notification = i18n(prefix + 'SPAM');
					break;
				case FolderType.Trash:
					notification = i18n(prefix + 'TRASH');
					break;
				case FolderType.Archive:
					notification = i18n(prefix + 'ARCHIVE');
					break;
				// no default
			}

			this.notification(notification);
		}
	}

	/*
	import { ThemeStore } from 'Stores/Theme';

	let alreadyFullscreen;
	*/
	let oLastMessage;

	const
		ScopeCompose = 'Compose',

		tpl = createElement('template'),

		base64_encode = text => text ? b64Encode(text).match(/.{1,76}/g).join('\r\n') : '',

		getEmail = value => addressparser(value)[0]?.email || false,

		/**
		 * @param {Array} aList
		 * @param {boolean} bFriendly
		 * @returns {string}
		 */
		emailArrayToStringLineHelper = (aList, bFriendly) =>
			aList.filter(item => item.email).map(item => item.toLine(bFriendly)).join(', '),

		reloadDraftFolder = () => {
			const draftsFolder = FolderUserStore.draftsFolder();
			if (draftsFolder && UNUSED_OPTION_VALUE !== draftsFolder) {
				setFolderETag(draftsFolder, '');
				if (FolderUserStore.currentFolderFullName() === draftsFolder) {
					MessagelistUserStore.reload(true);
				} else {
					folderInformation(draftsFolder);
				}
			}
		},

		findIdentity = addresses => {
			addresses = addresses.map(item => item.email);
			return IdentityUserStore.find(item => addresses.includes(item.email()));
		},

		/**
		 * @param {Function} fKoValue
		 * @param {Array} emails
		 */
		addEmailsTo = (fKoValue, emails) => {
			if (arrayLength(emails)) {
				const value = fKoValue().trim(),
					values = emails.map(item => item ? item.toLine() : null)
						.validUnique();

				fKoValue(value + (value ? ', ' :  '') + values.join(', ').trim());
			}
		},

		isPlainEditor = () => 'Plain' === SettingsUserStore.editorDefaultType(),

		/**
		 * @param {string} prefix
		 * @param {string} subject
		 * @returns {string}
		 */
		replySubjectAdd = (prefix, subject) => {
			prefix = prefix.toUpperCase().trim();
			subject = subject.replace(/\s+/g, ' ').trim();

			let drop = false,
				re = 'RE' === prefix,
				fwd = 'FWD' === prefix;

			const parts = [],
				prefixIsRe = !fwd;

			if (subject) {
				subject.split(':').forEach(part => {
					const trimmedPart = part.trim();
					if (!drop && (/^(RE|FWD)$/i.test(trimmedPart) || /^(RE|FWD)[[(][\d]+[\])]$/i.test(trimmedPart))) {
						if (!re) {
							re = !!/^RE/i.test(trimmedPart);
						}

						if (!fwd) {
							fwd = !!/^FWD/i.test(trimmedPart);
						}
					} else {
						parts.push(part);
						drop = true;
					}
				});
			}

			if (prefixIsRe) {
				re = false;
			} else {
				fwd = false;
			}

			return ((prefixIsRe ? 'Re: ' : 'Fwd: ') + (re ? 'Re: ' : '')
				+ (fwd ? 'Fwd: ' : '') + parts.join(':').trim()).trim();
		};

	ko.extenders.toggleSubscribe = (target, options) => {
		target.subscribe(options[1], options[0], 'beforeChange');
		target.subscribe(options[2], options[0]);
		return target;
	};

	class MimePart {
		constructor() {
			this.headers = {};
			this.body = '';
			this.boundary = '';
			this.children = [];
		}

		toString() {
			const hasSub = this.children.length,
				boundary = this.boundary || (this.boundary = 'part' + Jua.randomId()),
				headers = this.headers;
			if (hasSub && !headers['Content-Type'].includes(boundary)) {
				headers['Content-Type'] += `; boundary="${boundary}"`;
			}
			let result = Object.entries(headers).map(([key, value]) => `${key}: ${value}`).join('\r\n') + '\r\n';
			if (this.body) {
				result += '\r\n' + this.body.replace(/\r?\n/g, '\r\n');
			}
			if (hasSub) {
				this.children.forEach(part => result += '\r\n--' + boundary + '\r\n' + part);
				result += '\r\n--' + boundary + '--\r\n';
			}
			return result;
		}
	}

	class ComposePopupView extends AbstractViewPopup {
		constructor() {
			super('Compose');

			const fEmailOutInHelper = (context, identity, name, isIn) => {
				const identityEmail = context && identity?.[name]();
				if (identityEmail && (isIn ? true : context[name]())) {
					let list = context[name]().trim().split(',');

					list = list.filter(email => {
						email = email.trim();
						return email && identityEmail.trim() !== email;
					});

					isIn && list.push(identityEmail);

					context[name](list.join(','));
				}
			};

			this.oEditor = null;

			this.sLastFocusedField = 'to';

			this.allowContacts = AppUserStore.allowContacts();
			this.allowIdentities = SettingsCapa('Identities');
			this.allowSpellcheck = SettingsUserStore.allowSpellcheck;

			addObservablesTo(this, {
				// bootstrap dropdown
				identitiesMenu: null,

				from: '',
				to: '',
				cc: '',
				bcc: '',
				replyTo: '',

				subject: '',

				isHtml: false,

				requestDsn: false,
				requestReadReceipt: false,
				requireTLS: false,
				markAsImportant: false,

				sendError: false,
				sendSuccessButSaveError: false,
				savedError: false,

				sendErrorDesc: '',
				savedErrorDesc: '',

				savedTime: 0,

				emptyToError: false,

				attachmentsInProcessError: false,
				attachmentsInErrorError: false,

				showCc: false,
				showBcc: false,
				showReplyTo: false,

				doSign: false,
				doEncrypt: false,

				draftsFolder: '',
				draftUid: 0,
				sending: false,
				saving: false,

				viewArea: 'body',

				attacheMultipleAllowed: false,
				addAttachmentEnabled: false,

				editorArea: null, // initDom

				currentIdentity: IdentityUserStore()[0]
			});

			// Used by ko.bindingHandlers.emailsTags
			['to','cc','bcc'].forEach(name => {
				this[name].focused = ko.observable(false);
				this[name].focused.subscribe(value => value && (this.sLastFocusedField = name));
			});

			this.attachments = koArrayWithDestroy();
			this.encryptOptions = koArrayWithDestroy();
			this.signOptions = koArrayWithDestroy();

			this.dragAndDropOver = ko.observable(false).extend({ debounce: 1 });
			this.dragAndDropVisible = ko.observable(false).extend({ debounce: 1 });

			this.currentIdentity.extend({
				toggleSubscribe: [
					this,
					(identity) => {
						fEmailOutInHelper(this, identity, 'bcc');
						fEmailOutInHelper(this, identity, 'replyTo');
					},
					(identity) => {
						fEmailOutInHelper(this, identity, 'bcc', true);
						fEmailOutInHelper(this, identity, 'replyTo', true);
					}
				]
			});

			this.doClose = this.doClose.debounce(200);

			this.iTimer = 0;

			addComputablesTo(this, {
				sendButtonSuccess: () => !this.sendError() && !this.sendSuccessButSaveError(),

				savedTimeText: () =>
					this.savedTime() ? i18n('COMPOSE/SAVED_TIME', { TIME: this.savedTime().format('LT') }) : '',

				emptyToErrorTooltip: () => (this.emptyToError() ? i18n('COMPOSE/EMPTY_TO_ERROR_DESC') : ''),

				attachmentsErrorTooltip: () => {
					let result = '';
					switch (true) {
						case this.attachmentsInProcessError():
							result = i18n('COMPOSE/ATTACHMENTS_UPLOAD_ERROR_DESC');
							break;
						case this.attachmentsInErrorError():
							result = i18n('COMPOSE/ATTACHMENTS_ERROR_DESC');
							break;
						// no default
					}
					return result;
				},

				attachmentsInProcess: () => this.attachments.filter(item => item && !item.complete()),
				attachmentsInError: () => this.attachments.filter(item => item?.error()),

				attachmentsCount: () => this.attachments().length,
				attachmentsInErrorCount: () => this.attachmentsInError.length,
				attachmentsInProcessCount: () => this.attachmentsInProcess.length,
				isDraft: () => this.draftsFolder() && this.draftUid(),

				canEncrypt: () => this.encryptOptions().length,
				canMailvelope: () => this.encryptOptions.includes('Mailvelope'),
				canSign: () => this.signOptions().length,

				encryptOptionsText: () => this.encryptOptions().join(', '),
				signOptionsText: () => this.signOptions().map(o => o[0]).join(', '),

				identitiesOptions: () =>
					IdentityUserStore.map(item => ({
						item: item,
						optValue: item.id(),
						optText: item.formattedName()
					})),

				canBeSentOrSaved: () => !this.sending() && !this.saving()
			});

			addSubscribablesTo(this, {
				sendError: value => !value && this.sendErrorDesc(''),

				savedError: value => !value && this.savedErrorDesc(''),

				sendSuccessButSaveError: value => !value && this.savedErrorDesc(''),

				currentIdentity: value => {
					if (value) {
						this.from(value.formattedName());
						this.doEncrypt(value.pgpEncrypt() || SettingsUserStore.pgpEncrypt());
						this.doSign(value.pgpSign() || SettingsUserStore.pgpSign());
					}
				},

				from: () => {
					this.initSign();
					this.initEncrypt();
				},

				cc: value => {
					if (false === this.showCc() && value.length) {
						this.showCc(true);
					}
					this.initEncrypt();
				},

				bcc: value => {
					if (false === this.showBcc() && value.length) {
						this.showBcc(true);
					}
					this.initEncrypt();
				},

				replyTo: value => {
					if (false === this.showReplyTo() && value.length) {
						this.showReplyTo(true);
					}
				},

				attachmentsInErrorCount: value => {
					if (0 === value) {
						this.attachmentsInErrorError(false);
					}
				},

				to: value => {
					if (this.emptyToError() && value.length) {
						this.emptyToError(false);
					}
					this.initEncrypt();
				},

				attachmentsInProcess: value => {
					if (this.attachmentsInProcessError() && arrayLength(value)) {
						this.attachmentsInProcessError(false);
					}
				},

				viewArea: value => {
					if (!this.mailvelope && 'mailvelope' == value) {
						/**
						 * Creates an iframe with an editor for a new encrypted mail.
						 * The iframe will be injected into the container identified by selector.
						 * https://mailvelope.github.io/mailvelope/Editor.html
						 */
						let armored = oLastMessage && oLastMessage.body.classList.contains('mailvelope'),
							text = armored ? oLastMessage.plain() : this.oEditor.getData(),
							draft = this.isDraft(),
							encrypted = PgpUserStore.isEncrypted(text),
							size = SettingsGet('phpUploadSizes')['post_max_size'],
							quota = pInt(size);
						switch (size.slice(-1)) {
							case 'G': quota *= 1024; // fallthrough
							case 'M': quota *= 1024; // fallthrough
							case 'K': quota *= 1024;
						}
						// Issue: can't select signing key
	//					this.doSign(this.doSign() || confirm('Sign this message?'));
						mailvelope.createEditorContainer('#mailvelope-editor', PgpUserStore.mailvelopeKeyring, {
							// https://mailvelope.github.io/mailvelope/global.html#EditorContainerOptions
							quota: Math.max(2048, (quota / 1024)) - 48, // (text + attachments) limit in kilobytes
							armoredDraft: (encrypted && draft) ? text : '', // Ascii Armored PGP Text Block
							predefinedText: encrypted ? '' : (this.oEditor.isHtml() ? htmlToPlain(text) : text),
							quotedMail: (encrypted && !draft) ? text : '', // Ascii Armored PGP Text Block mail that should be quoted
	/*
							quotedMailIndent: true, // if true the quoted mail will be indented (default: true)
							quotedMailHeader: '', // header to be added before the quoted mail
							keepAttachments: false, // add attachments of quotedMail to editor (default: false)
							// Issue: can't select signing key
							signMsg: this.doSign()
	*/
						}).then(editor => this.mailvelope = editor);
					}
				}
			});

			decorateKoCommands(this, {
				sendCommand: self => self.canBeSentOrSaved(),
				saveCommand: self => self.canBeSentOrSaved(),
				deleteCommand: self => self.isDraft(),
				skipCommand: self => self.canBeSentOrSaved(),
				contactsCommand: self => self.allowContacts
			});

			this.from(IdentityUserStore()[0].formattedName());
		}

		sentFolder()
		{
			let sSentFolder = this.currentIdentity()?.sentFolder?.() || FolderUserStore.sentFolder();
			if (SettingsUserStore.replySameFolder()) {
				if (
					3 === arrayLength(this.aDraftInfo) &&
					this.aDraftInfo[2]?.length
				) {
					sSentFolder = this.aDraftInfo[2];
				}
			}
			return UNUSED_OPTION_VALUE === sSentFolder ? null : sSentFolder;
		}

		sendCommand() {
			this.attachmentsInProcessError(false);
			this.attachmentsInErrorError(false);
			this.emptyToError(false);

			if (this.attachmentsInProcess().length) {
				this.attachmentsInProcessError(true);
				this.attachmentsArea();
			} else if (this.attachmentsInError().length) {
				this.attachmentsInErrorError(true);
				this.attachmentsArea();
			}

			if (!this.to().trim() && !this.cc().trim() && !this.bcc().trim()) {
				this.emptyToError(true);
			}

			if (!this.emptyToError() && !this.attachmentsInErrorError() && !this.attachmentsInProcessError()) {
				const sSentFolder = this.sentFolder();
				if ('' === sSentFolder) {
					showScreenPopup(FolderSystemPopupView, [FolderType.Sent]);
				} else {
					const sendError = e => {
						console.error(e);
						this.sendError(true);
						this.sendErrorDesc(e);
						this.sending(false);
					};
					const sendFailed = (iError, data) => {
						this.sendError(true);
						this.sendErrorDesc(
							getNotification(iError, data?.message, Notifications.CantSendMessage)
							+ "\n" + (data?.messageAdditional || data?.message)
						);
					};
					try {
						this.sendError(false);
						this.sending(true);

						const sendMessage = params => {
							Remote.request('SendMessage',
								(iError, data) => {
									this.sending(false);
									if (iError) {
	/*
										if (Notifications.AuthError === iError && !params.auth) {
											AskPopupView.password('SMTP login', 'retry', 3).then(result => {
												if (result) {
													this.sending(true);
													params.auth = result;
													sendMessage(params);
												} else {
													sendFailed(iError, data);
												}
											});
										} else
	*/
										if (Notifications.CantSaveMessage === iError) {
											this.sendSuccessButSaveError(true);
											let msg = i18n('COMPOSE/SAVED_ERROR_ON_SEND');
											if (data?.messageAdditional) {
												msg = msg + "\n" + data?.messageAdditional;
											}
											this.savedErrorDesc(msg);
										} else {
											this.sendError(true);
											sendFailed(iError, data);
											// Remove remembered passphrase as it could be wrong
											let key = ('S/MIME' === params.sign) ? this.currentIdentity() : null;
											params.signFingerprint
											&& this.signOptions.forEach(option => ('GnuPG' === option[0]) && (key = option[1]));
											key && Passphrases.delete(key);
										}
									} else {
										if (arrayLength(this.aDraftInfo) > 0) {
											const flag = {
												'reply': '\\answered',
												'forward': '$forwarded'
											}[this.aDraftInfo[0]];
											if (flag) {
												const aFlags = oLastMessage.flags();
												if (aFlags.indexOf(flag) === -1) {
													aFlags.push(flag);
													oLastMessage.flags(aFlags);
												}
											}
										}
										this.close();
									}
									setFolderETag(this.draftsFolder(), '');
									setFolderETag(params.saveFolder, '');
									if (3 === arrayLength(this.aDraftInfo)) {
										setFolderETag(this.aDraftInfo[2], '');
									}
									reloadDraftFolder();
								},
								params,
								30000
							);
						};

						this.getMessageRequestParams(sSentFolder)
						.then(sendMessage)
						.catch(sendError);
					} catch (e) {
						sendError(e);
					}
				}
			}
		}

		saveCommand() {
			if (!this.saving() && !this.sending()) {
				if (FolderUserStore.draftsFolderNotEnabled()) {
					showScreenPopup(FolderSystemPopupView, [FolderType.Drafts]);
				} else {
					this.savedError(false);
					this.saving(true);
					this.autosaveStart();
					this.getMessageRequestParams(FolderUserStore.draftsFolder(), 1).then(params => {
						Remote.request('SaveMessage',
							(iError, oData) => {
								let result = false;

								this.saving(false);

								if (!iError) {
									if (oData.Result.folder && oData.Result.uid) {
										result = true;

										if (this.bFromDraft) {
											const message = MessageUserStore.message();
											if (message && this.draftsFolder() === message.folder && this.draftUid() == message.uid) {
												MessageUserStore.message(null);
											}
										}

										this.draftsFolder(oData.Result.folder);
										this.draftUid(oData.Result.uid);

										this.savedTime(new Date);

										if (this.bFromDraft) {
											setFolderETag(this.draftsFolder(), '');
										}
										setFolderETag(FolderUserStore.draftsFolder(), '');
									}
								}

								if (!result) {
									this.savedError(true);
									this.savedErrorDesc(getNotification(Notifications.CantSaveMessage));
								}

								reloadDraftFolder();
							},
							params,
							200000
						);
					}).catch(e => {
						this.saving(false);
						this.savedError(true);
						this.savedErrorDesc(getNotification(Notifications.CantSaveMessage) + ': ' + e);
					});
				}
			}
		}

		deleteCommand() {
			AskPopupView.hidden()
			&& showScreenPopup(AskPopupView, [
				i18n('POPUPS_ASK/DESC_WANT_DELETE_MESSAGES'),
				() => {
					const
						sFromFolderFullName = this.draftsFolder(),
						oUids = new Set([this.draftUid()]);
					MessagelistUserStore.moveMessages(sFromFolderFullName, oUids);
					this.close();
				}
			]);
		}

		onClose() {
			this.skipCommand();
			return false;
		}

		skipCommand() {
			ComposePopupView.inEdit(true);

			if (!FolderUserStore.draftsFolderNotEnabled() && SettingsUserStore.allowDraftAutosave()) {
				this.saveCommand();
			}

			this.doClose();
		}

		contactsCommand() {
			if (this.allowContacts) {
				this.skipCommand();
				setTimeout(() => {
					showScreenPopup(ContactsPopupView, [true, this.sLastFocusedField]);
				}, 200);
			}
		}

		autosaveStart() {
			clearTimeout(this.iTimer);
			this.iTimer = setTimeout(()=>{
				if (this.modalVisible()
					&& !FolderUserStore.draftsFolderNotEnabled()
					&& SettingsUserStore.allowDraftAutosave()
					&& !this.isEmptyForm(false)
					&& !this.savedError()
				) {
					this.saveCommand();
				}

				this.autosaveStart();
			}, 60000);
		}

		// getAutocomplete
		emailsSource(value, fResponse) {
			Remote.abort('Suggestions').request('Suggestions',
				(iError, data) => {
					if (!iError && isArray(data.Result)) {
						fResponse(
							data.Result.map(item => (item?.[0] ? (new EmailModel(item[0], item[1])).toLine() : null))
							.filter(v => v)
						);
					} else if (Notifications.RequestAborted !== iError) {
						fResponse([]);
					}
				},
				{
					Query: value
	//				,Page: 1
				}
			);
		}

		selectIdentity(identity) {
			identity = identity?.item;
			if (identity) {
				this.currentIdentity(identity);
				this.setSignature(identity);
			}
		}

		onHide() {
			// Stop autosave
			clearTimeout(this.iTimer);

			ComposePopupView.inEdit() || this.reset();

			this.to.focused(false);

	//		alreadyFullscreen || exitFullscreen();
		}

		dropMailvelope() {
			if (this.mailvelope) {
				elementById('mailvelope-editor').textContent = '';
				this.mailvelope = null;
			}
		}

		editor(fOnInit) {
			if (fOnInit && this.editorArea()) {
				if (this.oEditor) {
					fOnInit(this.oEditor);
				} else {
					// setTimeout(() => {
					this.oEditor = new HtmlEditor(
						this.editorArea(),
						() => fOnInit(this.oEditor),
						bHtml => this.isHtml(!!bHtml)
					);
					// }, 1000);
				}
			}
		}

		setSignature(identity, msgComposeType) {
			if (identity && ComposeType.Draft !== msgComposeType && ComposeType.EditAsNew !== msgComposeType) {
				this.editor(editor => {
					let signature = identity.signature() || '',
						isHtml = signature.startsWith(':HTML:'),
						fromLine = oLastMessage ? emailArrayToStringLineHelper(oLastMessage.from, true) : '';
					if (fromLine) {
						signature = signature.replace(/{{FROM-FULL}}/g, fromLine);
						if (!fromLine.includes(' ') && 0 < fromLine.indexOf('@')) {
							fromLine = fromLine.replace(/@\S+/, '');
						}
						signature = signature.replace(/{{FROM}}/g, fromLine);
					}
					signature = (isHtml ? signature.slice(6) : signature)
						.replace(/\r/g, '')
						.replace(/\s{1,2}?{{FROM}}/g, '')
						.replace(/\s{1,2}?{{FROM-FULL}}/g, '')
						.replace(/{{DATE}}/g, new Date().format({dateStyle: 'full', timeStyle: 'short'}))
						.replace(/{{TIME}}/g, new Date().format('LT'))
						.replace(/{{MOMENT:[^}]+}}/g, '');
					signature.length && editor.setSignature(signature, isHtml, !!identity.signatureInsertBefore());
				});
			}
		}

		/**
		 * @param {string=} type = ComposeType.Empty
		 * @param {?MessageModel|Array=} oMessageOrArray = null
		 * @param {Array=} aToEmails = null
		 * @param {Array=} aCcEmails = null
		 * @param {Array=} aBccEmails = null
		 * @param {string=} sCustomSubject = null
		 * @param {string=} sCustomPlainText = null
		 */
		onShow(type, oMessageOrArray, aToEmails, aCcEmails, aBccEmails, sCustomSubject, sCustomPlainText) {
			this.autosaveStart();

			this.viewModelDom.dataset.wysiwyg = SettingsUserStore.editorDefaultType();

			let options = {
				mode: type || ComposeType.Empty,
				to:  aToEmails,
				cc:  aCcEmails,
				bcc: aBccEmails,
				subject: sCustomSubject,
				text: sCustomPlainText
			};
			if (1 < arrayLength(oMessageOrArray)) {
				options.messages = oMessageOrArray;
			} else {
				options.message = isArray(oMessageOrArray) ? oMessageOrArray[0] : oMessageOrArray;
			}

			if (ComposePopupView.inEdit()) {
				if (ComposeType.Empty !== options.mode) {
					showScreenPopup(AskPopupView, [
						i18n('COMPOSE/DISCARD_UNSAVED_DATA'),
						() => this.initOnShow(options),
						null,
						false
					]);
				} else {
					addEmailsTo(this.to, aToEmails);
					addEmailsTo(this.cc, aCcEmails);
					addEmailsTo(this.bcc, aBccEmails);

					if (sCustomSubject && !this.subject()) {
						this.subject(sCustomSubject);
					}
				}
			} else {
				this.initOnShow(options);
			}

			ComposePopupView.inEdit(false);
			// Chrome bug #298
	//		alreadyFullscreen = isFullscreen();
	//		alreadyFullscreen || (ThemeStore.isMobile() && toggleFullscreen());
		}

		/**
		 * @param {object} options
		 */
		initOnShow(options) {

			const
	//			excludeEmail = new Set(),
				excludeEmail = {},
				mEmail = AccountUserStore.email();

			oLastMessage = options.message;

			if (mEmail) {
	//			excludeEmail.add(mEmail);
				excludeEmail[mEmail] = true;
			}

			this.reset();

			let identity = null;
			if (oLastMessage) {
				switch (options.mode) {
					case ComposeType.Reply:
					case ComposeType.ReplyAll:
					case ComposeType.Forward:
					case ComposeType.ForwardAsAttachment:
						identity = findIdentity(oLastMessage.to.concat(oLastMessage.cc, oLastMessage.bcc))
							/* || findIdentity(oLastMessage.deliveredTo)*/;
						break;
					case ComposeType.Draft:
						identity = findIdentity(oLastMessage.from.concat(oLastMessage.replyTo));
						break;
					// no default
	//				case ComposeType.Empty:
				}
			}
			identity = identity || IdentityUserStore()[0];
			if (identity) {
	//			excludeEmail.add(identity.email());
				excludeEmail[identity.email()] = true;
			}

			if (arrayLength(options.to)) {
				this.to(emailArrayToStringLineHelper(options.to));
			}

			if (arrayLength(options.cc)) {
				this.cc(emailArrayToStringLineHelper(options.cc));
			}

			if (arrayLength(options.bcc)) {
				this.bcc(emailArrayToStringLineHelper(options.bcc));
			}

			if (options.mode && oLastMessage) {
				let usePlain,
					sCc = '',
					sDate = timestampToString(oLastMessage.dateTimestamp(), 'FULL'),
					sSubject = oLastMessage.subject(),
					sText = '',
					aDraftInfo = oLastMessage.draftInfo;

				switch (options.mode) {
					case ComposeType.Reply:
					case ComposeType.ReplyAll: {
	//					if (1 == oLastMessage.to.length) {
	//						setTimeout(() => this.from(emailArrayToStringLineHelper(oLastMessage.to)), 1);
	//					}
						if (ComposeType.Reply === options.mode) {
							this.to(emailArrayToStringLineHelper(oLastMessage.replyEmails(excludeEmail)));
						} else {
							let parts = oLastMessage.replyAllEmails(excludeEmail);
							this.to(emailArrayToStringLineHelper(parts[0]));
							this.cc(emailArrayToStringLineHelper(parts[1]));
						}
						this.subject(replySubjectAdd('Re', sSubject));
						this.prepareMessageAttachments(oLastMessage, options.mode);
						this.aDraftInfo = ['reply', oLastMessage.uid, oLastMessage.folder];
						this.sInReplyTo = oLastMessage.messageId;
						this.sReferences = (oLastMessage.references + ' ' + oLastMessage.messageId).trim();
						oLastMessage.headers().valuesByName('autocrypt').forEach(value => {
							let autocrypt = new MimeHeaderAutocryptModel(value);
							if (autocrypt.addr && autocrypt.keydata) {
								PgpUserStore.hasPublicKeyForEmails([autocrypt.addr])
								|| PgpUserStore.importKey(autocrypt.pem(), true, true);
	//							|| showScreenPopup(OpenPgpImportPopupView, [autocrypt.pem()])
							}
						});
					} break;

					case ComposeType.Forward:
					case ComposeType.ForwardAsAttachment:
						this.subject(replySubjectAdd('Fwd', sSubject));
						this.prepareMessageAttachments(oLastMessage, options.mode);
						this.aDraftInfo = ['forward', oLastMessage.uid, oLastMessage.folder];
						this.sInReplyTo = oLastMessage.messageId;
						this.sReferences = (oLastMessage.references + ' ' + oLastMessage.messageId).trim();
						break;

					case ComposeType.Draft:
						this.bFromDraft = true;
						this.draftsFolder(oLastMessage.folder);
						this.draftUid(oLastMessage.uid);
						// fallthrough
					case ComposeType.EditAsNew:
						this.to(emailArrayToStringLineHelper(oLastMessage.to));
						this.cc(emailArrayToStringLineHelper(oLastMessage.cc));
						this.bcc(emailArrayToStringLineHelper(oLastMessage.bcc));
						this.replyTo(emailArrayToStringLineHelper(oLastMessage.replyTo));
						this.subject(sSubject);
						this.prepareMessageAttachments(oLastMessage, options.mode);
						this.aDraftInfo = 3 === arrayLength(aDraftInfo) ? aDraftInfo : null;
						this.sInReplyTo = oLastMessage.inReplyTo;
						this.sReferences = oLastMessage.references;
						break;

	//				case ComposeType.Empty:
	//					break;
					// no default
				}

				// https://github.com/the-djmaze/snappymail/issues/491
				tpl.innerHTML = oLastMessage.bodyAsHTML();
				tpl.content.querySelectorAll('img').forEach(img => {
					img.src || img.dataset.xSrcCid || img.dataset.xSrc || img.replaceWith(img.alt || img.title);
				});
				sText = tpl.innerHTML.trim();

				switch (options.mode) {
					case ComposeType.Reply:
					case ComposeType.ReplyAll:
						sText = '<br><br><p>'
							+ i18n('COMPOSE/REPLY_MESSAGE_TITLE', { DATETIME: sDate, EMAIL: oLastMessage.from.toString(false, true) })
							+ ':</p><blockquote>'
							+ sText.trim()
							+ '</blockquote>';
						break;

					case ComposeType.Forward:
						sCc = oLastMessage.cc.toString(false, true);
						sText = '<br><br><p>' + i18n('COMPOSE/FORWARD_MESSAGE_TOP_TITLE') + '</p><div>'
							+ i18n('GLOBAL/FROM') + ': ' + oLastMessage.from.toString(false, true)
							+ '<br>'
							+ i18n('GLOBAL/TO') + ': ' + oLastMessage.to.toString(false, true)
							+ (sCc.length ? '<br>' + i18n('GLOBAL/CC') + ': ' + sCc : '')
							+ '<br>'
							+ i18n('COMPOSE/FORWARD_MESSAGE_TOP_SENT')
							+ ': '
							+ encodeHtml(sDate)
							+ '<br>'
							+ i18n('GLOBAL/SUBJECT')
							+ ': '
							+ encodeHtml(sSubject)
							+ '<br><br>'
							+ sText.trim()
							+ '</div>';
						break;

					case ComposeType.ForwardAsAttachment:
						sText = '';
						break;

					default:
						usePlain = PgpUserStore.isEncrypted(sText) || isPlainEditor() || !oLastMessage.isHtml();
						if (usePlain) {
							sText = oLastMessage.plain();
						}
				}

				this.editor(editor => {
					usePlain ? (editor.modePlain() | editor.setPlain(sText)) : editor.setHtml(sText);
					this.setSignature(identity, options.mode);
					this.setFocusInPopup();
				});
			} else if (ComposeType.Empty === options.mode) {
				this.subject(null != options.subject ? '' + options.subject : '');
				this.editor(editor => {
					editor.setHtml(options.text ? '' + options.text : '');
					isPlainEditor() && editor.modePlain();
					this.setSignature(identity);
					this.setFocusInPopup();
				});
			} else if (options.messages) {
				options.messages.forEach(item => this.addMessageAsAttachment(item));
				this.editor(editor => {
					isPlainEditor() ? editor.setPlain('') : editor.setHtml('');
					this.setSignature(identity, options.mode);
					this.setFocusInPopup();
				});
			} else {
				this.setFocusInPopup();
			}

			// item.cId item.isInline item.isLinked
			const downloads = this.attachments.filter(item => item && !item.tempName()).map(item => item.id);
			if (arrayLength(downloads)) {
				Remote.request('MessageUploadAttachments',
					(iError, oData) => {
						const result = oData?.Result;
						downloads.forEach((id, index) => {
							const attachment = this.getAttachmentById(id);
							if (attachment) {
								attachment
									.waiting(false)
									.uploading(false)
									.complete(true);
								if (iError || !result?.[index]) {
									attachment.error(getUploadErrorDescByCode(UploadErrorCode.NoFileUploaded));
								} else {
									attachment.tempName(result[index].tempName);
									attachment.type(result[index].mimeType);
								}
							}
						});
					},
					{
						attachments: downloads
					},
					999000
				);
			}

			this.currentIdentity(identity);
		}

		setFocusInPopup() {
			setTimeout(() => {
				if (!this.to()) {
					this.to.focused(true);
				} else if (!this.subject()) {
					this.viewModelDom.querySelector('input[name="subject"]').focus();
				} else {
					this.oEditor?.focus();
				}
			}, 100);
		}

		doClose() {
			if (AskPopupView.hidden()) {
				if (ComposePopupView.inEdit() || (this.isEmptyForm() && !this.draftUid())) {
					this.close();
				} else {
					showScreenPopup(AskPopupView, [
						i18n('POPUPS_ASK/DESC_WANT_CLOSE_THIS_WINDOW'),
						() => this.close()
					]);
				}
			}
		}

		onBuild(dom) {
			// initUploader
			const oJua = new Jua({
					action: serverRequest('Upload'),
					clickElement: dom.querySelector('#composeUploadButton'),
					dragAndDropElement: dom.querySelector('.b-attachment-place')
				}),
				attachmentSizeLimit = pInt(SettingsGet('attachmentLimit'));

			oJua
				.on('onDragEnter', () => {
					this.dragAndDropOver(true);
				})
				.on('onDragLeave', () => {
					this.dragAndDropOver(false);
				})
				.on('onBodyDragEnter', () => {
					this.attachmentsArea();
					this.dragAndDropVisible(true);
				})
				.on('onBodyDragLeave', () => {
					this.dragAndDropVisible(false);
				})
				.on('onProgress', (id, loaded, total) => {
					let item = this.getAttachmentById(id);
					if (item) {
						item.progress(Math.floor((loaded / total) * 100));
					}
				})
				.on('onSelect', (sId, oData) => {
					this.dragAndDropOver(false);

					const
						size = pInt(oData.size, null),
						attachment = new ComposeAttachmentModel(
							sId,
							oData.fileName ? oData.fileName.toString() : '',
							size
						);

					this.addAttachment(attachment, 1, oJua);

					if (0 < size && 0 < attachmentSizeLimit && attachmentSizeLimit < size) {
						attachment
							.waiting(false)
							.uploading(true)
							.complete(true)
							.error(i18n('UPLOAD/ERROR_FILE_IS_TOO_BIG'));

						return false;
					}

					return true;
				})
				.on('onStart', id => {
					let item = this.getAttachmentById(id);
					if (item) {
						item
							.waiting(false)
							.uploading(true)
							.complete(false);
					}
				})
				.on('onComplete', (id, result, data) => {
					const attachment = this.getAttachmentById(id),
						response = data?.Result || {},
						errorCode = response.code,
						attachmentJson = result && response.Attachment;

					let error = '';
					if (null != errorCode) {
						error = getUploadErrorDescByCode(errorCode);
					} else if (!attachmentJson) {
						error = i18n('UPLOAD/ERROR_UNKNOWN');
					}

					if (attachment) {
						if (error) {
							attachment
								.waiting(false)
								.uploading(false)
								.complete(true)
								.error(error + '\n' + response.message);
						} else if (attachmentJson) {
							attachment
								.waiting(false)
								.uploading(false)
								.complete(true);
							attachment.fileName(attachmentJson.name);
							attachment.size(attachmentJson.size ? pInt(attachmentJson.size) : 0);
							attachment.tempName(attachmentJson.tempName ? attachmentJson.tempName : '');
							attachment.isInline = false;
							attachment.type(attachmentJson.mimeType);
						}
					}
				});

			this.addAttachmentEnabled(true);

			addShortcut('q', 'meta', ScopeCompose, ()=>false);
			addShortcut('w', 'meta', ScopeCompose, ()=>false);

			addShortcut('m', 'meta', ScopeCompose, () => {
				this.identitiesMenu().ddBtn.toggle();
				return false;
			});

			addShortcut('arrowdown', 'meta', ScopeCompose, () => {
				this.skipCommand();
				return false;
			});

			addShortcut('s', 'meta', ScopeCompose, () => {
				this.saveCommand();
				return false;
			});
			addShortcut('save', '', ScopeCompose, () => {
				this.saveCommand();
				return false;
			});

			addShortcut('enter', 'meta', ScopeCompose, () => {
	//			if (SettingsUserStore.allowCtrlEnterOnCompose()) {
					this.sendCommand();
					return false;
	//			}
			});
			addShortcut('mailsend', '', ScopeCompose, () => {
				this.sendCommand();
				return false;
			});

			addShortcut('escape,close', 'shift', ScopeCompose, () => {
				this.doClose();
				return false;
			});

			this.editor(editor => editor[isPlainEditor()?'modePlain':'modeWysiwyg']());
		}

		/**
		 * @param {string} id
		 * @returns {?Object}
		 */
		getAttachmentById(id) {
			return this.attachments.find(item => item && id === item.id);
		}

		/**
		 * @param {MessageModel} message
		 */
		addMessageAsAttachment(message) {
			if (message) {
				const attachment = new ComposeAttachmentModel(
					message.requestHash,
					message.subject() /*+ '-' + Jua.randomId()*/ + '.eml',
					message.size
				);
				attachment.fromMessage = true;
				attachment.complete(true);
				this.addAttachment(attachment);
			}
		}

		addAttachment(attachment, view, oJua) {
			oJua || attachment.waiting(false).uploading(true);
			attachment.cancel = () => {
				this.attachments.remove(attachment);
				oJua?.cancel(attachment.id);
			};
			this.attachments.push(attachment);
			view && this.attachmentsArea();
		}

		/**
		 * @param {string} id
		 * @param {string} name
		 * @param {number} size
		 * @returns {ComposeAttachmentModel}
		 */
		addAttachmentHelper(id, name, size) {
			const attachment = new ComposeAttachmentModel(id, name, size);
			this.addAttachment(attachment, 1);
			return attachment;
		}

		/**
		 * @param {MessageModel} message
		 * @param {string} type
		 */
		prepareMessageAttachments(message, type) {
			if (message) {
				let reply = [ComposeType.Reply, ComposeType.ReplyAll].includes(type);
				if (reply || [ComposeType.Forward, ComposeType.Draft, ComposeType.EditAsNew].includes(type)) {
					// item instanceof AttachmentModel
					message.attachments.forEach(item => {
						if (!reply || item.isLinked()) {
							const attachment = new ComposeAttachmentModel(
								item.download,
								item.fileName,
								item.estimatedSize,
								item.isInline(),
								item.isLinked(),
								item.cId,
								item.contentLocation
							);
							attachment.fromMessage = true;
							attachment.type(item.mimeType);
							this.addAttachment(attachment);
						}
					});
				} else if (ComposeType.ForwardAsAttachment === type) {
					this.addMessageAsAttachment(message);
				}
			}
		}

		/**
		 * @param {boolean=} includeAttachmentInProgress = true
		 * @returns {boolean}
		 */
		isEmptyForm(includeAttachmentInProgress = true) {
			const withoutAttachment = includeAttachmentInProgress
				? !this.attachments.length
				: !this.attachments.some(item => item?.complete());

			return (
				!this.to.length &&
				!this.cc.length &&
				!this.bcc.length &&
				!this.replyTo.length &&
				!this.subject.length &&
				withoutAttachment &&
				(!this.oEditor || !this.oEditor.getData())
			);
		}

		reset() {
			this.to('');
			this.cc('');
			this.bcc('');
			this.replyTo('');
			this.subject('');

			this.requestDsn(SettingsUserStore.requestDsn());
			this.requestReadReceipt(SettingsUserStore.requestReadReceipt());
			this.requireTLS(SettingsUserStore.requireTLS());
			this.markAsImportant(false);

			this.bodyArea();

			this.aDraftInfo = null;
			this.sInReplyTo = '';
			this.bFromDraft = false;
			this.sReferences = '';

			this.sendError(false);
			this.sendSuccessButSaveError(false);
			this.savedError(false);
			this.savedTime(0);
			this.emptyToError(false);
			this.attachmentsInProcessError(false);

			this.showCc(false);
			this.showBcc(false);
			this.showReplyTo(false);

			this.doSign(SettingsUserStore.pgpSign());
			this.doEncrypt(SettingsUserStore.pgpEncrypt());

			this.attachments([]);

			this.dragAndDropOver(false);
			this.dragAndDropVisible(false);

			this.draftsFolder('');
			this.draftUid(0);

			this.sending(false);
			this.saving(false);

			this.oEditor?.clear();

			this.dropMailvelope();
		}

		attachmentsArea() {
			this.viewArea('attachments');
		}
		bodyArea() {
			this.viewArea('body');
		}

		allRecipients() {
			return [
					// From/sender is also recipient (Sent mailbox)
	//				this.currentIdentity().email(),
					this.from(),
					this.to(),
					this.cc(),
					this.bcc()
				].join(',').split(',').map(value => getEmail(value.trim())).validUnique();
		}

		/**
		 * Checks if signing a message is possible with from email address.
		 * And sets all that can.
		 */
		initSign() {
			let options = [],
				identity = this.currentIdentity(),
				email = getEmail(this.from()),
				key = OpenPGPUserStore.getPrivateKeyFor(email, 1);
			key && options.push(['OpenPGP', key]);
			key = GnuPGUserStore.getPrivateKeyFor(email, 1);
			key && options.push(['GnuPG', key]);
			identity.smimeKeyValid() && identity.smimeCertificateValid() && identity.email() === email
				&& options.push(['S/MIME']);
			console.dir({signOptions: options});
			this.signOptions(options);
		}

		async initEncrypt() {
			const recipients = this.allRecipients(),
				options = [];

			if (recipients.length) {
				GnuPGUserStore.hasPublicKeyForEmails(recipients)
				&& options.push('GnuPG');

				OpenPGPUserStore.hasPublicKeyForEmails(recipients)
				&& options.push('OpenPGP');

				const count = recipients.length,
					identity = this.currentIdentity(),
					from = (identity.smimeKey() && identity.smimeCertificate()) ? identity.email() : null;
				count
					&& count === recipients.filter(email =>
						email == from
						|| SMimeUserStore.find(certificate => email == certificate.emailAddress && certificate.smimeencrypt)
					).length
					&& options.push('S/MIME');

				if (await MailvelopeUserStore.hasPublicKeyForEmails(recipients)) {
					options.push('Mailvelope');
				} else {
					'mailvelope' === this.viewArea() && this.bodyArea();
	//				this.dropMailvelope();
				}
			}

			console.dir({encryptOptions:options});
			this.encryptOptions(options);
		}

		async getMessageRequestParams(sSaveFolder, draft)
		{
			let Text = this.oEditor.getData().trim(),
				l,
				hasAttachments = 0;

			// Prepare ComposeAttachmentModel attachments
			const attachments = {};
			this.attachments.forEach(item => {
				if (item?.complete() && item?.tempName() && item?.enabled()) {
					++hasAttachments;
					attachments[item.tempName()] = {
						name: item.fileName(),
						inline: item.isInline,
						cId: item.cId,
						location: item.contentLocation,
						type: item.mimeType()
					};
				}
			});
	/*
			let sToAddress = this.to();

			if (/".*" <.*,.*>/g.test(sToAddress)) {
				sToAddress = sToAddress.match(/<.*>/g)[0].replace(/[<>]/g, '');
			}
	*/
			const
				identity = this.currentIdentity(),
				params = {
					identityID: identity.id(),
					messageFolder: this.draftsFolder(),
					messageUid: this.draftUid(),
					saveFolder: sSaveFolder,
					from: this.from(),
					to: this.to(),
					cc: this.cc(),
					bcc: this.bcc(),
					replyTo: this.replyTo(),
					subject: this.subject(),
					draftInfo: this.aDraftInfo,
					inReplyTo: this.sInReplyTo,
					references: this.sReferences,
					markAsImportant: this.markAsImportant() ? 1 : 0,
					attachments: attachments,
					// Only used at send, not at save:
					dsn: this.requestDsn() ? 1 : 0,
					requireTLS: this.requireTLS() ? 1 : 0,
					readReceiptRequest: this.requestReadReceipt() ? 1 : 0,
					autocrypt: [],
					/**
					 * Basic support for Linked Data (Structured Email)
					 * https://json-ld.org/
					 * https://structured.email/
					 **/
					linkedData: []
				},
				recipients = draft ? [identity.email()] : this.allRecipients(),
				signOptions = !draft && this.doSign() && this.signOptions(),
				encryptOptions = this.doEncrypt() && this.encryptOptions(),
				isHtml = this.oEditor.isHtml();

			if (isHtml) {
				do {
					l = Text.length;
					Text = Text
						// Remove Microsoft Office styling
						.replace(/(<[^>]+[;"'])\s*mso-[a-z-]+\s*:[^;"']+/gi, '$1')
						// Remove hubspot data-hs- attributes
						.replace(/(<[^>]+)\s+data-hs-[a-z-]+=("[^"]+"|'[^']+')/gi, '$1');
				} while (l != Text.length)
				params.html = Text;
				params.plain = htmlToPlain(Text);
			} else {
				params.plain = Text;
			}

			if (this.mailvelope && 'mailvelope' === this.viewArea()) {
				params.encrypted = draft
					? await this.mailvelope.createDraft()
					: await this.mailvelope.encrypt(recipients);
	/*
				Object.entries(PgpUserStore.getPublicKeyOfEmails(recipients) || {}).forEach(([k,v]) =>
					params.autocrypt.push({addr:k, keydata:v.replace(/-----(BEGIN|END) PGP PUBLIC KEY BLOCK-----/g).trim()})
				);
	*/
			} else if (signOptions.length || encryptOptions.length) {
				if (!draft && !hasAttachments && !Text.length) {
					throw i18n('COMPOSE/ERROR_EMPTY_BODY');
				}
				let data = new MimePart;
				data.headers['Content-Type'] = 'text/'+(isHtml?'html':'plain')+'; charset="utf-8"';
				data.headers['Content-Transfer-Encoding'] = 'base64';
				data.body = base64_encode(Text);
				if (isHtml) {
					const alternative = new MimePart, plain = new MimePart;
					alternative.headers['Content-Type'] = 'multipart/alternative';
					plain.headers['Content-Type'] = 'text/plain; charset="utf-8"';
					plain.headers['Content-Transfer-Encoding'] = 'base64';
					plain.body = base64_encode(params.plain);
					// First add plain
					alternative.children.push(plain);
					// Now add HTML
					alternative.children.push(data);
					data = alternative;
				}
				let isSigned = false;
				for (let i = 0; i < signOptions.length; ++i) {
					if ('OpenPGP' == signOptions[i][0]) {
						try {
							// Doesn't sign attachments
							let signed = new MimePart;
							signed.headers['Content-Type'] =
								'multipart/signed; micalg="pgp-sha256"; protocol="application/pgp-signature"';
							signed.headers['Content-Transfer-Encoding'] = '7Bit';
							signed.children.push(data);
							let signature = new MimePart;
							signature.headers['Content-Type'] = 'application/pgp-signature; name="signature.asc"';
							signature.headers['Content-Transfer-Encoding'] = '7Bit';
							signature.body = await OpenPGPUserStore.sign(data.toString(), signOptions[i][1], 1);
							signed.children.push(signature);
							isSigned = true;
							params.html = params.plain = '';
							params.signed = signed.toString();
							params.boundary = signed.boundary;
							data = signed;
	/*
							Object.entries(PgpUserStore.getPublicKeyOfEmails([getEmail(this.from())]) || {})
							.forEach(([k,v]) => params.publicKey = v);
	*/
							break;
						} catch (e) {
							console.error(e);
						}
					} else if ('GnuPG' == signOptions[i][0]) {
						// TODO: sign in PHP fails
						let pass = await GnuPGUserStore.sign(signOptions[i][1]);
						if (null != pass) {
	//						params.signData = data.toString();
							params.signFingerprint = signOptions[i][1].fingerprint;
							params.signPassphrase = pass;
	//						params.attachPublicKey = false;
							isSigned = true;
							break;
						}
					} else if ('S/MIME' == signOptions[i][0]) {
						// TODO: sign in PHP fails
						params.sign = 'S/MIME';
	//					params.signCertificate = identity.smimeCertificate();
	//					params.signPrivateKey = identity.smimeKey();
	//					params.attachCertificate = false;
						if (identity.smimeKeyEncrypted()) {
							const pass = await Passphrases.ask(identity,
								i18n('SMIME/PRIVATE_KEY_OF', {EMAIL: identity.email()}),
								'CRYPTO/SIGN'
							);
							if (null != pass) {
								params.signPassphrase = pass.password;
								pass.remember && Passphrases.handle(identity, pass.password);
								isSigned = true;
							}
						}
					}
				}
				if (signOptions.length && !isSigned) {
					throw 'Signing failed';
				}

				if (encryptOptions.length) {
					const autocrypt = () =>
						Object.entries(PgpUserStore.getPublicKeyOfEmails(recipients) || {}).forEach(([k,v]) =>
							params.autocrypt.push({
								addr: k,
								keydata: v.replace(/-----(BEGIN|END) PGP PUBLIC KEY BLOCK-----/g, '').trim()
							})
						);
					for (let i = 0; i < encryptOptions.length; ++i) {
						if ('OpenPGP' == encryptOptions[i]) {
							// Doesn't encrypt attachments
							params.encrypted = await OpenPGPUserStore.encrypt(data.toString(), recipients);
							params.signed = '';
							autocrypt();
							break;
						}
						if ('GnuPG' == encryptOptions[i]) {
							// Does encrypt attachments
							params.encryptFingerprints = JSON.stringify(GnuPGUserStore.getPublicKeyFingerprints(recipients));
							autocrypt();
							break;
						}
						if ('S/MIME' == encryptOptions[i]) {
							params.encryptCertificates = [identity.smimeCertificate()];
							SMimeUserStore.forEach(certificate => {
								certificate.emailAddress != identity.email()
								&& recipients.includes(certificate.emailAddress)
								&& params.encryptCertificates.push(certificate.id);
							});
							break;
						}
						// We skip Mailvelope as it has its own window
					}
				}
			}

			return params;
		}
	}

	/**
	 * When view is closed and reopened, fill it with previous data.
	 * This, for example, happens when opening Contacts view to select recipients
	 */
	ComposePopupView.inEdit = ko.observable(false);

	class MailFolderList extends AbstractViewLeft {
		constructor() {
			super();

	//		this.oContentScrollable = null;

			this.composeInEdit = ComposePopupView.inEdit;

			this.systemFolders = FolderUserStore.systemFolders;

			this.moveAction = moveAction;

			this.allowContacts = AppUserStore.allowContacts();

			this.foldersFilter = foldersFilter;

			this.filterUnseen = ko.observable(false);

			addComputablesTo(this, {
				foldersFilterVisible: () => 20 < FolderUserStore.folderList().CountRec,

				folderListVisible: () => {
					let result = FolderUserStore.folderList().visible();
					return 1 === result.length && result[0].isInbox() ? result[0].visibleSubfolders() : result;
				}
			});
		}

		onBuild(dom) {
			const qs = s => dom.querySelector(s),
				eqs = (ev, s) => ev.target.closestWithin(s, dom);

			this.oContentScrollable = qs('.b-content');

			dom.addEventListener('click', event => {
				let el = eqs(event, '.e-collapsed-sign');
				if (el) {
					const folder = ko.dataFor(el);
					if (folder) {
						const collapsed = folder.collapsed();
						setExpandedFolder(folder.fullName, collapsed);

						folder.collapsed(!collapsed);
						stopEvent(event);
						return;
					}
				}

				el = eqs(event, 'a');
				if (el?.matches('.selectable')) {
					event.preventDefault();
					const folder = ko.dataFor(el);
					if (folder) {
						if (moveAction()) {
							const copy = event.ctrlKey || 2 === moveAction(),
								messages = MessagelistUserStore.listCheckedOrSelectedUidsWithSubMails();
							moveAction(0);
							messages.size && MessagelistUserStore.moveMessages(
								messages.folder,
								messages,
								folder.fullName,
								copy
							);
						} else {
							if (!SettingsUserStore.usePreviewPane()) {
								MessageUserStore.message(null);
							}
	/*
							if (folder.fullName === FolderUserStore.currentFolderFullName()) {
								setFolderETag(folder.fullName, '');
							}
	*/
							let search = '';
							if (event.target.matches('.flag-icon') && !folder.isFlagged()) {
								search = 'flagged';
							} else if (folder.unreadCount() && event.clientX > el.getBoundingClientRect().right - 25) {
								search = 'unseen';
							}
							hasher.setHash(mailBox(folder.fullNameHash, 1, search));

							// in mobile mode hide the panel when a folder is clicked
							ThemeStore.isMobile() && leftPanelDisabled(true);
						}

						AppUserStore.focusedState(ScopeMessageList);
					}
				}
			});

			addShortcut('arrowup,arrowdown', '', ScopeFolderList, event => {
				let items = [], index = 0;
				dom.querySelectorAll('li a').forEach(node => {
					if (node.offsetHeight || node.getClientRects().length) {
						items.push(node);
						if (node.matches('.focused')) {
							node.classList.remove('focused');
							index = items.length - 1;
						}
					}
				});
				if (items.length) {
					if ('ArrowUp' === event.key) {
						index && --index;
					} else if (index < items.length - 1) {
						++index;
					}
					items[index].classList.add('focused');
					this.scrollToFocused();
				}

				return false;
			});

			addShortcut('enter,open', '', ScopeFolderList, () => {
				const item = qs('li a.focused');
				if (item) {
					AppUserStore.focusedState(ScopeMessageList);
					item.click();
				}

				return false;
			});

			addShortcut('space', '', ScopeFolderList, () => {
				const item = qs('li a.focused'),
					folder = item && ko.dataFor(item);
				if (folder) {
					const collapsed = folder.collapsed();
					setExpandedFolder(folder.fullName, collapsed);
					folder.collapsed(!collapsed);
				}

				return false;
			});

	//		addShortcut('tab', 'shift', ScopeFolderList, () => {
			addShortcut('escape,tab,arrowright', '', ScopeFolderList, () => {
				AppUserStore.focusedState(ScopeMessageList);
				moveAction(0);
				return false;
			});
		}

		scrollToFocused() {
			const scrollable = this.oContentScrollable;
			if (scrollable) {
				let block, focused = scrollable.querySelector('li a.focused');
				if (focused) {
					const fRect = focused.getBoundingClientRect(),
						sRect = scrollable.getBoundingClientRect();
					if (fRect.top < sRect.top) {
						block = 'start';
					} else if (fRect.bottom > sRect.bottom) {
						block = 'end';
					}
					block && focused.scrollIntoView(block === 'start');
				}
			}
		}

		composeClick() {
			showMessageComposer();
		}

		clearFolderSearch() {
			foldersFilter('');
		}

		createFolder() {
			showScreenPopup(FolderCreatePopupView);
		}

		configureFolders() {
			hasher.setHash(settings('folders'));
		}

		contactsClick() {
			if (this.allowContacts) {
				showScreenPopup(ContactsPopupView);
			}
		}
	}

	class FolderClearPopupView extends AbstractViewPopup {
		constructor() {
			super('FolderClear');

			addObservablesTo(this, {
				folder: null,
				clearing: false
			});

			addComputablesTo(this, {
				dangerDescHtml: () => {
	//				const folder = this.folder();
	//				return i18n('POPUPS_CLEAR_FOLDER/DANGER_DESC_HTML_1', { FOLDER: folder.fullName.replace(folder.delimiter, ' / ') });
					return i18n('POPUPS_CLEAR_FOLDER/DANGER_DESC_HTML_1', { FOLDER: this.folder()?.localName() });
				}
			});

			decorateKoCommands(this, {
				clearCommand: self => !self.clearing()
			});
		}

		clearCommand() {
			const folder = this.folder();
			if (folder) {
				this.clearing(true);
				Remote.request('FolderClear', iError => {
					folder.totalEmails(0);
					folder.unreadEmails(0);
					MessageUserStore.message(null);
					MessagelistUserStore.reload(true, true);
					this.clearing(false);
					iError ? alert(getNotification(iError)) : this.close();
				}, {
					folder: folder.fullName
				});
			}
		}

		onShow(folder) {
			this.clearing(false);
			this.folder(folder);
		}
	}

	class AdvancedSearchPopupView extends AbstractViewPopup {
		constructor() {
			super('AdvancedSearch');

			addObservablesTo(this, {
				from: '',
				to: '',
				subject: '',
				text: '',
				keyword: '',
				repliedValue: -1,
				selectedDateValue: 0,
				selectedTreeValue: '',

				hasAttachment: false,
				starred: false,
				unseen: false
			});

			addComputablesTo(this, {
				showMultisearch: () => FolderUserStore.hasCapability('MULTISEARCH'),

				// Almost the same as MessageModel.tagOptions
				keywords: () => {
					const keywords = [{value:'',label:''}];
					FolderUserStore.currentFolder().optionalTags().forEach(value => {
						let lower = value.toLowerCase();
						keywords.push({
							value: value,
							label: i18n('MESSAGE_TAGS/'+lower, 0, lower)
						});
					});
					return keywords
				},

				showKeywords: () => FolderUserStore.currentFolder().permanentFlags().some(isAllowedKeyword),

				repliedOptions: () => {
					translateTrigger();
					return [
						{ id: -1, name: '' },
						{ id: 1, name: i18n('GLOBAL/YES') },
						{ id: 0, name: i18n('GLOBAL/NO') }
					];
				},

				selectedDates: () => {
					translateTrigger();
					// We should think about migrating all SEARCH/DATE_ to either SEARCH/SINCE_DATE or SEARCH/BEFORE_DATE
					// and adjust the prefix accordingly
					// let prefix_since = 'SEARCH/SINCE_DATE_';
					let prefix = 'SEARCH/SINCE_';
					let prefix_before = 'SEARCH/BEFORE_';
					return [
						{ id: 0, name: i18n('SEARCH/DATE_ALL') },
						{ id: 3, name: i18n(prefix + '3_DAYS') },
						{ id: 7, name: i18n(prefix + '7_DAYS') },
						{ id: 30, name: i18n(prefix + 'MONTH') },
						{ id: 90, name: i18n(prefix + '3_MONTHS') },
						{ id: 180, name: i18n(prefix + '6_MONTHS') },
						{ id: 365, name: i18n(prefix + 'YEAR') },
						{ id: -3, name: i18n(prefix_before + '3_DAYS') },
						{ id: -7, name: i18n(prefix_before + '7_DAYS') },
						{ id: -30, name: i18n(prefix_before + 'MONTH') },
						{ id: -90, name: i18n(prefix_before + '3_MONTHS') },
						{ id: -180, name: i18n(prefix_before + '6_MONTHS') },
						{ id: -365, name: i18n(prefix_before + 'YEAR') }
					];
				},

				selectedTree: () => {
					translateTrigger();
					let prefix = 'SEARCH/SUBFOLDERS_';
					return [
						{ id: '', name: i18n(prefix + 'NONE') },
						{ id: 'subtree-one', name: i18n(prefix + 'SUBTREE_ONE') },
						{ id: 'subtree', name: i18n(prefix + 'SUBTREE') }
					];
				}
			});
		}

		submitForm() {
			const search = this.buildSearchString();
			if (search) {
				MessagelistUserStore.mainSearch(search);
			}

			this.close();
		}

		buildSearchString() {
			const
				self = this,
				data = new FormData(),
				append = (key, value) => value.length && data.append(key, value);

			append('from', self.from().trim());
			append('to', self.to().trim());
			append('subject', self.subject().trim());
			append('text', self.text().trim());
			append('keyword', self.keyword());
			append('in', self.selectedTreeValue());
			if (0 < self.selectedDateValue()) {
				let d = new Date();
				d.setDate(d.getDate() - self.selectedDateValue());
				append('since', d.toISOString().split('T')[0]);
			}
			else if (-1 > self.selectedDateValue()) {
				let d = new Date();
				d.setDate(d.getDate() + self.selectedDateValue());
				append('before', d.toISOString().split('T')[0]);
			}

			let result = decodeURIComponent(new URLSearchParams(data).toString());

			if (self.hasAttachment()) {
				result += '&attachment';
			}
			if (self.unseen()) {
				result += '&unseen';
			}
			if (self.starred()) {
				result += '&flagged';
			}
			if (1 == self.repliedValue()) {
				result += '&answered';
			}
			if (0 == self.repliedValue()) {
				result += '&unanswered';
			}

			return result.replace(/^&+/, '');
		}

		onShow(search) {
			const self = this,
				params = new URLSearchParams('?'+search);
			self.from(pString(params.get('from')));
			self.to(pString(params.get('to')));
			self.subject(pString(params.get('subject')));
			self.text(pString(params.get('text')));
			self.keyword(pString(params.get('keyword')));
			self.selectedTreeValue(pString(params.get('in')));
			self.selectedDateValue(0);
			self.hasAttachment(params.has('attachment'));
			self.starred(params.has('flagged'));
			self.unseen(params.has('unseen'));
			if (params.has('answered')) {
				self.repliedValue(1);
			} else if (params.has('unanswered')) {
				self.repliedValue(0);
			}
		}
	}

	const
		canBeMovedHelper = () => MessagelistUserStore.hasCheckedOrSelected(),

		/**
		 * @param {string} sFolderFullName
		 * @param {number} iSetAction
		 * @param {Array=} aMessages = null
		 * @returns {void}
		 */
		listAction = (...args) => MessagelistUserStore.setAction(...args),

		moveMessagesToFolderType = (toFolderType, bDelete) => {
			let messages = MessagelistUserStore.listCheckedOrSelectedUidsWithSubMails();
			messages.size && rl.app.moveMessagesToFolderType(
				toFolderType,
				messages.folder,
				messages,
				bDelete
			);
		},

		pad2 = v => 10 > v ? '0' + v : '' + v,
		Ymd = dt => dt.getFullYear() + pad2(1 + dt.getMonth()) + pad2(dt.getDate()),

		setMessage = msg => {
			populateMessageBody(msg);
	/* This will replace url hash, and then load message
	 * It's working properly yet
	//		let hash = msg.href;
			let hash = mailBox(
				msg.folder,
				MessagelistUserStore.page(),
				MessagelistUserStore.listSearch(),
				MessagelistUserStore.threadUid(),
				msg.uid
			);
			MessageUserStore.message() ? hasher.replaceHash(hash) : hasher.setHash(hash);
	*/
		};


	let
		sLastSearchValue = '';

	class MailMessageList extends AbstractViewRight {
		constructor() {
			super();

			this.allowDangerousActions = SettingsCapa('DangerousActions');

			this.messageList = MessagelistUserStore;
			this.archiveAllowed = MessagelistUserStore.archiveAllowed;
			this.canMarkAsSpam = MessagelistUserStore.canMarkAsSpam;
			this.isSpamFolder = MessagelistUserStore.isSpamFolder;

			this.composeInEdit = ComposePopupView.inEdit;

			this.isMobile = ThemeStore.isMobile; // Obsolete

			this.popupVisibility = arePopupsVisible;

			this.useCheckboxesInList = SettingsUserStore.useCheckboxesInList;

			this.userUsageProc = FolderUserStore.quotaPercentage;

			this.hideDeleted = SettingsUserStore.hideDeleted;

			addObservablesTo(this, {
				focusSearch: false
			});

			// append drag and drop
			this.dragOver = ko.observable(false).extend({ throttle: 1 });
			this.dragOverEnter = ko.observable(false).extend({ throttle: 1 });

			const attachmentsActions = Settings.app('attachmentsActions');
			this.attachmentsActions = ko.observableArray(arrayLength(attachmentsActions) ? attachmentsActions : []);

			addComputablesTo(this, {

				sortSupported: () => FolderUserStore.hasCapability('SORT') && !MessagelistUserStore.threadUid(),

				messageListSearchDesc: () => {
					const value = MessagelistUserStore().search;
					return value ? i18n('MESSAGE_LIST/SEARCH_RESULT_FOR', { SEARCH: value }) : ''
				},

				messageListPaginator: computedPaginatorHelper(MessagelistUserStore.page, MessagelistUserStore.pageCount),

				checkAll: {
					read: () => MessagelistUserStore.hasChecked(),
					write: (value) => {
						value = !!value;
						MessagelistUserStore.forEach(message => message.checked(value));
					}
				},

				inputSearch: {
					read: MessagelistUserStore.mainSearch,
					write: value => sLastSearchValue = value
				},

				isIncompleteChecked: () => {
					const c = MessagelistUserStore.listChecked().length;
					return c && MessagelistUserStore().length > c;
				},

				listGrouped: () => {
					let uid = MessagelistUserStore.threadUid(),
						sort = FolderUserStore.sortMode() || 'DATE';
					return SettingsUserStore.listGrouped() && (sort.includes('DATE') || sort.includes('FROM')) && !uid;
				},

				timeFormat: () => (FolderUserStore.sortMode() || '').includes('FROM') ? 'AUTO' : 'LT',

				groupedList: () => {
					let list = [], current, sort = FolderUserStore.sortMode() || 'DATE';
					if (sort.includes('FROM')) {
						MessagelistUserStore.forEach(msg => {
							let email = msg.from[0]?.email;
							if (!current || email != current.id) {
								current = {
									id: email,
									label: msg.from[0]?.toLine(),
									search: 'from=' + email,
									messages: []
								};
								list.push(current);
							}
							current.messages.push(msg);
						});
					} else if (sort.includes('DATE')) {
						let today = Ymd(new Date()),
							rtf = Intl.RelativeTimeFormat
								? new Intl.RelativeTimeFormat(doc.documentElement.lang, { numeric: "auto" }) : 0;
						MessagelistUserStore.forEach(msg => {
							let dt = (new Date(msg.dateTimestamp() * 1000)),
								date,
								ymd = Ymd(dt);
							if (!current || ymd != current.id) {
								if (rtf && today == ymd) {
									date = rtf.format(0, 'day');
								} else if (rtf && today - 1 == ymd) {
									date = rtf.format(-1, 'day');
	//							} else if (today - 7 < ymd) {
	//								date = dt.format({weekday: 'long'});
	//								date = dt.format({dateStyle: 'full'},0,LanguageStore.hourCycle());
								} else {
	//								date = dt.format({dateStyle: 'medium'},0,LanguageStore.hourCycle());
									date = dt.format({dateStyle: 'full'},0,LanguageStore.hourCycle());
								}
								current = {
									id: ymd,
									label: date,
									search: 'on=' + dt.getFullYear() + '-' + pad2(1 + dt.getMonth()) + '-' + pad2(dt.getDate()),
									messages: []
								};
								list.push(current);
							}
							current.messages.push(msg);
						});
					}
					return list;
				},

				sortText: () => {
					let mode = FolderUserStore.sortMode(),
						desc = '' === mode || mode.includes('REVERSE');
					mode = mode.split(/\s+/);
					if (mode.includes('FROM')) {
						 return '@' + (desc ? '⬆' : '⬇');
					}
					if (mode.includes('SUBJECT')) {
						 return '𝐒' + (desc ? '⬆' : '⬇');
					}
					return (mode.includes('SIZE') ? '✉' : '📅') + (desc ? '⬇' : '⬆');
				},

				downloadAsZipAllowed: () => this.attachmentsActions.includes('zip')
			});

			this.selector = new Selector(
				MessagelistUserStore,
				MessagelistUserStore.selectedMessage,
				MessagelistUserStore.focusedMessage,
				'.messageListItem',
				'.messageListItem .messageCheckbox'
			);

			this.selector.on('ItemSelect', message => {
				if (message) {
	//				setMessage(message.clone());
					setMessage(message);
				} else {
					MessageUserStore.message(null);
				}
			});

			this.selector.on('MiddleClick', message => populateMessageBody(message, true));

			this.selector.on('ItemGetUid', message => (message ? message.folder + '/' + message.uid : ''));

			this.selector.on('canSelect', () => MessagelistUserStore.canSelect());

			this.selector.on('click', (event, currentMessage) => {
				const el = event.target;
				if (el.closest('.flagParent')) {
					if (currentMessage) {
						const checked = MessagelistUserStore.listCheckedOrSelected();
						listAction(
							currentMessage.folder,
							currentMessage.isFlagged() ? MessageSetAction.UnsetFlag : MessageSetAction.SetFlag,
							checked.find(message => message.uid == currentMessage.uid) ? checked : [currentMessage]
						);
					}
				} else if (el.closest('.threads-len')) {
					this.gotoThread(currentMessage);
				} else {
					return 1;
				}
			});

			this.selector.on('UpOrDown', up => {
				if (!MessagelistUserStore.hasChecked()) {
					up = up ? -1 : 1;
					const page = MessagelistUserStore.page() + up;
					if (page > 0 && page <= MessagelistUserStore.pageCount()) {
						if (SettingsUserStore.usePreviewPane() || MessageUserStore.message()) {
							this.selector.iSelectNextHelper = up;
						} else {
							this.selector.iFocusedNextHelper = up;
						}
						this.selector.unselect();
						this.gotoPage(page);
					}
				}
			});

			addEventListener('mailbox.message-list.selector.go-down',
				e => this.selector.newSelectPosition('ArrowDown', false, e.detail)
			);

			addEventListener('mailbox.message-list.selector.go-up',
				e => this.selector.newSelectPosition('ArrowUp', false, e.detail)
			);

			addEventListener('mailbox.message.show', e => {
				const sFolder = e.detail.folder, iUid = e.detail.uid;

				const message = MessagelistUserStore.find(
					item => sFolder === item?.folder && iUid == item?.uid
				);

				if ('INBOX' === sFolder) {
					hasher.setHash(mailBox(sFolder));
				}

				if (message) {
					this.selector.selectMessageItem(message);
				} else {
					if ('INBOX' !== sFolder) {
						hasher.setHash(mailBox(sFolder));
					}
					if (sFolder && iUid) {
						let message = new MessageModel;
						message.folder = sFolder;
						message.uid = iUid;
						setMessage(message);
					} else {
						MessageUserStore.message(null);
					}
				}
			});

			MessagelistUserStore.endHash.subscribe((() =>
				this.selector.scrollToFocused()
			).throttle(50));

			decorateKoCommands(this, {
				downloadAttachCommand: canBeMovedHelper,
				downloadZipCommand: canBeMovedHelper,
				forwardCommand: canBeMovedHelper,
				deleteWithoutMoveCommand: canBeMovedHelper,
				deleteCommand: () => MessagelistUserStore.hasCheckedOrSelectedAndUndeleted(),
				undeleteCommand: () => MessagelistUserStore.hasCheckedOrSelectedAndDeleted(),
				archiveCommand: canBeMovedHelper,
				spamCommand: canBeMovedHelper,
				notSpamCommand: canBeMovedHelper,
				moveCommand: canBeMovedHelper,
				copyCommand: canBeMovedHelper
			});
		}

		changeSort(self, event) {
			FolderUserStore.sortMode(event.target.closest('li').dataset.sort);
			this.reload();
		}

		clearListIsVisible() {
			return (
				!this.messageListSearchDesc()
			 && !MessagelistUserStore.error()
			 && !MessagelistUserStore.endThreadUid()
			 && MessagelistUserStore().length
			 && (MessagelistUserStore.isSpamFolder() || MessagelistUserStore.isTrashFolder())
			 && SettingsCapa('DangerousActions')
			);
		}

		clear() {
			SettingsCapa('DangerousActions')
			&& showScreenPopup(FolderClearPopupView, [FolderUserStore.currentFolder()]);
		}

		reload() {
			MessagelistUserStore.isLoading()
			|| MessagelistUserStore.reload(false, true);
		}

		forwardCommand() {
			showMessageComposer([
				ComposeType.ForwardAsAttachment,
				MessagelistUserStore.listCheckedOrSelected()
			]);
		}

		/**
		 * Download selected messages
		 */
		downloadZipCommand() {
			let hashes = []/*, uids = []*/;
	//		MessagelistUserStore.forEach(message => message.checked() && uids.push(message.uid));
			MessagelistUserStore.forEach(message => message.checked() && hashes.push(message.requestHash));
			downloadZip(null, hashes, null, null, MessagelistUserStore().folder);
		}

		/**
		 * Download attachments of selected messages
		 */
		downloadAttachCommand() {
			let hashes = [];
			MessagelistUserStore.forEach(message => {
				if (message.checked()) {
					message.attachments.forEach(attachment => {
						if (!attachment.isLinked() && attachment.download) {
							hashes.push(attachment.download);
						}
					});
				}
			});
			downloadZip(null, hashes);
		}

		deleteWithoutMoveCommand() {
			SettingsCapa('DangerousActions')
			&& moveMessagesToFolderType(FolderType.Trash, true);
		}

		// User setting hideDeleted || immediatelyMoveToTrash ??
		deleteCommand() {
			/**
			 * When FolderUserStore.trashFolder is set to "Do not use",
			 * flag as \Deleted for removal by later EXPUNGE
			 */
			if (UNUSED_OPTION_VALUE === FolderUserStore.trashFolder()) {
				listAction(
					FolderUserStore.currentFolderFullName(),
					MessageSetAction.SetDeleted,
					MessagelistUserStore.listCheckedOrSelected()
				);
			} else {
				moveMessagesToFolderType(FolderType.Trash);
			}
		}

		// User setting !hideDeleted && !immediatelyMoveToTrash ??
		undeleteCommand() {
			listAction(
				FolderUserStore.currentFolderFullName(),
				MessageSetAction.UnsetDeleted,
				MessagelistUserStore.listCheckedOrSelected()
			);
		}

		archiveCommand() {
			moveMessagesToFolderType(FolderType.Archive);
		}

		spamCommand() {
			moveMessagesToFolderType(FolderType.Junk);
		}

		notSpamCommand() {
			moveMessagesToFolderType(FolderType.Inbox);
		}

		moveOrCopy(vm, event, mode) {
			if (canBeMovedHelper()) {
				if (vm && event?.preventDefault) {
					stopEvent(event);
				}

				let i = moveAction();
				AppUserStore.focusedState(i ? ScopeMessageList : ScopeFolderList);
				moveAction(i ? 0 : mode);
			}
		}

		moveCommand(vm, event) {
			this.moveOrCopy(vm, event, 1);
		}

		copyCommand(vm, event) {
			this.moveOrCopy(vm, event, 2);
		}

		composeClick() {
			showMessageComposer();
		}

		cancelSearch() {
			MessagelistUserStore.mainSearch('');
			this.focusSearch(false);
		}

		cancelThreadUid() {
			// history.go(-1) better?
			hasher.setHash(
				mailBox(
					FolderUserStore.currentFolderFullNameHash(),
					MessagelistUserStore.pageBeforeThread(),
					MessagelistUserStore.listSearch()
				)
			);
		}

		listSetSeen() {
			listAction(
				FolderUserStore.currentFolderFullName(),
				MessageSetAction.SetSeen,
				MessagelistUserStore.listCheckedOrSelected()
			);
		}

		listSetAllSeen() {
			let sFolderFullName = FolderUserStore.currentFolderFullName(),
				iThreadUid = MessagelistUserStore.endThreadUid();
			if (sFolderFullName) {
				let cnt = 0;
				const uids = [];

				let folder = getFolderFromCacheList(sFolderFullName);
				if (folder) {
					MessagelistUserStore.forEach(message => {
						if (message.isUnseen()) {
							++cnt;
						}

						message.flags.push('\\seen');
	//					message.flags.valueHasMutated();
						iThreadUid && uids.push(message.uid);
					});

					if (iThreadUid) {
						folder.unreadEmails(Math.max(0, folder.unreadEmails() - cnt));
					} else {
						folder.unreadEmails(0);
					}

					Remote.request('MessageSetSeenToAll', null, {
						folder: sFolderFullName,
						setAction: 1,
						threadUids: uids.join(',')
					});
				}
			}
		}

		listUnsetSeen() {
			listAction(
				FolderUserStore.currentFolderFullName(),
				MessageSetAction.UnsetSeen,
				MessagelistUserStore.listCheckedOrSelected()
			);
		}

		listSetFlags() {
			listAction(
				FolderUserStore.currentFolderFullName(),
				MessageSetAction.SetFlag,
				MessagelistUserStore.listCheckedOrSelected()
			);
		}

		listUnsetFlags() {
			listAction(
				FolderUserStore.currentFolderFullName(),
				MessageSetAction.UnsetFlag,
				MessagelistUserStore.listCheckedOrSelected()
			);
		}

		seenMessagesFast(seen) {
			const checked = MessagelistUserStore.listCheckedOrSelected();
			if (checked.length) {
				listAction(
					checked[0].folder,
					seen ? MessageSetAction.SetSeen : MessageSetAction.UnsetSeen,
					checked
				);
			}
		}

		gotoPage(page) {
			page && hasher.setHash(
				mailBox(
					FolderUserStore.currentFolderFullNameHash(),
					page,
					MessagelistUserStore.listSearch(),
					MessagelistUserStore.threadUid()
				)
			);
		}

		gotoThread(message) {
			if (message?.threadsLen()) {
				MessagelistUserStore.pageBeforeThread(MessagelistUserStore.page());

				hasher.setHash(
					mailBox(FolderUserStore.currentFolderFullNameHash(), 1, MessagelistUserStore.listSearch(), message.uid)
				);
			}
		}

		listEmptyMessage() {
			if (!this.dragOver()
			 && !MessagelistUserStore().length
			 && !MessagelistUserStore.isLoading()
			 && !MessagelistUserStore.error()) {
				 return i18n('MESSAGE_LIST/EMPTY_' + (MessagelistUserStore.listSearch() ? 'SEARCH_' : '') + 'LIST');
			}
			return '';
		}

		onBuild(dom) {
			const b_content = dom.querySelector('.b-content'),
				eqs = (ev, s) => ev.target.closestWithin(s, dom);

			setTimeout(() => {
				// initMailboxLayoutResizer
				const top = dom.querySelector('.messageList'),
					fToggle = () => {
						let layout = SettingsUserStore.usePreviewPane();
						setLayoutResizer(top, ClientSideKeyNameMessageListSize,
							layout ? (LayoutSideView === layout ? 'Width' : 'Height') : 0
						);
					};
				if (top) {
					fToggle();
					addEventListener('rl-layout', fToggle);
				}
			}, 1);

			this.selector.init(b_content, ScopeMessageList);

			addEventsListeners(dom, {
				click: event => {
					if (eqs(event, '.toggleLeft')) {
						toggleLeftPanel();
					} else {
						ThemeStore.isMobile() && leftPanelDisabled(true);

						if (eqs(event, '.messageList') && ScopeMessageView === AppUserStore.focusedState()) {
							AppUserStore.focusedState(ScopeMessageList);
						}

						let el = eqs(event, '.e-paginator a');
						el && this.gotoPage(ko.dataFor(el)?.value);

						eqs(event, '.checkboxCheckAll') && this.checkAll(!this.checkAll());
					}
				},
				dblclick: event => {
					let msg = ko.dataFor(eqs(event, '.messageListItem'));
					if (msg) {
						msg.threadsLen() ? this.gotoThread(msg) : toggleFullscreen();
					}
				}
			});

			// initUploaderForAppend

			if (Settings.app('allowAppendMessage')) {
				const dropZone = dom.querySelector('.listDragOver'),
					validFiles = oEvent => {
						for (const item of oEvent.dataTransfer.items) {
							if ('file' === item.kind && RFC822 === item.type) {
								return true;
							}
						}
					};
				addEventsListeners(dropZone, {
					dragover: oEvent => {
						if (validFiles(oEvent)) {
							oEvent.dataTransfer.dropEffect = 'copy';
							oEvent.preventDefault();
						}
					},
				});
				addEventsListeners(b_content, {
					dragenter: oEvent => {
						if (validFiles(oEvent)) {
							if (b_content.contains(oEvent.target)) {
								this.dragOver(true);
							}
							if (oEvent.target == dropZone) {
								oEvent.dataTransfer.dropEffect = 'copy';
								this.dragOverEnter(true);
							}
						}
					},
					dragleave: oEvent => {
						if (oEvent.target == dropZone) {
							this.dragOverEnter(false);
						}
						let related = oEvent.relatedTarget;
						if (!related || !b_content.contains(related)) {
							this.dragOver(false);
						}
					},
					drop: oEvent => {
						oEvent.preventDefault();
						if (oEvent.target == dropZone && validFiles(oEvent)) {
							MessagelistUserStore.loading(true);
							dropFilesInFolder(FolderUserStore.currentFolderFullName(), oEvent.dataTransfer.files);
						}
						this.dragOverEnter(false);
						this.dragOver(false);
					}
				});
			}

			// initShortcuts

			addShortcut('enter,open', '', ScopeMessageList, () => {
				if (formFieldFocused()) {
					MessagelistUserStore.mainSearch(sLastSearchValue);
					return false;
				}
				if (MessageUserStore.message() && MessagelistUserStore.canSelect()) {
					isFullscreen() || toggleFullscreen();
					return false;
				}
			});

			// archive (zip)
			registerShortcut('z', '', [ScopeMessageList, ScopeMessageView], () => {
				this.archiveCommand();
				return false;
			});

			// delete
			registerShortcut('delete', 'shift', ScopeMessageList, () => {
				MessagelistUserStore.listCheckedOrSelected().length && this.deleteWithoutMoveCommand();
				return false;
			});
	//		registerShortcut('3', 'shift', ScopeMessageList, () => {
			registerShortcut('delete', '', ScopeMessageList, () => {
				MessagelistUserStore.listCheckedOrSelected().length && this.deleteCommand();
				return false;
			});

			// check mail
			addShortcut('r', 'meta', [ScopeFolderList, ScopeMessageList, ScopeMessageView], () => {
				this.reload();
				return false;
			});

			// check all
			registerShortcut('a', 'meta', ScopeMessageList, () => {
				this.checkAll(!(this.checkAll() && !this.isIncompleteChecked()));
				return false;
			});

			// write/compose (open compose popup)
			registerShortcut('w,c,new', '', [ScopeMessageList, ScopeMessageView], () => {
				showMessageComposer();
				return false;
			});

			// important - star/flag messages
			registerShortcut('i', '', [ScopeMessageList, ScopeMessageView], () => {
				const checked = MessagelistUserStore.listCheckedOrSelected();
				if (checked.length) {
					listAction(
						checked[0].folder,
						checked.every(message => message.isFlagged()) ? MessageSetAction.UnsetFlag : MessageSetAction.SetFlag,
						checked
					);
				}
				return false;
			});

			registerShortcut('t', '', [ScopeMessageList], () => {
				let message = MessagelistUserStore.selectedMessage() || MessagelistUserStore.focusedMessage();
				if (0 < message?.threadsLen()) {
					this.gotoThread(message);
				}
				return false;
			});

			// move
			registerShortcut('insert', '', ScopeMessageList, () => {
				this.moveCommand();
				return false;
			});

			// read
			registerShortcut('q', '', [ScopeMessageList, ScopeMessageView], () => {
				this.seenMessagesFast(true);
				return false;
			});

			// unread
			registerShortcut('u', '', [ScopeMessageList, ScopeMessageView], () => {
				this.seenMessagesFast(false);
				return false;
			});

			registerShortcut('f,mailforward', 'shift', [ScopeMessageList, ScopeMessageView], () => {
				this.forwardCommand();
				return false;
			});

			if (SettingsCapa('Search')) {
				// search input focus
				addShortcut('/', '', [ScopeMessageList, ScopeMessageView], () => {
					this.focusSearch(true);
					return false;
				});
			}

			// cancel search
			addShortcut('escape', '', ScopeMessageList, () => {
				if (this.messageListSearchDesc()) {
					this.cancelSearch();
					return false;
				} else if (MessagelistUserStore.endThreadUid()) {
					this.cancelThreadUid();
					return false;
				}
			});

			// change focused state
			addShortcut('tab', 'shift', ScopeMessageList, () => {
				AppUserStore.focusedState(ScopeFolderList);
				return false;
			});
			addShortcut('arrowleft', '', ScopeMessageList, () => {
				AppUserStore.focusedState(ScopeFolderList);
				return false;
			});
			addShortcut('tab,arrowright', '', ScopeMessageList, () => {
				if (MessageUserStore.message()) {
					AppUserStore.focusedState(ScopeMessageView);
					return false;
				}
			});

			addShortcut('arrowleft', 'meta', ScopeMessageView, ()=>false);
			addShortcut('arrowright', 'meta', ScopeMessageView, ()=>false);

			addShortcut('f', 'meta', ScopeMessageList, this.advancedSearchClick);
		}

		advancedSearchClick() {
			showScreenPopup(AdvancedSearchPopupView, [MessagelistUserStore.mainSearch()]);
		}

		groupSearch(group) {
			group.search && MessagelistUserStore.mainSearch(group.search);
		}

		groupCheck(group) {
			group.messages.forEach(message => message.checked(!message.checked()));
		}

		quotaTooltip() {
			return i18n('MESSAGE_LIST/QUOTA_SIZE', {
				SIZE: FileInfo.friendlySize(FolderUserStore.quotaUsage()),
				PROC: FolderUserStore.quotaPercentage(),
				LIMIT: FileInfo.friendlySize(FolderUserStore.quotaLimit())
			}).replace(/<[^>]+>/g, '');
		}
	}

	class OpenPgpImportPopupView extends AbstractViewPopup {
		constructor() {
			super('OpenPgpImport');

			addObservablesTo(this, {
				search: '',

				key: '',
				keyError: false,
				keyErrorMessage: '',

				saveGnuPG: true,
				saveServer: true
			});

			this.canGnuPG = GnuPGUserStore.isSupported();

			this.key.subscribe(() => {
				this.keyError(false);
				this.keyErrorMessage('');
			});
		}

		searchPGP() {
			this.key(i18n('SUGGESTIONS/SEARCHING_DESC'));
			const fn = () => Remote.request('PgpSearchKey',
				(iError, oData) => {
					if (iError) {
						this.key(oData.message);
					} else {
						this.key(oData.Result);
					}
				}, {
					query: this.search()
				}
			);
			fetch(
				`https://keys.openpgp.org/pks/lookup?op=get&options=mr&search=${this.search()}`,
				{
					method: 'GET',
					mode: 'cors',
					cache: 'no-cache',
					redirect: 'error',
					referrerPolicy: 'no-referrer',
					credentials: 'omit'
				}
			)
			.then(response => {
				if ('application/pgp-keys' == response.headers.get('Content-Type')) {
					response.text().then(body => this.key(body));
				} else {
					fn();
				}
			})
			.catch(e => {
				this.key('keys.openpgp.org: ' + e?.message + '\nTrying local...');
				fn();
				throw e;
			});
		}

		submitForm() {
			let keyTrimmed = this.key().trim();

			if (/\n/.test(keyTrimmed)) {
				keyTrimmed = keyTrimmed.replace(/\r+/g, '').replace(/\n{2,}/g, '\n\n');
			}

			this.keyError(!keyTrimmed);
			this.keyErrorMessage('');

			if (keyTrimmed) {
				let match = null,
					count = 30,
					done = false;
				const GnuPG = this.saveGnuPG() && GnuPGUserStore.isSupported(),
					backup = this.saveServer(),
					// eslint-disable-next-line max-len
					reg = /[-]{3,6}BEGIN[\s]PGP[\s](PRIVATE|PUBLIC)[\s]KEY[\s]BLOCK[-]{3,6}[\s\S]+?[-]{3,6}END[\s]PGP[\s](PRIVATE|PUBLIC)[\s]KEY[\s]BLOCK[-]{3,6}/gi;

				do {
					match = reg.exec(keyTrimmed);
					if (match && 0 < count) {
						if (match[0] && match[1] && match[2] && match[1] === match[2]) {
							PgpUserStore.importKey(this.key(), GnuPG, backup);
						}
						--count;
						done = false;
					} else {
						done = true;
					}
				} while (!done);

				this.close();
			}
		}

		onShow(key) {
			this.key(key || '');
			this.keyError(false);
			this.keyErrorMessage('');
		}
	}

	const
		oMessageScrollerDom = () => elementById('messageItem') || {},

		currentMessage = MessageUserStore.message,

		setAction = action => {
			const message = currentMessage();
			message && MessagelistUserStore.setAction(message.folder, action, [message]);
		},

		fetchRaw = url => rl.fetch(url).then(response => response.ok && response.text());

	class MailMessageView extends AbstractViewRight {
		constructor() {
			super();

			const
				/**
				 * @param {Function} fExecute
				 * @param {Function} fCanExecute = true
				 * @returns {Function}
				 */
				createCommand = (fExecute, fCanExecute) => {
					let fResult = () => {
							fCanExecute() && fExecute.call(null);
							return false;
						};
					fResult.canExecute = fCanExecute;
					return fResult;
				},

				createCommandReplyHelper = type =>
					createCommand(() => this.replyOrforward(type), this.canBeRepliedOrForwarded),

				createCommandActionHelper = (folderType, bDelete) =>
					createCommand(() => {
						const message = currentMessage();
						if (message) {
							currentMessage(null);
							rl.app.moveMessagesToFolderType(folderType, message.folder, new Set([message.uid]), bDelete);
						}
					}, this.messageVisible),
				createCommandSetHelper = action =>
					createCommand(() => setAction(action), this.messageVisible),
				createCommandDeleteHelper = () =>
					createCommand(() => {
						/**
						 * When FolderUserStore.trashFolder is set to "Do not use",
						 * flag as \Deleted for removal by later EXPUNGE
						 */
						if (UNUSED_OPTION_VALUE === FolderUserStore.trashFolder()) {
							setAction(MessageSetAction.SetDeleted);
						} else {
							const message = currentMessage();
							if (message) {
								currentMessage(null);
								rl.app.moveMessagesToFolderType(FolderType.Trash, message.folder, new Set([message.uid]));
							}
						}
					}, this.messageVisible);

			this.msgDefaultAction = SettingsUserStore.msgDefaultAction;
			this.simpleAttachmentsList = SettingsUserStore.simpleAttachmentsList;

			addObservablesTo(this, {
				showAttachmentControls: !!get(ClientSideKeyNameMessageAttachmentControls),
				downloadAsZipLoading: false,
				showFullInfo: '1' === get(ClientSideKeyNameMessageHeaderFullInfo),
				// bootstrap dropdown
				actionsMenu: null,
				// viewer
				viewFromShort: '',
				dkimData: ['none', '', ''],
				nowTracking: false
			});

			this.moveAction = moveAction;

			const attachmentsActions = Settings.app('attachmentsActions');
			this.attachmentsActions = ko.observableArray(arrayLength(attachmentsActions) ? attachmentsActions : []);

			this.hasCheckedMessages = MessagelistUserStore.hasChecked;
			this.archiveAllowed = MessagelistUserStore.archiveAllowed;
			this.canMarkAsSpam = MessagelistUserStore.canMarkAsSpam;
			this.isDraftFolder = MessagelistUserStore.isDraftFolder;
			this.isSpamFolder = MessagelistUserStore.isSpamFolder;

			this.message = currentMessage;
			this.messageLoadingThrottle = MessageUserStore.loading;
			this.messageError = MessageUserStore.error;

			this.fullScreenMode = isFullscreen;
			this.toggleFullScreen = toggleFullscreen;

			this.downloadAsZipError = ko.observable(false).extend({ falseTimeout: 7000 });

			this.messageDomFocused = ko.observable(false).extend({ rateLimit: 0 });

			// viewer
			this.viewHash = '';

			addComputablesTo(this, {
				allowAttachmentControls: () => arrayLength(attachmentsActions) && SettingsCapa('AttachmentsActions'),

				downloadAsZipAllowed: () => this.attachmentsActions.includes('zip')
					&& (currentMessage()?.attachments || [])
						.filter(item => item?.checked() && item?.download /*&& !item?.isLinked()*/)
						.length,

				tagsAllowed: () => FolderUserStore.currentFolder()?.tagsAllowed(),

				messageVisible: () => !MessageUserStore.loading() && !!currentMessage(),

				tagsToHTML: () => currentMessage()?.flags().map(value =>
						isAllowedKeyword(value)
						? '<span class="focused msgflag-'+value+'">' + i18n('MESSAGE_TAGS/'+value,0,value) + '</span>'
						: ''
					).join(' '),

				askReadReceipt: () => currentMessage()?.readReceipt
					&& !(MessagelistUserStore.isDraftFolder() || MessagelistUserStore.isSentFolder())
					&& !currentMessage()?.flags().includes('$mdnsent')
					&& !currentMessage()?.flags().includes('\\answered'),

				listAttachments: () => currentMessage()?.attachments()
					.filter(item => SettingsUserStore.listInlineAttachments() || !item.isLinked()),
	//			hasAttachments: () => currentMessage()?.attachments()?.length,
				hasAttachments: () => currentMessage()?.attachments()
					.some(item => SettingsUserStore.listInlineAttachments() || !item.isLinked()),
	//			listInline: () => currentMessage()?.attachments().filter(item => item.isLinked()),
	//			hasInline: () => currentMessage()?.attachments().some(item => item.isLinked()),

				canBeRepliedOrForwarded: () => !MessagelistUserStore.isDraftFolder() && this.messageVisible(),

				dkimIcon: () => {
					switch (this.dkimData()[0]) {
						case 'none':
							return '';
						case 'pass':
							return '✔';
						default:
							return '✖';
					}
				},
				dkimIconClass: () => 'pass' === this.dkimData()[0] ? 'iconcolor-green' : 'iconcolor-red',

				dkimTitle:() => {
					const dkim = this.dkimData();
					return dkim[0] ? dkim[2] || 'DKIM: ' + dkim[0] : '';
				},

				showWhitelistOptions: () => 'match' === SettingsUserStore.viewImages(),

				firstUnsubsribeLink: () => currentMessage()?.unsubsribeLinks()[0] || '',

				pgpSupported: () => currentMessage() && PgpUserStore.isSupported(),

				canBeUndeleted: () => currentMessage()?.isDeleted(),

				messageListOrViewLoading:
					() => MessagelistUserStore.isLoading() | MessageUserStore.loading()
			});

			addSubscribablesTo(this, {
				message: message => {
					if (message) {
						if (this.viewHash !== message.hash) {
							this.scrollMessageToTop();
						}
						this.viewHash = message.hash;
						// TODO: make first param a user setting #683
						this.viewFromShort(message.from.toString(false, true));
						this.dkimData(message.dkim[0] || ['none', '', '']);
						this.nowTracking(false);
					} else {
						MessagelistUserStore.selectedMessage(null);

						this.viewHash = '';

						this.scrollMessageToTop();
					}
				},

				showFullInfo: value => set(ClientSideKeyNameMessageHeaderFullInfo, value ? '1' : '0')
			});

			// commands
			this.replyCommand = createCommandReplyHelper(ComposeType.Reply);
			this.replyAllCommand = createCommandReplyHelper(ComposeType.ReplyAll);
			this.forwardCommand = createCommandReplyHelper(ComposeType.Forward);
			this.forwardAsAttachmentCommand = createCommandReplyHelper(ComposeType.ForwardAsAttachment);
			this.editAsNewCommand = createCommandReplyHelper(ComposeType.EditAsNew);

	//		this.deleteCommand = createCommandActionHelper(FolderType.Trash);
			// User setting hideDeleted || immediatelyMoveToTrash ??
			this.deleteCommand = createCommandDeleteHelper();
			// User setting !hideDeleted && !immediatelyMoveToTrash ??
			this.undeleteCommand = createCommandSetHelper(MessageSetAction.UnsetDeleted);
			this.deleteWithoutMoveCommand = createCommandActionHelper(FolderType.Trash, true);
			this.archiveCommand = createCommandActionHelper(FolderType.Archive);
			this.spamCommand = createCommandActionHelper(FolderType.Junk);
			this.notSpamCommand = createCommandActionHelper(FolderType.Inbox);

			decorateKoCommands(this, {
				editCommand: self => self.messageVisible(),
				moveCommand: self => self.messageVisible(),
				copyCommand: self => self.messageVisible(),
				goUpCommand: self => !self.messageListOrViewLoading(),
				goDownCommand: self => !self.messageListOrViewLoading()
			});
		}

		toggleFullInfo() {
			this.showFullInfo(!this.showFullInfo());
		}

		closeMessage() {
			currentMessage(null);
		}

		editCommand() {
			currentMessage() && showMessageComposer([ComposeType.Draft, currentMessage()]);
		}

		moveOrCopy(vm, event, mode) {
			if (vm && event?.preventDefault) {
				stopEvent(event);
			}
			this.actionsMenu().ddBtn.hide();
			AppUserStore.focusedState(ScopeFolderList);
			moveAction(mode);
		}

		moveCommand(vm, event) {
			this.moveOrCopy(vm, event, 1);
		}

		copyCommand(vm, event) {
			this.moveOrCopy(vm, event, 2);
		}

		setUnseen() {
			setAction(MessageSetAction.UnsetSeen);
			currentMessage(null);
		}

		goUpCommand() {
			fireEvent('mailbox.message-list.selector.go-up',
				!!currentMessage() // bForceSelect
			);
		}

		goDownCommand() {
			fireEvent('mailbox.message-list.selector.go-down',
				!!currentMessage() // bForceSelect
			);
		}

		/**
		 * @param {string} sType
		 * @returns {void}
		 */
		replyOrforward(sType) {
			showMessageComposer([sType, currentMessage()]);
		}

		onBuild(dom) {
			const eqs = (ev, s) => ev.target.closestWithin(s, dom);
			dom.addEventListener('click', event => {
				let el = eqs(event, 'a');
				if (el && 0 === event.button && mailToHelper(el.href)) {
					stopEvent(event);
					return;
				}

				el = eqs(event, '.attachmentsPlace .showPreview');
				if (el) {
					const attachment = ko.dataFor(el), url = attachment?.linkDownload();
	//				if (url && FileType.Eml === attachment.fileType) {
					if (url && RFC822 == attachment.mimeType) {
						stopEvent(event);
						fetchRaw(url).then(text => {
							const oMessage = new MessageModel();
							MimeToMessage(text, oMessage);
							// cleanHTML
							oMessage.popupMessage();
						});
					}
					return;
				}

				el = eqs(event, '.attachmentsPlace .showPreplay');
				if (el) {
					stopEvent(event);
					const attachment = ko.dataFor(el);
					if (attachment && SMAudio.supported) {
						switch (true) {
							case SMAudio.supportedMp3 && attachment.isMp3():
								SMAudio.playMp3(attachment.linkDownload(), attachment.fileName);
								break;
							case SMAudio.supportedOgg && attachment.isOgg():
								SMAudio.playOgg(attachment.linkDownload(), attachment.fileName);
								break;
							case SMAudio.supportedWav && attachment.isWav():
								SMAudio.playWav(attachment.linkDownload(), attachment.fileName);
								break;
							// no default
						}
					}
					return;
				}

				el = eqs(event, '.attachmentItem');
				if (el) {
					const attachment = ko.dataFor(el), url = attachment?.linkDownload();
					if (url) {
						if ('application/pgp-keys' == attachment.mimeType
						 && (OpenPGPUserStore.isSupported() || GnuPGUserStore.isSupported())) {
							fetchRaw(url).then(text =>
								showScreenPopup(OpenPgpImportPopupView, [text])
							);
						} else {
							download(url, attachment.fileName);
						}
					}
				}

				if (eqs(event, '.messageItemHeader .subjectParent .flagParent')) {
					setAction(currentMessage()?.isFlagged() ? MessageSetAction.UnsetFlag : MessageSetAction.SetFlag);
				}
			});

			keyScopeReal.subscribe(value => this.messageDomFocused(ScopeMessageView === value));

			// initShortcuts

			// exit fullscreen, back
			addShortcut('escape', '', ScopeMessageView, () => {
				if (!this.viewModelDom.hidden && currentMessage()) {
					const preview = SettingsUserStore.usePreviewPane();
					if (isFullscreen()) {
						exitFullscreen();
						if (preview) {
							AppUserStore.focusedState(ScopeMessageList);
						}
					} else if (!preview) {
						currentMessage(null);
					} else {
						AppUserStore.focusedState(ScopeMessageList);
					}

					return false;
				}
			});

			// fullscreen
			addShortcut('enter,open', '', ScopeMessageView, () => {
				isFullscreen() || toggleFullscreen();
				return false;
			});

			// reply
			registerShortcut('r,mailreply', '', [ScopeMessageList, ScopeMessageView], () => {
				if (currentMessage()) {
					this.replyCommand();
					return false;
				}
				return true;
			});

			// replyAll
			registerShortcut('a', '', [ScopeMessageList, ScopeMessageView], () => {
				if (currentMessage()) {
					this.replyAllCommand();
					return false;
				}
			});
			registerShortcut('mailreply', 'shift', [ScopeMessageList, ScopeMessageView], () => {
				if (currentMessage()) {
					this.replyAllCommand();
					return false;
				}
			});

			// forward
			registerShortcut('f,mailforward', '', [ScopeMessageList, ScopeMessageView], () => {
				if (currentMessage()) {
					this.forwardCommand();
					return false;
				}
			});

			// message information
			registerShortcut('i', 'meta', [ScopeMessageList, ScopeMessageView], () => {
				currentMessage() && this.toggleFullInfo();
				return false;
			});

			// toggle message blockquotes
			registerShortcut('b', '', [ScopeMessageList, ScopeMessageView], () => {
				const message = currentMessage();
				if (message?.body) {
					message.body.querySelectorAll('details').forEach(node => node.open = !node.open);
					return false;
				}
			});

			addShortcut('b', 'shift', [ScopeMessageList, ScopeMessageView], () => {
				if (!formFieldFocused()) {
					currentMessage()?.swapColors?.();
					return false;
				}
			});

			addShortcut('arrowup,arrowleft', 'meta', [ScopeMessageList, ScopeMessageView], () => {
				this.goUpCommand();
				return false;
			});

			addShortcut('arrowdown,arrowright', 'meta', [ScopeMessageList, ScopeMessageView], () => {
				this.goDownCommand();
				return false;
			});

			// delete
			addShortcut('delete', '', ScopeMessageView, () => {
				this.deleteCommand();
				return false;
			});
			addShortcut('delete', 'shift', ScopeMessageView, () => {
				this.deleteWithoutMoveCommand();
				return false;
			});

			// change focused state
			addShortcut('arrowleft', '', ScopeMessageView, () => {
				if (!isFullscreen() && currentMessage() && SettingsUserStore.usePreviewPane()
				 && !oMessageScrollerDom().scrollLeft) {
					AppUserStore.focusedState(ScopeMessageList);
					return false;
				}
			});
			addShortcut('tab', 'shift', ScopeMessageView, () => {
				if (!isFullscreen() && currentMessage() && SettingsUserStore.usePreviewPane()) {
					AppUserStore.focusedState(ScopeMessageList);
				}
				return false;
			});

			MessageUserStore.bodiesDom(dom.querySelector('.bodyText'));
		}

		scrollMessageToTop() {
			oMessageScrollerDom().scrollTop = 0;
		}

		scrollMessageToLeft() {
			oMessageScrollerDom().scrollLeft = 0;
		}

		toggleAttachmentControls() {
			const b = !this.showAttachmentControls();
			this.showAttachmentControls(b);
			set(ClientSideKeyNameMessageAttachmentControls, b);
		}

		downloadAsZip() {
			const hashes = (currentMessage()?.attachments || [])
				.map(item => item?.checked() /*&& !item?.isLinked()*/ ? item.download : '')
				.filter(v => v);
			downloadZip(
				currentMessage().subject(),
				hashes,
				() => this.downloadAsZipError(true),
				this.downloadAsZipLoading
			);
		}

		/**
		 * @param {MessageModel} oMessage
		 * @returns {void}
		 */
		showImages() {
			currentMessage().showExternalImages();
		}

		showTracking() {
			const msg = currentMessage(), body = msg?.body;
			if (body && msg.hasTracking()) {
				let attr = 'data-x-href-tracking';
				body.querySelectorAll('a['+attr+']').forEach(node => node.href = node.getAttribute(attr));
	//			attr = 'data-x-src-tracking';
	//			body.querySelectorAll('img['+attr+']').forEach(node => node.src = node.getAttribute(attr));
				this.nowTracking(true);
			}
		}

		whitelistText(txt) {
			let value = (SettingsUserStore.viewImagesWhitelist().trim() + '\n' + txt).trim();
	/*
			if ('pass' === currentMessage().spf[0]?.[0]) value += '+spf';
			if ('pass' === currentMessage().dkim[0]?.[0]) value += '+dkim';
			if ('pass' === currentMessage().dmarc[0]?.[0]) value += '+dmarc';
	*/
			SettingsUserStore.viewImagesWhitelist(value);
			Remote.saveSetting('ViewImagesWhitelist', value);
			currentMessage().showExternalImages(1);
		}

		/**
		 * @returns {string}
		 */
		printableCheckedMessageCount() {
			const cnt = MessagelistUserStore.listCheckedOrSelectedUidsWithSubMails().size;
			return 0 < cnt ? (100 > cnt ? cnt : '99+') : '';
		}

		/**
		 * @param {MessageModel} oMessage
		 * @returns {void}
		 */
		readReceipt() {
			let oMessage = currentMessage();
			if (oMessage.readReceipt) {
				oMessage.flags.push('$mdnsent');
				Remote.request('SendReadReceiptMessage',
					iError => iError && oMessage.flags.remove('$mdnsent'),
					{
						messageFolder: oMessage.folder,
						messageUid: oMessage.uid,
						readReceipt: oMessage.readReceipt,
						subject: i18n('READ_RECEIPT/SUBJECT', { SUBJECT: oMessage.subject() }),
						plain: i18n('READ_RECEIPT/BODY', { 'READ-RECEIPT': AccountUserStore.email() })
					}
				);
			}
		}

		newTag() {
			let message = currentMessage();
			if (message) {
				let keyword = prompt(i18n('MESSAGE/NEW_TAG'), '')?.replace(/[\s\\]+/g, '');
				if (keyword.length && isAllowedKeyword(keyword)) {
					message.toggleTag(keyword);
					FolderUserStore.currentFolder().permanentFlags.push(keyword);
				}
			}
		}

		pgpDecrypt() {
			const oMessage = currentMessage(),
				data = oMessage.pgpEncrypted();
			delete data.error;
			PgpUserStore.decrypt(oMessage).then(result => {
				if (!result) {
					// TODO: translate
					throw Error('Decryption failed, canceled or not possible');
				}
				oMessage.pgpDecrypted(true);
				if (result.data) {
					MimeToMessage(result.data, oMessage);
					oMessage.html() ? oMessage.viewHtml() : oMessage.viewPlain();
					if (result.signatures?.length) {
						oMessage.pgpSigned({
							signatures: result.signatures,
							success: !!result.signatures.length
						});
					}
				}
			})
			.catch(e => {
				data.error = e.message;
			})
			.finally(() => {
				oMessage.pgpEncrypted(data);
			});
		}

		pgpVerify(/*self, event*/) {
			const oMessage = currentMessage()/*, ctrl = event.target.closest('.openpgp-control')*/;
			PgpUserStore.verify(oMessage).then(result => {
				if (result) {
					oMessage.pgpSigned(result);
				} else {
					alert('Verification failed or no valid public key found');
				}
	/*
				if (result?.success) {
					i18n('CRYPTO/GOOD_SIGNATURE', {
						USER: validKey.user + ' (' + validKey.id + ')'
					});
					message.getText()
				} else {
					const keyIds = arrayLength(signingKeyIds) ? signingKeyIds : null,
						additional = keyIds
							? keyIds.map(item => item?.toHex?.()).filter(v => v).join(', ')
							: '';

					i18n('CRYPTO/ERROR', {
						TYPE: 'OpenPGP',
						ERROR: 'message'
					}) + (additional ? ' (' + additional + ')' : '');
				}
	*/
			});
		}

		async smimeDecrypt() {
			const message = currentMessage();
			const addresses = message.from.concat(message.to, message.cc, message.bcc).map(item => item.email),
				identity = IdentityUserStore.find(item => addresses.includes(item.email())),
				data = message.smimeEncrypted(); // { partId: "1" }
			if (data && identity) {
				delete data.error;
				let pass, params = { ...data }; // clone
				params.folder = message.folder;
				params.uid = message.uid;
	//			params.bodyPart = params.bodyPart?.raw;
				params.certificate = identity.smimeCertificate();
				params.privateKey = identity.smimeKey();
				if (identity.smimeKeyEncrypted()) {
					pass = await Passphrases.ask(identity,
						i18n('SMIME/PRIVATE_KEY_OF', {EMAIL: identity.email()}),
						'CRYPTO/DECRYPT'
					);
					if (!pass) {
						return;
					}
					params.passphrase = pass?.password;
				}
				Remote.post('SMimeDecryptMessage', null, params).then(response => {
					if (response?.Result?.data) {
						message.smimeDecrypted(true);
						MimeToMessage(response.Result.data, message);
						message.html() ? message.viewHtml() : message.viewPlain();
						pass && pass.remember && Passphrases.handle(identity, pass.password);
						if ('signed' in response.Result) {
							message.smimeSigned(response.Result.signed);
						}
					}
				}).catch(e => {
					data.error = e.message;
				})
				.finally(() => {
					message.smimeEncrypted(data);
				});
			}
		}

		smimeVerify(/*self, event*/) {
			const message = currentMessage(),
				data = message.smimeSigned(); // { partId: "1", micAlg: "pgp-sha256" }
			if (data) {
				const params = { ...data }; // clone
				params.folder = message.folder;
				params.uid = message.uid;
				params.bodyPart = data.bodyPart?.raw;
				params.sigPart = data.sigPart?.bodyRaw;
				Remote.post('SMimeVerifyMessage', null, params).then(response => {
					if (response?.Result) {
						if (response.Result.body) {
							MimeToMessage(response.Result.body, message);
							message.html() ? message.viewHtml() : message.viewPlain();
						}
						data.success = response.Result.success;
						message.smimeSigned(data);
					}
				});
			}
		}

	}

	class MailBoxUserScreen extends AbstractScreen {
		constructor() {
			var styleSheet = createElement('style');
			doc.head.appendChild(styleSheet);
			initOnStartOrLangChange(() =>
				styleSheet.innerText = '.subjectParent:empty::after,.subjectParent .subject:empty::after'
				+'{content:"'+i18n('MESSAGE/EMPTY_SUBJECT_TEXT')+'"}'
			);
			super('mailbox', [
				SystemDropDownUserView,
				MailFolderList,
				MailMessageList,
				MailMessageView
			]);
		}

		/**
		 * @returns {void}
		 */
		updateWindowTitle() {
			const count = Settings.app('listPermanentFiltered') ? 0 : FolderUserStore.foldersInboxUnreadCount(),
				email = AccountUserStore.email();

			rl.setTitle(
				(email
					? '' + (0 < count ? '(' + count + ') ' : ' ') + email + ' - '
					: ''
				) + i18n('TITLES/MAILBOX')
			);
		}

		/**
		 * @returns {void}
		 */
		onShow() {
			this.updateWindowTitle();
			AppUserStore.focusedState('none');
			AppUserStore.focusedState(ScopeMessageList);
		}

		/**
		 * @param {string} folderHash
		 * @param {number} page
		 * @param {string} search
		 * @returns {void}
		 */
		onRoute(folderHash, page, search, messageUid) {
			// Only works when FolderUserStore.folderList() is loaded
			const folder = getFolderFromHashMap(folderHash.replace(/~([\d]+)$/, ''));
			if (folder) {
				FolderUserStore.currentFolder(folder);
				MessagelistUserStore.page(1 > page ? 1 : page);
				MessagelistUserStore.listSearch(search);
				if (messageUid) {
					let message = new MessageModel;
					message.folder = folderHash;
					message.uid = messageUid;
					populateMessageBody(message);
				} else {
					let threadUid = folderHash.replace(/^.+~(\d+)$/, '$1');
					MessagelistUserStore.threadUid((folderHash === threadUid) ? 0 : pInt(threadUid));
				}
				MessagelistUserStore.reload();
			}
		}

		/**
		 * @returns {void}
		 */
		onStart() {
			super.onStart();

			addEventListener('mailbox.inbox-unread-count', e => {
				FolderUserStore.foldersInboxUnreadCount(e.detail);
	/*			// Disabled in SystemDropDown.html
				const email = AccountUserStore.email();
				AccountUserStore.forEach(item =>
					email === item?.email && item?.count(e.detail)
				);
	*/
				this.updateWindowTitle();
			});
		}

		/**
		 * @returns {void}
		 */
		onBuild() {
			doc.addEventListener('click', event =>
				event.target.closest('#rl-right') && moveAction(0)
			);
		}

		/**
		 * Parse link as generated by mailBox()
		 * @returns {Array}
		 */
		routes() {
			const
				folder = (request, vals) => request ? pString(vals[0]) : getFolderInboxName(),
				fNormS = (request, vals) => [folder(request, vals), request ? pInt(vals[1]) : 1, decodeURI(pString(vals[2]))];

			return [
				// Folder: INBOX | INBOX.sub | Sent | fullNameHash
				[/^([^/]*)$/, { normalize_: fNormS }],
				// Search: {folder}/{string}
				[/^([a-zA-Z0-9.~_-]+)\/(.+)\/?$/, { normalize_: (request, vals) =>
					[folder(request, vals), 1, decodeURI(pString(vals[1]))]
				}],
				// Message: {folder}/m{uid}(/{search})?
				[/^([a-zA-Z0-9.~_-]+)\/m([1-9][0-9]*)(?:\/(.+))?$/, { normalize_: (request, vals) =>
					[folder(request, vals), 1, pString(vals[2]), pString(vals[1])]
				}],
				// Page: {folder}/p{int}(/{search})?
				[/^([a-zA-Z0-9.~_-]+)\/p([1-9][0-9]*)(?:\/(.+))?$/, { normalize_: fNormS }]
			];
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

	class UserSettingsGeneral extends AbstractViewSettings {
		constructor() {
			super();

			this.mailto = ko.observable(!!navigator.registerProtocolHandler);

			this.language = LanguageStore.language;
			this.languages = LanguageStore.languages;
			this.hourCycle = LanguageStore.hourCycle;

			this.soundNotification = SMAudio.notifications;
			this.notificationSound = ko.observable(SettingsGet('NotificationSound'));
			this.notificationSounds = ko.observableArray(SettingsGet('newMailSounds'));

			this.minRefreshInterval = SettingsGet('minRefreshInterval');

			this.desktopNotifications = NotificationUserStore.enabled;
			this.isDesktopNotificationAllowed = NotificationUserStore.allowed;

			this.threadsAllowed = AppUserStore.threadsAllowed;
			// 'THREAD=REFS', 'THREAD=REFERENCES', 'THREAD=ORDEREDSUBJECT'
			this.threadAlgorithms = ko.observableArray();
			FolderUserStore.capabilities.forEach(capa =>
				capa.startsWith('THREAD=') && this.threadAlgorithms.push(capa.slice(7))
			);
			this.threadAlgorithms.sort((a, b) => a.length - b.length);
			this.threadAlgorithm = SettingsUserStore.threadAlgorithm;

			['useThreads', 'threadAlgorithm',
			 // These use addSetting()
			 'layout', 'messageReadDelay', 'messagesPerPage', 'checkMailInterval',
			 'editorDefaultType', 'editorWysiwyg', 'msgDefaultAction', 'maxBlockquotesLevel',
			 // These are in addSettings()
			 'requestReadReceipt', 'requestDsn', 'requireTLS', 'pgpSign', 'pgpEncrypt',
			 'viewHTML', 'viewImages', 'viewImagesWhitelist', 'removeColors', 'allowStyles', 'allowDraftAutosave',
			 'hideDeleted', 'listInlineAttachments', 'simpleAttachmentsList', 'collapseBlockquotes',
			 'useCheckboxesInList', 'listGrouped', 'replySameFolder', 'allowSpellcheck',
			 'messageReadAuto', 'showNextMessage', 'messageNewWindow', 'markdown'
			].forEach(name => this[name] = SettingsUserStore[name]);

			this.allowLanguagesOnSettings = !!SettingsGet('allowLanguagesOnSettings');

			this.languageTrigger = ko.observable(SaveSettingStatus.Idle);

			this.identities = IdentityUserStore;

			this.wysiwygs = WYSIWYGS;

			addComputablesTo(this, {
				languageFullName: () => convertLangName(this.language()),

				identityMainDesc: () => {
					const identity = IdentityUserStore.main();
					return identity ? identity.formattedName() : '---';
				},

				editorDefaultTypes: () => {
					translateTrigger();
					return [
						{ id: 'Html', name: i18n('SETTINGS_GENERAL/EDITOR_HTML') },
						{ id: 'Plain', name: i18n('SETTINGS_GENERAL/EDITOR_PLAIN') }
					];
				},

				hasWysiwygs: () => 1 < WYSIWYGS().length,

				msgDefaultActions: () => {
					translateTrigger();
					return [
						{ id: 1, name: i18n('MESSAGE/BUTTON_REPLY') }, // ComposeType.Reply,
						{ id: 2, name: i18n('MESSAGE/BUTTON_REPLY_ALL') } // ComposeType.ReplyAll
					];
				},

				layoutTypes: () => {
					translateTrigger();
					return [
						{ id: 0, name: i18n('SETTINGS_GENERAL/LAYOUT_NO_SPLIT') },
						{ id: LayoutSideView, name: i18n('SETTINGS_GENERAL/LAYOUT_VERTICAL_SPLIT') },
						{ id: LayoutBottomView, name: i18n('SETTINGS_GENERAL/LAYOUT_HORIZONTAL_SPLIT') }
					];
				}
			});

			this.addSetting('EditorDefaultType');
			this.addSetting('editorWysiwyg');
			this.addSetting('MsgDefaultAction');
			this.addSetting('MessageReadDelay');
			this.addSetting('MessagesPerPage');
			this.addSetting('CheckMailInterval');
			this.addSetting('Layout');
			this.addSetting('MaxBlockquotesLevel');

			this.addSettings([
				'requestReadReceipt', 'requestDsn', 'requireTLS', 'pgpSign', 'pgpEncrypt',
				'ViewHTML', 'ViewImages', 'ViewImagesWhitelist', 'RemoveColors', 'AllowStyles', 'AllowDraftAutosave',
				'HideDeleted', 'ListInlineAttachments', 'simpleAttachmentsList', 'CollapseBlockquotes',
				'UseCheckboxesInList', 'listGrouped', 'ReplySameFolder', 'allowSpellcheck',
				'messageReadAuto', 'showNextMessage', 'messageNewWindow', 'markdown',
				'DesktopNotifications', 'SoundNotification']);

			const fReloadLanguageHelper = (saveSettingsStep) => () => {
					this.languageTrigger(saveSettingsStep);
					setTimeout(() => this.languageTrigger(SaveSettingStatus.Idle), 1000);
				};

			addSubscribablesTo(this, {
				language: value => {
					this.languageTrigger(SaveSettingStatus.Saving);
					translatorReload(value)
						.then(fReloadLanguageHelper(SaveSettingStatus.Success), fReloadLanguageHelper(SaveSettingStatus.Failed))
						.then(() => Remote.saveSetting('language', value));
				},

				hourCycle: value =>
					Remote.saveSetting('hourCycle', value),

				notificationSound: value => {
					Remote.saveSetting('NotificationSound', value);
					Settings.set('NotificationSound', value);
				},

				useThreads: value => {
					MessagelistUserStore([]);
					Remote.saveSetting('UseThreads', value);
				},

				threadAlgorithm: value => {
					MessagelistUserStore([]);
					Remote.saveSetting('threadAlgorithm', value);
				},

				checkMailInterval: () => {
					setRefreshFoldersInterval(SettingsUserStore.checkMailInterval());
				}
			});
		}

		editMainIdentity() {
			editIdentity(IdentityUserStore.main());
		}

		testSoundNotification() {
			SMAudio.playNotification(true);
		}

		testSystemNotification() {
			NotificationUserStore.display('SnappyMail', 'Test notification');
		}

		selectLanguage() {
			showScreenPopup(LanguagesPopupView, [this.language, this.languages(), LanguageStore.userLanguage()]);
		}

		registerMailto() {
			console.log(`mailto = ${location.protocol}//${location.host}${location.pathname}?mailto`);
			navigator.registerProtocolHandler(
				'mailto',
				`${location.protocol}//${location.host}${location.pathname}?mailto&to=%s`,
				(SettingsGet('title') || 'SnappyMail')
			);
			alert(i18n('GLOBAL/DONE'));
			this.mailto(0);
		}
	}

	class UserSettingsContacts /*extends AbstractViewSettings*/ {
		constructor() {
			this.contactsAutosave = ko.observable(!!SettingsGet('ContactsAutosave'));

			this.allowContactsSync = ContactUserStore.allowSync;
			this.syncMode = ContactUserStore.syncMode;
			this.syncUrl = ContactUserStore.syncUrl;
			this.syncUser = ContactUserStore.syncUser;
			this.syncPass = ContactUserStore.syncPass;

			this.syncModeOptions = koComputable(() => {
				translateTrigger();
				return [
					{ id: 0, name: i18n('GLOBAL/NO') },
					{ id: 1, name: i18n('GLOBAL/YES') },
					{ id: 2, name: i18n('SETTINGS_CONTACTS/SYNC_READ') },
				];
			});

			this.saveTrigger = koComputable(() =>
					[
						ContactUserStore.syncMode(),
						ContactUserStore.syncUrl(),
						ContactUserStore.syncUser(),
						ContactUserStore.syncPass()
					].join('|')
				)
				.extend({ debounce: 500 });

			this.contactsAutosave.subscribe(value =>
				Remote.saveSettings(null, { ContactsAutosave: value })
			);

			this.saveTrigger.subscribe(() =>
				Remote.request('SaveContactsSyncData', null, {
					Mode: ContactUserStore.syncMode(),
					Url: ContactUserStore.syncUrl(),
					User: ContactUserStore.syncUser(),
					Password: ContactUserStore.syncPass()
				})
			);
		}
	}

	class UserSettingsAccounts /*extends AbstractViewSettings*/ {
		constructor() {
			this.allowAdditionalAccount = SettingsCapa('AdditionalAccounts');
			this.allowIdentities = SettingsCapa('Identities');

			this.accounts = AccountUserStore;
			this.loading = AccountUserStore.loading;
			this.identities = IdentityUserStore;
			this.mainEmail = SettingsGet('mainEmail');

			this.accountForDeletion = ko.observable(null).askDeleteHelper();
			this.identityForDeletion = ko.observable(null).askDeleteHelper();

			this.showUnread = SettingsUserStore.showUnreadCount;
			SettingsUserStore.showUnreadCount.subscribe(value => Remote.saveSetting('ShowUnreadCount', value));

	//		this.additionalAccounts = koComputable(() => AccountUserStore.filter(account => account.isAdditional()));
		}

		addNewAccount() {
			showScreenPopup(AccountPopupView);
		}

		editAccount(account) {
			if (account?.isAdditional()) {
				showScreenPopup(AccountPopupView, [account]);
			}
		}

		addNewIdentity() {
			editIdentity();
		}

		editIdentity(identity) {
			editIdentity(identity);
		}

		/**
		 * @param {AccountModel} accountToRemove
		 * @returns {void}
		 */
		deleteAccount(accountToRemove) {
			if (accountToRemove?.askDelete()) {
				this.accountForDeletion(null);
				this.accounts.remove(account => accountToRemove === account);

				Remote.request('AccountDelete', (iError, data) => {
					if (!iError && data.Reload) {
						rl.route.root();
						setTimeout(() => location.reload(), 1);
					} else {
						loadAccountsAndIdentities();
					}
				}, {
					emailToDelete: accountToRemove.email
				});
			}
		}

		/**
		 * @param {IdentityModel} identityToRemove
		 * @returns {void}
		 */
		deleteIdentity(identityToRemove) {
			if (identityToRemove?.askDelete()) {
				this.identityForDeletion(null);
				IdentityUserStore.remove(oIdentity => identityToRemove === oIdentity);
				Remote.request('IdentityDelete', () => rl.app.accountsAndIdentities(), {
					idToDelete: identityToRemove.id()
				});
			}
		}

		accountsAndIdentitiesAfterMove() {
			Remote.request('AccountsAndIdentitiesSortOrder', null, {
				Accounts: AccountUserStore.filter(item => item.isAdditional()).map(item => item.email),
				Identities: IdentityUserStore.map(item => (item ? item.id() : ""))
			});
		}

		onBuild(oDom) {
			oDom.addEventListener('click', event => {
				let el = event.target.closestWithin('.accounts-list .e-action', oDom);
				el && ko.dataFor(el) && this.editAccount(ko.dataFor(el));

				el = event.target.closestWithin('.identities-list .e-action', oDom);
				el && ko.dataFor(el) && this.editIdentity(ko.dataFor(el));
			});
		}
	}

	//export class UserSettingsFilters /*extends AbstractViewSettings*/ {
	class UserSettingsFilters /*extends AbstractViewSettings*/ {
		constructor() {
			this.scripts = ko.observableArray();
			this.loading = ko.observable(true).extend({ debounce: 200 });
			addObservablesTo(this, {
				serverError: false,
				serverErrorDesc: ''
			});

			rl.loadScript(SettingsGet('StaticLibsJs').replace('/libs.', '/sieve.')).then(() => {
				const Sieve = window.Sieve;
				Sieve.folderList = FolderUserStore.folderList;
				Sieve.serverError.subscribe(value => this.serverError(value));
				Sieve.serverErrorDesc.subscribe(value => this.serverErrorDesc(value));
				Sieve.loading.subscribe(value => this.loading(value));
				Sieve.scripts.subscribe(value => this.scripts(value));
				Sieve.updateList();
			}).catch(e => console.error(e));

			this.hasActive = koComputable(() => this.scripts().filter(script=>script.active()).length);

			this.scriptForDeletion = ko.observable(null).askDeleteHelper();
		}

	/*
		// TODO: issue on account switch
		// When current domain has sieve but the new has not, or current has not and the new has
		disabled() {
			return !SettingsCapa('Sieve');
		}
	*/

		addScript() {
			this.editScript();
		}

		editScript(script) {
			window.Sieve.ScriptView.showModal(script ? [script] : null);
		}

		deleteScript(script) {
			window.Sieve.deleteScript(script);
		}

		disableScripts() {
			window.Sieve.setActiveScript('');
		}

		enableScript(script) {
			window.Sieve.setActiveScript(script.name());
		}

		onBuild(oDom) {
			oDom.addEventListener('click', event => {
				const el = event.target.closestWithin('.script-item .script-name', oDom),
					script = el && ko.dataFor(el);
				script && this.editScript(script);
			});
		}

		onShow() {
			window.Sieve?.updateList();
		}
	}

	class OpenPgpGeneratePopupView extends AbstractViewPopup {
		constructor() {
			super('OpenPgpGenerate');

			this.identities = IdentityUserStore;

			addObservablesTo(this, {
				email: '',
				emailError: false,

				name: '',
				password: '',
				keyType: 'ECC',

				submitRequest: false,
				submitError: '',

				backupPublicKey: true,
				backupPrivateKey: false,

				saveGnuPGPublic: true,
				saveGnuPGPrivate: false
			});

			this.canGnuPG = SettingsCapa('GnuPG');

			this.email.subscribe(() => this.emailError(false));
		}

		submitForm() {
			const type = this.keyType().toLowerCase(),
				userId = {
					name: this.name(),
					email: IDN.toASCII(this.email())
				},
				cfg = {
					type: type,
					userIDs: [userId],
					passphrase: this.password().trim()
	//				format: 'armored' // output key format, defaults to 'armored' (other options: 'binary' or 'object')
				};
	/*
			if ('ecc' === type) {
				cfg.curve = 'curve25519';
			} else {
				cfg.rsaBits = pInt(this.keyBitLength());
			}
	*/
			this.emailError(!this.email().trim());
			if (this.emailError()) {
				return;
			}

			this.submitRequest(true);
			this.submitError('');

			openpgp.generateKey(cfg).then(keyPair => {
				if (keyPair) {
					const fn = () => {
						this.submitRequest(false);
						this.close();
					};

					OpenPGPUserStore.storeKeyPair(keyPair);

					keyPair.onServer = (this.backupPublicKey() ? 1 : 0) + (this.backupPrivateKey() ? 2 : 0);
					keyPair.inGnuPG = (this.saveGnuPGPublic() ? 1 : 0) + (this.saveGnuPGPrivate() ? 2 : 0);
					if (keyPair.onServer || keyPair.inGnuPG) {
						if (!this.backupPrivateKey() && !this.saveGnuPGPrivate()) {
							delete keyPair.privateKey;
						}
						GnuPGUserStore.storeKeyPair(keyPair, fn);
					} else {
						fn();
					}
				}
			})
			.catch((e) => {
				this.submitRequest(false);
				this.showError(e);
			});
		}

		hideError() {
			this.submitError('');
		}

		showError(e) {
			console.log(e);
			if (e?.message) {
				this.submitError(e.message);
			}
		}

		onShow() {
			this.name(''/*IdentityUserStore()[0].name()*/);
			this.password('');
			this.email(''/*IdentityUserStore()[0].email()*/);
			this.emailError(false);
			this.submitError('');
		}
	}

	class SMimeImportPopupView extends AbstractViewPopup {
		constructor() {
			super('SMimeImport');

			addObservablesTo(this, {
				pem: '',
				pemError: false,
				pemErrorMessage: '',
				pemValid: false
			});

			this.pem.subscribe(value => {
				this.pemError(false);
				this.pemErrorMessage('');
				this.pemValid(value && value.includes('-----BEGIN CERTIFICATE-----'));
			});
		}

		submitForm() {
			if (this.pemValid()) {
				Remote.request('SMimeImportCertificate',
					(iError, oData) => {
						if (iError) {
							this.pemError(true);
							this.pemErrorMessage(getNotification(iError, oData?.message));
	//						oData?.messageAdditional;
						} else {
							this.close();
						}
					},
					{pem:this.pem()}
				);
			} else {
				this.pemError(true);
			}
		}

		onShow() {
			this.pem('');
			this.pemError(false);
			this.pemErrorMessage('');
		}
	}

	class UserSettingsSecurity extends AbstractViewSettings {
		constructor() {
			super();

			this.autoLogout = SettingsUserStore.autoLogout;
			this.autoLogoutOptions = koComputable(() => {
				translateTrigger();
				return [
					{ id: 0, name: i18n('SETTINGS_SECURITY/NEVER') },
					{ id: 5, name: relativeTime(300) },
					{ id: 15, name: relativeTime(900) },
					{ id: 30, name: relativeTime(1800) },
					{ id: 60, name: relativeTime(3600) },
					{ id: 120, name: relativeTime(7200) },
					{ id: 300, name: relativeTime(18000) },
					{ id: 600, name: relativeTime(36000) }
				];
			});
			this.addSetting('AutoLogout');

			this.keyPassForget = SettingsUserStore.keyPassForget;
			this.addSetting('keyPassForget');

			this.gnupgPublicKeys = GnuPGUserStore.publicKeys;
			this.gnupgPrivateKeys = GnuPGUserStore.privateKeys;

			this.openpgpkeysPublic = OpenPGPUserStore.publicKeys;
			this.openpgpkeysPrivate = OpenPGPUserStore.privateKeys;

			this.smimeCertificates = SMimeUserStore;

			this.canOpenPGP = SettingsCapa('OpenPGP');
			this.canGnuPG = GnuPGUserStore.isSupported();
			this.canMailvelope = !!window.mailvelope;
		}

		addOpenPgpKey() {
			showScreenPopup(OpenPgpImportPopupView);
		}

		generateOpenPgpKey() {
			showScreenPopup(OpenPgpGeneratePopupView);
		}

		importToOpenPGP() {
			OpenPGPUserStore.loadBackupKeys();
		}

		importToSMime() {
			showScreenPopup(SMimeImportPopupView);
		}

		onBuild() {
			/**
			 * Create an iframe to display the Mailvelope keyring settings.
			 * The iframe will be injected into the container identified by selector.
			 */
			window.mailvelope && mailvelope.createSettingsContainer('#mailvelope-settings'/*[, keyring], options*/);
			/**
			 * https://github.com/the-djmaze/snappymail/issues/973
			Remote.request('GetStoredPGPKeys', (iError, data) => {
				console.dir([iError, data]);
			});
			*/
		}
	}

	const folderForDeletion = ko.observable(null).askDeleteHelper();

	class UserSettingsFolders /*extends AbstractViewSettings*/ {
		constructor() {
			this.showKolab = FolderUserStore.allowKolab();
			this.defaultOptionsAfterRender = defaultOptionsAfterRender;
			this.kolabTypeOptions = ko.observableArray();
			let i18nFilter = key => i18n('SETTINGS_FOLDERS/TYPE_' + key);
			initOnStartOrLangChange(()=>{
				this.kolabTypeOptions([
					{ id: '', name: '' },
					{ id: 'event', name: i18nFilter('CALENDAR') },
					{ id: 'contact', name: i18nFilter('CONTACTS') },
					{ id: 'task', name: i18nFilter('TASKS') },
					{ id: 'note', name: i18nFilter('NOTES') },
					{ id: 'file', name: i18nFilter('FILES') },
					{ id: 'journal', name: i18nFilter('JOURNAL') },
					{ id: 'configuration', name: i18nFilter('CONFIGURATION') }
				]);
			});

			this.displaySpecSetting = FolderUserStore.displaySpecSetting;
			this.folderList = FolderUserStore.folderList;
			this.folderListOptimized = FolderUserStore.optimized;
			this.folderListError = FolderUserStore.error;
			this.hideUnsubscribed = SettingsUserStore.hideUnsubscribed;
			this.unhideKolabFolders = SettingsUserStore.unhideKolabFolders;

			this.loading = FolderUserStore.foldersChanging;

			this.folderForDeletion = folderForDeletion;

			SettingsUserStore.hideUnsubscribed.subscribe(value => Remote.saveSetting('HideUnsubscribed', value));
			SettingsUserStore.unhideKolabFolders.subscribe(value => Remote.saveSetting('UnhideKolabFolders', value));
		}

		onShow() {
			FolderUserStore.error('');
		}
	/*
		onBuild(oDom) {
		}
	*/
		createFolder() {
			showScreenPopup(FolderCreatePopupView);
		}

		systemFolder() {
			showScreenPopup(FolderSystemPopupView);
		}

		deleteFolder(folderToRemove) {
			if (folderToRemove
			 && folderToRemove.canBeDeleted()
			 && folderToRemove.askDelete()
			) {
				if (0 < folderToRemove.totalEmails()) {
	//				FolderUserStore.error(getNotification(Notifications.CantDeleteNonEmptyFolder));
					folderToRemove.errorMsg(getNotification(Notifications.CantDeleteNonEmptyFolder));
				} else {
					folderForDeletion(null);

					if (folderToRemove) {
						Remote.abort('Folders').post('FolderDelete', FolderUserStore.foldersDeleting, {
								folder: folderToRemove.fullName
							}).then(
								() => {
	//								folderToRemove.attributes.push('\\nonexistent');
									folderToRemove.selectable(false);
	//								folderToRemove.isSubscribed(false);
	//								folderToRemove.checkable(false);
									if (!folderToRemove.subFolders.length) {
										removeFolderFromCacheList(folderToRemove.fullName);
										const folder = getFolderFromCacheList(folderToRemove.parentName);
										(folder ? folder.subFolders : FolderUserStore.folderList).remove(folderToRemove);
									}
								},
								error => {
									FolderUserStore.error(
										getNotification(error.code, '', Notifications.CantDeleteFolder)
										+ '.\n' + error.message
									);
								}
							);
					}
				}
			}
		}

		hideError() {
			FolderUserStore.error('');
		}

		toggleFolderKolabType(folder, event) {
			let type = event.target.value;
			// TODO: append '.default' ?
			Remote.request('FolderSetMetadata', null, {
				folder: folder.fullName,
				key: FolderMetadataKeys.KolabFolderType,
				value: type
			});
			folder.kolabType(type);
		}

		toggleFolderSubscription(folder) {
			let subscribe = !folder.isSubscribed();
			Remote.request('FolderSubscribe', null, {
				folder: folder.fullName,
				subscribe: subscribe ? 1 : 0
			});
			folder.isSubscribed(subscribe);
		}

		toggleFolderCheckable(folder) {
			let checkable = !folder.checkable();
			Remote.request('FolderCheckable', null, {
				folder: folder.fullName,
				checkable: checkable ? 1 : 0
			});
			folder.checkable(checkable);
		}
	}

	const themeBackground = {
		name: ThemeStore.userBackgroundName,
		hash: ThemeStore.userBackgroundHash
	};
	addObservablesTo(themeBackground, {
		uploaderButton: null,
		loading: false,
		error: ''
	});

	class UserSettingsThemes /*extends AbstractViewSettings*/ {
		constructor() {
			this.fontSansSerif = ThemeStore.fontSansSerif;
			this.fontSerif = ThemeStore.fontSerif;
			this.fontMono = ThemeStore.fontMono;
			addSubscribablesTo(ThemeStore, {
				fontSansSerif: value => {
					Remote.saveSettings(null, {
						fontSansSerif: value
					});
				},
				fontSerif: value => {
					Remote.saveSettings(null, {
						fontSerif: value
					});
				},
				fontMono: value => {
					Remote.saveSettings(null, {
						fontMono: value
					});
				}
			});

			this.theme = ThemeStore.theme;
			this.themes = ThemeStore.themes;
			this.themesObjects = ko.observableArray();

			themeBackground.enabled = SettingsCapa('UserBackground');
			this.background = themeBackground;

			this.themeTrigger = ko.observable(SaveSettingStatus.Idle).extend({ debounce: 100 });

			ThemeStore.theme.subscribe(value => {
				this.themesObjects.forEach(theme => theme.selected(value === theme.name));

				changeTheme(value, this.themeTrigger);

				Remote.saveSettings(null, {
					Theme: value
				});
			});
		}

		setTheme(theme) {
			ThemeStore.theme(theme.name);
		}

		onBuild() {
			const currentTheme = ThemeStore.theme();

			this.themesObjects(
				ThemeStore.themes.map(theme => ({
					name: theme,
					nameDisplay: convertThemeName(theme),
					selected: ko.observable(theme === currentTheme),
					themePreviewSrc: themePreviewLink(theme)
				}))
			);

			// initUploader

			if (themeBackground.uploaderButton() && themeBackground.enabled) {
				const oJua = new Jua({
					action: serverRequest('UploadBackground'),
					limit: 1,
					clickElement: themeBackground.uploaderButton()
				});

				oJua
					.on('onStart', () => {
						themeBackground.loading(true);
						themeBackground.error('');
					})
					.on('onComplete', (id, result, data) => {
						themeBackground.loading(false);
						themeBackground.name(data?.Result?.name || '');
						themeBackground.hash(data?.Result?.hash || '');
						if (!themeBackground.name() || !themeBackground.hash()) {
							let errorMsg = '';
							if (data.code) {
								switch (data.code) {
									case UploadErrorCode.FileIsTooBig:
										errorMsg = i18n('SETTINGS_THEMES/ERROR_FILE_IS_TOO_BIG');
										break;
									case UploadErrorCode.FileType:
										errorMsg = i18n('SETTINGS_THEMES/ERROR_FILE_TYPE_ERROR');
										break;
									// no default
								}
							}

							themeBackground.error(errorMsg || data.message || i18n('SETTINGS_THEMES/ERROR_UNKNOWN'));
						}
					});
			}
		}

		onShow() {
			themeBackground.error('');
		}

		clearBackground() {
			if (themeBackground.enabled) {
				Remote.request('ClearUserBackground', () => {
					themeBackground.name('');
					themeBackground.hash('');
				});
			}
		}
	}

	class SettingsMenuUserView extends AbstractViewLeft {
		/**
		 * @param {Object} screen
		 */
		constructor(screen) {
			super();

			this.menu = screen.menu;
		}

		link(route) {
			return settings(route);
		}

		backToInbox() {
			hasher.setHash(mailbox(getFolderInboxName()));
		}
	}

	class SettingsPaneUserView extends AbstractViewRight {
		constructor() {
			super();
		}

		onShow() {
			MessageUserStore.message(null);
		}

		onBuild(dom) {
			dom.addEventListener('click', () => {
				if (event.target.closestWithin('.toggleLeft', dom)) {
					toggleLeftPanel();
				} else {
					ThemeStore.isMobile() && leftPanelDisabled(true);
				}
			});
		}
	}

	class SettingsUserScreen extends AbstractSettingsScreen {
		constructor() {
			super([SettingsMenuUserView, SettingsPaneUserView, SystemDropDownUserView]);

			const views = [
				UserSettingsGeneral
			];

			if (AppUserStore.allowContacts()) {
				views.push(UserSettingsContacts);
			}

			if (SettingsCapa('AdditionalAccounts') || SettingsCapa('Identities')) {
				views.push(UserSettingsAccounts);
			}

			// TODO: issue on account switch
			// When current domain has sieve but the new has not, or current has not and the new has
			if (SettingsCapa('Sieve')) {
				views.push(UserSettingsFilters);
			}

			views.push(UserSettingsSecurity);

			views.push(UserSettingsFolders);

			if (SettingsCapa('Themes')) {
				views.push(UserSettingsThemes);
			}

			views.forEach((item, index) =>
				settingsAddViewModel(item, item.name.replace('User', ''),
					(item === UserSettingsAccounts && !SettingsCapa('AdditionalAccounts'))
						? 'SETTINGS_ACCOUNTS/LEGEND_IDENTITIES' : 0,
					0, 0 === index)
			);

			runSettingsViewModelHooks(false);

			initOnStartOrLangChange(
				() => this.sSettingsTitle = i18n('TITLES/SETTINGS'),
				() => this.setSettingsTitle()
			);
		}

		onShow() {
			this.setSettingsTitle();
			keyScope(ScopeSettings);
		}

		setSettingsTitle() {
			const sEmail = AccountUserStore.email();
			rl.setTitle((sEmail ? sEmail + ' - ' :  '') + this.sSettingsTitle);
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

	class AppUser extends AbstractApp {
		constructor() {
			super(Remote);

			// wakeUp
			const interval = 3600000; // 60m
			let lastTime = Date.now();
			setInterval(() => {
				const currentTime = Date.now();
				(currentTime > (lastTime + interval + 1000))
				&& Remote.request('Version',
						iError => (100 < iError) && location.reload(),
						{ version: Settings.app('version') }
					);
				lastTime = currentTime;
			}, interval);

			addEventsListener(doc, ['keydown','keyup'], (ev=>$htmlCL.toggle('rl-ctrl-key-pressed', ev.ctrlKey)).debounce(500));

			addShortcut('escape,enter', '', dropdownsDetectVisibility);
			addEventListener('click', dropdownsDetectVisibility);

			this.folderList = FolderUserStore.folderList;
			this.messageList = MessagelistUserStore;

			this.ask = AskPopupView;

			this.loadAccountsAndIdentities = loadAccountsAndIdentities;
		}

		/**
		 * @param {number} iFolderType
		 * @param {string} sFromFolderFullName
		 * @param {Set} oUids
		 * @param {boolean=} bDelete = false
		 */
		moveMessagesToFolderType(iFolderType, sFromFolderFullName, oUids, bDelete) {
			let oMoveFolder = null,
				nSetSystemFoldersNotification = 0;

			switch (iFolderType) {
				case FolderType.Junk:
					oMoveFolder = getFolderFromCacheList(FolderUserStore.spamFolder());
					nSetSystemFoldersNotification = iFolderType;
					bDelete = bDelete || UNUSED_OPTION_VALUE === FolderUserStore.spamFolder();
					break;
				case FolderType.Inbox:
					oMoveFolder = getFolderFromCacheList(getFolderInboxName());
					break;
				case FolderType.Trash:
					oMoveFolder = getFolderFromCacheList(FolderUserStore.trashFolder());
					nSetSystemFoldersNotification = iFolderType;
					bDelete = bDelete/* || UNUSED_OPTION_VALUE === FolderUserStore.trashFolder()*/
						|| sFromFolderFullName === FolderUserStore.spamFolder()
						|| sFromFolderFullName === FolderUserStore.trashFolder();
					break;
				case FolderType.Archive:
					oMoveFolder = getFolderFromCacheList(FolderUserStore.archiveFolder());
					nSetSystemFoldersNotification = iFolderType;
					bDelete = bDelete || UNUSED_OPTION_VALUE === FolderUserStore.archiveFolder();
					break;
				// no default
			}

			if (bDelete) {
				showScreenPopup(AskPopupView, [
					i18n('POPUPS_ASK/DESC_WANT_DELETE_MESSAGES'),
					() => {
						MessagelistUserStore.moveMessages(sFromFolderFullName, oUids);
					}
				]);
			} else if (oMoveFolder) {
				MessagelistUserStore.moveMessages(sFromFolderFullName, oUids, oMoveFolder.fullName);
			} else {
				showScreenPopup(FolderSystemPopupView, [nSetSystemFoldersNotification]);
			}
		}

		/**
		 * @param {string} folder
		 * @param {Array=} list = []
		 */
		folderInformation(folder, list) {
			folderInformation(folder, list);
		}

		logout() {
			Remote.request('Logout', (iError, data) =>
				iError ? alert('Logout error: ' + getErrorMessage(iError, data))
					: rl.logoutReload(Settings.app('customLogoutLink'))
			);
		}

		bootstart() {
			super.bootstart();

			addEventListener('beforeunload', event => {
				if (arePopupsVisible() || (!SettingsUserStore.usePreviewPane() && MessageUserStore.message())) {
					event.preventDefault();
					return event.returnValue = i18n('POPUPS_ASK/EXIT_ARE_YOU_SURE');
				}
			}, {capture: true});
		}

		refresh() {
			initThemes();
			LanguageStore.language(SettingsGet('language'));
			this.start();
		}

		start() {
			if (SettingsGet('Auth')) {
				rl.setTitle(i18n('GLOBAL/LOADING'));

				SMAudio.notifications(!!SettingsGet('SoundNotification'));
				NotificationUserStore.enabled(!!SettingsGet('DesktopNotifications'));

				AccountUserStore.email(SettingsGet('Email'));

				SettingsUserStore.init();
				ContactUserStore.init();

				loadFolders((success, error) => {
					try {
						if (success) {
							startScreens([
								MailBoxUserScreen,
								SettingsUserScreen
							]);

							setRefreshFoldersInterval(SettingsGet('CheckMailInterval'));

							loadAccountsAndIdentities();

							setTimeout(() => {
								const cF = FolderUserStore.currentFolderFullName();
								getFolderInboxName() === cF || folderInformation(cF);
								FolderUserStore.hasCapability('LIST-STATUS') || folderInformationMultiply(true);
							}, 1000);

							setTimeout(() => Remote.request('AppDelayStart'), 35000);

							// add pointermove ?
							addEventsListener(doc, ['touchstart','mousemove','keydown'], SettingsUserStore.delayLogout, {passive:true});
							SettingsUserStore.delayLogout();

							// initLeftSideLayoutResizer
							setTimeout(() => {
								const left = elementById('rl-left'),
									fToggle = () =>
										setLayoutResizer(left, ClientSideKeyNameFolderListSize,
											(ThemeStore.isMobile() || leftPanelDisabled()) ? 0 : 'Width');
								if (left) {
									fToggle();
									leftPanelDisabled.subscribe(fToggle);
								}
							}, 1);

							setInterval(reloadTime, 60000);

							PgpUserStore.init();
							SMimeUserStore.loadCertificates();

							setTimeout(() => mailToHelper(SettingsGet('mailToEmail')), 500);
						} else {
							this.logout();
							alert('Folders error: ' + getErrorMessage(0, error));
						}
					} catch (e) {
						console.error(e);
					}
				});
			} else {
				startScreens([LoginUserScreen]);
			}
		}

		showMessageComposer(params = [])
		{
			showScreenPopup(ComposePopupView, params);
		}
	}

	AskPopupView.password = function(sAskDesc, btnText, ask) {
		return new Promise(resolve => {
			this.showModal([
				sAskDesc,
				view => resolve({
					password:view.passphrase(),
					username:/*ask & 2 ? */view.username(),
					remember:/*ask & 4 ? */view.remember()
				}),
				() => resolve(null),
				true,
				ask || 1,
				btnText
			]);
		});
	};

	AskPopupView.cryptkey = () => new Promise(resolve => {
		const fn = () => AskPopupView.showModal([
			i18n('CRYPTO/ASK_CRYPTKEY_PASS'),
			view => {
				let pass = view.passphrase();
				if (pass) {
					Remote.post('ResealCryptKey', null, {
						passphrase: pass
					}).then(response => {
						resolve(response?.Result);
					}).catch(e => {
						if (111 === e.code) {
							fn();
						} else {
							console.error(e);
							resolve(null);
						}
					});
				} else {
					resolve(null);
				}
			},
			() => resolve(null),
			true,
			1,
			i18n('CRYPTO/DECRYPT')
		]);
		fn();
	});

	bootstrap(new AppUser);

})();
