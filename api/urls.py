from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('shelter-checkin/', views.shelter_checkin_api, name='shelter_checkin'),

    path('check-distribution/', views.check_distribution_api, name='check_distribution'),

    path('distribution-items/', views.distribution_item_list_api, name='distribution_item_list'),

    path('field-report/', views.field_report_api, name='field_report'),

    path('shelters/', views.shelter_list_api, name='shelter_list'),

    path('get-user-groups/', views.get_user_groups_api, name='get_user_groups'),

    path('post-group-message/', views.post_group_message_api, name='post_group_message'),

    path('groups/<str:group_id>/messages/', views.get_group_messages_api, name='get_group_messages_api'),

    path('shelter-checkin-sync/', views.shelter_checkin_sync_api, name='shelter_checkin_sync_api'),

    path('register-field-user/', views.register_field_user_api, name='register_field_user_api'),

    path('post-dm-message/', views.post_dm_message_api, name='post_dm_message_api'),

    path( 'get-all-users/', views.get_all_users_api, name='get_all_users_api' ),

    path('delete-message/', views.delete_message_api, name='delete_message_api'),


]