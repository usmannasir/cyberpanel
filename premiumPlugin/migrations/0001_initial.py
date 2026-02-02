# Generated migration for PremiumPluginConfig

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='PremiumPluginConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_method', models.CharField(choices=[('patreon', 'Patreon Subscription'), ('paypal', 'PayPal Payment'), ('both', 'Check Both (Patreon or PayPal)')], default='both', help_text='Choose which payment method to use for verification.', max_length=10)),
                ('activation_key', models.CharField(blank=True, default='', help_text='Validated activation key - grants access without re-entering.', max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Premium Plugin Configuration',
                'verbose_name_plural': 'Premium Plugin Configurations',
            },
        ),
    ]
