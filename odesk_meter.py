#!/usr/bin/env python
import os
import sys
import json
from datetime import datetime, timedelta

import pygtk
pygtk.require('2.0')
import gtk

# Update python path
_PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
_LIB_DIR = os.path.join(_PROJECT_DIR, 'lib')
[sys.path.insert(0, path) for path in (_LIB_DIR,)]

from odesk import Client
from odesk.utils import Query
from odesk.utils import Q

KEYS_FILE = 'keys.json'

ODESK_WORKED_ON_FORMAT = '%Y%m%d'


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
        client = Client(keys['key'], keys['secret'])
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

    client = Client(keys['key'], keys['secret'],
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
        to_date = now.date()
        if not from_date:
            from_date = now.date() - timedelta(days=now.weekday())

    query = Query(
        select=Query.DEFAULT_TIMEREPORT_FIELDS,
        where=(Q('worked_on') >= from_date) & (Q('worked_on') <= to_date))
    auth_user_uid = get_auth_user_uid(client)

    return client.timereport.get_provider_report(auth_user_uid, query)


def get_today_and_this_week_times(data):
    """Return mapping of teams and hours worked for each team today
    and this week.

    :data:    parsed json data returned from ``get_timereport()`` function

    """
    now = datetime.now()

    date_idx = data['table']['cols'].index(
        {'type': 'date', 'label': 'worked_on'})
    team_idx = data['table']['cols'].index(
        {'type': 'string', 'label': 'team_name'})
    hours_idx = data['table']['cols'].index(
        {'type': 'number', 'label': 'hours'})

    teams = {}

    for row in data['table']['rows']:
        team_name = row['c'][team_idx]['v']
        hours = float(row['c'][hours_idx]['v'])
        date_worked_on = row['c'][date_idx]['v']
        if team_name not in teams:
            teams[team_name] = {'today_hours': 0.0, 'week_hours': 0.0}
        teams[team_name]['week_hours'] += hours
        if date_worked_on == now.strftime(ODESK_WORKED_ON_FORMAT):
            teams[team_name]['today_hours'] += hours
    return teams


def get_timereport_layout(data, odesk_uid):
    """Render text widged showing timereport data.

    :data:        parsed json data returned from ``get_timereport()`` function
    :odesk_uid:   oDesk user UID

    """
    row_template = '{0}:\n\t{1:.2f} hrs today\n\t{2:.2f} hrs this week\n'
    rows_rendered = '\n'.join(
        [row_template.format(team_name,
                             team_data['today_hours'],
                             team_data['week_hours'])
         for team_name, team_data
         in get_today_and_this_week_times(data).items()]
    )
    if not rows_rendered:
        rows_rendered = "\nNo worked hours yet"
    template = 'User: {odesk_uid}\n{rows}'
    return template.format(
        odesk_uid=odesk_uid,
        rows=rows_rendered
    )


#=========================
# odesk_meter GTK app code
#=========================
class Base(object):
    def __init__(self):
        # Initialize oDesk API
        self.client = get_client(authorize=(not os.path.exists(KEYS_FILE)))
        self.odesk_uid = get_auth_user_uid(self.client)
        self.timereport_data = get_timereport(self.client)

        # Main window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.set_title("oDesk Meter")

        # Button ``refresh``
        self.button_refresh = gtk.Button('Refresh')
        self.button_refresh.set_size_request(70, 30)
        self.button_refresh.connect('clicked', self.refresh)

        # Text area
        self.main_text = gtk.TextView()
        self.main_text.set_property('editable', False)
        self.main_text.set_property('cursor-visible', False)
        self.main_text_buffer = self.main_text.get_buffer()
        self.main_text_buffer.set_text(
            get_timereport_layout(self.timereport_data, self.odesk_uid))

        # Put buttons
        layout = gtk.Layout()
        layout.put(self.button_refresh, 5, 5)
        layout.put(self.main_text, 10, 40)

        self.window.add(layout)
        self.window.show_all()
        self.window.connect('destroy', self.destroy)

    def refresh(self, widget):
        self.timereport_data = get_timereport(self.client)
        self.main_text_buffer.set_text(
            get_timereport_layout(self.timereport_data, self.odesk_uid))

    def destroy(self, widget):
        """Close main window."""
        gtk.main_quit()

    def main(self):
        gtk.main()


if __name__ == '__main__':
    try:
        if not os.path.exists(KEYS_FILE):
            print 'Preparing to get access token...\n'
            get_client(authorize=True)
            print '\nNow as access token is obtained, you can run odesk meter ``python odesk_meter.py``'
            exit(1)
        Base().main()
    except KeyboardInterrupt:
        exit(1)
