// admin/static/js/common.js

// Функция для показа уведомлений
function showAlert(message, type = 'success', duration = 5000) {
    const id = 'alert-' + Date.now();
    const html = `
        <div id="${id}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    $('#alerts-container').append(html);

    if (duration > 0) {
        setTimeout(function() {
            $('#' + id).fadeOut('slow', function() { $(this).remove(); });
        }, duration);
    }
}

// Настройка AJAX для включения токена авторизации
function setupAjaxAuth() {
    const token = localStorage.getItem('token');
    if (token) {
        $.ajaxSetup({
            beforeSend: function(xhr) {
                xhr.setRequestHeader('Authorization', 'Bearer ' + token);
            },
            error: function(xhr, status, error) {
                if (xhr.status === 401) {
                    console.log('Authentication error in API request');
                    showAlert('Ошибка аутентификации при запросе к API. Попробуйте перезайти.', 'danger');
                }
            }
        });
    }
}

// Подсветка активного пункта меню
function highlightActiveMenuItem() {
    const currentPath = window.location.pathname;

    if (currentPath === '/dashboard') {
        $('#nav-dashboard').addClass('active');
    } else if (currentPath.startsWith('/bots')) {
        if (currentPath.includes('/categories')) {
            $('#nav-categories').addClass('active');
        } else {
            $('#nav-bots').addClass('active');
        }
    } else if (currentPath.startsWith('/users')) {
        $('#nav-users').addClass('active');
    } else if (currentPath.startsWith('/payments')) {
        $('#nav-payments').addClass('active');
    } else if (currentPath.startsWith('/reports')) {
        $('#nav-reports').addClass('active');
    } else if (currentPath.startsWith('/changelogs')) {
        $('#nav-changelogs').addClass('active');
    }
}

// Инициализация при загрузке страницы
$(document).ready(function() {
    setupAjaxAuth();
    highlightActiveMenuItem();

    // Переключение боковой панели
    $("#menu-toggle").click(function(e) {
        e.preventDefault();
        $("#wrapper").toggleClass("toggled");
    });

    // Делаем функцию showAlert глобальной
    window.showAlert = showAlert;
});