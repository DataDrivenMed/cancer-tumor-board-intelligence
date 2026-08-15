from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from services.extraction_normalization import normalize_structured_output


class ModelGatewayError(RuntimeError):
    pass


DEFAULT_HF_ROUTER = "https://router.huggingface.co/v1"


def structured_json_response_raw(
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
    """Return the provider's parsed structured output without post-model mutation.

    This function is the audit-preserving entry point for extraction workflows.
    Callers that normalize or repair output must do so explicitly and retain this
    raw payload separately from the normalized representation.
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
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ModelGatewayError("The model returned structured output with a non-object top level.")
        return parsed
    except ModelGatewayError:
        raise
    except Exception as exc:
        raise ModelGatewayError(
            f"Structured extraction request failed through the configured model endpoint: {exc}"
        ) from exc


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
    """Compatibility wrapper returning schema-aware normalized structured output.

    New extraction code should prefer ``structured_json_response_raw`` and apply
    normalization explicitly so both raw and normalized payloads remain auditable.
    Existing non-extraction callers retain their prior behavior through this wrapper.
    """

    parsed = structured_json_response_raw(
        model=model,
        system_instructions=system_instructions,
        user_input=user_input,
        schema_name=schema_name,
        json_schema=json_schema,
        api_key=api_key,
        auth_token=auth_token,
        base_url=base_url,
        reasoning_effort=reasoning_effort,
    )
    return normalize_structured_output(schema_name, parsed)
