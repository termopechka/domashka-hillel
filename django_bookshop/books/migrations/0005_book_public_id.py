import uuid

from django.db import migrations, models


def populate_public_ids(apps, schema_editor):
    Book = apps.get_model("books", "Book")
    for book in Book.objects.filter(public_id__isnull=True).iterator():
        book.public_id = uuid.uuid4()
        book.save(update_fields=["public_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("books", "0004_alter_book_author_alter_book_description_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="public_id",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(populate_public_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="book",
            name="public_id",
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
    ]
