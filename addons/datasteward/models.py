# -*- coding: utf-8 -*-
from addons.base.models import (BaseUserSettings, )
from addons.datasteward.serializer import DataStewardSerializer
from django.db import models

_provider = 'datasteward'


class DataStewardProvider(object):
    """An alternative to `ExternalProvider` not tied to OAuth"""
    name = 'DataSteward'
    short_name = 'datasteward'
    serializer = DataStewardSerializer

    def __init__(self, account=None):
        super(DataStewardProvider, self).__init__()  # this does exactly nothing...
        # provide an unauthenticated session by default
        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.provider_id if self.account else 'anonymous'
        )


class UserSettings(BaseUserSettings):
    oauth_provider = DataStewardProvider
    serializer = DataStewardSerializer

    enabled = models.BooleanField(default=False)
