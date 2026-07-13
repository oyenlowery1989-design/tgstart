"""HTTP Basic auth, ported unchanged from 6_messaging/65/dashboard.py."""
import os
import secrets
from typing import Optional
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from dotenv import load_dotenv

load_dotenv()

DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
security = HTTPBasic(auto_error=False)


def require_auth(credentials: Optional[HTTPBasicCredentials] = Depends(security)) -> None:
    if not DASHBOARD_PASSWORD:
        return
    valid_user = credentials is not None and secrets.compare_digest(credentials.username, DASHBOARD_USER)
    valid_pass = credentials is not None and secrets.compare_digest(credentials.password, DASHBOARD_PASSWORD)
    if not (valid_user and valid_pass):
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})
