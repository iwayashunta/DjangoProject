# Sotuken_Portable/urls.py

from django.urls import path
from . import views

app_name = 'Sotsuken_Portable' # アプリケーションの名前空間を定義

urlpatterns = [
    path('', views.index, name='index'), # ルートURL ('/') にアクセスしたらviews.indexを呼び出す
]