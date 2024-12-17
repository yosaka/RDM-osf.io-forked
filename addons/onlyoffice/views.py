# -*- coding: utf-8 -*-
from flask import request, Response
import logging

import requests
import os
import time
from osf.models import BaseFileNode

from . import util as onlyoffice_util
from . import proof_key as pfkey
from . import settings
from . import token
from website import settings as websettings

from framework.auth.decorators import must_be_logged_in

logger = logging.getLogger(__name__)

pkhelper = pfkey.ProofKeyHelper()

#  wopi CheckFileInfo endpoint

# Do not add decorator, or else online editor will not open.
def onlyoffice_check_file_info(**kwargs):
    access_token = request.args.get('access_token', '')
    if access_token == '':
        return Response(response='', status=500)

    # proof key check
    if onlyoffice_util.check_proof_key(pkhelper, request, access_token) is False:
        return Response(response='', status=500)

    jsonobj = token.decrypt(access_token)
    # logger.info('onlyoffice: check_file_info jsonobj = {}'.format(jsonobj))
    if jsonobj is None:
        return Response(response='', status=500)

    # token check
    file_id = kwargs['file_id']
    if token.check_token(jsonobj, file_id) is False:
        return Response(response='', status=500)

    cookie = token.get_cookie(jsonobj)
    user_info = onlyoffice_util.get_user_info(cookie)
    try:
        file_node = BaseFileNode.objects.get(_id=file_id)
    except Exception:
        logger.warning('onlyoffice: BaseFileNode None')
        return Response(response='', status=500)
    file_version = onlyoffice_util.get_file_version(file_id)
    cookies = {websettings.COOKIE_NAME: cookie}
    file_info = onlyoffice_util.get_file_info(file_node, file_version, cookies)
    filename = '' if file_info is None else file_info['name']

    logger.info('ONLYOFFICE: file opened : user id = {}, fullname = {}, file_name = {}'
                .format(user_info['user_id'], user_info['full_name'], filename))

    res = {
        'BaseFileName': filename,
        'Version': file_version,
        #'ReadOnly': True,
        'UserCanReview': True,
        'UserCanWrite': True,
        'SupportsRename': True,
        'SupportsReviewing': True,
        'UserId': user_info['user_id'],
        'UserFriendlyName': user_info['display_name'],
    }
    return res

    '''
    Available response parameters and examples for ONLYOFFICE.
        'BaseFileName': 'Word.docx',
        'Version': 'Khirz6zTPdfd7',
        'BrandcrumbBrandName': "NII",
        'BrandcrumbBrandUrl': "https://www.nii.ac.jp",
        'BrandcrumbDocName': "barnd_doc.docx",
        'BrandcrumbFolderName': "Example Folder Name",
        'BrandcrumbFolderUrl': "https://www.nii.ac.jp/foler/",
        'ClosePostMessage': True,
        'EditModulePostMessages': True,
        'EditNotificationPostMessage': True,
        'FileShareingPostMessage': True,
        'FileVersionPostMessages': True,
        'PostMessageOrigin': "http://192.168.1.141",
        'CloseUrl': '',
        'FileShareingUrl': '',
        'FileVersionUrl': '',
        'HostEditUrl': '',
        'DisablePrint': True,
        'FileExension': '.docx',
        'FileNameMaxLength': 32,
        'LastModifiedTime': isomtime,
        'isAnonymousUser': True,
        'UserFriendlyName': 'Friendly name',
        'UserId': '1',
        'ReadOnly': True,
        'UserCanRename': True,
        'UserCanReview': True,
        'UserCanWrite': True,
        'SuuportsRename': True,
        'SupportsReviewing': True,
        'HidePrintOption': False
    '''


#  file content view endpoint

# Do not add decorator, or else online editor will not open.
def onlyoffice_file_content_view(**kwargs):
    access_token = request.args.get('access_token', '')
    if access_token == '':
        return Response(response='', status=500)

    # proof key check
    if onlyoffice_util.check_proof_key(pkhelper, request, access_token) is False:
        return Response(response='', status=500)

    jsonobj = token.decrypt(access_token)
    # logger.info('onlyoffice: file_content_view jsonobj = {}'.format(jsonobj))
    if jsonobj is None:
        return Response(response='', status=500)

    # token check
    file_id = kwargs['file_id']
    if token.check_token(jsonobj, file_id) is False:
        return Response(response='', status=500)

    cookie = token.get_cookie(jsonobj)
    user_info = onlyoffice_util.get_user_info(cookie)
    try:
        file_node = BaseFileNode.objects.get(_id=file_id)
    except Exception:
        logger.warning('onlyoffice: BaseFileNode None')
        return Response(response='', status=500)
    file_version = onlyoffice_util.get_file_version(file_id)
    cookies = {websettings.COOKIE_NAME: cookie}
    file_info = onlyoffice_util.get_file_info(file_node, file_version, cookies)
    filename = '' if file_info is None else file_info['name']

    # logger.info('onlyoffice: file_content_view: method, file_id, access_token = {} {} {}'.format(request.method, file_id, access_token))
    # logger.info('onlyoffice: waterbutler url = {}'.format(websettings.WATERBUTLER_URL))

    if request.method == 'GET':
        #  wopi GetFile endpoint
        content = ''
        status_code = ''
        try:
            wburl = file_node.generate_waterbutler_url(version=file_version, action='download', direct=None, _internal=True)
            # logger.info('onlyoffice: wburl, cookies = {}  {}'.format(wburl, cookies))
            response = requests.get(
                wburl,
                cookies=cookies,
                stream=True
            )
            status_code = response.status_code
            if status_code == 200:
                content = response.raw
            else:
                logger.warning('onlyoffice: Waterbutler return error.')
        except Exception as err:
            logger.warning(err)
            return

        return Response(response=content, status=status_code)

    if request.method == 'POST':
        #  wopi PutFile endpoint
        logger.info('ONLYOFFICE: file saved  : user id = {}, fullname = {}, file_name = {}'
                    .format(user_info['user_id'], user_info['full_name'], filename))
        if not request.data:
            return Response(response='Not possible to get the file content.', status=401)

        data = request.data
        wburl = file_node.generate_waterbutler_url(direct=None, _internal=True) + '?kind=file'
        logger.debug('onlyoffice: wburl = {}'.format(wburl))
        try:
            response = requests.put(
                wburl,
                cookies=cookies,
                data=data,
            )
            status_code = response.status_code
            if status_code != 200:
                logger.warning('onlyoffice: Waterbutler return error.')
        except Exception as err:
            logger.warning(err)

        return Response(status=status_code)


# Do not add decorator, or else online editor will not open.
def onlyoffice_lock_file(**kwargs):
    file_id = kwargs['file_id']
    logger.debug('onlyoffice: lock_file: file_id = {}'.format(file_id))

    if request.method == 'POST':
        operation = request.META.get('X-WOPI-Override', None)
        if operation == 'LOCK':
            lockId = request.META.get('X-WOPI-Lock', None)
            logger.debug(f"onlyoffice: Lock: file id: {file_id}, access token: {request.args.get['access_token']}, lock id: {lockId}")
        elif operation == 'UNLOCK':
            lockId = request.META.get('X-WOPI-Lock', None)
            logger.debug(f"onlyoffice: UnLock: file id: {file_id}, access token: {request.args.get['access_token']}, lock id: {lockId}")
        elif operation == 'REFRESH_LOCK':
            lockId = request.META.get('X-WOPI-Lock', None)
            logger.debug(f"onlyoffice: RefreshLock: file id: {file_id}, access token: {request.args.get['access_token']}, lock id: {lockId}")
        elif operation == 'RENAME':
            toName = request.META.get('X-WOPI-RequestedName', None)
            logger.debug(f"onlyoffice: Rename: file id: {file_id}, access token: {request.args.get['access_token']}, toName: {toName}")

    return Response(status=200)   # Status 200


@must_be_logged_in
def onlyoffice_edit_by_onlyoffice(**kwargs):
    file_id = kwargs['file_id']
    cookie = request.cookies.get(websettings.COOKIE_NAME)
    # logger.info('onlyoffice: cookie = {}'.format(cookie))
    try:
        file_node = BaseFileNode.objects.get(_id=file_id)
    except Exception:
        logger.warning('onlyoffice: BaseFileNode None')
        return Response(response='', status=500)
    ext = os.path.splitext(file_node.name)[1][1:]
    access_token = token.encrypt(cookie, file_id)
    # access_token ttl (ms)
    token_ttl = (time.time() + settings.WOPI_TOKEN_TTL) * 1000

    wopi_client_host = settings.WOPI_CLIENT_ONLYOFFICE
    logger.debug('onlyoffice: edit_online.index_view wopi_client_host = {}'.format(wopi_client_host))

    wopi_url = ''
    wopi_client_url = onlyoffice_util.get_onlyoffice_url(wopi_client_host, 'edit', ext)
    if wopi_client_url:
        wopi_src_host = settings.WOPI_SRC_HOST
        wopi_src = f'{wopi_src_host}/wopi/files/{file_id}'
        # logger.info('onlyoffice: edit_by_onlyoffice.index_view wopi_src = {}'.format(wopi_src))
        wopi_url = wopi_client_url \
            + 'rs=ja-jp&ui=ja-jp'  \
            + '&WOPISrc=' + wopi_src

    # logger.info('onlyoffice: edit_by_online.index_view wopi_url = {}'.format(wopi_url))

    # Get public key for proof-key check from onlyoffice server, if did not have yet.
    if pkhelper.hasKey() is False:
        proof_key = onlyoffice_util.get_proof_key(wopi_client_host)
        if proof_key is not None:
            pkhelper.setKey(proof_key)
            # logger.info('onlyoffice: edit_by_onlyoffice pkhelper key initialized.')

    logger.debug('onlyoffice: edit_by_online.index_view wopi_url = {}'.format(wopi_url))
    context = {
        'wopi_url': wopi_url,
        'access_token': access_token,
        'access_token_ttl': token_ttl,
    }
    return context
