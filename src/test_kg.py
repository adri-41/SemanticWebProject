from rdflib import Graph

g = Graph()
g.parse("data/kg.ttl", format="turtle")

print("Nombre de triplets :", len(g))
for s, p, o in g:
    print(s, p, o)
