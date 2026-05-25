import json

from fastapi import FastAPI, Request

from sftp_backend import SFTPBackend
from s3_api import handle_request

app = FastAPI()

config = json.load(open("config.json"))

backend = SFTPBackend(config["sftp"])
creds = config["auth"]["users"]

router = handle_request(app, backend, creds)


@app.get("/debug")
def debug():
    sftp = backend._connect()
    return sftp.listdir("/")

@app.api_route("/{full_path:path}", methods=["GET", "PUT", "DELETE", "HEAD", "POST"])
@app.api_route("/", methods=["GET"])
async def proxy(request: Request):
    return await router(request)
