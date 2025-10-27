from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('start/<int:product_id>/', views.start_chat, name='start_chat'),
    path('room/<int:chatroom_id>/', views.chatroom_detail, name='chatroom_detail'),
    path('accept/<int:chatroom_id>/', views.accept_chat, name='accept_chat'),
    path('reject/<int:chatroom_id>/', views.reject_chat, name='reject_chat'),
    path('farmer/chats/', views.farmer_chats_view, name='farmer-chats'),
    path('customer/chats/', views.customer_chats_view, name='customer-chats'),
    path('confirm/<int:product_id>/', views.confirm_chat, name='confirm_chat'),
    # Bid URL removed ✅
]
