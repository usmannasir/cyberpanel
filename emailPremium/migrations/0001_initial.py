# Generated by Django 3.1.3 on 2023-10-27 20:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('mailServer', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailLogs',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('destination', models.CharField(max_length=200)),
                ('timeStamp', models.CharField(max_length=200)),
                ('email', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mailServer.eusers')),
            ],
        ),
        migrations.CreateModel(
            name='EmailLimits',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('limitStatus', models.IntegerField(default=0)),
                ('monthlyLimits', models.IntegerField(default=2000)),
                ('monthlyUsed', models.IntegerField(default=0)),
                ('hourlyLimit', models.IntegerField(default=50)),
                ('hourlyUsed', models.IntegerField(default=0)),
                ('emailLogs', models.IntegerField(default=0)),
                ('email', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mailServer.eusers')),
            ],
        ),
        migrations.CreateModel(
            name='DomainLimits',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('limitStatus', models.IntegerField(default=0)),
                ('monthlyLimit', models.IntegerField(default=10000)),
                ('monthlyUsed', models.IntegerField(default=0)),
                ('domain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mailServer.domains')),
            ],
        ),
    ]
