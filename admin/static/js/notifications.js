// admin/static/js/notifications.js

$(document).ready(function() {
    // Загружаем уведомления при загрузке страницы
    loadNotifications();

    // Обновляем уведомления каждые 30 секунд
    setInterval(loadNotifications, 30000);

    // Обработчик клика на "Отметить все как прочитанные"
    $('#mark-all-read').click(function(e) {
        e.preventDefault();

        $.ajax({
            url: '/notifications/mark-read',
            type: 'POST',
            success: function() {
                $('#notifications-badge').hide();
                showAlert('Все уведомления отмечены как прочитанные', 'success');
                loadNotifications();
            },
            error: function() {
                showAlert('Ошибка при обработке уведомлений', 'danger');
            }
        });
    });

    // Предотвращаем закрытие выпадающего меню при клике на его содержимое
    $(document).on('click', '.notification-item', function(e) {
        e.stopPropagation();
    });
});

// Функция загрузки уведомлений
function loadNotifications() {
    $.get('/notifications', function(data) {
        const unreadCount = data.unreadCount;
        const notifications = data.notifications;

        // Обновляем счетчик непрочитанных уведомлений
        if (unreadCount > 0) {
            $('#notifications-badge').text(unreadCount).show();
        } else {
            $('#notifications-badge').hide();
        }

        // Очищаем и заполняем список уведомлений
        const notificationsList = $('#notifications-list');
        notificationsList.empty();

        if (notifications.length === 0) {
            notificationsList.html('<div class="text-center p-3 text-muted">Нет новых уведомлений</div>');
        } else {
            notifications.forEach(function(notification) {
                let badgeClass = '';

                // Определяем класс и цвет для различных типов уведомлений
                switch (notification.type) {
                    case 'order':
                        if (notification.status === 'paid') {
                            badgeClass = 'bg-success';
                        } else if (notification.status === 'pending') {
                            badgeClass = 'bg-warning';
                        } else {
                            badgeClass = 'bg-secondary';
                        }
                        break;
                    case 'bug_report':
                        if (notification.status === 'new') {
                            badgeClass = 'bg-danger';
                        } else if (notification.status === 'in_progress') {
                            badgeClass = 'bg-primary';
                        } else {
                            badgeClass = 'bg-success';
                        }
                        break;
                    case 'review':
                        if (notification.rating >= 4) {
                            badgeClass = 'bg-success';
                        } else if (notification.rating >= 2) {
                            badgeClass = 'bg-warning';
                        } else {
                            badgeClass = 'bg-danger';
                        }
                        break;
                    case 'message':
                        badgeClass = 'bg-info';
                        break;
                    default:
                        badgeClass = 'bg-secondary';
                }

                // Форматируем дату
                const date = new Date(notification.created_at);
                const formattedDate = date.toLocaleString();

                // Создаем элемент уведомления
                const notificationItem = `
                    <a href="${notification.link}" class="dropdown-item notification-item d-flex align-items-center py-2">
                        <div class="me-3">
                            <div class="icon-circle ${badgeClass}">
                                <i class="fas ${notification.icon} text-white"></i>
                            </div>
                        </div>
                        <div>
                            <div class="small text-muted">${formattedDate}</div>
                            <span class="fw-bold">${notification.title}</span>
                            <div class="text-truncate" style="max-width: 250px;">${notification.message}</div>
                        </div>
                    </a>
                `;

                notificationsList.append(notificationItem);
            });
        }
    });
}