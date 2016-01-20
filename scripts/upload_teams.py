from urlparse import urlparse
import os
import re

from SPARQLWrapper import SPARQLWrapper, JSON
import requests


def query_people(offset=0, limit=100):
    """ Query for American Football players and their metadata and triples.
    """
    client = SPARQLWrapper("http://dbpedia.org/sparql")
    client.setQuery('''
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT DISTINCT
        ?team
        ?teamType
        ?name
        ?url
        ?description
        ?arenaLocationName as ?city
        ?playerName as ?players
    WHERE {
      ?team rdf:type ?teamType .
      FILTER(
        (?teamType = yago:NationalFootballLeagueTeams) ||
        (?teamType = yago:NationalBasketballAssociationTeams) ||
        (?teamType = yago:MajorLeagueBaseballTeams)
      )

      ?team rdfs:label ?name ;
            foaf:isPrimaryTopicOf ?url .
      FILTER(LANG(?name) = 'en')

      ?team rdf:type ?teamType .

      OPTIONAL {
        ?team rdfs:comment ?description .
        FILTER(LANG(?description) = 'en')
      }
      OPTIONAL {
        _:arena dbo:tenant ?team .
        _:arena dbo:location _:arenaLocation .
        _:arenaLocation rdf:type dbo:City .
        _:arenaLocation rdfs:label ?arenaLocationName .
        FILTER(LANG(?arenaLocationName) = 'en')
      }
    } OFFSET %(offset)d LIMIT %(limit)d
    ''' % {'offset': offset, 'limit': limit})
    client.setReturnFormat(JSON)
    result = client.query().convert()
    return result['results']['bindings']


def query_team_players(offset, limit):
    client = SPARQLWrapper("http://dbpedia.org/sparql")
    client.setQuery('''
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT DISTINCT
      ?team
      group_concat(?playerName, '|') as ?players
    WHERE {
      ?team rdf:type _:teamType .
      FILTER(
        (_:teamType = yago:NationalFootballLeagueTeams) ||
        (_:teamType = yago:NationalBasketballAssociationTeams) ||
        (_:teamType = yago:MajorLeagueBaseballTeams)
      )

      _:player dbo:team|dbp:team ?team ;
               rdf:type dbo:Athlete ;
               rdfs:label ?playerName .
      FILTER(LANG(?playerName) = 'en')
    } GROUP BY ?team OFFSET %(offset)d LIMIT %(limit)d
    ''' % {'offset': offset, 'limit': limit})
    client.setReturnFormat(JSON)
    result = client.query().convert()
    return result['results']['bindings']


def get_all_people():
    """ Return all American football players and their metadata as triples.
    """
    fns = [query_people, query_team_players]
    fn = fns.pop(0)

    limit = 2000
    n_offset = 0
    results = []
    while True:
        offset = n_offset * limit
        print 'grabbing rows %d-%d' % (offset, offset + limit)

        import datetime
        start = datetime.datetime.now()
        new_results = fn(offset=offset, limit=limit)
        dt = datetime.datetime.now() - start
        print ' ' * 4 + 'took %.1f seconds' % dt.total_seconds()

        if len(new_results) == 0:
            try:
                fn = fns.pop(0)
                n_offset = 0
                continue
            except IndexError:
                break
        results.extend(new_results)
        n_offset += 1
    return results


def convert_for_fuse(results):
    sort_key = lambda x: (x['team']['value'], x.get('name') is None)
    results.sort(key=sort_key)
    fuseobjs = []
    fuseobj = None

    fields = ('description', 'city', 'players')
    for result in results:
        uri = result['team']['value']
        if fuseobj is None or fuseobj['fuse:id'] != uri:
            # if this is the initial iteration or the fuse:id is new, store
            # the fuseobj and create a new one
            if fuseobj is not None:
                # set is not JSON serializable - convert list before storing
                for field in fields:
                    fuseobj[field] = list(fuseobj[field])
                fuseobjs.append(fuseobj)
            fuseobj = {
                'fuse:type': 'team',
                'fuse:id': uri,
                'name': re.sub('\(.*?\)', '', result['name']['value']).strip(),
                'url': result['url']['value'],
            }
            yago = 'http://dbpedia.org/class/yago/'
            fuseobj['sport'] = {
                yago + 'MajorLeagueBaseballTeams': 'Baseball',
                yago + 'NationalFootballLeagueTeams': 'Football',
                yago + 'NationalBasketballAssociationTeams': 'Basketball',
            }[result['teamType']['value']]
            for field in fields:
                fuseobj[field] = set()
        for field in fields:
            try:
                value = result[field]['value']
            except KeyError:
                pass
            else:
                if field == 'players':
                    players = set(value.split('|'))
                    players = {re.sub('\(.*?\)', '', x).strip()
                               for x in players}
                    fuseobj[field] |= players
                else:
                    fuseobj[field].add(value)
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
    fuseobjs = convert_for_fuse(results)
    res = requests.post(
        'http://%s:8000/api/tasks/types/update' % server_address,
        json={'items': fuseobjs})
    res.raise_for_status()


if __name__ == '__main__':
    main()
