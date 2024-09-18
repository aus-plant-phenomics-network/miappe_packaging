# %%
from typing import Optional, Set

import msgspec


class User(msgspec.Struct, dict=True):
    """A struct representing a user"""

    name: str
    groups: Set[str] = set()
    email: Optional[str] = None


class User2(msgspec.Struct):
    """An updated version of the User struct, now with a phone number"""

    name: str
    groups: Set[str] = set()
    email: Optional[str] = None
    phone: Optional[str] = None


old_dec = msgspec.json.Decoder(User)

new_dec = msgspec.json.Decoder(User2)

new_msg = msgspec.json.encode(User2("bob", groups={"finance"}, phone="512-867-5309"))

user = old_dec.decode(new_msg)

# %%
