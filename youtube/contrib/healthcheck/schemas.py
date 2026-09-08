from youtube.schemas.base import BaseSchema


class StatusOkResponseSchema(BaseSchema):
    """
    Successful response schema.
    """

    status: str = 'ok'
