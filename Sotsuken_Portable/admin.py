from django.contrib import admin
from .models import User, Group, GroupMember, SafetyStatus, SupportRequest, OfficialAlert , Shelter , Comment

# 各モデルを管理サイトに登録
admin.site.register(User)
admin.site.register(Group)
admin.site.register(GroupMember)
admin.site.register(SafetyStatus)
admin.site.register(SupportRequest)
admin.site.register(OfficialAlert)
admin.site.register(Shelter)
admin.site.register(Comment)
from django.contrib import admin

# Register your models here.
