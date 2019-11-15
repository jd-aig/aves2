#! /usr/bin/env python3

import time
import os
import sys
import requests


AVES_API_HOST = os.environ['AVES_API_HOST']
AVES_API_JOB_REPORT_URL = os.environ['AVES_API_JOB_REPORT_URL']


if __name__ == '__main__':
    url = os.path.join(AVES_API_HOST, AVES_API_JOB_REPORT_URL)
    status = sys.argv[1]
    msg = sys.argv[2]

    data = {
        'status': status,
        'msg': msg
    }

    print('Send result to aves')
    print('url: %s' % url)
    print('data: %s' % data)

    retry = 3
    while retry > 0:
        retry -= 1
        try:
            r = requests.get(url, params=data, timeout=10)
        except Exception as e:
            print('Fail to report, try again 10 seconds later ...')
            print(e)
        time.sleep(10)
