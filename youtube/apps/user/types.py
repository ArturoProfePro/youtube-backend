from typing import NewType

from youtube.apps.user.schemas import UserReadSchema

SessionId = NewType('SessionId', str)

CurrentUser = NewType('CurrentUser', UserReadSchema)
