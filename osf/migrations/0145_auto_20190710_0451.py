# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-07-10 04:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0144_merge_20190603_0456'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fileinfo',
            name='file_size',
            field=models.BigIntegerField(),
        ),
    ]
