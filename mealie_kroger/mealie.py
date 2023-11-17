from dataclasses import dataclass
from datetime import datetime
import requests
from urllib.parse import urljoin


@dataclass
class ShoppingList:
    name: str
    id: str
    created_at: datetime


@dataclass
class Food:
    name: str
    extras: object
    id: str


@dataclass
class Unit:
    name: str
    id: str


@dataclass
class ShoppingListItem:
    quantity: float
    unit: Unit
    food: Food
    note: str
    display: str


class MealieApi:
    def __init__(self, url: str, api_token: str) -> None:
        if not url:
            raise ValueError("Must provide mealie url")
        if not api_token:
            raise ValueError("Must provide mealie API token")

        self.url = url
        self.api_token = api_token

    def get_shopping_lists(
        self, page: int = -1, per_page: int = -1
    ) -> list[ShoppingList]:
        resp = requests.get(
            urljoin(
                self.url,
                f"/api/groups/shopping/lists?page={page}&perPage={per_page}&orderDirection=desc",
            ),
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        shopping_lists = []
        for shopping_list_json in resp.json()["items"]:
            shopping_lists.append(
                ShoppingList(
                    name=shopping_list_json["name"],
                    id=shopping_list_json["id"],
                    created_at=datetime.strptime(
                        shopping_list_json["createdAt"], "%Y-%m-%dT%H:%M:%S.%f"
                    ),
                )
            )

        return shopping_lists

    def get_shopping_list_items(self, list_id: str) -> list[ShoppingListItem]:
        resp = requests.get(
            urljoin(self.url, f"/api/groups/shopping/lists/{list_id}"),
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        shopping_list_items = []

        def get_unit(shopping_list_item_json) -> Unit:
            unit_json = shopping_list_item_json["unit"]
            if unit_json is None:
                return None
            return Unit(name=unit_json["name"], id=unit_json["id"])

        def get_food(shopping_list_item_json) -> Food:
            food_json = shopping_list_item_json["food"]
            if food_json is None:
                return None
            return Food(
                name=food_json["name"], extras=food_json["extras"], id=food_json["id"]
            )

        for shopping_list_item_json in resp.json()["listItems"]:
            shopping_list_items.append(
                ShoppingListItem(
                    quantity=shopping_list_item_json["quantity"],
                    unit=get_unit(shopping_list_item_json),
                    food=get_food(shopping_list_item_json),
                    note=shopping_list_item_json["note"],
                    display=shopping_list_item_json["display"],
                )
            )
        return shopping_list_items

    def get_foods(self, page: int = -1, per_page: int = -1) -> list[Food]:
        resp = requests.get(
            urljoin(
                self.url,
                f"/api/foods?page={page}&perPage={per_page}&orderDirection=desc",
            ),
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        foods = []
        for food_json in resp.json()["items"]:
            foods.append(
                Food(
                    name=food_json["name"],
                    extras=food_json["extras"],
                    id=food_json["id"],
                )
            )
        return foods

    def update_food_extras(self, food_id: str, name: str, extras: dict[str, str]):
        resp = requests.put(
            urljoin(
                self.url,
                f"/api/foods/{food_id}",
            ),
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
            },
            json={
                'extras': extras,
                'name': name
            }
        )
        resp.raise_for_status()
