import asyncio

# FIX FOR WINDOWS + PLAYWRIGHT + PYTHON 3.12
asyncio.set_event_loop_policy(
    asyncio.WindowsProactorEventLoopPolicy()
)

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from playwright.async_api import async_playwright

app = FastAPI()

# STATIC FILES
app.mount("/static", StaticFiles(directory="static"), name="static")

# TEMPLATES
templates = Jinja2Templates(directory="templates")


# -----------------------------
# CATEGORY DETECTION
# -----------------------------
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


# -----------------------------
# URL ANALYZER
# -----------------------------
async def analyze_url(target_url: str):

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

    async with async_playwright() as p:

        # LAUNCH BROWSER
        browser = await p.chromium.launch(
            headless=True
        )

        # CREATE PAGE
        page = await browser.new_page()

        # RESPONSE HANDLER
        def handle_response(response):

            try:

                request = response.request

                headers = response.headers

                content_type = headers.get(
                    "content-type",
                    ""
                )

                item = {
                    "url": response.url,
                    "method": request.method,
                    "status": response.status,
                    "content_type": content_type,
                    "resource_type": request.resource_type,
                    "request_headers": dict(request.headers),
                    "response_headers": dict(headers),
                }

                category = categorize(
                    content_type,
                    response.url
                )

                results[category].append(item)

            except Exception as e:
                print("ERROR:", e)

        # LISTEN TO NETWORK RESPONSES
        page.on("response", handle_response)

        # OPEN URL
        await page.goto(
            target_url,
            wait_until="domcontentloaded",
            timeout=120000
        )

        # EXTRA WAIT FOR LAZY REQUESTS
        await page.wait_for_timeout(5000)

        # CLOSE BROWSER
        await browser.close()

    return results


# -----------------------------
# HOME PAGE
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "data": None,
            "url": None
        }
    )


# -----------------------------
# ANALYZE ROUTE
# -----------------------------
@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    url: str = Form(...)
):

    try:

        # AUTO ADD HTTPS
        if not url.startswith("http"):
            url = "https://" + url

        # ANALYZE URL
        data = await analyze_url(url)
        print(data)
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "data": data,
                "url": url
            }
        )

    except Exception as e:

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "data": None,
                "url": url,
                "error": str(e)
            }
        )