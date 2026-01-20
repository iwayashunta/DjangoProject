import re

import self
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User, SafetyStatus, SupportRequest, CommunityPost, Comment, Group, Shelter, \
    DistributionInfo, DistributionItem, OfficialAlert  # カスタムUserモデルをインポート

User = get_user_model()



class SafetyStatusForm(forms.ModelForm):
    """
    安否状況を報告・更新するためのフォーム
    """

    class Meta:
        model = SafetyStatus
        # フォームに表示するフィールドを指定
        fields = ('status', 'message')
        # 画面に表示されるラベル名を変更したい場合はlabelsも指定
        labels = {
            'status': '現在の安否状況',
            'message': '状況を伝えるメッセージ（任意）',
        }
        # ウィジェットのカスタマイズ（CSSクラスの追加など）
        widgets = {
            'status': forms.Select(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'message': forms.Textarea(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,  # テキストエリアの高さを3行分に指定
            }),
        }


class SupportRequestForm(forms.ModelForm):
    """
    支援要請を新規作成するためのフォーム
    """

    class Meta:
        model = SupportRequest
        # フォームに表示するフィールドを指定
        # (requesterはビューで自動的に設定するので、ここには含めない)
        fields = ('category', 'priority', 'details')
        labels = {
            'category': '要請カテゴリ (必須)',
            'priority': '優先度 (必須)',
            'details': '詳細な状況・数量など',
        }
        # ウィジェットのカスタマイズ（CSSクラスの追加など）
        widgets = {
            'category': forms.Select(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-400 bg-white'
            }),
            'priority': forms.Select(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-400 bg-white'
            }),
            'details': forms.Textarea(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-400',
                'rows': 3,  # こちらも高さを3行分に指定
                'placeholder': '具体的な品目や必要人数、期間を簡潔に入力してください。'  # プレースホルダーも追加可能
            }),
        }


class CommunityPostForm(forms.ModelForm):
    """
    コミュニティ投稿を作成・編集するためのフォーム
    """

    class Meta:
        model = CommunityPost
        # フォームでユーザーに入力させるフィールドを指定
        # authorはビューで自動的に設定するので、ここには含めない
        fields = ('title', 'content', 'region_tag', 'image')
        labels = {
            'title': 'タイトル',
            'content': '内容',
            'region_tag': '地域タグ (任意、例: 〇〇地区)',
            'image': '画像 (任意)',  # ★追加
        }
        # ウィジェットで入力欄にCSSクラスを適用
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'content': forms.Textarea(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 8
            }),
            'region_tag': forms.TextInput(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white'
            }),
        }


class CommentForm(forms.ModelForm):
    """
    リプライ（コメント）を投稿するためのフォーム
    """

    class Meta:
        model = Comment
        # ユーザーに入力させるのは text フィールドのみ
        fields = ('text',)
        labels = {
            'text': '',  # ラベルは表示しない（プレースホルダーで示すため）
        }
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': '返信を入力...'
            }),
        }


class GroupCreateForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ('name',)  # ユーザーに入力させるのはグループ名のみ
        labels = {
            'name': '新しいグループ名',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-lg', 'placeholder': '例: 山田家'})
        }


class UserUpdateForm(forms.ModelForm):
    """
    ユーザー情報（氏名、メールアドレス）を更新するためのフォーム
    """

    class Meta:
        model = User
        fields = ('full_name', 'email')
        labels = {
            'full_name': '氏名',
            'email': 'メールアドレス',
        }


class MyPasswordChangeForm(PasswordChangeForm):
    """
    PasswordChangeFormのラベルとヘルプテキストを日本語化するためのカスタムフォーム
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = "現在のパスワード"
        self.fields['new_password1'].label = "新しいパスワード"
        self.fields['new_password2'].label = "新しいパスワード（確認用）"

        # ↓↓↓ ヘルプテキストを日本語に設定 ↓↓↓
        self.fields['new_password1'].help_text = (
            '<ul>'
            '<li class="text-xs text-gray-500 list-disc list-inside">パスワードは8文字以上である必要があります。</li>'
            '<li class="text-xs text-gray-500 list-disc list-inside">一般的なパスワードや、数字のみのパスワードは使用できません。</li>'
            '</ul>'
        )
        self.fields['new_password2'].help_text = '確認のため、もう一度同じパスワードを入力してください。'


from django import forms
from .models import Shelter


class ShelterForm(forms.ModelForm):
    class Meta:
        model = Shelter
        # 1. fields に latitude, longitude を追加
        fields = ['management_id', 'name', 'address', 'latitude', 'longitude',
                  'max_capacity', 'current_occupancy', 'is_pet_friendly', 'opening_status']

        labels = {
            'management_id': '避難所管理ID',
            'name': '避難所名',
            'address': '住所',
            'latitude': '緯度',
            'longitude': '経度',
            'max_capacity': '最大収容人数',
            'current_occupancy': '現在の避難者数',
            'is_pet_friendly': 'ペット受け入れ可',
            'opening_status': '開設状況',
        }

        help_texts = {
            'management_id': '他の避難所と絶対に重複しない、半角英数字のIDを入力してください。例: TKY-SHIBUYA-01',
            'current_occupancy': 'この値は現場レポートによっても自動更新されます。',
        }

        widgets = {
            'management_id': forms.TextInput(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': '例: TKY-001'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': '例: 第一市民体育館'
            }),
            'address': forms.TextInput(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),

            # 2. 緯度・経度のウィジェットを追加
            'latitude': forms.NumberInput(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'id': 'id_latitude',  # JSで値を入れるためのID
                'placeholder': '例: 35.6895',
                'step': '0.000001'  # 小数点入力を許可
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'id': 'id_longitude',  # JSで値を入れるためのID
                'placeholder': '例: 139.6917',
                'step': '0.000001'  # 小数点入力を許可
            }),

            'max_capacity': forms.NumberInput(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'current_occupancy': forms.NumberInput(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'opening_status': forms.Select(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'is_pet_friendly': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
            }),
        }


class SignUpForm(UserCreationForm):
    """
    ユーザー登録用のフォーム
    モデルの変更（英数字ID、ユニークEmail）に対応
    """

    class Meta(UserCreationForm.Meta):
        model = User
        # AbstractUserの'username'と、カスタムフィールド'full_name', 'email'を使用
        fields = ('username', 'full_name', 'email')

    def __init__(self, *args, **kwargs):
        """
        フォームの初期化メソッド
        """
        super().__init__(*args, **kwargs)

        # username (ログインID) の設定
        self.fields['username'].label = 'ログインID'
        self.fields['username'].help_text = '半角英数字のみ使用可能です。'

        # full_name (氏名) の設定
        self.fields['full_name'].required = True  # 必須にする

        # email (メールアドレス) の設定
        self.fields['email'].required = True  # 必須にする

        # パスワード入力欄のヘルプテキスト設定
        # UserCreationForm ではフィールド名は 'password1' と 'password2' です
        if 'password1' in self.fields:
            self.fields['password1'].help_text = (
                "<ul>"
                "<li>パスワードは最低8文字以上必要です。</li>"
                "<li>他の個人情報と似ているものは使用できません。</li>"
                "<li>よく使われるパスワードは使用できません。</li>"
                "<li>数字だけのパスワードは使用できません。</li>"
                "</ul>"
            )

    def clean_username(self):
        """
        ログインIDのバリデーション（英数字チェック）
        """
        username = self.cleaned_data.get('username')
        # モデル側にもValidatorはありますが、フォームでも明示的にチェックして親切なエラーを出す
        if not re.match(r'^[a-zA-Z0-9]+$', username):
            raise ValidationError("ログインIDは半角英数字のみで入力してください。")
        return username

    def clean_email(self):
        """
        メールアドレスのバリデーション（重複チェック）
        """
        email = self.cleaned_data.get('email')
        if email:
            # 大文字小文字を区別せずに重複チェック (iexact)
            if User.objects.filter(email__iexact=email).exists():
                raise ValidationError("このメールアドレスは既に登録されています。")
        return email


class UserSearchForm(forms.Form):
    q = forms.CharField(
        label='キーワード',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '検索ワードを入力...',
            'class': 'w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )

    # ★追加: 検索対象の選択
    TARGET_CHOICES = [
        ('all', 'すべて (ID/氏名/メール)'),
        ('username', 'ログインID'),
        ('full_name', '氏名'),
        ('email', 'メールアドレス'),
    ]
    search_target = forms.ChoiceField(
        label='検索対象',
        choices=TARGET_CHOICES,
        initial='all',
        widget=forms.Select(attrs={
            'class': 'w-full p-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )

    # 安否状況での絞り込み
    status_filter = forms.ChoiceField(
        label='安否状況',
        required=False,
        choices=[
            ('', '全て'),
            ('safe', '無事'),
            ('help', '要支援'),
            ('unknown', '未確認'),
            ('unregistered', '未登録'),  # レコード自体がない場合
        ],
        widget=forms.Select(attrs={
            'class': 'w-full p-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )


class DistributionInfoForm(forms.ModelForm):
    """炊き出し・物資配布情報を登録・編集するフォーム"""

    # ★★★ 追加: 新規品目入力用のフィールド（モデルには保存されない一時的な欄） ★★★
    new_item_name = forms.CharField(
        label='新しい品目を追加',
        required=False,  # 必須ではない（既存から選ぶ場合もあるため）
        widget=forms.TextInput(attrs={
            'class': 'w-full p-2 border rounded bg-blue-50',
            'placeholder': 'リストにない場合、ここに入力してください（例: カイロ）'
        })
    )

    class Meta:
        model = DistributionInfo
        # 'shelter' と 'related_item' を追加しました
        fields = [
            'related_item', 'new_item_name', 'title', 'info_type', 'status',
            'shelter', 'location_name',
            'description', 'start_time', 'end_time'
        ]

        labels = {
            'related_item': '配布品目（リストから選択）',
            'new_item_name': '配布品目（リストにない場合）',  # ★追加
            'title': '配布内容のタイトル',
            'info_type': '情報の種類',
            'status': '現在の状況',
            'shelter': '場所（避難所から選択）',
            'location_name': '場所名（手入力する場合）',
            'description': '詳細情報',
            'start_time': '開始日時',
            'end_time': '終了日時',
        }

        help_texts = {
            'related_item': '既存のマスタから選ぶ場合はこちら。',
            'new_item_name': 'マスタにない品目を配布する場合はこちらに入力してください。',
            'location_name': '「避難所」を選択した場合は入力不要です。',
        }

        widgets = {
            'related_item': forms.Select(attrs={'class': 'w-full p-2 border rounded bg-white'}),

            # ★追加: 新規入力欄のデザイン
            'new_item_name': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded',
                'placeholder': '例: 菓子パン（マスタにない場合）'
            }),

            'title': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded',
                'placeholder': '例: おにぎりの配布、給水活動'
            }),
            'info_type': forms.Select(attrs={'class': 'w-full p-2 border rounded bg-white'}),
            'status': forms.Select(attrs={'class': 'w-full p-2 border rounded bg-white'}),
            'shelter': forms.Select(attrs={'class': 'w-full p-2 border rounded bg-white'}),
            'location_name': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded',
                'placeholder': '例: 第一公園 入口付近'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full p-2 border rounded',
                'rows': 3,
                'placeholder': '例: 1人2個まで。無くなり次第終了します。'
            }),
            'start_time': forms.DateTimeInput(attrs={'class': 'w-full p-2 border rounded', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'w-full p-2 border rounded', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ★ここに追加します (super().__init__ の後)
        self.fields['related_item'].required = False
        self.fields['new_item_name'].required = False
        self.fields['shelter'].required = False
        self.fields['location_name'].required = False

        # ★★★ ここが重要な修正ポイント ★★★

    def clean(self):
        """
        複数フィールドにまたがるバリデーション
        """
        cleaned_data = super().clean()

        # 1. 値の取得
        related_item = cleaned_data.get('related_item')
        new_item_name = cleaned_data.get('new_item_name')

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        # 2. 品目のチェック: どちらか一方が必須
        # (両方空ならエラー、両方入っていてもOKとするならこのままで良いですが、
        #  どちらか一つに絞りたい場合は if related_item and new_item_name: ... も追加します)
        if not related_item and not new_item_name:
            # フォーム全体のエラーとして表示する場合
            raise ValidationError("「リストから選択」または「品目名の手入力」のどちらかは必須です。")

            # もし特定のフィールドにエラーを出したい場合は以下のように書く
            # self.add_error('related_item', 'どちらかを入力してください')
            # self.add_error('new_item_name', 'どちらかを入力してください')

        # 3. 日時の前後関係チェック
        if start_time and end_time:
            if start_time > end_time:
                # end_time フィールドに対してエラーを追加する
                self.add_error('end_time', "終了日時は開始日時より後に設定してください。")

        return cleaned_data


# --- 配布物資マスタ用のフォーム ---
class DistributionItemForm(forms.ModelForm):
    class Meta:
        model = DistributionItem
        fields = ['name', 'description']
        labels = {
            'name': '物資名',
            'description': '説明',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 共通のデザイン（枠線、角丸、フォーカス時の色など）
        common_classes = "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"

        # 各フィールドにクラスを適用
        self.fields['name'].widget.attrs.update({
            'class': common_classes,
            'placeholder': '例: 飲料水 (500ml)'
        })
        self.fields['description'].widget.attrs.update({
            'class': common_classes,
            'rows': 4,  # 説明欄は少し高さをとる
            'placeholder': '補足説明があれば入力してください'
        })


# --- 公式アナウンス用のフォーム（ついでに作っておくと便利） ---
class OfficialAlertForm(forms.ModelForm):
    class Meta:
        model = OfficialAlert
        fields = ['title', 'content', 'severity', 'is_active']
        labels = {
            'title': 'タイトル',
            'content': '内容',
            'severity': '重要度',
            'is_active': '有効にする',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_classes = "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white"

        self.fields['title'].widget.attrs['class'] = common_classes
        self.fields['content'].widget.attrs.update({'class': common_classes, 'rows': 4})
        self.fields['severity'].widget.attrs['class'] = common_classes
        # チェックボックスは少し違うスタイルで
        self.fields['is_active'].widget.attrs[
            'class'] = "h-5 w-5 text-orange-600 focus:ring-orange-500 border-gray-300 rounded"