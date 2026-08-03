from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Name of category")
    slug = models.SlugField(max_length=100)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(_("Title"), max_length=100)
    author = models.CharField(_("Author"), max_length=100)
    price = models.DecimalField(
        _("Price"), decimal_places=2, max_digits=10, null=True, blank=True
    )
    description = models.TextField(_("Description"))
    stock = models.IntegerField(_("Stock"), default=0)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name="books",
        verbose_name=_("Category"),
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.title} by {self.author}"

    def get_absolute_url(self):
        return reverse("book:detail", kwargs={"pk": self.pk})
