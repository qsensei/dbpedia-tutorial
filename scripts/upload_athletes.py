from urlparse import urlparse
import json
import os
import time
import sys

import requests

SLEEP_INTERVAL = 0.5


def print_dot():
    sys.stdout.write(".")
    sys.stdout.flush()


def get_server_address():
    """ Try to figure out docker host from DOCKER_HOST.
    """
    docker_host = os.environ.get('DOCKER_HOST')
    if docker_host:
        return urlparse(docker_host).hostname
    return 'localhost'


def main():
    server_address = get_server_address()

    print "Upload data"
    filename = os.environ.get('PEOPLE_JSON', 'var/athletes.json')
    with open(filename) as f:
        data = json.load(f)
    res = requests.post(
        'http://%s:8000/api/tasks/types/update' % server_address,
        json=data)
    res.raise_for_status()
    print "Wait for data ingest task"
    taskurl = res.headers['location']
    while True:
        print_dot()
        res = requests.get(taskurl).json()
        if res['done']:
            taskurl = res['index_task']['@id']
            break
        time.sleep(SLEEP_INTERVAL)
    print "\n"
    print "Wait for index task"
    while True:
        print_dot()
        res = requests.get(taskurl).json()
        if res['done']:
            break
        time.sleep(SLEEP_INTERVAL)
    print "\n"


if __name__ == '__main__':
    main()
