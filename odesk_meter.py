import os
import sys
import json
from datetime import datetime, timedelta

from odesk import Client
from odesk.utils import Query
from odesk.utils import Q

KEYS_FILE = 'keys.json'


_PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
_LIB_DIR = os.path.join(_PROJECT_DIR, 'lib')
[sys.path.insert(0, path) for path in (_LIB_DIR,)]


def get_client(authorize=False):
    """Authenticate using keys stored in ``keys.json`` and return
    the ``Client`` instance ready for work.

    """
    if authorize:
        keys = {}
        public_key = raw_input('Please enter public key: > ')
        secret_key = raw_input('Please enter secret key: > ')

        keys.update({'key': public_key, 'secret': secret_key})
    else:
        with open(KEYS_FILE) as f:
            keys = json.loads(f.read())

    if authorize:
        client = Client(keys['key'], keys['secret'], auth='oauth')
        verifier = raw_input(
            'Please enter the verification code you get '
            'following this link:\n{0}\n\n> '.format(client.auth.get_authorize_url()))

        access_token_0, access_token_1 = client.auth.get_access_token(verifier)
        print 'Updating keys....',
        keys['access_token_0'] = access_token_0
        keys['access_token_1'] = access_token_1
        with open(KEYS_FILE, 'w') as f:
            f.write(json.dumps(keys))
        print 'OK'

    client = Client(keys['key'], keys['secret'], auth='oauth',
                    oauth_access_token=keys['access_token_0'],
                    oauth_access_token_secret=keys['access_token_1'],
                    )

    return client


def get_auth_info(client):
    return client.get('https://www.odesk.com/api/auth/v1/info')


def get_auth_user_uid(client):
    auth_info = get_auth_info(client)
    return auth_info['auth_user']['uid']


def get_timereport(client, from_date=None, to_date=None):
    """Return parsed JSON data with timereport for given period.
    Fields are default.

    :from_date:    date object
    :to_date:      date object

    If empty - timereport from now to the begining of the current week.

    """
    now = datetime.now()
    if not to_date:
        if not from_date:
            to_date = now.date()
            from_date = now.date() - timedelta(days=now.weekday())

    query = Query(
        select=Query.DEFAULT_TIMEREPORT_FIELDS,
        where=(Q('worked_on') <= to_date) & (Q('worked_on') >= to_date))
    auth_user_uid = get_auth_user_uid(client)

    return client.timereport.get_provider_report(auth_user_uid, query)
