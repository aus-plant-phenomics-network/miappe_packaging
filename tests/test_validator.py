# from appnlib.core.types import FieldInfo, Schema
# from rdflib import Namespace
# from rdflib.namespace import FOAF, XSD


# # ---------------------------------------------------------------------------------------
# # Test Schema Validator
# # ---------------------------------------------------------------------------------------
# class FFOAF(FOAF):
#     _NS = Namespace("http://fakefoaf.com")


# PersonBase = Schema(
#     rdf_resource=FOAF.Person,
#     attrs={
#         "firstName": FieldInfo(ref=FOAF.firstName, range=XSD.string, required=True),
#         "lastName": FieldInfo(ref=FOAF.lastName, range=XSD.string, required=True),
#         "age": FieldInfo(ref=FOAF.age, range=XSD.positiveInteger, required=False),
#     },
# )

# PersonExact = Schema(
#     rdf_resource=FOAF.Person,
#     attrs={
#         "firstName": FieldInfo(ref=FFOAF.firstName, range=XSD.string, required=True),
#         "lastName": FieldInfo(ref=FFOAF.lastName, range=XSD.string, required=True),
#         "age": FieldInfo(ref=FFOAF.age, range=XSD.positiveInteger, required=False),
#     },
# )

# PersonRequired = Schema(
#     rdf_resource=FOAF.Person,
#     attrs={
#         "firstName": FieldInfo(ref=FOAF.firstName, range=XSD.string, required=True),
#         "lastName": FieldInfo(ref=FOAF.lastName, range=XSD.string, required=True),
#         "birthday": FieldInfo(ref=FOAF.birthday, range=XSD.dateTime, required=False),
#     },
# )

# PersonPartial = Schema(
#     rdf_resource=FOAF.Person,
#     attrs={
#         "firstName": FieldInfo(ref=FOAF.firstName, range=XSD.string, required=True),
#         "lastName": FieldInfo(ref=FOAF.lastName, range=XSD.string, required=True),
#         "age": FieldInfo(ref=FOAF.age, range=XSD.positiveInteger, required=False),
#         "birthday": FieldInfo(ref=FOAF.birthday, range=XSD.dateTime, required=False),
#     },
# )
