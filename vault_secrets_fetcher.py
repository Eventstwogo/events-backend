import hvac
import requests
from fastapi import FastAPI, HTTPException

app = FastAPI()

vault_url = "https://vault.events2go.com.au"
vault_token = "hvs.ATZ5B71yX4RmAjAB9dIoT6U7"

client = hvac.Client(url=vault_url, token=vault_token)


@app.get("/db-credentials/")
async def get_db_credentials():
    try:
        headers = {
            "X-Vault-Token": vault_token,
            "Content-Type": "application/json",
        }

        response = requests.get(f"{vault_url}/v1/kv/data/data", headers=headers)

        if response.status_code == 200:
            secrets = response.json()["data"]["data"]
            return {
                "DATABASE": secrets.get("DATABASE"),
                "DB_HOST": secrets.get("DB_HOST"),
                "DB_PASSWORD": secrets.get("DB_PASSWORD"),
                "DB_PORT": secrets.get("DB_PORT"),
                "SOURCE_DB_NAME": secrets.get("SOURCE_DB_NAME"),
                "SENDER_EMAIL": secrets.get("SENDER_EMAIL"),
                "SENDER_PASSWORD": secrets.get("SENDER_PASSWORD"),
                "SMTP_LOGIN": secrets.get("SMTP_LOGIN"),
                "SMTP_PORT": secrets.get("SMTP_PORT"),
                "SMTP_SERVER": secrets.get("SMTP_SERVER"),
                "SPACES_ACCESS_KEY": secrets.get("SPACES_ACCESS_KEY"),
                "SPACES_BUCKET_NAME": secrets.get("SPACES_BUCKET_NAME"),
                "SPACES_REGION_NAME": secrets.get("SPACES_REGION_NAME"),
                "SPACES_SECRET_KEY": secrets.get("SPACES_SECRET_KEY"),
            }

        raise HTTPException(
            status_code=500, detail="Cannot retrieve Vault secrets"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vault error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
