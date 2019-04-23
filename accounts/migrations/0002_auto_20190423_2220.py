# Generated by Django 2.1.5 on 2019-04-23 15:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='trello_board',
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name='profile',
            name='trello_key',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name='profile',
            name='trello_secret',
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
