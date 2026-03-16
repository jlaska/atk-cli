"""httpx-based ATK API client with transparent token refresh."""

from typing import Any

import httpx

from . import algolia
from . import auth as auth_mod
from . import config as cfg_mod
from .constants import ALGOLIA_BASE_URL, BASE_URL, BROWSER_HEADERS
from .exceptions import APIError, AuthenticationError


class ATKClient:
    """Stateless API client — loads tokens from disk before each authenticated request."""

    def __init__(
        self,
        profile: str | None = None,
        verbose: bool = False,
        site_key: str = "atk",
    ) -> None:
        self._profile = profile
        self._verbose = verbose
        self._site_key = site_key
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers=BROWSER_HEADERS,
            follow_redirects=True,
            timeout=30.0,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "ATKClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _ensure_auth(self) -> str:
        """Return a valid access token, refreshing if expired."""
        tokens = auth_mod.get_tokens(self._profile)
        access = tokens["access_token"]
        if auth_mod.is_token_expired(access):
            access = self._refresh(tokens["refresh_token"])
        return access

    def _refresh(self, refresh_token: str) -> str:
        resp = self._http.patch(
            "/v6/sessions/refresh_token",
            json={"refreshToken": refresh_token},
        )
        if resp.status_code != 200:
            raise AuthenticationError(
                "Token refresh failed. Run 'atk login' to re-authenticate."
            )
        data = resp.json()
        new_access = data.get("accessToken", "")
        new_refresh = data.get("refreshToken", refresh_token)
        if not new_access:
            raise AuthenticationError("Token refresh returned no access token.")
        auth_mod.save_tokens(new_access, new_refresh, self._profile)
        return new_access

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        authenticated: bool = True,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        headers: dict[str, str] = {}
        if extra_headers:
            headers.update(extra_headers)
        if authenticated:
            token = self._ensure_auth()
            headers["x-access-token"] = token

        if self._verbose:
            from rich import print as rprint
            rprint(f"[dim]{method} {path}  params={params}[/dim]")

        resp = self._http.request(method, path, params=params, json=json, headers=headers)
        if resp.status_code == 401:
            raise AuthenticationError("Not authenticated. Run 'atk login'.")
        if not resp.is_success:
            raise APIError(
                f"API error {resp.status_code}: {resp.text[:200]}",
                status_code=resp.status_code,
            )
        try:
            return resp.json()
        except Exception:
            return resp.text

    # ── Auth endpoints ─────────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate and return raw response (contains accessToken, refreshToken)."""
        # Bootstrap cookies
        self._http.get("/sign_in")
        resp = self._request(
            "POST",
            "/api/v6/sessions/login",
            json={"email": email, "password": password},
            authenticated=False,
            extra_headers={"Referer": f"{BASE_URL}/sign_in"},
        )
        return resp

    # ── User endpoints ─────────────────────────────────────────────────────────

    def get_user_info(self) -> dict[str, Any]:
        return self._request("GET", "/api/v8/users/interstitial_candidate")

    def get_customer_summary(self) -> dict[str, Any]:
        return self._request("GET", "/api/v8/cds_core/customer_summaries")

    # ── Favorites endpoints ────────────────────────────────────────────────────

    def get_favorites_page(self, page: int = 1, site_key: str | None = None) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/v6/user_favorites/results",
            params={"page": page, "site_key": site_key or self._site_key},
        )

    def get_recent_favorites(self, limit: int = 16) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/v6/user_favorites/most_recent",
            params={"limit": limit},
        )

    def get_top_rated_favorites(self) -> dict[str, Any]:
        return self._request("GET", "/api/v6/user_favorites/top_rated")

    def get_all_favorites(self, site_key: str | None = None) -> list[dict[str, Any]]:
        all_results: list[dict[str, Any]] = []
        page = 1
        while True:
            data = self.get_favorites_page(page=page, site_key=site_key)
            results = data.get("results", [])
            all_results.extend(results)
            pagination = data.get("pagination", {})
            if pagination.get("last_page", True):
                break
            page += 1
        return all_results

    def get_favorites_metadata(self, site_key: str | None = None) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/v6/user_favorites_meta_data",
            params={"site_key": site_key or self._site_key},
        )

    def create_favorite(self, object_id: str, site_key: str | None = None) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v6/user_favorites",
            json={"object_id": object_id, "site_key": site_key or self._site_key},
        )

    def delete_favorite(self, object_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/api/v6/user_favorites/{object_id}")

    def get_recipe_collections(self, recipe_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v6/user_favorites/recipes/{recipe_id}/collections")

    def check_favorites_intersection(
        self, object_ids: list[str], site_key: str | None = None
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v6/user_favorites/intersection",
            params={"site_key": site_key or self._site_key},
            json={"object_ids": object_ids},
        )

    # ── Ratings ────────────────────────────────────────────────────────────────

    def get_recipe_detail(self, recipe_id: int | str) -> dict[str, Any]:
        return self._request("GET", f"/api/v6/recipes/{recipe_id}")

    def get_document_by_object_id(self, object_id: str) -> dict[str, Any]:
        """Fetch a document from the Algolia index by its objectID (e.g. 'equipment_review_2639')."""
        cfg = algolia.get_algolia_config(verbose=self._verbose)
        url = f"{ALGOLIA_BASE_URL}/1/indexes/{cfg['index_name']}/{object_id}"
        headers = {
            "X-Algolia-Application-Id": cfg["app_id"],
            "X-Algolia-API-Key": cfg["api_key"],
        }
        resp = httpx.get(url, headers=headers, timeout=15.0)
        if not resp.is_success:
            raise APIError(
                f"Algolia error {resp.status_code}: {resp.text[:200]}",
                status_code=resp.status_code,
            )
        return resp.json()

    def get_recipe_rating(self, recipe_id: int | str) -> dict[str, Any]:
        return self._request("GET", f"/api/v6/ratings/recipe/{recipe_id}")

    def export_recipe_pdf(self, slug: str, output_path: "Path") -> None:
        """Render the ATK recipe /print page to a PDF via Playwright.

        Uses the dedicated /print URL which has ATK's clean print layout.
        The cookie consent banner is suppressed via the OptanonAlertBoxClosed
        cookie so it never appears in the rendered output.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            from .exceptions import ATKError
            raise ATKError(
                "PDF export requires playwright. "
                "Install with: pip install 'atk-cli[pdf]' && playwright install chromium"
            )

        access_token = self._ensure_auth()

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                context = browser.new_context()
                import datetime
                consent_date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
                context.add_cookies([
                    # Auth
                    {
                        "name": "user_token",
                        "value": access_token,
                        "domain": ".americastestkitchen.com",
                        "path": "/",
                    },
                    {
                        "name": "anonymous",
                        "value": "false",
                        "domain": ".americastestkitchen.com",
                        "path": "/",
                    },
                    # Suppress OneTrust cookie-consent banner
                    {
                        "name": "OptanonAlertBoxClosed",
                        "value": consent_date,
                        "domain": ".americastestkitchen.com",
                        "path": "/",
                    },
                    {
                        "name": "OptanonConsent",
                        "value": "isGpcEnabled=0&datestamp=" + consent_date + "&version=202209.1.0&isIABGlobal=false&hosts=&consentId=suppressed&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&AwaitingReconsent=false",
                        "domain": ".americastestkitchen.com",
                        "path": "/",
                    },
                ])
                page = context.new_page()
                page.goto(
                    f"{BASE_URL}/recipes/{slug}/print",
                    wait_until="networkidle",
                    timeout=60_000,
                )
                page.pdf(path=str(output_path), format="Letter")
            finally:
                browser.close()

    # ── Discovery ──────────────────────────────────────────────────────────────

    def get_trending_recipes(self) -> dict[str, Any]:
        return self._request("GET", "/api/cortado/trending-recipes", authenticated=False)

    # ── Algolia search ─────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        search_type: str = "recipe",
        page: int = 0,
        hits_per_page: int = 20,
    ) -> dict[str, Any]:
        cfg = algolia.get_algolia_config(verbose=self._verbose)
        url = f"{ALGOLIA_BASE_URL}/1/indexes/*/queries"
        headers = {
            "X-Algolia-Application-Id": cfg["app_id"],
            "X-Algolia-API-Key": cfg["api_key"],
            "Content-Type": "application/json",
        }
        facet_filter = f"search_document_klass:{search_type}" if search_type else ""
        request_body = {
            "requests": [
                {
                    "indexName": cfg["index_name"],
                    "params": (
                        f"query={query}&page={page}&hitsPerPage={hits_per_page}"
                        + (f"&facetFilters={facet_filter}" if facet_filter else "")
                    ),
                }
            ]
        }
        resp = httpx.post(url, headers=headers, json=request_body, timeout=15.0)
        if not resp.is_success:
            raise APIError(f"Algolia error {resp.status_code}: {resp.text[:200]}")
        return resp.json()
