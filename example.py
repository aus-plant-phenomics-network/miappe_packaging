# %%
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import XSD, FOAF, RDF


graph = Graph()
Obama = URIRef("Obama")
Biden = BNode()
graph.add((Obama, RDF.type, FOAF.Person))
graph.add((Biden, RDF.type, FOAF.Person))
graph.add((Obama, FOAF.firstName, Literal("Barrack")))
graph.add((Biden, FOAF.firstName, Literal("Joe")))
graph.add((Obama, FOAF.knows, Biden))
graph.add((Biden, FOAF.knows, Literal([Obama, Biden])))


graph.serialize("people.json", format="json-ld", context={"foaf": FOAF._NS})

# %%
