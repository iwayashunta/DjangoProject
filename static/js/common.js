// js/common.js

const screens = document.querySelectorAll('.screen');
const screenTitle = document.getElementById('screen-title');

// 画面を切り替える関数
function navigate(screenId, titleText) {
    screens.forEach(screen => {
        screen.style.display = 'none';
        // 画面切り替え時にスクロールをトップに戻す
        screen.closest('main').scrollTop = 0;
    });

    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.style.display = 'flex';
        // 画面の種類に応じて flex-direction を調整
        if (screenId === 'home-screen' || screenId === 'emergency-sos-screen' || screenId === 'admin-menu-screen' || screenId === 'user-menu-screen') {
            // これらの画面はコンテンツを中央に配置するflex-direction: columnがデフォルトで良いので削除
            targetScreen.classList.remove('flex-col');
        } else {
            // 他の画面はコンテンツを縦に並べるflex-direction: columnを適用
            targetScreen.classList.add('flex-col');
        }
        screenTitle.textContent = titleText;
    }
}

// ページ読み込み時の初期画面設定
document.addEventListener('DOMContentLoaded', function() {
    // ログインページの場合は login.html にリダイレクト、または別途ログイン画面を表示
    // ここはメインコンテンツ用の common.js なので、最初の画面をホームとする
    navigate('home-screen', '避難支援ホーム');
});