from django.contrib.auth.forms import UserCreationForm
from django import forms

from .models import User, SafetyStatus, SupportRequest  # カスタムUserモデルをインポート

class SignUpForm(UserCreationForm):
    """
    ユーザー登録用のフォーム
    """
    class Meta(UserCreationForm.Meta):
        # フォームの基になるモデルと、使用するフィールドを指定
        model = User
        fields = ('username', 'email') # ここに登録時に入力させたい項目を追加

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