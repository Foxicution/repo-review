from typing import Callable, TypeVar

from option import NONE, Err, Ok, Option, Result, Some

T = TypeVar('T')


def try_decorator(function: Callable[..., T]) -> Callable[..., Result[T, Exception]]:
    """Decorator that wraps a function in a try/except block and returns a Result monad"""
    def wrapper(*args, **kwargs) -> Result[T, Exception]:
        try:
            return Ok(function(*args, **kwargs))
        except Exception as e:
            return Err(e)
    return wrapper


def call_on_input(input, function: Callable[..., T]) -> Option[T]:
    """Calls a function on an input if the input is not None and returns an Option monad"""
    return Some(function(input)) if input else NONE
