from msal import PublicClientApplication
import requests

client_id = "1fec8e78-bce4-4aaf-ab1b-5451cc387264"  # Postman client ID
authority = "https://login.microsoftonline.com/common"
scopes = ["Files.Read.All", "Sites.Read.All", "User.Read"]

app = PublicClientApplication(client_id, authority=authority)
result = app.acquire_token_interactive(scopes=scopes)

token = result.get("access_token")
print("Access token:", token)

# Test request to Graph
response = requests.get(
    "https://graph.microsoft.com/v1.0/me/drive/root/children",
    headers={"Authorization": f"Bearer {token}"}
)
print(response.status_code)
print(response.json())
