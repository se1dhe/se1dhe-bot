// admin/static/js/auth.js

$(document).ready(function() {
    // Проверяем, есть ли сохраненный токен для авторизации
    const token = localStorage.getItem('token');
    if (token && window.location.pathname === '/') {
        window.location.href = '/dashboard';
    }

    // Обработка выхода из системы
    $('#logout-btn').click(function(e) {
        e.preventDefault();
        localStorage.removeItem('token');
        window.location.href = '/';
    });
});

// Функция для сохранения токена после аутентификации
function saveAuthToken(token, redirect = '/dashboard') {
    localStorage.setItem('token', token);
    window.location.href = redirect;
}