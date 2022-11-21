import streamlit as st
from toolz.functoolz import pipe
from typing import Optional
import openai
import json


openai.api_key = json.loads(st.secrets["openai_key"])['api_key']

# TODO: Monadic error handling
def get_request(prompt: str) -> Optional[openai.Completion]:
    try:
        return openai.Completion.create(model="text-davinci-002",
                                        prompt=prompt,
                                        max_tokens=700,
                                        temperature=0.1,
                                        top_p=1)
    except Exception:
        st.error("Error generating code review. Reload the webpage and try again.")
        return None


def format_response(response: Optional[openai.Completion]) -> str:
    try:
        return response.choices[0].text
    except Exception:
        return ""


def decode_st_code(st_code) -> Optional[str]:
    try:
        return st_code.read().decode("utf-8")
    except UnicodeDecodeError:
        return None


def get_output(prompt: str) -> str:
    return pipe(prompt, get_request, format_response)


@st.cache
def ai_magic(prompt: str, code):
    in_1 = prompt.format(Code=code)[-10000:]
    out_1 = get_output(in_1)
    in_2 = in_1 + out_1 + '\n\nRate the code from 1 to 10:'
    out_2 = get_output(in_2)
    fin = in_2 + out_2
    return out_1, out_2, fin, 0 if len(in_1) < 10000 else 1


