from django.contrib.auth.password_validation import UserAttributeSimilarityValidator
from django.core.exceptions import ValidationError

class CustomUserAttributeSimilarityValidator(UserAttributeSimilarityValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError as e:
            # 標準のエラーメッセージをキャッチして、独自のものに書き換える
            if e.code == 'password_too_similar':
                raise ValidationError(
                    "このパスワードは他の個人情報と似ているため\n使用できません。",
                    code='password_too_similar'
                )
            raise e