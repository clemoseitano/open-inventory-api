from django.urls import path
from discovery.views import (
    ProcessImagesView,
    ProcessTextView,
    CheckResultView,
    RegistrationView,
    LoginView,
    ActivateAccountView,
    ResetPasswordView,
    ForgotPasswordView,
    ProductViewSet,
    SyncPushView,
    SyncPullView,
    DownloadDatabaseView,
)

product_list = ProductViewSet.as_view({"get": "list", "post": "create"})
product_detail = ProductViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
)

urlpatterns = [
    path("register/", RegistrationView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path(
        "activate/<str:uidb64>/<str:token>/",
        ActivateAccountView.as_view(),
        name="activate",
    ),
    path(
        "reset-password/<str:uidb64>/<str:token>/",
        ResetPasswordView.as_view(),
        name="reset-password",
    ),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("products/", product_list, name="product-list"),
    path("products/<int:pk>/", product_detail, name="product-detail"),
    path("process-images/", ProcessImagesView.as_view(), name="process-images"),
    path("process-text/", ProcessTextView.as_view(), name="process-text"),
    path(
        "inference-response/<str:task_id>",
        CheckResultView.as_view(),
        name="inference-response",
    ),
    # Sync Endpoints
    path("sync/push/", SyncPushView.as_view(), name="sync-push"),
    path("sync/pull/", SyncPullView.as_view(), name="sync-pull"),
    path("sync/download-db/", DownloadDatabaseView.as_view(), name="sync-download"),
]
