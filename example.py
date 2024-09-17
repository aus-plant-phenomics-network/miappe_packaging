# %%
import msgspec
from rdflib import URIRef

from appnlib.core.dataclass import DEFAULT_CODEC, default_dec_hook, default_enc_hook
from appnlib.core.types import FieldInfo, Schema

StudySchema = Schema(
    rdf_resource=URIRef("http://purl.org/ppeo/PPEO.owl#study"),
    attrs={
        "factor": FieldInfo(
            ref=URIRef("http://purl.org/ppeo/PPEO.owl#hasFactor"),
            resource_ref=URIRef("http://purl.org/ppeo/PPEO.owl#experimentalFactor"),
        )
    },
)

bytes_data = msgspec.json.encode(StudySchema, enc_hook=default_enc_hook)
decoded_data = msgspec.json.decode(bytes_data, type=Schema, dec_hook=default_dec_hook)
# %%
