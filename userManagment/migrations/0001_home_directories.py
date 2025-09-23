# Generated migration for home directories feature

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('loginSystem', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HomeDirectory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Directory name (e.g., home, home2)', max_length=50, unique=True)),
                ('path', models.CharField(help_text='Full path to home directory', max_length=255, unique=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this home directory is active')),
                ('is_default', models.BooleanField(default=False, help_text='Whether this is the default home directory')),
                ('max_users', models.IntegerField(default=0, help_text='Maximum number of users (0 = unlimited)')),
                ('description', models.TextField(blank=True, help_text='Description of this home directory')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Home Directory',
                'verbose_name_plural': 'Home Directories',
                'db_table': 'home_directories',
            },
        ),
        migrations.CreateModel(
            name='UserHomeMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('home_directory', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='userManagment.homedirectory')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='home_mapping', to='loginSystem.administrator')),
            ],
            options={
                'verbose_name': 'User Home Mapping',
                'verbose_name_plural': 'User Home Mappings',
                'db_table': 'user_home_mappings',
            },
        ),
    ]
