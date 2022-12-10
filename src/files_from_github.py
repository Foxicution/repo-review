from github import Github, GithubException
from github.ContentFile import ContentFile
from github.Repository import Repository
from option import Result, Option
from lambdas import _
from streamlit import secrets, text_input, cache
from streamlit.runtime.secrets import Secrets
from json import loads
from toolz.functoolz import pipe
from functools import partial
from typing import Iterator, List

from generics import try_decorator, call_on_input


def github_hooks(secret: Secrets = secrets) -> Github:
    return pipe(secret['github_token'], loads, _['secondary'], Github)

@try_decorator
def get_repository(repository_link: str, hooks: Github = github_hooks()) -> Result[Repository, GithubException]:
    return pipe(repository_link.removeprefix('https://github.com/'), hooks.get_repo)

def unpack_repository(repository: Option[Result[Repository, GithubException]]) -> Option[Repository]:
    return repository.map(lambda result: result.unwrap())

@cache(hash_funcs={Option: hash})
def repository(repository_link: str) -> Option[Repository]:
    return pipe(
        repository_link,
        partial(call_on_input, function=get_repository),
        unpack_repository)

def contents(repository: Option[Repository], directory: str = '') -> Option[List[ContentFile] | ContentFile]:
    return repository.map(lambda repository: repository.get_contents(directory))

#TODO: Reduce nesting and size of this function
def files(repository: Option[Repository]) -> Iterator[ContentFile]:
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

def get_files(repository_link: str) -> Iterator[ContentFile]:
    return pipe(repository_link, repository, files)

def main():
    pipe(text_input('Input repository link'), repository, files, list, print)
    
if __name__ == '__main__':
    main()
