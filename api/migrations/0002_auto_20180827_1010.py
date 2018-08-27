# Generated by Django 2.1 on 2018-08-27 10:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='exchange',
            name='storage_exchange_id',
        ),
        migrations.AddField(
            model_name='exchange',
            name='api_url',
            field=models.CharField(max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='exchange',
            name='last_updated',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='exchange',
            name='logo',
            field=models.CharField(max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='exchange',
            name='top_pair',
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='exchange',
            name='top_pair_volume',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='exchange',
            name='url',
            field=models.CharField(max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='exchange',
            name='volume',
            field=models.FloatField(null=True),
        ),
        migrations.AlterField(
            model_name='exchange',
            name='enabled',
            field=models.BooleanField(blank=True, default=True),
        ),
        migrations.AlterField(
            model_name='exchangestatus',
            name='running',
            field=models.BooleanField(blank=True, default=False),
        ),
    ]
