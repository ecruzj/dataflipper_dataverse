import os
# import sys
# from pathlib import Path
# from dotenv import load_dotenv, set_key
from ..services.env_loader import get_env_variable_value
from msal import PublicClientApplication, TokenCache # msal Microsoft Authentication Library
from ..logging.logging_conf import get_logger

log = get_logger(__name__)

# ---------- Read environment variables ----------
# ICPS URL
api_url = get_env_variable_value("DATAVERSE_BASE_URI")
api_version = get_env_variable_value("API_VERSION")
webapi_url = f"{api_url}/api/data/v{api_version}"
# OPS Azure Tenant ID
tenant_id = get_env_variable_value("TENANT_ID")
# Microsoft public app [Microsoft Power Platform]
client_id = get_env_variable_value("CLIENT_ID")
# optional for prefilling
username = get_env_variable_value("USERNAME")

# if not username:
#     email = get_current_user_email(default_domain="ontario.ca")
#     if email:
#         os.environ["USERNAME"] = email
#         try:
#             set_key(ENV_FILE, "USERNAME", email)
#         except Exception:
#             pass

# authority = f"https://login.microsoftonline.com/{tenant_id}"
# scopes = [
#     f"{api_url}/user_impersonation" # Dataverse
# ]

# Allow explicit AUTHORITY or build from TENANT_ID
authority = os.getenv("AUTHORITY") or (f"https://login.microsoftonline.com/{tenant_id}" if tenant_id else None)

# Validate early to avoid https://login.microsoftonline.com/None
def _fail(msg: str) -> None:
    raise RuntimeError(
        msg +
        "\nPlace a .env next to the EXE (recommended) or set environment vars.\n"
        "Minimal .env example:\n"
        "  TENANT_ID=00000000-0000-0000-0000-000000000000\n"
        "  CLIENT_ID=11111111-1111-1111-1111-111111111111\n"
        "  DATAVERSE_BASE_URI=https://<org>.crm.dynamics.com\n"
        "  API_VERSION=9.2\n"
        "# Optional: AUTHORITY=https://login.microsoftonline.com/<tenant-guid>\n"
    )

if not authority or "None" in str(authority):
    _fail(f"Invalid/missing AUTHORITY (TENANT_ID={tenant_id!r}, AUTHORITY={authority!r})")
if not client_id:
    _fail("Missing CLIENT_ID")
if not api_url:
    _fail("Missing DATAVERSE_BASE_URI")

webapi_url = f"{api_url}/api/data/v{api_version}"
scopes = [f"{api_url}/user_impersonation"]

# ---------- MSAL app & token cache ----------
token_cache = TokenCache()
app = PublicClientApplication(
    client_id,
    authority=authority,
    token_cache=token_cache
)

# Global variable to save the current token
_cached_token = None

def dump_msal_config():
    log.info("Configuration MSAL Auth:")
    log.info(f"API URL: {api_url}  Version: {api_version}")
    log.info(f"username: {username}")
    # log.info(f"client id: {client_id}")
    # log.info(f"Authority: {authority}  Tenant id: {tenant_id}  scopes: {scopes} ")
    # log.info(f"WebAPI URL: {webapi_url}")

def get_access_token_with_username():    
    dump_msal_config() # just for debugging purposes
    global _cached_token
    
    # If there is already a valid token in the global cache, we return it.
    if _cached_token and "access_token" in _cached_token:
        return _cached_token["access_token"]
    
    accounts = app.get_accounts(username=username)
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]

    print("Opening browser for interactive login...")
    log.info("Opening browser for interactive login...")
    
    result = app.acquire_token_interactive(
        scopes=scopes,
        login_hint=username
    )
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Error getting token: {result.get('error_description')}")
    
def get_access_token_with_msal_default():
    dump_msal_config() # just for debugging purposes
    global _cached_token
    
    log.info("Getting access token with MSAL default method...")
    
    # If there is already a valid token in the global cache, we return it.
    if _cached_token and "access_token" in _cached_token:
        return _cached_token["access_token"]
    
    # 1. Search for cached accounts
    accounts = app.get_accounts()
    if accounts:
        print("Cached Accounts:")
        log.info(f"Found {len(accounts)} cached accounts.")
        for idx, acc in enumerate(accounts):
            print(f"{idx + 1}. {acc['username']}")
        chosen = accounts[0]  # By default, the first
        print(f"Using account: {chosen['username']}")
        result = app.acquire_token_silent(scopes, account=chosen)
        if result and "access_token" in result:
            _cached_token = result
            return result["access_token"]

    # 2. No valid token, open browser
    print("There is no active session. A browser will open for you to log in.")
    log.info("There is no active session. A browser will open for you to log in.")
    result = app.acquire_token_interactive(scopes=scopes)
    if "access_token" in result:
        _cached_token = result
        return result["access_token"]
    else:
        raise Exception(f"Error getting token: {result.get('error_description')}")