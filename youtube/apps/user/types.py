from typing import NewType
from youtube.apps.user.schemas import UserReadSchema

CurrentUser = NewType('CurrentUser', UserReadSchema)
