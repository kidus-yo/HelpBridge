from django.urls import path
from .views import (
    ChatSessionListCreateView,
    ChatSessionDetailView,
    MessageListCreateView,
)

urlpatterns = [
    path('sessions/', ChatSessionListCreateView.as_views() if hasattr(ChatSessionListCreateView, 'as_views') else ChatSessionListCreateView.as_view(), name='chat-session-list-create'),
    path('sessions/<uuid:session_id>/', ChatSessionDetailView.as_view(), name='chat-session-detail'),
    path('sessions/<uuid:session_id>/messages/', MessageListCreateView.as_view(), name='chat-message-list-create'),
]

