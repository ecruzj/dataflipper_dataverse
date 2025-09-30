from ..core.services.env_loader import get_env_variable_value
from ..core.logging.logging_conf import get_logger
from ..core.services.dataverse_client import call_dataverse
from urllib.parse import quote

log = get_logger(__name__)

# ---------- Read environment variables ----------
SHAREPOINT_BASE_URL = get_env_variable_value("SHAREPOINT_BASE_URL")
SHAREPOINT_SITE_PATH = get_env_variable_value("SHAREPOINT_SITE_PATH")
LOCATION_QUERY = get_env_variable_value("LOCATION_QUERY")

# Entity Mapping -> Folder in SharePoint
FOLDER_MAP = {
    "account": "account",
    "case": "incident",
    "ecase": "icps_ecase",
    "inspection": "icps_inspection",
    "investigation": "icps_investigation",
}

def get_relativeurls_for_object_id(object_id):
    # Query SharePoint document locations associated with the given object ID
    location_query = f"{LOCATION_QUERY} {object_id}"
    response = call_dataverse(location_query)

    if not response.get("value"):
        print(f"No SharePoint document locations found for object ID: {object_id}")
        log.info(f"No SharePoint document locations found for object ID: {object_id}")
        return []

    # Extract all 'relativeurl' values
    relative_urls = [location.get("relativeurl") for location in response["value"] if location.get("relativeurl")]

    return relative_urls

def build_sharepoint_folder_url(relativeurl: str, entity_type: str):
    """
    Constructs the full folder URL in SharePoint for a related document.
    - relativeurl: Relative path returned by Dataverse (without the site prefix).
    - entity_type: Business entity ('account', 'case', 'ecase', 'inspection', 'investigation').
    Rules:
    * If relativeurl starts with 'e-', use 'icps_ecase' as the folder.
    * Otherwise, use FOLDER_MAP[entity]
    """
    
    sharepoint_base_url = SHAREPOINT_BASE_URL
    sharepoint_site_path = SHAREPOINT_SITE_PATH

    # Make sure to encode spaces and special characters
    rel = (relativeurl or "").strip().lstrip("/")      # without initial slashes
    
    if not rel:
        raise ValueError("empty or invalid relativeurl")
    
    encoded_rel = quote(rel)                           # encode spaces/special characters
    
    entity = (entity_type or "").strip().lower()
    folder = FOLDER_MAP.get(entity, entity)            # fallback to the entity name
    
    # Special rule: 'e-' prefix forces use of icps_ecase
    if rel.startswith("e-"):
        folder = "icps_ecase"

    if not folder:
        raise ValueError(f"invalid entity_type: {entity_type}")

    # If it starts with "e-", use icps_ecase folder, otherwise use entity_type (folder)
    # folder = "icps_ecase" if rel.startswith("e-") else FOLDER_MAP.get((entity_type or "").lower())

    return f"{sharepoint_base_url}{sharepoint_site_path}{folder}/{encoded_rel}"