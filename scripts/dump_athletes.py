from collections import defaultdict
import json
import os
import re

from SPARQLWrapper import SPARQLWrapper, JSON


def query_people(offset=0, limit=100):
    client = SPARQLWrapper("http://dbpedia.org/sparql")
    client.setQuery('''
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT DISTINCT
        ?person
        ?personType
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
      ?person rdf:type ?personType ;
              dbo:team|dbp:team _:team ;
              dbo:position _:position ;
              foaf:name ?name ;
              foaf:isPrimaryTopicOf ?url ;
              rdfs:comment ?description ;
              dbo:birthDate ?birthDate .
      _:team rdf:type _:teamType .
      FILTER (
        (!regex(?name, "^.+,.+$", "i")) &&
        (LANG(?description) = 'en') &&
        (DATATYPE(?birthDate) = xsd:date) &&
        (
            (
                (?personType = dbo:BaseballPlayer) &&
                (_:teamType = yago:MajorLeagueBaseballTeams)
            ) ||
            (
                (?personType = dbo:BasketballPlayer) &&
                (_:teamType = yago:NationalBasketballAssociationTeams)
            ) ||
            (
                (?personType = dbo:AmericanFootballPlayer) &&
                (_:teamType = yago:NationalFootballLeagueTeams)
            )
        )
    )

      _:team rdfs:label ?teamName .
      FILTER (LANG(?teamName) = 'en')

      _:position rdfs:label ?positionName .
      FILTER (LANG(?positionName) = 'en')

      OPTIONAL {
        ?person dbo:draftYear ?draftYear .
      }
      OPTIONAL {
        ?person dbp:college ?college .
        ?college rdfs:label ?collegeName .
        FILTER(LANG(?collegeName) = 'en')
      }
      OPTIONAL {
        ?person dbp:highschool ?highschool .
        ?highschool rdfs:label ?highSchoolName .
        FILTER(LANG(?highSchoolName) = 'en')
      }
      OPTIONAL {
        ?person dbo:birthPlace _:birthPlace .
        _:birthPlace dbo:country _:birthCountry .
        _:birthCountry rdfs:label ?birthPlaceName .
        FILTER(LANG(?birthPlaceName) = 'en')
      }
    } OFFSET %(offset)d LIMIT %(limit)d
    ''' % {'offset': offset, 'limit': limit})
    client.setReturnFormat(JSON)

    print 'grabbing rows %d-%d' % (offset, offset + limit)
    import datetime
    start = datetime.datetime.now()

    result = client.query().convert()

    dt = datetime.datetime.now() - start
    print ' ' * 4 + 'took %.1f seconds' % dt.total_seconds()
    return result['results']['bindings']


def get_people(max_limit=None):
    limit = 2000
    n_offset = 0
    people = []
    while True:
        offset = n_offset * limit
        results = query_people(offset=offset, limit=limit)
        if len(results) == 0:
            break
        people.extend(results)
        n_offset += 1
    return people


def iterate_fuse_objects(max_limit=None):
    """ Generate all Fuse objects from the entire list of people.

    We'll:
    1. Sort all the rows returned by the URI.
    2. Group each set of URIs into a single Fuse object.
    3. yield the last Fuse object when the new URI comes.

    If you are not familiar with Python yield statements, see:

        http://stackoverflow.com/questions/231767/what-does-the-yield-keyword-do-in-python

    """
    people = get_people(max_limit=max_limit)
    people.sort(key=lambda x: x['person']['value'])

    fuseobj = None
    for athlete in people:
        athlete_uri = athlete['person']['value']
        if fuseobj is None or fuseobj['fuse:id'] != athlete_uri:
            # if this is the initial iteration or the fuse:id is new, yield
            # the fuseobj and create a new one
            if fuseobj is not None:
                # set is not JSON serializable - convert list before yielding
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
    """ Convert the SPARQL json object dictionary into a Fuse type.
    """
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


def main():
    # Get some custom variables from the environment (mostly for testing)
    # PEOPLE_DUMP_LIMIT decides how many people we'll dump to file.
    # PEOPLE_JSON specifies a custom athletes file location.
    max_limit = int(os.environ.get('PEOPLE_DUMP_LIMIT'))
    filename = os.environ.get('PEOPLE_JSON', 'var/athletes.json')
    items = []
    for person in iterate_fuse_objects(max_limit=max_limit):
        items.append(person)
    with open(filename, 'w') as f:
        json.dump({'items': items}, f, indent=2)


if __name__ == '__main__':
    main()
