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

app.controller('webmailCtrl', ['$scope', '$http', '$sce', '$timeout', function($scope, $http, $sce, $timeout) {

    // ── State ────────────────────────────────────────────────
    $scope.currentEmail = '';
    $scope.managedAccounts = [];
    $scope.folders = [];
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
    $scope.selectAll = false;
    $scope.showMoveDropdown = false;
    $scope.moveTarget = '';
    $scope.showBcc = false;

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
    $scope.wmSettings = {};

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

    // ── Init ─────────────────────────────────────────────────
    $scope.init = function() {
        // Try SSO first
        apiCall('/webmail/api/sso', {}, function(data) {
            if (data.status === 1) {
                $scope.currentEmail = data.email;
                $scope.managedAccounts = data.accounts || [];
                $scope.loadFolders();
                $scope.loadSettings();
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
                $scope.loadFolders();
                $scope.loadSettings();
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
                $scope.folders = data.folders;
                $scope.loadMessages();
            } else {
                notify(data.error_message || 'Failed to load folders.', 'error');
            }
        });
    };

    $scope.selectFolder = function(name) {
        $scope.currentFolder = name;
        $scope.currentPage = 1;
        $scope.openMsg = null;
        $scope.viewMode = 'list';
        $scope.searchQuery = '';
        $scope.loadMessages();
    };

    $scope.getFolderIcon = function(folder) {
        // Use folder_type from backend if available (mapped from Dovecot folder names)
        var ftype = folder.folder_type || '';
        if (ftype === 'inbox') return 'fa-inbox';
        if (ftype === 'sent') return 'fa-paper-plane';
        if (ftype === 'drafts') return 'fa-file';
        if (ftype === 'trash') return 'fa-trash';
        if (ftype === 'junk') return 'fa-ban';
        if (ftype === 'archive') return 'fa-box-archive';
        // Fallback to name-based detection
        var n = (folder.display_name || folder.name || '').toLowerCase();
        if (n === 'inbox') return 'fa-inbox';
        if (n.indexOf('sent') >= 0) return 'fa-paper-plane';
        if (n.indexOf('draft') >= 0) return 'fa-file';
        if (n.indexOf('deleted') >= 0 || n.indexOf('trash') >= 0) return 'fa-trash';
        if (n.indexOf('junk') >= 0 || n.indexOf('spam') >= 0) return 'fa-ban';
        if (n.indexOf('archive') >= 0) return 'fa-box-archive';
        return 'fa-folder';
    };

    $scope.createFolder = function() {
        var name = prompt('Folder name:');
        if (!name) return;
        // Dovecot namespace: prefix with INBOX. and use . as separator
        if (name.indexOf('INBOX.') !== 0) {
            name = 'INBOX.' + name;
        }
        apiCall('/webmail/api/createFolder', {name: name}, function(data) {
            if (data.status === 1) {
                $scope.loadFolders();
                notify('Folder created.');
            } else {
                notify(data.error_message, 'error');
            }
        });
    };

    // ── Messages ─────────────────────────────────────────────
    $scope.loadMessages = function() {
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
        if (!$scope.searchQuery) {
            $scope.loadMessages();
            return;
        }
        $scope.loading = true;
        apiCall('/webmail/api/searchMessages', {
            folder: $scope.currentFolder,
            query: $scope.searchQuery
        }, function(data) {
            $scope.loading = false;
            if (data.status === 1 && data.uids && data.uids.length > 0) {
                // Fetch the found messages by their UIDs
                apiCall('/webmail/api/listMessages', {
                    folder: $scope.currentFolder,
                    page: 1,
                    perPage: data.uids.length,
                    uids: data.uids
                }, function(msgData) {
                    if (msgData.status === 1) {
                        $scope.messages = msgData.messages;
                        $scope.totalMessages = msgData.total;
                        $scope.totalPages = msgData.pages;
                    }
                });
            } else if (data.status === 1) {
                $scope.messages = [];
                $scope.totalMessages = 0;
                $scope.totalPages = 1;
                notify('No messages found.', 'info');
            }
        }, function() {
            $scope.loading = false;
        });
    };

    // ── Open/Read Message ────────────────────────────────────
    $scope.openMessage = function(msg) {
        apiCall('/webmail/api/getMessage', {
            folder: $scope.currentFolder,
            uid: msg.uid
        }, function(data) {
            if (data.status === 1) {
                $scope.openMsg = data.message;
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
                        if (f.name === $scope.currentFolder && f.unread_count > 0) {
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

    function getSelectedUids() {
        return $scope.messages.filter(function(m) { return m.selected; }).map(function(m) { return m.uid; });
    }

    $scope.bulkDelete = function() {
        var uids = getSelectedUids();
        if (uids.length === 0) return;
        apiCall('/webmail/api/deleteMessages', {folder: $scope.currentFolder, uids: uids}, function(data) {
            if (data.status === 1) {
                $scope.loadMessages();
                $scope.loadFolders();
            }
        });
    };

    $scope.bulkMarkRead = function() {
        var uids = getSelectedUids();
        if (uids.length === 0) return;
        apiCall('/webmail/api/markRead', {folder: $scope.currentFolder, uids: uids}, function() {
            $scope.loadMessages();
            $scope.loadFolders();
        });
    };

    $scope.bulkMarkUnread = function() {
        var uids = getSelectedUids();
        if (uids.length === 0) return;
        apiCall('/webmail/api/markUnread', {folder: $scope.currentFolder, uids: uids}, function() {
            $scope.loadMessages();
            $scope.loadFolders();
        });
    };

    $scope.bulkMove = function() {
        var uids = getSelectedUids();
        if (uids.length === 0 || !$scope.moveTarget) return;
        apiCall('/webmail/api/moveMessages', {
            folder: $scope.currentFolder,
            uids: uids,
            targetFolder: $scope.moveTarget.name || $scope.moveTarget
        }, function(data) {
            if (data.status === 1) {
                $scope.showMoveDropdown = false;
                $scope.moveTarget = '';
                $scope.loadMessages();
                $scope.loadFolders();
            }
        });
    };

    $scope.toggleFlag = function(msg) {
        apiCall('/webmail/api/markFlagged', {folder: $scope.currentFolder, uids: [msg.uid]}, function() {
            msg.is_flagged = !msg.is_flagged;
        });
    };

    $scope.deleteMsg = function(msg) {
        apiCall('/webmail/api/deleteMessages', {folder: $scope.currentFolder, uids: [msg.uid]}, function(data) {
            if (data.status === 1) {
                $scope.openMsg = null;
                $scope.viewMode = 'list';
                $scope.loadMessages();
                $scope.loadFolders();
            }
        });
    };

    // ── Attachments ──────────────────────────────────────────
    $scope.downloadAttachment = function(att) {
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = '/webmail/api/getAttachment';
        form.target = '_blank';
        var fields = {folder: $scope.currentFolder, uid: $scope.openMsg.uid, partId: att.part_id};
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
                $scope.contacts = data.contacts;
                $scope.filteredContacts = data.contacts;
            }
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
                $scope.sieveRules = data.rules;
            }
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
    $scope.loadSettings = function() {
        apiCall('/webmail/api/getSettings', {}, function(data) {
            if (data.status === 1) {
                $scope.wmSettings = data.settings;
                if ($scope.wmSettings.messagesPerPage) {
                    $scope.perPage = parseInt($scope.wmSettings.messagesPerPage);
                }
            }
        });
    };

    $scope.saveSettings = function() {
        apiCall('/webmail/api/saveSettings', $scope.wmSettings, function(data) {
            if (data.status === 1) {
                notify('Settings saved.');
                if ($scope.wmSettings.messagesPerPage) {
                    $scope.perPage = parseInt($scope.wmSettings.messagesPerPage);
                }
            } else {
                notify(data.error_message, 'error');
            }
        });
    };

}]);
