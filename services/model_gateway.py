from __future__ import annotations

import json
from typing import Any

from openai import OpenAI


class ModelGatewayError(RuntimeError):
    pass


def structured_json_response(
    *,
    base_url: str,
    auth_token: str | None,
    model: str,
    system_instructions: str,
    user_input: str,
    schema_name: str,
    json_schema: dict[str, Any],
    reasoning_effort: str = "high",
) -> dict[str, Any]:
    """Call an OpenAI-compatible inference endpoint with JSON-schema output.

    This gateway is provider-neutral. It can point to Hugging Face Inference
    Providers, Groq, Fireworks, Together, a self-hosted vLLM server, or another
    OpenAI-compatible endpoint. The application therefore does not depend on
    the OpenAI API or on any specific commercial model host.

    For local/self-hosted endpoints that do not require authentication, a
    harmless placeholder token is supplied only because the OpenAI Python
    client expects a non-empty api_key value.
    """
    if not base_url:
        raise ModelGatewayError("MODEL_BASE_URL is not configured.")
    if not model:
        raise ModelGatewayError("MODEL_NAME is not configured.")

    client = OpenAI(
        base_url=base_url.rstrip("/"),
        api_key=auth_token or "local-no-auth",
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
