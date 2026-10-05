# saymaker

Generate images and video from Python on [SayMaker](https://saymaker.ai/?utm_source=pypi&utm_medium=package): one API key runs Veo 3.1, Kling 3.0, Seedance 2.0, MiniMax H3, Nano Banana 2, GPT Image 2.5, Seedream 5.0 and the rest of the shelf on your own credits.

```python
from saymaker import generate, generate_video

url = generate("a paper-cut layered mountain range at dusk, warm rim light")
clip = generate_video("a paper boat drifting down a rain gutter, low angle, slow push-in")
```

Standard library only, no dependencies. Each call returns the URL of the finished file.

## API key

Sign up on [saymaker.ai](https://saymaker.ai/?utm_source=pypi&utm_medium=package) (new accounts get sign-up credits), create a key at [saymaker.ai/settings/apikeys](https://saymaker.ai/settings/apikeys?utm_source=pypi&utm_medium=package), then either pass it or export it:

```bash
export SAYMAKER_API_KEY=sk-...
```

A key runs on your account exactly like the site does: same models, same credit prices, same plan, and every run lands in your library at [saymaker.ai/history](https://saymaker.ai/history?utm_source=pypi&utm_medium=package).

## Images

```python
generate("isometric diorama of a ramen shop at night", aspect_ratio="16:9")
generate("product shot of a glass perfume bottle on wet slate", model="gpt-image-2-5-flare")
```

The default model is `saymaker-image-v1`, the cheapest text-to-image run. Pass `model=` for `nano-banana-2`, `gpt-image-2-5-flare`, `seedream-5-pro`, `qwen-image-3-pro` and the others listed in `saymaker.MODELS`.

### Editing a photo

Pass `image_url` and the prompt describes the change rather than the picture:

```python
generate(
    "change the jacket to dark green, keep the face, pose and background exactly as they are",
    image_url="https://example.com/portrait.jpg",
)
```

Naming what must stay is what decides whether the edit holds. Prompts that only name the change tend to drift the whole picture.

## Video

```python
generate_video("a fox trotting through fresh snow at dawn, tracking shot", duration=6)
generate_video("the camera slowly orbits the statue", image_url="https://example.com/statue.jpg")
generate_video("a street drummer in the rain", model="veo-3-1", resolution="1080p")
```

Video takes minutes; `generate_video` waits up to 15 minutes by default (`timeout=`). The default model is `minimax-h3-fast`, the one a free account can run (480p or 768p, 4 to 15 seconds). Veo 3.1, Kling 3.0, Seedance 2.0 and the other video models need a plan or a credit pack; see [pricing](https://saymaker.ai/pricing?utm_source=pypi&utm_medium=package). Each model's options are on its page, e.g. [Veo 3.1](https://saymaker.ai/video/veo-3-1?utm_source=pypi&utm_medium=package), [Kling 3.0](https://saymaker.ai/video/kling-3-0?utm_source=pypi&utm_medium=package), [Seedance 2.0](https://saymaker.ai/video/seedance-2?utm_source=pypi&utm_medium=package).

## Errors worth catching

Each failure is its own subclass of `SayMakerError`, so you can branch on what to do next:

- `AuthError` — no key, or the key is wrong or deleted
- `QuotaError` — the account is out of credits
- `PlanError` — that model needs a paid plan or a credit pack
- `RejectedError` — the content filter or the model refused the prompt; rewrite it rather than retrying

The API answers refusals with HTTP 200 and an error code in the body, so a client that only checks the status code reports a refusal as success. This one reads the body.

Free-account output carries a watermark; a paid plan returns the clean file.

MIT licensed. Made by [SayMaker](https://saymaker.ai/?utm_source=pypi&utm_medium=package), the AI video generator agent.
