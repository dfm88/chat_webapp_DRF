# Generated by Django 3.2.8 on 2022-03-02 15:42

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='membership',
            unique_together={('user', 'chatroom', 'date_joined'), ('user', 'chatroom', 'date_lefted')},
        ),
    ]
