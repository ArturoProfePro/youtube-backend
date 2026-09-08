"""
Module containing exceptions for tests.
"""

from typing import Self

from youtube.exceptions import BusinessLogicException


class CustomTestError(BusinessLogicException):
    """
    Test error.
    """

    @property
    def message(self: Self) -> str:
        return 'Test message'
