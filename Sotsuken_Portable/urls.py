# Sotuken_Portable/urls.py
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
    path('logout/', LogoutView.as_view(next_page='index'), name='logout'),

# ユーザー登録関連のURLパターン
    path('signup/', views.signup_view, name='signup'),
    path('signup/confirm/', views.signup_confirm_view, name='signup_confirm'),
    path('signup/done/', views.signup_done_view, name='signup_done'),

    path('safety/', views.safety_check_view, name='safety_check'),

    path('sos/', views.emergency_sos_view, name='emergency_sos'),
    path('sos/done/', views.emergency_sos_done_view, name='emergency_sos_done'),
    #path('map', views.map, name='map'),

    #path('emergency_common', views.emergency_common, name='emergency_common'),
]