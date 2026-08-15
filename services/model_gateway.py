from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI


class ModelGatewayError(RuntimeError):
    pass


DEFAULT_HF_ROUTER = "https://router.huggingface.co/v1"


def structured_json_response(
    *,
    model: str,
    system_instructions: str,
    user_input: str,
    schema_name: str,
    json_schema: dict[str, Any],
    api_key: str | None = None,
    auth_token: str | None = None,
    base_url: str | None = None,
    reasoning_effort: str = "high",
) -> dict[str, Any]:
    """Call an OpenAI-compatible endpoint with strict JSON-schema output.

    The clinical application is model-provider neutral. By default the hosted
    research prototype uses Hugging Face Inference Providers, which can route
    the open-weight gpt-oss model to supported inference backends. A self-hosted
    OpenAI-compatible endpoint can be selected with MODEL_BASE_URL.

    `api_key` remains as a compatibility alias for older callers. It is not
    specific to the OpenAI API and may contain a Hugging Face/provider token.
    """
    endpoint = base_url or os.getenv("MODEL_BASE_URL") or DEFAULT_HF_ROUTER
    token = auth_token or api_key or os.getenv("MODEL_AUTH_TOKEN") or os.getenv("HF_TOKEN")

    if not model:
        raise ModelGatewayError("MODEL_NAME is not configured.")
    if endpoint == DEFAULT_HF_ROUTER and not token:
        raise ModelGatewayError(
            "No inference token is configured. The default Hugging Face router requires a Hugging Face token. "
            "This is not an OpenAI API key."
        )

    client = OpenAI(
        base_url=endpoint.rstrip("/"),
        api_key=token or "local-no-auth",
    )

    request: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_input},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": json_schema,
            },
        },
    }
    if reasoning_effort:
        request["reasoning_effort"] = reasoning_effort

    try:
        response = client.chat.completions.create(**request)
        content = response.choices[0].message.content
        if not content:
            raise ModelGatewayError("The model returned no structured output.")
        return json.loads(content)
    except ModelGatewayError:
        raise
    except Exception as exc:
        raise ModelGatewayError(
            f"Structured extraction request failed through the configured model endpoint: {exc}"
        ) from exc
