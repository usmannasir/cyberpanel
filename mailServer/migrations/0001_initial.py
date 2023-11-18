# Generated by Django 3.1.3 on 2023-10-27 20:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('websiteFunctions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Domains',
            fields=[
                ('domain', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('childOwner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='websiteFunctions.childdomains')),
                ('domainOwner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='websiteFunctions.websites')),
            ],
            options={
                'db_table': 'e_domains',
            },
        ),
        migrations.CreateModel(
            name='Forwardings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(max_length=80)),
                ('destination', models.TextField()),
            ],
            options={
                'db_table': 'e_forwardings',
            },
        ),
        migrations.CreateModel(
            name='Pipeprograms',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(max_length=80)),
                ('destination', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Transport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(max_length=128, unique=True)),
                ('transport', models.CharField(max_length=128)),
            ],
            options={
                'db_table': 'e_transport',
            },
        ),
        migrations.CreateModel(
            name='EUsers',
            fields=[
                ('email', models.CharField(max_length=80, primary_key=True, serialize=False)),
                ('password', models.CharField(max_length=200)),
                ('mail', models.CharField(default='', max_length=200)),
                ('DiskUsage', models.CharField(default='0', max_length=200)),
                ('emailOwner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mailServer.domains')),
            ],
            options={
                'db_table': 'e_users',
            },
        ),
    ]
