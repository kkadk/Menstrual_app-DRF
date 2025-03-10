from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserProfileViewSet,
    MenstrualCycleViewSet,
    MenstrualCycleHistoryViewSet,
    FlowIntensityLogViewSet,
    PredictionViewSet,
    RegisterUserView,
    VerifyEmailView
)

router = DefaultRouter()
router.register('user-profiles', UserProfileViewSet, basename='user-profile')
router.register('menstrual-cycles', MenstrualCycleViewSet, basename='menstrual-cycle')
router.register('menstrual-cycle-history', MenstrualCycleHistoryViewSet, basename='menstrual-cycle-history')
router.register('flow-intensity-logs', FlowIntensityLogViewSet, basename='flow-intensity-log')
router.register('predictions', PredictionViewSet, basename='prediction')

urlpatterns = [
    path('register/', RegisterUserView.as_view(), name='register'),
    path('verify-email/<str:token>/', VerifyEmailView.as_view(), name='verify-email'),
    path('', include(router.urls)),  # Register all routes from the router
]