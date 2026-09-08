"""
Module containing pagination schemas.
"""

from __future__ import annotations

from typing import Generic, Self, TypeVar

from pydantic import BaseModel, Field

from .base import BaseSchema


class PaginationRequestSchema(BaseSchema):
    """
    Pagination request schema.
    """

    page: int = Field(gt=0, default=1, description='Page number')
    page_size: int = Field(gt=0, le=20, default=8, description='Page size')

    def to_pagination_schema(self: Self) -> PaginationSchema:
        """
        Convert to a pagination schema using limit and offset.
        """
        return PaginationSchema(limit=self.page_size, offset=(self.page - 1) * self.page_size)


class AppliedPaginationResponseSchema(BaseSchema):
    """
    Applied pagination response schema.
    """

    page: int
    page_size: int
    count: int


class PaginationResponseSchema(BaseSchema):
    """
    Pagination response schema.
    """

    pagination: AppliedPaginationResponseSchema


class PaginationSchema(BaseModel):
    """
    Pagination schema using limit and offset.
    """

    limit: int
    offset: int


T = TypeVar('T')


class PaginationResultSchema(BaseModel, Generic[T]):
    """
    Pagination result schema.
    """

    objects: list[T]
    count: int
