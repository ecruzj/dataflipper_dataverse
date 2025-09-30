import os
from dotenv import load_dotenv
load_dotenv()

def resolve_current_user_email(default_domain="ontario.ca") -> str:
        # 1) .env (USERNAME puede venir como correo)
        
        env_user = os.getenv("USERNAME")
        if env_user and "@" in env_user:
            return env_user

        # 2) Windows envs -> username@domain
        win_user = os.environ.get("USERNAME")
        dns_domain = (os.environ.get("USERDNSDOMAIN") or default_domain or "").lower()
        if win_user and dns_domain:
            return f"{win_user}@{dns_domain}"
        
        # DATAVERSE_BASE_URI

        return env_user or win_user or ""
    
def resolve_current_environment() -> str:
        # .env (DATAVERSE_BASE_URI)     
        env_url = os.getenv("DATAVERSE_BASE_URI")
        if env_url and env_url.startswith("http"):
            return env_url
        
        return env_url or ""