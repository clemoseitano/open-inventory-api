from django.contrib import admin
from django.urls import path, include
from graphene_django.views import GraphQLView

from discovery.schemas import schema

urlpatterns = [
    path("admin/", admin.site.urls),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    path("api/", include("discovery.urls")),
    path("graphql", GraphQLView.as_view(graphiql=True, schema=schema)),
]
