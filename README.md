# core

## Overview

This package provides a set of APIs to define many aspects of a project in a way that conforms to the [MIAPPE](https://www.miappe.org/overview/) standard. MIAPPE conformant metadata is stored as an RDF graph and can be serialised to a `json-ld` file that conforms to the [RO-Crate](https://www.researchobject.org/ro-crate/) standard.

## Quick-start

Install either `pdm` or `poetry`. Note: install poetry or pdm globally with `pipx` so you can reuse the package manager for other repos. In this document,
we will use `pdm` since it is the command used in the make file.

```bash
pipx install pdm
```

Install dependencies:

```bash
pdm install
```

## Example

```python
import datetime
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Annotated, NamedTuple, TypedDict

from msgspec import field
from rdflib.namespace import FOAF

from appnlib.core.schema import FieldInfo, IDRef, Schema
from appnlib.core.struct import LinkedDataClass, Registry


class Person(LinkedDataClass):
    __rdf_resource__ = FOAF.Person
    __rdf_context__ = FOAF._NS
    firstName: str
    lastName: str
    birthdate: datetime.date
    mbox: str | None = None
    knows: Annotated[
        list[str],
        FieldInfo(ref=FOAF.knows, range=IDRef(ref=FOAF.Person), repeat=True),
    ] = field(default_factory=list)


class Group(LinkedDataClass):
    __schema__ = Schema(
        __rdf_resource__=FOAF.Group,
        attrs={
            "member": FieldInfo(FOAF.member, range=IDRef(ref=FOAF.Person), repeat=True)
        },
    )
    member: list[str]


ID_POOL = {
    "BarrackObama": "http://example.org/BarrackObama",
    "JoeBiden": "http://example.org/JoeBiden",
    "BillClinton": "http://example.org/BillClinton",
    "AlGore": "http://example.org/AlGore",
}

Obama = Person(
    id=ID_POOL["BarrackObama"],
    firstName="Barrack",
    lastName="Obama",
    birthdate=datetime.datetime(1961, 8, 4),
    knows=[ID_POOL["JoeBiden"], ID_POOL["BillClinton"]],
)

Biden = Person(
    id=ID_POOL["JoeBiden"],
    firstName="Joe",
    lastName="Biden",
    birthdate=datetime.date(1942, 11, 20),
    knows=[ID_POOL["BarrackObama"]],
)

Clinton = Person(
    id=ID_POOL["BillClinton"],
    firstName="Bill",
    lastName="Clinton",
    birthdate=datetime.datetime(1946, 8, 19),
    knows=[ID_POOL["AlGore"], ID_POOL["BarrackObama"]],
)

AlGore = Person(
    id=ID_POOL["AlGore"],
    firstName="Al",
    lastName="Gore",
    birthdate=datetime.datetime(1948, 3, 31),
    knows=[ID_POOL["BillClinton"]],
)

Presidents = Group(
    id="http://example.org/USPresidents",
    member=[ID_POOL["BarrackObama"], ID_POOL["BillClinton"], ID_POOL["JoeBiden"]],
)
VicePresidents = Group(
    id="http://example.org/USVicePresidents",
    member=[ID_POOL["AlGore"], ID_POOL["JoeBiden"]],
)

registry = Registry()

registry.serialize(destination="WhiteHouse.json", context={"foaf": FOAF._NS})

```

## Design

Each Python LinkedDataClass defines a schema for a particular resource (`rdfs:Resource`). The resource type information is stored using the special attribute [`__rdf_resource__`](#__rdf_resource__). Each instance of a LinkedDataClass has an [`id`](#id) that uniquely identify any instance of a resource within the graph.

The attributes of a semantic class define a property (`rdf:Property`) and will by default have `__rdf_resource__` as its domain.

# Appendix

## Special attributes

### `id`

Represents the identifier for a resource instance. id values can be supplied by the user, in which case, it must be a globally unique URI, or minted automatically as a blank node.

### `__rdf_resource__`

`__rdf_resource__` is a read-only class attribute that describes the type of a resource instance. For any instance of a LinkedDataClass, this information will be serialised as `(id, rdf.type, __rdf_resource)`.


## MIAPPE Schema Language

## RDF Terms

- IRI (`URIRef` in `rdflib`): a unicode string conforming to IRI [syntax](https://www.ietf.org/rfc/rfc3987.txt)
- Literal (`Literal` in `rdflib`): literal values such as string, numbers and dates.
- Blank (`BNode` in `rdflib`): local identifiers used in some concrete RDF store/syntaxes. Locally scoped to the file or RDF store and are not persistent or portal identifiers for blank nodes.

## Serialisation Note:

The official document (See section [3.5](https://www.w3.org/TR/2014/REC-rdf11-concepts-20140225/#dfn-blank-node-identifier)) specifies that IRIs may be minted to replace Blank Nodes in an RDF graph. This IRIs should be globally unique. The official document recommends using `/<well-known>/genid/<BNode value>` to replace a BNode with an IRI, where `well-known` is a well-known IRI.

## RDF Grammar in `rdflib` syntax
```
subject := URIRef | BNode
predicate := URIRef
object := URIRef | Literal | BNode
term := URIRef | Literal | BNode
statement := (subject, predicate, object)
graph := {statement+}
graphName := URIRef | BNode
namedGraph := (graphName, graph)
defaultGraph := graph?
dataset := (defaultGraph, {namedGraph+})
```
