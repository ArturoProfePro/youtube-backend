from pydantic import BaseModel

from youtube.schemas import CreateSchema, ReadSchema, UpdateSchema


class TagCategoryBaseSchema(BaseModel):
    name: str


class TagCategoryCreateSchema(TagCategoryBaseSchema, CreateSchema):
    pass


class TagCategoryUpdateSchema(UpdateSchema):
    name: str | None = None


class TagCategoryReadSchema(TagCategoryBaseSchema, ReadSchema):
    pass


class VideoTagCreateSchema(CreateSchema):
    name: str
    slug: str | None = None
    category: TagCategoryCreateSchema


class VideoTagUpdateSchema(UpdateSchema):
    category: TagCategoryUpdateSchema | None = None
    name: str | None = None
    slug: str | None = None


class VideoTagReadSchema(ReadSchema):
    name: str
    slug: str
    category: TagCategoryReadSchema
