from urlparse import urlparse
import os

from SPARQLWrapper import SPARQLWrapper, JSON
import requests


def query_people(birthplace, offset=0, limit=100):
    client = SPARQLWrapper("http://dbpedia.org/sparql")
    client.setQuery('''
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX : <http://dbpedia.org/resource/>
    SELECT DISTINCT ?name ?birth ?death ?occupationName ?description_en ?person
    WHERE {
      ?person dbo:birthPlace :%(birthplace)s .
      ?person dbo:birthName ?name .
      ?person dbo:birthDate ?birth .
      ?person dbo:deathDate ?death .
      ?person rdfs:comment ?description_en .

      OPTIONAL {
        ?person dbo:occupation ?occupation .
        ?occupation rdfs:label ?occupationName .
        FILTER (LANG(?occupationName) = 'en') .
      }

      FILTER (LANG(?description_en) = 'en') .
      FILTER (DATATYPE(?birth) = xsd:date) .
      FILTER (DATATYPE(?death) = xsd:date) .
    } ORDER BY ?name OFFSET %(offset)d LIMIT %(limit)d
    ''' % {'birthplace': birthplace, 'offset': offset, 'limit': limit})
    client.setReturnFormat(JSON)
    return client.query().convert()['results']['bindings']


def convert_for_fuse(results):
    people = {x['person']['value'] for x in results}
    fuseobjs = []
    for person in people:
        fuseobj = {
            'fuse:type': 'person',
            'fuse:id': person
        }
        matches = filter(lambda x: x['person']['value'] == person, results)
        fuseobj['name'] = matches[0]['name']['value']
        fuseobj['birth'] = {'_date': matches[0]['birth']['value']}
        fuseobj['death'] = {'_date': matches[0]['death']['value']}
        fuseobj['description'] = matches[0]['description_en']['value']
        fuseobj['url'] = matches[0]['person']['value']
        fuseobj['occupation'] = []
        for match in matches:
            try:
                occupation = match['occupationName']['value']
            except KeyError:
                continue
            fuseobj['occupation'].append(occupation)
        fuseobjs.append(fuseobj)
    return fuseobjs


def main():
    server_address = _get_server_address()
    results = query_people('Germany')
    fuseobjs = convert_for_fuse(results)
    res = requests.post(
        'http://%s:8000/api/tasks/types/update' % server_address,
        json={'items': fuseobjs})
    res.raise_for_status()


def _get_server_address():
    docker_host = os.environ.get('DOCKER_HOST')
    if docker_host:
        return urlparse(docker_host).hostname
    return 'localhost'


if __name__ == '__main__':
    main()
