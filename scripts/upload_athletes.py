from collections import defaultdict
from urlparse import urlparse
import json
import os
import re

import requests


def iterate_people():
    filename = os.environ.get('PEOPLE_NDJSON', 'var/people.ndjson')
    with open(filename) as f:
        for line in f:
            yield json.loads(line)


def iterate_fuse_objects():
    people = list(iterate_people())
    people.sort(key=lambda x: x['person']['value'])

    fuseobj = None
    for athlete in people:
        athlete_uri = athlete['person']['value']
        if fuseobj is None or fuseobj['fuse:id'] != athlete_uri:
            # if this is the initial iteration or the fuse:id is new, store
            # the fuseobj and create a new one
            if fuseobj is not None:
                # set is not JSON serializable - convert list before storing
                fuseobj['team'] = list(fuseobj['team'])
                fuseobj['position'] = list(fuseobj['position'])
                fuseobj['high_school'] = list(fuseobj['high_school'])
                fuseobj['college'] = list(fuseobj['college'])
                yield fuseobj
            fuseobj = defaultdict(set)
            fuseobj['fuse:type'] = 'athlete'
            fuseobj['fuse:id'] = athlete_uri
            dbo = 'http://dbpedia.org/ontology/'
            fuseobj['sport'] = {
                dbo + 'BaseballPlayer': 'Baseball',
                dbo + 'BasketballPlayer': 'Basketball',
                dbo + 'AmericanFootballPlayer': 'Football',
            }[convert_value(athlete['personType'])]
            for key in ('name', 'description', 'birth_date', 'sport',
                        'draft_year', 'url', 'birth_place'):
                try:
                    fuseobj[key] = convert_value(athlete[key])
                except KeyError:
                    pass
        for key in ('position', 'high_school', 'college', 'team'):
            try:
                value = convert_value(athlete[key])
            except KeyError:
                pass
            else:
                # Clean up the strings
                if isinstance(value, basestring):
                    value = re.sub('\(.*?\)', '', value).strip()
                    if key == 'college':
                        flags = re.X | re.I
                        exp = r'''
                            ((wo)?men\'s)?.*
                            (football|basketball|baseball).*$
                        '''
                        value = re.sub(exp, '', value, flags=flags).strip()
                fuseobj[key].add(value)


def convert_value(value_obj):
    valuetype = value_obj['type']
    value = value_obj['value']
    if valuetype == 'typed-literal':
        typ = value_obj['datatype']
        if typ == 'http://www.w3.org/2001/XMLSchema#integer':
            value = int(value)
        elif typ == 'http://www.w3.org/2001/XMLSchema#float':
            value = float(value)
        elif typ == 'http://www.w3.org/2001/XMLSchema#date':
            value = {'_date': value}
    return value


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
