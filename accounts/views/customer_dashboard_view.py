from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from products.models import Product
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.models import User
import math
from django.utils.translation import gettext_lazy as _
from accounts.views.role_based_redirect import farmer_required, customer_required
from accounts.models import FarmerReview, CustomerProfile, FarmerProfile  # Import FarmerProfile
from django.db.models import Avg
from products.models import ProductSynonym
import json
from products.views import synonyms_dict
from django.http import JsonResponse


def haversine(lat1, lon1, lat2, lon2):
    """Calculating  the great-circle distance between two points on the Earth using harversine formula to store 
    latitude and longitude of both faremer and customer."""
    R = 6371  # Earth radius in kilometers
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@login_required
@customer_required
def customer_dashboard_view(request):
    # getting the search query and filter parameters from the requesest from ui 
    query = request.GET.get('q')
    filter_type = request.GET.get('filter_type')
    distance_filter = request.GET.get('distance_filter')

#   Fetching all products by recently posted date
    products = Product.objects.all().order_by('-date_posted')


# searching through name or synonyms of the product
    if query:
        query_lower = query.lower()
        matching_ids = set()

        for product in products:
            # first matching through product sub_category
            if query_lower in product.sub_category.lower():
                matching_ids.add(product.id)
                continue

            # after cheching subcategory now Checking through  synonyms
            if ProductSynonym.objects.filter(product=product, synonym__icontains=query_lower).exists():
                matching_ids.add(product.id)
# showing only the matching products
        products = products.filter(id__in=matching_ids)

    # calculating average rating for each farmer
   
    farmer_avg_ratings = FarmerReview.objects.values('farmer').annotate(avg_rating=Avg('rating'))
    farmer_avg_dict = {item['farmer']: round(item['avg_rating'] or 0, 1) for item in farmer_avg_ratings}
    
    # attaching average rating to each product 
    for product in products:
        product.farmer_avg_rating = farmer_avg_dict.get(product.farmer.id, 0)

    # Price filter aplying if selected
    if filter_type == 'price':
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        if min_price and max_price:
            products = products.filter(price__gte=min_price, price__lte=max_price)
        elif min_price:
            products = products.filter(price__gte=min_price)
        elif max_price:
            products = products.filter(price__lte=max_price)

    # apply Date filter if selected through ui 
    elif filter_type == 'date':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date:
            start_date_parsed = parse_date(start_date)
            if start_date_parsed:
                products = products.filter(date_posted__gte=start_date_parsed)
        if end_date:
            end_date_parsed = parse_date(end_date)
            if end_date_parsed:
                products = products.filter(date_posted__lte=end_date_parsed)

    # Applying Quantity filter if selected in ui 
    elif filter_type == 'quantity':
        min_quantity = request.GET.get('min_quantity')
        max_quantity = request.GET.get('max_quantity')
        if min_quantity and max_quantity:
            products = products.filter(quantity__gte=min_quantity, quantity__lte=max_quantity)
        elif min_quantity:
            products = products.filter(quantity__gte=min_quantity)
        elif max_quantity:
            products = products.filter(quantity__lte=max_quantity)

# taking customer location from ui to calculated the ddistance between customer and farmer
    try:
        customer_profile = request.user.customerprofile
        customer_lat = customer_profile.latitude
        customer_lon = customer_profile.longitude
    except CustomerProfile.DoesNotExist:
        customer_profile = None
        customer_lat = None
        customer_lon = None

# a list to store products with their calculated distance
    products_with_distance = []

# Calculating distance between customer and farmer if both have latitude and longitude
    if customer_lat is not None and customer_lon is not None:
        for product in products:
            try:
                farmer_profile = product.farmer  # Use FarmerProfile
                farmer_lat = farmer_profile.latitude
                farmer_lon = farmer_profile.longitude
            except FarmerProfile.DoesNotExist:
                farmer_profile = None
                farmer_lat = None
                farmer_lon = None
        # compute distance only if both latitudes and longitudes are available

            if farmer_lat is not None and farmer_lon is not None:
                dist = haversine(customer_lat, customer_lon, farmer_lat, farmer_lon)
                product.distance = round(dist, 3)
                product.display_distance = f"{round(dist * 1000)} m" if dist < 1 else f"{dist:.2f} km"
                products_with_distance.append((product, dist))

                #No location data → treat as infinitely far

            else:
                product.distance = None
                product.display_distance = None
                products_with_distance.append((product, float('inf')))

        # Sort or filter by distance based on user selection in ui.
        if distance_filter == 'nearest':
            products_with_distance.sort(key=lambda x: x[1])
        elif distance_filter == 'farthest':
            products_with_distance.sort(key=lambda x: x[1], reverse=True)
        elif distance_filter == 'enter_range':
            min_dist = request.GET.get('min_distance')
            max_dist = request.GET.get('max_distance')
            unit = request.GET.get('distance_unit', 'km')

        # converting meter to kilometer if user selected meter as unit
            try:
                min_dist = float(min_dist) if min_dist else None
                max_dist = float(max_dist) if max_dist else None
                if unit == 'meter':
                    if min_dist is not None:
                        min_dist /= 1000
                    if max_dist is not None:
                        max_dist /= 1000
            except ValueError:
                min_dist = None
                max_dist = None

# filtering products within the specified distance range
            filtered = []
            for product, dist in products_with_distance:
                if dist == float('inf') or dist is None:
                    continue
                if min_dist is not None and dist < min_dist:
                    continue
                if max_dist is not None and dist > max_dist:
                    continue
                filtered.append((product, dist))
            products_with_distance = filtered

# Extract sorted/filtered products
        products = [p[0] for p in products_with_distance]

    else:
        for product in products:
            product.distance = None
            product.display_distance = None

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(products, 9)
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    # AJAX Response
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "accounts/customer_dashboard.html", {
        'products': products_page,
    })


    # Full page render
    return render(request, 'accounts/customer_dashboard.html', {
        'products': products_page,
        'customer_profile': customer_profile,
        'query': query,
        'filter_type': filter_type,
        'distance_filter': distance_filter,
        'synonyms_dict': json.dumps(synonyms_dict, ensure_ascii=False)
    })


@login_required
def view_farmer_location(request, farmer_id):
    farmer_profile = get_object_or_404(FarmerProfile, id=farmer_id)
    latitude = farmer_profile.latitude
    longitude = farmer_profile.longitude

    context = {
        'latitude': latitude,
        'longitude': longitude,
        'farmer_name': farmer_profile.user.username,
    }
    return render(request, 'accounts/view_farmer_location.html', context)