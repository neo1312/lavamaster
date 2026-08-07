from rest_framework import routers

from customers.views import CustomerViewSet

router = routers.DefaultRouter()
router.register('customers', CustomerViewSet, basename='customer')

urlpatterns = router.urls
