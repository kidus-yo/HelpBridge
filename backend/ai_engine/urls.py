from django.urls import path
from .views import AIStatusView, AnswerQuestionView

urlpatterns = [
    path('status/', AIStatusView.as_view(), name='ai-status'),
    path('answer/', AnswerQuestionView.as_view(), name='ai-answer'),
]
