import uuid, json

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
# Create your models here.
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class UserManager(BaseUserManager):
    # create_userメソッドを修正
    def create_user(self, login_id, password=None, **extra_fields):
        if not login_id:
            raise ValueError('The Login ID field must be set')

        email = extra_fields.get('email')
        if email:
            extra_fields['email'] = self.normalize_email(email)

        # usernameにlogin_idをコピーしておく（任意だが互換性のために推奨）
        extra_fields.setdefault('username', login_id)

        user = self.model(login_id=login_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    # create_superuserメソッドを修正
    def create_superuser(self, login_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        # ... (is_staff, is_superuserのチェック) ...

        return self.create_user(login_id, password, **extra_fields)

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

    # 1. ログインIDフィールドを追加 (ユニーク制約付き)
    #    ユーザーが自分で決める or システムが自動生成する
    login_id = models.CharField(
        verbose_name='ログインID',
        max_length=50,
        unique=True,
        help_text='ログイン時に使用する一意のIDです。'
    )

    # 2. 氏名フィールド
    full_name = models.CharField(verbose_name='氏名', max_length=150, blank=True)

    # 3. emailフィールドのユニーク制約は外す（連絡先としてのみ使用）
    email = models.EmailField(verbose_name='メールアドレス', blank=True)

    # 4. ログインに使うフィールドを 'login_id' に設定
    USERNAME_FIELD = 'login_id'

    # 5. createsuperuserコマンドで聞かれる項目に 'email' を追加
    REQUIRED_FIELDS = ['email']

    # 6. usernameのユニーク制約は外したままでOK
    username = models.CharField(('username'), max_length=150, unique=False, blank=True)

    # --- カスタムマネージャーの修正 ---
    objects = UserManager()  # UserManagerは後述

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

    def __str__(self):
        return self.full_name or self.login_id

    class Meta:
        # DjangoにカスタムUserモデルを使用することを伝えます
        pass

    # ユーザー名としてメールアドレスを使用する場合
    # USERNAME_FIELD = 'email'
    # REQUIRED_FIELDS = ['username']

class Group(models.Model):
    """
    ユーザーをまとめるためのグループ（家族、地域コミュニティなど）を定義するモデル。
    """
    # 1. グループ名 (必須)
    name = models.CharField(
    verbose_name="グループ名",
    max_length=100
    )

    # 2. 作成者 (Userモデルへの外部キー/必須)
    creator = models.ForeignKey(
        'User',  # 'Sotsuken_Portable.User' ではなく 'User' で自己参照可能
        verbose_name="作成者",
        on_delete=models.SET_NULL,  # 作成者が削除されてもグループは残す
        null=True,
        related_name="created_groups"
    )

    # 3. 招待コード (ユニークな識別子。QRコードなどに利用)
    # UUIDFieldを使って、グローバルに一意な値を自動生成
    invitation_code = models.UUIDField(
        verbose_name="招待コード",
        default=uuid.uuid4,
        unique=True,
        editable=False,  # 管理サイトなどでの編集を不可にする
        help_text="QRコードやリンクに使用される一意のコード"
    )

    # 4. 作成日時
    created_at = models.DateTimeField(
        verbose_name="作成日時",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "グループ"
        verbose_name_plural = "グループ"

    def __str__(self):
        return self.name

class GroupMember(models.Model):
    """
    どのUserがどのGroupに所属しているかを管理する中間モデル。
    """
    ROLE_CHOICES = (
        ('member', 'メンバー'),
        ('admin', 'グループ管理者'),  # グループ内での権限
    )

    # 1. 所属グループ (Groupモデルへの外部キー/必須)
    group = models.ForeignKey(
        Group,
        verbose_name="グループ",
        on_delete=models.CASCADE,  # グループが削除されたらメンバー情報も削除
        related_name="memberships"
    )

    # 2. ユーザー (Userモデルへの外部キー/必須)
    member = models.ForeignKey(
        'User',
        verbose_name="メンバー",
        on_delete=models.CASCADE,  # ユーザーが削除されたらメンバー情報も削除
        related_name="group_memberships"
    )

    # 3. グループ内での役割/権限
    role = models.CharField(
        verbose_name="グループ内権限",
        max_length=20,
        choices=ROLE_CHOICES,
        default='member'
    )

    # 4. 参加日時
    joined_at = models.DateTimeField(
        verbose_name="参加日時",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "グループメンバー"
        verbose_name_plural = "グループメンバー"
        # 【ユニーク制約】一人のユーザーが一つのグループに二重で所属できないようにする
        unique_together = ('group', 'member')

    def __str__(self):
        return f"{self.member.username} in {self.group.name}"

class SafetyStatus(models.Model):
    """
    ユーザーの現在の安否状況と位置情報を記録するモデル。
    各ユーザーにつき、最新のレコード一つだけが存在する。
    """

    # 状態の選択肢
    STATUS_CHOICES = (
        ('safe', '無事'),
        ('help', '支援が必要'),
        ('unknown', '未確認'),
        ('checking', '確認中'),
    )

    # 1. ユーザー (Userモデルへの一対一リレーション/必須)
    # ユーザーごとに1レコードのみを持つため、OneToOneFieldを使用
    user = models.OneToOneField(
        'User',
        verbose_name="ユーザー",
        on_delete=models.CASCADE,  # ユーザーが削除されたら安否情報も削除
        primary_key=True,  # ここを主キーとして、必ず1レコードに制限
        related_name="safety_status_record"
    )

    # 2. 現在の安否状態
    status = models.CharField(
        verbose_name="安否状態",
        max_length=20,
        choices=STATUS_CHOICES,
        default='unknown'
    )

    # 3. 状況メッセージ
    message = models.TextField(
        verbose_name="状況メッセージ",
        blank=True,  # 入力は必須ではない
        null=True,
        help_text="状況を知らせる自由記述のメッセージ (例: ○○に避難中、食料あり)"
    )

    # 4. 最終更新日時
    last_updated = models.DateTimeField(
        verbose_name="最終更新日時",
        auto_now=True  # レコードが保存されるたびに自動で更新
    )

    # 5. 位置情報 (最終確認時の緯度・経度)
    latitude = models.FloatField(
        verbose_name="緯度",
        null=True,
        blank=True
    )
    longitude = models.FloatField(
        verbose_name="経度",
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "安否状況"
        verbose_name_plural = "安否状況"
        # ユーザーをキーにしているため、他に追加のユニーク制約は不要

    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"


class SupportRequest(models.Model):
    """
    ユーザーからの構造化された支援要請を記録するモデル。
    """

    # 支援要請カテゴリ
    CATEGORY_CHOICES = [
        ('food', '食料'),
        ('water', '飲料水'),
        ('medical', '医療/医薬品'),
        ('shelter', '避難場所/毛布'),
        ('other', 'その他'),
    ]

    # 優先度
    PRIORITY_CHOICES = [
        ('high', '高 (緊急)'),
        ('medium', '中'),
        ('low', '低'),
    ]

    # 対応状況
    STATUS_CHOICES = [
        ('pending', '未対応'),
        ('in_progress', '対応中'),
        ('resolved', '解決済'),
        ('cancelled', 'キャンセル'),
    ]

    # 1. 要請者 (Userモデルへの外部キー/必須)
    requester = models.ForeignKey(
        'User',
        verbose_name="要請者",
        on_delete=models.SET_NULL,  # ユーザー削除後も要請は履歴として残す
        null=True,
        related_name="support_requests"
    )

    # 2. カテゴリ (必須)
    category = models.CharField(
        verbose_name="要請カテゴリ",
        max_length=20,
        choices=CATEGORY_CHOICES
    )

    # 3. 優先度 (必須)
    priority = models.CharField(
        verbose_name="優先度",
        max_length=10,
        choices=PRIORITY_CHOICES
    )

    # 4. 詳細な状況/数量
    details = models.TextField(
        verbose_name="詳細な状況/数量",
        blank=True,
        null=True
    )

    # 5. 要請日時
    requested_at = models.DateTimeField(
        verbose_name="要請日時",
        auto_now_add=True
    )

    # 6. 対応状況
    status = models.CharField(
        verbose_name="対応状況",
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # 7. 要請時の位置情報
    latitude = models.FloatField(verbose_name="緯度", null=True, blank=True)
    longitude = models.FloatField(verbose_name="経度", null=True, blank=True)

    class Meta:
        verbose_name = "支援要請"
        verbose_name_plural = "支援要請一覧"
        ordering = ['-requested_at']  # 新しい要請を上位に表示

    def __str__(self):
        return f"要請({self.get_category_display()}) from {self.requester.username if self.requester else 'Deleted User'}"


class SOSReport(models.Model):
    """
    緊急SOS発信の履歴を記録するモデル。
    """

    # 対応状況 (共通化のためSupportRequestとほぼ同じ)
    STATUS_CHOICES = [
        ('pending', '未対応'),
        ('dispatched', '救助隊派遣済'),
        ('resolved', '解決済'),
        ('false_alarm', '誤報/キャンセル'),
    ]

    # 1. 発信者 (Userモデルへの外部キー/必須)
    reporter = models.ForeignKey(
        'User',
        verbose_name="発信者",
        on_delete=models.SET_NULL,
        null=True,
        related_name="sos_reports"
    )

    # 2. 発信日時
    reported_at = models.DateTimeField(
        verbose_name="発信日時",
        auto_now_add=True
    )

    # 3. 発信時の位置情報 (必須)
    latitude = models.FloatField(verbose_name="緯度")
    longitude = models.FloatField(verbose_name="経度")

    # 4. 状況 (自動メッセージなどがあれば記録)
    situation_notes = models.TextField(
        verbose_name="状況メモ",
        blank=True,
        null=True,
        help_text="発信時に自動送信された情報や現場の状況メモ"
    )

    # 5. 対応状況
    status = models.CharField(
        verbose_name="対応状況",
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    class Meta:
        verbose_name = "SOSレポート"
        verbose_name_plural = "SOSレポート一覧"
        ordering = ['-reported_at']

    def __str__(self):
        return f"SOS Report ({self.get_status_display()}) at {self.reported_at.strftime('%Y-%m-%d %H:%M')}"


class Message(models.Model):
    """
    チャット（グループチャット、ダイレクトメッセージ）のメッセージを記録するモデル。
    """

    # 宛先タイプ
    DESTINATION_TYPE_CHOICES = [
        ('group', 'グループチャット'),
        ('dm', 'ダイレクトメッセージ'),
        ('community', 'コミュニティ投稿'),  # コミュニティ投稿をメッセージ形式で扱う場合
    ]

    # 1. 送信者 (Userモデルへの外部キー/必須)
    sender = models.ForeignKey(
        'User',
        verbose_name="送信者",
        on_delete=models.SET_NULL,  # ユーザー削除後もメッセージは残す
        null=True,
        related_name="sent_messages"
    )

    # 2. メッセージの内容 (必須)
    content = models.TextField(
        verbose_name="メッセージ内容"
    )

    # 3. 送信日時 (必須)
    timestamp = models.DateTimeField(
        verbose_name="送信日時",
        auto_now_add=True
    )

    # 4. 宛先グループ (Groupモデルへの外部キー/グループチャットの場合)
    # null=True, blank=True にすることで、DMや全体通知にも使える
    group = models.ForeignKey(
        'Group',
        verbose_name="宛先グループ",
        on_delete=models.CASCADE,  # グループ削除でメッセージも削除
        null=True,
        blank=True,
        related_name="group_messages"
    )

    # 5. 宛先ユーザー (DMの場合)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Userモデルを安全に参照
        verbose_name="宛先ユーザー",
        on_delete=models.CASCADE,
        null=True,  # グループチャットの場合はNULLになるので必須
        blank=True,
        related_name="received_messages"
    )

    # 5. メッセージタイプ
    #destination_type = models.CharField(
        #verbose_name="宛先タイプ",
        #max_length=20,
        #choices=DESTINATION_TYPE_CHOICES,
        #default='group'
    #)

    # 6. 既読フラグ (簡易的な実装)
    # 複雑な既読管理（誰が読んだか）は別の中間テーブル (ReadReceipt) を使いますが、
    # 簡易的に「宛先全体で既読か否か」のフラグを持たせます。
    is_read = models.BooleanField(
        verbose_name="既読",
        default=False
    )

    class Meta:
        verbose_name = "メッセージ"
        verbose_name_plural = "メッセージ一覧"
        ordering = ['timestamp']  # 時系列順に並べる

    def __str__(self):
        return f"Msg from {self.sender.username if self.sender else 'Deleted'} to {self.group.name if self.group else 'DM/Other'}"


class CommunityPost(models.Model):
    """
    ユーザーコミュニティ（情報掲示板）の投稿を記録するモデル。
    """

    # 投稿ステータス（管理サイトでの確認・承認フローを想定）
    STATUS_CHOICES = [
        ('published', '公開済'),
        ('draft', '下書き'),
        ('review', '管理者確認中'),
        ('hidden', '非表示'),
    ]

    # 1. 投稿者 (Userモデルへの外部キー/必須)
    author = models.ForeignKey(
        'User',
        verbose_name="投稿者",
        on_delete=models.SET_NULL,  # ユーザー削除後も投稿は残す
        null=True,
        related_name="community_posts"
    )

    # 2. タイトル (必須)
    title = models.CharField(
        verbose_name="タイトル",
        max_length=200
    )

    # 3. 内容 (必須)
    content = models.TextField(
        verbose_name="内容"
    )

    # 4. 投稿日時 (必須)
    posted_at = models.DateTimeField(
        verbose_name="投稿日時",
        auto_now_add=True
    )

    # 5. 地域カテゴリ/タグ (オプション: 情報の絞り込み用)
    region_tag = models.CharField(
        verbose_name="地域タグ",
        max_length=50,
        blank=True,
        null=True,
        help_text="例: 〇〇地区、避難所A"
    )

    # 6. ステータス
    status = models.CharField(
        verbose_name="公開ステータス",
        max_length=20,
        choices=STATUS_CHOICES,
        default='published'  # 基本的に投稿と同時に公開
    )

    # 7. 最終更新日時
    updated_at = models.DateTimeField(
        verbose_name="最終更新日時",
        auto_now=True
    )

    class Meta:
        verbose_name = "コミュニティ投稿"
        verbose_name_plural = "コミュニティ投稿一覧"
        ordering = ['-posted_at']  # 新しい投稿を上位に表示

    def __str__(self):
        return self.title


class Comment(models.Model):
    """
    コミュニティ投稿へのリプライ（コメント）を記録するモデル。
    """
    # 1. どの投稿へのリプライか (必須)
    post = models.ForeignKey(
        CommunityPost,
        verbose_name="対象の投稿",
        on_delete=models.CASCADE,  # 親の投稿が削除されたら、リプライも一緒に削除
        related_name='comments'  # post.comments のように逆参照できるようになる
    )

    # 2. リプライの投稿者 (必須)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # カスタムUserモデルを安全に参照
        verbose_name="投稿者",
        on_delete=models.CASCADE
    )

    # 3. リプライの内容 (必須)
    text = models.TextField(verbose_name="コメント内容")

    # 4. 投稿日時 (必須)
    created_at = models.DateTimeField(verbose_name="投稿日時", auto_now_add=True)

    class Meta:
        verbose_name = "コメント"
        verbose_name_plural = "コメント一覧"
        ordering = ['created_at']  # 古い順に表示

    def __str__(self):
        return f'{self.author.username}: {self.text[:20]}'


class Shelter(models.Model):
    """
    避難所の情報（場所、キャパシティ、空き状況）を管理するモデル。
    """

    # 開設状況の選択肢
    OPENING_STATUS_CHOICES = [
        ('open', '開設中'),
        ('closed', '閉鎖'),
        ('preparating', '開設準備中'),
    ]

    # 1. 避難所名 (必須)
    name = models.CharField(
        verbose_name="避難所名",
        max_length=200,
        unique=True  # 避難所名は一意であると仮定
    )

    # 2. 住所 (必須)
    address = models.CharField(
        verbose_name="住所",
        max_length=255
    )

    # 3. 位置情報 (緯度・経度/必須)
    latitude = models.FloatField(verbose_name="緯度")
    longitude = models.FloatField(verbose_name="経度")

    # 4. 最大収容人数 (必須)
    max_capacity = models.IntegerField(
        verbose_name="最大収容人数"
    )

    # 5. 現在の収容人数 (変動データ)
    current_occupancy = models.IntegerField(
        verbose_name="現在の収容人数",
        default=0
    )

    # 6. 開設状況
    opening_status = models.CharField(
        verbose_name="開設状況",
        max_length=20,
        choices=OPENING_STATUS_CHOICES,
        default='open'
    )

    # 7. ペット可否
    is_pet_friendly = models.BooleanField(
        verbose_name="ペット可",
        default=False
    )

    # 8. 最終情報更新日時（収容人数が最後に更新された日時）
    last_updated = models.DateTimeField(
        verbose_name="最終更新日時",
        auto_now=True
    )

    class Meta:
        verbose_name = "避難所"
        verbose_name_plural = "避難所一覧"

    def __str__(self):
        return self.name


from django.db import models

class RPiData(models.Model):
    """
    Raspberry Piなどの現場デバイスから送られる構造化データを記録するモデル。
    """

    # データの種類
    DATA_TYPE_CHOICES = [
        ('shelter_checkin', '避難所受付データ'),
        ('food_distribution', '炊き出し確認データ'),
        ('environmental', '環境センサーデータ'),  # 将来的な拡張を想定
        ('other', 'その他'),
    ]

    # 1. データタイプ (必須)
    data_type = models.CharField(
        verbose_name="データタイプ",
        max_length=50,
        choices=DATA_TYPE_CHOICES
    )

    # 2. デバイスID (送信元を一意に識別)
    device_id = models.CharField(
        verbose_name="RPiデバイスID",
        max_length=100,
        help_text="データ送信元のRaspberry Piや端末の識別子"
    )

    # 3. 構造化データ本体 (JSON形式で格納)
    # MySQLでは、JSONFieldを使うことで辞書形式のデータをそのまま格納・検索できる
    payload = models.JSONField(
        verbose_name="構造化データ (JSON)",
        help_text="データ本体。例: {'user_id': 'U001', 'checkin_time': '...'}"
    )

    # 4. 送信日時
    received_at = models.DateTimeField(
        verbose_name="受信日時",
        auto_now_add=True
    )

    # 5. データ取得時の位置情報
    latitude = models.FloatField(verbose_name="緯度", null=True, blank=True)
    longitude = models.FloatField(verbose_name="経度", null=True, blank=True)

    # 6. 処理フラグ (データがサーバーで処理済みかを示す)
    is_processed = models.BooleanField(
        verbose_name="処理済",
        default=False,
        help_text="このデータが分析や集計で利用されたかどうか"
    )

    class Meta:
        verbose_name = "RPiデータ"
        verbose_name_plural = "RPiデータ一覧"
        ordering = ['-received_at']

    def __str__(self):
        return f"RPi Data: {self.get_data_type_display()} from {self.device_id} at {self.received_at.strftime('%Y-%m-%d %H:%M')}"

class OfficialAlert(models.Model):
    """
    行政などからの公式な緊急情報を管理するモデル。
    """
    SEVERITY_CHOICES = [
        ('info', '情報'),
        ('warning', '警報'),
        ('emergency', '緊急'),
    ]

    title = models.CharField(verbose_name="タイトル", max_length=200)
    content = models.TextField(verbose_name="内容")
    severity = models.CharField(
        verbose_name="重要度",
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='info'
    )
    published_at = models.DateTimeField(verbose_name="発表日時", auto_now_add=True)

    class Meta:
        verbose_name = "公式緊急情報"
        verbose_name_plural = "公式緊急情報一覧"
        ordering = ['-published_at']  # 新しい情報が上に来るように

    def __str__(self):
        return self.title
