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
    # ★修正 (SupportRequest.id は UUID)
    path('support-request/<uuid:pk>/resolve/', views.resolve_support_request_view, name='resolve_support_request'),

    path('sos/', views.emergency_sos_view, name='emergency_sos'),
    path('sos/done/', views.emergency_sos_done_view, name='emergency_sos_done'),

    # --- マップ・情報 ---
    path('map/', views.map_view, name='map'),
    path('emergency/', views.emergency_info_view, name='emergency_info'),

    # --- メニュー ---
    path('menu/', views.user_menu_view, name='user_menu'),
    path('admin-panel/', views.admin_menu_view, name='admin_menu'),

    # --- 管理機能 (User.id は UUID) ---
    path('management/users/', views.user_management_view, name='user_management'),
    # ★修正
    path('management/users/<uuid:user_id>/delete/', views.user_delete_view, name='user_delete'),
    # ★修正
    path('management/users/<uuid:user_id>/change-role/', views.user_change_role_view, name='user_change_role'),

    # --- 避難所管理 (Shelter.id / management_id) ---
    path('management/shelters/', views.shelter_management_view, name='shelter_management'),
    # ShelterモデルもUUIDModelを継承させるなら uuid に変更。
    # ただし management_id (文字列ID) をキーにしているなら str のままでOK。
    # 今回は統一のためにモデル側でUUID化するならここも uuid にしても良いが、
    # 既存コードが management_id (str) を使っているならそのままでOK。
    # ここでは元のコードの意図（手入力ID）を尊重して str のままにします。
    path('management/shelters/<str:management_id>/edit/', views.shelter_edit_view, name='shelter_edit'),
    path('management/shelters/<str:management_id>/delete/', views.shelter_delete_view, name='shelter_delete'),

    # --- SOSレポート管理 (SOSReport.id は UUID) ---
    path('management/sos-reports/', views.sos_report_list_view, name='sos_report_list'),
    # ★修正
    path('management/sos-reports/<uuid:report_id>/update-status/', views.sos_report_update_status_view,
         name='sos_report_update_status'),
    # ★修正
    path('management/sos-reports/<uuid:report_id>/delete/', views.sos_report_delete_view, name='sos_report_delete'),

    path('management/sos-reports/export-csv/', views.sos_report_export_csv_view, name='sos_report_export_csv'),

    # --- 物資管理 ---
    path('management/distribution/add/', views.add_distribution_info_view, name='add_distribution_info'),

    # --- コミュニティ (CommunityPost.id / Comment.id は UUID) ---
    path('community/', views.CommunityPostListView.as_view(), name='community_list'),
    # ★修正
    path('community/post/<uuid:pk>/', views.CommunityPostDetailView.as_view(), name='community_detail'),
    # ★修正
    path('community/post/<uuid:pk>/delete/', views.CommunityPostDeleteView.as_view(), name='community_delete'),
    # ★修正
    path('community/comment/<uuid:pk>/delete/', views.CommentDeleteView.as_view(), name='comment_delete'),
    path('community/new/', views.CommunityPostCreateView.as_view(), name='community_create'),

    # --- チャット (Group.id / User.id は UUID) ---
    path('chat/', views.chat_group_list_view, name='chat_group_list'),
    # ★修正: group_id が 'all'(文字列) の場合もあるため、uuid ではなく str に変更するのが安全です
    # uuidコンバータは厳密にUUID形式しか受け付けず、'all' が来ると404になります。
    # なのでここは <str:group_id> に変更します。
    path('chat/group/<str:group_id>/', views.chat_room_view, name='chat_room'),

    # --- グループ管理 (Group.id は UUID) ---
    path('groups/', views.GroupListView.as_view(), name='group_list'),
    path('groups/new/', views.GroupCreateView.as_view(), name='group_create'),
    # ★修正
    path('groups/<uuid:pk>/', views.GroupDetailView.as_view(), name='group_detail'),
    # ★修正
    path('groups/<uuid:pk>/delete/', views.GroupDeleteView.as_view(), name='group_delete'),
    # ★修正
    path('groups/<uuid:pk>/leave/', views.GroupLeaveView.as_view(), name='group_leave'),

    # --- DM (User.id は UUID) ---
    path('chat/dm/', views.dm_user_list_view, name='dm_user_list'),
    # ★修正
    path('chat/dm/<uuid:user_id>/', views.dm_room_view, name='dm_room'),
    # ★修正
    path('chat/connect/<uuid:user_id>/', views.send_connection_request_view, name='send_connection_request'),
    # ★修正
    path('chat/approve/<uuid:user_id>/', views.approve_connection_request_view, name='approve_connection_request'),

    # --- 設定 ---
    path('settings/', views.settings_view, name='settings'),
    path('settings/profile/', views.user_profile_edit, name='user_profile_edit'),

    # --- QRコード ---
    path('qr/my-status/', views.my_status_qr_view, name='my_status_qr'),
    # ★修正
    path('groups/<uuid:group_id>/invite-qr/', views.group_invite_qr_view, name='group_invite_qr'),
    path('qr/scan/', views.qr_scan_view, name='qr_scanner'),
    # invitation_code は元々UUIDFieldだったのでそのままでOK
    path('groups/join-by-code/<uuid:invitation_code>/', views.join_group_by_code_view, name='group_join_by_code'),
    path('qr/user-id/', views.user_id_qr_view, name='user_id_qr'),

    # --- その他 ---
    path('manuals/', views.manual_list, name='manual_list'),
    path('management/rpi-checkin-logs/', views.rpi_checkin_log_view, name='rpi_checkin_logs'),
    path('management/distribution-logs/', views.distribution_log_view, name='distribution_logs'),
    path('ajax/get-nearby-alerts/', views.get_nearby_alerts_view, name='get_nearby_alerts'),
    # ★修正
    path('safety/history/<uuid:user_id>/', views.safety_history_view, name='safety_history'),
]