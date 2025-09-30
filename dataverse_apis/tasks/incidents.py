from core.services.dataverse_client import call_dataverse

ENTITY_NAME = "incidents"

def get_incident_by_incident_id(incident_id: str) -> str | None:
    endpoint = f"{ENTITY_NAME}({incident_id})"
    result = call_dataverse(endpoint)
    
    record = result.get("value", [])
    if record:
        return record
    return None

def get_incident_id_by_ticket_number(ticket_number: str) -> str | None:
    endpoint = f"{ENTITY_NAME}?$filter=ticketnumber eq '{ticket_number}'"
    result = call_dataverse(endpoint)
    
    records = result.get("value", [])
    if records:
        return records[0].get("incidentid")
    return None