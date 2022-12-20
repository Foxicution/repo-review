from functools import partial
from json import loads
from typing import Iterator, List

from github import Github, GithubException
from github.ContentFile import ContentFile
from github.Repository import Repository
from lambdas import _
from option import Option, Result
from streamlit import secrets
from streamlit.runtime.secrets import Secrets
from toolz.functoolz import pipe

from generics import call_on_input, try_decorator


def github_hooks(secret: Secrets = secrets) -> Github:
    return pipe(secret['github_token'], loads, _['secondary'], Github)


@try_decorator
def get_repository(repository_link: str, hooks: Github = github_hooks()) -> Result[Repository, GithubException]:
    return pipe(repository_link.removeprefix('https://github.com/'), hooks.get_repo)


def unpack_repository(repository: Option[Result[Repository, GithubException]]) -> Option[Repository]:
    return repository.map(lambda result: result.unwrap())


def repository(repository_link: str) -> Option[Repository]:
    return pipe(repository_link, partial(call_on_input, function=get_repository), unpack_repository)


def contents(repository: Option[Repository], directory: str = '') -> Option[List[ContentFile] | ContentFile]:
    return repository.map(lambda repository: repository.get_contents(directory))


# TODO: Reduce nesting and size of this function
def files(repository: Option[Repository]) -> Iterator[ContentFile | None]:
    base_contents = contents(repository)
    if base_contents.is_none:
        return None
    base_contents = base_contents.unwrap()
    while base_contents:
        content = base_contents.pop()
        if content.type == 'dir':
            base_contents.extend(contents(repository, content.path).unwrap())
        else:
            yield content


def get_files(repository_link: str) -> Iterator[ContentFile | None]:
    return pipe(repository_link, repository, files)


def file_list(repository_link: str) -> List[ContentFile]:
    """Returns an empty list if the repository link is empty"""
    return pipe(repository_link, get_files, list)
