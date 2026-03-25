import json
import os
import base64

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db import transaction

from .models import Contact, ContactGroup, ContactGroupMembership, WebmailSettings, SieveRule
from .services.imap_client import IMAPClient
from .services.smtp_client import SMTPClient
from .services.email_composer import EmailComposer
from .services.sieve_client import SieveClient
from .services.snappymail_contacts_importer import SnappymailContactsImporter
from .services.snappymail_rules_importer import SnappymailRulesImporter
from .services.webmail_folder_settings_store import WebmailFolderSettingsStore

import plogical.CyberCPLogFileWriter as logging

WEBMAIL_CONF = '/etc/cyberpanel/webmail.conf'

WEBMAIL_SEARCH_MAX_RESULTS = 500


def _webmail_message_sort_ts(msg):
    """Parse message date header for sorting (best-effort)."""
    if not msg or not isinstance(msg, dict):
        return 0.0
    raw = msg.get('date') or ''
    if not raw:
        return 0.0
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(raw)
        if dt is not None:
            return dt.timestamp()
    except Exception:
        pass
    return 0.0


class WebmailManager:

    def __init__(self, request):
        self.request = request

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _json_response(data):
        return HttpResponse(json.dumps(data), content_type='application/json')

    @staticmethod
    def _error(msg):
        return HttpResponse(json.dumps({'status': 0, 'error_message': str(msg)}),
                            content_type='application/json')

    @staticmethod
    def _success(extra=None):
        data = {'status': 1}
        if extra:
            data.update(extra)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def _get_post_data(self):
        try:
            return json.loads(self.request.body)
        except Exception:
            return self.request.POST.dict()

    def _get_email(self):
        # Check for explicit email in POST body (from account switcher)
        # This ensures the correct account is used even if session is stale
        try:
            data = json.loads(self.request.body)
            explicit = data.get('fromAccount', '')
            if explicit:
                accounts = self._get_managed_accounts()
                if explicit in accounts:
                    self.request.session['webmail_email'] = explicit
                    return explicit
        except Exception:
            pass
        return self.request.session.get('webmail_email')

    def _get_master_config(self):
        """Read master user config from /etc/cyberpanel/webmail.conf"""
        try:
            with open(WEBMAIL_CONF, 'r') as f:
                config = json.load(f)
            return config.get('master_user'), config.get('master_password')
        except Exception:
            return None, None

    def _get_imap(self, email_addr=None):
        """Create IMAP client, preferring master user auth for SSO sessions."""
        addr = email_addr or self._get_email()
        if not addr:
            raise Exception('No email account selected')

        master_user, master_pass = self._get_master_config()
        if master_user and master_pass:
            return IMAPClient(addr, '', master_user=master_user, master_password=master_pass)

        # Fallback: standalone login with stored password
        password = self.request.session.get('webmail_password', '')
        return IMAPClient(addr, password)

    def _get_smtp(self):
        addr = self._get_email()
        if not addr:
            raise Exception('No email account selected')

        # If using master user (SSO), we can't auth to SMTP since
        # auth_master_user_separator is not set in Dovecot.
        # Use local relay via port 25 instead (Postfix permits localhost).
        master_user, master_pass = self._get_master_config()
        is_standalone = self.request.session.get('webmail_standalone', False)

        if master_user and master_pass and not is_standalone:
            return SMTPClient(addr, '', use_local_relay=True)

        password = self.request.session.get('webmail_password', '')
        return SMTPClient(addr, password)

    def _get_sieve(self, email_addr=None):
        addr = email_addr or self._get_email()
        if not addr:
            raise Exception('No email account selected')

        master_user, master_pass = self._get_master_config()
        if master_user and master_pass:
            return SieveClient(addr, '', master_user=master_user, master_password=master_pass)

        password = self.request.session.get('webmail_password', '')
        return SieveClient(addr, password)

    def _get_managed_accounts(self):
        """Get email accounts the current CyberPanel user can access."""
        try:
            from plogical.acl import ACLManager
            from loginSystem.models import Administrator
            from mailServer.models import Domains, EUsers

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            websites = ACLManager.findAllSites(currentACL, userID)
            websites = websites + ACLManager.findChildDomains(websites)

            accounts = []
            for site in websites:
                try:
                    domain = Domains.objects.get(domain=site)
                    for eu in EUsers.objects.filter(emailOwner=domain):
                        accounts.append(eu.email)
                except Exception:
                    continue
            return accounts
        except Exception:
            return []

    # ── Page Renders ──────────────────────────────────────────

    def loadWebmail(self):
        from plogical.httpProc import httpProc
        email = self._get_email()
        accounts = self._get_managed_accounts()

        if not email and accounts:
            if len(accounts) == 1:
                self.request.session['webmail_email'] = accounts[0]
                email = accounts[0]
            else:
                # Multiple accounts - render picker
                proc = httpProc(self.request, 'webmail/index.html',
                                {'accounts': json.dumps(accounts), 'show_picker': True},
                                'listEmails')
                return proc.render()

        proc = httpProc(self.request, 'webmail/index.html',
                        {'email': email or '',
                         'accounts': json.dumps(accounts),
                         'show_picker': False},
                        'listEmails')
        return proc.render()

    def loadLogin(self):
        return render(self.request, 'webmail/login.html')

    # ── Auth APIs ─────────────────────────────────────────────

    def apiLogin(self):
        data = self._get_post_data()
        email_addr = data.get('email', '')
        password = data.get('password', '')

        if not email_addr or not password:
            return self._error('Email and password are required.')

        try:
            client = IMAPClient(email_addr, password)
            client.close()
        except Exception as e:
            return self._error('Login failed: %s' % str(e))

        self.request.session['webmail_email'] = email_addr
        self.request.session['webmail_password'] = password
        self.request.session['webmail_standalone'] = True
        return self._success()

    def apiLogout(self):
        for key in ['webmail_email', 'webmail_password', 'webmail_standalone']:
            self.request.session.pop(key, None)
        return self._success()

    def apiSSO(self):
        """Auto-login for CyberPanel users."""
        accounts = self._get_managed_accounts()
        if not accounts:
            return self._error('No email accounts found for your user.')
        # Preserve previously selected account if still valid
        current = self.request.session.get('webmail_email')
        if not current or current not in accounts:
            current = accounts[0]
        self.request.session['webmail_email'] = current
        return self._success({'email': current, 'accounts': accounts})

    def apiListAccounts(self):
        accounts = self._get_managed_accounts()
        return self._success({'accounts': accounts})

    def apiSwitchAccount(self):
        data = self._get_post_data()
        email = data.get('email', '')
        accounts = self._get_managed_accounts()
        if email not in accounts:
            return self._error('You do not have access to this account.')
        self.request.session['webmail_email'] = email
        return self._success({'email': email})

    # ── Folder APIs ───────────────────────────────────────────

    def apiListFolders(self):
        try:
            with self._get_imap() as imap:
                folders = imap.list_folders()
            return self._success({'folders': folders})
        except Exception as e:
            return self._error(str(e))

    def apiCreateFolder(self):
        data = self._get_post_data()
        name = data.get('name', '')
        if not name:
            return self._error('Folder name is required.')
        try:
            with self._get_imap() as imap:
                if imap.create_folder(name):
                    return self._success()
                return self._error('Failed to create folder.')
        except Exception as e:
            return self._error(str(e))

    def apiRenameFolder(self):
        data = self._get_post_data()
        old_name = data.get('oldName', '')
        new_name = data.get('newName', '')
        if not old_name or not new_name:
            return self._error('Both old and new folder names are required.')
        try:
            with self._get_imap() as imap:
                if imap.rename_folder(old_name, new_name):
                    return self._success()
                return self._error('Failed to rename folder.')
        except Exception as e:
            return self._error(str(e))

    def apiDeleteFolder(self):
        data = self._get_post_data()
        name = data.get('name', '')
        if not name:
            return self._error('Folder name is required.')
        # CyberPanel/Dovecot folder names (INBOX. prefix, separator '.')
        protected = {
            'INBOX', 'INBOX.Sent', 'INBOX.Drafts', 'INBOX.Deleted Items',
            'INBOX.Junk E-mail', 'INBOX.Archive', 'INBOX.spam', 'INBOX.Trash',
            'Sent', 'Drafts', 'Trash', 'Spam', 'Junk', 'Archive',
            'Deleted Items', 'Junk E-mail',
        }
        protected.update(set(IMAPClient.SPECIAL_FOLDERS.values()))
        if name in protected:
            return self._error('Cannot delete system folder.')
        try:
            with self._get_imap() as imap:
                if imap.delete_folder(name):
                    return self._success()
                return self._error('Failed to delete folder.')
        except Exception as e:
            return self._error(str(e))

    # ── Message APIs ──────────────────────────────────────────

    def apiListMessages(self):
        data = self._get_post_data()
        folder = data.get('folder', 'INBOX')
        page = int(data.get('page', 1))
        per_page = int(data.get('perPage', 25))
        uids_filter = data.get('uids')
        if uids_filter is not None and not isinstance(uids_filter, list):
            uids_filter = None
        try:
            with self._get_imap() as imap:
                result = imap.list_messages(
                    folder, page, per_page, uids_filter=uids_filter)
            return self._success(result)
        except Exception as e:
            return self._error(str(e))

    def apiSearchMessages(self):
        data = self._get_post_data()
        folder = (data.get('folder') or 'INBOX').strip()
        query = (data.get('query') or '').strip()
        scope = (data.get('scope') or 'all').strip().lower()
        if not query:
            return self._error('Search text is required.')
        if scope not in ('all', 'folder'):
            scope = 'all'
        try:
            with self._get_imap() as imap:
                if scope == 'folder':
                    uids = imap.search_messages(folder, query)
                    uids = [
                        u.decode() if isinstance(u, bytes) else str(u)
                        for u in uids if u]
                    if not uids:
                        return self._success({
                            'messages': [],
                            'scope': 'folder',
                            'folder': folder,
                        })
                    per = max(len(uids), 1)
                    result = imap.list_messages(
                        folder, 1, per, uids_filter=uids)
                    for m in result.get('messages') or []:
                        m['folder'] = folder
                    return self._success({
                        'messages': result.get('messages') or [],
                        'scope': 'folder',
                        'folder': folder,
                    })

                # Search all selectable folders
                folders = imap.list_folders()
                all_messages = []
                for finfo in folders:
                    if len(all_messages) >= WEBMAIL_SEARCH_MAX_RESULTS:
                        break
                    fname = finfo.get('name')
                    if not fname:
                        continue
                    try:
                        uids = imap.search_messages(fname, query)
                        if not uids:
                            continue
                        uids = [
                            u.decode() if isinstance(u, bytes) else str(u)
                            for u in uids if u]
                        remaining = WEBMAIL_SEARCH_MAX_RESULTS - len(all_messages)
                        if remaining <= 0:
                            break
                        if len(uids) > remaining:
                            uids = uids[:remaining]
                        result = imap.list_messages(
                            fname, 1, len(uids), uids_filter=uids)
                        for m in result.get('messages') or []:
                            m['folder'] = fname
                            all_messages.append(m)
                    except Exception:
                        continue
                try:
                    all_messages.sort(
                        key=_webmail_message_sort_ts, reverse=True)
                except Exception:
                    pass
                return self._success({
                    'messages': all_messages,
                    'scope': 'all',
                })
        except Exception as e:
            return self._error(str(e))

    def apiGetMessage(self):
        data = self._get_post_data()
        folder = data.get('folder', 'INBOX')
        uid = data.get('uid', '')
        if not uid:
            return self._error('Message UID is required.')
        try:
            with self._get_imap() as imap:
                msg = imap.get_message(folder, uid)
                if msg is None:
                    return self._error('Message not found.')
                imap.mark_read(folder, [uid])
            return self._success({'message': msg})
        except Exception as e:
            return self._error(str(e))

    def apiGetAttachment(self):
        data = self._get_post_data()
        folder = data.get('folder', 'INBOX')
        uid = data.get('uid', '')
        part_id = data.get('partId', '')
        try:
            with self._get_imap() as imap:
                result = imap.get_attachment(folder, uid, part_id)
                if result is None:
                    return self._error('Attachment not found.')
                filename, content_type, payload = result
            response = HttpResponse(payload, content_type=content_type)
            # Sanitize filename to prevent header injection and path traversal
            import os as _os
            safe_filename = _os.path.basename(filename)
            safe_filename = safe_filename.replace('"', '_').replace('\r', '').replace('\n', '').replace('\x00', '')
            if not safe_filename:
                safe_filename = 'attachment'
            response['Content-Disposition'] = 'attachment; filename="%s"' % safe_filename
            return response
        except Exception as e:
            return self._error(str(e))

    # ── Action APIs ───────────────────────────────────────────

    def apiSendMessage(self):
        try:
            # For multipart forms, check fromAccount in POST data
            if self.request.content_type and 'multipart' in self.request.content_type:
                from_account = self.request.POST.get('fromAccount', '')
                if from_account:
                    accounts = self._get_managed_accounts()
                    if from_account in accounts:
                        self.request.session['webmail_email'] = from_account

            email_addr = self._get_email()
            if not email_addr:
                return self._error('Not logged in.')

            # Handle multipart form data for attachments
            if self.request.content_type and 'multipart' in self.request.content_type:
                to = self.request.POST.get('to', '')
                cc = self.request.POST.get('cc', '')
                bcc = self.request.POST.get('bcc', '')
                subject = self.request.POST.get('subject', '')
                body_html = self.request.POST.get('body', '')
                in_reply_to = self.request.POST.get('inReplyTo', '')
                references = self.request.POST.get('references', '')

                attachments = []
                for key in self.request.FILES:
                    f = self.request.FILES[key]
                    attachments.append((f.name, f.content_type, f.read()))
            else:
                data = self._get_post_data()
                to = data.get('to', '')
                cc = data.get('cc', '')
                bcc = data.get('bcc', '')
                subject = data.get('subject', '')
                body_html = data.get('body', '')
                in_reply_to = data.get('inReplyTo', '')
                references = data.get('references', '')
                attachments = None

            try:
                mime_msg = EmailComposer.compose(
                    from_addr=email_addr,
                    to_addrs=to,
                    subject=subject,
                    body_html=body_html,
                    cc_addrs=cc,
                    bcc_addrs=bcc,
                    attachments=attachments,
                    in_reply_to=in_reply_to,
                    references=references,
                )
            except ValueError as ve:
                return self._error(str(ve))

            smtp = self._get_smtp()
            result = smtp.send_message(mime_msg)

            if not result['success']:
                return self._error(result.get('error', 'Failed to send.'))

            # Save to Sent folder
            try:
                with self._get_imap() as imap:
                    raw = mime_msg.as_bytes()
                    smtp.save_to_sent(imap, raw)
            except Exception:
                pass

            # Auto-collect contacts
            try:
                settings = WebmailSettings.objects.filter(email_account=email_addr).first()
                if settings is None or settings.auto_collect_contacts:
                    self._auto_collect(email_addr, to, cc)
            except Exception:
                pass

            return self._success({'messageId': result['message_id'], 'sentFrom': email_addr})
        except Exception as e:
            return self._error(str(e))

    def _auto_collect(self, owner, to_addrs, cc_addrs=''):
        """Auto-save recipients as contacts."""
        import re
        all_addrs = '%s,%s' % (to_addrs, cc_addrs) if cc_addrs else to_addrs
        emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', all_addrs)
        for addr in emails:
            if addr == owner:
                continue
            Contact.objects.get_or_create(
                owner_email=owner,
                email_address=addr,
                defaults={'is_auto_collected': True, 'display_name': addr.split('@')[0]},
            )

    def apiSaveDraft(self):
        try:
            email_addr = self._get_email()
            if not email_addr:
                return self._error('Not logged in.')
            data = self._get_post_data()
            to = data.get('to', '')
            subject = data.get('subject', '')
            body_html = data.get('body', '')

            mime_msg = EmailComposer.compose(
                from_addr=email_addr,
                to_addrs=to,
                subject=subject,
                body_html=body_html,
            )

            with self._get_imap() as imap:
                # CyberPanel's Dovecot uses INBOX.Drafts
                draft_folders = ['INBOX.Drafts', 'Drafts', 'Draft']
                saved = False
                for folder in draft_folders:
                    try:
                        if imap.append_message(folder, mime_msg.as_bytes(), '\\Draft \\Seen'):
                            saved = True
                            break
                    except Exception:
                        continue
                if not saved:
                    imap.create_folder('INBOX.Drafts')
                    imap.append_message('INBOX.Drafts', mime_msg.as_bytes(), '\\Draft \\Seen')

            return self._success()
        except Exception as e:
            return self._error(str(e))

    def apiDeleteMessages(self):
        data = self._get_post_data()
        folder = data.get('folder', 'INBOX')
        uids = data.get('uids', [])
        if not uids:
            return self._error('No messages selected.')
        try:
            with self._get_imap() as imap:
                imap.delete_messages(folder, uids)
            return self._success()
        except Exception as e:
            return self._error(str(e))

    def apiMoveMessages(self):
        data = self._get_post_data()
        folder = data.get('folder', 'INBOX')
        uids = data.get('uids', [])
        target = data.get('targetFolder', '')
        if not uids or not target:
            return self._error('Messages and target folder are required.')
        try:
            with self._get_imap() as imap:
                imap.move_messages(folder, uids, target)
            return self._success()
        except Exception as e:
            return self._error(str(e))

    def apiMarkRead(self):
        data = self._get_post_data()
        folder = data.get('folder', 'INBOX')
        uids = data.get('uids', [])
        try:
            with self._get_imap() as imap:
                imap.mark_read(folder, uids)
            return self._success()
        except Exception as e:
            return self._error(str(e))

    def apiMarkUnread(self):
        data = self._get_post_data()
        folder = data.get('folder', 'INBOX')
        uids = data.get('uids', [])
        try:
            with self._get_imap() as imap:
                imap.mark_unread(folder, uids)
            return self._success()
        except Exception as e:
            return self._error(str(e))

    def apiMarkFlagged(self):
        data = self._get_post_data()
        folder = data.get('folder', 'INBOX')
        uids = data.get('uids', [])
        try:
            with self._get_imap() as imap:
                imap.mark_flagged(folder, uids)
            return self._success()
        except Exception as e:
            return self._error(str(e))

    # ── Contact APIs ──────────────────────────────────────────

    def apiListContacts(self):
        email = self._get_email()
        try:
            contacts_qs = Contact.objects.filter(owner_email=email)
            contacts = list(contacts_qs.values(
                'id', 'display_name', 'email_address', 'phone', 'organization', 'notes', 'is_auto_collected'
            ))
            if not contacts and not contacts_qs.exists():
                # Best-effort: auto-import contacts from SnappyMail if our DB is empty.
                try:
                    importer = SnappymailContactsImporter()
                    sn_contacts = importer.import_contacts(email)
                    if sn_contacts:
                        with transaction.atomic():
                            for c in sn_contacts:
                                c_email = (c.get('email_address') or '').strip()
                                if not c_email:
                                    continue
                                display = (c.get('display_name') or '').strip()
                                Contact.objects.get_or_create(
                                    owner_email=email,
                                    email_address=c_email,
                                    defaults={
                                        'display_name': display,
                                        'is_auto_collected': False,
                                    }
                                )
                        contacts = list(Contact.objects.filter(owner_email=email).values(
                            'id', 'display_name', 'email_address', 'phone', 'organization', 'notes', 'is_auto_collected'
                        ))
                except Exception as e:
                    # Don't break UI if auto-import fails.
                    try:
                        logging.CyberCPLogFileWriter.writeToFile(
                            'SnappyMail auto-import contacts failed for %s: %s' % (email, str(e)))
                    except Exception:
                        pass
            return self._success({'contacts': contacts})
        except Exception as e:
            return self._error(str(e))

    def apiCreateContact(self):
        email = self._get_email()
        data = self._get_post_data()
        try:
            contact = Contact.objects.create(
                owner_email=email,
                display_name=data.get('displayName', ''),
                email_address=data.get('emailAddress', ''),
                phone=data.get('phone', ''),
                organization=data.get('organization', ''),
                notes=data.get('notes', ''),
            )
            return self._success({'id': contact.id})
        except Exception as e:
            return self._error(str(e))

    def apiUpdateContact(self):
        email = self._get_email()
        data = self._get_post_data()
        contact_id = data.get('id')
        try:
            contact = Contact.objects.get(id=contact_id, owner_email=email)
            for field in ['display_name', 'email_address', 'phone', 'organization', 'notes']:
                camel = field.replace('_', ' ').title().replace(' ', '')
                camel = camel[0].lower() + camel[1:]
                if camel in data:
                    setattr(contact, field, data[camel])
            contact.save()
            return self._success()
        except Contact.DoesNotExist:
            return self._error('Contact not found.')
        except Exception as e:
            return self._error(str(e))

    def apiDeleteContact(self):
        email = self._get_email()
        data = self._get_post_data()
        contact_id = data.get('id')
        try:
            Contact.objects.filter(id=contact_id, owner_email=email).delete()
            return self._success()
        except Exception as e:
            return self._error(str(e))

    def apiSearchContacts(self):
        email = self._get_email()
        data = self._get_post_data()
        query = data.get('query', '')
        try:
            from django.db.models import Q
            contacts = Contact.objects.filter(
                owner_email=email
            ).filter(
                Q(display_name__icontains=query) | Q(email_address__icontains=query)
            ).values('id', 'display_name', 'email_address')[:20]
            return self._success({'contacts': list(contacts)})
        except Exception as e:
            return self._error(str(e))

    def apiListContactGroups(self):
        email = self._get_email()
        try:
            groups = list(ContactGroup.objects.filter(owner_email=email).values('id', 'name'))
            return self._success({'groups': groups})
        except Exception as e:
            return self._error(str(e))

    def apiCreateContactGroup(self):
        email = self._get_email()
        data = self._get_post_data()
        name = data.get('name', '')
        if not name:
            return self._error('Group name is required.')
        try:
            group = ContactGroup.objects.create(owner_email=email, name=name)
            return self._success({'id': group.id})
        except Exception as e:
            return self._error(str(e))

    def apiDeleteContactGroup(self):
        email = self._get_email()
        data = self._get_post_data()
        group_id = data.get('id')
        try:
            ContactGroup.objects.filter(id=group_id, owner_email=email).delete()
            return self._success()
        except Exception as e:
            return self._error(str(e))

    # ── SnappyMail Imports ─────────────────────────────────────

    def apiImportContactsFromSnappymail(self):
        """
        Import contacts from SnappyMail/RainLoop into wm_contacts.

        Optional POST body:
          - clearExisting (bool): delete existing contacts for this email before importing.
        """
        email = self._get_email()
        data = self._get_post_data()
        clear_existing = bool(data.get('clearExisting', False))

        try:
            if clear_existing:
                Contact.objects.filter(owner_email=email).delete()

            importer = SnappymailContactsImporter()
            contacts = importer.import_contacts(email)

            imported_new = 0
            updated_existing = 0

            with transaction.atomic():
                for c in contacts:
                    c_email = (c.get('email_address') or '').strip()
                    if not c_email:
                        continue
                    display = (c.get('display_name') or '').strip()

                    obj, created = Contact.objects.get_or_create(
                        owner_email=email,
                        email_address=c_email,
                        defaults={
                            'display_name': display,
                            'is_auto_collected': False,
                        }
                    )
                    if created:
                        imported_new += 1
                    else:
                        # Only overwrite if current display name is empty.
                        if display and not (obj.display_name or '').strip():
                            obj.display_name = display
                            obj.is_auto_collected = False
                            obj.save(update_fields=['display_name', 'is_auto_collected'])
                            updated_existing += 1

            return self._success({
                'imported_new': imported_new,
                'updated_existing': updated_existing,
                'total_found': len(contacts),
            })
        except Exception as e:
            # Do not leak DB credentials in error output.
            try:
                logging.CyberCPLogFileWriter.writeToFile(
                    'SnappyMail contacts import failed for %s: %s' % (email, str(e)))
            except Exception:
                pass
            return self._error('SnappyMail contacts import failed.')

    def apiImportRulesFromSnappymail(self):
        """
        Import RainLoop/SnappyMail sieve filters into CyberPanel webmail.

        Approach:
        - Fetch RainLoop ManageSieve script body (typically `rainloop.user`)
        - Store it as RAW in wm_sieve_rules.sieve_script
        - Upload it to ManageSieve as CyberPanel's `cyberpanel` active script
        """
        email = self._get_email()
        data = self._get_post_data()
        clear_existing = bool(data.get('clearExisting', True))

        try:
            importer = SnappymailRulesImporter()
            script_name = ''
            raw_script = ''

            with self._get_sieve(email) as sieve:
                script_name, raw_script = importer.fetch_raw_script(sieve)

            raw_script = (raw_script or '').strip()
            if not raw_script:
                return self._error('No RainLoop sieve script content found to import.')

            if clear_existing:
                SieveRule.objects.filter(email_account=email, sieve_script__gt='').delete()

            priority = -1000
            rule_name = 'SnappyMail import: %s' % (script_name or 'rainloop.user')

            SieveRule.objects.create(
                email_account=email,
                name=rule_name,
                priority=priority,
                is_active=True,
                condition_field='from',
                condition_type='contains',
                condition_value='',
                action_type='move',
                action_value='',
                sieve_script=raw_script,
            )

            self._sync_sieve_rules(email)

            return self._success({'imported_rule': rule_name})
        except ConnectionRefusedError:
            return self._error('ManageSieve connection refused. Is dovecot-sieve running on port 4190?')
        except Exception as e:
            try:
                logging.CyberCPLogFileWriter.writeToFile(
                    'SnappyMail rules import failed for %s: %s' % (email, str(e)))
            except Exception:
                pass
            return self._error('SnappyMail rules import failed.')

    # ── Sieve Rule APIs ───────────────────────────────────────

    def apiListRules(self):
        email = self._get_email()
        try:
            rules_qs = SieveRule.objects.filter(email_account=email)

            # Best-effort auto-import when our DB doesn't have rules yet.
            if not rules_qs.exists():
                try:
                    importer = SnappymailRulesImporter()
                    script_name = ''
                    raw_script = ''
                    with self._get_sieve(email) as sieve:
                        script_name, raw_script = importer.fetch_raw_script(sieve)

                    raw_script = (raw_script or '').strip()
                    if raw_script:
                        # Create a single RAW rule. This makes the imported script active.
                        SieveRule.objects.create(
                            email_account=email,
                            name='SnappyMail import: %s' % (script_name or 'rainloop.user'),
                            priority=-1000,
                            is_active=True,
                            condition_field='from',
                            condition_type='contains',
                            condition_value='',
                            action_type='move',
                            action_value='',
                            sieve_script=raw_script,
                        )
                        self._sync_sieve_rules(email)
                        rules_qs = SieveRule.objects.filter(email_account=email)
                except Exception as e:
                    try:
                        logging.CyberCPLogFileWriter.writeToFile(
                            'SnappyMail auto-import rules failed for %s: %s' % (email, str(e)))
                    except Exception:
                        pass

            rules_qs = rules_qs.order_by('priority')
            rules = []
            for r in rules_qs:
                sieve_script = getattr(r, 'sieve_script', '') or ''
                rules.append({
                    'id': r.id,
                    'name': r.name,
                    'priority': r.priority,
                    'is_active': bool(r.is_active),
                    'condition_field': r.condition_field,
                    'condition_type': r.condition_type,
                    'condition_value': r.condition_value,
                    'action_type': r.action_type,
                    'action_value': r.action_value,
                    'is_raw': bool(sieve_script.strip()),
                })
            return self._success({'rules': rules})
        except Exception as e:
            return self._error(str(e))

    def apiCreateRule(self):
        email = self._get_email()
        data = self._get_post_data()
        try:
            rule = SieveRule.objects.create(
                email_account=email,
                name=data.get('name', 'New Rule'),
                priority=data.get('priority', 0),
                is_active=data.get('isActive', True),
                condition_field=data.get('conditionField', 'from'),
                condition_type=data.get('conditionType', 'contains'),
                condition_value=data.get('conditionValue', ''),
                action_type=data.get('actionType', 'move'),
                action_value=data.get('actionValue', ''),
            )
            self._sync_sieve_rules(email)
            return self._success({'id': rule.id})
        except Exception as e:
            return self._error(str(e))

    def apiUpdateRule(self):
        email = self._get_email()
        data = self._get_post_data()
        rule_id = data.get('id')
        try:
            rule = SieveRule.objects.get(id=rule_id, email_account=email)
            for field in ['name', 'priority', 'is_active', 'condition_field',
                          'condition_type', 'condition_value', 'action_type', 'action_value']:
                camel = field.replace('_', ' ').title().replace(' ', '')
                camel = camel[0].lower() + camel[1:]
                if camel in data:
                    val = data[camel]
                    if field == 'is_active':
                        val = bool(val)
                    elif field == 'priority':
                        val = int(val)
                    setattr(rule, field, val)
            rule.save()
            self._sync_sieve_rules(email)
            return self._success()
        except SieveRule.DoesNotExist:
            return self._error('Rule not found.')
        except Exception as e:
            return self._error(str(e))

    def apiDeleteRule(self):
        email = self._get_email()
        data = self._get_post_data()
        rule_id = data.get('id')
        try:
            SieveRule.objects.filter(id=rule_id, email_account=email).delete()
            self._sync_sieve_rules(email)
            return self._success()
        except Exception as e:
            return self._error(str(e))

    def apiActivateRules(self):
        email = self._get_email()
        try:
            self._sync_sieve_rules(email)
            return self._success()
        except Exception as e:
            return self._error(str(e))

    def _sync_sieve_rules(self, email):
        """Generate sieve script from DB rules and upload to Dovecot.

        ManageSieve may not be available if dovecot-sieve/pigeonhole is not
        installed or if the ManageSieve service isn't running on port 4190.
        Rules are always saved to the database; Sieve sync is best-effort.
        """
        rules = SieveRule.objects.filter(email_account=email, is_active=True).order_by('priority')
        raw_script = ''
        for r in rules:
            sieve_script = getattr(r, 'sieve_script', '') or ''
            if sieve_script.strip():
                raw_script = sieve_script
                break

        if raw_script.strip():
            # If we imported raw ManageSieve rules, override CyberPanel-generated rules.
            script = raw_script
        else:
            rule_dicts = []
            for r in rules:
                rule_dicts.append({
                    'name': r.name,
                    'condition_field': r.condition_field,
                    'condition_type': r.condition_type,
                    'condition_value': r.condition_value,
                    'action_type': r.action_type,
                    'action_value': r.action_value,
                })
            script = SieveClient.rules_to_sieve(rule_dicts)

        try:
            with self._get_sieve(email) as sieve:
                sieve.put_script('cyberpanel', script)
                sieve.activate_script('cyberpanel')
        except ConnectionRefusedError:
            logging.CyberCPLogFileWriter.writeToFile(
                'Sieve sync skipped for %s: ManageSieve not running on port 4190. '
                'Install dovecot-sieve and enable ManageSieve.' % email)
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile('Sieve sync failed for %s: %s' % (email, str(e)))

    # ── Settings APIs ─────────────────────────────────────────

    def apiGetSettings(self):
        email = self._get_email()
        try:
            settings, created = WebmailSettings.objects.get_or_create(email_account=email)
            folder_store = WebmailFolderSettingsStore()
            folder_settings = folder_store.get_for_account(email)
            return self._success({
                'settings': {
                    'displayName': settings.display_name,
                    'signatureHtml': settings.signature_html,
                    'messagesPerPage': settings.messages_per_page,
                    'defaultReplyBehavior': settings.default_reply_behavior,
                    'themePreference': settings.theme_preference,
                    'autoCollectContacts': settings.auto_collect_contacts,
                    'folderSettings': folder_settings,
                }
            })
        except Exception as e:
            return self._error(str(e))

    def apiSaveSettings(self):
        email = self._get_email()
        data = self._get_post_data()
        try:
            settings, created = WebmailSettings.objects.get_or_create(email_account=email)
            if isinstance(data, dict):
                if 'displayName' in data:
                    settings.display_name = (data.get('displayName') or '')[:200]
                if 'signatureHtml' in data:
                    settings.signature_html = data.get('signatureHtml') or ''
                if 'messagesPerPage' in data:
                    try:
                        mp = int(data.get('messagesPerPage'))
                        if mp < 1:
                            mp = 25
                        settings.messages_per_page = mp
                    except Exception:
                        pass
                if 'defaultReplyBehavior' in data:
                    drb = data.get('defaultReplyBehavior') or 'reply'
                    if drb in ['reply', 'reply_all']:
                        settings.default_reply_behavior = drb
                if 'themePreference' in data:
                    tp = data.get('themePreference') or 'auto'
                    if tp in ['light', 'dark', 'auto']:
                        settings.theme_preference = tp
                if 'autoCollectContacts' in data:
                    settings.auto_collect_contacts = bool(data.get('autoCollectContacts'))

            settings.save()

            # Folder settings are stored outside the DB (file-based) to avoid migrations.
            folder_settings = data.get('folderSettings') if isinstance(data, dict) else None
            if isinstance(folder_settings, dict):
                folder_store = WebmailFolderSettingsStore()
                folder_store.save_for_account(email, folder_settings)
            return self._success()
        except Exception as e:
            return self._error(str(e))

    # ── Image Proxy ───────────────────────────────────────────

    def apiProxyImage(self):
        """Proxy external images to prevent tracking and mixed content."""
        if not self._get_email():
            return self._error('Not logged in.')

        url_b64 = self.request.GET.get('url', '') or self.request.POST.get('url', '')
        try:
            url = base64.urlsafe_b64decode(url_b64).decode('utf-8')
        except Exception:
            return self._error('Invalid URL.')

        if not url.startswith(('http://', 'https://')):
            return self._error('Invalid URL scheme.')

        # Block internal/private IPs to prevent SSRF
        import urllib.parse
        import socket
        import ipaddress
        hostname = urllib.parse.urlparse(url).hostname or ''
        try:
            resolved_ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(resolved_ip)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved:
                return self._error('Invalid URL.')
        except (socket.gaierror, ValueError):
            return self._error('Invalid URL.')

        try:
            import urllib.request
            req = urllib.request.Request(url, headers={
                'User-Agent': 'CyberPanel-Webmail-Proxy/1.0',
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                content_type = resp.headers.get('Content-Type', 'image/png')
                if not content_type.startswith('image/'):
                    return self._error('Not an image.')
                data = resp.read(5 * 1024 * 1024)  # 5MB max
            return HttpResponse(data, content_type=content_type)
        except Exception:
            return self._error('Failed to fetch image.')
