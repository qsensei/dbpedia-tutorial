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
    run('bin/python scripts/upload_athletes.py')


@task
def setup_fuse(container='dbpedia-tutorial'):
    run('docker run -dp 8000:8000 --name %s docker.qsensei.com/fuse-free' % (
        container))
    setup_instance()
    start_instance()


@task
def reload_schema():
    stop_instance()
    setup_instance()
    start_instance()
    reindex()


def setup_instance():
    wait_for_container_ready()
    host = _get_server_host()
    with fuse_schema() as z:
        res = requests.put(
            'http://%s:8000/api/admin/instance' % host,
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
    host = _get_server_host()
    res = requests.post(
        'http://%s:8000/api/admin/instance' % host,
        json={'action': 'start'})
    res.raise_for_status()
    wait_for_ready()


def stop_instance():
    host = _get_server_host()
    res = requests.post(
        'http://%s:8000/api/admin/instance' % host,
        json={'action': 'stop'})
    res.raise_for_status()
    wait_for_stopped()


def wait_for_container_ready():
    url = 'http://%s:8000/api/admin/instance' % _get_server_host()
    for _ in xrange(20):
        try:
            res = requests.get(url)
            if res.status_code == 200:
                return
        except KeyboardInterrupt:
            raise
        except requests.ConnectionError:
            time.sleep(0.5)
    raise RuntimeError('Timeout waiting for container to start.')


def wait_for_ready():
    host = _get_server_host()
    for _ in xrange(10):
        res = requests.get(
            'http://%s:8000/api/admin/instance' % host)
        res.raise_for_status()
        if res.json()['ready']:
            return
        time.sleep(0.5)
    raise RuntimeError('Timeout while waiting for Fuse to be ready.')


def wait_for_stopped():
    host = _get_server_host()
    for _ in xrange(10):
        res = requests.get(
            'http://%s:8000/api/admin/instance' % host)
        res.raise_for_status()
        if res.json()['status'] == 'stopped':
            return
        time.sleep(0.5)
    raise RuntimeError('Timeout while waiting for Fuse to stop.')


@task
def reindex():
    host = _get_server_host()
    res = requests.post(
        'http://%s:8000/api/tasks/types/index' % host
    )
    res.raise_for_status()


@task
def teardown(container='dbpedia-tutorial'):
    run('docker rm -fv %s' % container)


def _get_server_host():
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
