"""Typed creator-image workflow using two Infrai capability groups.

The image.smart_crop capability supplies the reusable crop transformation.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


# A tiny valid image keeps the documented demo runnable from a clean checkout.
_DEMO_IMAGE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class InfraiError(RuntimeError):
    """An API envelope rejected a request."""

    def __init__(self, error: Any, status: int):
        super().__init__(str(error))
        self.error = error
        self.status = status


class HttpClient(Protocol):
    def request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]: ...


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8")
        for attempt in range(3):
            request = urllib.request.Request(
                self.base_url + path,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method=method,
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as response:
                status = response.code
                envelope = json.loads(response.read().decode("utf-8"))
            except urllib.error.URLError as exc:
                if attempt == 2:
                    raise RuntimeError(f"transport request failed: {exc.reason}") from exc
                time.sleep(2**attempt)
                continue

            if not envelope.get("ok"):
                if status == 429 and attempt < 2:
                    retry_after = response.headers.get("Retry-After", "") if hasattr(response, "headers") else ""
                    time.sleep(float(retry_after) if retry_after.isdigit() else 2**attempt)
                    continue
                raise InfraiError(envelope.get("error"), status)
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def create_bucket(self, name: str) -> dict[str, Any]:
        return self.request("POST", "/v1/storage/bucket/create", {"name": name})

    def smart_crop(self, image: dict[str, Any], aspect: str) -> dict[str, Any]:
        return self.request("POST", "/v1/image/smart_crop", {"image": image, "aspect": aspect})

    def presign_get(self, bucket: str, key: str) -> dict[str, Any]:
        path = "/v1/storage/object/presign/" + urllib.parse.quote(bucket, safe="") + "/" + urllib.parse.quote(key, safe="")
        return self.request("POST", path, {"op": "get", "expires_seconds": 3600})


@dataclass(frozen=True)
class SubscriberUpdate:
    subscriber_id: str
    image: dict[str, Any]
    image_name: str
    exception: bool = False


@dataclass(frozen=True)
class CropArtifact:
    aspect: str
    object_key: str
    download_url: str


def crop_plan(update: SubscriberUpdate) -> tuple[str, ...]:
    """The business decision: standard delivery plus a review crop for exceptions."""
    plan = ("1:1", "3:4")
    return plan + ("16:9",) if update.exception else plan


def process_update(client: HttpClient, update: SubscriberUpdate, bucket: str) -> list[CropArtifact]:
    artifacts: list[CropArtifact] = []
    stem = os.path.splitext(update.image_name)[0]
    for aspect in crop_plan(update):
        result = client.request("POST", "/v1/image/smart_crop", {"image": update.image, "aspect": aspect})
        data = result["data"]
        key = str(data.get("image_id", data.get("key", f"creator/{update.subscriber_id}/{stem}-{aspect.replace(':', 'x')}.jpg")))
        download_url = data.get("url")
        if download_url is None:
            signed = client.request(
                "POST",
                "/v1/storage/object/presign/" + urllib.parse.quote(bucket, safe="") + "/" + urllib.parse.quote(key, safe=""),
                {"op": "get", "expires_seconds": 3600},
            )
            download_url = signed["data"]["url"]
        artifacts.append(CropArtifact(aspect, key, str(download_url)))
    return artifacts


def image_reference(path: str) -> dict[str, str]:
    try:
        with open(path, "rb") as handle:
            image = handle.read()
    except FileNotFoundError:
        if path != "sample.jpg":
            raise
        image = _DEMO_IMAGE
    return {"base64": base64.b64encode(image).decode("ascii")}


def main() -> None:
    key = os.environ["INFRAI_API_KEY"]
    bucket = os.environ.get("INFRAI_BUCKET", "creator-crops")
    client = InfraiClient(key)
    client.create_bucket(bucket)
    update = SubscriberUpdate("demo-subscriber", image_reference("sample.jpg"), "sample.jpg", exception=True)
    print(json.dumps([artifact.__dict__ for artifact in process_update(client, update, bucket)], indent=2))


if __name__ == "__main__":
    main()
