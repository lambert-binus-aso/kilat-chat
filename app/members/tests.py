from django.test import TestCase
from decimal import Decimal
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.contrib.auth.hashers import check_password
from django.test import Client
from .models import User
from .models import AI_Models, APIUsage, Conversations, Messages, Responses
from .services import save_prompt_and_build_history, save_answer_and_usage, generate_messages


class SessionFlowTests(TestCase):
    def test_signup_login_logout(self):
        signup = self.client.post('/signup/', {
            'username': 'sampleuser',
            'email': 'sample@example.com',
            'password': 'ExamplePass123!',
        })
        self.assertEqual(signup.status_code, 201)
        self.assertEqual(signup.json()['redirect'], '/chat/')
        user = User.objects.get(email='sample@example.com')
        self.assertTrue(check_password('ExamplePass123!', user.password))
        self.assertEqual(self.client.get('/api/me/').json()['id'], user.id)

        logout = self.client.post('/logout/')
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(self.client.get('/api/me/').status_code, 401)

        wrong = self.client.post('/login/', {
            'email': 'sample@example.com',
            'password': 'wrong-password',
        })
        self.assertEqual(wrong.status_code, 400)

        login = self.client.post('/login/', {
            'email': 'sample@example.com',
            'password': 'ExamplePass123!',
        })
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get('/api/me/').json()['username'], 'sampleuser')


class ConversationHistoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='owner', email='owner@example.com', password='unused')
        self.other_user = User.objects.create(username='other', email='other@example.com', password='unused')
        self.model = AI_Models.objects.create(
            name='deepseek-ai/deepseek-v4.1-flash',
            provider='NVIDIA',
            cost_per_mil_input_toks='0.1',
            cost_per_mil_output_toks='0.2',
        )

    def test_new_conversation_saves_prompt(self):
        conversation, message, history = save_prompt_and_build_history(
            user=self.user, prompt='  Hello!  ', model=self.model
        )
        self.assertEqual(conversation.user, self.user)
        self.assertEqual(message.raw_msg, 'Hello!')
        self.assertEqual(message.model, self.model)
        self.assertEqual(history, [{'role': 'user', 'content': 'Hello!'}])

    def test_existing_conversation_includes_previous_assistant_responses(self):
        conversation, first, _ = save_prompt_and_build_history(
            user=self.user, prompt='First prompt', model=self.model
        )
        save_answer_and_usage(first, 'First answer')
        _, second, history = save_prompt_and_build_history(
            user=self.user, prompt='Second prompt', model=self.model,
            conversation_id=conversation.pk,
        )
        self.assertEqual(second.conversation, conversation)
        self.assertEqual(
            history,
            [
                {'role': 'user', 'content': 'First prompt'},
                {'role': 'assistant', 'content': 'First answer'},
                {'role': 'user', 'content': 'Second prompt'},
            ],
        )
        self.assertEqual(Messages.objects.filter(conversation=conversation).count(), 2)

    def test_other_users_conversations_cannot_be_appended(self):
        conversation = Conversations.objects.create(user=self.other_user, title='Private')
        with self.assertRaises(Conversations.DoesNotExist):
            save_prompt_and_build_history(
                user=self.user, prompt='Not allowed', model=self.model,
                conversation_id=conversation.pk,
            )
        self.assertFalse(Messages.objects.filter(conversation=conversation).exists())

    def test_blank_prompt_is_rejected_without_writing(self):
        with self.assertRaises(ValueError):
            save_prompt_and_build_history(user=self.user, prompt='  ', model=self.model)
        self.assertFalse(Messages.objects.exists())


class ChatAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='owner', email='owner@example.com', password='unused',
        )
        self.other = User.objects.create(
            username='other', email='other@example.com', password='unused',
        )
        session = self.client.session
        session['user_id'] = self.user.id
        session.save()

    def post_chat(self, message='What is a transistor?', model='deepseek-ai/deepseek-v4.1-flash',
                  conversation_id=None, request_id=None):
        return self.client.post(
            '/api/chat/',
            data=json.dumps({
                'message': message, 'model': model,
                'conversation_id': conversation_id,
                'request_id': request_id or str(uuid4()),
            }),
            content_type='application/json',
        )

    def chunks(self):
        return iter([
            SimpleNamespace(choices=[
                SimpleNamespace(delta=SimpleNamespace(content='## Hello\n')),
            ], usage=None),
            SimpleNamespace(choices=[
                SimpleNamespace(delta=SimpleNamespace(content='**world**')),
            ], usage=None),
            SimpleNamespace(choices=[], usage=SimpleNamespace(
                prompt_tokens=100, completion_tokens=20,
            )),
        ])

    def test_model_list_contains_both_supported_models(self):
        response = self.client.get('/api/models/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item['id'] for item in response.json()['models']},
            {'deepseek-ai/deepseek-v4.1-flash', 'z-ai/glm-5.3-flash'},
        )

    def test_streams_and_persists_chat_with_usage(self):
        model = AI_Models.objects.get(name='deepseek-ai/deepseek-v4.1-flash', provider='NVIDIA')
        model.cost_per_mil_input_toks = Decimal('0.25000000')
        model.cost_per_mil_output_toks = Decimal('0.75000000')
        model.save()
        identifier = str(uuid4())
        with patch('members.api.has_provider_key', return_value=True), patch(
            'members.api.generate_messages', side_effect=lambda history, model: self.chunks(),
        ) as provider:
            response = self.post_chat(request_id=identifier)
            self.assertEqual(response.status_code, 200)
            events = b''.join(response.streaming_content).decode()
            self.assertIn('event: meta', events)
            self.assertIn('event: delta', events)
            self.assertIn('## Hello', events)
            self.assertIn('event: done', events)
            self.assertEqual(provider.call_count, 1)
            self.assertEqual(provider.call_args.kwargs['model'], model.name)
            self.assertEqual(provider.call_args.args[0], [
                {'role': 'user', 'content': 'What is a transistor?'},
            ])

        message = Messages.objects.get(request_id=identifier)
        self.assertEqual(message.status, 'completed')
        self.assertEqual(message.responses.raw_output, '## Hello\n**world**')
        usage = APIUsage.objects.get(message=message)
        self.assertEqual((usage.input_tokens, usage.output_tokens), (100, 20))
        self.assertEqual(usage.total_cost, Decimal('0.0000400000'))
        thread = self.client.get(f'/api/conversations/{message.conversation_id}/').json()
        self.assertEqual([row['role'] for row in thread['messages']], ['user', 'assistant'])
        self.assertEqual(self.client.get('/api/conversations/').json()['conversations'][0]['id'], message.conversation_id)

        # A duplicate POST returns stored output without another provider call.
        with patch('members.api.generate_messages') as provider:
            duplicate = self.post_chat(request_id=identifier)
            self.assertEqual(duplicate.status_code, 200)
            self.assertEqual(duplicate.json()['reply'], '## Hello\n**world**')
            provider.assert_not_called()
        self.assertEqual(Messages.objects.count(), 1)

    def test_switching_models_preserves_correct_history(self):
        with patch('members.api.has_provider_key', return_value=True), patch(
            'members.api.generate_messages', side_effect=lambda history, model: self.chunks(),
        ) as provider:
            first = self.post_chat('Explain RAM.')
            list(first.streaming_content)
            thread_id = Messages.objects.first().conversation_id
            second = self.post_chat(
                'Explain ROM.', model='z-ai/glm-5.3-flash',
                conversation_id=thread_id,
            )
            list(second.streaming_content)
            self.assertEqual(provider.call_args.kwargs['model'], 'z-ai/glm-5.3-flash')
            self.assertEqual(provider.call_args.args[0], [
                {'role': 'user', 'content': 'Explain RAM.'},
                {'role': 'assistant', 'content': '## Hello\n**world**'},
                {'role': 'user', 'content': 'Explain ROM.'},
            ])
        self.assertEqual(
            list(Messages.objects.order_by('pk').values_list('model__name', flat=True)),
            ['deepseek-ai/deepseek-v4.1-flash', 'z-ai/glm-5.3-flash'],
        )

    def test_authentication_and_ownership(self):
        self.assertEqual(self.client.get('/api/conversations/').status_code, 200)
        other_thread = Conversations.objects.create(user=self.other, title='Private')
        self.assertEqual(self.client.get(f'/api/conversations/{other_thread.pk}/').status_code, 404)
        self.assertEqual(self.post_chat(conversation_id=other_thread.pk).status_code, 404)
        self.assertFalse(Messages.objects.exists())
        self.client.post('/logout/')
        self.assertEqual(self.client.get('/api/conversations/').status_code, 401)
        self.assertEqual(self.post_chat().status_code, 401)

    def test_provider_error_marks_prompt_failed(self):
        def faulty_stream(history, model):
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content='Partial'))],
                usage=None,
            )
            raise RuntimeError('Simulated provider failure')

        with patch('members.api.has_provider_key', return_value=True), patch(
            'members.api.generate_messages', side_effect=faulty_stream,
        ):
            response = self.post_chat()
            events = b''.join(response.streaming_content).decode()
        self.assertIn('event: error', events)
        self.assertNotIn('event: done', events)
        message = Messages.objects.get()
        self.assertEqual(message.status, 'failed')
        self.assertFalse(Responses.objects.exists())
        self.assertFalse(APIUsage.objects.exists())

    def test_rejects_unsupported_model_and_invalid_input(self):
        self.assertEqual(self.post_chat(model='gpt-6').status_code, 400)
        self.assertEqual(self.post_chat(message=' ').status_code, 400)
        self.assertFalse(Messages.objects.exists())

    def test_chat_api_requires_csrf_token(self):
        protected = Client(enforce_csrf_checks=True)
        session = protected.session
        session['user_id'] = self.user.pk
        session.save()
        page = protected.get('/chat/')
        self.assertIn('csrftoken', page.cookies)
        response = protected.post(
            '/api/chat/',
            data=json.dumps({
                'message': 'Test', 'model': 'z-ai/glm-5.3-flash',
                'conversation_id': None,
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Messages.objects.exists())

    def test_glm_provider_uses_documented_id_and_parameters(self):
        streamed = MagicMock()
        streamed.__iter__.return_value = iter([])
        with patch.dict('os.environ', {'NVIDIA_API_KEY': 'test-only-key'}), patch(
            'members.services.OpenAI',
        ) as client_type:
            client_type.return_value.chat.completions.create.return_value = streamed
            list(generate_messages(
                [{'role': 'user', 'content': 'Hi!'}],
                model='z-ai/glm-5.3-flash',
            ))
            options = client_type.return_value.chat.completions.create.call_args.kwargs
            self.assertEqual(options['model'], 'z-ai/glm-5.3-flash')
            self.assertEqual(options['temperature'], 0.5)
            self.assertEqual(options['top_p'], 1)
            self.assertTrue(options['stream'])
            streamed.close.assert_called_once()
            client_type.return_value.close.assert_called_once()
