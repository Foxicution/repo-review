from dataclasses import dataclass
from typing import TypeVar

T = TypeVar('T')


@dataclass
class Package:
    root: str
    packages: list[str]
