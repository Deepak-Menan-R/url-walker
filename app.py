from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import time

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


def categorize(content_type: str, url: str):
    content_type = (content_type or "").lower()

    if "text/html" in content_type:
        return "html"

    elif "application/json" in content_type:
        return "json"

    elif "javascript" in content_type:
        return "javascript"

    elif "text/css" in content_type:
        return "css"

    elif content_type.startswith("image/"):
        return "images"

    elif content_type.startswith("video/") or any(
        ext in url for ext in [".m3u8", ".mp4", ".webm", ".ts"]
    ):
        return "media"

    elif "font" in content_type:
        return "fonts"

    return "other"


def analyze_url(target_url: str):
    results = {
        "html": [],
        "json": [],
        "javascript": [],
        "css": [],
        "images": [],
        "media": [],
        "fonts": [],
        "other": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        captured = []

        def handle_response(response):
            try:
                request = response.request

                headers = response.headers
                content_type = headers.get("content-type", "")

                item = {
                    "url": response.url,
                    "method": request.method,
                    "status": response.status,
                    "content_type": content_type,
                    "resource_type": request.resource_type,
                }

                category = categorize(content_type, response.url)

                results[category].append(item)

            except Exception as e:
                print("Error:", e)

        page.on("response", handle_response)

        page.goto(target_url, wait_until="networkidle", timeout=120000)

        # wait a little more for lazy-loaded requests
        time.sleep(5)

        browser.close()

    return results


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
    request=request,
    name="index.html",
    context={
        "data": None
    }
)


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(request: Request, url: str = Form(...)):
    data = analyze_url(url)

    return templates.TemplateResponse(
    request=request,
    name="index.html",
    context={
        "data": None
    }
)