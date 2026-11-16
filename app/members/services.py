import os
from decimal import Decimal

from openai import OpenAI
from django.db import transaction
from django.db.models import Q

from .models import AI_Models, APIUsage, Conversations, Messages, Responses


NVIDIA_MODELS = {
    "deepseek-ai/deepseek-v4.1-flash": {
        "label": "DeepSeek V4.1 Flash",
        "temperature": 1,
        "top_p": 0.95,
    },
    "z-ai/glm-5.3-flash": {
        "label": "GLM-5.3 Flash",
        "temperature": 0.5,
        "top_p": 1,
    },
}
DEFAULT_NVIDIA_MODEL = "deepseek-ai/deepseek-v4.1-flash"

OPENROUTER_MODELS = {
    "inclusionai/ling-3.2-flash:free": {
        "label": "Ling 3.2 Flash (Free)",
    },
    "google/gemma-4-26b-a4b-it:free": {
        "label": "Gemma 4 26B A4B (Free)",
    },
}
SUPPORTED_MODELS = {**OPENROUTER_MODELS, **NVIDIA_MODELS}
DEFAULT_MODEL = "inclusionai/ling-3.2-flash:free"


def provider_for_model(model):
    if model in OPENROUTER_MODELS:
        return "OpenRouter"
    if model in NVIDIA_MODELS:
        return "NVIDIA"
    raise ValueError("Unsupported model.")


def configured_models():
    """Only models explicitly supported by this app can be selected."""
    return [
        row for row in AI_Models.objects.filter(name__in=SUPPORTED_MODELS)
        if row.provider == provider_for_model(row.name)
    ]


def has_provider_key(model=None):
    """Look up the selected provider's secret from the server environment."""
    model = model or DEFAULT_MODEL
    key_var = "OPENROUTER_API_KEY" if provider_for_model(model) == "OpenRouter" else "NVIDIA_API_KEY"
    return bool(os.getenv(key_var, "").strip())


@transaction.atomic
def save_prompt_and_build_history(*, user, prompt, model, conversation_id=None, request_id=None):
    """Save one prompt and build ordered chat-completions history.

    Returns (conversation, saved_message, history). The view should pass
    the authenticated User and a validated AI_Models row. This function
    does not make an external API request.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string.")
    if not isinstance(model, AI_Models) or model.pk is None:
        raise ValueError("model must be a saved AI_Models instance.")
    if user.pk is None:
        raise ValueError("user must be a saved User instance.")

    prompt = prompt.strip()
    if conversation_id is None:
        conversation = Conversations.objects.create(user=user, title=prompt[:30])
    else:
        conversation = Conversations.objects.select_for_update().get(
            pk=conversation_id, user=user
        )

    saved_message = Messages.objects.create(
        conversation=conversation, model=model, raw_msg=prompt, request_id=request_id
    )
    history = []
    for message in (
        Messages.objects.filter(conversation=conversation)
        .filter(Q(status='completed') | Q(pk=saved_message.pk))
        .select_related("responses")
        .order_by("sent_at", "pk")
    ):
        history.append({"role": "user", "content": message.raw_msg})
        response = getattr(message, "responses", None)
        if response is not None:
            history.append({"role": "assistant", "content": response.raw_output})

    return conversation, saved_message, history


@transaction.atomic
def save_answer_and_usage(message, answer, usage=None):
    """Persist an answer and provider-reported token counts together."""
    if not answer:
        raise ValueError("Empty provider response.")
    Responses.objects.create(message=message, raw_output=answer)
    recorded_usage = None
    if (usage is not None and getattr(usage, 'prompt_tokens', None) is not None
            and getattr(usage, 'completion_tokens', None) is not None):
        input_tokens = int(usage.prompt_tokens)
        output_tokens = int(usage.completion_tokens)
        cost = None
        if (message.model.cost_per_mil_input_toks is not None and
                message.model.cost_per_mil_output_toks is not None):
            cost = (
                Decimal(input_tokens) * message.model.cost_per_mil_input_toks
                + Decimal(output_tokens) * message.model.cost_per_mil_output_toks
            ) / Decimal(1_000_000)
            cost = cost.quantize(Decimal("0.0000000001"))
        recorded_usage = APIUsage.objects.create(
            message=message, input_tokens=input_tokens,
            output_tokens=output_tokens, total_cost=cost,
        )
    message.status = "completed"
    message.save(update_fields=["status"])
    return recorded_usage


def generate_messages(messages, model=None):
    """Stream one provider reply using the selected model's server-side key."""
    model = model or DEFAULT_MODEL
    provider = provider_for_model(model)
    key_var = "OPENROUTER_API_KEY" if provider == "OpenRouter" else "NVIDIA_API_KEY"
    if not has_provider_key(model):
        raise RuntimeError(f"{key_var} is not configured.")
    client = OpenAI(
        base_url=(
            "https://openrouter.ai/api/v1" if provider == "OpenRouter"
            else "https://integrate.api.nvidia.com/v1"
        ),
        api_key=os.environ[key_var],
        timeout=120.0 if provider == "OpenRouter" else 270.0,
        max_retries=0,  # retries could incur duplicate inference charges
    )
    stream = None
    try:
        options = {
            "model": model,
            "messages": messages,
            "max_tokens": 2048 if provider == "OpenRouter" else (
                4096 if model.startswith("z-ai/") else 2048
            ),
            "stream": True,
        }
        if provider == "OpenRouter":
            options["stream_options"] = {"include_usage": True}
        else:
            options["temperature"] = NVIDIA_MODELS[model]["temperature"]
            options["top_p"] = NVIDIA_MODELS[model]["top_p"]
        stream = client.chat.completions.create(**options)
        yield from stream
    finally:
        if stream is not None:
            stream.close()
        client.close()

