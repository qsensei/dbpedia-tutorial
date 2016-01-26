import json

from SPARQLWrapper import SPARQLWrapper, JSON


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
  ?person rdf:type dbo:AmericanFootballPlayer ;
          dbo:team _:team ;
          foaf:name ?name ;
          foaf:isPrimaryTopicOf ?url .

  _:team rdf:type yago:NationalFootballLeagueTeams .
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
    FILTER(LANG(?collegeName) = 'en')
  }
  OPTIONAL {
    ?person dbp:highschool _:highschool .
    _:highschool rdfs:label ?highSchoolName .
    FILTER(LANG(?highSchoolName) = 'en')
  }
  OPTIONAL {
    ?person dbo:birthPlace _:birthPlace .
    _:birthPlace dbo:country _:birthCountry .
    _:birthCountry rdfs:label ?birthPlaceName .
    FILTER(LANG(?birthPlaceName) = 'en')
  }
} OFFSET 0 LIMIT 3
''')
client.setReturnFormat(JSON)
results = client.query().convert()
print json.dumps(results, indent=2)
