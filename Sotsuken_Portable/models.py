from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class User(AbstractUser):
    # ロール定義
    ROLE_CHOICES = (
        ('general', '一般ユーザー'),
        ('admin', 'システム管理者'),
        ('rescuer', '救助チーム')
    )

    # 安否状況定義
    STATUS_CHOICES = (
        ('safe', '無事'),
        ('help', '要支援'),
        ('unknown', '未確認'),
    )

    # カスタムフィールド
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='general')
    safety_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')

    # オプション：最終位置情報
    last_known_latitude = models.FloatField(null=True, blank=True)
    last_known_longitude = models.FloatField(null=True, blank=True)

    # groups フィールドにユニークな related_name を追加
    groups = models.ManyToManyField(
        Group,
        verbose_name=('groups'),
        blank=True,
        help_text=(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="sotsuken_user_set",  # ユニークな名前に変更
        related_query_name="user",
    )

    # user_permissions フィールドにユニークな related_name を追加
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=('user permissions'),
        blank=True,
        help_text=('Specific permissions for this user.'),
        related_name="sotsuken_user_permissions_set",  # ユニークな名前に変更
        related_query_name="user",
    )

    class Meta:
        # DjangoにカスタムUserモデルを使用することを伝えます
        pass

    # ユーザー名としてメールアドレスを使用する場合
    # USERNAME_FIELD = 'email'
    # REQUIRED_FIELDS = ['username']