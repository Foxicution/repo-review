import os
import random
import streamlit as st
from streamlit_components.graph_visualizer import my_component
from networkx import Graph
from pyvis.network import Network
from github import Github, Repository
from typing import Optional, Callable, Any, Pattern, AnyStr
from functools import wraps
import re
from toolz.functoolz import pipe
from python_components.types import T, Package
from python_components.networkx_graphing import get_graphs, without_keys
import pickle
import json
from python_components.large_lang_model import ai_magic
from google.cloud import firestore
from google.oauth2 import service_account
from python_components.large_lang_model import ai_magic

st.set_page_config(layout='wide')
if 'init' not in st.session_state:
    st.session_state.init = True


def replace_semicolons_with_new_line(code: str) -> str:
    return code.replace(';', '\n')


def extract_and_remove_pattern(pattern: Pattern[AnyStr], code: str) -> tuple[list[str], str]:
    return pattern.findall(code), pattern.sub('\n', code)


def remove_comments(code: str) -> str:
    return re.sub(re.compile('#.*?\n'), '', code)


def remove_docs(code: str) -> str:
    return re.sub(re.compile(re.compile(r'""".*?"""', re.DOTALL)), '', code)


def remove_strings(code: str) -> str:
    return re.sub(re.compile(r'".*?"'), '', code)


def remove_single_quote_strings(code: str) -> str:
    return re.sub(re.compile(r"'.*?'"), '', code)


def clean_code(code: str) -> str:
    return pipe(code, remove_comments, remove_docs, remove_strings, remove_single_quote_strings)


# TODO: rewrite this function into more functional style
def get_package_string_lines(code: str) -> list[str]:
    from_import_pattern = re.compile(r'(?:\s+)?from\s+(.+)(?:\n)')
    import_pattern = re.compile(r'(?:\s+)?import\s+(.+)(?:\n)')
    new_code = replace_semicolons_with_new_line(code)
    from_imports, new_code = extract_and_remove_pattern(from_import_pattern, new_code)
    imports, _ = extract_and_remove_pattern(import_pattern, new_code)
    return from_imports + imports


def format_package_string_lines(lines: list[str]):
    as_pattern = re.compile(r'\s+as\s+\w+')
    return [as_pattern.sub('', line) for line in lines]


def append_pak(from_pak: str, to_pak: str, edges: list[(str, str)]) -> tuple[str, str]:
    return edges.append((from_pak.strip(), to_pak.strip()))


def try_decorator(error_msg: str) -> Callable[[Callable[[Any], T]], Callable[[Any], Optional[T]]]:
    def decorator(f: Callable[[Any], T]) -> Callable[[Any], Optional[T]]:
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception:
                st.error(error_msg)
                return None

        return wrapper

    return decorator


@try_decorator('Error authenticating with github. Press F5 to reload the page and try again.')
def authenticate_github(token: str) -> Github:
    return Github(token)


@try_decorator('Error getting repo. Did you type the url correctly?')
def get_repo(repo_path: str) -> Repository:
    return g.get_repo(repo_path)


def vis_parameters(nx_graph: Graph) -> tuple[str, str]:
    nt = Network(directed=True, bgcolor='#f2f3f4')
    nt.from_nx(nx_graph)
    network_data = nt.get_network_data()
    vis_data = {"nodes": network_data[0], "edges": network_data[1]}
    return json.dumps(vis_data), nt.options.to_json()


def import_line_to_packages(import_line: str) -> Package:
    clean_line = re.sub('as\s+\S+', '', import_line).replace('.', '/')
    for symbol in ['\n', '(', ')', ',', 'import']:
        clean_line = clean_line.replace(symbol, '')
    packages = clean_line.split()
    return Package(packages[0], packages[1:])


def add_packages_to_root(package: Package) -> list[str]:
    if package.packages:
        return [f'{package.root}/{imported_package}' for imported_package in package.packages]
    else:
        return [f'{package.root}']


def packages_from_line(line: str, file_name: str) -> list[str]:
    package = import_line_to_packages(line)
    stripped_root = package.root.lstrip('/')
    difference = len(package.root) - len(stripped_root)
    if difference > 0:
        root_folder = "/".join(list(file_name.split('/')[:-difference]))
        package.root = f'{root_folder}{stripped_root}'
    return add_packages_to_root(package)


def file_package_imports(import_lines: list[str], file_name: str) -> list[str]:
    package_imports = []
    for line in import_lines:
        package_imports += packages_from_line(line, file_name)
    return package_imports


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    return tuple(int(h.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return '#' + ''.join(hex(x)[2:].zfill(2) for x in rgb)


def score_to_colour(score: float) -> str:
    green, red = hex_to_rgb('#7fe7dc'), hex_to_rgb('#f47a60')
    return pipe(map(lambda start, end: int(start + (end - start) / 9 * (score - 1)), red, green), tuple, rgb_to_hex)


@st.cache
def extract_data_from_repo(repo_link: str) -> list[dict]:
    nodes = []
    repo = pipe(repo_link.removeprefix('https://github.com/'), get_repo)
    contents = repo.get_contents('.')
    while contents:
        file_content = contents.pop(0)
        if file_content.type == 'dir':
            contents.extend(repo.get_contents(file_content.path))
        else:
            if file_content.path.endswith('.py'):
                file_path = file_content.path.rstrip('py').rstrip('.')
                file_content = file_content.decoded_content.decode()

                ###################################################
                code = clean_code(file_content)
                from_with_braces = re.compile(r'from\s+(.+\s+import\s+\((?:.|\n)+?\))')
                from_with_braces, new_code = extract_and_remove_pattern(from_with_braces, code)
                from_import = re.compile(r'from\s+(.+)')
                from_import, new_code = extract_and_remove_pattern(from_import, new_code)
                import_pattern = re.compile(r'import\s+(.+)')
                import_pattern, new_code = extract_and_remove_pattern(import_pattern, new_code)
                packages = file_package_imports(from_with_braces, file_path)
                packages += file_package_imports(from_import, file_path)
                packages += file_package_imports(import_pattern, file_path)

                ####################################################
                file_name = file_path.split('/')[-1]
                node_info = {'id': file_path,
                             'label': file_name,
                             'title': file_name,
                             'code': file_content,
                             'size': 20,
                             'imports': packages,
                             'type': 'internal'}
                average_score = 0
                for key, prompt in prompts.items():
                    try:
                        out_1, out_2, fin, exceed_len = ai_magic(prompt, code)
                        encoded_fin = fin.encode('utf-8')
                        save_prompt(encoded_fin, exceed_len)
                        score = int(re.findall(r'\d+', out_2)[0])
                        node_info[key] = {'response': f'1:{remove_empty_lines(out_1)}', 'score': score}
                        average_score += score
                        node_info['title'] = node_info['title'] + f'\n{key}: {score}'
                    except Exception:
                        print("API error")
                        score = 5
                        node_info[key] = {'response': f'Error in the API response', 'score': score}
                        average_score += score
                        node_info['title'] = node_info['title'] + f'\n{key}: {score}'
                average_score = average_score / 4
                node_info['color'] = score_to_colour(average_score)
                node_info['score'] = average_score

                nodes.append(node_info)
    with open(f"analyzed_repos/{repo_link.removeprefix('https://github.com/').replace('/', '_o_')}", 'wb') as f:
        pickle.dump(nodes, f)
    return nodes


def remove_empty_lines(text: str) -> str:
    return "\n".join([ll.rstrip() for ll in text.splitlines() if ll.strip()])


def save_prompt(fin: bytes, exceed_len: int):
    database.collection('ai_responses').add({'response': fin, 'exceeded_lenght': exceed_len})


def read_pickle(file_path):
    with open(file_path, 'rb') as f:
        return pickle.load(f)


def setup(secrets: dict) -> tuple[firestore.Client, dict, Github]:
    key_dict = json.loads(secrets["db_key"])
    credentials = service_account.Credentials.from_service_account_info(key_dict)
    return (firestore.Client(credentials=credentials),
           json.loads(secrets["prompts"]),
           authenticate_github(json.loads(secrets['github_token'])['secondary']))


database, prompts, g = setup(st.secrets)


def data_display(data, temp):
    temp.text("Repo-review in progress...")

    graph, sub_graph = get_graphs(data)
    vis_data, options = vis_parameters(graph)
    sub_data, sub_options = vis_parameters(sub_graph)
    chk = temp.checkbox('Show external modules')
    if chk:
        result = my_component(vis_data, options)
    else:
        result = my_component(sub_data, sub_options)
    if result == 0:
        print(result)
    else:
        node_data = graph.nodes.get(result)
        if node_data['type'] == 'external':
            with st.sidebar:
                st.text('File: ' + result + '.py')
                st.text('External module')
        else:
            with st.sidebar:
                st.text('File: ' + result + '.py')
                st.text(f"Overall score: {node_data['score']}")
                category = st.selectbox('Category', prompts.keys())
                st.text(category)
                st.text(f"Score: {node_data[category]['score']}")
                st.text(node_data[category]['response'])
                st.code(node_data['code'])


def dev_main():
    temp = st.empty()
    dir_to_repos = 'analyzed_repos/'
    analysed_repo_data = {}
    for repo_link in os.listdir(dir_to_repos):
        analysed_repo_data[repo_link.replace('_o_', '/')] = read_pickle(dir_to_repos + repo_link)
    with temp.container():
        repo_link = st.text_input('Input a github repo url (Hint: only open-source repos are supported for now)')
        analysed_repo = st.selectbox('Or choose an already analyzed one', analysed_repo_data.keys())
        button = st.button('Submit')
    if button:
        st.session_state['init'] = False
    if repo_link:
        data = extract_data_from_repo(repo_link)
    else:
        data = analysed_repo_data[analysed_repo]
    if not st.session_state['init']:
        data_display(data, temp)


def prod_main():
    temp = st.empty()
    dir_to_repos = 'analyzed_repos/'
    analysed_repo_data = {}
    for repo_link in os.listdir(dir_to_repos):
        analysed_repo_data[repo_link.replace('_o_', '/')] = read_pickle(dir_to_repos + repo_link)
    with temp.container():
        analysed_repo = st.selectbox('Or choose an already analyzed one', analysed_repo_data.keys())
        button = st.button('Submit')
    if button:
        st.session_state['init'] = False
    data = analysed_repo_data[analysed_repo]
    if not st.session_state['init']:
        data_display(data, temp)


def main(release: bool = False) -> None:
    if release:
        prod_main()
    else:
        dev_main()


if __name__ == "__main__":
    main(True)
