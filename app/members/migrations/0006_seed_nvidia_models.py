from django.db import migrations


def add_models(apps, schema_editor):
    AIModels = apps.get_model('members', 'AI_Models')
    for model_id in (
        'deepseek-ai/deepseek-v4.1-flash',
        'z-ai/glm-5.3-flash',
    ):
        AIModels.objects.get_or_create(
            name=model_id,
            provider='NVIDIA',
            defaults={
                'cost_per_mil_input_toks': None,
                'cost_per_mil_output_toks': None,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('members', '0005_messages_request_id_messages_status_and_more'),
    ]

    operations = [
        # Keep model records on rollback if conversations reference them.
        migrations.RunPython(add_models, migrations.RunPython.noop),
    ]
