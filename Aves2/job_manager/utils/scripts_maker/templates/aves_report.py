#! /usr/bin/env python3

import time
import os
import sys
import requests


AVES_API_HOST = os.environ['AVES_API_HOST']
AVES_API_JOB_REPORT_URL = os.environ['AVES_API_JOB_REPORT_URL']
AVES_API_JOB_STATUS_REPORT_URL = os.environ['AVES_API_JOB_STATUS_REPORT_URL']
AVES_API_WORKER_STATUS_REPORT_URL = os.environ['AVES_API_WORKER_STATUS_REPORT_URL']


if __name__ == '__main__':
    report_type = sys.argv[1]  # job_status/worker_status
    status = sys.argv[2]
    msg = sys.argv[3]

    if report_type == 'worker_status':
        url = os.path.join(AVES_API_HOST, AVES_API_WORKER_STATUS_REPORT_URL)
    elif report_type == "job_status":
        url = os.path.join(AVES_API_HOST, AVES_API_JOB_STATUS_REPORT_URL)
    else:
        url = os.path.join(AVES_API_HOST, AVES_API_JOB_REPORT_URL)

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
            if not r.ok:
                raise Exception(r.text)
            break
        except requests.exceptions.ConnectTimeout as e:
            print('Timeout, server maybe lost,  try again 10 seconds later ...')
            print(e)
        except Exception as e:
            print(e)
            break
        time.sleep(10)
