# repo-review
v2 of my code-review app called repo-review. Available on [repo-review.streamlit.app](https://repo-review.streamlit.app/)

Tests structure follows the root folder structure.

frontend contains FastAPI and all related files responsible for web integration.

src contains main runner code.

other files are for streamlit app integration until we finish frontend with FastAPI and Jinja.

To run it type `uvicorn frontend.app.main:app --reload` and open localhost `http://127.0.0.1:8000` in your browser

Project is being held up a bit while analysis of the stack graphs is being performed / possible migration to Rust.

Project on hold ATM
