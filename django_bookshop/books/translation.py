from modeltranslation.translator import register, TranslationOptions
from .models import Book


@register(Book)
class BookTranslationOptions(TranslationOptions):
    fields = ("title", "description")
