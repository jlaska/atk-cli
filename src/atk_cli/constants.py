import pathlib

# ── Paths ────────────────────────────────────────────────────────────────────
ATK_DIR = pathlib.Path.home() / ".atk"
CONFIG_FILE = ATK_DIR / "config.json"
TOKENS_FILE = ATK_DIR / "tokens.json"

# ── Base URLs ────────────────────────────────────────────────────────────────
BASE_URL = "https://www.americastestkitchen.com"
ALGOLIA_BASE_URL = "https://y1fnzxui30-dsn.algolia.net"

# ── Algolia ──────────────────────────────────────────────────────────────────
ALGOLIA_APP_ID = "REDACTED_APP_ID"
ALGOLIA_API_KEY = "REDACTED_API_KEY"
# Index name captured from HAR — may need refreshing from a new capture if search returns 404
ALGOLIA_INDEX = "everest_search_atk_production"

# ── Site keys ────────────────────────────────────────────────────────────────
SITE_KEYS = ["atk", "cio", "cco"]
DEFAULT_SITE_KEY = "atk"

# ── Browser headers (required by ATK API) ────────────────────────────────────
BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "Origin": BASE_URL,
    "sec-ch-ua": '"Chromium";v="146", "Google Chrome";v="146", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}
