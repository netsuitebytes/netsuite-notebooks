"""
netsuite_auth.py — NetSuite OAuth1 credential loader.

Credentials are fetched from Azure Key Vault when KEY_VAULT_URL is set in the
environment; otherwise they fall back to a local .env.<env> file.  This lets
sandbox notebooks use local files while production runs pull secrets from the
vault without storing them on disk.

Environment variables (set before importing or in the shell):
    NETSUITE_ENV   — "sandbox2" (default) or "production"
    KEY_VAULT_URL  — Azure Key Vault URL, e.g. https://my-vault.vault.azure.net/
                     When absent, a local .env.<NETSUITE_ENV> file is used instead.

Azure Key Vault secret naming convention (replace {env} with NETSUITE_ENV value):
    ns-{env}-account-id
    ns-{env}-consumer-key
    ns-{env}-consumer-secret
    ns-{env}-token-id
    ns-{env}-token-secret

After get_auth() is called, run_suiteql() and run_suiteql_all() are ready to use
without passing auth or BASE_URL as arguments.
"""

import os
import requests
from requests_oauthlib import OAuth1

os.environ.setdefault("NETSUITE_ENV", "sandbox2")

# Module-level state — populated by get_auth()
_auth: OAuth1 | None = None
_base_url: str | None = None


# ---------------------------------------------------------------------------
# Credential loaders (private)
# ---------------------------------------------------------------------------

def _load_from_key_vault(env: str) -> dict:
    """Fetch NetSuite secrets from Azure Key Vault using DefaultAzureCredential.

    DefaultAzureCredential tries (in order): environment variables, workload
    identity, managed identity, Azure CLI login, Visual Studio Code credential.
    For local development, `az login` is sufficient.
    """
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    vault_url = os.environ["KEY_VAULT_URL"]
    client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())

    prefix = f"ns-{env}"
    return {
        "NS_ACCOUNT_ID":      client.get_secret(f"{prefix}-account-id").value,
        "NS_CONSUMER_KEY":    client.get_secret(f"{prefix}-consumer-key").value,
        "NS_CONSUMER_SECRET": client.get_secret(f"{prefix}-consumer-secret").value,
        "NS_TOKEN_ID":        client.get_secret(f"{prefix}-token-id").value,
        "NS_TOKEN_SECRET":    client.get_secret(f"{prefix}-token-secret").value,
    }


def _load_from_dotenv(env: str) -> dict:
    """Load NetSuite credentials from a local .env.<env> file."""
    from dotenv import load_dotenv

    env_file = f".env.{env}"
    if not os.path.exists(env_file):
        raise FileNotFoundError(
            f"Credential file '{env_file}' not found and KEY_VAULT_URL is not set. "
            f"Either create '{env_file}' or set KEY_VAULT_URL to use Azure Key Vault."
        )
    load_dotenv(env_file, override=True)
    return {
        "NS_ACCOUNT_ID":      os.getenv("NS_ACCOUNT_ID"),
        "NS_CONSUMER_KEY":    os.getenv("NS_CONSUMER_KEY"),
        "NS_CONSUMER_SECRET": os.getenv("NS_CONSUMER_SECRET"),
        "NS_TOKEN_ID":        os.getenv("NS_TOKEN_ID"),
        "NS_TOKEN_SECRET":    os.getenv("NS_TOKEN_SECRET"),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_auth(env: str | None = None) -> tuple[OAuth1, str]:
    """Load credentials, initialize module state, and return (auth, BASE_URL).

    After this call, run_suiteql() and run_suiteql_all() are ready to use
    without explicitly passing auth or BASE_URL.

    Args:
        env: Environment name — "sandbox2" or "production".
             Defaults to the NETSUITE_ENV environment variable, then "sandbox2".

    Returns:
        Tuple of (requests_oauthlib.OAuth1, BASE_URL string)
    """
    global _auth, _base_url

    env = env or os.getenv("NETSUITE_ENV", "sandbox2")

    if os.getenv("KEY_VAULT_URL"):
        print(f"Loading credentials from Azure Key Vault [{env}]")
        creds = _load_from_key_vault(env)
    else:
        print(f"Loading credentials from .env.{env}")
        creds = _load_from_dotenv(env)

    account_id   = creds["NS_ACCOUNT_ID"]
    realm        = account_id.replace("-", "_").upper()
    consumer_key = creds["NS_CONSUMER_KEY"]
    consumer_sec = creds["NS_CONSUMER_SECRET"]
    token_id     = creds["NS_TOKEN_ID"]
    token_sec    = creds["NS_TOKEN_SECRET"]

    print(f"ACCOUNT_ID:   {account_id}")
    print(f"REALM:        {realm}")
    print(f"CONSUMER_KEY: {consumer_key[:6]}..." if consumer_key else "CONSUMER_KEY: NOT SET")
    print(f"TOKEN_ID:     {token_id[:6]}..."     if token_id     else "TOKEN_ID:     NOT SET")

    _auth = OAuth1(
        consumer_key, consumer_sec, token_id, token_sec,
        signature_method="HMAC-SHA256",
        realm=realm,
    )
    _base_url = f"https://{account_id}.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql"

    return _auth, _base_url


def run_suiteql(query: str, limit: int = 1000, offset: int = 0) -> list:
    """Run a single page of a SuiteQL query and return results as a list of dicts.

    Requires get_auth() to have been called first.
    """
    if _auth is None or _base_url is None:
        raise RuntimeError("Call get_auth() before run_suiteql().")

    response = requests.post(
        _base_url,
        auth=_auth,
        json={"q": query},
        headers={"prefer": "transient", "Content-Type": "application/json"},
        params={"limit": limit, "offset": offset},
    )
    if not response.ok:
        print("Status:", response.status_code)
        print("Response:", response.text)
    response.raise_for_status()
    return response.json().get("items", [])


def run_suiteql_all(query: str, page_size: int = 1000) -> list:
    """Run a SuiteQL query with automatic pagination, returning all results.

    Requires get_auth() to have been called first.
    """
    all_results = []
    offset = 0
    while True:
        page = run_suiteql(query, limit=page_size, offset=offset)
        all_results.extend(page)
        print(f"  Fetched {len(all_results)} rows so far...")
        if len(page) < page_size:
            break
        offset += page_size
    print(f"Total rows fetched: {len(all_results)}")
    return all_results
