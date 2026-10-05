"""Generate images and video on SayMaker (https://saymaker.ai) from Python.

    from saymaker import generate, generate_video
    url = generate("a paper-cut layered mountain range at dusk")
    clip = generate_video("a paper boat drifting down a rain gutter, low angle")

One API key runs the whole SayMaker shelf: Nano Banana 2, GPT Image 2.5,
Seedream 5.0, Veo 3.1, Kling 3.0, Seedance 2.0, MiniMax H3 and more, on your
own credits. Create a key at https://saymaker.ai/settings/apikeys and pass it
as ``api_key=`` or set ``SAYMAKER_API_KEY``.

Standard library only.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Callable, Optional

__version__ = "0.1.1"
__all__ = [
    "generate",
    "generate_video",
    "SayMakerError",
    "AuthError",
    "QuotaError",
    "PlanError",
    "BusyError",
    "RejectedError",
    "MODELS",
    "BASE",
]

BASE = "https://saymaker.ai"
KEYS_URL = BASE + "/settings/apikeys"

#: Model id -> the routing field the API expects next to it. Ids not listed
#: here are sent with "kie"; the full list with inputs is on saymaker.ai/models.
MODELS = {
    # image
    "saymaker-image-v1": "kie",
    "nano-banana-2-lite": "kie",
    "nano-banana-2": "poyo",
    "nano-banana-pro": "poyo",
    "gpt-image-2": "poyo",
    "gpt-image-2-5-flare": "kie",
    "seedream-5-lite": "poyo",
    "seedream-5-pro": "kie",
    "qwen-image-3-pro": "kie",
    "grok-imagine-image-2-0": "poyo",
    # video
    "minimax-h3-fast": "vgenv",
    "minimax-h3": "poyo",
    "seedance-2": "kie",
    "seedance-2-fast": "kie",
    "seedance-2-5": "kie",
    "veo-3-1": "kie",
    "kling-3-0": "kie",
    "kling-3-0-turbo": "kie",
    "wan-3-0": "kie",
    "ltx-2-5-fast": "replicate",
}

#: The cheapest text-to-image model; the edit default takes an input image.
DEFAULT_IMAGE_MODEL = "saymaker-image-v1"
DEFAULT_EDIT_MODEL = "nano-banana-2-lite"
#: The video model a free account can run (480p or 768p, 4 to 15 seconds).
DEFAULT_VIDEO_MODEL = "minimax-h3-fast"


class SayMakerError(RuntimeError):
    """Base class. Catch a subclass to decide what to do next."""


class AuthError(SayMakerError):
    """No API key, or the key is invalid or deleted."""


class QuotaError(SayMakerError):
    """The account is out of credits."""


class PlanError(SayMakerError):
    """This model needs a paid plan or a credit pack."""


class BusyError(SayMakerError):
    """Another run on this account is still rendering. Free accounts run one at a time."""


class RejectedError(SayMakerError):
    """The content filter or the model refused the prompt. Reword it."""


Transport = Callable[[str, str, Optional[dict], dict], dict]


def _http(method: str, url: str, body: Optional[dict], headers: dict) -> dict:
    headers = {**headers, "User-Agent": f"saymaker-python/{__version__}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")


def _parse_submit(env: dict) -> str:
    # Refusals arrive as HTTP 200 with code -1; the status code alone reads as success.
    if env.get("code") != 0:
        msg = str(env.get("message") or "request refused")
        low = msg.lower()
        if (env.get("data") or {}).get("busy") or "is rendering" in low or "at once" in low:
            raise BusyError(msg)
        if "api key" in low or "no auth" in low:
            raise AuthError(msg)
        if "insufficient credits" in low:
            raise QuotaError(msg)
        if "subscription" in low or "plan" in low or "sign in" in low:
            raise PlanError(msg)
        raise SayMakerError(msg)
    data = env.get("data") or {}
    # A signed-out request is also a 200 with code 0 — only `wall` tells it apart.
    if data.get("wall"):
        raise AuthError(f"SayMaker needs an API key; create one at {KEYS_URL}")
    task = data.get("id")
    if not task:
        raise SayMakerError("the service returned no task id")
    return str(task)


def _run(
    media: str,
    scene: str,
    model: str,
    prompt: str,
    options: dict,
    api_key: Optional[str],
    timeout: float,
    poll_every: float,
    base_url: str,
    transport: Optional[Transport],
) -> str:
    if not str(prompt or "").strip():
        raise ValueError("prompt is required")
    key = api_key or os.environ.get("SAYMAKER_API_KEY") or None
    if not key:
        raise AuthError(f"pass api_key= or set SAYMAKER_API_KEY; create a key at {KEYS_URL}")
    http = transport or _http
    headers = {"Authorization": f"Bearer {key}"}
    task = _parse_submit(
        http(
            "POST",
            base_url + "/api/ai/generate",
            {
                "provider": MODELS.get(model, "kie"),
                "mediaType": media,
                "model": model,
                "scene": scene,
                "prompt": prompt,
                "options": options,
            },
            headers,
        )
    )

    # Free-account runs wait in a queue and only reach the model on the poll
    # that crosses the end of the wait, so polling is what starts the work.
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(poll_every)
        try:
            env = http("POST", base_url + "/api/ai/query", {"taskId": task}, headers)
        except (OSError, ValueError):
            continue  # a dropped poll is not a failed generation
        if env.get("code") != 0:
            continue
        data = env.get("data") or {}
        for field in ("cleanImages", "images", "videos"):
            if data.get(field):
                return data[field][0]
        if str(data.get("status") or "").lower() in {"failed", "error"}:
            raise RejectedError("the run failed; reword the prompt rather than retrying the same text")
    raise SayMakerError(f"deadline passed after {timeout:g}s; the run may still finish in your SayMaker history")


def _check_url(image_url: Optional[str]) -> None:
    if image_url is not None and not image_url.startswith(("http://", "https://")):
        raise ValueError("image_url must be a public http(s) url")


def generate(
    prompt: str,
    *,
    image_url: Optional[str] = None,
    model: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = 4500.0,
    poll_every: float = 5.0,
    base_url: str = BASE,
    transport: Optional[Transport] = None,
) -> str:
    """Generate one image — or edit ``image_url`` — and return its URL.

    For an edit the prompt describes the change and should name what must stay
    ("keep the same face and lighting"). Raises a :class:`SayMakerError`
    subclass on a refusal, an empty balance or a timeout.
    """
    _check_url(image_url)
    chosen = model or (DEFAULT_EDIT_MODEL if image_url else DEFAULT_IMAGE_MODEL)
    # `size` carries the aspect ratio — the site's own field name. An edit
    # defaults to "auto", which keeps the source framing.
    options: dict = {"size": aspect_ratio or ("auto" if image_url else "1:1"), "resolution": "1K", "n": 1}
    if image_url:
        options["image_input"] = [image_url]
    return _run(
        "image",
        "image-to-image" if image_url else "text-to-image",
        chosen,
        prompt,
        options,
        api_key,
        timeout,
        poll_every,
        base_url,
        transport,
    )


def generate_video(
    prompt: str,
    *,
    image_url: Optional[str] = None,
    model: str = DEFAULT_VIDEO_MODEL,
    duration: Optional[int] = None,
    resolution: Optional[str] = None,
    aspect_ratio: str = "16:9",
    sound: bool = True,
    api_key: Optional[str] = None,
    timeout: float = 5400.0,
    poll_every: float = 10.0,
    base_url: str = BASE,
    transport: Optional[Transport] = None,
) -> str:
    """Generate one clip — or animate ``image_url`` as the first frame — and return its URL.

    Video takes minutes. ``model`` defaults to MiniMax H3 Fast, the one a free
    account can run; Veo 3.1, Kling 3.0 and Seedance 2.0 need a plan or a pack.
    """
    _check_url(image_url)
    options: dict = {"aspect_ratio": aspect_ratio, "sound": sound}
    if image_url:
        options["image_input"] = [image_url]
    if duration:
        options["duration"] = duration
    if resolution:
        options["resolution"] = resolution
    return _run(
        "video",
        "image-to-video" if image_url else "text-to-video",
        model,
        prompt,
        options,
        api_key,
        timeout,
        poll_every,
        base_url,
        transport,
    )
