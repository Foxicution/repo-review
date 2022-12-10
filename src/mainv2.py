from github import Github, GithubException
from github.ContentFile import ContentFile
from github.Repository import Repository
from option import Result, Option, Ok, Err, NONE, Some
from lambdas import _
from streamlit import secrets, text_input, text
from streamlit.runtime.secrets import Secrets
from json import loads
from toolz.functoolz import pipe
from functools import partial
from typing import List, TypeVar, Callable, Any
from decorator import decorator
from custom_types import T


@decorator
def _try(function: Callable[..., T], *args, **kwargs) -> Result[T, Exception]:
    try:
        return Ok(function(*args, **kwargs))
    except Exception as e:
        return Err(e)

def github_hooks(secret: Secrets = secrets) -> Github:
    return pipe(secret['github_token'], loads, _['secondary'], Github)

@_try
def get_repository(repository_link: str, hooks: Github = github_hooks()) -> Result[Repository, GithubException]:
    return pipe(repository_link.removeprefix('https://github.com/'), hooks.get_repo)

def call_on_input(input, function: Callable[..., T]) -> Option[T]:
    return Some(function(input)) if input else NONE

def unpack_repository(repository: Option[Result[Repository, GithubException]]) -> Option[Repository]:
    return repository.map(lambda result: result.unwrap())

def repository(repository_link: str) -> Option[Repository]:
    return pipe(
        repository_link,
        partial(call_on_input, function=get_repository),
        unpack_repository)

def contents(repository_link: str) -> Option[List[ContentFile] | ContentFile]:
    return repository(repository_link).map(lambda repository: repository.get_contents(''))

def main():
    repository_contents = contents(text_input('Input repository link'))
    repository_contents.map(lambda contents: text(contents))
    
if __name__ == '__main__':
    main()
