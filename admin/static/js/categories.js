// admin/static/js/categories.js

$(document).ready(function() {
    // Загрузка списка категорий
    function loadCategories() {
        $.get('/bots/categories', function(data) {
            var tableBody = $('#categories-table tbody');
            tableBody.empty();

            if (data.length === 0) {
                tableBody.append('<tr><td colspan="6" class="text-center">Нет данных</td></tr>');
            } else {
                // Получаем количество ботов в каждой категории
                $.get('/bots', function(bots) {
                    // Создаем счетчик для категорий
                    var categoryCounts = {};

                    // Подсчитываем количество ботов для каждой категории
                    bots.forEach(function(bot) {
                        if (bot.category_id) {
                            if (!categoryCounts[bot.category_id]) {
                                categoryCounts[bot.category_id] = 0;
                            }
                            categoryCounts[bot.category_id]++;
                        }
                    });

                    // Отображаем категории с количеством ботов
                    data.forEach(function(category) {
                        var botCount = categoryCounts[category.id] || 0;

                        tableBody.append(`
                            <tr>
                                <td>${category.id}</td>
                                <td>${category.name}</td>
                                <td>${category.description || '-'}</td>
                                <td>${category.discount}%</td>
                                <td>${botCount}</td>
                                <td class="text-center">
                                    <button class="btn btn-primary btn-sm edit-category" data-id="${category.id}">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-danger btn-sm delete-category" data-id="${category.id}" data-name="${category.name}">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </td>
                            </tr>
                        `);
                    });
                });
            }
        }).fail(function(error) {
            showAlert('Ошибка при загрузке категорий: ' + error.responseJSON?.detail || 'Неизвестная ошибка', 'danger');
        });
    }

    // Загрузка категорий при загрузке страницы
    loadCategories();

    // Обработка добавления категории
    $('#save-category').click(function() {
        var formData = {
            name: $('#name').val(),
            description: $('#description').val(),
            discount: parseFloat($('#discount').val() || 0)
        };

        $.ajax({
            url: '/bots/categories',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function(result) {
                $('#addCategoryModal').modal('hide');
                $('#add-category-form')[0].reset();
                showAlert('Категория успешно добавлена', 'success');
                loadCategories();
            },
            error: function(error) {
                showAlert('Ошибка при добавлении категории: ' + error.responseJSON?.detail || 'Неизвестная ошибка', 'danger');
            }
        });
    });

    // Обработка редактирования категории - открытие модального окна
    $(document).on('click', '.edit-category', function() {
        var categoryId = $(this).data('id');

        $.get('/bots/categories/' + categoryId, function(category) {
            $('#edit-id').val(category.id);
            $('#edit-name').val(category.name);
            $('#edit-description').val(category.description || '');
            $('#edit-discount').val(category.discount);
            $('#editCategoryModal').modal('show');
        }).fail(function(error) {
            showAlert('Ошибка при загрузке данных категории: ' + error.responseJSON?.detail || 'Неизвестная ошибка', 'danger');
        });
    });

    // Сохранение отредактированной категории
    $('#update-category').click(function() {
        var categoryId = $('#edit-id').val();
        var formData = {
            name: $('#edit-name').val(),
            description: $('#edit-description').val(),
            discount: parseFloat($('#edit-discount').val() || 0)
        };

        $.ajax({
            url: '/bots/categories/' + categoryId,
            type: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function(result) {
                $('#editCategoryModal').modal('hide');
                showAlert('Категория успешно обновлена', 'success');
                loadCategories();
            },
            error: function(error) {
                showAlert('Ошибка при обновлении категории: ' + error.responseJSON?.detail || 'Неизвестная ошибка', 'danger');
            }
        });
    });

    // Удаление категории - открытие модального окна
    $(document).on('click', '.delete-category', function() {
        var categoryId = $(this).data('id');
        var categoryName = $(this).data('name');

        $('#delete-category-name').text(categoryName);
        $('#confirm-delete').data('id', categoryId);
        $('#deleteCategoryModal').modal('show');
    });

    // Подтверждение удаления категории
    $('#confirm-delete').click(function() {
        var categoryId = $(this).data('id');

        $.ajax({
            url: '/bots/categories/' + categoryId,
            type: 'DELETE',
            success: function(result) {
                $('#deleteCategoryModal').modal('hide');
                showAlert('Категория успешно удалена', 'success');
                loadCategories();
            },
            error: function(error) {
                $('#deleteCategoryModal').modal('hide');
                showAlert('Ошибка при удалении категории: ' + error.responseJSON?.detail || 'Неизвестная ошибка', 'danger');
            }
        });
    });
});