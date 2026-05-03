from datetime import datetime
from pydantic import BaseModel


class Player(BaseModel):
    id: str
    nickname: str
    color: str
    cash: int = 1500
    position: int = 0
    properties: list[str] = []
    get_out_of_jail_free: int = 0
    in_jail: bool = False
    jail_turns: int = 0
    is_active: bool = True
    is_bankrupt: bool = False
    last_seen: datetime
