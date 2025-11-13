from django.contrib import admin
from .models import User, Group, GroupMember, SafetyStatus, SupportRequest, OfficialAlert, Shelter, Comment, \
    DistributionItem, DistributionRecord, CommunityPost, Manual

# 各モデルを管理サイトに登録
admin.site.register(User)
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

