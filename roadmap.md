
###  12/09/2024

- [ ] Add to for method `to_builtins` for different scenarios. Currently, composite graph (graph with more than one entity) does not test reliably. This is because ordering of list is also compared, which is exacerbated by the fact that rdf.Graph is a generator with non-deterministic iterator. Either look for a unittest method that reliably tests list of objects or have to write the test utility. Not the highest of priority since the `to_struct` method has passed.
- [ ] Add validation at construction - `msgsec` typically validates data at serialisation, deserialisation. This makes sense in the wider context since it assumes data transferred is via HTTP with minimal input from the actual user. In our use-case. this could be too limiting since we will need to constantly validate user data. Possible to move to pydantic at some points.
- [ ] Type coercion and strict type checking - i.e. given string, convert to `datetime.datetime` or given `datetime.date` convert to `datetime.datetime` and vice-versa. Currently, `msgspec` will raise an error at serialisation when the data type does not match exactly the annotation type, which could be too strict.
