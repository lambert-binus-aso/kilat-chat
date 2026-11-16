from django.contrib import admin
from .models import AI_Models, APIUsage, Conversations, Messages, Responses, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email')
    search_fields = ('username', 'email')
    readonly_fields = ('password',)  # Password hashes must never be edited as plain text.


@admin.register(AI_Models)
class AIModelsAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'cost_per_mil_input_toks', 'cost_per_mil_output_toks')
    search_fields = ('name', 'provider')


@admin.register(Conversations)
class ConversationsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'created_at')
    search_fields = ('title', 'user__email')


@admin.register(Messages)
class MessagesAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'model', 'status', 'sent_at')
    list_filter = ('status', 'model')
    readonly_fields = ('request_id',)


@admin.register(Responses)
class ResponsesAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'created_at')


@admin.register(APIUsage)
class APIUsageAdmin(admin.ModelAdmin):
    list_display = ('message', 'input_tokens', 'output_tokens', 'total_cost')
