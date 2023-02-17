import unittest
from flask import request

import mock
from nose.tools import *

from osf.models import BaseFileNode
from website.edit_online.views import edit_by_onlyoffice, edit_by_collabora
from website import settings

from flask import Flask
app = Flask(__name__)

class Response():
    status_code = 0
    text = ''
    content = ''

class TestCase1(unittest.TestCase):

    def setUp(self):
        self.resp = Response()
        self.resp.status_code = 200
        self.resp.text = ''
        self.resp.content = b''

    @mock.patch('webste.edit_online.util.requests')
    def test_case1(self, mock_requests):

        self.resp.content = b'<?xml version="1.0" encoding="utf-8"?><wopi-discovery><net-zone name="external-http"><app name="Word" favIconUrl="http://192.168.1.1:8002/web-apps/apps/documenteditor/main/resources/img/favicon.ico"><action name="edit" ext="docx" urlsrc="http://192.168.1.1:8002/hosting/wopi/word/view?&amp;&lt;rs=DC_LLCC&amp;&gt;&lt;dchat=DISABLE_CHAT&amp;&gt;&lt;embed=EMBEDDED&amp;&gt;&lt;fs=FULLSCREEN&amp;&gt;&lt;hid=HOST_SESSION_ID&amp;&gt;&lt;rec=RECORDING&amp;&gt;&lt;sc=SESSION_CONTEXT&amp;&gt;&lt;thm=THEME_ID&amp;&gt;&lt;ui=UI_LLCC&amp;&gt;&lt;wopisrc=WOPI_SOURCE&amp;&gt;&amp;" /></app></net-zone></wopi-discovery>'

        mock_base_file_node = mock.MagicMock()
        mock_base_file_node.load.return_value = 'filename1.docx'
        with mock.patch('osf.models.BaseFileNode', mock_base_file_node):
            with app.test_request_context('/wopi', headers={'Cookie': 'osf=Cookie String'}):
                mock_requests.get.return_value = self.resp
                context = edit_by_onlyoffice(file_id_ver="ABCDEFG-01")
                # print('wopi_url = {}'.format(context['wopi_url']))
                # print('access_token = {}'.format(context['access_token']))
                
                assert_equal(context['wopi_url'], 'http://192.168.1.1:8002/hosting/wopi/word/view?rs=ja-jp&ui=ja-jp&wopisrc=http://server.rdm.nii.ac.jp/wopi/files/ABCDEFG-01', 'edit_by_onlyoffice test1')
                assert_equal(context['access_token'], 'Cookie String', 'edit_by_onlyoffice test2')


    @mock.patch('website.edit_online.util.requests')
    def test_case2(self, mock_requests):

        self.resp.text = '<wopi-discovery><net-zone name="external-http"><app favIconUrl="http://192.168.1.1:9980/browser/abd9205/images/x-office-document.svg" name="writer"><action default="true" ext="docx" name="edit" urlsrc="http://192.168.1.1:9980/browser/abd9205/cool.html?"/></app></net-zone></wopi-discovery>'

        mock_base_file_node = mock.MagicMock()
        mock_base_file_node.load.return_value = 'filename1.docx'
        with mock.patch('osf.models.BaseFileNode', mock_base_file_node):
            with app.test_request_context('/wopi', headers={'Cookie': 'osf=Cookie String'}):
                mock_requests.get.return_value = self.resp
                context = edit_by_collabora(file_id_ver="ABCDEFG-01")
                # print('wopi_url = {}'.format(context['wopi_url']))
                # print('access_token = {}'.format(context['access_token']))

                assert_equal(context['wopi_url'], 'http://192.168.1.1:9980/browser/abd9205/cool.html?access_token=Cookie String&WOPISrc=http://server.rdm.nii.ac.jp/wopi/files/ABCDEFG-01', 'edit_by_collabora test1')
                assert_equal(context['access_token'], 'Cookie String', 'edit_by_collabora test2')
