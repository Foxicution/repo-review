from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from toolz.functoolz import pipe

from src.files_from_github import file_list
from src.graphing import get_network_from_gh_filelist

app = FastAPI()

templates = Jinja2Templates(directory="frontend/templates")
app.mount("/frontend/static", StaticFiles(directory="frontend/static"), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("frontend/static/inode_logo.ico")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    data = {"page": "Home page"}
    return templates.TemplateResponse("page.html", {"request": request, "data": data})


@app.get("/tool", response_class=HTMLResponse)
async def tool(request: Request):
    data = {"page": "Tool page"}
    return templates.TemplateResponse("page.html", {"request": request, "data": data})


@app.get("/tool/{page_name}", response_class=HTMLResponse)
async def repo(request: Request, page_name: str):
    graph = pipe(
        "https://github.com/python/mypy",
        file_list,
        get_network_from_gh_filelist,
    )
    data = {"page": graph.__str__()}
    return templates.TemplateResponse("page.html", {"request": request, "data": data})
