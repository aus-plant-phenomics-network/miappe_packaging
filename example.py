# %%
from pydantic import create_model

DynamicFoobarModel = create_model("DynamicFoobarModel", foo=(str, ...), bar=(int, 123))
