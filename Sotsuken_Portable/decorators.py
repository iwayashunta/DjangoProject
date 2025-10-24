from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden

def admin_required(function=None, login_url=None):
    """
    ユーザーのロールが 'admin' または 'rescuer' であることを確認するデコレータ
    """
    # ユーザーが条件を満たすか（TrueかFalseか）を判定する関数
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.role in ['admin', 'rescuer'],
        login_url=login_url or '/login/' # 条件を満たさない場合の遷移先
    )
    if function:
        return actual_decorator(function)
    return actual_decorator