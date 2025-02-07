import copy
import json
import uuid

import mock
import pytest
import requests
from datetime import datetime, timezone, timedelta
from jsonschema import ValidationError, SchemaError
from mock import patch, MagicMock
from nose import tools as nt
from requests import ConnectionError, ReadTimeout, Timeout
from rest_framework import status

from addons.nextcloudinstitutions.models import NextcloudInstitutionsProvider
from admin.rdm_custom_storage_location.export_data import utils
from admin.rdm_custom_storage_location.export_data.views.restore import ProcessError
from framework.celery_tasks import app as celery_app
from osf.models import ExportData
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ExportDataLocationFactory,
    ExportDataFactory,
    ExportDataRestoreFactory,
)
from tests.base import AdminTestCase

FAKE_TASK_ID = '00000000-0000-0000-0000-000000000000'
RESTORE_EXPORT_DATA_PATH = 'admin.rdm_custom_storage_location.export_data.views.restore'
EXPORT_DATA_UTIL_PATH = 'admin.rdm_custom_storage_location.export_data.utils'
EXPORT_DATA_TASK_PATH = 'admin.rdm_custom_storage_location.tasks'
TEST_PROJECT_ID = 'test1'
TEST_PROVIDER = 'osfstorage'
institution_json = {
    'id': 99,
    'guid': 'inst99',
    'name': 'Testing University [Test]'
}
project_json = {
    'id': 'pj2t8',
    'name': 'project inst 001'
}
folder_1_json = {
    'path': '/6524c5572617af0d7c4d2ae3/',
    'materialized_path': '/chat/static/',
    'project': project_json
}
folder_2_json = {
    'path': '/6524c5562617af0d7c4d2adb/',
    'materialized_path': '/chat/templates/',
    'project': project_json
}
folders_json = [
    folder_1_json,
    folder_2_json
]
file_1_json = {
    'id': 36563,
    'path': '/6583fc9c7c76a00f81713f5d',
    'materialized_path': '/helloworld1.py',
    'name': 'helloworld1.py',
    'provider': 'osfstorage',
    'created_at': '2023-12-21 08:51:40',
    'modified_at': '2023-12-21 08:51:40',
    'project': project_json,
    'tags': [],
    'version': [
        {
            'identifier': '1',
            'created_at': '2023-12-21 08:51:40',
            'modified_at': '2023-12-21 08:51:40',
            'size': 1249,
            'version_name': 'helloworld1.py',
            'contributor': 'admin01_inst56@example.com.vn',
            'metadata': {
                'md5': 'd53e2699d9a615c4978fab6efada0f15',
                'etag': '35129ca0aee8d12e686f3bead7725379775b6a974eb10f60232a3b22ddcd30a1',
                'kind': 'file',
                'name': 'd71d0346be62dace293de7f972ec38e9acd2d470a9eb7de49f95aea90636d304',
                'path': '/d71d0346be62dace293de7f972ec38e9acd2d470a9eb7de49f95aea90636d304',
                'sha1': '06e59ccf4dc713bd48e4bea4686e052b6bc68e9d',
                'size': '1249',
                'extra': {
                    'md5': 'd53e2699d9a615c4978fab6efada0f15',
                    'encryption': ''
                },
                'sha256': 'd71d0346be62dace293de7f972ec38e9acd2d470a9eb7de49f95aea90636d304',
                'sha512': '860595ecf55a0e47e768073149bb12504c297fa41ebc35b8a1733b3c11ba57e7b41f53f76e860fb8b7910102f9880fe6d433b8abb83b99ad99a7f304e3669fbf',
                'sizeInt': 1249,
                'modified': 'Thu, 21 Dec 2023 08:51:40 GMT',
                'provider': 's3compat',
                'contentType': 'binary/octet-stream',
                'created_utc': None,
                'materialized': '/d71d0346be62dace293de7f972ec38e9acd2d470a9eb7de49f95aea90636d304',
                'modified_utc': '2023-12-21T08:51:40+00:00'
            },
            'location': {
                'nid': 'pj2t8',
                'host': '9a488c3f14b7',
                'bucket': 'grdm-ierae',
                'folder': '',
                'object': 'd71d0346be62dace293de7f972ec38e9acd2d470a9eb7de49f95aea90636d304',
                'address': None,
                'service': 's3compat',
                'version': '0.0.1',
                'provider': 's3compat',
                'encrypt_uploads': False
            }
        }
    ],
    'size': 1249,
    'location': {
        'nid': 'pj2t8',
        'host': '9a488c3f14b7',
        'bucket': 'grdm-ierae',
        'folder': '',
        'object': 'd71d0346be62dace293de7f972ec38e9acd2d470a9eb7de49f95aea90636d304',
        'address': None,
        'service': 's3compat',
        'version': '0.0.1',
        'provider': 's3compat',
        'encrypt_uploads': False
    },
    'timestamp': {
        'timestamp_id': 9814,
        'inspection_result_status': 1,
        'provider': 'osfstorage',
        'upload_file_modified_user': None,
        'project_id': 'pj2t8',
        'path': '/helloworld1.py',
        'key_file_name': 's4put_5da6fc68d3006db01238471e019d997b_pub.pem',
        'upload_file_created_user': 84,
        'upload_file_size': 1249,
        'verify_file_size': 1249,
        'verify_user': 84
    },
    'checkout_id': None
}
file_2_json = {
    'id': 36566,
    'path': '/658907b47c76a00f81714047',
    'materialized_path': '/blog/blog.py',
    'name': 'blog.py',
    'provider': 'osfstorage',
    'created_at': '2023-12-25 04:40:20',
    'modified_at': '2023-12-25 04:40:20',
    'project': project_json,
    'tags': [],
    'version': [
        {
            'identifier': '1',
            'created_at': '2023-12-25 04:40:20',
            'modified_at': '2023-12-25 04:40:20',
            'size': 10818,
            'version_name': 'blog.py',
            'contributor': 'admin01_inst56@example.com.vn',
            'metadata': {
                'md5': '3c99887c8cb4f33081570eac9703e500',
                'etag': '171acf637d5c7a92053fb73f297bf6918b39cf7ff89af0266bc9af67e31c173d',
                'kind': 'file',
                'name': '764976fccf6e20b40e3d3437dfdf2e955532f235945f08a9b7728fb823d0f582',
                'path': '/764976fccf6e20b40e3d3437dfdf2e955532f235945f08a9b7728fb823d0f582',
                'sha1': 'cac6bfc9badda593d9cc829d989273b6916f7f75',
                'size': '10818',
                'extra': {
                    'md5': '3c99887c8cb4f33081570eac9703e500',
                    'encryption': ''
                },
                'sha256': '764976fccf6e20b40e3d3437dfdf2e955532f235945f08a9b7728fb823d0f582',
                'sha512': '22f680b31f5a00845f9447b3ec6b591bd3f255632f6e58243bf978c3d7d358bb7cbec7dd5d5c02470b3b890c3e5d07b5e302d457ac86011e83f2acac550ec507',
                'sizeInt': 10818,
                'modified': 'Mon, 25 Dec 2023 04:40:20 GMT',
                'provider': 's3compat',
                'contentType': 'binary/octet-stream',
                'created_utc': None,
                'materialized': '/764976fccf6e20b40e3d3437dfdf2e955532f235945f08a9b7728fb823d0f582',
                'modified_utc': '2023-12-25T04:40:20+00:00'
            },
            'location': {
                'nid': 'pj2t8',
                'host': '9a488c3f14b7',
                'bucket': 'grdm-ierae',
                'folder': '',
                'object': '764976fccf6e20b40e3d3437dfdf2e955532f235945f08a9b7728fb823d0f582',
                'address': None,
                'service': 's3compat',
                'version': '0.0.1',
                'provider': 's3compat',
                'encrypt_uploads': False
            }
        }
    ],
    'size': 10818,
    'location': {
        'nid': 'pj2t8',
        'host': '9a488c3f14b7',
        'bucket': 'grdm-ierae',
        'folder': '',
        'object': '764976fccf6e20b40e3d3437dfdf2e955532f235945f08a9b7728fb823d0f582',
        'address': None,
        'service': 's3compat',
        'version': '0.0.1',
        'provider': 's3compat',
        'encrypt_uploads': False
    },
    'timestamp': {
        'timestamp_id': 9815,
        'inspection_result_status': 1,
        'provider': 'osfstorage',
        'upload_file_modified_user': None,
        'project_id': 'pj2t8',
        'path': '/blog/blog.py',
        'key_file_name': 's4put_5da6fc68d3006db01238471e019d997b_pub.pem',
        'upload_file_created_user': 84,
        'upload_file_size': 10818,
        'verify_file_size': 10818,
        'verify_user': 84
    },
    'checkout_id': None
}
file_3_json = {
    'id': 36569,
    'path': '/658907b97c76a00f81714065',
    'materialized_path': '/blog/docker-compose.yml',
    'name': 'docker-compose.yml',
    'provider': 'osfstorage',
    'created_at': '2023-12-25 04:40:25',
    'modified_at': '2023-12-25 04:40:25',
    'project': project_json,
    'tags': [],
    'version': [
        {
            'identifier': '1',
            'created_at': '2023-12-25 04:40:25',
            'modified_at': '2023-12-25 04:40:25',
            'size': 257,
            'version_name': 'docker-compose.yml',
            'contributor': 'admin01_inst56@example.com.vn',
            'metadata': {
                'md5': 'b898161e932e5edfe8512fb37484cc59',
                'etag': 'a373c77e8667f5b17f43662c3d2363d99d31e0d731617eddf68feadff9c45df5',
                'kind': 'file',
                'name': '962d811bd42bcce10da657af37c37fd19a39c8c82284d0544f4fde2b655720b1',
                'path': '/962d811bd42bcce10da657af37c37fd19a39c8c82284d0544f4fde2b655720b1',
                'sha1': '804711104e75bb0572444dd1550534e606dd4700',
                'size': '257',
                'extra': {
                    'md5': 'b898161e932e5edfe8512fb37484cc59',
                    'encryption': ''
                },
                'sha256': '962d811bd42bcce10da657af37c37fd19a39c8c82284d0544f4fde2b655720b1',
                'sha512': '89aa6cab81568eac435a6cfbfe4b452b8617f2d641b1fa05d640aa8cb819477b02150175d5b919708c2b5996f0c62a4d487fc71ec709d96872b75046155d7751',
                'sizeInt': 257,
                'modified': 'Mon, 25 Dec 2023 04:40:24 GMT',
                'provider': 's3compat',
                'contentType': 'binary/octet-stream',
                'created_utc': None,
                'materialized': '/962d811bd42bcce10da657af37c37fd19a39c8c82284d0544f4fde2b655720b1',
                'modified_utc': '2023-12-25T04:40:24+00:00'
            },
            'location': {
                'nid': 'pj2t8',
                'host': '9a488c3f14b7',
                'bucket': 'grdm-ierae',
                'folder': '',
                'object': '962d811bd42bcce10da657af37c37fd19a39c8c82284d0544f4fde2b655720b1',
                'address': None,
                'service': 's3compat',
                'version': '0.0.1',
                'provider': 's3compat',
                'encrypt_uploads': False
            }
        }
    ],
    'size': 257,
    'location': {
        'nid': 'pj2t8',
        'host': '9a488c3f14b7',
        'bucket': 'grdm-ierae',
        'folder': '',
        'object': '962d811bd42bcce10da657af37c37fd19a39c8c82284d0544f4fde2b655720b1',
        'address': None,
        'service': 's3compat',
        'version': '0.0.1',
        'provider': 's3compat',
        'encrypt_uploads': False
    },
    'timestamp': {
        'timestamp_id': 9816,
        'inspection_result_status': 1,
        'provider': 'osfstorage',
        'upload_file_modified_user': None,
        'project_id': 'pj2t8',
        'path': '/blog/docker-compose.yml',
        'key_file_name': 's4put_5da6fc68d3006db01238471e019d997b_pub.pem',
        'upload_file_created_user': 84,
        'upload_file_size': 257,
        'verify_file_size': 257,
        'verify_user': 84
    },
    'checkout_id': None
}
file_4_json = {
    'id': 36570,
    'path': '/658907bc7c76a00f81714073',
    'materialized_path': '/blog/Dockerfile',
    'name': 'Dockerfile',
    'provider': 'osfstorage',
    'created_at': '2023-12-25 04:40:28',
    'modified_at': '2023-12-25 04:40:28',
    'project': project_json,
    'tags': [],
    'version': [
        {
            'identifier': '1',
            'created_at': '2023-12-25 04:40:28',
            'modified_at': '2023-12-25 04:40:28',
            'size': 223,
            'version_name': 'Dockerfile',
            'contributor': 'admin01_inst56@example.com.vn',
            'metadata': {
                'md5': '32215d4817ec892d9fa6d0aa09032a54',
                'etag': 'f2d4608d7d8d20ecb1b63aa21a54b26e4962b978b276004c30680a472ec57cd4',
                'kind': 'file',
                'name': 'cc436ccb5614a4e083bfb9d5546a22c7e52ef49dc8bceb9c9693cdecb2e368e2',
                'path': '/cc436ccb5614a4e083bfb9d5546a22c7e52ef49dc8bceb9c9693cdecb2e368e2',
                'sha1': 'f7f251d7530254d168d6ec73525e31c649421666',
                'size': '223',
                'extra': {
                    'md5': '32215d4817ec892d9fa6d0aa09032a54',
                    'encryption': ''
                },
                'sha256': 'cc436ccb5614a4e083bfb9d5546a22c7e52ef49dc8bceb9c9693cdecb2e368e2',
                'sha512': '415eeaa4d2a51b690f962ab0667484a6cd773d3a4de85bff649597367ce9930a222199d2f13576d970efc907656477f823925ff13cd42049fafe455b1d2d24c8',
                'sizeInt': 223,
                'modified': 'Mon, 25 Dec 2023 04:40:28 GMT',
                'provider': 's3compat',
                'contentType': 'binary/octet-stream',
                'created_utc': None,
                'materialized': '/cc436ccb5614a4e083bfb9d5546a22c7e52ef49dc8bceb9c9693cdecb2e368e2',
                'modified_utc': '2023-12-25T04:40:28+00:00'
            },
            'location': {
                'nid': 'pj2t8',
                'host': '9a488c3f14b7',
                'bucket': 'grdm-ierae',
                'folder': '',
                'object': 'cc436ccb5614a4e083bfb9d5546a22c7e52ef49dc8bceb9c9693cdecb2e368e2',
                'address': None,
                'service': 's3compat',
                'version': '0.0.1',
                'provider': 's3compat',
                'encrypt_uploads': False
            }
        }
    ],
    'size': 223,
    'location': {
        'nid': 'pj2t8',
        'host': '9a488c3f14b7',
        'bucket': 'grdm-ierae',
        'folder': '',
        'object': 'cc436ccb5614a4e083bfb9d5546a22c7e52ef49dc8bceb9c9693cdecb2e368e2',
        'address': None,
        'service': 's3compat',
        'version': '0.0.1',
        'provider': 's3compat',
        'encrypt_uploads': False
    },
    'timestamp': {
        'timestamp_id': 9817,
        'inspection_result_status': 1,
        'provider': 'osfstorage',
        'upload_file_modified_user': None,
        'project_id': 'pj2t8',
        'path': '/blog/Dockerfile',
        'key_file_name': 's4put_5da6fc68d3006db01238471e019d997b_pub.pem',
        'upload_file_created_user': 84,
        'upload_file_size': 223,
        'verify_file_size': 223,
        'verify_user': 84
    },
    'checkout_id': None
}
# old file
file_5_json = {
    'id': 36583,
    'path': '/658907e07c76a00f81714129',
    'materialized_path': '/blog/static/blog.css',
    'name': 'blog.css',
    'provider': 'osfstorage',
    'created_at': '2022-11-25 04:41:04',
    'modified_at': '2022-11-25 04:41:04',
    'project': project_json,
    'tags': [],
    'version': [
        {
            'identifier': '1',
            'created_at': '2022-11-25 04:41:04',
            'modified_at': '2022-11-25 04:41:04',
            'size': 2283,
            'version_name': 'blog.css',
            'contributor': 'admin01_inst56@example.com.vn',
            'metadata': {
                'md5': 'bdbfbec057078db6331cc2a3fbf57418',
                'etag': '43c102afefd43175c21a5b4d8cdf35a8536a45989f50cc9bca91777b3e3fbbef',
                'kind': 'file',
                'name': '350526f64b1961da90e3bc04e12ac60dc973f74f7b92fcd351a5305501090f05',
                'path': '/350526f64b1961da90e3bc04e12ac60dc973f74f7b92fcd351a5305501090f05',
                'sha1': 'd4d21a67706d03d782090cbae6fe069a4c8761a4',
                'size': '2283',
                'extra': {
                    'md5': 'bdbfbec057078db6331cc2a3fbf57418',
                    'encryption': ''
                },
                'sha256': '350526f64b1961da90e3bc04e12ac60dc973f74f7b92fcd351a5305501090f05',
                'sizeInt': 2283,
                'modified': 'Mon, 25 Nov 2022 04:41:04 GMT',
                'provider': 's3compat',
                'contentType': 'binary/octet-stream',
                'created_utc': None,
                'materialized': '/350526f64b1961da90e3bc04e12ac60dc973f74f7b92fcd351a5305501090f05',
                'modified_utc': '2022-11-25T04:41:04+00:00'
            },
            'location': {
                'nid': 'pj2t8',
                'host': '9a488c3f14b7',
                'bucket': 'grdm-ierae',
                'folder': '',
                'object': '350526f64b1961da90e3bc04e12ac60dc973f74f7b92fcd351a5305501090f05',
                'address': None,
                'service': 's3compat',
                'version': '0.0.1',
                'provider': 's3compat',
                'encrypt_uploads': False
            }
        }
    ],
    'size': 2283,
    'location': {
        'nid': 'pj2t8',
        'host': '9a488c3f14b7',
        'bucket': 'grdm-ierae',
        'folder': '',
        'object': '350526f64b1961da90e3bc04e12ac60dc973f74f7b92fcd351a5305501090f05',
        'address': None,
        'service': 's3compat',
        'version': '0.0.1',
        'provider': 's3compat',
        'encrypt_uploads': False
    },
    'timestamp': {
        'timestamp_id': 9830,
        'inspection_result_status': 1,
        'provider': 'osfstorage',
        'upload_file_modified_user': None,
        'project_id': 'pj2t8',
        'path': '/blog/static/blog.css',
        'key_file_name': 's4put_5da6fc68d3006db01238471e019d997b_pub.pem',
        'upload_file_created_user': 84,
        'upload_file_size': 2283,
        'verify_file_size': 2283,
        'verify_user': 84
    },
    'checkout_id': None
}
FAKE_DATA = {
    'institution': institution_json,
    'folder': folders_json,
    'files': [
        file_1_json,
        file_2_json,
        file_3_json,
    ],
}
FAKE_DATA_NEW = {
    'institution': institution_json,
    'folder': folders_json,
    'files': [
        file_1_json,
        file_2_json,
        file_4_json,
    ]
}


def gen_file(file_id, version_n=1, **kwargs):
    datetime_format = '%Y-%m-%d %H:%M:%S'
    project_guid = kwargs.get('project_guid', 'prj01')
    project_name = kwargs.get('project_name', f'project {project_guid}')
    user_id = kwargs.get('user_id', 1)
    user_email = kwargs.get('user_email', 'user_ut@example.com.vn')
    file_name = kwargs.get('name', f'file_{file_id}.txt')
    file_tags = kwargs.get('tags', ['test', 'generated'])
    file_timestamp_id = kwargs.get('timestamp_id', file_id)
    wb_container_id = kwargs.get('wb_container_id', '9a488c3f14b7')
    location_provider = kwargs.get('location_provider', 's3compat')
    location_bucket = kwargs.get('location_bucket', 'grdm-ierae')

    file_path = f'/{uuid.uuid4().hex[:24]}'
    materialized_path = f'/{file_name}'

    project_uuid = uuid.uuid4().hex
    prj_json = {
        'id': project_guid,
        'name': project_name
    }

    version_list = []
    now = datetime.now(tz=timezone.utc)
    for i in range(version_n, 0, -1):
        created_at = now - timedelta(minutes=1)
        ver_size = 1200 + i
        ver_sha256 = uuid.uuid4().hex + uuid.uuid4().hex
        ver_md5 = uuid.uuid4().hex
        ver_sha1 = (uuid.uuid4().hex + uuid.uuid4().hex)[:40]
        ver_etag = uuid.uuid4().hex + uuid.uuid4().hex
        ver_sha512 = uuid.uuid4().hex + uuid.uuid4().hex + uuid.uuid4().hex + uuid.uuid4().hex
        ver_path = f'/{ver_sha256}'
        ver_json = {
            'identifier': str(i),
            'created_at': created_at.strftime(datetime_format),
            'modified_at': created_at.strftime(datetime_format),
            'size': ver_size,
            'version_name': file_name,
            'contributor': user_email,
            'metadata': {
                'md5': ver_md5,
                'etag': ver_etag,
                'kind': 'file',
                'name': ver_sha256,
                'path': ver_path,
                'sha1': ver_sha1,
                'size': str(ver_size),
                'extra': {
                    'md5': ver_md5,
                    'encryption': ''
                },
                'sha256': ver_sha256,
                'sha512': ver_sha512,
                'sizeInt': ver_size,
                'modified': created_at.strftime('%a, %d %b %Y %H:%M:%S %Z'),
                'provider': location_provider,
                'contentType': 'binary/octet-stream',
                'created_utc': None,
                'materialized': ver_path,
                'modified_utc': created_at.isoformat(timespec='seconds')
            },
            'location': {
                'nid': project_guid,
                'host': wb_container_id,
                'bucket': location_bucket,
                'folder': '',
                'object': ver_sha256,
                'address': None,
                'service': location_provider,
                'version': '0.0.1',
                'provider': location_provider,
                'encrypt_uploads': False
            }
        }
        version_list.append(ver_json)

    latest_version = version_list[0]
    first_version = version_list[-1]
    timestamp_json = {
        'timestamp_id': file_timestamp_id,
        'inspection_result_status': 1,
        'provider': 'osfstorage',
        'upload_file_modified_user': None,
        'project_id': project_guid,
        'path': materialized_path,
        'key_file_name': f'{project_guid}_{project_uuid}_pub.pem',
        'upload_file_created_user': user_id,
        'upload_file_size': latest_version['size'],
        'verify_file_size': latest_version['size'],
        'verify_user': user_id,
    }
    file_json = {
        'id': file_id,
        'path': file_path,
        'materialized_path': materialized_path,
        'name': latest_version['version_name'],
        'provider': 'osfstorage',
        'created_at': first_version['created_at'],
        'modified_at': latest_version['modified_at'],
        'project': prj_json,
        'tags': file_tags,
        'version': version_list,
        'size': latest_version['size'],
        'location': latest_version['location'],
        'timestamp': timestamp_json,
        'checkout_id': None,
    }
    return file_json


class FakeRes:
    def __init__(self, status_code):
        self.status_code = status_code

    def json(self):
        data = FAKE_DATA
        return data


def mock_check_not_aborted_task():
    return None


def mock_check_aborted_task():
    raise ProcessError('Mock test exception by aborting task')


def get_mock_get_file_data_response_addon_storage(*args, **kwargs):
    response_body = {'data': []}
    if args[2] == '/':
        response_body = {
            'data': [
                {
                    'attributes': {
                        'path': '/folder/',
                        'materialized': '/folder/',
                        'kind': 'folder'
                    }
                },
                {
                    'attributes': {
                        'path': '/file2.txt',
                        'materialized': '/file2.txt',
                        'kind': 'file'
                    }
                }
            ]
        }
    elif args[2] == '/folder/':
        response_body = {
            'data': [
                {
                    'attributes': {
                        'path': '/folder/file1.txt',
                        'materialized': '/folder/file1.txt',
                        'kind': 'file'
                    }
                }
            ]
        }
    elif args[2] == '/test_exception/':
        raise ConnectionError('Mock test connection error while getting file info')

    test_response = requests.Response()
    test_response.status_code = status.HTTP_200_OK if args[2] != '/test_error_response/' else status.HTTP_404_NOT_FOUND
    test_response._content = json.dumps(response_body).encode('utf-8')
    return test_response


def get_mock_file_data_response_bulk_mount(*args, **kwargs):
    if args[2] == '/':
        response_body = {
            'data': [
                {
                    'attributes': {
                        'path': '/fake_folder_id/',
                        'materialized': '/folder/',
                        'kind': 'folder'
                    }
                },
                {
                    'attributes': {
                        'path': '/fake_file2_id',
                        'materialized': '/file2.txt',
                        'kind': 'file'
                    }
                }
            ]
        }
    elif args[2] == '/fake_folder_id/':
        response_body = {
            'data': [
                {
                    'attributes': {
                        'path': '/fake_file1_id',
                        'materialized': '/folder/file1.txt',
                        'kind': 'file'
                    }
                }
            ]
        }

    test_response = requests.Response()
    test_response.status_code = status.HTTP_200_OK
    test_response._content = json.dumps(response_body).encode('utf-8')
    return test_response


@pytest.mark.feature_202210
class TestUtils(AdminTestCase):

    def setUp(self):
        self.institution = InstitutionFactory()

        self.access_key = 'access_key'
        self.secret_key = 'secret_key'
        self.bucket = 'mybucket'

        self.wb_credentials = {
            'storage': {
                'access_key': self.access_key,
                'secret_key': self.secret_key,
            }
        }

        self.wb_settings = {
            'storage': {
                'folder': '/code/website/osfstoragecache',
                'provider': 'filesystem',
            }
        }

    def test_write_json_file__successfully(self):
        mock_json_dump_patcher = mock.patch(f'{EXPORT_DATA_UTIL_PATH}.json.dump')
        json_data = {'json_data': 'json_data'}
        output_file = '_temp.json'

        mock_json_dump = mock_json_dump_patcher.start()

        utils.write_json_file(json_data, output_file)
        call_args = mock_json_dump.call_args
        mock_json_dump.assert_called()
        nt.assert_equal(call_args[0][0], json_data)
        nt.assert_equal(call_args[1], {'ensure_ascii': False, 'indent': 2, 'sort_keys': False})

        mock_json_dump_patcher.stop()

    def test_from_json__file_not_found(self):
        mock_json_dump_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.json.dump',
            side_effect=Exception()
        )
        json_data = {'json_data': 'json_data'}
        output_file = '_temp.json'

        mock_json_dump = mock_json_dump_patcher.start()
        with pytest.raises(Exception):
            utils.write_json_file(json_data, output_file)
        mock_json_dump.assert_called()

        mock_json_dump_patcher.stop()

    def test_update_storage_location__create_new(self):
        result = utils.update_storage_location(
            institution_guid=self.institution.guid,
            storage_name='testname',
            wb_credentials=self.wb_credentials,
            wb_settings=self.wb_settings,
        )
        nt.assert_equal(result.waterbutler_credentials, self.wb_credentials)
        nt.assert_equal(result.waterbutler_settings, self.wb_settings)
        nt.assert_equal(result.name, 'testname')

    def test_update_storage_location__update(self):
        ExportDataLocationFactory(
            institution_guid=self.institution.guid,
            name='testname',
            waterbutler_credentials={'storage': {}},
            waterbutler_settings={'storage': {}},
        )
        result = utils.update_storage_location(
            institution_guid=self.institution.guid,
            storage_name='testname',
            wb_credentials=self.wb_credentials,
            wb_settings=self.wb_settings,
        )
        nt.assert_not_equal(result.waterbutler_credentials, {'storage': {}})
        nt.assert_not_equal(result.waterbutler_settings, {'storage': {}})
        nt.assert_equal(result.waterbutler_credentials, self.wb_credentials)
        nt.assert_equal(result.waterbutler_settings, self.wb_settings)
        nt.assert_equal(result.name, 'testname')

    def test_test_dropboxbusiness_connection__no_option(self):
        mock_get_two_addon_options = mock.MagicMock(return_value=None)
        with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options', mock_get_two_addon_options):
            data, status_code = utils.test_dropboxbusiness_connection(self.institution)
            mock_get_two_addon_options.assert_called()
            nt.assert_equal(status_code, 400)
            nt.assert_true('message' in data)
            nt.assert_equal(data.get('message'), 'Invalid Institution ID.: {}'.format(self.institution.id))

    def test_test_dropboxbusiness_connection__no_token(self):
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=('apple', 'banana')
        )
        mock_addon_option_to_token_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.addon_option_to_token',
            return_value=None
        )

        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()
        mock_addon_option_to_token = mock_addon_option_to_token_patcher.start()

        data, status_code = utils.test_dropboxbusiness_connection(self.institution)
        mock_get_two_addon_options.assert_called()
        mock_addon_option_to_token.assert_called()
        nt.assert_equal(status_code, 400)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'No tokens.')

        mock_addon_option_to_token_patcher.stop()
        mock_get_two_addon_options_patcher.stop()

    def test_test_dropboxbusiness_connection__valid(self):
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=('apple', 'banana')
        )
        mock_addon_option_to_token_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.addon_option_to_token',
            return_value='token'
        )
        mock_TeamInfo_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.TeamInfo',
            return_value=True
        )

        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()
        mock_addon_option_to_token = mock_addon_option_to_token_patcher.start()
        mock_TeamInfo_patcher.start()

        data, status_code = utils.test_dropboxbusiness_connection(self.institution)
        mock_get_two_addon_options.assert_called()
        mock_addon_option_to_token.assert_called()
        nt.assert_equal(status_code, 200)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'Credentials are valid')

        mock_TeamInfo_patcher.stop()
        mock_addon_option_to_token_patcher.stop()
        mock_get_two_addon_options_patcher.stop()

    def test_test_dropboxbusiness_connection__invalid_token(self):
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=('apple', 'banana')
        )
        mock_addon_option_to_token_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.addon_option_to_token',
            return_value='token'
        )
        mock_TeamInfo_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.TeamInfo',
            side_effect=Exception()
        )

        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()
        mock_addon_option_to_token = mock_addon_option_to_token_patcher.start()
        mock_TeamInfo_patcher.start()

        data, status_code = utils.test_dropboxbusiness_connection(self.institution)
        mock_get_two_addon_options.assert_called()
        mock_addon_option_to_token.assert_called()
        nt.assert_equal(status_code, 400)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'Invalid tokens.')

        mock_TeamInfo_patcher.stop()
        mock_addon_option_to_token_patcher.stop()
        mock_get_two_addon_options_patcher.stop()

    def test_save_s3_credentials__error_connection(self):
        mock_test_s3_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_s3_connection',
            return_value=({'message': 'test'}, 400)
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )

        mock_test_s3_connection = mock_test_s3_connection_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_s3_credentials(
            institution_guid=self.institution.guid,
            storage_name='testname',
            access_key=self.access_key,
            secret_key=self.secret_key,
            bucket=self.bucket
        )
        mock_test_s3_connection.assert_called()
        mock_update_storage_location.assert_not_called()
        nt.assert_equal(data, {'message': 'test'})
        nt.assert_equal(status_code, 400)

        mock_test_s3_connection_patcher.stop()
        mock_update_storage_location_patcher.stop()

    def test_save_s3_credentials__successfully(self):
        mock_test_s3_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_s3_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )

        mock_test_s3_connection = mock_test_s3_connection_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_s3_credentials(
            institution_guid=self.institution.guid,
            storage_name='testname',
            access_key=self.access_key,
            secret_key=self.secret_key,
            bucket=self.bucket
        )
        mock_test_s3_connection.assert_called()
        mock_update_storage_location.assert_called()
        nt.assert_equal(data, {'message': 'Saved credentials successfully!!'})
        nt.assert_equal(status_code, 200)

        mock_test_s3_connection_patcher.stop()
        mock_update_storage_location_patcher.stop()

    def test_save_s3compat_credentials__error_connection(self):
        mock_test_s3compat_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_s3compat_connection',
            return_value=({'message': 'test'}, 400)
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )

        mock_test_s3compat_connection = mock_test_s3compat_connection_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_s3compat_credentials(
            institution_guid=self.institution.guid,
            storage_name='testname',
            host_url='http://host_url/',
            access_key=self.access_key,
            secret_key=self.secret_key,
            bucket=self.bucket
        )
        mock_test_s3compat_connection.assert_called()
        mock_update_storage_location.assert_not_called()
        nt.assert_equal(data, {'message': 'test'})
        nt.assert_equal(status_code, 400)

        mock_test_s3compat_connection_patcher.stop()
        mock_update_storage_location_patcher.stop()

    def test_save_s3compat_credentials__successfully(self):
        mock_test_s3compat_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_s3compat_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )

        mock_test_s3compat_connection = mock_test_s3compat_connection_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_s3compat_credentials(
            institution_guid=self.institution.guid,
            storage_name='testname',
            host_url='http://host_url/',
            access_key=self.access_key,
            secret_key=self.secret_key,
            bucket=self.bucket
        )
        mock_test_s3compat_connection.assert_called()
        mock_update_storage_location.assert_called()
        nt.assert_equal(data, {'message': 'Saved credentials successfully!!'})
        nt.assert_equal(status_code, 200)

        mock_test_s3compat_connection_patcher.stop()
        mock_update_storage_location_patcher.stop()

    def test_save_dropboxbusiness_credentials__error_connection(self):
        mock_test_dropboxbusiness_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_dropboxbusiness_connection',
            return_value=({'message': 'test'}, 400)
        )
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=None
        )

        mock_test_dropboxbusiness_connection = mock_test_dropboxbusiness_connection_patcher.start()
        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()

        data, status_code = utils.save_dropboxbusiness_credentials(
            institution=self.institution,
            storage_name='testname',
            provider_name='dropboxbusiness',
        )
        mock_test_dropboxbusiness_connection.assert_called()
        mock_get_two_addon_options.assert_not_called()
        nt.assert_equal(data, {'message': 'test'})
        nt.assert_equal(status_code, 400)

        mock_get_two_addon_options_patcher.stop()
        mock_test_dropboxbusiness_connection_patcher.stop()

    def test_save_dropboxbusiness_credentials__no_option(self):
        mock_test_dropboxbusiness_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_dropboxbusiness_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=None
        )

        mock_test_dropboxbusiness_connection = mock_test_dropboxbusiness_connection_patcher.start()
        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()

        ret = utils.save_dropboxbusiness_credentials(
            institution=self.institution,
            storage_name='testname',
            provider_name='dropboxbusiness',
        )
        mock_test_dropboxbusiness_connection.assert_called()
        mock_get_two_addon_options.assert_called()
        nt.assert_is_none(ret)

        mock_get_two_addon_options_patcher.stop()
        mock_test_dropboxbusiness_connection_patcher.stop()

    def test_save_dropboxbusiness_credentials__no_token(self):
        mock_test_dropboxbusiness_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_dropboxbusiness_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=('apple', 'banana')
        )
        mock_addon_option_to_token_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.addon_option_to_token',
            return_value=None
        )

        mock_test_dropboxbusiness_connection = mock_test_dropboxbusiness_connection_patcher.start()
        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()
        mock_addon_option_to_token = mock_addon_option_to_token_patcher.start()

        ret = utils.save_dropboxbusiness_credentials(
            institution=self.institution,
            storage_name='testname',
            provider_name='dropboxbusiness',
        )
        mock_test_dropboxbusiness_connection.assert_called()
        mock_get_two_addon_options.assert_called()
        mock_addon_option_to_token.assert_called()
        nt.assert_is_none(ret)

        mock_addon_option_to_token_patcher.stop()
        mock_get_two_addon_options_patcher.stop()
        mock_test_dropboxbusiness_connection_patcher.stop()

    def test_save_dropboxbusiness_credentials__valid(self):
        mock_test_dropboxbusiness_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_dropboxbusiness_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=(mock.MagicMock(), mock.MagicMock())
        )
        mock_addon_option_to_token_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.addon_option_to_token',
            return_value='token'
        )
        mock_TeamInfo_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.TeamInfo',
            return_value=mock.Mock(team_folders=mock.Mock(keys=mock.Mock(return_value=['team_folder_id'])))
        )
        mock_get_current_admin_group_and_sync_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_current_admin_group_and_sync',
            return_value=('admin_group', 'admin_dbmid_list')
        )

        mock_get_current_admin_dbmid_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_current_admin_dbmid',
            return_value='admin_dbmid'
        )
        mock_wd_info_for_institutions_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.wd_info_for_institutions',
            return_value=({}, {})
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )

        mock_test_dropboxbusiness_connection = mock_test_dropboxbusiness_connection_patcher.start()
        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()
        mock_addon_option_to_token = mock_addon_option_to_token_patcher.start()
        mock_TeamInfo_patcher.start()
        mock_get_current_admin_group_and_sync = mock_get_current_admin_group_and_sync_patcher.start()
        mock_get_current_admin_dbmid = mock_get_current_admin_dbmid_patcher.start()
        mock_wd_info_for_institutions = mock_wd_info_for_institutions_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_dropboxbusiness_credentials(
            institution=self.institution,
            storage_name='testname',
            provider_name='dropboxbusiness',
        )
        mock_test_dropboxbusiness_connection.assert_called()
        mock_get_two_addon_options.assert_called()
        mock_addon_option_to_token.assert_called()
        mock_get_current_admin_group_and_sync.assert_called()
        mock_get_current_admin_dbmid.assert_called()
        mock_wd_info_for_institutions.assert_called()
        mock_update_storage_location.assert_called()
        nt.assert_equal(status_code, 200)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'Dropbox Business was set successfully!!')

        mock_update_storage_location_patcher.stop()
        mock_wd_info_for_institutions_patcher.stop()
        mock_get_current_admin_dbmid_patcher.stop()
        mock_get_current_admin_group_and_sync_patcher.stop()
        mock_TeamInfo_patcher.stop()
        mock_addon_option_to_token_patcher.stop()
        mock_get_two_addon_options_patcher.stop()
        mock_test_dropboxbusiness_connection_patcher.stop()

    def test_save_dropboxbusiness_credentials__invalid_token(self):
        mock_test_dropboxbusiness_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_dropboxbusiness_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_get_two_addon_options_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.get_two_addon_options',
            return_value=('apple', 'banana')
        )
        mock_addon_option_to_token_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.addon_option_to_token',
            return_value='token'
        )
        mock_TeamInfo_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.dropboxbusiness_utils.TeamInfo',
            side_effect=Exception()
        )

        mock_test_dropboxbusiness_connection = mock_test_dropboxbusiness_connection_patcher.start()
        mock_get_two_addon_options = mock_get_two_addon_options_patcher.start()
        mock_addon_option_to_token = mock_addon_option_to_token_patcher.start()
        mock_TeamInfo_patcher.start()

        with pytest.raises(Exception):
            utils.save_dropboxbusiness_credentials(
                institution=self.institution,
                storage_name='testname',
                provider_name='dropboxbusiness',
            )
            mock_test_dropboxbusiness_connection.assert_called()
            mock_get_two_addon_options.assert_called()
            mock_addon_option_to_token.assert_called()

        mock_TeamInfo_patcher.stop()
        mock_addon_option_to_token_patcher.stop()
        mock_get_two_addon_options_patcher.stop()
        mock_test_dropboxbusiness_connection_patcher.stop()

    def test_save_basic_storage_institutions_credentials_common__no_extended_data(self):
        mock_wd_info_for_institutions_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.wd_info_for_institutions',
            return_value=({}, {})
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )
        provider = NextcloudInstitutionsProvider(username='username', password='password', host='host')

        mock_wd_info_for_institutions = mock_wd_info_for_institutions_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_basic_storage_institutions_credentials_common(
            institution=self.institution,
            storage_name='test_storage_name',
            folder='test_folder/',
            provider_name='test_provider_name',
            provider=provider,
        )
        mock_wd_info_for_institutions.assert_called()
        mock_update_storage_location.assert_called()
        nt.assert_equal(status_code, 200)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'Saved credentials successfully!!')

        mock_update_storage_location_patcher.stop()
        mock_wd_info_for_institutions_patcher.stop()

    def test_save_basic_storage_institutions_credentials_common__with_extended_data(self):
        mock_wd_info_for_institutions_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.wd_info_for_institutions',
            return_value=({}, {})
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )
        provider = NextcloudInstitutionsProvider(username='username', password='password', host='host')

        mock_wd_info_for_institutions = mock_wd_info_for_institutions_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_basic_storage_institutions_credentials_common(
            institution=self.institution,
            storage_name='test_storage_name',
            folder='test_folder/',
            provider_name='test_provider_name',
            provider=provider,
            extended_data={'year': 1964},
        )
        mock_wd_info_for_institutions.assert_called()
        mock_update_storage_location.assert_called()
        nt.assert_equal(status_code, 200)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'Saved credentials successfully!!')

        mock_update_storage_location_patcher.stop()
        mock_wd_info_for_institutions_patcher.stop()

    def test_save_nextcloudinstitutions_credentials__error_connection(self):
        mock_test_owncloud_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_owncloud_connection',
            return_value=({'message': 'test'}, 400)
        )
        mock_save_basic_storage_institutions_credentials_common_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.save_basic_storage_institutions_credentials_common',
            return_value=({'message': 'test'}, 400)
        )

        mock_test_owncloud_connection = mock_test_owncloud_connection_patcher.start()
        mock_save_basic_storage_institutions_credentials_common = mock_save_basic_storage_institutions_credentials_common_patcher.start()

        data, status_code = utils.save_nextcloudinstitutions_credentials(
            institution=self.institution,
            storage_name='test_storage_name',
            host_url='test_url',
            username='test_username',
            password='test_password',
            folder='test_folder/',
            notification_secret='not_secret',
            provider_name='nextcloudinstitutions',
        )
        mock_test_owncloud_connection.assert_called()
        mock_save_basic_storage_institutions_credentials_common.assert_not_called()
        nt.assert_equal(data, {'message': 'test'})
        nt.assert_equal(status_code, 400)

        mock_save_basic_storage_institutions_credentials_common_patcher.stop()
        mock_test_owncloud_connection_patcher.stop()

    def test_save_nextcloudinstitutions_credentials__successfully(self):
        mock_test_owncloud_connection_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.test_owncloud_connection',
            return_value=({'message': 'test'}, 200)
        )
        mock_wd_info_for_institutions_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.wd_info_for_institutions',
            return_value=({}, {})
        )
        mock_update_storage_location_patcher = mock.patch(
            f'{EXPORT_DATA_UTIL_PATH}.update_storage_location',
            return_value=None
        )

        mock_test_owncloud_connection = mock_test_owncloud_connection_patcher.start()
        mock_wd_info_for_institutions = mock_wd_info_for_institutions_patcher.start()
        mock_update_storage_location = mock_update_storage_location_patcher.start()

        data, status_code = utils.save_nextcloudinstitutions_credentials(
            institution=self.institution,
            storage_name='test_storage_name',
            host_url='test_url',
            username='test_username',
            password='test_password',
            folder='test_folder/',
            notification_secret='not_secret',
            provider_name='nextcloudinstitutions',
        )
        mock_test_owncloud_connection.assert_called()
        mock_wd_info_for_institutions.assert_called()
        mock_update_storage_location.assert_called()
        nt.assert_equal(status_code, 200)
        nt.assert_true('message' in data)
        nt.assert_equal(data.get('message'), 'Saved credentials successfully!!')

        mock_update_storage_location_patcher.stop()
        mock_wd_info_for_institutions_patcher.stop()
        mock_test_owncloud_connection_patcher.stop()

    def test_validate_exported_data(self):
        # not found schema
        with nt.assert_raises(FileNotFoundError):
            result = utils.validate_exported_data({}, 'fake-schema.json')
            nt.assert_is_none(result)

        # jsonschema.ValidationError: 'institution' is a required property
        result = utils.validate_exported_data({}, 'file-info-schema.json')
        nt.assert_false(result)

        # normal
        result = utils.validate_exported_data(FAKE_DATA, 'file-info-schema.json')
        nt.assert_true(result)

        # test file_5_json don't have sha512 in metadata
        FAKE_DATA['files'].append(file_5_json)
        result = utils.validate_exported_data(FAKE_DATA, 'file-info-schema.json')
        nt.assert_true(result)

    def test_validate_file_json(self):
        # not found schema
        with nt.assert_raises(FileNotFoundError):
            result = utils.validate_file_json({}, 'fake-schema.json')
            nt.assert_is_none(result)

        # jsonschema.ValidationError: 'institution' is a required property
        result = utils.validate_file_json({}, 'file-info-schema.json')
        nt.assert_false(result)

        # normal
        result = utils.validate_file_json(FAKE_DATA, 'file-info-schema.json')
        nt.assert_true(result)

        # test file_5_json don't have sha512 in metadata
        FAKE_DATA['files'].append(file_5_json)
        result = utils.validate_file_json(FAKE_DATA, 'file-info-schema.json')
        nt.assert_true(result)

    def test_count_file_ng_ok(self):
        # for check Export Data and check Restore Data
        # file_id=1~files_len
        files_len = 3
        files_old = [gen_file(i, version_n=5) for i in range(1, files_len + 1, 1)]
        # file_id=1~files_len+2
        files_new = files_old + [
            gen_file(files_len + 1, version_n=10),
            gen_file(files_len + 2, version_n=10),
        ]
        data_old = utils.process_data_information(files_old)
        data_new = utils.process_data_information(files_new)
        res = utils.count_files_ng_ok(data_new, data_old)
        # check properties
        nt.assert_in('ok', res)
        nt.assert_in('ng', res)
        nt.assert_in('total', res)
        nt.assert_in('list_file_ng', res)
        # check quantity
        nt.assert_equal(res['ok'] + res['ng'], res['total'])
        # taken all without limit on the NG file list
        nt.assert_equal(len(res['list_file_ng']), res['ng'])
        # check properties in each NG file item
        file_info = res['list_file_ng'][0]
        nt.assert_in('project_id', file_info)
        nt.assert_in('path', file_info)
        nt.assert_in('version_id', file_info)
        nt.assert_in('size', file_info)
        nt.assert_in('reason', file_info)

        # case of no change
        data_old = utils.process_data_information(files_old)
        data_new = utils.process_data_information(files_old)
        res = utils.count_files_ng_ok(data_new, data_old)
        # check quantity
        nt.assert_equal(res['ng'], 0)
        nt.assert_equal(len(res['list_file_ng']), res['ng'])
        nt.assert_equal(res['ok'], res['total'])

    def test_count_file_ng_ok__exclude_location(self):
        # file_id=1~files_len
        files_len = 3
        files_old = [gen_file(i, version_n=5) for i in range(1, files_len + 1, 1)]
        # simulate the case where the location is changed
        files_new = []
        for file_info in copy.deepcopy(files_old):
            version_list = file_info['version']
            latest_version = version_list[0]
            latest_ver_location = latest_version['location']
            # e.g. re-deploy WB server
            latest_ver_location['host'] = uuid.uuid4().hex[:12],
            # e.g. change only the bucket
            latest_ver_location['bucket'] = 'grdm-ierae-new',
            file_info['location'] = latest_version['location']
            files_new.append(file_info)

        data_old = utils.process_data_information(files_old)
        data_new = utils.process_data_information(files_new)
        res = utils.count_files_ng_ok(data_new, data_old)
        # check properties
        nt.assert_in('ok', res)
        nt.assert_in('ng', res)
        nt.assert_in('total', res)
        nt.assert_in('list_file_ng', res)
        # check quantity
        nt.assert_equal(res['ok'] + res['ng'], res['total'])
        # taken all without limit on the NG file list
        nt.assert_equal(len(res['list_file_ng']), res['ng'])
        # check properties in each NG file item
        file_info = res['list_file_ng'][0]
        nt.assert_in('project_id', file_info)
        nt.assert_in('path', file_info)
        nt.assert_in('version_id', file_info)
        nt.assert_in('size', file_info)
        nt.assert_in('reason', file_info)
        # check content in 'reason': '"location" not match'
        nt.assert_in('location', file_info['reason'])
        nt.assert_in('" not match', file_info['reason'])

        # case of excluding 'location'
        exclude_keys = ['location']
        res = utils.count_files_ng_ok(data_new, data_old, exclude_keys=exclude_keys)
        nt.assert_equal(res['ng'], 0)
        nt.assert_equal(len(res['list_file_ng']), res['ng'])
        nt.assert_equal(res['ok'], res['total'])

    def test_count_file_ng_ok__same_files_in_other_projects(self):
        # project_id=prj01 file_id=1~files_len
        # project_id=prj02 file_id=1~files_len
        files_len = 3
        files_old = [
            gen_file(i, version_n=3, project_guid='prj01',)
            for i in range(1, files_len + 1, 1)] + [
            gen_file(i, version_n=3, project_guid='prj02',)
            for i in range(1, files_len + 1, 1)]
        # file_id=1~files_len+1
        files_new = files_old + [
            gen_file(files_len + 1, version_n=10, project_guid='prj02')
        ]

        data_old = utils.process_data_information(files_old)
        data_new = utils.process_data_information(files_new)
        res = utils.count_files_ng_ok(data_new, data_old)
        print(f'res={res}')

        # check properties
        nt.assert_in('ok', res)
        nt.assert_in('ng', res)
        nt.assert_in('total', res)
        nt.assert_in('list_file_ng', res)

        # check quantity
        nt.assert_equal(res['ok'] + res['ng'], res['total'])
        # taken all without limit on the NG file list
        nt.assert_equal(len(res['list_file_ng']), res['ng'])

        # check properties in each NG file item
        file_info = res['list_file_ng'][0]
        nt.assert_in('project_id', file_info)
        nt.assert_in('path', file_info)
        nt.assert_in('version_id', file_info)
        nt.assert_in('size', file_info)
        nt.assert_in('reason', file_info)

        # check content in 'reason': '"...project..." not match'
        nt.assert_not_in('project', file_info['reason'])
        nt.assert_not_in('" not match', file_info['reason'])


@pytest.mark.feature_202210
class TestUtilsForExportData(AdminTestCase):
    def setUp(self):
        super(TestUtilsForExportData, self).setUp()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.institution = InstitutionFactory()
        self.export_data = ExportDataFactory()

    def test_validate_exported_data(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.return_value = None

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                result = utils.validate_exported_data({}, 'file-info-schema.json')
                mock_from_json.assert_called()
                mock_validate.assert_called()
                nt.assert_true(result)

    def test_validate_exported_data_validation_error(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.side_effect = ValidationError(f'Mock test jsonschema.ValidationError')

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                result = utils.validate_exported_data({}, 'file-info-schema.json')
                mock_from_json.assert_called()
                mock_validate.assert_called()
                nt.assert_false(result)

    def test_validate_exported_data_other_error(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.side_effect = FileNotFoundError(f'Mock test jsonschema.SchemaError')

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                with nt.assert_raises(FileNotFoundError):
                    result = utils.validate_exported_data({}, 'fake-schema.json')
                    mock_from_json.assert_called()
                    mock_validate.assert_called()
                    nt.assert_is_none(result)

    def test_check_diff(self):
        a_standard = {
            'section1': {
                'category1': 1,
                'category2': 2
            },
            'section2': {
                'category1': 1,
                'category2': 2
            }

        }
        a_new = {
            'section1': {
                'category1': 1,
                'category2': 2
            },
            'section2': {
                'category1': 1,
                'category2': 3
            }

        }
        utils.deep_diff(a_new, a_standard, exclude_keys=['section1', 'section2'])

    def test_check_diff_epsilon(self):
        res = utils.deep_diff(1.2, 2.1, parent_key='section1', epsilon_keys=['section1', 'section2'])
        nt.assert_equal(res, None)

    def test_check_diff_between_list_flip(self):
        a_standard = [
            {
                'category1': 1,
                'category2': 1
            },
            {
                'category1': 2,
                'category2': 1
            },
            {
                'category1': 1,
                'category2': 2
            }
        ]
        a_new = [
            {
                'category1': 1,
                'category2': 2
            },
            {
                'category1': 1,
                'category2': 3
            }
        ]
        res = utils.deep_diff(a_standard, a_new, exclude_keys=['section1', 'section2'])
        nt.assert_not_equal(res, None)

    def test_check_diff_between_list_not_flip(self):
        a_standard = [
            {
                'category1': 1,
                'category2': 1
            },
            {
                'category1': 2,
                'category2': 1
            },
            {
                'category1': 1,
                'category2': 2
            }
        ]
        a_new = [
            {
                'category1': 1,
                'category2': 2
            },
            {
                'category1': 1,
                'category2': 3
            }
        ]
        res = utils.deep_diff(a_new, a_standard, exclude_keys=['section1', 'section2'])
        nt.assert_not_equal(res, None)

    def test_type_dict(self):
        a_standard = {
            'section1': {
                'category1': 1,
                'category2': 2
            },
            'section2': {
                'category1': 1,
                'category2': 2
            }

        }
        a_new = {
            'section3': {
                'category1': 1,
                'category2': 2
            },
            'section4': {
                'category1': 1,
                'category2': 3
            }

        }
        res = utils.deep_diff(a_new, a_standard, exclude_keys=['section1', 'section2'])
        nt.assert_not_equal(res, None)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_check_for_file_existent_on_export_location(self, mock_get_file_data):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        response_body = {
            'data': [
                {
                    'id': '1',
                    'attributes': {
                        'name': '10a14359db515c709492b51cff52feaad4783c166ba9ad34fb03e74be1924c4d',
                        'size': 8,
                    }
                }
            ]
        }
        test_response._content = json.dumps(response_body).encode('utf-8')
        mock_get_file_data.return_value = test_response

        file_json = {
            'files': [
                {
                    'materialized_path': '/test_path/file1.txt',
                    'version': [
                        {
                            'version_name': 'file1.txt',
                            'size': 10,
                            'identifier': 1,
                            'metadata': {
                                'md5': '9193f63d5939cfbb102e677ca717465d',
                                'sha256': '10a14359db515c709492b51cff52feaad4783c166ba9ad34fb03e74be1924c4d'
                            }
                        }
                    ]
                },
                {
                    'materialized_path': '/test_path/file2.txt',
                    'version': [
                        {
                            'version_name': 'file2.txt',
                            'size': 20,
                            'identifier': 1,
                            'metadata': {
                                'md5': '273604bfeef7126abe1f9bff1e45126c',
                                'sha256': '19ad8d7393d45c3a124d2e9bb5111412973a16fb3d24a0aa378bcd410c33fd3f'
                            }
                        }
                    ]
                }
            ]
        }
        result = utils.check_for_file_existent_on_export_location(file_json, TEST_PROJECT_ID, TEST_PROVIDER, '/test/', None, None, None)
        expected_result = [
            {
                'path': '/test_path/file2.txt',
                'size': 20,
                'version_id': 1,
                'reason': 'File does not exist on the Export Storage Location',
            }
        ]
        nt.assert_equal(result, expected_result)


@pytest.mark.feature_202210
class TestUtilsForCheckRestoreData(AdminTestCase):
    def setUp(self):
        super(TestUtilsForCheckRestoreData, self).setUp()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.institution = InstitutionFactory()
        self.export_data = ExportDataFactory()
        self.export_data_restore = ExportDataRestoreFactory()
        self.export_data_restore.export = self.export_data

    def test_count_file_ng_ok(self):
        data_old = utils.process_data_information(FAKE_DATA['files'])
        data_new = utils.process_data_information(FAKE_DATA_NEW['files'])
        rs = utils.count_files_ng_ok(data_new, data_old)
        nt.assert_greater(rs['ng'], 0)

    def test_check_diff(self):
        a_standard = {
            'section1': {
                'category1': 1,
                'category2': 2
            },
            'section2': {
                'category1': 1,
                'category2': 2
            }

        }
        a_new = {
            'section1': {
                'category1': 1,
                'category2': 2
            },
            'section2': {
                'category1': 1,
                'category2': 3
            }

        }
        utils.deep_diff(a_new, a_standard, exclude_keys=['section1', 'section2'])

    def test_check_diff_epsilon(self):
        res = utils.deep_diff(1.2, 2.1, parent_key='section1', epsilon_keys=['section1', 'section2'])
        nt.assert_equal(res, None)

    def test_check_diff_between_list_flip(self):
        a_standard = [
            {
                'category1': 1,
                'category2': 1
            },
            {
                'category1': 2,
                'category2': 1
            },
            {
                'category1': 1,
                'category2': 2
            }
        ]
        a_new = [
            {
                'category1': 1,
                'category2': 2
            },
            {
                'category1': 1,
                'category2': 3
            }
        ]
        res = utils.deep_diff(a_standard, a_new, exclude_keys=['section1', 'section2'])
        nt.assert_not_equal(res, None)

    def test_check_diff_between_list_not_flip(self):
        a_standard = [
            {
                'category1': 1,
                'category2': 1
            },
            {
                'category1': 2,
                'category2': 1
            },
            {
                'category1': 1,
                'category2': 2
            }
        ]
        a_new = [
            {
                'category1': 1,
                'category2': 2
            },
            {
                'category1': 1,
                'category2': 3
            }
        ]
        res = utils.deep_diff(a_new, a_standard, exclude_keys=['section1', 'section2'])
        nt.assert_not_equal(res, None)

    def test_check_diff_between_dict(self):
        a_standard = {
            'section1': {
                'category1': 1,
                'category2': 2
            },
            'section2': {
                'category1': 1,
                'category2': 2
            }

        }
        a_new = {
            'section3': {
                'category1': 1,
                'category2': 2
            },
            'section4': {
                'category1': 1,
                'category2': 3
            }

        }
        res = utils.deep_diff(a_new, a_standard, exclude_keys=['section1', 'section2'])
        nt.assert_not_equal(res, None)


@pytest.mark.feature_202210
class TestUtilsForRestoreData(AdminTestCase):
    def setUp(self):
        celery_app.conf.update({
            'task_always_eager': False,
            'task_eager_propagates': False,
        })
        self.export_data = ExportDataFactory()
        self.export_data_restore = ExportDataRestoreFactory(status=ExportData.STATUS_RUNNING)
        self.export_data_restore.destination.waterbutler_settings['storage']['provider'] = 'dropboxbusiness'
        self.export_data_restore.destination.save()
        self.destination_id = self.export_data_restore.destination.id

    # check_for_any_running_restore_process
    def test_check_for_any_running_restore_process_true_result(self):
        result = utils.check_for_any_running_restore_process(self.destination_id)
        nt.assert_equal(result, True)

    def test_check_for_any_running_restore_process_false_result(self):
        result = utils.check_for_any_running_restore_process(-1)
        nt.assert_equal(result, False)

    # validate_file_json
    def test_validate_file_json(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.return_value = None

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                result = utils.validate_file_json({}, 'file-info-schema.json')
                mock_from_json.assert_called()
                mock_validate.assert_called()
                nt.assert_true(result)

    def test_validate_file_json_validation_error(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.side_effect = ValidationError(f'Mock test jsonschema.ValidationError')

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                result = utils.validate_file_json({}, 'file-info-schema.json')
                mock_from_json.assert_called()
                mock_validate.assert_called()
                nt.assert_false(result)

    def test_validate_file_json_schema_error(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.side_effect = SchemaError(f'Mock test jsonschema.SchemaError')

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                result = utils.validate_file_json({}, 'file-info-schema.json')
                mock_from_json.assert_called()
                mock_validate.assert_called()
                nt.assert_false(result)

    def test_validate_file_json_other_error(self):
        mock_from_json = MagicMock()
        mock_from_json.return_value = {}
        mock_validate = MagicMock()
        mock_validate.side_effect = FileNotFoundError(f'Mock test jsonschema.SchemaError')

        with patch(f'{EXPORT_DATA_UTIL_PATH}.from_json', mock_from_json):
            with patch(f'jsonschema.validate', mock_validate):
                with nt.assert_raises(FileNotFoundError):
                    result = utils.validate_file_json({}, 'fake-schema.json')
                    mock_from_json.assert_called()
                    mock_validate.assert_called()
                    nt.assert_is_none(result)

    # get_file_data
    def test_get_file_data(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get = MagicMock()
        mock_get.return_value = test_response
        with patch('requests.get', mock_get):
            response = utils.get_file_data(TEST_PROJECT_ID, TEST_PROVIDER, '/test/file.txt', None)
            mock_get.assert_called()
            nt.assert_equal(response.content, b'{}')
            nt.assert_equal(response.status_code, status.HTTP_200_OK)

    def test_get_file_data_info(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = {}

        mock_get = MagicMock()
        mock_get.return_value = test_response
        with patch('requests.get', mock_get):
            response = utils.get_file_data(TEST_PROJECT_ID, TEST_PROVIDER, '/test/file.txt', None,
                                           get_file_info=True)
            mock_get.assert_called()
            nt.assert_equal(response.content, {})
            nt.assert_equal(response.status_code, status.HTTP_200_OK)

    def test_get_file_data_with_version(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get = MagicMock()
        mock_get.return_value = test_response
        with patch('requests.get', mock_get):
            response = utils.get_file_data(TEST_PROJECT_ID, TEST_PROVIDER, '/test/file.txt', None, version=2)
            mock_get.assert_called()
            nt.assert_equal(response.content, b'{}')
            nt.assert_equal(response.status_code, status.HTTP_200_OK)

    def test_get_file_data_from_export_data(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get = MagicMock()
        mock_get.return_value = test_response
        with patch('requests.get', mock_get):
            response = utils.get_file_data(ExportData.EXPORT_DATA_FAKE_NODE_ID, TEST_PROVIDER, '/test/file.txt',
                                           None,
                                           location_id=self.export_data.location.id)
            mock_get.assert_called()
            nt.assert_equal(response.content, b'{}')
            nt.assert_equal(response.status_code, status.HTTP_200_OK)

    # get_files_in_path
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_get_files_in_path__response_empty(self, mock_get_file_data):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            response_body = {
                'data': []
            }
            test_response.status_code = status.HTTP_200_OK
            test_response._content = json.dumps(response_body).encode('utf-8')
            return test_response

        mock_get_file_data.side_effect = get_data_by_file_or_folder

        result = utils.get_files_in_path(ExportData.EXPORT_DATA_FAKE_NODE_ID, TEST_PROVIDER, '/test/',
                                         None)
        mock_get_file_data.assert_called()
        nt.assert_equal(result, [])

    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_get_files_in_path__response_error(self, mock_get_file_data):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            test_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            test_response._content = b'Mock test response error when move file'
            return test_response

        mock_get_file_data.side_effect = get_data_by_file_or_folder

        result = utils.get_files_in_path(ExportData.EXPORT_DATA_FAKE_NODE_ID, TEST_PROVIDER, '/test/',
                                         None)
        mock_get_file_data.assert_called()
        nt.assert_equal(result, [])

    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_get_files_in_path__addon_no_max_keys(self, mock_get_file_data):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            response_body = {
                'data': [{
                    'attributes': {
                        'path': '/folder/',
                        'materialized': '/folder/'
                    }
                }]
            }
            test_response.status_code = status.HTTP_200_OK
            test_response._content = json.dumps(response_body).encode('utf-8')
            return test_response

        mock_get_file_data.side_effect = get_data_by_file_or_folder

        result = utils.get_files_in_path(ExportData.EXPORT_DATA_FAKE_NODE_ID, TEST_PROVIDER, '/test/',
                                         None)
        mock_get_file_data.assert_called()
        nt.assert_equal(result, [{
            'attributes': {
                'path': '/folder/',
                'materialized': '/folder/'
            }
        }])

    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_get_files_in_path__next_token(self, mock_get_file_data):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            response_body = {
                'data': [{
                    'attributes': {
                        'path': '/folder/',
                        'materialized': '/folder/'
                    }
                }],
                'next_token': '/folder 1/'
            }
            if 'next_token' in kwargs and kwargs['next_token'] == '/folder 1/':
                response_body = {
                    'data': [{
                        'attributes': {
                            'path': '/folder 1/',
                            'materialized': '/folder 1/'
                        }
                    }],
                    'next_token': None
                }
            test_response.status_code = status.HTTP_200_OK
            test_response._content = json.dumps(response_body).encode('utf-8')
            return test_response

        mock_get_file_data.side_effect = get_data_by_file_or_folder

        result = utils.get_files_in_path(ExportData.EXPORT_DATA_FAKE_NODE_ID, 's3compat', '/test/',
                                         None)
        mock_get_file_data.assert_called()
        nt.assert_equal(result, [{
            'attributes': {
                'path': '/folder/',
                'materialized': '/folder/'
            }
        }, {
            'attributes': {
                'path': '/folder 1/',
                'materialized': '/folder 1/'
            }
        }])

    # create_folder
    def test_create_folder(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_201_CREATED
        test_response._content = json.dumps({}).encode('utf-8')

        mock_put = MagicMock()
        mock_put.return_value = test_response
        with patch('requests.put', mock_put):
            response_body, status_code = utils.create_folder(TEST_PROJECT_ID, TEST_PROVIDER, '/', 'test/', None)
            nt.assert_equal(response_body, {})
            nt.assert_equal(status_code, status.HTTP_201_CREATED)

    def test_create_folder_failed(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_409_CONFLICT

        mock_put = MagicMock()
        mock_put.return_value = test_response
        with patch('requests.put', mock_put):
            response_body, status_code = utils.create_folder(TEST_PROJECT_ID, TEST_PROVIDER, '/', 'test/', None)
            nt.assert_is_none(response_body)
            nt.assert_equal(status_code, status.HTTP_409_CONFLICT)

    def test_create_folder_exception(self):
        mock_put = MagicMock()
        mock_put.side_effect = ConnectionError('Mock test in create folder on storage')
        with patch('requests.put', mock_put):
            response_body, status_code = utils.create_folder(TEST_PROJECT_ID, TEST_PROVIDER, '/', 'test/', None)
            nt.assert_is_none(response_body)
            nt.assert_is_none(status_code)

    # upload_file
    def test_upload_file(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_201_CREATED
        test_response._content = json.dumps({}).encode('utf-8')

        mock_put = MagicMock()
        mock_put.return_value = test_response
        with patch('requests.put', mock_put):
            response_body, status_code = utils.upload_file(TEST_PROJECT_ID, TEST_PROVIDER, '/', {}, 'test.txt',
                                                           None)
            nt.assert_equal(response_body, {})
            nt.assert_equal(status_code, status.HTTP_201_CREATED)

    def test_upload_file_failed(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_409_CONFLICT

        mock_put = MagicMock()
        mock_put.return_value = test_response
        with patch('requests.put', mock_put):
            response_body, status_code = utils.upload_file(TEST_PROJECT_ID, TEST_PROVIDER, '/', {}, 'test.txt',
                                                           None)
            nt.assert_is_none(response_body)
            nt.assert_equal(status_code, status.HTTP_409_CONFLICT)

    def test_upload_file_exception(self):
        mock_put = MagicMock()
        mock_put.side_effect = ConnectionError('Mock test in upload file on storage')

        with patch('requests.put', mock_put):
            response_body, status_code = utils.upload_file(TEST_PROJECT_ID, TEST_PROVIDER, '/', {}, 'test.txt',
                                                           None)
            nt.assert_is_none(response_body)
            nt.assert_is_none(status_code)

    # update_existing_file
    def test_update_existing_file(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_put = MagicMock()
        mock_put.return_value = test_response
        with patch('requests.put', mock_put):
            response_body, status_code = utils.update_existing_file(TEST_PROJECT_ID, TEST_PROVIDER, '/', {},
                                                                    'test.txt',
                                                                    None)
            nt.assert_equal(response_body, {})
            nt.assert_equal(status_code, status.HTTP_200_OK)

    def test_update_existing_file_failed(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_404_NOT_FOUND

        mock_put = MagicMock()
        mock_put.return_value = test_response
        with patch('requests.put', mock_put):
            response_body, status_code = utils.update_existing_file(TEST_PROJECT_ID, TEST_PROVIDER, '/', {},
                                                                    'test.txt',
                                                                    None)
            nt.assert_is_none(response_body)
            nt.assert_equal(status_code, status.HTTP_404_NOT_FOUND)

    def test_update_existing_file_exception(self):
        mock_put = MagicMock()
        mock_put.side_effect = ConnectionError('Mock test in update existing file on storage')

        with patch('requests.put', mock_put):
            response_body, status_code = utils.update_existing_file(TEST_PROJECT_ID, TEST_PROVIDER, '/', {},
                                                                    'test.txt',
                                                                    None)
            nt.assert_is_none(response_body)
            nt.assert_is_none(status_code)

    # create_folder_path
    def test_create_folder_path_invalid_folder_path(self):
        response = utils.create_folder_path(TEST_PROJECT_ID, self.export_data_restore.destination, '/folder', None)
        nt.assert_equal(response, None)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_create_folder_path_create_folders(self, mock_get_file_data, mock_create_folder):
        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get_file_data.return_value = test_response
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)

        response = utils.create_folder_path(TEST_PROJECT_ID, self.export_data_restore.destination, '/folder/', None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        nt.assert_equal(response, None)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_create_folder_path_failed_to_get_folder_info(self, mock_get_file_data, mock_create_folder):
        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }
        test_not_found_response = requests.Response()
        test_not_found_response.status_code = status.HTTP_404_NOT_FOUND

        mock_get_file_data.return_value = test_not_found_response
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)

        response = utils.create_folder_path(TEST_PROJECT_ID, self.export_data_restore.destination, '/folder/', None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        nt.assert_equal(response, None)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_create_folder_path_no_match_folder_info(self, mock_get_file_data, mock_create_folder):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            if args[2] == '/':
                response_body = {
                    'data': [{
                        'attributes': {
                            'path': '/folder2/',
                            'materialized': '/folder2/'
                        }
                    }]
                }
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps(response_body).encode('utf-8')
            else:
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps({}).encode('utf-8')
            return test_response

        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        mock_get_file_data.side_effect = get_data_by_file_or_folder
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)

        response = utils.create_folder_path(TEST_PROJECT_ID, self.export_data_restore.destination, '/folder/', None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        nt.assert_equal(response, None)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_create_folder_path_create_folder_with_existing_folder(self, mock_get_file_data, mock_create_folder):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            if args[2] == '/':
                response_body = {
                    'data': [{
                        'attributes': {
                            'path': '/folder/',
                            'materialized': '/folder/'
                        }
                    }]
                }
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps(response_body).encode('utf-8')
            else:
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps({}).encode('utf-8')
            return test_response

        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        mock_get_file_data.side_effect = get_data_by_file_or_folder
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)

        response = utils.create_folder_path(TEST_PROJECT_ID, self.export_data_restore.destination, '/folder/', None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_not_called()
        nt.assert_equal(response, None)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_create_folder_path_failed_to_create_folder(self, mock_get_file_data, mock_create_folder):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get_file_data.return_value = test_response
        mock_create_folder.return_value = (None, status.HTTP_400_BAD_REQUEST)

        response = utils.create_folder_path(TEST_PROJECT_ID, self.export_data_restore.destination, '/folder/', None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        nt.assert_equal(response, None)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_create_folder_path__ignore_for_bulk_mount_method(self, mock_get_file_data, mock_create_folder):
        self.export_data_restore.destination.waterbutler_settings['storage']['provider'] = TEST_PROVIDER
        self.export_data_restore.destination.save()
        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)

        response = utils.create_folder_path(TEST_PROJECT_ID, self.export_data_restore.destination, '/folder/', None)
        mock_get_file_data.assert_not_called()
        mock_create_folder.assert_called()
        nt.assert_equal(response, None)

    # upload_file_path
    def test_upload_file_path_invalid_file_path(self):
        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/', {}, None)
        nt.assert_equal(response, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.upload_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_upload_file_path_create_folders_and_file(self, mock_get_file_data, mock_create_folder, mock_upload_file):
        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get_file_data.return_value = test_response
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_upload_file.return_value = ({}, status.HTTP_200_OK)

        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file.txt', {},
                                          None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        mock_upload_file.assert_called()
        nt.assert_equal(response, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.upload_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_upload_file_path_failed_to_get_folder_info(self, mock_get_file_data, mock_create_folder, mock_upload_file):
        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }
        test_not_found_response = requests.Response()
        test_not_found_response.status_code = status.HTTP_404_NOT_FOUND

        mock_get_file_data.return_value = test_not_found_response
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_upload_file.return_value = ({}, status.HTTP_200_OK)

        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file.txt', {},
                                          None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        mock_upload_file.assert_called()
        nt.assert_equal(response, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.upload_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_upload_file_path_no_match_folder_info(self, mock_get_file_data, mock_create_folder, mock_upload_file):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            if args[2] == '/':
                response_body = {
                    'data': [{
                        'attributes': {
                            'path': '/folder2/',
                            'materialized': '/folder2/'
                        }
                    }]
                }
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps(response_body).encode('utf-8')
            else:
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps({}).encode('utf-8')
            return test_response

        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        mock_get_file_data.side_effect = get_data_by_file_or_folder
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_upload_file.return_value = ({}, status.HTTP_200_OK)

        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file.txt', {},
                                          None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        mock_upload_file.assert_called()
        nt.assert_equal(response, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.upload_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_upload_file_path_create_file_with_existing_folder(self, mock_get_file_data, mock_create_folder, mock_upload_file):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            if args[2] == '/':
                response_body = {
                    'data': [{
                        'attributes': {
                            'path': '/folder/',
                            'materialized': '/folder/'
                        }
                    }]
                }
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps(response_body).encode('utf-8')
            else:
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps({}).encode('utf-8')
            return test_response

        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        mock_get_file_data.side_effect = get_data_by_file_or_folder
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_upload_file.return_value = ({}, status.HTTP_200_OK)

        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file.txt', {},
                                          None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_not_called()
        mock_upload_file.assert_called()
        nt.assert_equal(response, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.update_existing_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.upload_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_upload_file_path_update_file(self, mock_get_file_data, mock_create_folder, mock_upload_file, mock_update_file):
        def get_data_by_file_or_folder(*args, **kwargs):
            test_response = requests.Response()
            if args[2] == '/':
                response_body = {
                    'data': [{
                        'attributes': {
                            'path': '/folder/',
                            'materialized': '/folder/'
                        }
                    }]
                }
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps(response_body).encode('utf-8')
            else:
                test_response.status_code = status.HTTP_200_OK
                test_response._content = json.dumps({
                    'data': [{
                        'attributes': {
                            'path': '/folder/file.txt',
                            'materialized': '/folder/file.txt'
                        }
                    }]
                }).encode('utf-8')
            return test_response

        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        update_file_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/file.txt',
                    'materialized': '/folder/file.txt'
                }
            }
        }

        mock_get_file_data.side_effect = get_data_by_file_or_folder
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_upload_file.return_value = ({}, status.HTTP_200_OK)
        mock_update_file.return_value = (update_file_response_body, status.HTTP_200_OK)

        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file.txt', {},
                                          None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_not_called()
        mock_update_file.assert_called()
        mock_upload_file.assert_not_called()
        nt.assert_equal(response, update_file_response_body)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.upload_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_upload_file_path_failed_to_create_folder(self, mock_get_file_data, mock_create_folder, mock_upload_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get_file_data.return_value = test_response
        mock_create_folder.return_value = (None, status.HTTP_400_BAD_REQUEST)
        mock_upload_file.return_value = ({}, status.HTTP_200_OK)

        response = utils.upload_file_path(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file.txt', {},
                                          None)
        mock_get_file_data.assert_called()
        mock_create_folder.assert_called()
        mock_upload_file.assert_not_called()
        nt.assert_equal(response, {})

    # copy_file_to_other_storage
    def test_copy_file_to_other_storage(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_201_CREATED
        test_response._content = json.dumps({}).encode('utf-8')

        mock_post = MagicMock()
        mock_post.return_value = test_response
        with patch('requests.post', mock_post):
            response_body = utils.copy_file_to_other_storage(self.export_data, TEST_PROJECT_ID, TEST_PROVIDER, '/test.txt', '/', 'test.txt',
                                                                          None)
            nt.assert_equal(response_body, {})

    def test_copy_file_to_other_storage_failed(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_409_CONFLICT

        mock_post = MagicMock()
        mock_post.return_value = test_response
        with patch('requests.post', mock_post):
            response_body = utils.copy_file_to_other_storage(self.export_data, TEST_PROJECT_ID, TEST_PROVIDER, '/test.txt', '/', 'test.txt',
                                                                          None)
            nt.assert_is_none(response_body)

    def test_copy_file_to_other_storage_exception(self):
        mock_post = MagicMock()
        mock_post.side_effect = Exception('test_copy_file_to_other_storage_exception')

        with patch('requests.post', mock_post):
            response_body = utils.copy_file_to_other_storage(
                self.export_data, TEST_PROJECT_ID, TEST_PROVIDER,
                '/test.txt', '/', 'test.txt',
                None)
            nt.assert_is_none(response_body)

    def test_copy_file_to_other_storage_exception_timeout(self):
        mock_post = MagicMock()
        mock_post.side_effect = ConnectionError('test_copy_file_to_other_storage_exception')
        with patch('requests.post', mock_post):
            response_body = utils.copy_file_to_other_storage(
                self.export_data, TEST_PROJECT_ID, TEST_PROVIDER,
                '/test.txt', '/', 'test.txt',
                None)
            nt.assert_is_none(response_body)

        mock_post = MagicMock()
        mock_post.side_effect = Timeout('test_copy_file_to_other_storage_exception')
        with patch('requests.post', mock_post):
            response_body = utils.copy_file_to_other_storage(
                self.export_data, TEST_PROJECT_ID, TEST_PROVIDER,
                '/test.txt', '/', 'test.txt',
                None)
            nt.assert_is_none(response_body)

        mock_post = MagicMock()
        mock_post.side_effect = ReadTimeout('test_copy_file_to_other_storage_exception')
        with patch('requests.post', mock_post):
            response_body = utils.copy_file_to_other_storage(
                self.export_data, TEST_PROJECT_ID, TEST_PROVIDER,
                '/test.txt', '/', 'test.txt',
                None)
            nt.assert_is_none(response_body)

    # copy_file_from_location_to_destination
    def test_copy_file_from_location_to_destination_invalid_file_path(self):
        response = utils.copy_file_from_location_to_destination(
            self.export_data, TEST_PROJECT_ID, TEST_PROVIDER,
            '/folder/',
            '/', None)
        nt.assert_equal(response, None)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_to_other_storage')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_files_in_path')
    def test_copy_file_from_location_to_destination_create_folders_and_file(
            self, mock_get_files_in_path, mock_create_folder, mock_copy_file):
        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        mock_get_files_in_path.return_value = []
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_copy_file.return_value = {}

        response = utils.copy_file_from_location_to_destination(
            self.export_data, TEST_PROJECT_ID, TEST_PROVIDER,
            '/folder/file.txt',
            '/folder/file.txt', None)
        mock_get_files_in_path.assert_called()
        mock_create_folder.assert_called()
        mock_copy_file.assert_called()
        nt.assert_equal(response, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_to_other_storage')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_files_in_path')
    def test_copy_file_from_location_to_destination_failed_to_get_folder_info(
            self, mock_get_files_in_path, mock_create_folder, mock_copy_file):
        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        mock_get_files_in_path.return_value = []
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_copy_file.return_value = {}

        response = utils.copy_file_from_location_to_destination(
            self.export_data, TEST_PROJECT_ID, TEST_PROVIDER,
            '/folder/file.txt',
            '/folder/file.txt',
            None)
        mock_get_files_in_path.assert_called()
        mock_create_folder.assert_called()
        mock_copy_file.assert_called()
        nt.assert_equal(response, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_to_other_storage')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_files_in_path')
    def test_copy_file_from_location_to_destination_no_match_folder_info(
            self, mock_get_files_in_path, mock_create_folder, mock_copy_file):
        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        mock_get_files_in_path.return_value = [{
            'attributes': {
                'path': '/folder2/',
                'materialized': '/folder2/'
            }
        }]
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_copy_file.return_value = {}

        response = utils.copy_file_from_location_to_destination(
            self.export_data, TEST_PROJECT_ID, TEST_PROVIDER,
            '/folder/file.txt',
            '/folder/file.txt',
            None)
        mock_get_files_in_path.assert_called()
        mock_create_folder.assert_called()
        mock_copy_file.assert_called()
        nt.assert_equal(response, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_to_other_storage')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_files_in_path')
    def test_copy_file_from_location_to_destination_success(
            self, mock_get_files_in_path, mock_create_folder, mock_copy_file):
        create_folder_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/',
                    'materialized': '/folder/'
                }
            }
        }

        copy_file_response_body = {
            'data': {
                'attributes': {
                    'path': '/folder/file.txt',
                    'materialized': '/folder/file.txt'
                }
            }
        }

        mock_get_files_in_path.return_value = [{
            'attributes': {
                'path': '/folder/',
                'materialized': '/folder/'
            }
        }]
        mock_create_folder.return_value = (create_folder_response_body, status.HTTP_200_OK)
        mock_copy_file.return_value = copy_file_response_body

        response = utils.copy_file_from_location_to_destination(
            self.export_data, TEST_PROJECT_ID, TEST_PROVIDER,
            '/folder/file.txt',
            '/folder/file.txt',
            None)
        mock_get_files_in_path.assert_called()
        mock_create_folder.assert_not_called()
        mock_copy_file.assert_called()
        nt.assert_equal(response, copy_file_response_body)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_to_other_storage')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_files_in_path')
    def test_copy_file_from_location_to_destination_failed_to_create_folder(
            self, mock_get_files_in_path, mock_create_folder, mock_copy_file):
        mock_get_files_in_path.return_value = []
        mock_create_folder.return_value = (None, status.HTTP_400_BAD_REQUEST)
        mock_copy_file.return_value = {}

        response = utils.copy_file_from_location_to_destination(
            self.export_data, TEST_PROJECT_ID, TEST_PROVIDER,
            '/folder/file.txt',
            '/folder/file.txt',
            None)
        mock_get_files_in_path.assert_called()
        mock_create_folder.assert_called()
        mock_copy_file.assert_not_called()
        nt.assert_equal(response, None)

    # move_file
    def test_move_file_in_addon_storage(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_post = MagicMock()
        mock_post.return_value = test_response
        with patch('requests.post', mock_post):
            response = utils.move_file(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file1.txt',
                                       '/backup/folder/file1.txt',
                                       None, is_addon_storage=True)
            nt.assert_equal(response.status_code, status.HTTP_200_OK)
            nt.assert_is_none(response.content)

    def test_move_file_in_bulk_mount_storage(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_post = MagicMock()
        mock_post.return_value = test_response
        with patch('requests.post', mock_post):
            response = utils.move_file(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/', '/hash_backup_folder_id/',
                                       None,
                                       is_addon_storage=False)
            nt.assert_equal(response.status_code, status.HTTP_200_OK)
            nt.assert_is_none(response.content)

    def test_move_file_exception(self):
        mock_post = MagicMock()
        mock_post.side_effect = ConnectionError('Mock test exception for moving folder or file')
        with patch('requests.post', mock_post):
            with nt.assert_raises(ConnectionError):
                response = utils.move_file(TEST_PROJECT_ID, TEST_PROVIDER, '/folder/file1.txt',
                                           '/backup/folder/file1.txt',
                                           None, is_addon_storage=True)
                nt.assert_is_none(response)

    # move_addon_folder_to_backup
    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_to_backup_success(self, mock_get_all_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_paths.return_value = (['/folder/test1.txt'], [])
        mock_move_file.return_value = test_response
        mock_delete_paths.return_value = None

        result = utils.move_addon_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                   self.export_data_restore.process_start_timestamp,
                                                   None)
        mock_get_all_paths.assert_called()
        mock_move_file.assert_called()
        mock_delete_paths.assert_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_to_backup_aborted(self, mock_get_all_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_paths.return_value = (['/folder/test1.txt'], [])
        mock_move_file.return_value = test_response
        mock_delete_paths.return_value = None

        with nt.assert_raises(ProcessError):
            result = utils.move_addon_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                       self.export_data_restore.process_start_timestamp,
                                                       None,
                                                       check_abort_task=mock_check_aborted_task)
            mock_get_all_paths.assert_called()
            mock_move_file.assert_not_called()
            mock_delete_paths.assert_not_called()
            nt.assert_is_none(result)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_to_backup_empty_path_list(self, mock_get_all_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_paths.return_value = ([], [])
        mock_move_file.return_value = test_response
        mock_delete_paths.return_value = None

        result = utils.move_addon_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                   self.export_data_restore.process_start_timestamp,
                                                   None)
        mock_get_all_paths.assert_called()
        mock_move_file.assert_not_called()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_to_backup_move_files_error(self, mock_get_all_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        test_response._content = b'Mock test response error when move file'

        mock_get_all_paths.return_value = (['/folder/test1.txt'], [])
        mock_move_file.return_value = test_response
        mock_delete_paths.return_value = None

        result = utils.move_addon_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                   self.export_data_restore.process_start_timestamp,
                                                   None,
                                                   check_abort_task=mock_check_not_aborted_task)
        mock_get_all_paths.assert_called()
        mock_move_file.assert_called()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result,
                        {'error': f'{status.HTTP_500_INTERNAL_SERVER_ERROR} - {test_response.content}'})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_to_backup_exception(self, mock_get_all_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        test_response._content = b'Mock test response error when move file.'

        mock_get_all_paths.return_value = (['/folder/test1.txt'], [])
        mock_move_file.side_effect = Exception(f'Mock test exception when move file')
        mock_delete_paths.return_value = None

        result = utils.move_addon_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                   self.export_data_restore.process_start_timestamp,
                                                   None,
                                                   check_abort_task=mock_check_not_aborted_task)
        mock_get_all_paths.assert_called()
        mock_move_file.assert_called()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {'error': repr(Exception('Mock test exception when move file'))})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_to_backup_exception_and_aborted(self, mock_get_all_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        test_response._content = b'Mock test response error when move file'

        mock_get_all_paths.return_value = (['/folder/test1.txt'], [])
        mock_move_file.side_effect = Exception('Mock test exception when move file')
        mock_delete_paths.return_value = None

        with nt.assert_raises(ProcessError):
            result = utils.move_addon_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                       self.export_data_restore.process_start_timestamp,
                                                       None,
                                                       check_abort_task=mock_check_aborted_task)
            mock_get_all_paths.assert_called()
            mock_move_file.assert_called()
            mock_delete_paths.assert_not_called()
            nt.assert_is_none(result)

    # get_all_file_paths_in_addon_storage
    def test_get_all_file_paths_in_addon_storage(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, ['/folder/file1.txt', '/file2.txt'])
            nt.assert_equal(root_child_folders, ['/folder/'])

    def test_get_all_file_paths_in_addon_storage_exclude_path(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/', None,
                                                                                           exclude_path_regex='^\\/folder\\/.*$')
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, ['/file2.txt'])
            nt.assert_equal(root_child_folders, [])

    def test_get_all_file_paths_in_addon_storage_include_path(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/', None,
                                                                                           include_path_regex='^\\/folder\\/.*$')
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, ['/folder/file1.txt'])
            nt.assert_equal(root_child_folders, ['/folder/'])

    def test_get_all_file_paths_in_addon_storage_response_error(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/test_error_response/',
                                                                                           None)
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, [])
            nt.assert_equal(root_child_folders, [])

    def test_get_all_file_paths_in_addon_storage_empty_path(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/empty_path/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, ['/empty_path/'])
            nt.assert_equal(root_child_folders, [])

    def test_get_all_file_paths_in_addon_storage_invalid_regex(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/', None,
                                                                                           exclude_path_regex='\\/folder_[0-9]++\\/.*')
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, [])
            nt.assert_equal(root_child_folders, [])

    def test_get_all_file_paths_in_addon_storage_exception(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage

        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            list_file_path, root_child_folders = utils.get_all_file_paths_in_addon_storage(TEST_PROJECT_ID,
                                                                                           TEST_PROVIDER,
                                                                                           '/test_exception/',
                                                                                           None)
            mock_get_file_data.assert_called()
            nt.assert_equal(list_file_path, [])
            nt.assert_equal(root_child_folders, [])

    # move_bulk_mount_folder_to_backup
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_success(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_child_paths.return_value = [('/fake_hashed_path/', '/folder/')], []
        create_folder_response = {
            'data': {
                'attributes': {
                    'path': '/fake_hashed_path/'
                }
            }
        }
        mock_create_folder.return_value = create_folder_response, status.HTTP_201_CREATED
        mock_move_file.return_value = test_response

        result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                        self.export_data_restore.process_start_timestamp,
                                                        None)
        mock_get_all_child_paths.assert_called()
        mock_create_folder.assert_called()
        mock_move_file.assert_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_empty_path_list(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        create_folder_response = {
            'data': {
                'attributes': {
                    'path': '/fake_hashed_path/'
                }
            }
        }

        mock_get_all_child_paths.return_value = [], []
        mock_create_folder.return_value = create_folder_response, status.HTTP_201_CREATED
        mock_move_file.return_value = test_response

        result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                        self.export_data_restore.process_start_timestamp,
                                                        None)
        mock_get_all_child_paths.assert_called()
        mock_create_folder.assert_not_called()
        mock_move_file.assert_not_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_abort_while_creating_folder(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_process_error = ProcessError('Mock test exception by aborting task')
        create_folder_response = {
            'data': {
                'attributes': {
                    'path': '/fake_hashed_path/'
                }
            }
        }

        mock_get_all_child_paths.return_value = [('/fake_hashed_path/', '/folder/')], []
        mock_create_folder.return_value = create_folder_response, status.HTTP_201_CREATED
        mock_move_file.return_value = test_response

        result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                        self.export_data_restore.process_start_timestamp,
                                                        None,
                                                        check_abort_task=mock_check_aborted_task)
        mock_get_all_child_paths.assert_called()
        mock_create_folder.assert_not_called()
        mock_move_file.assert_not_called()
        nt.assert_equal(result, {'error': repr(test_process_error)})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_abort_while_moving_file(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        create_folder_response = {
            'data': {
                'attributes': {
                    'path': '/fake_hashed_path/'
                }
            }
        }

        abort_flag = False

        def side_effect_after_create_folder(*args, **kwargs):
            nonlocal abort_flag
            abort_flag = True
            return create_folder_response, status.HTTP_201_CREATED

        def mock_check_task():
            if abort_flag:
                mock_check_aborted_task()
            else:
                mock_check_not_aborted_task()

        mock_get_all_child_paths.return_value = [('/fake_hashed_path/', '/folder/')], []
        mock_create_folder.side_effect = side_effect_after_create_folder
        mock_move_file.return_value = test_response

        with nt.assert_raises(ProcessError):
            result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                            self.export_data_restore.process_start_timestamp,
                                                            None,
                                                            check_abort_task=mock_check_task)
            mock_get_all_child_paths.assert_called()
            mock_create_folder.assert_called()
            mock_move_file.assert_not_called()
            nt.assert_is_none(result)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_response_error_while_creating_folder(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_child_paths.return_value = [('/fake_hashed_path/', '/folder/')], []
        mock_create_folder.return_value = {}, status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_move_file.return_value = test_response

        result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                        self.export_data_restore.process_start_timestamp,
                                                        None)
        mock_get_all_child_paths.assert_called()
        mock_create_folder.assert_called()
        mock_move_file.assert_not_called()
        nt.assert_equal(result, {'error': 'Cannot create backup folder'})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_response_error_while_moving_file(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        test_response._content = b'Mock test response error when move file'
        create_folder_response = {
            'data': {
                'attributes': {
                    'path': '/fake_hashed_path/'
                }
            }
        }

        mock_get_all_child_paths.return_value = [('/fake_hashed_path/', '/folder/')], []
        mock_create_folder.return_value = create_folder_response, status.HTTP_201_CREATED
        mock_move_file.return_value = test_response

        result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                        self.export_data_restore.process_start_timestamp,
                                                        None)
        mock_get_all_child_paths.assert_called()
        mock_create_folder.assert_called()
        mock_move_file.assert_called()
        nt.assert_equal(result,
                        {'error': f'{status.HTTP_500_INTERNAL_SERVER_ERROR} - {test_response.content}'})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_to_backup_exception_while_moving_file(self, mock_get_all_child_paths, mock_create_folder, mock_move_file):
        connection_error = ConnectionError(f'Mock test exception while moving file')

        create_folder_response = {
            'data': {
                'attributes': {
                    'path': '/fake_hashed_path/'
                }
            }
        }

        mock_get_all_child_paths.return_value = [('/fake_hashed_path/', '/folder/')], []
        mock_create_folder.return_value = create_folder_response, status.HTTP_201_CREATED
        mock_move_file.side_effect = connection_error

        result = utils.move_bulk_mount_folder_to_backup(TEST_PROJECT_ID, TEST_PROVIDER,
                                                        self.export_data_restore.process_start_timestamp,
                                                        None)
        mock_get_all_child_paths.assert_called()
        mock_create_folder.assert_called()
        mock_move_file.assert_called()
        nt.assert_equal(result, {'error': repr(connection_error)})

    # get_all_child_paths_in_bulk_mount_storage
    def test_get_all_child_paths_in_bulk_mount_storage_invalid_path(self):
        mock_get_file_data = MagicMock()
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/file.txt', None)
            mock_get_file_data.assert_not_called()
            nt.assert_equal(path_list, [])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_at_root(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [('/fake_folder_id/', '/folder/'), ('/fake_file2_id', '/file2.txt')])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_at_root_child_folder(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/folder/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [('/fake_file1_id', '/folder/file1.txt')])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_response_error(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        test_response._content = json.dumps({}).encode('utf-8')

        mock_get_file_data = MagicMock()
        mock_get_file_data.return_value = test_response
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/test_error_response/',
                                                                                        None)
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_exception(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = ConnectionError('Mock test connection error while getting file info')
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/test_exception/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_exclude_path(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/', None,
                                                                                        exclude_path_regex='^\\/folder\\/$')
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [('/fake_file2_id', '/file2.txt')])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_and_get_encrypted_path_from_args(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/folder/', None,
                                                                                        get_path_from='/folder/')
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [('/fake_file1_id', '/folder/file1.txt')])
            nt.assert_equal(path_from_args, '/fake_folder_id/')

    def test_get_all_child_paths_in_bulk_mount_storage_non_existing_data_in_root_child_folder(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/folder3/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_non_existing_data_in_deepest_folder(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/folder/folder4/', None)
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [])
            nt.assert_is_none(path_from_args)

    def test_get_all_child_paths_in_bulk_mount_storage_invalid_exclude_regex(self):
        mock_get_file_data = MagicMock()
        mock_get_file_data.side_effect = get_mock_file_data_response_bulk_mount
        with patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data', mock_get_file_data):
            path_list, path_from_args = utils.get_all_child_paths_in_bulk_mount_storage(TEST_PROJECT_ID,
                                                                                        TEST_PROVIDER,
                                                                                        '/', None,
                                                                                        exclude_path_regex='^\\/folder_[0-9]++\\/$')
            mock_get_file_data.assert_called()
            nt.assert_equal(path_list, [])
            nt.assert_is_none(path_from_args)

    # move_addon_folder_from_backup
    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_from_backup(self, mock_get_all_file_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_file_paths.return_value = (['/backup_2022101010/folder/file1.txt', '/file2.txt'],
                                                ['/backup_2022101010/'])
        mock_move_file.return_value = test_response
        result = utils.move_addon_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_file_paths.assert_called_once()
        mock_move_file.assert_called_once()
        mock_delete_paths.assert_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_from_backup_empty_path_list(self, mock_get_all_file_paths, mock_move_file,
                                                           mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_file_paths.return_value = ([], [])
        mock_move_file.return_value = test_response
        result = utils.move_addon_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_file_paths.assert_called_once()
        mock_move_file.assert_not_called()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_from_backup_response_error(self, mock_get_all_file_paths, mock_move_file,
                                                          mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_403_FORBIDDEN
        test_response._content = b'Mock test error response while moving file'

        mock_get_all_file_paths.return_value = (['/backup_2022101010/folder/file1.txt', '/file2.txt'],
                                                ['/backup_2022101010/'])
        mock_move_file.return_value = test_response
        result = utils.move_addon_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_file_paths.assert_called_once()
        mock_move_file.assert_called_once()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {'error': f'{status.HTTP_403_FORBIDDEN} - {test_response.content}'})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_from_backup_exception(self, mock_get_all_file_paths, mock_move_file, mock_delete_paths):
        connection_error = ConnectionError('Mock test exception while moving file')

        mock_get_all_file_paths.return_value = (['/backup_2022101010/folder/file1.txt', '/file2.txt'],
                                                ['/backup_2022101010/'])
        mock_move_file.side_effect = connection_error
        result = utils.move_addon_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_file_paths.assert_called_once()
        mock_move_file.assert_called_once()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {'error': repr(connection_error)})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_from_backup_only_file_in_backup_folder(self, mock_get_all_file_paths, mock_move_file,
                                                                      mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_file_paths.return_value = (['/backup_2022101010/file1.txt', '/file2.txt'],
                                                ['/backup_2022101010/'])
        mock_move_file.return_value = test_response
        result = utils.move_addon_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_file_paths.assert_called_once()
        mock_move_file.assert_called_once()
        mock_delete_paths.assert_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_file_paths_in_addon_storage')
    def test_move_addon_folder_from_backup_no_backup_folder(self, mock_get_all_file_paths, mock_move_file,
                                                            mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_file_paths.return_value = (['/folder/file1.txt', '/file2.txt'],
                                                [])
        mock_move_file.return_value = test_response
        result = utils.move_addon_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_file_paths.assert_called_once()
        mock_move_file.assert_not_called()
        mock_delete_paths.assert_called()
        nt.assert_equal(result, {})

    # move_bulk_mount_folder_from_backup
    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_from_backup(self, mock_get_all_child_paths, mock_move_file, mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_child_paths.return_value = ([('/backup_child_folder_id/', '/backup_2022101010/folder/'),
                                                  ('/backup_file2_id', '/backup_2022101010/file2.txt')],
                                                 '/backup_folder_id/')
        mock_move_file.return_value = test_response
        result = utils.move_bulk_mount_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_child_paths.assert_called_once()
        nt.assert_equal(mock_move_file.call_count, 2)
        mock_delete_paths.assert_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_from_backup_empty_path_list(self, mock_get_all_child_paths, mock_move_file,
                                                                mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_get_all_child_paths.return_value = ([], None)
        mock_move_file.return_value = test_response
        result = utils.move_bulk_mount_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_child_paths.assert_called_once()
        mock_move_file.assert_not_called()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_from_backup_response_error(self, mock_get_all_child_paths, mock_move_file,
                                                               mock_delete_paths):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_403_FORBIDDEN
        test_response._content = b'Mock test error response while moving file'

        mock_get_all_child_paths.return_value = ([('/backup_child_folder_id/', '/backup_2022101010/folder/'),
                                                  ('/backup_file2_id', '/backup_2022101010/file2.txt')],
                                                 '/backup_folder_id/')
        mock_move_file.return_value = test_response
        result = utils.move_bulk_mount_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_child_paths.assert_called_once()
        mock_move_file.assert_called_once()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {'error': f'{status.HTTP_403_FORBIDDEN} - {test_response.content}'})

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_paths')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.move_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_all_child_paths_in_bulk_mount_storage')
    def test_move_bulk_mount_folder_from_backup_exception(self, mock_get_all_child_paths, mock_move_file,
                                                          mock_delete_paths):
        connection_error = ConnectionError('Mock test exception while moving file')

        mock_get_all_child_paths.return_value = ([('/backup_child_folder_id/', '/backup_2022101010/folder/'),
                                                  ('/backup_file2_id', '/backup_2022101010/file2.txt')],
                                                 '/backup_folder_id/')
        mock_move_file.side_effect = connection_error
        result = utils.move_bulk_mount_folder_from_backup(TEST_PROJECT_ID, TEST_PROVIDER, '2022101010', None)
        mock_get_all_child_paths.assert_called_once()
        mock_move_file.assert_called_once()
        mock_delete_paths.assert_not_called()
        nt.assert_equal(result, {'error': repr(connection_error)})

    # delete_paths
    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    def test_delete_paths(self, mock_delete_file):
        mock_delete_file.return_value = None
        utils.delete_paths(TEST_PROJECT_ID, TEST_PROVIDER, ['/folder/', '/file.txt'], None)
        nt.assert_equal(mock_delete_file.call_count, 2)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    def test_delete_paths_exception(self, mock_delete_file):
        mock_delete_file.side_effect = ConnectionError(f'Mock test exception while deleting file')
        utils.delete_paths(TEST_PROJECT_ID, TEST_PROVIDER, ['/folder/', '/file.txt'], None)
        nt.assert_equal(mock_delete_file.call_count, 2)

    # delete_file
    @patch(f'requests.delete')
    def test_delete_file(self, mock_delete_request):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK

        mock_delete_request.return_value = test_response
        response = utils.delete_file(TEST_PROJECT_ID, TEST_PROVIDER, '/file.txt', None)
        mock_delete_request.assert_called_once()
        nt.assert_equal(response, test_response)

    # delete_all_files_except_backup
    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup(self, mock_get_file_data, mock_delete_file):
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage
        utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
        mock_get_file_data.assert_called_once()
        nt.assert_equal(mock_delete_file.call_count, 2)

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup_get_file_response_error(self, mock_get_file_data, mock_delete_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_404_NOT_FOUND

        mock_get_file_data.return_value = test_response
        with nt.assert_raises(Exception):
            utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
            mock_get_file_data.assert_called_once()
            mock_delete_file.assert_not_called()

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup_get_file_exception(self, mock_get_file_data, mock_delete_file):
        mock_get_file_data.side_effect = ConnectionError('Mock test exception while getting file data')
        with nt.assert_raises(ConnectionError):
            utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
            mock_get_file_data.assert_called_once()
            mock_delete_file.assert_not_called()

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup_no_paths_to_delete(self, mock_get_file_data, mock_delete_file):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({'data': []}).encode('utf-8')

        mock_get_file_data.return_value = test_response
        utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
        mock_get_file_data.assert_called_once()
        mock_delete_file.assert_not_called()

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup_with_backup_folders(self, mock_get_file_data, mock_delete_file):
        response_body = {
            'data': [
                {
                    'attributes': {
                        'path': '/backup_2022101010/',
                        'materialized': '/backup_2022101010/',
                        'kind': 'folder'
                    }
                },
                {
                    'attributes': {
                        'path': '/file2.txt',
                        'materialized': '/file2.txt',
                        'kind': 'file'
                    }
                }
            ]
        }

        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps(response_body).encode('utf-8')

        mock_get_file_data.return_value = test_response
        utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
        mock_get_file_data.assert_called_once()
        mock_delete_file.assert_called_once()

    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup_delete_file_exception(self, mock_get_file_data, mock_delete_file):
        mock_get_file_data.side_effect = get_mock_get_file_data_response_addon_storage
        mock_delete_file.side_effect = ConnectionError('Mock test exception while deleting path')
        with nt.assert_raises(ConnectionError):
            utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
            mock_get_file_data.assert_called_once()
            mock_delete_file.assert_called_once()

    @patch(f're.compile')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.delete_file')
    @patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    def test_delete_all_files_except_backup_invalid_regex(self, mock_get_file_data, mock_delete_file,
                                                          mock_compile_regex):
        response_body = {
            'data': [
                {
                    'attributes': {
                        'path': '/backup_2022101010/',
                        'materialized': '/backup_2022101010/',
                        'kind': 'folder'
                    }
                },
                {
                    'attributes': {
                        'path': '/file2.txt',
                        'materialized': '/file2.txt',
                        'kind': 'file'
                    }
                }
            ]
        }

        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps(response_body).encode('utf-8')

        mock_get_file_data.return_value = test_response
        mock_compile_regex.side_effect = ValueError('Mock test invalid regex')
        utils.delete_all_files_except_backup(TEST_PROJECT_ID, TEST_PROVIDER, None)
        mock_get_file_data.assert_called_once()
        nt.assert_equal(mock_delete_file.call_count, 2)

    # is_add_on_storage
    def test_is_add_on_storage(self):
        # missing provider
        nt.assert_is_none(utils.is_add_on_storage(None))
        nt.assert_is_none(utils.is_add_on_storage('osf_storage'))

        # both addon method and bulk-mount method
        nt.assert_false(utils.is_add_on_storage('owncloud'))
        nt.assert_false(utils.is_add_on_storage('s3compat'))
        nt.assert_false(utils.is_add_on_storage('s3'))

        # only addon method providers
        nt.assert_true(utils.is_add_on_storage('nextcloudinstitutions'))
        nt.assert_true(utils.is_add_on_storage('s3compatinstitutions'))
        nt.assert_true(utils.is_add_on_storage('ociinstitutions'))
        nt.assert_true(utils.is_add_on_storage('dropboxbusiness'))

        # only bulk-mount method providers
        nt.assert_false(utils.is_add_on_storage('onedrivebusiness'))
        nt.assert_false(utils.is_add_on_storage('swift'))
        nt.assert_false(utils.is_add_on_storage('box'))
        nt.assert_false(utils.is_add_on_storage('nextcloud'))
        nt.assert_false(utils.is_add_on_storage('osfstorage'))
        nt.assert_false(utils.is_add_on_storage('onedrive'))
        nt.assert_false(utils.is_add_on_storage('googledrive'))
