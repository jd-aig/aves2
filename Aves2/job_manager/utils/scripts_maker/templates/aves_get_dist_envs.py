#! /usr/bin/env python

import requests
import os
import sys
import time


AVES_API_HOST = os.environ['AVES_API_HOST']
AVES_API_TOKEN = os.environ['AVES_API_TOKEN']
AVES_API_JOB_DIST_ENVS_URL = os.environ['AVES_API_JOB_DIST_ENVS_URL']

HEADERS = {
    'Authorization': 'Token %s' % AVES_API_TOKEN,
}


def get_dist_envs(dst_env_file):
    url = os.path.join(AVES_API_HOST, AVES_API_JOB_DIST_ENVS_URL)

    try:
        r = requests.get(url, headers=HEADERS)
    except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
        print(e)
        return False

    if not r.ok:
        try:
            print("Warning: {0}".format(r.json()['detail']))
        except Exception as e:
            print(e)
        return False

    with open(dst_env_file, 'w') as f:
        for k, v in r.json().items():
            f.write('export {k}={v}\n'.format(k=k, v=v))
        return True


if __name__ == '__main__':
    env_file = sys.argv[1]
    if not get_dist_envs(env_file):
        exit(2)
