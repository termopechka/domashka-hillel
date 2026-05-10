from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Name of category')
    slug = models.SlugField(max_length=100)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    price = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    description = models.TextField()
    stock = models.IntegerField()
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name='books',
        verbose_name='Category',
        blank=True,
        null=True
    )

    def __str__(self):
        return f'{self.title} by {self.author}'