from dataclasses import dataclass
from os.path import exists
from urllib.parse import quote, unquote

from git import Tree
from git.repo import Repo
from toolz.functoolz import pipe


@dataclass
class File:
    """represents a file in a repository"""

    path: str
    content: str


def random_string(string_length: int = 10) -> str:
    """generates a random string of fixed length"""
    from random import choice
    from string import ascii_lowercase

    letters = ascii_lowercase
    return "".join(choice(letters) for i in range(string_length))


def to_url(string: str) -> str:
    """converts a string to a url using % encoding"""
    return quote(string, safe="")


def from_url(url: str) -> str:
    """converts a url to a string using % decoding"""
    return unquote(url)


def format_repo_url(repo_url: str) -> str:
    """removes the storage system domain from the repo url"""
    return repo_url.split("github.com/")[-1]


def pull_repo(repo_path) -> Repo:
    """pulls the latest changes from a repository in a local directory"""
    repo = Repo(repo_path)
    repo.remote().pull()
    return repo


# TODO: add Result monad to handle errors
def get_repo(repo_url: str) -> Repo:
    """clones a repository to a local directory"""
    repo_path = f"repos/{pipe(repo_url, format_repo_url, to_url)}"
    return pull_repo(repo_path) if exists(repo_path) else Repo.clone_from(repo_url, repo_path)


def traverse_tree(tree: Tree, path: str = "") -> list[File]:
    """traverses a tree and returns the contents of each file"""
    for blob in tree.blobs:
        yield File(path=f"{path}/{blob.name}", content=blob.data_stream.read())
    for sub_tree in tree.trees:
        yield from traverse_tree(sub_tree, f"{path}/{sub_tree.name}")


def repo_file_list(repo: Repo) -> list[File]:
    """returns the contents of all files in a repository"""
    tree = repo.head.commit.tree
    return list(traverse_tree(tree))


def files_from_repository(repo_url: str) -> list[File]:
    """returns the contents of all files in a repository"""
    return pipe(repo_url, get_repo, repo_file_list)


def main():
    files_from_repository("https://github.com/Foxicution/repo-review")


if __name__ == "__main__":
    main()
