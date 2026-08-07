from rest_framework import routers

from pricing.views import ServiceTypeViewSet

router = routers.DefaultRouter()
router.register('service-types', ServiceTypeViewSet, basename='service-type')

urlpatterns = router.urls
