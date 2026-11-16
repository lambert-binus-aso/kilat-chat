from django.db import migrations


def seed_free_models(apps, schema_editor):
    AIModels = apps.get_model("members", "AI_Models")
    for model_id in (
        "inclusionai/ling-3.2-flash:free",
        "google/gemma-4-26b-a4b-it:free",
    ):
        AIModels.objects.get_or_create(
            name=model_id,
            provider="OpenRouter",
            defaults={
                "cost_per_mil_input_toks": 0,
                "cost_per_mil_output_toks": 0,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("members", "0006_seed_nvidia_models"),
    ]

    operations = [
        # Preserve any referenced model rows if the migration is reversed.
        migrations.RunPython(seed_free_models, migrations.RunPython.noop),
    ]
