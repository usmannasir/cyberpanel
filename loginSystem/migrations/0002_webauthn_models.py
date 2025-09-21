# Generated migration for WebAuthn models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('loginSystem', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebAuthnCredential',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('credential_id', models.CharField(help_text='Base64 encoded credential ID', max_length=255, unique=True)),
                ('public_key', models.TextField(help_text='Base64 encoded public key')),
                ('counter', models.BigIntegerField(default=0, help_text='Signature counter for replay protection')),
                ('name', models.CharField(help_text='User-friendly name for the passkey', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_used', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this credential is active')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webauthn_credentials', to='loginSystem.administrator')),
            ],
            options={
                'verbose_name': 'WebAuthn Credential',
                'verbose_name_plural': 'WebAuthn Credentials',
                'db_table': 'webauthn_credentials',
            },
        ),
        migrations.CreateModel(
            name='WebAuthnChallenge',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('challenge', models.CharField(help_text='Base64 encoded challenge', max_length=255)),
                ('challenge_type', models.CharField(choices=[('registration', 'Registration'), ('authentication', 'Authentication')], max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('used', models.BooleanField(default=False)),
                ('metadata', models.TextField(default='{}', help_text='Additional challenge metadata as JSON')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webauthn_challenges', to='loginSystem.administrator')),
            ],
            options={
                'verbose_name': 'WebAuthn Challenge',
                'verbose_name_plural': 'WebAuthn Challenges',
                'db_table': 'webauthn_challenges',
            },
        ),
        migrations.CreateModel(
            name='WebAuthnSession',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(help_text='Unique session identifier', max_length=255, unique=True)),
                ('session_type', models.CharField(choices=[('registration', 'Registration'), ('authentication', 'Authentication')], max_length=20)),
                ('data', models.TextField(help_text='Session data as JSON')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webauthn_sessions', to='loginSystem.administrator')),
            ],
            options={
                'verbose_name': 'WebAuthn Session',
                'verbose_name_plural': 'WebAuthn Sessions',
                'db_table': 'webauthn_sessions',
            },
        ),
        migrations.CreateModel(
            name='WebAuthnSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=False, help_text='Whether WebAuthn is enabled for this user')),
                ('require_passkey', models.BooleanField(default=False, help_text='Require passkey for login (passwordless)')),
                ('allow_multiple_credentials', models.BooleanField(default=True, help_text='Allow multiple passkeys per user')),
                ('max_credentials', models.IntegerField(default=10, help_text='Maximum number of passkeys allowed')),
                ('timeout_seconds', models.IntegerField(default=60, help_text='WebAuthn operation timeout in seconds')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='webauthn_settings', to='loginSystem.administrator')),
            ],
            options={
                'verbose_name': 'WebAuthn Settings',
                'verbose_name_plural': 'WebAuthn Settings',
                'db_table': 'webauthn_settings',
            },
        ),
        migrations.AddIndex(
            model_name='webauthncredential',
            index=models.Index(fields=['user', 'is_active'], name='webauthn_cre_user_id_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='webauthncredential',
            index=models.Index(fields=['credential_id'], name='webauthn_cre_credent_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='webauthnchallenge',
            index=models.Index(fields=['user', 'challenge_type', 'used'], name='webauthn_cha_user_id_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='webauthnchallenge',
            index=models.Index(fields=['expires_at'], name='webauthn_cha_expires_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='webauthnsession',
            index=models.Index(fields=['session_id'], name='webauthn_ses_session_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='webauthnsession',
            index=models.Index(fields=['expires_at'], name='webauthn_ses_expires_123456_idx'),
        ),
    ]
