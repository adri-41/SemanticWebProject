from pyshacl import validate
from rdflib import Graph

g = Graph()
g.parse("data/kg.ttl", format="turtle")

shacl = Graph()
shacl.parse("shapes/shacl.ttl", format="turtle")

conforms, results_graph, results_text = validate(
    g,
    shacl_graph=shacl,
    inference='rdfs',
    abort_on_first=False
)

print("Conforme :", conforms)
print(results_text)