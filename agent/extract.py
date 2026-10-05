from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from agent.llm import DEFAULT_MODEL, LLMResult, parse_structured, write_trace
from agent.prompts import load


class ExtractionError(Exception):
    def __init__(
        self,
        message: str,
        *,
        input_text: str,
        attempts: list[str],
        errors: list[str],
        trace_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.input_text = input_text
        self.attempts = attempts
        self.errors = errors
        self.trace_id = trace_id


@dataclass
class ExtractionResult:
    data: BaseModel
    metadata: LLMResult
    retry_count: int
    trace_id: str


def extract(
    text: str,
    schema: type[BaseModel],
    prompt_name: str = "extract_fields",
    model: str = DEFAULT_MODEL,
) -> ExtractionResult:
    rendered, version = load(prompt_name, input_text=text, schema_name=schema.__name__)
    attempts: list[str] = []
    errors: list[str] = []
    last_result: LLMResult | None = None

    for retry_count in range(2):
        prompt = rendered
        if retry_count == 1:
            prompt = (
                f"{rendered}\n\nThe previous object failed validation: {errors[-1]}. "
                "Return a corrected object that satisfies the schema. Do not invent missing facts."
            )
        try:
            parsed, result = parse_structured(
                prompt, schema, model=model, prompt_version=version
            )
            last_result = result
            attempts.append(result.text)
            if parsed is None:
                raise ValidationError.from_exception_data(schema.__name__, [])
            return ExtractionResult(
                data=parsed,
                metadata=result,
                retry_count=retry_count,
                trace_id=result.trace_id,
            )
        except Exception as error:
            errors.append(str(error))
            if last_result is not None:
                try:
                    write_trace(last_result)
                except Exception:
                    pass

    raise ExtractionError(
        "extraction failed after one retry",
        input_text=text,
        attempts=attempts,
        errors=errors,
        trace_id=last_result.trace_id if last_result else None,
    )
