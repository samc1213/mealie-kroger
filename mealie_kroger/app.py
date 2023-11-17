from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from html import escape, unescape
from mealie_kroger.kroger import CartItemModel, KrogerApi
from mealie_kroger.mealie import MealieApi
from mealie_kroger.oauth import OAuthToken, OAuthProvider
from os import getenv
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

import json

client_id = getenv("KROGER_CLIENT_ID")
client_secret = getenv("KROGER_CLIENT_SECRET")

oauth_provider = OAuthProvider(
    client_id=client_id,
    client_secret=client_secret,
    access_token_url="https://api.kroger.com/v1/connect/oauth2/token",
    authorize_url="https://api.kroger.com/v1/connect/oauth2/authorize",
    scope="profile.compact product.compact cart.basic:write",
)

app = FastAPI()
secret_key = getenv("SESSION_SECRET_KEY")
app.add_middleware(SessionMiddleware, secret_key=secret_key)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

mealie_url = getenv("MEALIE_URL")
mealie_api_token = getenv("MEALIE_API_TOKEN")
mealie_api = MealieApi(mealie_url, mealie_api_token)
kroger_api = KrogerApi(oauth_provider)


def get_token_from_session(session):
    return None


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


@app.get("/add-to-cart")
async def add_to_cart(request: Request):
    if "list_id" not in request.query_params:
        raise HTTPException(status_code=422, detail="Must provide list_id parameter")

    shopping_list_id = request.query_params["list_id"]
    list_items = mealie_api.get_shopping_list_items(shopping_list_id)

    return templates.TemplateResponse(
        "add-to-cart.html.j2",
        {
            "request": request,
            "list_items": list_items,
            "shopping_list_id": shopping_list_id,
        },
    )


@app.post("/add-to-cart")
async def add_to_cart_post(request: Request):
    form_data = await request.form()
    list_items = mealie_api.get_shopping_list_items(form_data["shopping_list_id"])
    cart_items = []
    for list_item in list_items:
        if (
            list_item.food
            and list_item.food.extras
            and "kroger_upc" in list_item.food.extras
        ):
            cart_items.append(
                CartItemModel(quantity=1, upc=list_item.food.extras["kroger_upc"])
            )
    if "token" not in request.session:
        request.session["next"] = str(
            request.url_for(add_to_cart.__name__).include_query_params(
                list_id=form_data["shopping_list_id"]
            )
        )
        return RedirectResponse(
            request.url_for(login_via_kroger.__name__),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if cart_items:
        new_token = kroger_api.add_to_cart(
            OAuthToken.from_dict(request.session["token"]), cart_items
        )
        if new_token:
            request.session["token"] = new_token.to_dict()

    return RedirectResponse(
        request.url_for(index.__name__), status_code=status.HTTP_303_SEE_OTHER
    )


@app.post("/link-food")
async def link_food(request: Request):
    form_data = await request.form()
    current_extras = json.loads(unescape(form_data["extras"]))
    current_extras["kroger_upc"] = str(form_data["upc"])
    mealie_api.update_food_extras(form_data["id"], form_data["name"], current_extras)
    return RedirectResponse(
        request.url_for(link_foods.__name__), status_code=status.HTTP_303_SEE_OTHER
    )


@app.get("/link-foods")
async def link_foods(request: Request):
    foods = mealie_api.get_foods()
    foods = [{"food": f, "extras_escaped": escape(json.dumps(f.extras))} for f in foods]
    return templates.TemplateResponse(
        "link-foods.html.j2", {"request": request, "foods": foods}
    )


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html.j2",
        {
            "request": request,
            "locations": None,
            "shopping_lists": mealie_api.get_shopping_lists(),
        },
    )


@app.get("/login/kroger")
async def login_via_kroger(request: Request):
    url = oauth_provider.get_authorize_url(request.url_for(auth_via_kroger.__name__))
    return RedirectResponse(url)


@app.get("/auth/kroger")
async def auth_via_kroger(request: Request):
    token = oauth_provider.get_access_token(
        request.query_params, request.url_for(auth_via_kroger.__name__)
    )
    request.session["token"] = token.to_dict()
    if "next" in request.session:
        redirect = request.session["next"]
        del request.session["next"]
    else:
        redirect = request.url_for(index.__name__)

    return RedirectResponse(redirect)
