import jwe
import jwt

from jsonschema import validate
from datetime import datetime, timezone, timedelta
import logging

from . import settings

logger = logging.getLogger(__name__)

OFFICESERVER_JWE_KEY = jwe.kdf(settings.OFFICESERVER_JWE_SECRET.encode('utf-8'), settings.OFFICESERVER_JWE_SALT.encode('utf-8'))

token_schema = {
    "type": "object",
    "required": ["exp", "data"],
    "properties": {
        "exp" : {"type" : "number"},
        "data" : {
            "type": "object",
            "required": ["auth", "file_id"],
            "properties" : {
                "auth" : {"type" : "string"},
                "file_id" : {"type" : "string"}
            }
        }
    }
}

def _get_timestamp():
    nt = datetime.now(timezone.utc).timestamp()
    return nt


def _check_schema(token):
    try:
        validate(instance=token, schema=token_schema)
        return True
    except jsonschema.exceptions.ValidationError as e:
        logger.info('token schema error : {}'.format(e))
        return False


def encrypt(cookie, file_id):
    jwte = jwt.encode(
        {
            'data' : {
                'auth': cookie,
                'file_id': file_id
            },
            'exp': int(datetime.now(timezone.utc).timestamp() +
                       timedelta(seconds=settings.WOPI_TOKEN_TTL).seconds) +
                       settings.WOPI_EXPIRATION_TIMER_DELAY
        },
        settings.OFFICESERVER_JWT_SECRET, algorithm=settings.OFFICESERVER_JWT_ALGORITHM)
        #websettings.JWT_SECRET, algorithm=websettings.JWT_ALGORITHM)
    #print(jwte)
    encstr = jwe.encrypt(jwte, OFFICESERVER_JWE_KEY).decode()
    #print(encstr)
    logger.info('token encstr = {}'.format(encstr))
    return encstr


def decrypt(encstr):
    try:
        decstr = jwe.decrypt(encstr.encode('utf-8'), OFFICESERVER_JWE_KEY)
        jsonobj = jwt.decode(decstr, settings.OFFICESERVER_JWT_SECRET, algorithms=settings.OFFICESERVER_JWT_ALGORITHM)
        #jsonobj = jwt.decode(decstr, websettings.JWT_SECRET, algorithms=websettings.JWT_ALGORITHM)
    except Exception as e:
        logger.info('decrypt failed.')
        jsonobj = None
    return jsonobj


def check_token(jsonobj, file_id):
    # token schema check
    if _check_schema(jsonobj) is False:
        logger.info('check_schema failed.')
        return False

    # file_id check
    if file_id != jsonobj['data']['file_id']:
        logger.info('token file_id check failed.')
        logger.info('file_id, token file_id : {}  {}'.format(file_id, jsonobj['data']['file_id']))
        return False

    # expiration check
    nt = int(_get_timestamp())
    if nt > jsonobj['exp']:
        logger.info('token time expire failed.')
        logger.info('nt, token expire : {}  {}'.format(nt, jsonobj['exp']))
        return False

    return True


def get_cookie(jsonobj):
    return jsonobj['data']['auth']
