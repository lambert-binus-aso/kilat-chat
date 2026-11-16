"""Authenticated JSON and SSE endpoints for KilatChat.

HTTP/session validation belongs here; provider calls and persistence helpers
live in services.py. Model API keys are never returned to the browser.
"""

import json
import logging
import uuid

from django.db import IntegrityError
from django.db.models import Max
from django.db.models.functions import Coalesce
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET, require_POST

from .models import AI_Models, Conversations, Messages, Responses, User
from .services import (
    NVIDIA_MODELS,
    configured_models,
    generate_messages,
    has_provider_key,
    save_answer_and_usage,
    save_prompt_and_build_history,
)

logger = logging.getLogger(__name__)
MAX_PROMPT_LENGTH = 20_000


def _user(request):
    pk = request.session.get('user_id')
    return User.objects.filter(pk=pk).first() if pk else None


def _unauthorized():
    return JsonResponse({'error': 'Please log in to use KilatChat.'}, status=401)


def _error(message, status=400, **extra):
    return JsonResponse({'error': message, **extra}, status=status)


def _sse(event, data):
    return f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'


@require_GET
def models_api(request):
    records = {row.name for row in configured_models()}
    return JsonResponse({
        'models': [
            {'id': name, 'name': details['label'], 'provider': 'NVIDIA'}
            for name, details in NVIDIA_MODELS.items() if name in records
        ],
    })


@require_GET
def conversations_api(request):
    user = _user(request)
    if user is None:
        return _unauthorized()
    threads = (
        Conversations.objects.filter(user=user)
        .annotate(last_activity=Coalesce(Max('messages__sent_at'), 'created_at'))
        .order_by('-last_activity', '-pk')
    )
    return JsonResponse({
        'conversations': [
            {'id': thread.pk, 'title': thread.title}
            for thread in threads
        ],
    })


@require_GET
def conversation_api(request, conversation_id):
    user = _user(request)
    if user is None:
        return _unauthorized()
    conversation = Conversations.objects.filter(user=user, pk=conversation_id).first()
    if conversation is None:
        return _error('Conversation not found.', status=404)
    messages = (
        Messages.objects.filter(conversation=conversation)
        .select_related('model', 'responses')
        .order_by('sent_at', 'pk')
    )
    entries = []
    for message in messages:
        entries.append({
            'role': 'user',
            'text': message.raw_msg,
            'model': message.model.name,
            'status': message.status,
        })
        response = getattr(message, 'responses', None)
        if response is not None:
            entries.append({
                'role': 'assistant',
                'text': response.raw_output,
                'model': message.model.name,
            })
    return JsonResponse({
        'conversation_id': conversation.pk,
        'title': conversation.title,
        'messages': entries,
    })


@require_POST
def chat_api(request):
    user = _user(request)
    if user is None:
        return _unauthorized()

    if len(request.body) > 65_536:
        return _error('Message request is too large.', status=413)
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return _error('Invalid JSON request.')
    if not isinstance(data, dict):
        return _error('Expected a JSON object.')

    prompt = data.get('message')
    model_id = data.get('model')
    conversation_id = data.get('conversation_id')
    request_id = data.get('request_id')
    if not isinstance(prompt, str) or not prompt.strip():
        return _error('Enter a message to send.')
    if len(prompt) > MAX_PROMPT_LENGTH:
        return _error('Messages cannot exceed 20,000 characters.')
    if not isinstance(model_id, str) or model_id not in NVIDIA_MODELS:
        return _error('Select a supported model.')
    if conversation_id is not None:
        if isinstance(conversation_id, bool) or not str(conversation_id).isdigit():
            return _error('Invalid conversation ID.')
        conversation_id = int(conversation_id)
        if not Conversations.objects.filter(pk=conversation_id, user=user).exists():
            return _error('Conversation not found.', status=404)

    if request_id is None:
        request_id = uuid.uuid4()
    else:
        try:
            request_id = uuid.UUID(str(request_id))
        except (ValueError, TypeError, AttributeError):
            return _error('Invalid request ID.')

    # Repeated submits never cause a second inference. A completed request
    # can return its saved result; in-flight/failed requests are not replayed.
    previous = Messages.objects.select_related('conversation', 'responses').filter(
        request_id=request_id, conversation__user=user,
    ).first()
    if previous is not None:
        if previous.raw_msg != prompt.strip() or previous.model.name != model_id:
            return _error('This request ID has already been used.', status=409)
        if previous.status == 'completed':
            answer = getattr(previous, 'responses', None)
            if answer is not None:
                return JsonResponse({
                    'conversation_id': previous.conversation_id,
                    'title': previous.conversation.title,
                    'reply': answer.raw_output,
                })
        return _error(
            'This request was already submitted. Refresh conversation history before sending again.',
            status=409,
            conversation_id=previous.conversation_id,
        )

    if not has_provider_key():
        return _error('NVIDIA_API_KEY is not configured on the server.', status=503)
    model = AI_Models.objects.filter(provider='NVIDIA', name=model_id).first()
    if model is None:
        return _error('Model configuration is missing. Run Django migrations.', status=503)
    try:
        conversation, saved, history = save_prompt_and_build_history(
            user=user,
            prompt=prompt,
            model=model,
            conversation_id=conversation_id,
            request_id=request_id,
        )
    except IntegrityError:
        return _error('Another request is already in progress. Refresh history and try again.', status=409)
    except Conversations.DoesNotExist:
        return _error('Conversation not found.', status=404)

    def events():
        answer_parts = []
        usage = None
        try:
            yield _sse('meta', {
                'conversation_id': conversation.pk,
                'title': conversation.title,
                'model': model_id,
            })
            for chunk in generate_messages(history, model=model_id):
                if getattr(chunk, 'usage', None) is not None:
                    usage = chunk.usage
                for choice in getattr(chunk, 'choices', []) or []:
                    delta = getattr(choice, 'delta', None)
                    content = getattr(delta, 'content', None)
                    # Deliberately do not send hidden reasoning_content.
                    if isinstance(content, str) and content:
                        answer_parts.append(content)
                        yield _sse('delta', {'text': content})
            answer = ''.join(answer_parts)
            save_answer_and_usage(saved, answer, usage)
            yield _sse('done', {'conversation_id': conversation.pk, 'title': conversation.title})
        except Exception:
            logger.exception('Model generation or answer persistence failed (message_id=%s)', saved.pk)
            yield _sse('error', {
                'error': 'The model could not complete this request. Your prompt was saved; please start a new message.',
                'conversation_id': conversation.pk,
            })
        finally:
            # Also releases a pending conversation if the client disconnects
            # and closes the streaming iterator before the model finishes.
            Messages.objects.filter(pk=saved.pk, status='pending').update(status='failed')

    response = StreamingHttpResponse(events(), content_type='text/event-stream; charset=utf-8')
    response['Cache-Control'] = 'no-cache, no-transform'
    response['X-Accel-Buffering'] = 'no'
    return response
