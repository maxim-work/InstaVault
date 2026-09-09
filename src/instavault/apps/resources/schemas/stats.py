from pydantic import BaseModel


class Statistics(BaseModel):
    all_users: int
    banned_users: int
    all_resources: int
    new_users_since: int
    active_users_since: int
