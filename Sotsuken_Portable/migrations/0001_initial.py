import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='DistributionItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='物資名')),
                ('description', models.TextField(blank=True, null=True, verbose_name='説明')),
            ],
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='グループ名')),
                ('invitation_code', models.UUIDField(default=uuid.uuid4, editable=False, help_text='QRコードやリンクに使用される一意のコード', unique=True, verbose_name='招待コード')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
            ],
            options={
                'verbose_name': 'グループ',
                'verbose_name_plural': 'グループ',
            },
        ),
        migrations.CreateModel(
            name='JmaArea',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='地域名')),
                ('code', models.CharField(max_length=20, unique=True, verbose_name='エリアコード')),
                ('latitude', models.FloatField(verbose_name='代表緯度')),
                ('longitude', models.FloatField(verbose_name='代表経度')),
            ],
        ),
        migrations.CreateModel(
            name='Manual',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='タイトル')),
                ('pdf_file', models.FileField(upload_to='manuals/', verbose_name='PDFファイル')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
            ],
            options={
                'verbose_name': 'マニュアル',
                'verbose_name_plural': 'マニュアル',
            },
        ),
        migrations.CreateModel(
            name='RPiData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_type', models.CharField(choices=[('shelter_checkin', '避難所受付データ'), ('food_distribution', '炊き出し確認データ'), ('environmental', '環境センサーデータ'), ('other', 'その他')], max_length=50, verbose_name='データタイプ')),
                ('device_id', models.CharField(help_text='データ送信元のRaspberry Piや端末の識別子', max_length=100, verbose_name='RPiデバイスID')),
                ('payload', models.JSONField(help_text="データ本体。例: {'user_id': 'U001', 'checkin_time': '...'}", verbose_name='構造化データ (JSON)')),
                ('received_at', models.DateTimeField(auto_now_add=True, verbose_name='受信日時')),
                ('original_timestamp', models.DateTimeField(blank=True, null=True, verbose_name='元の記録日時')),
                ('latitude', models.FloatField(blank=True, null=True, verbose_name='緯度')),
                ('longitude', models.FloatField(blank=True, null=True, verbose_name='経度')),
                ('is_processed', models.BooleanField(default=False, help_text='このデータが分析や集計で利用されたかどうか', verbose_name='処理済')),
            ],
            options={
                'verbose_name': 'RPiデータ',
                'verbose_name_plural': 'RPiデータ一覧',
                'ordering': ['-received_at'],
            },
        ),
        migrations.CreateModel(
            name='Shelter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('management_id', models.CharField(help_text='例: TKY-SHIBUYA-01 のように、システム全体でユニークなIDを設定してください。', max_length=50, unique=True, verbose_name='避難所管理ID')),
                ('name', models.CharField(max_length=200, unique=True, verbose_name='避難所名')),
                ('address', models.CharField(max_length=255, verbose_name='住所')),
                ('latitude', models.FloatField(blank=True, null=True, verbose_name='緯度')),
                ('longitude', models.FloatField(blank=True, null=True, verbose_name='経度')),
                ('max_capacity', models.IntegerField(verbose_name='最大収容人数')),
                ('current_occupancy', models.IntegerField(default=0, verbose_name='現在の収容人数')),
                ('opening_status', models.CharField(choices=[('open', '開設中'), ('closed', '閉鎖'), ('preparating', '開設準備中')], default='open', max_length=20, verbose_name='開設状況')),
                ('is_pet_friendly', models.BooleanField(default=False, verbose_name='ペット可')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='最終更新日時')),
            ],
            options={
                'verbose_name': '避難所',
                'verbose_name_plural': '避難所一覧',
            },
        ),
        migrations.CreateModel(
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
            },
        ),
        migrations.CreateModel(
            name='OnlineUser',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('channel_name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='SafetyStatus',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='safety_status_record', serialize=False, to=settings.AUTH_USER_MODEL, verbose_name='ユーザー')),
                ('status', models.CharField(choices=[('safe', '無事'), ('help', '支援が必要'), ('unknown', '未確認'), ('checking', '確認中')], default='unknown', max_length=20, verbose_name='安否状態')),
                ('message', models.TextField(blank=True, help_text='状況を知らせる自由記述のメッセージ (例: ○○に避難中、食料あり)', null=True, verbose_name='状況メッセージ')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='最終更新日時')),
                ('latitude', models.FloatField(blank=True, null=True, verbose_name='緯度')),
                ('longitude', models.FloatField(blank=True, null=True, verbose_name='経度')),
            ],
            options={
                'verbose_name': '安否状況',
                'verbose_name_plural': '安否状況',
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(verbose_name='メッセージ内容')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='送信日時')),
                ('is_read', models.BooleanField(default=False, verbose_name='既読')),
                ('image', models.ImageField(blank=True, null=True, upload_to='chat_images/', verbose_name='添付画像')),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='group_messages', to='Sotsuken_Portable.group', verbose_name='宛先グループ')),
                ('recipient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='received_messages', to=settings.AUTH_USER_MODEL, verbose_name='宛先ユーザー')),
                ('sender', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_messages', to=settings.AUTH_USER_MODEL, verbose_name='送信者')),
            ],
            options={
                'verbose_name': 'メッセージ',
                'verbose_name_plural': 'メッセージ一覧',
                'ordering': ['timestamp'],
            },
        ),
        migrations.AddField(
            model_name='group',
            name='creator',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_groups', to=settings.AUTH_USER_MODEL, verbose_name='作成者'),
        ),
        migrations.CreateModel(
            name='FieldReportLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_evacuees', models.PositiveIntegerField(verbose_name='報告時の避難者数')),
                ('medical_needs', models.PositiveIntegerField(verbose_name='報告時の要介護者数')),
                ('food_stock', models.CharField(max_length=10, verbose_name='報告時の食料残量')),
                ('original_timestamp', models.DateTimeField(verbose_name='現場での報告日時')),
                ('received_at', models.DateTimeField(auto_now_add=True, verbose_name='サーバー受信日時')),
                ('reported_by_device', models.CharField(blank=True, max_length=100, null=True, verbose_name='報告デバイスID')),
                ('shelter', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='Sotsuken_Portable.shelter', verbose_name='報告元避難所')),
            ],
            options={
                'verbose_name': '現場状況報告ログ',
                'verbose_name_plural': '現場状況報告ログ',
                'ordering': ['-original_timestamp'],
            },
        ),
        migrations.CreateModel(
            name='DistributionInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location_name', models.CharField(help_text='避難所を選択しない場合は具体的な場所名を入力（例: 〇〇公園）', max_length=100, verbose_name='場所名')),
                ('info_type', models.CharField(choices=[('food', '炊き出し・食料'), ('supplies', '物資配布'), ('water', '給水'), ('bath', '入浴支援')], max_length=20, verbose_name='種別')),
                ('title', models.CharField(max_length=100, verbose_name='内容タイトル')),
                ('description', models.TextField(blank=True, verbose_name='詳細')),
                ('status', models.CharField(choices=[('scheduled', '予定'), ('active', '実施中'), ('ended', '終了')], default='scheduled', max_length=20, verbose_name='状況')),
                ('start_time', models.DateTimeField(blank=True, null=True, verbose_name='開始日時')),
                ('end_time', models.DateTimeField(blank=True, null=True, verbose_name='終了日時')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('related_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='Sotsuken_Portable.distributionitem', verbose_name='配布品目 (マスタ)')),
                ('shelter', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='Sotsuken_Portable.shelter', verbose_name='関連避難所')),
            ],
            options={
                'verbose_name': '炊き出し・物資情報',
                'verbose_name_plural': '炊き出し・物資情報',
                'ordering': ['status', 'start_time'],
            },
        ),
        migrations.CreateModel(
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
            },
        ),
        migrations.CreateModel(
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
            },
        ),
        migrations.CreateModel(
            name='GroupMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('member', 'メンバー'), ('admin', 'グループ管理者')], default='member', max_length=20, verbose_name='グループ内権限')),
                ('joined_at', models.DateTimeField(auto_now_add=True, verbose_name='参加日時')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='Sotsuken_Portable.group', verbose_name='グループ')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_memberships', to=settings.AUTH_USER_MODEL, verbose_name='メンバー')),
            ],
            options={
                'verbose_name': 'グループメンバー',
                'verbose_name_plural': 'グループメンバー',
                'unique_together': {('group', 'member')},
            },
        ),
        migrations.CreateModel(
            name='DistributionRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('distributed_at', models.DateTimeField(auto_now_add=True, verbose_name='配布日時')),
                ('recorded_by_device', models.CharField(blank=True, max_length=100, null=True, verbose_name='記録デバイスID')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Sotsuken_Portable.distributionitem', verbose_name='受け取り物資')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='受け取りユーザー')),
            ],
            options={
                'unique_together': {('user', 'item')},
            },
        ),
        migrations.CreateModel(
            name='Connection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('requesting', '申請中'), ('accepted', '承認済み'), ('blocked', 'ブロック')], default='requesting', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('receiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_connections', to=settings.AUTH_USER_MODEL)),
                ('requester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_connections', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('requester', 'receiver')},
            },
        ),
    ]
