from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models import Avg


# Create your models here.
class Product(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=200)
    country_of_origin = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    winery = models.CharField(max_length=100)
    variety = models.CharField(max_length=100)
    image_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ratings = models.FloatField(default=0.0)
    slug = models.SlugField(unique=True, max_length=200)

    def __str__(self):
        return self.title
    
    def update_average_rating(self):
        """Recalculate and update the average rating."""
        avg_rating = self.user_ratings.aggregate(avg=Avg("stars"))["avg"]
        self.ratings = avg_rating if avg_rating is not None else 0.0
        self.save(update_fields=["ratings"])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super(Product, self).save(*args, **kwargs)


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='user_ratings')
    stars = models.PositiveIntegerField(choices=[(i, i) for i in range(1,6)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def save(self, *args, **kwargs):
        super(Rating, self).save(*args, **kwargs)
        # Update product average rating whenever a rating is created/updated
        self.product.update_average_rating()

    def __str__(self):
        return f"{self.user.username} - {self.product.title} ({self.stars}⭐)"