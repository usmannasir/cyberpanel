# Generated by Django 3.1.3 on 2023-10-27 20:11

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CyberPanelCosmetic',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('MainDashboardCSS', models.TextField(default='')),
            ],
        ),
        migrations.CreateModel(
            name='version',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('currentVersion', models.CharField(max_length=50)),
                ('build', models.IntegerField()),
            ],
        ),
    ]
