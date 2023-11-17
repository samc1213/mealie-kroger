import base64
from dataclasses import dataclass
import dataclasses
import time
from typing import Optional
import requests
from urllib.parse import urlparse, urlencode


@dataclass
class OAuthToken:
    expires_in: int
    access_token: str
    token_type: str
    created_at: Optional[int] = int(time.time())
    refresh_token: Optional[str] = None

    def is_expired(self) -> bool:
        return self.created_at + self.expires_in + 30 < time.time()
    
    @classmethod
    def from_dict(cls, dict: dict[str, str]):
        return cls(**dict)
    
    def to_dict(self) -> dict[str, str]:
        return dataclasses.asdict(self)


class OAuthProvider:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token_url: str,
        authorize_url: str,
        scope: str,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token_url = access_token_url
        self.authorize_url = authorize_url
        self.scope = scope

    def get_authorization(self):
        return base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode("utf-8")
        ).decode("ascii")

    def get_authorize_url(self, redirect_uri: str) -> str:
        parsed_authorize_url = urlparse(self.authorize_url)
        query_params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": self.scope,
        }
        return parsed_authorize_url._replace(query=urlencode(query_params)).geturl()

    def get_access_token(self, redirect_uri_params: dict[str, str], redirect_uri: str) -> OAuthToken:
        if "code" not in redirect_uri_params:
            raise ValueError("Expected authorization code in OAuth redirect")

        authorization_code = redirect_uri_params["code"]
        return self._get_access_token_from_authorization_code(authorization_code, redirect_uri)

    def _get_access_token_from_authorization_code(
        self, authorization_code: str, redirect_uri: str
    ) -> OAuthToken:
        return self._get_access_token(
            {
                "grant_type": "authorization_code",
                "scope": self.scope,
                "code": authorization_code,
                "redirect_uri": redirect_uri
            }
        )

    def _get_access_token_from_refresh_token(self, refresh_token: str) -> OAuthToken:
        return self._get_access_token(
            {
                "grant_type": "refresh_token",
                "scope": self.scope,
                "refresh_token": refresh_token,
            }
        )

    def _get_access_token(self, data: dict[str, str]) -> OAuthToken:
        resp = requests.post(
            self.access_token_url,
            data=data,
            headers={"Authorization": f"Basic {self.get_authorization()}"},
        )
        resp.raise_for_status()
        resp_json = resp.json()
        return OAuthToken(
            expires_in=resp_json.get("expires_in"),
            access_token=resp_json.get("access_token"),
            token_type=resp_json.get("token_type"),
            refresh_token=resp_json.get("refresh_token"),
        )

    def update_token_if_needed(self, token: OAuthToken) -> Optional[OAuthToken]:
        if not token.is_expired():
            return None

        if not token.refresh_token:
            raise ValueError("Cannot update token - no refresh_token provided")

        return self._get_access_token_from_refresh_token(token.refresh_token)

    def get(
        self, token: OAuthToken, url: str, headers: dict[str, str] = None, **kwargs
    ) -> tuple[any, Optional[OAuthToken]]:
        return self._perform_http_request(token, "get", url, headers, **kwargs)

    def put(
        self, token: OAuthToken, url: str, headers: dict[str, str] = None, **kwargs
    ) -> tuple[any, Optional[OAuthToken]]:
        return self._perform_http_request(token, "put", url, headers, **kwargs)

    def _perform_http_request(
        self,
        token: OAuthToken,
        method: str,
        url: str,
        headers: dict[str, str] = None,
        **kwargs,
    ) -> tuple[any, Optional[OAuthToken]]:
        new_token = self.update_token_if_needed(token)
        active_token = new_token or token
        resp = requests.request(
            method,
            url,
            headers={**(headers or {}), **{"Authorization": f"Bearer {active_token.access_token}"}},
            **kwargs,
        )
        resp.raise_for_status()
        return resp.json() if resp.text else None, new_token
