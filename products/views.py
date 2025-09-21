from django.shortcuts import render, get_object_or_404
from .models import Product, Rating
from django.core.paginator import Paginator

# Create your views here.
def home_view(request):
    products = Product.objects.all().order_by("-id")
    paginator = Paginator(products, 20)
    page_number = int(request.GET.get("page", 1))
    page_obj = paginator.get_page(page_number)
    ratings = Rating.objects.all()
    print("Products on page:", page_obj.object_list.count())

    context = {
        "page_obj": page_obj,
        "ratings": ratings
    }
    if request.headers.get("HX-Request") == "true":
        return render(request, "products/partials/products.html", context)
    return render(request, 'home.html', context)

def product_detail_view(request, id):
    product = get_object_or_404(Product, id=id)
    rating = Rating.objects.filter(product=product).first()
    context = {
        "product": product,
        "rating": rating
    }
    return render(request, 'products/product_details.html', context)