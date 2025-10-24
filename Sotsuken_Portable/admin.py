from django.contrib import admin
from .models import User, Group, GroupMember, SafetyStatus, SupportRequest

# 各モデルを管理サイトに登録
admin.site.register(User)
admin.site.register(Group)
admin.site.register(GroupMember)
admin.site.register(SafetyStatus)
admin.site.register(SupportRequest)
from django.contrib import admin

# Register your models here.
