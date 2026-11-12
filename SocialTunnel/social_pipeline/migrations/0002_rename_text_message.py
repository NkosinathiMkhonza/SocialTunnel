from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("social_pipeline", "0001_initial"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Text",
            new_name="Message",
        ),
    ]
