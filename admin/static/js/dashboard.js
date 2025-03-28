// admin/static/js/dashboard.js

$(document).ready(function() {
    loadDashboardData();

    // Обработчик кнопки обновления
    $('#refresh-dashboard').click(function() {
        $(this).find('i').addClass('fa-spin');
        loadDashboardData();
        setTimeout(() => {
            $(this).find('i').removeClass('fa-spin');
        }, 1000);
    });

    // Обработчики переключения периода для графика
    $('.btn-group [data-period]').click(function() {
        $('.btn-group [data-period]').removeClass('active');
        $(this).addClass('active');
        loadSalesChart($(this).data('period'));
    });
});

// Функция для загрузки данных дашборда
function loadDashboardData() {
    // Загрузка количества пользователей
    $.get('/users/count', function(data) {
        $('#users-count').text(data.count);
    }).fail(function(error) {
        $('#users-count').text('Ошибка');
        console.error('Error loading users count:', error);
    });

    // Загрузка статистики продаж
    $.get('/payments/stats', function(data) {
        $('#sales-count').text(data.total_sales.toFixed(2) + ' руб.');

        // Добавим доп. инфо
        $('#sales-info').html(
            `<small>Всего заказов: ${data.total_orders}<br>` +
            `Оплачено: ${data.paid_orders}<br>` +
            `В ожидании: ${data.pending_orders}</small>`
        );
    }).fail(function(error) {
        $('#sales-count').text('Ошибка');
        console.error('Error loading sales stats:', error);
    });

    // Загрузка количества ботов
    $.get('/bots/count', function(data) {
        $('#bots-count').text(data.count);
    }).fail(function(error) {
        $('#bots-count').text('Ошибка');
        console.error('Error loading bots count:', error);
    });

    // Загрузка количества баг-репортов
    $.get('/reports/count', function(data) {
        $('#bugs-count').text(data.count);
    }).fail(function(error) {
        $('#bugs-count').text('Ошибка');
        console.error('Error loading bugs count:', error);
    });

    // Загрузка последних продаж
    $.get('/payments/latest', function(data) {
        renderLatestSales(data);
    }).fail(function(error) {
        $('#latest-sales-table tbody').html('<tr><td colspan="5" class="text-center text-danger">Ошибка загрузки данных</td></tr>');
        console.error('Error loading latest sales:', error);
    });

    // Загрузка последних баг-репортов
    $.get('/reports/latest', function(data) {
        renderLatestBugReports(data);
    }).fail(function(error) {
        $('#latest-bugs-table tbody').html('<tr><td colspan="5" class="text-center text-danger">Ошибка загрузки данных</td></tr>');
        console.error('Error loading latest bugs:', error);
    });

    // Загружаем данные для графика по умолчанию (неделя)
    loadSalesChart('week');
}

// Функция для отображения последних продаж
function renderLatestSales(data) {
    var tableBody = $('#latest-sales-table tbody');
    tableBody.empty();

    if (data.length === 0) {
        tableBody.append('<tr><td colspan="5" class="text-center">Нет данных</td></tr>');
    } else {
        data.forEach(function(sale) {
            tableBody.append(`
                <tr>
                    <td>${sale.id}</td>
                    <td>${sale.user.username || sale.user.first_name || 'ID: ' + sale.user.id}</td>
                    <td>${sale.bot.name}</td>
                    <td>${sale.amount.toFixed(2)} ₽</td>
                    <td>${new Date(sale.created_at).toLocaleString()}</td>
                </tr>
            `);
        });
    }
}

// Функция для отображения последних баг-репортов
function renderLatestBugReports(data) {
    var tableBody = $('#latest-bugs-table tbody');
    tableBody.empty();

    if (data.length === 0) {
        tableBody.append('<tr><td colspan="5" class="text-center">Нет данных</td></tr>');
    } else {
        data.forEach(function(bug) {
            // Определение класса для статуса
            let statusClass = 'badge badge-';
            switch(bug.status) {
                case 'new':
                    statusClass += 'warning';
                    bug.status = 'Новый';
                    break;
                case 'in_progress':
                    statusClass += 'info';
                    bug.status = 'В работе';
                    break;
                case 'resolved':
                    statusClass += 'success';
                    bug.status = 'Решен';
                    break;
                default:
                    statusClass += 'secondary';
            }

            tableBody.append(`
                <tr>
                    <td>${bug.id}</td>
                    <td>${bug.user.username || bug.user.first_name || 'ID: ' + bug.user.id}</td>
                    <td>${bug.bot.name}</td>
                    <td><span class="${statusClass}">${bug.status}</span></td>
                    <td>${new Date(bug.created_at).toLocaleString()}</td>
                </tr>
            `);
        });
    }
}

// Функция для загрузки данных графика продаж
function loadSalesChart(period) {
    // В реальном приложении здесь был бы запрос к API
    // Сейчас используем заглушку с тестовыми данными

    let labels = [];
    let data = [];

    if (period === 'week') {
        labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
        data = [5000, 3000, 4500, 2500, 6000, 7000, 4000];
    } else if (period === 'month') {
        labels = ['Неделя 1', 'Неделя 2', 'Неделя 3', 'Неделя 4'];
        data = [15000, 20000, 18000, 25000];
    } else if (period === 'year') {
        labels = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];
        data = [30000, 25000, 40000, 35000, 42000, 48000, 50000, 55000, 45000, 60000, 70000, 75000];
    }

    const ctx = document.getElementById('salesChart').getContext('2d');

    // Уничтожаем предыдущий график, если он существует
    if (window.salesChart) {
        window.salesChart.destroy();
    }

    // Создаем новый график
    window.salesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Продажи (руб.)',
                data: data,
                backgroundColor: 'rgba(78, 115, 223, 0.2)',
                borderColor: 'rgba(78, 115, 223, 1)',
                borderWidth: 2,
                tension: 0.3,
                pointRadius: 3,
                pointBackgroundColor: 'rgba(78, 115, 223, 1)',
                pointBorderColor: '#fff',
                pointHoverRadius: 5,
                pointHoverBackgroundColor: 'rgba(78, 115, 223, 1)',
                pointHoverBorderColor: '#fff',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString() + ' ₽';
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.parsed.y.toLocaleString() + ' ₽';
                        }
                    }
                }
            }
        }
    });
}