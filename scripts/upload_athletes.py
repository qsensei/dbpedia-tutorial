from urlparse import urlparse
import json
import os

import requests


def iterate_fuse_objects():
    filename = os.environ.get('PEOPLE_NDJSON', 'var/people.ndjson')
    with open(filename) as f:
        for line in f:
            yield json.loads(line)


def get_server_address():
    """ Try to figure out docker host from DOCKER_HOST.
    """
    docker_host = os.environ.get('DOCKER_HOST')
    if docker_host:
        return urlparse(docker_host).hostname
    return 'localhost'


def main():
    server_address = get_server_address()
    items = list(iterate_fuse_objects())
    res = requests.post(
        'http://%s:8000/api/tasks/types/update' % server_address,
        json={'items': items})
    res.raise_for_status()
    taskurl = res.headers['location']
    while True:
        res = requests.get(taskurl).json()
        if res['done']:
            taskurl = res['index_task']['@id']
            break
    while True:
        res = requests.get(taskurl).json()
        if res['done']:
            break


if __name__ == '__main__':
    main()
