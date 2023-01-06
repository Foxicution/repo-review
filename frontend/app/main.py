from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
    data = {"page": page_name}
    return templates.TemplateResponse("page.html", {"request": request, "data": data})
