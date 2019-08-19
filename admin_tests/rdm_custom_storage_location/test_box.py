from boxsdk.exception import BoxAPIException
from django.test import RequestFactory
from django.utils import timezone
import httplib
import json
from nose import tools as nt
import mock

from addons.osfstorage.models import Region
from admin.rdm_custom_storage_location import views
from tests.base import AdminTestCase
from osf.models.external import ExternalAccount, ExternalAccountTemporary
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
)


class TestFetchToken(AdminTestCase):
    def setUp(self):
        super(TestFetchToken, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.is_staff = True
        self.user.save()
        self.seed_data = {
            'provider_name': 'box',
            'oauth_key': 'pzN7NJr1EDzXDHsoZRqJT6jHVkt7ryhQbOzQjiduLmPw8CHs8lzrUBrBiztMQvxK5KLplhpKuGxeP91W',
            'oauth_secret': 'qgKnksgBkx76yCl9CqtTP4DOzPYiHLN9LSHFoVsgLgCc6ZqXngWMww5ydxrqY6OzyjUAcP5wL8c58D1Z',
            'expires_at': timezone.now(),
            'refresh_token': 'e97DkIMV6B0j6NjD1CYIiAm4',
            'date_last_refreshed': timezone.now(),
            'display_name': 'box display name is here',
            'profile_url': 'example.com',
            '_id': self.institution._id,
            'provider_id': '88080800880',
        }

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.FetchTemporaryTokenView.as_view()(request)

    def test_provider_missing(self):
        response = self.view_post({
            'no_pro': 'box',
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Provider is missing.', response.content)

    def test_fail_oauth_procedure_canceled(self):
        response = self.view_post({
            'provider_short_name': 'box',
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Oauth permission procedure was canceled', response.content)

    def test_success(self):
        temp_account = ExternalAccountTemporary.objects.create(
            provider=self.seed_data['provider_name'],
            provider_name=self.seed_data['provider_name'],
            oauth_key=self.seed_data['oauth_key'],
            oauth_secret=self.seed_data['oauth_secret'],
            expires_at=self.seed_data['expires_at'],
            refresh_token=self.seed_data['refresh_token'],
            date_last_refreshed=self.seed_data['date_last_refreshed'],
            display_name=self.seed_data['display_name'],
            profile_url=self.seed_data['profile_url'],
            _id=self.seed_data['_id'],
            provider_id=self.seed_data['provider_id'],
        )
        response = self.view_post({
            'provider_short_name': 'box',
        })
        nt.assert_equals(response.status_code, httplib.OK)
        data = json.loads(response.content)
        response_temp_account = data['response_data']
        nt.assert_equals(response_temp_account['display_name'], temp_account.display_name)
        nt.assert_equals(response_temp_account['oauth_key'], temp_account.oauth_key)
        nt.assert_equals(response_temp_account['provider'], temp_account.provider)
        nt.assert_equals(response_temp_account['provider_id'], temp_account.provider_id)
        nt.assert_equals(response_temp_account['provider_name'], temp_account.provider_name)
        nt.assert_equals(response_temp_account['fullname'], self.user.fullname)


class TestSaveCredentials(AdminTestCase):
    def setUp(self):
        super(TestSaveCredentials, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.is_staff = True
        self.user.save()
        self.seed_data = {
            'provider_name': 'box',
            'oauth_key': 'pzN7NJr1EDzXDHsoZRqJT6jHVkt7ryhQbOzQjiduLmPw8CHs8lzrUBrBiztMQvxK5KLplhpKuGxeP91W',
            'oauth_secret': 'qgKnksgBkx76yCl9CqtTP4DOzPYiHLN9LSHFoVsgLgCc6ZqXngWMww5ydxrqY6OzyjUAcP5wL8c58D1Z',
            'expires_at': timezone.now(),
            'refresh_token': 'e97DkIMV6B0j6NjD1CYIiAm4',
            'date_last_refreshed': timezone.now(),
            'display_name': 'box display name is here',
            'profile_url': 'example.com',
            '_id': self.institution._id,
            'provider_id': '88080800880',
        }

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.SaveCredentialsView.as_view()(request)

    def test_provider_missing(self):
        response = self.view_post({
            'no_pro': 'box',
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Provider is missing.', response.content)

    def test_storage_name_missing(self):
        response = self.view_post({
            'provider_short_name': 'box',
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Storage name is missing.', response.content)

    def test_folder_missing(self):
        response = self.view_post({
            'provider_short_name': 'box',
            'storage_name': 'storage_name',
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Folder ID is missing.', response.content)

    @mock.patch('boxsdk.Client.folder')
    def test_success(self, mock_folder):
        ExternalAccountTemporary.objects.create(
            provider=self.seed_data['provider_name'],
            provider_name=self.seed_data['provider_name'],
            oauth_key=self.seed_data['oauth_key'],
            oauth_secret=self.seed_data['oauth_secret'],
            expires_at=self.seed_data['expires_at'],
            refresh_token=self.seed_data['refresh_token'],
            date_last_refreshed=self.seed_data['date_last_refreshed'],
            display_name=self.seed_data['display_name'],
            profile_url=self.seed_data['profile_url'],
            _id=self.seed_data['_id'],
            provider_id=self.seed_data['provider_id'],
        )
        response = self.view_post({
            'provider_short_name': 'box',
            'storage_name': 'storage_name',
            'box_folder': '0',
        })
        nt.assert_equals(response.status_code, httplib.OK)
        nt.assert_in('OAuth was set successfully', response.content)

        external_account = ExternalAccount.objects.get(
            provider=self.seed_data['provider_name'], provider_id=self.seed_data['provider_id'])
        nt.assert_equals(external_account.oauth_key, self.seed_data['oauth_key'])
        nt.assert_equals(external_account.oauth_secret, self.seed_data['oauth_secret'])

        nt.assert_false(ExternalAccountTemporary.objects.filter(_id=self.institution._id))

        institution_storage = Region.objects.filter(_id=self.institution._id).first()
        nt.assert_is_not_none(institution_storage)
        nt.assert_equals(institution_storage.name, 'storage_name')

        wb_credentials = institution_storage.waterbutler_credentials
        nt.assert_equals(wb_credentials['storage']['token'], self.seed_data['oauth_key'])

        wb_settings = institution_storage.waterbutler_settings
        nt.assert_equals(wb_settings['storage']['folder'], '0')

    # Connection tests
    def test_folder_id_missing(self):
        response = self.view_post({
            'provider_short_name': 'box',
            'storage_name': 'Cardboard Box',
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Folder ID is missing.', response.content)

    def test_temporary_external_account_missing(self):
        response = self.view_post({
            'provider_short_name': 'box',
            'storage_name': 'Cardboard Box',
            'box_folder': '0'
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Oauth data was not found. Please reload the page and try again.', response.content)

    @mock.patch('boxsdk.Client.folder')
    def test_invalid_folder_id(self, mock_folder):
        mock_folder.side_effect = BoxAPIException('NG')

        ExternalAccountTemporary.objects.create(
            provider=self.seed_data['provider_name'],
            provider_name=self.seed_data['provider_name'],
            oauth_key=self.seed_data['oauth_key'],
            oauth_secret=self.seed_data['oauth_secret'],
            expires_at=self.seed_data['expires_at'],
            refresh_token=self.seed_data['refresh_token'],
            date_last_refreshed=self.seed_data['date_last_refreshed'],
            display_name=self.seed_data['display_name'],
            profile_url=self.seed_data['profile_url'],
            _id=self.seed_data['_id'],
            provider_id=self.seed_data['provider_id'],
        )
        response = self.view_post({
            'provider_short_name': 'box',
            'storage_name': 'Cardboard Box',
            'box_folder': 'invalid_folder_id'
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Invalid folder ID.', response.content)

    @mock.patch('boxsdk.Client.folder')
    def test_connection_success(self, mock_folder):
        ExternalAccountTemporary.objects.create(
            provider=self.seed_data['provider_name'],
            provider_name=self.seed_data['provider_name'],
            oauth_key=self.seed_data['oauth_key'],
            oauth_secret=self.seed_data['oauth_secret'],
            expires_at=self.seed_data['expires_at'],
            refresh_token=self.seed_data['refresh_token'],
            date_last_refreshed=self.seed_data['date_last_refreshed'],
            display_name=self.seed_data['display_name'],
            profile_url=self.seed_data['profile_url'],
            _id=self.seed_data['_id'],
            provider_id=self.seed_data['provider_id'],
        )
        response = self.view_post({
            'provider_short_name': 'box',
            'storage_name': 'Cardboard Box',
            'box_folder': 'Valid folder'
        })

        nt.assert_equals(response.status_code, httplib.OK)
        nt.assert_in('OAuth was set successfully', response.content)
