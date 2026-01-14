from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from . import views

app_name = 'Sotsuken_Portable'

urlpatterns = [
    # --- 基本 ---
    path('', views.index, name='index'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='Sotsuken_Portable:index'), name='logout'),

    # --- ユーザー登録 ---
    path('signup/', views.signup_view, name='signup'),
    path('signup/confirm/', views.signup_confirm_view, name='signup_confirm'),
    path('signup/done/', views.signup_done_view, name='signup_done'),

    # --- 安否・SOS ---
    path('safety/', views.safety_check_view, name='safety_check'),
    path('support-request/<uuid:pk>/resolve/', views.resolve_support_request_view, name='resolve_support_request'),

    path('sos/', views.emergency_sos_view, name='emergency_sos'),
    path('sos/done/', views.emergency_sos_done_view, name='emergency_sos_done'),
    
    # ★★★ ワンクリックSOS用のURLを追加 ★★★
    path('sos/quick-alert/<uuid:user_id>/<str:token>/', views.quick_sos_view, name='quick_sos'),

    # --- マップ・情報 ---
    path('map/', views.map_view, name='map'),
    path('emergency/', views.emergency_info_view, name='emergency_info'),

    # --- メニュー ---
    path('menu/', views.user_menu_view, name='user_menu'),
    path('admin-panel/', views.admin_menu_view, name='admin_menu'),

    # --- 管理機能 ---
    path('management/users/', views.user_management_view, name='user_management'),
    path('management/users/<uuid:user_id>/delete/', views.user_delete_view, name='user_delete'),
    path('management/users/<uuid:user_id>/change-role/', views.user_change_role_view, name='user_change_role'),

    # --- 避難所管理 ---
    path('management/shelters/', views.shelter_management_view, name='shelter_management'),
    path('management/shelters/<str:management_id>/edit/', views.shelter_edit_view, name='shelter_edit'),
    path('management/shelters/<str:management_id>/delete/', views.shelter_delete_view, name='shelter_delete'),

    # --- SOSレポート管理 ---
    path('management/sos-reports/', views.sos_report_list_view, name='sos_report_list'),
    path('management/sos-reports/<uuid:report_id>/update-status/', views.sos_report_update_status_view, name='sos_report_update_status'),
    path('management/sos-reports/<uuid:report_id>/delete/', views.sos_report_delete_view, name='sos_report_delete'),
    path('management/sos-reports/export-csv/', views.sos_report_export_csv_view, name='sos_report_export_csv'),

    # --- 物資管理 ---
    path('management/distribution/add/', views.add_distribution_info_view, name='add_distribution_info'),

    # --- コミュニティ ---
    path('community/', views.CommunityPostListView.as_view(), name='community_list'),
    path('community/post/<uuid:pk>/', views.CommunityPostDetailView.as_view(), name='community_detail'),
    path('community/post/<uuid:pk>/delete/', views.CommunityPostDeleteView.as_view(), name='community_delete'),
    path('community/comment/<uuid:pk>/delete/', views.CommentDeleteView.as_view(), name='comment_delete'),
    path('community/new/', views.CommunityPostCreateView.as_view(), name='community_create'),

    # --- チャット ---
    path('chat/', views.chat_group_list_view, name='chat_group_list'),
    path('chat/group/<str:group_id>/', views.chat_room_view, name='chat_room'),

    # --- グループ管理 ---
    path('groups/', views.GroupListView.as_view(), name='group_list'),
    path('groups/new/', views.GroupCreateView.as_view(), name='group_create'),
    path('groups/<uuid:pk>/', views.GroupDetailView.as_view(), name='group_detail'),
    path('groups/<uuid:pk>/delete/', views.GroupDeleteView.as_view(), name='group_delete'),
    path('groups/<uuid:pk>/leave/', views.GroupLeaveView.as_view(), name='group_leave'),

    # --- DM ---
    path('chat/dm/', views.dm_user_list_view, name='dm_user_list'),
    path('chat/dm/<uuid:user_id>/', views.dm_room_view, name='dm_room'),
    path('chat/connect/<uuid:user_id>/', views.send_connection_request_view, name='send_connection_request'),
    path('chat/approve/<uuid:user_id>/', views.approve_connection_request_view, name='approve_connection_request'),

    # --- 設定 ---
    path('settings/', views.settings_view, name='settings'),
    path('settings/profile/', views.user_profile_edit, name='user_profile_edit'),

    # --- QRコード ---
    path('qr/my-status/', views.my_status_qr_view, name='my_status_qr'),
    path('groups/<uuid:group_id>/invite-qr/', views.group_invite_qr_view, name='group_invite_qr'),
    path('qr/scan/', views.qr_scan_view, name='qr_scanner'),
    path('groups/join-by-code/<uuid:invitation_code>/', views.join_group_by_code_view, name='group_join_by_code'),
    path('qr/user-id/', views.user_id_qr_view, name='user_id_qr'),

    # --- その他 ---
    path('manuals/', views.manual_list, name='manual_list'),
    path('management/rpi-checkin-logs/', views.rpi_checkin_log_view, name='rpi_checkin_logs'),
    path('management/distribution-logs/', views.distribution_log_view, name='distribution_logs'),
    path('ajax/get-nearby-alerts/', views.get_nearby_alerts_view, name='get_nearby_alerts'),
    path('safety/history/<uuid:user_id>/', views.safety_history_view, name='safety_history'),

    # --- 物資マスタ管理 ---
    path('management/items/', views.DistributionItemListView.as_view(), name='distribution_item_list'),
    path('management/items/add/', views.DistributionItemCreateView.as_view(), name='distribution_item_add'),
    path('management/items/<uuid:pk>/edit/', views.DistributionItemUpdateView.as_view(), name='distribution_item_edit'),
    path('management/items/<uuid:pk>/delete/', views.DistributionItemDeleteView.as_view(), name='distribution_item_delete'),

    # --- 公式アナウンス管理 ---
    path('management/alerts/', views.OfficialAlertListView.as_view(), name='official_alert_list'),
    path('management/alerts/add/', views.OfficialAlertCreateView.as_view(), name='official_alert_add'),
    path('management/alerts/<uuid:pk>/edit/', views.OfficialAlertUpdateView.as_view(), name='official_alert_edit'),
    path('management/alerts/<uuid:pk>/delete/', views.OfficialAlertDeleteView.as_view(), name='official_alert_delete'),
]
