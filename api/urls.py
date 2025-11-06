from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('shelter-checkin/', views.shelter_checkin_api, name='shelter_checkin'),

    path('check-distribution/', views.check_distribution_api, name='check_distribution'),

    path('distribution-items/', views.distribution_item_list_api, name='distribution_item_list'),

    path('field-report/', views.field_report_api, name='field_report'),

    path('shelters/', views.shelter_list_api, name='shelter_list'),


]