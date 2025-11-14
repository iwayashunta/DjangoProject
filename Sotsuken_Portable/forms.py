import self
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django import forms

from .models import User, SafetyStatus, SupportRequest, CommunityPost, Comment, Group, Shelter  # カスタムUserモデルをインポート

class SignUpForm(UserCreationForm):
    """
    ユーザー登録用のフォーム
    """
    class Meta(UserCreationForm.Meta):
        # フォームの基になるモデルと、使用するフィールドを指定
        model = User
        fields = ('login_id', 'full_name', 'email') # ここに登録時に入力させたい項目を追加

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
        fields = ('title', 'content', 'region_tag')
        labels = {
            'title': 'タイトル',
            'content': '内容',
            'region_tag': '地域タグ (任意、例: 〇〇地区)',
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
            'text': '', # ラベルは表示しない（プレースホルダーで示すため）
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
        fields = ('name',) # ユーザーに入力させるのはグループ名のみ
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

class ShelterForm(forms.ModelForm):
    class Meta:
        model = Shelter
        # フォームに表示するフィールドを指定
        fields = ['management_id', 'name', 'address', 'max_capacity', 'current_occupancy', 'is_pet_friendly', 'opening_status']
        # フォームのラベルを日本語で分かりやすく設定
        labels = {
            'management_id': '避難所管理ID',
            'name': '避難所名',
            'address': '住所',
            #'latitude': '緯度',  # 一旦消してます
            #'longitude': '経度', # 一旦消してます
            'max_capacity': '最大収容人数',
            'current_occupancy': '現在の避難者数',
            'is_pet_friendly': 'ペット受け入れ可',
            'opening_status': '開設状況',
        }

        help_texts = {
            'management_id': '他の避難所と絶対に重複しない、半角英数字のIDを入力してください。例: TKY-SHIBUYA-01',
            'current_occupancy': 'この値は現場レポートによっても自動更新されます。',
        }



