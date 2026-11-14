from django.urls import path

from knowledge.views import (
    DocumentDetailView,
    DocumentProcessView,
    DocumentUploadView,
    KnowledgeSearchView,
)

urlpatterns = [
    path("documents/", DocumentUploadView.as_view(), name="document-upload"),
    path("documents/<uuid:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("documents/<uuid:pk>/process/", DocumentProcessView.as_view(), name="document-process"),
    path("knowledge/search/", KnowledgeSearchView.as_view(), name="knowledge-search"),
]
