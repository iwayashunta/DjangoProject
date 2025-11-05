from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('shelter-checkin/', views.shelter_checkin_api, name='shelter_checkin'),
]