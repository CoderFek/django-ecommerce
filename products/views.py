from django.shortcuts import render, get_object_or_404
from .models import Product, Rating

# Create your views here.
def home_view(request):
    products = Product.objects.all()
    ratings = Rating.objects.all()
    return render(request, 'home.html', {"products": products, "ratings": ratings})

def product_detail_view(request, id):
    product = get_object_or_404(Product, id=id)
    rating = Rating.objects.filter(product=product).first()
    context = {
        "product": product,
        "rating": rating
    }
    return render(request, 'products/product_details.html', context)