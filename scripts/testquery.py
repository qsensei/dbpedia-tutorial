import json

from SPARQLWrapper import SPARQLWrapper, JSON


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
} OFFSET 0 LIMIT 3
''')
client.setReturnFormat(JSON)
results = client.query().convert()
print json.dumps(results, indent=2)
