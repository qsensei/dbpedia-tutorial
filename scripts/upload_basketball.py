from urlparse import urlparse
import os
import re

from SPARQLWrapper import SPARQLWrapper, JSON
import requests


def query_people(offset=0, limit=100):
    """ Query for basketball players and their metadata.
    """
    client = SPARQLWrapper("http://dbpedia.org/sparql")
    client.setQuery('''
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT DISTINCT
        ?person
        ?name
        ?description
        ?url
        ?teamName as ?team
        ?positionName as ?position
        ?birthDate as ?birth_date
        ?draftYear as ?draft_year
        ?collegeName as ?college
        ?highSchoolName as ?high_school
        ?birthPlaceName as ?birth_place
    WHERE {
      ?person rdf:type dbo:BasketballPlayer ;
              dbp:team _:team ;
              foaf:name ?name ;
              foaf:isPrimaryTopicOf ?url .
      FILTER (!regex(?name, "^.+,.+$", "i"))

      _:team rdf:type yago:NationalBasketballAssociationTeams .
      _:team rdfs:label ?teamName .
      FILTER (LANG(?teamName) = 'en')

      OPTIONAL {
        ?person rdfs:comment ?description .
        FILTER (LANG(?description) = 'en')
      }
      OPTIONAL {
        ?person dbo:position _:position .
        _:position rdfs:label ?positionName .
        FILTER (LANG(?positionName) = 'en')
      }
      OPTIONAL {
        ?person dbo:birthDate ?birthDate .
        FILTER (DATATYPE(?birthDate) = xsd:date)
      }
      OPTIONAL {
        ?person dbo:draftYear ?draftYear .
      }
      OPTIONAL {
        ?person dbp:college _:college .
        _:college rdfs:label ?collegeName .
        FILTER (LANG(?collegeName) = 'en')
      }
      OPTIONAL {
        ?person dbp:highschool _:highschool .
        _:highschool rdfs:label ?highSchoolName .
        FILTER (LANG(?highSchoolName) = 'en')
      }
      OPTIONAL {
        ?person dbo:birthPlace _:birthPlace .
        _:birthPlace dbo:country _:birthCountry .
        _:birthCountry rdfs:label ?birthPlaceName .
        FILTER (LANG(?birthPlaceName) = 'en')
      }
    } OFFSET %(offset)d LIMIT %(limit)d
    ''' % {'offset': offset, 'limit': limit})
    client.setReturnFormat(JSON)
    result = client.query().convert()
    return result['results']['bindings']


def get_all_people():
    """ Return all basketball players and their metadata.
    """
    limit = 2000
    n_offset = 0
    results = []
    while True:
        offset = n_offset * limit
        print 'grabbing rows %d-%d' % (offset, offset + limit)

        import datetime
        start = datetime.datetime.now()
        new_results = query_people(offset=offset, limit=limit)
        dt = datetime.datetime.now() - start
        print ' ' * 4 + 'took %.1f seconds' % dt.total_seconds()

        if len(new_results) == 0:
            break
        results.extend(new_results)
        n_offset += 1
    return results


def convert_for_fuse(results):
    sort_key = lambda x: x['person']['value']
    results.sort(key=sort_key)
    fuseobjs = []
    fuseobj = None
    for athlete in results:
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
                fuseobj['birth_place'] = list(fuseobj['birth_place'])
                fuseobjs.append(fuseobj)
            fuseobj = {
                'fuse:type': 'athlete',
                'fuse:id': athlete_uri,
                'sport': 'Basketball',
                # initialize multi fields as sets to prevent duplicates
                'team': set(),
                'position': set(),
                'high_school': set(),
                'college': set(),
                'birth_place': set(),
            }
            # OPTIONAL fields in the query aren't always returned. We need to
            # catch KeyError
            for key in ('description', 'birth_date', 'draft_year', 'name',
                        'url'):
                try:
                    valuetype = athlete[key]['type']
                    value = athlete[key]['value']
                    if valuetype == 'typed-literal':
                        typ = athlete[key]['datatype']
                        if typ == 'http://www.w3.org/2001/XMLSchema#integer':
                            value = int(value)
                        elif typ == 'http://www.w3.org/2001/XMLSchema#float':
                            value = float(value)
                        elif typ == 'http://www.w3.org/2001/XMLSchema#date':
                            value = {'_date': value}
                    fuseobj[key] = value
                except (KeyError, ValueError):
                    pass

        for key in ('position', 'high_school', 'college', 'team',
                    'birth_place'):
            try:
                value = athlete[key]['value']
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
    return fuseobjs


def get_server_address():
    """ Try to figure out docker host from DOCKER_HOST.
    """
    docker_host = os.environ.get('DOCKER_HOST')
    if docker_host:
        return urlparse(docker_host).hostname
    return 'localhost'


def main():
    server_address = get_server_address()
    results = get_all_people()
    print 'uploading to Fuse'
    fuseobjs = convert_for_fuse(results)
    res = requests.post(
        'http://%s:8000/api/tasks/types/update' % server_address,
        json={'items': fuseobjs})
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
