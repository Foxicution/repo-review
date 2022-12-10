from files_from_github import get_files
from streamlit import text_input, text
from toolz.functoolz import pipe

def main():
    pipe(text_input('Input repository link'), get_files, list, text)

if __name__ == '__main__':
    main()
