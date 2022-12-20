from toolz.functoolz import pipe

from files_from_github import file_list
from graphing import get_network_from_gh_filelist


def main():
    pipe("https://github.com/Foxicution/trello-weekday-list-automation", file_list, get_network_from_gh_filelist, print)


if __name__ == '__main__':
    main()
