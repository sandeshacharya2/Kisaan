from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db.models import Prefetch
from django.contrib import messages
from accounts.models import FarmerReview
from django.db.models import Avg
# Import custom decorator
from accounts.views.role_based_redirect import farmer_required, customer_required
from django.utils.translation import gettext_lazy as _

# Models
from .models import Product
from chat.models import ChatRoom, Message
from accounts.models import FarmerProfile, CustomerProfile

# chat/views.py — ADD THIS

from django.contrib.auth.decorators import login_required
# from accounts.decorators import customer_required  # Make sure you have this decorator
from django.db.models import Prefetch


#  FIXED: confirm_chat — now skips if chat already exists
@customer_required
def confirm_chat(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    farmer_profile = product.farmer
    customer_profile = request.user.customerprofile  # Get customer profile

    #  Check if chat room already exists between this farmer + customer
    existing_chat = ChatRoom.objects.filter(
        farmer=farmer_profile,
        customer=customer_profile
    ).exists()

    if existing_chat:
        # ✅ Skip confirmation — go straight to chat
        return redirect('chat:start_chat', product_id=product.id)

    # ✅ Handle POST (user clicked confirm/cancel)
    if request.method == 'POST':
        if 'confirm' in request.POST:
            return redirect('chat:start_chat', product_id=product.id)
        else:
            return redirect('customer-dashboard')  # or 'customer:dashboard' — adjust name

    # ✅ First time — show confirmation page
    context = {
        'product': product,
        'farmer': farmer_profile,
    }
    return render(request, 'chat/chat_confirm.html', context)


@login_required
@customer_required
def customer_chats_view(request):
    user = request.user
    customer_profile = user.customerprofile

    # --- Get all accepted chats for this customer ---
    accepted_chats = ChatRoom.objects.filter(
        customer=customer_profile,
        farmer_accepted=True  # Only show chats farmer has accepted
    ).select_related('farmer__user', 'product').prefetch_related(
        Prefetch('message_set', queryset=Message.objects.order_by('-timestamp'))
    ).order_by('-created_at')

    # Group by farmer — show latest message per farmer
    farmer_chats = {}
    for chat in accepted_chats:
        farmer_id = chat.farmer.id
        if farmer_id not in farmer_chats:
            latest_msg = chat.message_set.first()
            farmer_chats[farmer_id] = {
                'farmer': chat.farmer,
                'latest_chat': chat,
                'latest_message': latest_msg.text if latest_msg else _("No messages yet"),
                'total_chats': 0,
            }
        farmer_chats[farmer_id]['total_chats'] += 1

    grouped_chats = list(farmer_chats.values())

    # Optional: Get pending chats count for sidebar badge
    pending_chats_count = ChatRoom.objects.filter(
        customer=customer_profile,
        farmer_accepted=False,
        farmer_rejected=False
    ).count()

    context = {
        'grouped_chats': grouped_chats,
        'pending_chats_count': pending_chats_count,  # For sidebar

    }

    return render(request, 'chat/customer_chats.html', context)


# ✅ MAIN CHAT MANAGEMENT VIEW — for farmers
@login_required
@farmer_required
def farmer_chats_view(request):
    user = request.user
    farmer_profile = user.farmerprofile

    # --- Pending Chat Requests ---
    pending_chats = ChatRoom.objects.filter(
        farmer=farmer_profile,
        farmer_accepted=False,
        farmer_rejected=False
    ).select_related('customer__user', 'product')

    # --- Accepted Chat Rooms (Grouped by Customer) ---
    accepted_chats = ChatRoom.objects.filter(
        farmer=farmer_profile,
        farmer_accepted=True
    ).select_related('customer__user', 'product').prefetch_related(
        Prefetch('message_set', queryset=Message.objects.order_by('-timestamp'))
    ).order_by('-created_at')

    # Group by customer — show latest message per customer
    customer_chats = {}
    for chat in accepted_chats:
        cust_id = chat.customer.id
        if cust_id not in customer_chats:
            latest_msg = chat.message_set.first()  # Already ordered by -timestamp
            customer_chats[cust_id] = {
                'customer': chat.customer,
                'latest_chat': chat,
                'latest_message': latest_msg.text if latest_msg else _("No messages yet"),
                'total_chats': 0,
            }
        customer_chats[cust_id]['total_chats'] += 1

    grouped_chats = list(customer_chats.values())
    # ✅ UPDATED: FarmerReview.farmer expects FarmerProfile
    avg_rating = FarmerReview.objects.filter(farmer=farmer_profile).aggregate(Avg('rating'))['rating__avg'] or 0
    avg_rating = round(avg_rating, 1)

    # ✅ UPDATED: Fetch reviews using FarmerProfile
    reviews = FarmerReview.objects.filter(farmer=farmer_profile).select_related('customer').order_by('-created_at')

    avg_rating = FarmerReview.objects.filter(farmer=farmer_profile).aggregate(Avg('rating'))['rating__avg'] or 0
    reviews = FarmerReview.objects.filter(farmer=farmer_profile).select_related('customer__user').order_by('-created_at')
    context = {
        'pending_chats': pending_chats,
        'grouped_chats': grouped_chats,
        'avg_rating': avg_rating,
        'reviews': reviews,
    }

    return render(request, 'chat/farmer_chats.html', context)


# CUSTOMER STARTS CHAT VIA PRODUCT
@login_required
def start_chat(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    farmer_profile = product.farmer

    try:
        customer_profile = request.user.customerprofile
    except CustomerProfile.DoesNotExist:
        return HttpResponseForbidden(_("You must be a registered customer to start a chat."))

    # ✅ Get or create chatroom — UNIQUE per farmer-customer pair
    chatroom, created = ChatRoom.objects.get_or_create(
        farmer=farmer_profile,
        customer=customer_profile,
        defaults={'product': product}  # Only set if new
    )

    if created:
        # First-time chat — send welcome message
        Message.objects.create(
            chatroom=chatroom,
            sender=request.user,
            text=_("Hi %(farmer_username)s, I'm interested in your product '%(product_name)s'. Please accept this chat to continue.") % {
                'farmer_username': farmer_profile.user.username,
                'product_name': product.sub_category
            }
        )
    else:
        # Optional: Notify farmer that customer returned via different product
        Message.objects.create(
            chatroom=chatroom,
            sender=request.user,
            text=_("[System Note] Customer returned to chat via product: '%(product_name)s'") % {
                'product_name': product.sub_category
            }
        )

    return redirect('chat:chatroom_detail', chatroom_id=chatroom.id)


# CHATROOM DETAIL (MESSAGING INTERFACE)
@login_required
def chatroom_detail(request, chatroom_id):
    chatroom = get_object_or_404(ChatRoom, id=chatroom_id)

    # Permission check
    if request.user != chatroom.farmer.user and request.user != chatroom.customer.user:
        return HttpResponseForbidden(_("You don't have permission to view this chat."))

    # If farmer rejected, show rejection page to customer
    if chatroom.farmer_rejected:
        if request.user == chatroom.customer.user:
            return render(request, 'chat/chat_rejected.html', {'chatroom': chatroom})
        # Farmer can still view even if they rejected

    # If not accepted yet, show pending view
    if not chatroom.farmer_accepted:
        is_farmer = request.user == chatroom.farmer.user
        messages_list = chatroom.message_set.all().order_by('timestamp')
        return render(request, 'chat/chatroom_pending.html', {
            'chatroom': chatroom,
            'messages': messages_list,
            'is_farmer': is_farmer
        })

    # Handle message POST
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            Message.objects.create(
                chatroom=chatroom,
                sender=request.user,
                text=text
            )
        return redirect('chat:chatroom_detail', chatroom_id=chatroom.id)

    # GET: Show chat messages
    messages_list = chatroom.message_set.all().order_by('timestamp')
    return render(request, 'chat/chatroom.html', {
        'chatroom': chatroom,
        'messages': messages_list
    })


#FARMER ACCEPTS CHAT
@login_required
def accept_chat(request, chatroom_id):
    chatroom = get_object_or_404(ChatRoom, id=chatroom_id)

    if request.user != chatroom.farmer.user:
        return HttpResponseForbidden(_("Only the farmer can accept this chat."))

    chatroom.farmer_accepted = True
    chatroom.farmer_rejected = False
    chatroom.save()

    # Auto-send welcome message from farmer
    Message.objects.create(
        chatroom=chatroom,
        sender=chatroom.farmer.user,
        text=_("I've accepted your chat request. How can I help you?")
    )

    return redirect('chat:chatroom_detail', chatroom_id=chatroom.id)


# FARMER REJECTS CHAT
# FARMER REJECTS CHAT — Notify Customer via Message
@login_required
def reject_chat(request, chatroom_id):
    chatroom = get_object_or_404(ChatRoom, id=chatroom_id)

    if request.user != chatroom.farmer.user:
        return HttpResponseForbidden(_("Only the farmer can reject this chat."))

    chatroom.farmer_accepted = False
    chatroom.farmer_rejected = True
    chatroom.save()

    # Notify customer with system message
    Message.objects.create(
        chatroom=chatroom,
        sender=chatroom.farmer.user,  # Farmer is sender
        text=_("[System Notification] Unfortunately, the farmer has rejected your chat request.")
    )

    # Optional: Add Django success message for farmer
    messages.success(request, _("Chat request from %(customer_username)s has been rejected.") % {
        'customer_username': chatroom.customer.user.username
    })

    return redirect('farmer-dashboard')