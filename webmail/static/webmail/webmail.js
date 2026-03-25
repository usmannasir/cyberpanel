/* CyberPanel Webmail - AngularJS Controller */

app.filter('fileSize', function() {
    return function(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        var k = 1024;
        var sizes = ['B', 'KB', 'MB', 'GB'];
        var i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };
});

app.filter('wmDate', function() {
    return function(dateStr) {
        if (!dateStr) return '';
        try {
            var d = new Date(dateStr);
            var now = new Date();
            if (d.toDateString() === now.toDateString()) {
                return d.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
            }
            if (d.getFullYear() === now.getFullYear()) {
                return d.toLocaleDateString([], {month: 'short', day: 'numeric'});
            }
            return d.toLocaleDateString([], {year: 'numeric', month: 'short', day: 'numeric'});
        } catch(e) {
            return dateStr;
        }
    };
});

app.filter('trustHtml', ['$sce', function($sce) {
    return function(html) {
        return $sce.trustAsHtml(html);
    };
}]);

app.directive('wmAutocomplete', ['$http', function($http) {
    return {
        restrict: 'A',
        link: function(scope, element, attrs) {
            var dropdown = null;
            var debounce = null;

            element.on('input', function() {
                var val = element.val();
                var lastComma = val.lastIndexOf(',');
                var query = lastComma >= 0 ? val.substring(lastComma + 1).trim() : val.trim();

                if (query.length < 2) {
                    hideDropdown();
                    return;
                }

                clearTimeout(debounce);
                debounce = setTimeout(function() {
                    $http.post('/webmail/api/searchContacts', {query: query}, {
                        headers: {'X-CSRFToken': getCookie('csrftoken')}
                    }).then(function(resp) {
                        if (resp.data.status === 1 && resp.data.contacts.length > 0) {
                            showDropdown(resp.data.contacts, val, lastComma);
                        } else {
                            hideDropdown();
                        }
                    });
                }, 300);
            });

            function showDropdown(contacts, currentVal, lastComma) {
                hideDropdown();
                dropdown = document.createElement('div');
                dropdown.className = 'wm-autocomplete-dropdown';
                contacts.forEach(function(c) {
                    var item = document.createElement('div');
                    item.className = 'wm-autocomplete-item';
                    item.textContent = c.display_name ? c.display_name + ' <' + c.email_address + '>' : c.email_address;
                    item.addEventListener('click', function() {
                        var prefix = lastComma >= 0 ? currentVal.substring(0, lastComma + 1) + ' ' : '';
                        var newVal = prefix + c.email_address + ', ';
                        element.val(newVal);
                        element.triggerHandler('input');
                        scope.$apply(function() {
                            scope.$eval(attrs.ngModel + ' = "' + newVal.replace(/"/g, '\\"') + '"');
                        });
                        hideDropdown();
                    });
                    dropdown.appendChild(item);
                });
                element[0].parentNode.style.position = 'relative';
                element[0].parentNode.appendChild(dropdown);
            }

            function hideDropdown() {
                if (dropdown && dropdown.parentNode) {
                    dropdown.parentNode.removeChild(dropdown);
                }
                dropdown = null;
            }

            element.on('blur', function() {
                setTimeout(hideDropdown, 200);
            });
        }
    };
}]);

var WM_MIME_MAIL_ITEMS = 'application/x-cyberpanel-webmail-messages';

function _dataTransferOf(ev) {
    if (!ev) return null;
    return ev.dataTransfer || (ev.originalEvent && ev.originalEvent.dataTransfer) || null;
}

function _dataTransferHasWebmailMessages(dt) {
    if (!dt || !dt.types) return false;
    var t = WM_MIME_MAIL_ITEMS;
    if (typeof dt.types.includes === 'function') return dt.types.includes(t);
    for (var i = 0; i < dt.types.length; i++) {
        if (dt.types[i] === t) return true;
    }
    return false;
}

/**
 * Drag one or more messages (selected rows, or the row under the cursor) to move them.
 */
app.directive('wmMessageDrag', ['$timeout', function($timeout) {
    return {
        restrict: 'A',
        link: function(scope, element) {
            element.prop('draggable', true);
            element.attr('title', element.attr('title') || '');

            function safeDigest(fn) {
                var phase = scope.$root.$$phase;
                if (phase === '$apply' || phase === '$digest') {
                    $timeout(fn, 0);
                } else {
                    scope.$apply(fn);
                }
            }

            element.on('dragstart', function(ev) {
                var msg = scope.msg;
                if (!msg || !scope.getDragMessageItemsForMove) return;
                var items = scope.getDragMessageItemsForMove(msg);
                if (!items.length) {
                    ev.preventDefault();
                    return;
                }
                var dt = _dataTransferOf(ev);
                if (dt) {
                    try {
                        dt.effectAllowed = 'move';
                        dt.setData(WM_MIME_MAIL_ITEMS, JSON.stringify({ items: items }));
                        dt.setData('text/plain', 'webmail-messages');
                    } catch (e) { /* ignore */ }
                }
                safeDigest(function() {
                    if (scope.onMailItemsDragStart) scope.onMailItemsDragStart();
                });
            });

            element.on('dragend', function() {
                safeDigest(function() {
                    if (scope.onMailItemsDragEnd) scope.onMailItemsDragEnd();
                });
            });

            scope.$on('$destroy', function() {
                element.off('dragstart dragend');
            });
        }
    };
}]);

/**
 * Native HTML5 drag/drop for folder rows with proper digest + dataTransfer (Safari/Firefox).
 */
app.directive('wmFolderDnd', ['$timeout', function($timeout) {
    return {
        restrict: 'A',
        link: function(scope, element, attrs) {
            function folderName() {
                try {
                    return scope.$eval(attrs.wmFolderDnd);
                } catch (e) {
                    return null;
                }
            }

            function dragEnabled() {
                var fs = scope.wmSettings && scope.wmSettings.folderSettings;
                if (!fs || fs.enableDragDrop === undefined || fs.enableDragDrop === null) {
                    return true;
                }
                return !!fs.enableDragDrop;
            }

            function safeDigest(fn) {
                var phase = scope.$root.$$phase;
                if (phase === '$apply' || phase === '$digest') {
                    $timeout(fn, 0);
                } else {
                    scope.$apply(fn);
                }
            }

            function dataTransferOf(ev) {
                return _dataTransferOf(ev);
            }

            scope.$watch(function() {
                return [folderName(), dragEnabled()];
            }, function() {
                element.prop('draggable', dragEnabled() ? 'true' : 'false');
            }, true);

            element.on('dragstart', function(ev) {
                if (!dragEnabled()) {
                    ev.preventDefault();
                    return;
                }
                var name = folderName();
                if (!name) return;
                var dt = dataTransferOf(ev);
                if (dt) {
                    try {
                        dt.effectAllowed = 'move';
                        dt.setData('text/plain', name);
                    } catch (e) {}
                }
                safeDigest(function() {
                    scope.onFolderDragStart(name);
                });
            });

            element.on('dragover', function(ev) {
                var dt = dataTransferOf(ev);
                if (_dataTransferHasWebmailMessages(dt)) {
                    ev.preventDefault();
                    if (dt) {
                        try {
                            dt.dropEffect = 'move';
                        } catch (e2) {}
                    }
                    var name = folderName();
                    safeDigest(function() {
                        if (scope.onMessageDragOverFolder) scope.onMessageDragOverFolder(name);
                    });
                    return;
                }
                if (!dragEnabled()) return;
                ev.preventDefault();
                if (dt) {
                    try {
                        dt.dropEffect = 'move';
                    } catch (e3) {}
                }
                var name2 = folderName();
                safeDigest(function() {
                    scope.onFolderDragOver(ev, name2);
                });
            });

            element.on('drop', function(ev) {
                ev.preventDefault();
                var dt = dataTransferOf(ev);
                var raw = '';
                if (dt) {
                    try {
                        raw = dt.getData(WM_MIME_MAIL_ITEMS) || '';
                    } catch (e) {
                        raw = '';
                    }
                }
                if (raw) {
                    var parsed = null;
                    try {
                        parsed = JSON.parse(raw);
                    } catch (e2) {
                        parsed = null;
                    }
                    if (parsed && parsed.items && parsed.items.length) {
                        var dropName = folderName();
                        safeDigest(function() {
                            if (scope.onMessagesDropOnFolder) {
                                scope.onMessagesDropOnFolder(parsed.items, dropName);
                            }
                        });
                        return;
                    }
                }
                if (!dragEnabled()) return;
                var name3 = folderName();
                safeDigest(function() {
                    scope.onFolderDrop(ev, name3);
                });
            });

            element.on('dragend', function() {
                safeDigest(function() {
                    scope.onFolderDragEnd();
                });
            });

            scope.$on('$destroy', function() {
                element.off('dragstart dragover drop dragend');
            });
        }
    };
}]);

app.directive('wmSidebarResizerTouch', function() {
    return {
        restrict: 'A',
        link: function(scope, element) {
            element.on('touchstart', function(ev) {
                try {
                    ev.preventDefault();
                } catch (e) { /* ignore */ }
                scope.startSidebarResize(ev);
            });
            scope.$on('$destroy', function() {
                element.off('touchstart');
            });
        }
    };
});

app.controller('webmailCtrl', ['$scope', '$http', '$sce', '$timeout', '$document', '$window', function($scope, $http, $sce, $timeout, $document, $window) {

    // System folders: must stay in sync with webmailManager.apiDeleteFolder protected set
    var WM_SIDEBAR_WIDTH_KEY = 'wm_sidebar_width_px';
    var WM_SIDEBAR_MIN = 180;
    var WM_SIDEBAR_MAX = 560;
    var WM_SIDEBAR_DEFAULT = 220;
    var sidebarResizeActive = false;

    var WM_FOLDER_PROTECTED = {
        'INBOX': true,
        'INBOX.Sent': true, 'INBOX.Drafts': true, 'INBOX.Deleted Items': true,
        'INBOX.Junk E-mail': true, 'INBOX.Archive': true, 'INBOX.spam': true, 'INBOX.Trash': true,
        'Sent': true, 'Drafts': true, 'Trash': true, 'Spam': true, 'Junk': true, 'Archive': true,
        'Deleted Items': true, 'Junk E-mail': true
    };

    // ── State ────────────────────────────────────────────────
    $scope.currentEmail = '';
    $scope.managedAccounts = [];
    $scope.folders = [];
    $scope.displayFolders = [];
    /** Nested sidebar rows: { folder, depth, hasChildren } */
    $scope.displayFolderRows = [];
    /** folder name -> false when collapsed (expanded when unset/true) */
    $scope.folderExpanded = {};
    $scope.currentFolder = 'INBOX';
    $scope.messages = [];
    $scope.currentPage = 1;
    $scope.totalPages = 1;
    $scope.totalMessages = 0;
    $scope.perPage = 25;
    $scope.openMsg = null;
    $scope.trustedBody = '';
    $scope.viewMode = 'list';  // list, read, compose, contacts, rules, settings
    $scope.loading = false;
    $scope.sending = false;
    $scope.searchQuery = '';
    /** '__all__' or concrete IMAP folder name */
    $scope.messageSearchScope = '__all__';
    $scope.messageListSearchActive = false;
    $scope.selectAll = false;
    $scope.sidebarWidthPx = WM_SIDEBAR_DEFAULT;
    $scope.sidebarResizeEnabled = true;

    function refreshSidebarResizeEnabled() {
        try {
            $scope.sidebarResizeEnabled = $window.matchMedia('(min-width: 769px)').matches;
        } catch (e) {
            $scope.sidebarResizeEnabled = true;
        }
    }
    refreshSidebarResizeEnabled();

    try {
        var storedW = parseInt(localStorage.getItem(WM_SIDEBAR_WIDTH_KEY), 10);
        if (!isNaN(storedW) && storedW >= WM_SIDEBAR_MIN && storedW <= WM_SIDEBAR_MAX) {
            $scope.sidebarWidthPx = storedW;
        }
    } catch (e) { /* ignore */ }

    angular.element($window).on('resize', function() {
        $scope.$applyAsync(refreshSidebarResizeEnabled);
    });

    $scope.startSidebarResize = function(event) {
        if (!$scope.sidebarResizeEnabled) return;
        if (sidebarResizeActive) return;
        if (event.type === 'mousedown' && event.button !== 0) return;
        event.preventDefault();
        sidebarResizeActive = true;
        var startX = event.clientX != null ? event.clientX : (event.originalEvent && event.originalEvent.touches && event.originalEvent.touches[0] ? event.originalEvent.touches[0].clientX : (event.touches && event.touches[0] ? event.touches[0].clientX : 0));
        var startW = $scope.sidebarWidthPx;

        function clampW(n) {
            return Math.max(WM_SIDEBAR_MIN, Math.min(WM_SIDEBAR_MAX, n));
        }

        function onMove(e) {
            if (!$scope.sidebarResizeEnabled) return;
            var oe = e.originalEvent || e;
            var x = oe.clientX != null ? oe.clientX : (oe.touches && oe.touches[0] ? oe.touches[0].clientX : (e.clientX != null ? e.clientX : startX));
            var dx = x - startX;
            $scope.sidebarWidthPx = clampW(Math.round(startW + dx));
            $scope.$digest();
        }

        function onUp() {
            sidebarResizeActive = false;
            $document.off('mousemove touchmove', onMove);
            $document.off('mouseup touchend touchcancel', onUp);
            try {
                localStorage.setItem(WM_SIDEBAR_WIDTH_KEY, String($scope.sidebarWidthPx));
            } catch (err) { /* ignore */ }
            angular.element($window.document.body).removeClass('wm-resizing-sidebar');
        }

        angular.element($window.document.body).addClass('wm-resizing-sidebar');
        $document.on('mousemove touchmove', onMove);
        $document.on('mouseup touchend touchcancel', onUp);
    };
    $scope.showMoveDropdown = false;
    $scope.moveTarget = '';
    $scope.showBcc = false;
    $scope.showNewFolderDialog = false;
    $scope.newFolderNameInput = '';
    $scope.showDeleteFolderDialog = false;
    $scope.folderPendingDelete = null;

    // Compose
    $scope.compose = {to: '', cc: '', bcc: '', subject: '', body: '', files: [], inReplyTo: '', references: ''};

    // Contacts
    $scope.contacts = [];
    $scope.filteredContacts = [];
    $scope.contactSearch = '';
    $scope.editingContact = null;

    // Rules
    $scope.sieveRules = [];
    $scope.editingRule = null;

    // Settings
    $scope.wmSettings = {
        folderSettings: {
            specialDisplayMode: 'top',
            folderMappings: {
                inbox: 'INBOX',
                sent: 'INBOX.Sent',
                spam: 'INBOX.Junk E-mail',
                deleted_items: 'INBOX.Deleted Items',
                junk_e_mail: 'INBOX.Junk E-mail',
                drafts: 'INBOX.Drafts',
                trash: 'INBOX.Deleted Items',
                archive: 'INBOX.Archive'
            },
            folderOrder: [],
            specialOrder: ['inbox', 'sent', 'drafts', 'spam', 'trash', 'archive'],
            enableDragDrop: true
        }
    };
    $scope.draggingFolder = null;
    $scope.dragOverFolder = null;
    $scope.draggingMailItems = false;
    $scope.folderLayoutDirty = false;

    // Draft auto-save
    var draftTimer = null;

    // ── Helper ───────────────────────────────────────────────
    function apiCall(url, data, callback, errback) {
        var config = {headers: {'X-CSRFToken': getCookie('csrftoken')}};
        var payload = data || {};
        // Always send current account so backend uses the right email
        if ($scope.currentEmail && !payload.fromAccount) {
            payload.fromAccount = $scope.currentEmail;
        }
        $http.post(url, payload, config).then(function(resp) {
            if (callback) callback(resp.data);
        }, function(err) {
            console.error('API error:', url, err);
            if (errback) errback(err);
        });
    }

    function notify(msg, type) {
        new PNotify({title: type === 'error' ? 'Error' : 'Webmail', text: msg, type: type || 'success'});
    }

    function splitRecipients(s) {
        if (!s || typeof s !== 'string') return [];
        return s.split(/[,;]+/).map(function(t) { return (t || '').trim(); }).filter(Boolean);
    }

    function isPlausibleEmail(addr) {
        if (!addr || addr.indexOf('@') < 0) return false;
        var p = addr.split('@');
        if (p.length !== 2 || !p[0] || !p[1] || p[1].indexOf('.') < 0) return false;
        if (addr.length > 254) return false;
        return true;
    }

    function countValidRecipients(to, cc, bcc) {
        var all = splitRecipients(to).concat(splitRecipients(cc || '')).concat(splitRecipients(bcc || ''));
        var n = 0;
        for (var i = 0; i < all.length; i++) {
            if (isPlausibleEmail(all[i])) n++;
        }
        return n;
    }

    // ── Init ─────────────────────────────────────────────────
    $scope.init = function() {
        // Try SSO first
        apiCall('/webmail/api/sso', {}, function(data) {
            if (data.status === 1) {
                $scope.currentEmail = data.email;
                $scope.managedAccounts = data.accounts || [];
                // Load folder role mappings before listing folders so "At top" uses saved specialOrder.
                $scope.loadSettings(function() {
                    $scope.loadFolders();
                });
            } else {
                notify(data.error_message || 'No email accounts found. Create an email account first or use the standalone login.', 'error');
            }
        });
    };

    // ── Account Switching ────────────────────────────────────
    $scope.switchAccount = function() {
        var newEmail = $scope.currentEmail;
        if (!newEmail) return;

        // Reset view state immediately
        $scope.currentFolder = 'INBOX';
        $scope.currentPage = 1;
        $scope.openMsg = null;
        $scope.viewMode = 'list';
        $scope.messages = [];
        $scope.contacts = [];
        $scope.filteredContacts = [];
        $scope.sieveRules = [];

        apiCall('/webmail/api/switchAccount', {email: newEmail}, function(data) {
            if (data.status === 1) {
                $scope.loadSettings(function() {
                    $scope.loadFolders();
                });
            } else {
                notify(data.error_message || 'Failed to switch account', 'error');
                console.error('switchAccount failed:', data);
            }
        }, function(err) {
            notify('Failed to switch account: ' + (err.status || 'unknown error'), 'error');
            console.error('switchAccount HTTP error:', err);
        });
    };

    // ── Folders ──────────────────────────────────────────────
    $scope.loadFolders = function() {
        apiCall('/webmail/api/listFolders', {}, function(data) {
            if (data.status === 1) {
                $scope.folders = data.folders || [];
                $scope.applyFolderLayout();
                // Pick a sane default folder.
                // Some Dovecot setups may not expose a real "INBOX" mailbox (messages live under "INBOX.*").
                // The UI previously hardcoded currentFolder='INBOX', which caused "No messages" even when mail exists.
                var chooseDefaultFolder = function(folders) {
                    if (!folders || folders.length === 0) return 'INBOX';

                    // 1) Prefer exact INBOX if it has messages; otherwise some servers store mail only under INBOX.*.
                    var inbox = null;
                    for (var i = 0; i < folders.length; i++) {
                        if (folders[i] && folders[i].name === 'INBOX') {
                            inbox = folders[i];
                            break;
                        }
                    }
                    if (inbox) {
                        var inboxUnread = parseInt((inbox.unread_count) ? inbox.unread_count : 0, 10);
                        var inboxTotal = parseInt((inbox.total_count) ? inbox.total_count : 0, 10);
                        if (inboxUnread > 0 || inboxTotal > 0) {
                            return inbox.name;
                        }
                    }

                    // 2) Prefer the folder with most unread messages.
                    var best = null;
                    var bestUnread = -1;
                    for (var j = 0; j < folders.length; j++) {
                        var u = parseInt((folders[j] && folders[j].unread_count) ? folders[j].unread_count : 0, 10);
                        if (u > bestUnread) {
                            bestUnread = u;
                            best = folders[j];
                        }
                    }
                    if (best && bestUnread > 0) {
                        return best.name;
                    }

                    // 3) Otherwise, pick the folder with most total messages.
                    best = null;
                    var bestTotal = -1;
                    for (var k = 0; k < folders.length; k++) {
                        var t = parseInt((folders[k] && folders[k].total_count) ? folders[k].total_count : 0, 10);
                        if (t > bestTotal) {
                            bestTotal = t;
                            best = folders[k];
                        }
                    }

                    return (best && best.name) ? best.name : (folders[0].name || 'INBOX');
                };

                var mappings = (($scope.wmSettings || {}).folderSettings || {}).folderMappings || {};
                var mappedInbox = mappings.inbox || 'INBOX';
                var inboxFolder = null;
                for (var i = 0; i < $scope.folders.length; i++) {
                    if ($scope.folders[i] && $scope.folders[i].name === mappedInbox) {
                        inboxFolder = $scope.folders[i];
                        break;
                    }
                }
                if (inboxFolder && ((inboxFolder.unread_count || 0) > 0 || (inboxFolder.total_count || 0) > 0)) {
                    $scope.currentFolder = mappedInbox;
                } else {
                    $scope.currentFolder = chooseDefaultFolder($scope.folders);
                }

                // If folder ordering/mapping hides the selected folder from the UI list,
                // ensure we still display something sensible.
                if ($scope.displayFolders && $scope.displayFolders.length > 0) {
                    var ok = false;
                    for (var df = 0; df < $scope.displayFolders.length; df++) {
                        if ($scope.displayFolders[df] && $scope.displayFolders[df].name === $scope.currentFolder) {
                            ok = true;
                            break;
                        }
                    }
                    if (!ok) {
                        $scope.currentFolder = $scope.displayFolders[0].name;
                    }
                }
                $scope.currentPage = 1;
                $scope.loadMessages();
            } else {
                notify(data.error_message || 'Failed to load folders.', 'error');
            }
        });
    };

    // ── Folder Layout (mapping + ordering + drag/drop) ─────────
    function _getFolderMappings() {
        return (($scope.wmSettings || {}).folderSettings || {}).folderMappings || {};
    }

    function _getSpecialDisplayMode() {
        var mode = (($scope.wmSettings || {}).folderSettings || {}).specialDisplayMode;
        return (mode === 'interleaved') ? 'interleaved' : 'top';
    }

    function _getEnableDragDrop() {
        var enabled = (($scope.wmSettings || {}).folderSettings || {}).enableDragDrop;
        return enabled === undefined ? true : !!enabled;
    }

    /**
     * Default IMAP names when a semantic key has no mapping (SnappyMail-style order).
     * Order follows typical clients: Inbox, Sent, Drafts, Junk/Spam, Trash, Archive.
     */
    var WM_SPECIAL_KEY_DEFAULT_FOLDERS = {
        inbox: 'INBOX',
        sent: 'INBOX.Sent',
        drafts: 'INBOX.Drafts',
        spam: 'INBOX.Junk E-mail',
        deleted_items: 'INBOX.Deleted Items',
        junk_e_mail: 'INBOX.Junk E-mail',
        trash: 'INBOX.Deleted Items',
        archive: 'INBOX.Archive'
    };

    /**
     * Per-settings-key candidate IMAP names (first existing wins). Handles Spam vs Junk E-mail,
     * Trash vs Deleted Items, and non–CyberPanel defaults.
     */
    var WM_SPECIAL_ROLE_CANDIDATES = {
        inbox: ['INBOX'],
        sent: ['INBOX.Sent', 'Sent', 'INBOX.Sent Items', 'Sent Items'],
        drafts: ['INBOX.Drafts', 'Drafts'],
        spam: [
            'INBOX.Junk E-mail', 'Junk E-mail', 'INBOX.junk', 'INBOX.spam', 'INBOX.Spam',
            'Spam', 'Junk', 'junk', 'INBOX.Junk', 'Junk Mail'
        ],
        deleted_items: ['INBOX.Deleted Items', 'Deleted Items', 'INBOX.Trash', 'Trash', 'Bin', 'Deleted'],
        junk_e_mail: [
            'INBOX.Junk E-mail', 'Junk E-mail', 'INBOX.junk', 'INBOX.spam', 'INBOX.Spam',
            'Spam', 'Junk', 'junk', 'INBOX.Junk', 'Junk Mail'
        ],
        trash: ['INBOX.Deleted Items', 'Deleted Items', 'INBOX.Trash', 'Trash', 'Bin', 'Deleted'],
        archive: ['INBOX.Archive', 'Archive', 'Archive-Mail']
    };

    /** Resolve IMAP folder key regardless of INBOX.Spam vs INBOX.spam vs stored mapping case. */
    function _folderNameMatch(folderByName, want) {
        if (!want || !folderByName) return null;
        if (folderByName[want]) return want;
        var wl = String(want).toLowerCase();
        for (var k in folderByName) {
            if (!Object.prototype.hasOwnProperty.call(folderByName, k)) continue;
            if (String(k).toLowerCase() === wl) return k;
        }
        return null;
    }

    function _pickFolderForRole(key, mappings, folderByName) {
        var mapped = mappings[key];
        if (mapped) {
            var mhit = _folderNameMatch(folderByName, mapped);
            if (mhit) return mhit;
        }
        var cands = WM_SPECIAL_ROLE_CANDIDATES[key];
        if (cands) {
            for (var ci = 0; ci < cands.length; ci++) {
                var chit = _folderNameMatch(folderByName, cands[ci]);
                if (chit) return chit;
            }
        }
        var fb = WM_SPECIAL_KEY_DEFAULT_FOLDERS[key];
        if (fb) {
            var fhit = _folderNameMatch(folderByName, fb);
            if (fhit) return fhit;
        }
        return null;
    }

    function _folderTypeOf(name, folderByName) {
        var f = folderByName[name];
        return (f && f.folder_type) ? f.folder_type : 'folder';
    }

    function _specialCoversType(specialSet, folderByName, ftype) {
        if (!ftype || ftype === 'folder') {
            return false;
        }
        for (var sn in specialSet) {
            if (!Object.prototype.hasOwnProperty.call(specialSet, sn)) {
                continue;
            }
            if (_folderTypeOf(sn, folderByName) === ftype) {
                return true;
            }
        }
        return false;
    }

    function _getSpecialOrderKeys() {
        var keys = (($scope.wmSettings || {}).folderSettings || {}).specialOrder;
        if (!keys || !Array.isArray(keys) || keys.length === 0) {
            return ['inbox', 'sent', 'drafts', 'spam', 'trash', 'archive'];
        }
        return keys;
    }

    function _getFolderByName() {
        var map = {};
        for (var i = 0; i < ($scope.folders || []).length; i++) {
            var f = $scope.folders[i];
            if (f && f.name) map[f.name] = f;
        }
        return map;
    }

    function _folderDelimiterFromList() {
        var list = $scope.folders || [];
        for (var i = 0; i < list.length; i++) {
            var d = list[i] && list[i].delimiter;
            if (d != null && d !== '') {
                var s = String(d).replace(/^"|"$/g, '');
                return s || '.';
            }
        }
        return '.';
    }

    /** Parent for nested display: INBOX.X is root; INBOX.X.Y parents to INBOX.X if it exists. */
    function _getEffectiveFolderParent(name, folderByName) {
        if (!name || name === 'INBOX') return null;
        var sep = _folderDelimiterFromList();
        var parts = name.split(sep);
        if (parts.length <= 2) return null;
        var parentPath = parts.slice(0, -1).join(sep);
        while (parentPath && parentPath !== 'INBOX' && !folderByName[parentPath]) {
            var pp = parentPath.split(sep);
            if (pp.length <= 2) {
                parentPath = null;
                break;
            }
            parentPath = pp.slice(0, -1).join(sep);
        }
        if (!parentPath || parentPath === 'INBOX' || !folderByName[parentPath]) return null;
        return parentPath;
    }

    function _buildDisplayFolderRows(orderedFolders, folderByName) {
        var names = orderedFolders.map(function(f) { return f.name; });
        var parentOf = {};
        var childMap = {};
        for (var i = 0; i < names.length; i++) {
            childMap[names[i]] = [];
        }
        for (var j = 0; j < names.length; j++) {
            var nm = names[j];
            var p = _getEffectiveFolderParent(nm, folderByName);
            parentOf[nm] = p;
            if (p && childMap[p] !== undefined) {
                childMap[p].push(nm);
            }
        }
        var indexByName = {};
        for (var ix = 0; ix < names.length; ix++) {
            indexByName[names[ix]] = ix;
        }
        var key;
        for (key in childMap) {
            if (Object.prototype.hasOwnProperty.call(childMap, key)) {
                childMap[key].sort(function(a, b) {
                    var ia = indexByName[a] !== undefined ? indexByName[a] : 999999;
                    var ib = indexByName[b] !== undefined ? indexByName[b] : 999999;
                    return ia - ib;
                });
            }
        }
        var rows = [];
        function pushVisible(fname, depth) {
            var f = folderByName[fname];
            if (!f) return;
            var kids = childMap[fname] || [];
            var hasKids = kids.length > 0;
            rows.push({ folder: f, depth: depth, hasChildren: hasKids });
            var expanded = $scope.folderExpanded[fname] !== false;
            if (hasKids && expanded) {
                for (var c = 0; c < kids.length; c++) {
                    pushVisible(kids[c], depth + 1);
                }
            }
        }
        for (var r = 0; r < names.length; r++) {
            if (parentOf[names[r]] == null) {
                pushVisible(names[r], 0);
            }
        }
        return rows;
    }

    function _normalizeFolderOrder(folderByName) {
        var baseNames = Object.keys(folderByName);
        var baseOrder = ($scope.folders || []).map(function(f) { return f.name; });
        // Normalize order to contain only known folders and keep backend order as a fallback.
        var stored = (((($scope.wmSettings || {}).folderSettings || {}).folderOrder) || []).slice();
        var existing = {};
        for (var i = 0; i < baseOrder.length; i++) existing[baseOrder[i]] = true;

        var result = [];
        var seen = {};
        for (var j = 0; j < stored.length; j++) {
            var n = stored[j];
            if (existing[n] && !seen[n]) {
                seen[n] = true;
                result.push(n);
            }
        }
        // Append any missing folders in backend order.
        for (var k = 0; k < baseOrder.length; k++) {
            var bn = baseOrder[k];
            if (existing[bn] && !seen[bn]) {
                seen[bn] = true;
                result.push(bn);
            }
        }
        return result;
    }

    /**
     * Build the "special" sidebar block in strict specialOrder key order.
     * Do not re-sort by IMAP listing order (that pushed Trash/Junk out of the SnappyMail-style top block).
     */
    function _getSpecialFolderNames(folderByName, normalizedOrder) {
        var mappings = _getFolderMappings();
        var specialKeys = _getSpecialOrderKeys();
        var specialNamesInKeyOrder = [];
        var seen = {};
        var junkSlotFilled = false;
        var trashSlotFilled = false;
        for (var i = 0; i < specialKeys.length; i++) {
            var key = specialKeys[i];
            if ((key === 'junk_e_mail' || key === 'spam') && junkSlotFilled) {
                continue;
            }
            if ((key === 'trash' || key === 'deleted_items') && trashSlotFilled) {
                continue;
            }
            var picked = _pickFolderForRole(key, mappings, folderByName);
            if (!picked || seen[picked]) {
                continue;
            }
            seen[picked] = true;
            specialNamesInKeyOrder.push(picked);
            var ftPick = _folderTypeOf(picked, folderByName);
            if (key === 'junk_e_mail' || key === 'spam' || ftPick === 'junk') {
                junkSlotFilled = true;
            }
            if (key === 'trash' || key === 'deleted_items' || ftPick === 'trash') {
                trashSlotFilled = true;
            }
        }
        return specialNamesInKeyOrder;
    }

    $scope.ensureFolderAncestorsExpanded = function(folderName) {
        if (!folderName) return;
        var folderByName = _getFolderByName();
        var p = _getEffectiveFolderParent(folderName, folderByName);
        while (p) {
            $scope.folderExpanded[p] = true;
            p = _getEffectiveFolderParent(p, folderByName);
        }
    };

    $scope.toggleFolderExpand = function(folderName, evt) {
        if (evt) {
            evt.preventDefault();
            evt.stopPropagation();
        }
        if (!folderName) return;
        if ($scope.folderExpanded[folderName] === false) {
            delete $scope.folderExpanded[folderName];
        } else {
            $scope.folderExpanded[folderName] = false;
        }
        var folderByName = _getFolderByName();
        $scope.displayFolderRows = _buildDisplayFolderRows($scope.displayFolders, folderByName);
    };

    $scope.isFolderRowExpanded = function(folderName) {
        return $scope.folderExpanded[folderName] !== false;
    };

    $scope.getFolderRowLabel = function(folder, depth) {
        if (!folder) return '';
        var dn = folder.display_name || folder.name || '';
        if (depth <= 0) {
            var maps = _getFolderMappings();
            var nm = folder.name || '';
            if (maps.inbox && nm === maps.inbox) return 'Inbox';
            if (maps.sent && nm === maps.sent) return 'Sent';
            if (maps.drafts && nm === maps.drafts) return 'Drafts';
            if ((maps.spam && nm === maps.spam) || (maps.junk_e_mail && nm === maps.junk_e_mail)) return 'Spam';
            if ((maps.trash && nm === maps.trash) || (maps.deleted_items && nm === maps.deleted_items)) return 'Trash';
            if (maps.archive && nm === maps.archive) return 'Archive';
            return dn;
        }
        var sep = _folderDelimiterFromList();
        var idx = dn.lastIndexOf(sep);
        if (idx >= 0) return dn.slice(idx + sep.length);
        return dn;
    };

    $scope.applyFolderLayout = function() {
        if (!$scope.folders || $scope.folders.length === 0) {
            $scope.displayFolders = [];
            $scope.displayFolderRows = [];
            return;
        }

        var folderByName = _getFolderByName();
        var normalizedOrder = _normalizeFolderOrder(folderByName);
        var mode = _getSpecialDisplayMode();

        var specialNames = _getSpecialFolderNames(folderByName, normalizedOrder);
        var specialSet = {};
        for (var i = 0; i < specialNames.length; i++) specialSet[specialNames[i]] = true;

        var displayNames = [];
        if (mode === 'top') {
            // Special section at top, others follow in normalized order.
            displayNames = specialNames.slice();
            for (var j = 0; j < normalizedOrder.length; j++) {
                var n = normalizedOrder[j];
                if (specialSet[n]) {
                    continue;
                }
                var ft = _folderTypeOf(n, folderByName);
                if (_specialCoversType(specialSet, folderByName, ft)) {
                    continue;
                }
                displayNames.push(n);
            }
        } else {
            // Fully interleaved order.
            displayNames = normalizedOrder.slice();
        }

        $scope.displayFolders = displayNames.map(function(n) { return folderByName[n]; }).filter(function(x) { return !!x; });

        // Ensure currentFolder is valid.
        var found = false;
        for (var k = 0; k < displayNames.length; k++) {
            if (displayNames[k] === $scope.currentFolder) {
                found = true;
                break;
            }
        }
        if (!found) {
            var mappings = _getFolderMappings();
            var mappedInbox = mappings.inbox || 'INBOX';
            if (folderByName[mappedInbox]) {
                $scope.currentFolder = mappedInbox;
            } else if (displayNames.length > 0) {
                $scope.currentFolder = displayNames[0];
            }
        }
        $scope.ensureFolderAncestorsExpanded($scope.currentFolder);
        $scope.displayFolderRows = _buildDisplayFolderRows($scope.displayFolders, folderByName);
    };

    // React to settings changes without requiring a full reload.
    $scope.$watch('wmSettings.folderSettings.folderMappings', function() {
        if ($scope.folders && $scope.folders.length > 0) {
            $scope.applyFolderLayout();
            var mappings = _getFolderMappings();
            if (mappings && mappings.inbox && ($scope.folders || []).some(function(f) { return f && f.name === mappings.inbox; })) {
                $scope.currentFolder = mappings.inbox;
                if ($scope.viewMode === 'list' || $scope.viewMode === 'read') {
                    $scope.loadMessages();
                }
            }
        }
    }, true);
    $scope.$watch('wmSettings.folderSettings.specialDisplayMode', function() {
        if ($scope.folders && $scope.folders.length > 0) {
            $scope.applyFolderLayout();
        }
    });

    function _updateFolderOrderAfterDrag(draggedName, targetName) {
        if (!draggedName || !targetName || draggedName === targetName) return false;
        var folderByName = _getFolderByName();
        if (!folderByName[draggedName] || !folderByName[targetName]) return false;

        var normalizedOrder = _normalizeFolderOrder(folderByName);
        var mode = _getSpecialDisplayMode();

        // Determine special membership.
        var specialNames = _getSpecialFolderNames(folderByName, normalizedOrder);
        var specialSet = {};
        for (var i = 0; i < specialNames.length; i++) specialSet[specialNames[i]] = true;

        var newOrder = [];
        if (mode === 'interleaved') {
            newOrder = normalizedOrder.slice();
            var fromIdx = newOrder.indexOf(draggedName);
            var toIdx = newOrder.indexOf(targetName);
            if (fromIdx < 0 || toIdx < 0) return false;
            newOrder.splice(fromIdx, 1);
            // If removing dragged element shifts indices, recompute target index.
            toIdx = newOrder.indexOf(targetName);
            newOrder.splice(toIdx, 0, draggedName);
        } else {
            // top mode: reorder within the same group (special vs other)
            var draggedIsSpecial = !!specialSet[draggedName];
            var targetIsSpecial = !!specialSet[targetName];
            if (draggedIsSpecial !== targetIsSpecial) return false;

            var specialOrdered = [];
            var otherOrdered = [];
            for (var j = 0; j < normalizedOrder.length; j++) {
                var n = normalizedOrder[j];
                if (specialSet[n]) specialOrdered.push(n);
                else otherOrdered.push(n);
            }

            if (draggedIsSpecial) {
                var group = specialOrdered.slice();
                var fromIdx2 = group.indexOf(draggedName);
                var toIdx2 = group.indexOf(targetName);
                if (fromIdx2 < 0 || toIdx2 < 0) return false;
                group.splice(fromIdx2, 1);
                toIdx2 = group.indexOf(targetName);
                group.splice(toIdx2, 0, draggedName);
                newOrder = group.concat(otherOrdered);
            } else {
                var group2 = otherOrdered.slice();
                var fromIdx3 = group2.indexOf(draggedName);
                var toIdx3 = group2.indexOf(targetName);
                if (fromIdx3 < 0 || toIdx3 < 0) return false;
                group2.splice(fromIdx3, 1);
                toIdx3 = group2.indexOf(targetName);
                group2.splice(toIdx3, 0, draggedName);
                newOrder = specialOrdered.concat(group2);
            }
        }

        if (!$scope.wmSettings) {
            $scope.wmSettings = {};
        }
        if (!$scope.wmSettings.folderSettings) {
            $scope.wmSettings.folderSettings = {
                folderMappings: {},
                folderOrder: [],
                specialDisplayMode: 'top',
                enableDragDrop: true
            };
        }
        $scope.wmSettings.folderSettings.folderOrder = newOrder;
        $scope.folderLayoutDirty = true;
        $scope.applyFolderLayout();
        $timeout(function() {
            $scope.persistFolderLayoutSettings(true);
        }, 0);
        return true;
    }

    /** Persist folder layout only (silent on success unless silent is false). Errors are always reported. */
    $scope.persistFolderLayoutSettings = function(silent) {
        if (!$scope.wmSettings || !$scope.wmSettings.folderSettings) return;
        apiCall('/webmail/api/saveSettings', {
            folderSettings: angular.copy($scope.wmSettings.folderSettings)
        }, function(data) {
            if (data.status === 1) {
                $scope.folderLayoutDirty = false;
                if (!silent) {
                    notify('Folder layout saved.');
                }
            } else {
                notify(data.error_message || 'Could not save folder layout.', 'error');
            }
        }, function() {
            notify('Could not save folder layout.', 'error');
        });
    };

    $scope.onFolderDragStart = function(folderName) {
        if (!_getEnableDragDrop()) return;
        $scope.draggingFolder = folderName;
        $scope.dragOverFolder = null;
    };

    $scope.onFolderDragOver = function(evt, targetFolderName) {
        if (!_getEnableDragDrop()) return;
        evt.preventDefault();
        if (!$scope.draggingFolder || $scope.draggingFolder === targetFolderName) {
            $scope.dragOverFolder = null;
            return;
        }

        // In top mode, only allow drops within the same group.
        var mode = _getSpecialDisplayMode();
        if (mode === 'top') {
            var folderByName = _getFolderByName();
            var normalizedOrder = _normalizeFolderOrder(folderByName);
            var specialNames = _getSpecialFolderNames(folderByName, normalizedOrder);
            var specialSet = {};
            for (var i = 0; i < specialNames.length; i++) specialSet[specialNames[i]] = true;

            var draggedIsSpecial = !!specialSet[$scope.draggingFolder];
            var targetIsSpecial = !!specialSet[targetFolderName];
            if (draggedIsSpecial !== targetIsSpecial) {
                $scope.dragOverFolder = null;
                return;
            }
        }
        $scope.dragOverFolder = targetFolderName;
    };

    $scope.onFolderDrop = function(evt, targetFolderName) {
        if (!_getEnableDragDrop()) return;
        evt.preventDefault();
        if (!$scope.draggingFolder) return;
        _updateFolderOrderAfterDrag($scope.draggingFolder, targetFolderName);
        $scope.draggingFolder = null;
        $scope.dragOverFolder = null;
    };

    $scope.onFolderDragEnd = function() {
        $scope.draggingFolder = null;
        $scope.dragOverFolder = null;
    };

    $scope.selectFolder = function(name) {
        $scope.ensureFolderAncestorsExpanded(name);
        $scope.currentFolder = name;
        $scope.currentPage = 1;
        $scope.openMsg = null;
        $scope.viewMode = 'list';
        $scope.searchQuery = '';
        $scope.messageListSearchActive = false;
        var folderByName = _getFolderByName();
        $scope.displayFolderRows = _buildDisplayFolderRows($scope.displayFolders, folderByName);
        $scope.loadMessages();
    };

    $scope.getFolderDisplayName = function(folderName) {
        if (!folderName) return '';
        var list = $scope.folders || [];
        for (var i = 0; i < list.length; i++) {
            if (list[i] && list[i].name === folderName) {
                return $scope.getFolderRowLabel(list[i], 0);
            }
        }
        return folderName;
    };

    $scope.getFolderIcon = function(folder) {
        // Prefer semantic mapping selected in Settings.
        var mappings = (($scope.wmSettings || {}).folderSettings || {}).folderMappings || {};
        var name = folder.name || '';
        if (mappings.inbox && name === mappings.inbox) return 'fa-inbox';
        if ((mappings.spam && name === mappings.spam) || (mappings.junk_e_mail && name === mappings.junk_e_mail)) return 'fa-exclamation-triangle';
        if (mappings.drafts && name === mappings.drafts) return 'fa-file';
        if ((mappings.trash && name === mappings.trash) || (mappings.deleted_items && name === mappings.deleted_items)) return 'fa-trash';

        // Use folder_type from backend if available (mapped from Dovecot folder names)
        var ftype = folder.folder_type || '';
        if (ftype === 'inbox') return 'fa-inbox';
        if (ftype === 'sent') return 'fa-paper-plane';
        if (ftype === 'drafts') return 'fa-file';
        if (ftype === 'trash') return 'fa-trash';
        if (ftype === 'junk') return 'fa-exclamation-triangle';
        if (ftype === 'archive') return 'fa-box-archive';
        // Fallback to name-based detection
        var n = (folder.display_name || folder.name || '').toLowerCase();
        if (n === 'inbox') return 'fa-inbox';
        if (n.indexOf('sent') >= 0) return 'fa-paper-plane';
        if (n.indexOf('draft') >= 0) return 'fa-file';
        if (n.indexOf('deleted') >= 0 || n.indexOf('trash') >= 0) return 'fa-trash';
        if (n.indexOf('junk') >= 0 || n.indexOf('spam') >= 0) return 'fa-exclamation-triangle';
        if (n.indexOf('archive') >= 0) return 'fa-box-archive';
        return 'fa-folder';
    };

    $scope.canDeleteFolder = function(folder) {
        if (!folder || !folder.name) return false;
        var ftype = folder.folder_type || '';
        if (['inbox', 'sent', 'drafts', 'trash', 'junk', 'archive'].indexOf(ftype) >= 0) {
            return false;
        }
        var maps = _getFolderMappings();
        var n = folder.name;
        var nl = n.toLowerCase();
        var roleKeys = ['inbox', 'sent', 'drafts', 'spam', 'junk_e_mail', 'trash', 'deleted_items', 'archive'];
        for (var ri = 0; ri < roleKeys.length; ri++) {
            var mv = maps[roleKeys[ri]];
            if (mv && String(mv).toLowerCase() === nl) {
                return false;
            }
        }
        for (var pk in WM_FOLDER_PROTECTED) {
            if (WM_FOLDER_PROTECTED[pk] && String(pk).toLowerCase() === nl) {
                return false;
            }
        }
        return true;
    };

    $scope.openDeleteFolderConfirm = function(folder) {
        if (!$scope.canDeleteFolder(folder)) return;
        $scope.folderPendingDelete = folder;
        $scope.showDeleteFolderDialog = true;
    };

    $scope.cancelDeleteFolderDialog = function() {
        $scope.showDeleteFolderDialog = false;
        $scope.folderPendingDelete = null;
    };

    $scope.confirmDeleteFolder = function() {
        var folder = $scope.folderPendingDelete;
        if (!folder || !$scope.canDeleteFolder(folder)) {
            $scope.cancelDeleteFolderDialog();
            return;
        }
        apiCall('/webmail/api/deleteFolder', {name: folder.name}, function(data) {
            if (data.status === 1) {
                $scope.cancelDeleteFolderDialog();
                if ($scope.currentFolder === folder.name) {
                    $scope.currentFolder = 'INBOX';
                    $scope.viewMode = 'list';
                }
                $scope.loadFolders();
                notify('Folder deleted.');
            } else {
                notify(data.error_message || 'Failed to delete folder.', 'error');
            }
        }, function(err) {
            notify('Failed to delete folder.', 'error');
            console.error('deleteFolder:', err);
        });
    };

    $scope.openNewFolderDialog = function() {
        $scope.newFolderNameInput = '';
        $scope.showNewFolderDialog = true;
        $timeout(function() {
            var el = document.getElementById('wm-new-folder-input');
            if (el) {
                el.focus();
            }
        }, 150);
    };

    $scope.cancelNewFolderDialog = function() {
        $scope.showNewFolderDialog = false;
        $scope.newFolderNameInput = '';
    };

    $scope.submitNewFolderDialog = function() {
        var name = ($scope.newFolderNameInput || '').trim();
        if (!name) {
            notify('Type a folder name in the box, then click Create.', 'error');
            return;
        }
        if (name.indexOf('INBOX.') !== 0) {
            name = 'INBOX.' + name;
        }
        apiCall('/webmail/api/createFolder', {name: name}, function(data) {
            if (data.status === 1) {
                $scope.showNewFolderDialog = false;
                $scope.newFolderNameInput = '';
                $scope.loadFolders();
                notify('Folder created.');
            } else {
                notify(data.error_message || 'Failed to create folder.', 'error');
            }
        }, function(err) {
            notify('Failed to create folder.', 'error');
            console.error('createFolder:', err);
        });
    };

    // --- Messages ---
    $scope.loadMessages = function() {
        $scope.messageListSearchActive = false;
        $scope.loading = true;
        apiCall('/webmail/api/listMessages', {
            folder: $scope.currentFolder,
            page: $scope.currentPage,
            perPage: $scope.perPage
        }, function(data) {
            $scope.loading = false;
            if (data.status === 1) {
                $scope.messages = data.messages;
                $scope.totalMessages = data.total;
                $scope.totalPages = data.pages;
                $scope.selectAll = false;
            } else {
                notify(data.error_message || 'Failed to load messages.', 'error');
            }
        }, function() {
            $scope.loading = false;
        });
    };

    $scope.prevPage = function() {
        if ($scope.currentPage > 1) {
            $scope.currentPage--;
            $scope.loadMessages();
        }
    };

    $scope.nextPage = function() {
        if ($scope.currentPage < $scope.totalPages) {
            $scope.currentPage++;
            $scope.loadMessages();
        }
    };

    $scope.searchMessages = function() {
        var q = ($scope.searchQuery || '').trim();
        if (!q) {
            $scope.messageListSearchActive = false;
            $scope.loadMessages();
            return;
        }
        var scopeParam = $scope.messageSearchScope === '__all__' ? 'all' : 'folder';
        var folderParam = $scope.messageSearchScope === '__all__'
            ? $scope.currentFolder
            : $scope.messageSearchScope;
        $scope.loading = true;
        apiCall('/webmail/api/searchMessages', {
            query: q,
            scope: scopeParam,
            folder: folderParam
        }, function(data) {
            $scope.loading = false;
            if (data.status !== 1) {
                notify(data.error_message || 'Search failed.', 'error');
                return;
            }
            $scope.messageListSearchActive = true;
            $scope.messages = data.messages || [];
            $scope.totalMessages = $scope.messages.length;
            $scope.totalPages = 1;
            $scope.currentPage = 1;
            $scope.selectAll = false;
            if ($scope.messages.length === 0) {
                notify('No messages found.', 'info');
            }
        }, function() {
            $scope.loading = false;
        });
    };

    // ── Open/Read Message ────────────────────────────────────
    $scope.openMessage = function(msg) {
        var folder = (msg && msg.folder) ? msg.folder : $scope.currentFolder;
        apiCall('/webmail/api/getMessage', {
            folder: folder,
            uid: msg.uid
        }, function(data) {
            if (data.status === 1) {
                $scope.openMsg = data.message;
                $scope.openMsg.folder = folder;
                var html = data.message.body_html || '';
                var text = data.message.body_text || '';
                // Use sanitized HTML from backend, or escape plain text
                if (html) {
                    $scope.trustedBody = $sce.trustAsHtml(html);
                } else {
                    // Escape plain text to prevent XSS
                    var escaped = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                    $scope.trustedBody = $sce.trustAsHtml('<pre>' + escaped + '</pre>');
                }
                $scope.viewMode = 'read';
                // Only decrement unread count if message was actually unread
                if (!msg.is_read) {
                    msg.is_read = true;
                    $scope.folders.forEach(function(f) {
                        if (f.name === folder && f.unread_count > 0) {
                            f.unread_count--;
                        }
                    });
                }
            }
        });
    };

    // ── Compose ──────────────────────────────────────────────
    $scope.composeNew = function() {
        $scope.compose = {to: '', cc: '', bcc: '', subject: '', body: '', files: [], inReplyTo: '', references: ''};
        $scope.viewMode = 'compose';
        $scope.showBcc = false;
        $timeout(function() {
            var editor = document.getElementById('wm-compose-body');
            if (editor) {
                editor.innerHTML = '';
                // Add signature if available
                if ($scope.wmSettings.signatureHtml) {
                    editor.innerHTML = '<br><br><div class="wm-signature">-- <br>' + $scope.wmSettings.signatureHtml + '</div>';
                }
            }
        }, 100);
        startDraftAutoSave();
    };

    $scope.replyTo = function() {
        if (!$scope.openMsg) return;
        var subj = $scope.openMsg.subject || '';
        $scope.compose = {
            to: $scope.openMsg.from,
            cc: '',
            bcc: '',
            subject: (subj.match(/^Re:/i) ? '' : 'Re: ') + subj,
            body: '',
            files: [],
            inReplyTo: $scope.openMsg.message_id || '',
            references: (($scope.openMsg.references || '') + ' ' + ($scope.openMsg.message_id || '')).trim()
        };
        $scope.viewMode = 'compose';
        $timeout(function() {
            var editor = document.getElementById('wm-compose-body');
            if (editor) {
                var sig = $scope.wmSettings.signatureHtml ? '<br><br><div class="wm-signature">-- <br>' + $scope.wmSettings.signatureHtml + '</div>' : '';
                editor.innerHTML = '<br>' + sig + '<br><div class="wm-quoted">On ' + $scope.openMsg.date + ', ' + $scope.openMsg.from + ' wrote:<br><blockquote>' + ($scope.openMsg.body_html || $scope.openMsg.body_text || '') + '</blockquote></div>';
            }
        }, 100);
        startDraftAutoSave();
    };

    $scope.replyAll = function() {
        if (!$scope.openMsg) return;
        var cc = [];
        if ($scope.openMsg.to) cc.push($scope.openMsg.to);
        if ($scope.openMsg.cc) cc.push($scope.openMsg.cc);
        $scope.compose = {
            to: $scope.openMsg.from,
            cc: cc.join(', '),
            bcc: '',
            subject: (($scope.openMsg.subject || '').match(/^Re:/i) ? '' : 'Re: ') + ($scope.openMsg.subject || ''),
            body: '',
            files: [],
            inReplyTo: $scope.openMsg.message_id || '',
            references: (($scope.openMsg.references || '') + ' ' + ($scope.openMsg.message_id || '')).trim()
        };
        $scope.viewMode = 'compose';
        $timeout(function() {
            var editor = document.getElementById('wm-compose-body');
            if (editor) {
                editor.innerHTML = '<br><br><div class="wm-quoted">On ' + ($scope.openMsg.date || '') + ', ' + ($scope.openMsg.from || '') + ' wrote:<br><blockquote>' + ($scope.openMsg.body_html || $scope.openMsg.body_text || '') + '</blockquote></div>';
            }
        }, 100);
        startDraftAutoSave();
    };

    $scope.forwardMsg = function() {
        if (!$scope.openMsg) return;
        var fsubj = $scope.openMsg.subject || '';
        $scope.compose = {
            to: '',
            cc: '',
            bcc: '',
            subject: (fsubj.match(/^Fwd:/i) ? '' : 'Fwd: ') + fsubj,
            body: '',
            files: [],
            inReplyTo: '',
            references: ''
        };
        $scope.viewMode = 'compose';
        $timeout(function() {
            var editor = document.getElementById('wm-compose-body');
            if (editor) {
                editor.innerHTML = '<br><br><div class="wm-forwarded">---------- Forwarded message ----------<br>From: ' + $scope.openMsg.from + '<br>Date: ' + $scope.openMsg.date + '<br>Subject: ' + $scope.openMsg.subject + '<br>To: ' + $scope.openMsg.to + '<br><br>' + ($scope.openMsg.body_html || $scope.openMsg.body_text || '') + '</div>';
            }
        }, 100);
        startDraftAutoSave();
    };

    $scope.updateComposeBody = function() {
        var editor = document.getElementById('wm-compose-body');
        if (editor) {
            $scope.compose.body = editor.innerHTML;
        }
    };

    $scope.execCmd = function(cmd) {
        document.execCommand(cmd, false, null);
    };

    $scope.insertLink = function() {
        var url = prompt('Enter URL:');
        if (url) {
            document.execCommand('createLink', false, url);
        }
    };

    $scope.addFiles = function(files) {
        $scope.$apply(function() {
            for (var i = 0; i < files.length; i++) {
                $scope.compose.files.push(files[i]);
            }
        });
    };

    $scope.removeFile = function(index) {
        $scope.compose.files.splice(index, 1);
    };

    $scope.sendMessage = function() {
        $scope.updateComposeBody();
        var rcpt = countValidRecipients($scope.compose.to, $scope.compose.cc, $scope.compose.bcc);
        if (rcpt < 1) {
            notify('Enter at least one full email address (e.g. user@hotmail.com). "Test" or a name alone is not a valid address. Use the full address in To, Cc, or Bcc.', 'error');
            return;
        }
        $scope.sending = true;
        stopDraftAutoSave();

        var fd = new FormData();
        fd.append('fromAccount', $scope.currentEmail || '');
        fd.append('to', $scope.compose.to);
        fd.append('cc', $scope.compose.cc || '');
        fd.append('bcc', $scope.compose.bcc || '');
        fd.append('subject', $scope.compose.subject);
        fd.append('body', $scope.compose.body);
        fd.append('inReplyTo', $scope.compose.inReplyTo || '');
        fd.append('references', $scope.compose.references || '');
        for (var i = 0; i < $scope.compose.files.length; i++) {
            fd.append('attachment_' + i, $scope.compose.files[i]);
        }

        $http.post('/webmail/api/sendMessage', fd, {
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': undefined
            },
            transformRequest: angular.identity
        }).then(function(resp) {
            $scope.sending = false;
            if (resp.data.status === 1) {
                notify('Message sent from ' + (resp.data.sentFrom || 'unknown'));
                $scope.viewMode = 'list';
                $scope.loadMessages();
            } else {
                notify(resp.data.error_message, 'error');
            }
        }, function() {
            $scope.sending = false;
            notify('Failed to send message.', 'error');
        });
    };

    $scope.saveDraft = function() {
        $scope.updateComposeBody();
        apiCall('/webmail/api/saveDraft', {
            to: $scope.compose.to,
            subject: $scope.compose.subject,
            body: $scope.compose.body
        }, function(data) {
            if (data.status === 1) {
                notify('Draft saved.');
            }
        });
    };

    $scope.discardDraft = function() {
        stopDraftAutoSave();
        $scope.viewMode = 'list';
        $scope.compose = {to: '', cc: '', bcc: '', subject: '', body: '', files: [], inReplyTo: '', references: ''};
    };

    function startDraftAutoSave() {
        stopDraftAutoSave();
        draftTimer = setInterval(function() {
            $scope.updateComposeBody();
            if ($scope.compose.subject || $scope.compose.body || $scope.compose.to) {
                apiCall('/webmail/api/saveDraft', {
                    to: $scope.compose.to,
                    subject: $scope.compose.subject,
                    body: $scope.compose.body
                });
            }
        }, 60000); // Auto-save every 60 seconds
    }

    function stopDraftAutoSave() {
        if (draftTimer) {
            clearInterval(draftTimer);
            draftTimer = null;
        }
    }

    // ── Bulk Actions ─────────────────────────────────────────
    $scope.toggleSelectAll = function() {
        $scope.messages.forEach(function(m) { m.selected = $scope.selectAll; });
    };

    function selectedUidsByFolder() {
        var map = {};
        $scope.messages.forEach(function(m) {
            if (!m.selected) return;
            var f = m.folder || $scope.currentFolder;
            if (!map[f]) map[f] = [];
            map[f].push(m.uid);
        });
        return map;
    }

    function refreshListAfterBulk() {
        if ($scope.messageListSearchActive && ($scope.searchQuery || '').trim()) {
            $scope.searchMessages();
        } else {
            $scope.loadMessages();
        }
        $scope.loadFolders();
    }

    $scope.getDragMessageItemsForMove = function(primaryMsg) {
        var selected = ($scope.messages || []).filter(function(m) { return m.selected; });
        var list = selected.length ? selected : (primaryMsg ? [primaryMsg] : []);
        var out = [];
        for (var i = 0; i < list.length; i++) {
            var m = list[i];
            if (!m || m.uid == null || m.uid === '') continue;
            out.push({ folder: m.folder || $scope.currentFolder, uid: String(m.uid) });
        }
        return out;
    };

    $scope.onMailItemsDragStart = function() {
        $scope.draggingMailItems = true;
    };

    $scope.onMailItemsDragEnd = function() {
        $scope.draggingMailItems = false;
        $scope.dragOverFolder = null;
    };

    $scope.onMessageDragOverFolder = function(name) {
        $scope.dragOverFolder = name;
    };

    $scope.onMessagesDropOnFolder = function(items, targetFolder) {
        $scope.dragOverFolder = null;
        $scope.draggingMailItems = false;
        if (!targetFolder || !items || !items.length) return;
        var map = {};
        for (var j = 0; j < items.length; j++) {
            var it = items[j];
            if (!it || it.uid == null || it.uid === '' || !it.folder) continue;
            if (it.folder === targetFolder) continue;
            if (!map[it.folder]) map[it.folder] = [];
            map[it.folder].push(String(it.uid));
        }
        var keys = Object.keys(map);
        if (keys.length === 0) {
            notify('Messages are already in that folder.', 'info');
            return;
        }
        var state = { pending: keys.length, err: false };
        function finishMoves() {
            state.pending--;
            if (state.pending > 0) return;
            if (!state.err) {
                notify('Message(s) moved.', 'success');
            } else {
                notify('Some messages could not be moved.', 'error');
            }
            refreshListAfterBulk();
        }
        keys.forEach(function(fld) {
            apiCall('/webmail/api/moveMessages', {
                folder: fld,
                uids: map[fld],
                targetFolder: targetFolder
            }, function(data) {
                if (!data || data.status !== 1) {
                    state.err = true;
                }
                finishMoves();
            }, function() {
                state.err = true;
                finishMoves();
            });
        });
    };

    function bulkApiPerFolder(path, extra, done) {
        var map = selectedUidsByFolder();
        var keys = Object.keys(map);
        if (keys.length === 0) {
            if (done) done();
            return;
        }
        var pending = keys.length;
        keys.forEach(function(fld) {
            var payload = angular.extend({folder: fld, uids: map[fld]}, extra || {});
            apiCall('/webmail/api/' + path, payload, function(data) {
                if (!data || data.status !== 1) {
                    notify(data && data.error_message ? data.error_message : 'Action failed.', 'error');
                }
                pending--;
                if (pending <= 0 && done) done();
            }, function() {
                pending--;
                if (pending <= 0 && done) done();
            });
        });
    }

    $scope.bulkDelete = function() {
        var map = selectedUidsByFolder();
        var n = Object.keys(map).reduce(function(acc, k) { return acc + map[k].length; }, 0);
        if (n === 0) return;
        bulkApiPerFolder('deleteMessages', {}, function() {
            refreshListAfterBulk();
        });
    };

    $scope.bulkMarkRead = function() {
        var map = selectedUidsByFolder();
        var n = Object.keys(map).reduce(function(acc, k) { return acc + map[k].length; }, 0);
        if (n === 0) return;
        bulkApiPerFolder('markRead', {}, function() {
            refreshListAfterBulk();
        });
    };

    $scope.bulkMarkUnread = function() {
        var map = selectedUidsByFolder();
        var n = Object.keys(map).reduce(function(acc, k) { return acc + map[k].length; }, 0);
        if (n === 0) return;
        bulkApiPerFolder('markUnread', {}, function() {
            refreshListAfterBulk();
        });
    };

    $scope.bulkMove = function() {
        if (!$scope.moveTarget) return;
        var map = selectedUidsByFolder();
        var n = Object.keys(map).reduce(function(acc, k) { return acc + map[k].length; }, 0);
        if (n === 0) return;
        var targetFolder = $scope.moveTarget.name || $scope.moveTarget;
        var keys = Object.keys(map);
        var pending = keys.length;
        keys.forEach(function(fld) {
            apiCall('/webmail/api/moveMessages', {
                folder: fld,
                uids: map[fld],
                targetFolder: targetFolder
            }, function(data) {
                if (!data || data.status !== 1) {
                    notify(data && data.error_message ? data.error_message : 'Move failed.', 'error');
                }
                pending--;
                if (pending <= 0) {
                    $scope.showMoveDropdown = false;
                    $scope.moveTarget = '';
                    refreshListAfterBulk();
                }
            }, function() {
                pending--;
                if (pending <= 0) {
                    $scope.showMoveDropdown = false;
                    $scope.moveTarget = '';
                    refreshListAfterBulk();
                }
            });
        });
    };

    $scope.toggleFlag = function(msg) {
        var fld = msg.folder || $scope.currentFolder;
        apiCall('/webmail/api/markFlagged', {folder: fld, uids: [msg.uid]}, function() {
            msg.is_flagged = !msg.is_flagged;
        });
    };

    $scope.deleteMsg = function(msg) {
        var fld = (msg && msg.folder) ? msg.folder : $scope.currentFolder;
        apiCall('/webmail/api/deleteMessages', {folder: fld, uids: [msg.uid]}, function(data) {
            if (data.status === 1) {
                $scope.openMsg = null;
                $scope.viewMode = 'list';
                refreshListAfterBulk();
            }
        });
    };

    // ── Attachments ──────────────────────────────────────────
    $scope.downloadAttachment = function(att) {
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = '/webmail/api/getAttachment';
        form.target = '_blank';
        var fields = {
            folder: $scope.openMsg.folder || $scope.currentFolder,
            uid: $scope.openMsg.uid,
            partId: att.part_id
        };
        fields['csrfmiddlewaretoken'] = getCookie('csrftoken');
        for (var key in fields) {
            var input = document.createElement('input');
            input.type = 'hidden';
            input.name = key;
            input.value = fields[key];
            form.appendChild(input);
        }
        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    };

    // ── View Mode ────────────────────────────────────────────
    $scope.setView = function(mode) {
        stopDraftAutoSave();
        $scope.viewMode = mode;
        $scope.openMsg = null;
        if (mode === 'contacts') $scope.loadContacts();
        if (mode === 'rules') $scope.loadRules();
        if (mode === 'settings') $scope.loadSettings();
    };

    // ── Contacts ─────────────────────────────────────────────
    $scope.loadContacts = function() {
        apiCall('/webmail/api/listContacts', {}, function(data) {
            if (data.status === 1) {
                $scope.contacts = data.contacts || [];
                $scope.filteredContacts = data.contacts || [];
                $scope.filterContacts();
            } else {
                $scope.contacts = [];
                $scope.filteredContacts = [];
                notify(data.error_message || 'Could not load contacts.', 'error');
            }
        }, function(err) {
            $scope.contacts = [];
            $scope.filteredContacts = [];
            notify('Could not load contacts.', 'error');
            console.error('listContacts error:', err);
        });
    };

    $scope.importContactsFromSnappymail = function() {
        apiCall('/webmail/api/importContactsFromSnappymail', {}, function(data) {
            if (data.status === 1) {
                notify('Contacts imported from SnappyMail (found: ' + (data.total_found || 0) + ').');
                $scope.loadContacts();
            } else {
                notify(data.error_message || 'Failed to import contacts.', 'error');
            }
        }, function(err) {
            notify('Failed to import contacts.', 'error');
            console.error('importContactsFromSnappymail error:', err);
        });
    };

    $scope.filterContacts = function() {
        var q = ($scope.contactSearch || '').toLowerCase();
        $scope.filteredContacts = $scope.contacts.filter(function(c) {
            return (c.display_name || '').toLowerCase().indexOf(q) >= 0 ||
                   (c.email_address || '').toLowerCase().indexOf(q) >= 0;
        });
    };

    $scope.newContact = function() {
        $scope.editingContact = {display_name: '', email_address: '', phone: '', organization: '', notes: ''};
    };

    $scope.editContact = function(c) {
        $scope.editingContact = angular.copy(c);
    };

    $scope.saveContact = function() {
        var c = $scope.editingContact;
        var url = c.id ? '/webmail/api/updateContact' : '/webmail/api/createContact';
        apiCall(url, {
            id: c.id,
            displayName: c.display_name,
            emailAddress: c.email_address,
            phone: c.phone,
            organization: c.organization,
            notes: c.notes
        }, function(data) {
            if (data.status === 1) {
                $scope.editingContact = null;
                $scope.loadContacts();
                notify('Contact saved.');
            } else {
                notify(data.error_message, 'error');
            }
        });
    };

    $scope.removeContact = function(c) {
        if (!confirm('Delete contact ' + (c.display_name || c.email_address) + '?')) return;
        apiCall('/webmail/api/deleteContact', {id: c.id}, function(data) {
            if (data.status === 1) {
                $scope.loadContacts();
            }
        });
    };

    $scope.composeToContact = function(c) {
        $scope.compose = {to: c.email_address, cc: '', bcc: '', subject: '', body: '', files: [], inReplyTo: '', references: ''};
        $scope.viewMode = 'compose';
        $scope.showBcc = false;
        $timeout(function() {
            var editor = document.getElementById('wm-compose-body');
            if (editor) {
                editor.innerHTML = '';
                if ($scope.wmSettings.signatureHtml) {
                    editor.innerHTML = '<br><br><div class="wm-signature">-- <br>' + $scope.wmSettings.signatureHtml + '</div>';
                }
            }
        }, 100);
        startDraftAutoSave();
    };

    // ── Sieve Rules ──────────────────────────────────────────
    $scope.loadRules = function() {
        apiCall('/webmail/api/listRules', {}, function(data) {
            if (data.status === 1) {
                $scope.sieveRules = data.rules || [];
            } else {
                $scope.sieveRules = [];
                notify(data.error_message || 'Could not load mail rules.', 'error');
            }
        }, function(err) {
            $scope.sieveRules = [];
            notify('Could not load mail rules.', 'error');
            console.error('listRules error:', err);
        });
    };

    $scope.importRulesFromSnappymail = function() {
        apiCall('/webmail/api/importRulesFromSnappymail', {}, function(data) {
            if (data.status === 1) {
                notify('SnappyMail rules imported.');
                $scope.loadRules();
            } else {
                notify(data.error_message || 'Failed to import rules.', 'error');
            }
        }, function(err) {
            notify('Failed to import rules.', 'error');
            console.error('importRulesFromSnappymail error:', err);
        });
    };

    $scope.newRule = function() {
        $scope.editingRule = {
            name: '', priority: 0, conditionField: 'from',
            conditionType: 'contains', conditionValue: '',
            actionType: 'move', actionValue: ''
        };
    };

    $scope.editRule = function(rule) {
        $scope.editingRule = {
            id: rule.id,
            name: rule.name,
            priority: rule.priority,
            conditionField: rule.condition_field,
            conditionType: rule.condition_type,
            conditionValue: rule.condition_value,
            actionType: rule.action_type,
            actionValue: rule.action_value
        };
    };

    $scope.saveRule = function() {
        var r = $scope.editingRule;
        var url = r.id ? '/webmail/api/updateRule' : '/webmail/api/createRule';
        apiCall(url, r, function(data) {
            if (data.status === 1) {
                $scope.editingRule = null;
                $scope.loadRules();
                notify('Rule saved.');
            } else {
                notify(data.error_message, 'error');
            }
        });
    };

    $scope.removeRule = function(rule) {
        if (!confirm('Delete rule "' + rule.name + '"?')) return;
        apiCall('/webmail/api/deleteRule', {id: rule.id}, function(data) {
            if (data.status === 1) {
                $scope.loadRules();
            }
        });
    };

    // ── Settings ─────────────────────────────────────────────
    $scope.loadSettings = function(done) {
        apiCall('/webmail/api/getSettings', {}, function(data) {
            if (data.status === 1) {
                $scope.wmSettings = data.settings;
                if (!$scope.wmSettings.folderSettings) {
                    $scope.wmSettings.folderSettings = {folderMappings: {}, folderOrder: [], specialDisplayMode: 'top', enableDragDrop: true};
                }
                var fm = $scope.wmSettings.folderSettings.folderMappings;
                if (fm && fm.spam) {
                    fm.junk_e_mail = fm.spam;
                }
                if ($scope.wmSettings.messagesPerPage) {
                    $scope.perPage = parseInt($scope.wmSettings.messagesPerPage);
                }
                if ($scope.folders && $scope.folders.length > 0 && typeof $scope.applyFolderLayout === 'function') {
                    $scope.applyFolderLayout();
                }
            }
            if (typeof done === 'function') {
                $timeout(function() { done(); }, 0);
            }
        });
    };

    $scope.saveSettings = function() {
        var fm = ($scope.wmSettings || {}).folderSettings;
        fm = fm && fm.folderMappings;
        if (fm && fm.spam) {
            fm.junk_e_mail = fm.spam;
        }
        apiCall('/webmail/api/saveSettings', $scope.wmSettings, function(data) {
            if (data.status === 1) {
                notify('Settings saved.');
                if ($scope.wmSettings.messagesPerPage) {
                    $scope.perPage = parseInt($scope.wmSettings.messagesPerPage);
                }
                if ($scope.folders && $scope.folders.length > 0 && typeof $scope.applyFolderLayout === 'function') {
                    $scope.applyFolderLayout();
                }
            } else {
                notify(data.error_message, 'error');
            }
        });
    };

}]);
