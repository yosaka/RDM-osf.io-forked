# -*- coding: utf-8 -*-
# Generated by Django 1.11.28 on 2024-12-02 04:19
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import osf.models.base


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('addons_binderhub', '0002_custom_binderhubs'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServerAnnotation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('binderhub_url', models.TextField(blank=True, null=True)),
                ('jupyterhub_url', models.TextField(blank=True, null=True)),
                ('server_url', models.TextField()),
                ('name', models.TextField(blank=True)),
                ('memotext', models.TextField(blank=True)),
                ('node', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='osf.AbstractNode')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, osf.models.base.QuerySetExplainMixin),
        ),
    ]
