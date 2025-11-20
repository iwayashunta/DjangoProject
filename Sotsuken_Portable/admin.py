from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Group, GroupMember, SafetyStatus, SupportRequest, OfficialAlert, Shelter, Comment, \
    DistributionItem, DistributionRecord, CommunityPost, Manual

class CustomUserAdmin(UserAdmin):
    # 管理サイトの一覧画面に表示する項目
    list_display = ('username', 'full_name', 'email', 'role', 'safety_status', 'is_staff')
    # 管理サイトの編集画面のフィールド構成
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('full_name', 'email')}),
        ('災害用カスタム情報', {'fields': ('role', 'safety_status', 'last_known_latitude', 'last_known_longitude')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    # ユーザー作成時に必須とするフィールド
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password', 'password2', 'full_name', 'email', 'role'), # パスワード確認欄を追加
        }),
    )
    # 検索対象のフィールド
    search_fields = ('username', 'full_name')
    # 並び替えの基準
    ordering = ('username',)


# 各モデルを管理サイトに登録
admin.site.register(User, CustomUserAdmin)
admin.site.register(Group)
admin.site.register(GroupMember)
admin.site.register(SafetyStatus)
admin.site.register(SupportRequest)
admin.site.register(OfficialAlert)
admin.site.register(Shelter)
admin.site.register(Comment)
admin.site.register(DistributionItem)
admin.site.register(DistributionRecord)
admin.site.register(CommunityPost)
admin.site.register(Manual)

