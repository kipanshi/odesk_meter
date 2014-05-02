# Python bindings to oDesk API
# python-odesk version 0.5
# (C) 2010-2014 oDesk

import os
import json
import logging
import urllib3


from odesk.oauth import OAuth
from odesk.http import raise_http_error
from odesk.utils import decimal_default
from odesk.exceptions import IncorrectJsonResponseError


__all__ = ["Client"]


logger = logging.getLogger('python-odesk')

if os.environ.get("PYTHON_ODESK_DEBUG", False):
    if os.environ.get("PYTHON_ODESK_DEBUG_FILE", False):
        fh = logging.FileHandler(filename=os.environ["PYTHON_ODESK_DEBUG_FILE"]
            )
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
    else:
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)
else:
    ch = logging.StreamHandler()
    ch.setLevel(logging.CRITICAL)
    logger.addHandler(ch)


class Client(object):
    """
    Main API client with oAuth v1 authorization.

    *Parameters:*
      :public_key:                Public API key

      :secret_key:                API key secret

      :oauth_access_token:        oAuth access token public key

      :oauth_access_token_secret: oAuth access token secret key

      :fmt:                       (optional, default ``json``)
                                  API response format.
                                  Currently only ``'json'`` is supported

      :finreport:                 (optional, default ``True``)
                                  Whether to attach
                                  :py:mod:`odesk.routers.finreport` router

      :hr:                        (optional, default ``True``)
                                  Whether to attach
                                  :py:mod:`odesk.routers.hr` router

      :mc:                        (optional, default ``True``)
                                  Whether to attach
                                  :py:mod:`odesk.routers.mc` router

      :provider:                  (optional, default ``True``)
                                  Whether to attach
                                  :py:mod:`odesk.routers.provider` router

      :task:                      (optional, default ``True``)
                                  Whether to attach
                                  :py:mod:`odesk.routers.task` router

      :team:                      (optional, default ``True``)
                                  Whether to attach
                                  :py:mod:`odesk.routers.team` router

      :timereport:                (optional, default ``True``)
                                  Whether to attach
                                  :py:mod:`odesk.routers.timereport` router

      :job:                       (optional, default ``True``)
                                  Whether to attach
                                  :py:mod:`odesk.routers.job` router

    """

    def __init__(self, public_key, secret_key,
                 oauth_access_token=None, oauth_access_token_secret=None,
                 fmt='json', finreport=True, hr=True, mc=True,
                 provider=True, task=True, team=True,
                 timereport=True, job=True):

        self.public_key = public_key
        self.secret_key = secret_key
        self.fmt = fmt
        self.http = urllib3.PoolManager()

        self.oauth_access_token = oauth_access_token
        self.oauth_access_token_secret = oauth_access_token_secret

        #Namespaces
        self.auth = OAuth(self)

        if finreport:
            from odesk.routers.finreport import Finreports
            self.finreport = Finreports(self)

        if hr:
            from odesk.routers.hr import HR_V1, HR
            self.hr_v1 = HR_V1(self)
            self.hr = HR(self)

        if mc:
            from odesk.routers.mc import MC
            self.mc = MC(self)

        if provider:
            from odesk.routers.provider import Provider, Provider_V2
            self.provider = Provider(self)
            self.provider_v2 = Provider_V2(self)

        if task:
            from odesk.routers.task import Task
            self.task = Task(self)

        if team:
            from odesk.routers.team import Team, Team_V2
            self.team = Team(self)
            self.team_v2 = Team_V2(self)

        if timereport:
            from odesk.routers.timereport import TimeReport
            self.timereport = TimeReport(self)

        if job:
            from odesk.routers.job import Job
            self.job = Job(self)

    #Shortcuts for HTTP methods
    def get(self, url, data=None):
        return self.read(url, data, method='GET', fmt=self.fmt)

    def post(self, url, data=None):
        return self.read(url, data, method='POST', fmt=self.fmt)

    def put(self, url, data=None):
        return self.read(url, data, method='PUT', fmt=self.fmt)

    def delete(self, url, data=None):
        return self.read(url, data, method='DELETE', fmt=self.fmt)

    # The method that actually makes HTTP requests
    def urlopen(self, url, data=None, method='GET', headers=None):
        """Perform oAuth v1 signed HTTP request.

        *Parameters:*
          :url:         Target url

          :data:        Dictionary with parameters

          :method:      (optional, default ``GET``)
                        HTTP method, possible values:
                          * ``GET``
                          * ``POST``
                          * ``PUT``
                          * ``DELETE``

          :headers:     (optional, default ``{}``)
                        Dictionary with header values

        """

        if headers is None:
            headers = {}

        self.last_method = method
        self.last_url = url
        self.last_data = data

        # TODO: Headers are not supported fully yet
        # instead we pass oauth parameters in querystring
        if method in ('PUT', 'DELETE'):
            post_data = self.auth.get_oauth_params(
                url, self.oauth_access_token,
                self.oauth_access_token_secret,
                {}, method)  # don't need parameters in url
        else:
            if data is None:
                data = {}
            post_data = self.auth.get_oauth_params(
                url, self.oauth_access_token,
                self.oauth_access_token_secret,
                data, method)

        if method == 'GET':
            url = '{0}?{1}'.format(url, post_data)
            return self.http.urlopen(method, url)
        elif method == 'POST':
            return self.http.urlopen(
                method, url, body=post_data,
                headers={'Content-Type':
                         'application/x-www-form-urlencoded;charset=UTF-8'})
        elif method in ('PUT', 'DELETE'):
            url = '{0}?{1}'.format(url, post_data)
            headers['Content-Type'] = 'application/json'
            if data is not None:
                data_json = json.dumps(data)
            else:
                data_json = ''
            return self.http.urlopen(
                method, url, body=data_json, headers=headers)

        else:
            raise Exception('Wrong http method: {0}. Supported'
                            'methods are: '
                            'GET, POST, PUT, DELETE'.format(method))

    def read(self, url, data=None, method='GET', fmt='json'):
        """
        Returns parsed Python object or raises an error.

        *Parameters:*
          :url:       Target url

          :data:      Dictionary with parameters

          :method:    (optional, default ``GET``)
                      HTTP method, possible values:
                        * ``GET``
                        * ``POST``
                        * ``PUT``
                        * ``DELETE``

          :fmt:         (optional, default ``json``)
                        API response format.
                        Currently only ``'json'`` is supported

        """
        assert fmt == 'json', "Only JSON format is supported at the moment"

        if '/gds/' not in url:
            url = '{0}.{1}'.format(url, fmt)

        logger = logging.getLogger('python-odesk')

        logger.debug('Prepairing to make oDesk call')
        logger.debug('URL: {0}'.format(url))
        try:
            logger.debug('Data: {0}'.format(
                json.dumps(data, default=decimal_default)))
        except TypeError:
            logger.debug('Data: {0}'.format(str(data)))
        logger.debug('Method: {0}'.format(method))
        response = self.urlopen(url, data, method)

        if response.status != 200:
            logger.debug('Error: {0}'.format(response))
            raise_http_error(url, response)

        result = response.data
        logger.debug('Response: {0}'.format(result))

        if fmt == 'json':
            try:
                result = json.loads(result)
            except ValueError:
                # Not a valid json string
                logger.debug('Response is not a valid json string')
                raise IncorrectJsonResponseError(
                    json.dumps({'status': response.status, 'body': result},
                               default=decimal_default)
                )
        return result


if __name__ == "__main__":
    import doctest
    doctest.testmod()
