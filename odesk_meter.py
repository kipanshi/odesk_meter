from datetime import datetime, timedelta

import json
from odesk import Client
from odesk.utils import Query
from odesk.utils import Q


KEYS_FILE = 'keys.json'


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
