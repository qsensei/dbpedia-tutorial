import json

from SPARQLWrapper import SPARQLWrapper, JSON


client = SPARQLWrapper("http://dbpedia.org/sparql")
client.setQuery('''
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX : <http://dbpedia.org/resource/>
SELECT DISTINCT ?name ?birth ?death ?occupationName ?description_en ?person
WHERE {
  ?person dbo:birthPlace :Germany .
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
} ORDER BY ?name OFFSET 0 LIMIT 3
''')
client.setReturnFormat(JSON)
results = client.query().convert()
print json.dumps(results, indent=2)
