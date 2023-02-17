import unittest
from flask import request

import mock
from nose.tools import *
from osf.models import BaseFileNode
from website import settings
from website.wopi.views import check_file_info, _get_user_info, _get_file_info

from flask import Flask
app = Flask(__name__)


class TestCase1(unittest.TestCase):

    def setUp(self):
        self.user_info = {
            'user_id':   'uid',
            'full_name': 'full name',
            'display_name': 'display_name'
        }
        self.file_info = {
            'file_name': 'filename.docx',
            'file_size':  1234,
            'file_mtime': 2023012345
        }


    @mock.patch('util.requests')
    def test_case1(self, mock_requests):

        mock_base_file_node = mock.MagicMock()
        mock_base_file_node.load.return_value = 'filename1.docx'
        with mock.patch('basefilenode.BaseFileNode', mock_base_file_node):
            mock_get_user_info = mock.MagicMock()
            mock_get_user_info.return_value = self.user_info
            with mock.patch('views._get_user_info', mock_get_user_info):
                mock_get_file_info = mock.MagicMock()
                mock_get_file_info.return_value = self.file_info
                with mock.patch('views._get_file_info', mock_get_file_info):
                    with app.test_request_context('/wopi', headers={'Cookie': 'osf=Cookie String', 'User_Agent': 'COOLWSD'}, query_string={'access_token': "Token"}):
                        res = check_file_info(file_id_ver="ABCDEFG-01")
                        #print('{}, {}'.format(res['BaseFileName'], res['Size']))
                        assert_equal(res['BaseFileName'], 'filename.docx')
                        assert_equal(res['Size'], 1234)


    @mock.patch('util.requests')
    def test_case2(self, mock_requests):

        mock_base_file_node = mock.MagicMock()
        mock_base_file_node.load.return_value = 'filename1.docx'
        with mock.patch('basefilenode.BaseFileNode', mock_base_file_node):
            mock_get_user_info = mock.MagicMock()
            mock_get_user_info.return_value = self.user_info
            with mock.patch('views._get_user_info', mock_get_user_info):
                mock_get_file_info = mock.MagicMock()
                mock_get_file_info.return_value = self.file_info
                with mock.patch('views._get_file_info', mock_get_file_info):
                    with app.test_request_context('/wopi', headers={'Cookie': 'osf=Cookie String', 'User_Agent': 'Node.js'}, query_string={'access_token': "Token"}):
                        res = check_file_info(file_id_ver="ABCDEFG-01")
                        #print('{}, {}'.format(res['BaseFileName'], res['Size']))
                        assert_equal(res['BaseFileName'], 'filename.docx')
                        assert_equal(res['Size'], 1234)
