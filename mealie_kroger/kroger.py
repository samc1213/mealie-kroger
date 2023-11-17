from dataclasses import dataclass, asdict
from typing import Optional

from mealie_kroger.oauth import OAuthToken, OAuthProvider

@dataclass
class CartItemModel:
    quantity: int
    upc: str

@dataclass
class KrogerLocation:
    id: str
    name: str
    address_line_1: str
    city: str
    state: str

class KrogerApi:
    def __init__(self, oauth_provider: OAuthProvider) -> None:
        self.oauth_provider = oauth_provider

    def add_to_cart(self, token: OAuthToken, cart_items: list[CartItemModel]) -> Optional[OAuthToken]:
        _, new_token = self.oauth_provider.put(
            token,
            f"https://api.kroger.com/v1/cart/add",
            json={"items": [asdict(c) for c in cart_items]},
        )
        return new_token


    def get_kroger_locations_from_api(self, locations_response) -> list[KrogerLocation]:
        return [self._get_kroger_location_from_api(k) for k in locations_response["data"]]

    def _get_kroger_location_from_api(self, api_location: dict) -> KrogerLocation:
        address = api_location["address"]
        return KrogerLocation(
            id=api_location["locationId"],
            name=api_location["name"],
            address_line_1=address["addressLine1"],
            city=address["city"],
            state=address["state"],
        )

    def get_locations(self, token: OAuthToken, zip_code: str) -> tuple[list[KrogerLocation], Optional[OAuthToken]]:
        resp, new_token = self.oauth_provider.get(token,
                "https://api.kroger.com/v1/locations", params={"filter.zipCode.near": zip_code})
        return self.get_kroger_locations_from_api(resp), new_token
