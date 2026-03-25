from django.db import models


class WebmailSession(models.Model):
    session_key = models.CharField(max_length=64, unique=True)
    email_account = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wm_sessions'

    def __str__(self):
        return '%s (%s)' % (self.email_account, self.session_key[:8])


class Contact(models.Model):
    owner_email = models.CharField(max_length=200, db_index=True)
    display_name = models.CharField(max_length=200, blank=True, default='')
    email_address = models.CharField(max_length=200)
    phone = models.CharField(max_length=50, blank=True, default='')
    organization = models.CharField(max_length=200, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    is_auto_collected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wm_contacts'
        unique_together = ('owner_email', 'email_address')

    def __str__(self):
        return '%s <%s>' % (self.display_name, self.email_address)


class ContactGroup(models.Model):
    owner_email = models.CharField(max_length=200, db_index=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'wm_contact_groups'
        unique_together = ('owner_email', 'name')

    def __str__(self):
        return self.name


class ContactGroupMembership(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    group = models.ForeignKey(ContactGroup, on_delete=models.CASCADE)

    class Meta:
        db_table = 'wm_contact_group_members'
        unique_together = ('contact', 'group')


class WebmailSettings(models.Model):
    email_account = models.CharField(max_length=200, primary_key=True)
    display_name = models.CharField(max_length=200, blank=True, default='')
    signature_html = models.TextField(blank=True, default='')
    messages_per_page = models.IntegerField(default=25)
    default_reply_behavior = models.CharField(max_length=20, default='reply',
                                              choices=[('reply', 'Reply'),
                                                       ('reply_all', 'Reply All')])
    theme_preference = models.CharField(max_length=20, default='auto',
                                        choices=[('light', 'Light'),
                                                 ('dark', 'Dark'),
                                                 ('auto', 'Auto')])
    auto_collect_contacts = models.BooleanField(default=True)

    class Meta:
        db_table = 'wm_settings'

    def __str__(self):
        return self.email_account


class SieveRule(models.Model):
    email_account = models.CharField(max_length=200, db_index=True)
    name = models.CharField(max_length=200)
    priority = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    condition_field = models.CharField(max_length=50,
                                       choices=[('from', 'From'),
                                                ('to', 'To'),
                                                ('subject', 'Subject'),
                                                ('size', 'Size')])
    condition_type = models.CharField(max_length=50,
                                      choices=[('contains', 'Contains'),
                                               ('is', 'Is'),
                                               ('matches', 'Matches'),
                                               ('greater_than', 'Greater than')])
    condition_value = models.CharField(max_length=500)
    action_type = models.CharField(max_length=50,
                                   choices=[('move', 'Move to folder'),
                                            ('forward', 'Forward to'),
                                            ('discard', 'Discard'),
                                            ('flag', 'Flag')])
    action_value = models.CharField(max_length=500, blank=True, default='')
    sieve_script = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'wm_sieve_rules'
        ordering = ['priority']

    def __str__(self):
        return '%s: %s' % (self.email_account, self.name)
