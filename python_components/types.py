from typing import TypeVar
from dataclasses import dataclass

T = TypeVar('T')


@dataclass
class Package:
    root: str
    packages: list[str]
