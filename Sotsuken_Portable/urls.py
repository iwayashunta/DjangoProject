# Sotsuken_Portable/urls.py
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from . import views

app_name = 'Sotsuken_Portable' # アプリケーションの名前空間を定義

urlpatterns = [

    path('', views.index, name='index'), # ルートURL ('/') にアクセスしたらviews.indexを呼び出す

# ログイン
    path('login/',
         LoginView.as_view(
             template_name='login.html' # このパスが正しいことを確認
         ),
         name='login'),

    # ログアウト
    path('logout/', LogoutView.as_view(next_page='Sotsuken_Portable:index'), name='logout'),

# ユーザー登録関連のURLパターン
    path('signup/', views.signup_view, name='signup'),
    path('signup/confirm/', views.signup_confirm_view, name='signup_confirm'),
    path('signup/done/', views.signup_done_view, name='signup_done'),

    path('safety/', views.safety_check_view, name='safety_check'),

    path('sos/', views.emergency_sos_view, name='emergency_sos'),
    path('sos/done/', views.emergency_sos_done_view, name='emergency_sos_done'),
    path('map/', views.map_view, name='map'),

    path('emergency/', views.emergency_info_view, name='emergency_common'),

    path('menu/', views.user_menu_view, name='user_menu'),

    path('admin-panel/', views.admin_menu_view, name='admin_menu'),

    path('management/users/', views.user_management_view, name='user_management'),

    path('management/users/<int:user_id>/delete/', views.user_delete_view, name='user_delete'),

    path('management/users/<int:user_id>/change-role/', views.user_change_role_view, name='user_change_role'),

    path('community/', views.CommunityPostListView.as_view(), name='community_list'),
    path('community/post/<int:pk>/', views.CommunityPostDetailView.as_view(), name='community_detail'),

    path('community/post/<int:pk>/delete/', views.CommunityPostDeleteView.as_view(), name='community_delete'),

    path('community/comment/<int:pk>/delete/', views.CommentDeleteView.as_view(), name='comment_delete'),
    path('community/new/', views.CommunityPostCreateView.as_view(), name='community_create'),

    path('chat/', views.chat_group_list_view, name='chat_group_list'),
    path('chat/group/<int:group_id>/', views.chat_room_view, name='chat_room'),

    path('groups/', views.GroupListView.as_view(), name='group_list'),
    path('groups/new/', views.GroupCreateView.as_view(), name='group_create'),
    path('groups/<int:pk>/', views.GroupDetailView.as_view(), name='group_detail'),

    path('groups/<int:pk>/delete/', views.GroupDeleteView.as_view(), name='group_delete'),

    path('groups/<int:pk>/leave/', views.GroupLeaveView.as_view(), name='group_leave'),

    path('chat/dm/', views.dm_user_list_view, name='dm_user_list'),
    path('chat/dm/<int:user_id>/', views.dm_room_view, name='dm_room'),

    # 設定画面のURLを追加
    path('settings/', views.settings_view, name='settings'),

    # ユーザー情報編集画面のURLを追加
    path('settings/profile/', views.user_profile_edit, name='user_profile_edit'),

    # 1. 自分の安否情報QRコードを表示するページ
    path('qr/my-status/', views.my_status_qr_view, name='my_status_qr'),

    # 2. グループ招待用のQRコードを表示するページ (グループ詳細ページなどからリンク)
    path('groups/<int:group_id>/invite-qr/', views.group_invite_qr_view, name='group_invite_qr'),

    # 3. QRコードを読み取るためのスキャナーページ
    path('qr/scan/', views.qr_scan_view, name='qr_scanner'),

    path('groups/join-by-code/<uuid:invitation_code>/', views.join_group_by_code_view, name='group_join_by_code'),


]