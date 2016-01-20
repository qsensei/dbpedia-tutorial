from glob import glob
from urlparse import urlparse
import contextlib
import os
import tempfile
import time
import zipfile

from invoke import run, task
import requests


@task
def setup(container='dbpedia-tutorial'):
    setup_fuse(container)
    run('bin/python scripts/upload_football.py')
    run('bin/python scripts/upload_baseball.py')
    run('bin/python scripts/upload_basketball.py')
    run('bin/python scripts/upload_teams.py')


@task
def setup_fuse(container='dbpedia-tutorial'):
    run('docker run -dp 8000:8000 --name %s docker.qsensei.com/fuse-free' % (
        container))
    time.sleep(10)
    setup_instance()
    start_instance()


@task
def reload_schema():
    stop_instance()
    setup_instance()
    start_instance()
    reindex()


def setup_instance():
    server_address = _get_server_address()
    with fuse_schema() as z:
        res = requests.put(
            'http://%s:8000/api/admin/instance' % server_address,
            headers={'content-type': 'application/zip'},
            data=z)
        if res.status_code == 200:
            pass
        elif res.status_code == 400:
            print res.json()
        else:
            pass
        res.raise_for_status()


def start_instance():
    server_address = _get_server_address()
    res = requests.post(
        'http://%s:8000/api/admin/instance' % server_address,
        json={'action': 'start'})
    res.raise_for_status()
    time.sleep(5)


def stop_instance():
    server_address = _get_server_address()
    res = requests.post(
        'http://%s:8000/api/admin/instance' % server_address,
        json={'action': 'stop'})
    res.raise_for_status()
    time.sleep(5)


@task
def reindex():
    server_address = _get_server_address()
    res = requests.post(
        'http://%s:8000/api/tasks/types/index' % server_address
    )
    res.raise_for_status()


@task
def teardown(container='dbpedia-tutorial'):
    run('docker rm -fv %s' % container)


def _get_server_address():
    docker_host = os.environ.get('DOCKER_HOST')
    if docker_host:
        return urlparse(docker_host).hostname
    return 'localhost'


@contextlib.contextmanager
def fuse_schema():
    with tempfile.TemporaryFile() as f:
        with zipfile.ZipFile(f, 'w') as z:
            for fn in glob('schema/*.json'):
                z.write(fn, os.path.basename(fn))
            for fn in glob('schema/*.py'):
                z.write(fn, os.path.basename(fn))
        f.flush()
        f.seek(0)
        yield f
