// admin/static/js/bot-edit.js

$(document).ready(function() {
    // Функция обновления финальной цены со скидкой
    function updateFinalPrice() {
        const price = parseFloat($('#price').val()) || 0;
        const discount = parseFloat($('#discount').val()) || 0;
        const categoryDiscount = parseFloat($('#category-discount').val()) || 0;

        // Используем максимальную скидку
        const effectiveDiscount = Math.max(discount, categoryDiscount);

        if (price > 0 && effectiveDiscount > 0) {
            const finalPrice = price * (1 - effectiveDiscount / 100);
            $('#final-price').text(finalPrice.toFixed(2) + ' ₽');
            $('#price-container').show();
        } else {
            $('#final-price').text(price.toFixed(2) + ' ₽');
            $('#price-container').hide();
        }
    }

    // Инициализируем rich text редактор для описания
    if ($('#description').length) {
        $('#description').summernote({
            lang: 'ru-RU',
            height: 200,
            toolbar: [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['color', ['color']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
                ['view', ['fullscreen', 'codeview', 'help']]
            ],
            placeholder: 'Введите описание бота...'
        });
    }

    // Инициализируем rich text редактор для README
    if ($('#readme_content').length) {
        $('#readme_content').summernote({
            lang: 'ru-RU',
            height: 300,
            toolbar: [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'strikethrough', 'superscript', 'subscript', 'clear']],
                ['fontname', ['fontname']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['height', ['height']],
                ['table', ['table']],
                ['insert', ['link', 'picture', 'hr']],
                ['view', ['fullscreen', 'codeview', 'help']]
            ],
            placeholder: 'Введите инструкцию по установке и использованию бота...'
        });
    }

    // Обработка отображения имени файла в input file
    $('.custom-file-input').on('change', function() {
        const fileInput = $(this);
        const numFiles = fileInput.get(0).files.length;
        const label = fileInput.next('.custom-file-label');

        if (numFiles > 1) {
            label.text(numFiles + ' файлов выбрано');
        } else if (numFiles === 1) {
            label.text(fileInput.val().split('\\').pop());
        } else {
            label.text('Выберите файл');
        }

        // Добавляем превью изображений
        if (this.id === 'bot-images') {
            $('#image-preview').empty();
            const files = this.files;

            // Ограничиваем количество превью
            const maxPreviews = Math.min(files.length, 5);

            for (let i = 0; i < maxPreviews; i++) {
                const reader = new FileReader();
                reader.onload = (function(index) {
                    return function(e) {
                        $('#image-preview').append(
                            `<div class="image-item m-2 position-relative">
                                <img src="${e.target.result}" class="img-thumbnail" style="max-height: 100px; max-width: 150px;">
                                <button type="button" class="btn btn-sm btn-danger position-absolute" style="top: 0; right: 0;"
                                        onclick="$(this).parent().remove();">
                                    <i class="fas fa-times"></i>
                                </button>
                                <input type="hidden" name="image_order[]" value="${index}">
                            </div>`
                        );
                    }
                })(i);
                reader.readAsDataURL(files[i]);
            }

            // Предупреждение, если слишком много файлов
            if (files.length > 5) {
                showAlert('Вы выбрали ' + files.length + ' файлов. Будут загружены только первые 5.', 'warning');
            }
        }
    });

    // Обработка изменения категории
    $('#category_id').on('change', function() {
        const categoryId = $(this).val();
        if (categoryId) {
            // Получаем информацию о категории
            $.get('/bots/categories/' + categoryId, function(category) {
                if (category.discount > 0) {
                    $('#category-discount').val(category.discount);
                    $('#category-discount-info').text(`Скидка категории: ${category.discount}%`).show();
                } else {
                    $('#category-discount').val(0);
                    $('#category-discount-info').hide();
                }
                updateFinalPrice();
            });
        } else {
            $('#category-discount').val(0);
            $('#category-discount-info').hide();
            updateFinalPrice();
        }
    });

    // Обновление цены при изменении цены или скидки
    $('#price, #discount').on('input', updateFinalPrice);

    // Подготовка данных для предпросмотра
    function preparePreview() {
        // Основная информация
        const name = $('#name').val();
        const categoryId = $('#category_id').val();
        const categoryText = categoryId ? $('#category_id option:selected').text() : 'Без категории';
        const price = parseFloat($('#price').val()) || 0;
        const discount = parseFloat($('#discount').val()) || 0;
        const categoryDiscount = parseFloat($('#category-discount').val()) || 0;
        const effectiveDiscount = Math.max(discount, categoryDiscount);
        const supportLink = $('#support_group_link').val();
        const description = $('#description').summernote('code');
        const readme = $('#readme_content').summernote('code');
        const archiveFile = $('#archive_file')[0].files[0];

        // Заполняем информацию в модальное окно
        $('#preview-name').text(name);
        $('#preview-category').text(categoryText);

        // Цена и скидка
        if (price > 0) {
            if (effectiveDiscount > 0) {
                const finalPrice = price * (1 - effectiveDiscount / 100);
                $('#preview-price').html(`${finalPrice.toFixed(2)} ₽ <s class="text-muted">${price.toFixed(2)} ₽</s>`);
                $('#preview-discount').text(`Скидка ${effectiveDiscount}%`).show();
            } else {
                $('#preview-price').text(`${price.toFixed(2)} ₽`);
                $('#preview-discount').hide();
            }
        } else {
            $('#preview-price').text('0.00 ₽');
            $('#preview-discount').hide();
        }

        // Описание
        $('#preview-description').html(description);

        // Ссылка на группу поддержки
        if (supportLink) {
            const fullLink = 'https://t.me/' + supportLink;
            $('#preview-support').text(fullLink).attr('href', fullLink).parent().show();
        } else {
            $('#preview-support').parent().hide();
        }

        // Файл архива
        if (archiveFile) {
            $('#preview-archive').text(archiveFile.name);
        } else {
            $('#preview-archive').text('Не выбран');
        }

        // README
        $('#preview-readme').html(readme);

        // Изображения для карусели
        const botImages = $('#bot-images')[0].files;
        const carouselInner = $('#preview-carousel .carousel-inner');
        carouselInner.empty();

        if (botImages.length > 0) {
            for (let i = 0; i < Math.min(botImages.length, 5); i++) {
                const reader = new FileReader();
                reader.onload = (function(index) {
                    return function(e) {
                        carouselInner.append(`
                            <div class="carousel-item ${index === 0 ? 'active' : ''}">
                                <img src="${e.target.result}" class="d-block w-100" alt="Изображение ${index + 1}">
                            </div>
                        `);
                    }
                })(i);
                reader.readAsDataURL(botImages[i]);
            }
        } else {
            carouselInner.append(`
                <div class="carousel-item active">
                    <div class="d-flex justify-content-center align-items-center bg-light" style="height: 300px;">
                        <p class="text-muted">Нет изображений</p>
                    </div>
                </div>
            `);
        }
    }

    // Обработка отправки формы
    $('#create-bot-form, #edit-bot-form').submit(function(e) {
        e.preventDefault();

        // Проверяем, нужен ли предварительный просмотр
        if ($('#preview_bot').is(':checked')) {
            preparePreview();
            $('#previewModal').modal('show');
        } else {
            submitForm();
        }
    });

    // Отправка формы после предпросмотра
    $('#submit-after-preview').click(function() {
        $('#previewModal').modal('hide');
        submitForm();
    });

    // Функция отправки формы
    function submitForm() {
        const formId = $('.bot-form').attr('id');
        const formData = new FormData(document.getElementById(formId));
        const isEdit = formId === 'edit-bot-form';
        const botId = isEdit ? $('#bot-id').val() : null;

        // Добавляем изображения
        const botImages = $('#bot-images')[0].files;
        for (let i = 0; i < botImages.length; i++) {
            formData.append('media_files', botImages[i]);
        }

        // Определяем URL и метод запроса
        const url = isEdit ? `/bots/${botId}` : '/bots';
        const method = isEdit ? 'PUT' : 'POST';

        $.ajax({
            url: url,
            type: method,
            data: formData,
            contentType: false,
            processData: false,
            success: function(result) {
                showAlert(isEdit ? 'Бот успешно обновлен!' : 'Бот успешно создан!', 'success');
                // Перенаправляем на страницу списка ботов через 1 секунду
                setTimeout(function() {
                    window.location.href = '/bots/page';
                }, 1000);
            },
            error: function(error) {
                showAlert(
                    'Ошибка при ' + (isEdit ? 'обновлении' : 'создании') + ' бота: ' +
                    (error.responseJSON ? error.responseJSON.detail : 'Неизвестная ошибка'),
                    'danger'
                );
            }
        });
    }

    // Инициализация при загрузке страницы
    function init() {
        // Загружаем информацию о категории, если она выбрана
        const categoryId = $('#category_id').val();
        if (categoryId) {
            $('#category_id').trigger('change');
        }

        // Инициализируем отображение цены
        updateFinalPrice();
    }

    // Запускаем инициализацию
    init();
});