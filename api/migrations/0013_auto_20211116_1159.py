# Generated by Django 2.2 on 2021-11-16 11:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_auto_20210927_2148'),
    ]

    operations = [
        migrations.AlterField(
            model_name='market',
            name='base',
            field=models.CharField(max_length=32),
        ),
        migrations.AlterField(
            model_name='market',
            name='name',
            field=models.CharField(max_length=48),
        ),
        migrations.AlterField(
            model_name='market',
            name='quote',
            field=models.CharField(max_length=32),
        ),
    ]
