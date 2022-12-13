from files_from_github import file_list
from streamlit import text_input, text
from toolz.functoolz import pipe
from graphing import get_network_from_gh_filelist

def main():
    pipe(text_input('Input repository link'), file_list, get_network_from_gh_filelist, text)

if __name__ == '__main__':
    main()
