# Generated by Django 2.2 on 2021-06-14 11:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_market_updated'),
    ]

    operations = [
        migrations.RenameField(
            model_name='exchange',
            old_name='last_updated',
            new_name='last_data_fetch',
        ),
    ]
