from __future__ import annotations

import json
from typing import Any

from openai import OpenAI


class ModelGatewayError(RuntimeError):
    pass


def structured_json_response(
    *,
    api_key: str,
    model: str,
    system_instructions: str,
    user_input: str,
    schema_name: str,
    json_schema: dict[str, Any],
) -> dict[str, Any]:
    """Call the OpenAI Responses API with Structured Outputs.

    The gateway is intentionally small so another provider can be substituted later
    without changing the clinical extraction contract.
    """
    if not api_key:
        raise ModelGatewayError("OPENAI_API_KEY is not configured.")

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            instructions=system_instructions,
            input=user_input,
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": json_schema,
                }
            },
            store=False,
        )
        if not response.output_text:
            raise ModelGatewayError("The model returned no structured output.")
        return json.loads(response.output_text)
    except ModelGatewayError:
        raise
    except Exception as exc:
        raise ModelGatewayError(f"Structured extraction request failed: {exc}") from exc
