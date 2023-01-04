benchmarks for time graphing would take to run across all commits
tested using src/streamlit_ui.py 2023-01-03
to run use `scalene src/streamlit_ui.py` in the terminal
this will generate a report inside of the main directory called profile.html and profile.json


| repository                             | single commit time | every commit time | tree build time |
|----------------------------------------|--------------------|-------------------|-----------------|
| https://github.com/google/python-fire  | 7.463s             | 0.5h              | 2.410s          |
| https://github.com/EleutherAI/gpt-neox | 5.366s             | 2.5h              | 4.337s          |
| https://github.com/python/mypy         | 1m:26.681s         | 10.8246528 days   | 30.285s         |
