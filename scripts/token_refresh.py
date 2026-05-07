# Databricks notebook source
# ============================================================
# Token Refresh Script
# Schedule as a Databricks Job (every 12 hours)
# Cron: 0 0 */12 * * ? *
# ============================================================

from databricks.sdk import WorkspaceClient
import requests
from datetime import datetime

# Configuration
TS_BASE_URL = "https://databricks-emea.thoughtspot.cloud"
SECRET_SCOPE = "thoughtspot"

w = WorkspaceClient()

# Read stored credentials
username = dbutils.secrets.get(scope=SECRET_SCOPE, key="username")
password = dbutils.secrets.get(scope=SECRET_SCOPE, key="password")

print(f"Refreshing ThoughtSpot token for user: {username}")
print(f"Cluster: {TS_BASE_URL}")
print(f"Time: {datetime.now().isoformat()}")

# Authenticate to ThoughtSpot
resp = requests.post(
    f"{TS_BASE_URL}/api/rest/2.0/auth/token/full",
    json={
        "username": username,
        "password": password,
        "validity_time_in_sec": 86400,  # 24 hours
    },
    headers={"Content-Type": "application/json"},
    timeout=30,
)
resp.raise_for_status()
new_token = resp.json()["token"]

# Store the fresh token
w.secrets.put_secret(scope=SECRET_SCOPE, key="api-token", string_value=new_token)

print(f"✓ Token refreshed successfully")
print(f"  Expires in: 24 hours")
print(f"  Stored in: scope='{SECRET_SCOPE}', key='api-token'")
