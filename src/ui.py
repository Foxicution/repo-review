from files_from_github import file_list
from streamlit import text_input, text
from toolz.functoolz import pipe

def main():
    pipe(text_input('Input repository link'), file_list, text)

if __name__ == '__main__':
    main()
