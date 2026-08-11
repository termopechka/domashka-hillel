from django.db import models
from django.utils.translation import gettext_lazy as _


class Book(models.Model):
    external_id = models.UUIDField(_("External ID"), unique=True)
    isbn = models.CharField(
        _("ISBN"), max_length=13, unique=True, null=True, blank=True
    )
    title = models.CharField(_("Title"), max_length=255)
    author = models.CharField(_("Author"), max_length=255)
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Book")
        verbose_name_plural = _("Books")

    def __str__(self):
        return f"{self.title} — {self.author}"
