# Python bindings to oDesk API
# python-odesk version 0.5
# (C) 2010-2014 oDesk

from odesk.namespaces import Namespace


class Job(Namespace):
    api_url = 'profiles/'
    version = 1

    def get_job_profile(self, job_key):
        """Returns detailed profile information about job(s).

        Documented at
        http://developers.odesk.com/w/page/49065901/Job%20Profile

        *Parameters:*
          :job_key:   The job key or a list of keys, separated by ";",
                      number of keys per request is limited by 20.
                      You can access job profile by job reference number,
                      in that case you can't specify a list of jobs,
                      only one profile per request is available.

        """
        max_keys = 20
        url = 'jobs/{0}'
        # Check job key(s)
        if not job_key.__class__ in [str, int, list, tuple]:
            raise ValueError(
                'Invalid job key. Job recno, key or list of keys expected, ' +
                '{0} given'.format(job_key.__class__))
        elif job_key.__class__ in [list, tuple]:
            if len(job_key) > max_keys:
                raise ValueError(
                    'Number of keys per request is limited by {0}'.format(
                        max_keys))
            elif filter(lambda x: not str(x).startswith('~~'), job_key):
                raise ValueError(
                    'List should contain only job keys not recno.')
            else:
                url = url.format(';'.join(job_key))
        else:
            url = url.format(job_key)
        result = self.get(url)
        profiles = result.get('profiles', result)
        return profiles.get('profile', result)
