// admin/static/js/messages.js

$(document).ready(function() {
    const userId = $('input[name="user_id"]').val();

    // Загрузка истории сообщений
    function loadMessageHistory() {
        $.get(`/messages/message-history/${userId}`, function(data) {
            const messageContainer = $('#message-history');
            messageContainer.empty();

            if (data.length === 0) {
                messageContainer.html('<p class="text-center text-muted">Нет сообщений</p>');
                return;
            }

            // Сортируем сообщения от старых к новым
            data.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

            data.forEach(function(message) {
                const isAdmin = message.is_from_admin;
                const messageClass = isAdmin ? 'message message-admin' : 'message message-user';
                const sender = isAdmin ? 'Администратор' : 'Пользователь';

                let messageHtml = `
                    <div class="${messageClass}">
                        <div class="message-sender">
                            <strong>${sender}</strong>
                        </div>
                        <div class="message-content">
                `;

                // Добавляем медиа, если есть
                if (message.type !== 'text' && message.media_url) {
                    if (message.type === 'photo') {
                        messageHtml += `<img src="${message.media_url}" class="message-media"><br>`;
                    } else if (message.type === 'video') {
                        messageHtml += `<video src="${message.media_url}" class="message-media" controls></video><br>`;
                    } else if (message.type === 'audio') {
                        messageHtml += `<audio src="${message.media_url}" class="message-media" controls></audio><br>`;
                    } else if (message.type === 'document') {
                        messageHtml += `<a href="${message.media_url}" target="_blank" class="btn btn-sm btn-outline-primary">
                                            <i class="fas fa-file-download"></i> Скачать документ
                                        </a><br>`;
                    }
                }

                // Добавляем текст сообщения
                if (message.content) {
                    messageHtml += `${message.content}`;
                }

                // Добавляем время
                const messageDate = new Date(message.created_at);
                const formattedDate = messageDate.toLocaleString();

                messageHtml += `
                        </div>
                        <div class="message-time">
                            ${formattedDate}
                        </div>
                    </div>
                `;

                messageContainer.append(messageHtml);
            });

            // Прокручиваем контейнер до последнего сообщения
            messageContainer.scrollTop(messageContainer.prop('scrollHeight'));
        }).fail(function(error) {
            $('#message-history').html('<p class="text-center text-danger">Ошибка загрузки сообщений</p>');
            console.error('Error loading message history:', error);
        });
    }

    // Загружаем историю сообщений при загрузке страницы
    loadMessageHistory();

    // Обработка предпросмотра текстового сообщения
    $('#message_text').on('input', function() {
        const text = $(this).val();
        const parseMode = $('input[name="parse_mode"]:checked').val();

        let previewText = text;

        if (parseMode === 'html') {
            $('#text-preview').html(previewText);
        } else if (parseMode === 'markdown') {
            // Базовое преобразование Markdown в HTML для предпросмотра
            previewText = previewText
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/\n/g, '<br>');
            $('#text-preview').html(previewText);
        } else {
            $('#text-preview').text(previewText);
        }
    });

    // Обработка изменения режима форматирования для текстового сообщения
    $('input[name="parse_mode"]').change(function() {
        $('#message_text').trigger('input');
    });

    // Обработка отправки текстового сообщения
    $('#text-message-form').submit(function(e) {
        e.preventDefault();

        const messageText = $('#message_text').val();
        const parseMode = $('input[name="parse_mode"]:checked').val();

        if (!messageText.trim()) {
            alert('Введите текст сообщения');
            return;
        }

        // Отправляем AJAX запрос
        $.ajax({
            url: '/messages/send-text',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                user_id: userId,
                message_text: messageText,
                parse_mode: parseMode
            }),
            success: function(result) {
                if (result.success) {
                    $('#message_text').val('');
                    $('#text-preview').html('<p class="text-muted">Предпросмотр сообщения</p>');
                    showAlert('Сообщение успешно отправлено', 'success');
                    loadMessageHistory();
                } else {
                    showAlert('Ошибка: ' + result.message, 'danger');
                }
            },
            error: function(error) {
                showAlert('Ошибка при отправке сообщения', 'danger');
                console.error('Error sending message:', error);
            }
        });
    });

    // Обработка предпросмотра фото
    $('#photo').change(function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                $('#photo-preview').attr('src', e.target.result).show();
            };
            reader.readAsDataURL(file);
        } else {
            $('#photo-preview').hide();
        }
    });

    // Обработка отправки фото
    $('#photo-message-form').submit(function(e) {
        e.preventDefault();

        const formData = new FormData(this);

        $.ajax({
            url: '/messages/send-photo',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(result) {
                if (result.success) {
                    $('#photo-message-form')[0].reset();
                    $('#photo-preview').hide();
                    showAlert('Изображение успешно отправлено', 'success');
                    loadMessageHistory();
                } else {
                    showAlert('Ошибка: ' + result.message, 'danger');
                }
            },
            error: function(error) {
                showAlert('Ошибка при отправке изображения', 'danger');
                console.error('Error sending photo:', error);
            }
        });
    });

    // Обработка предпросмотра видео
    $('#video').change(function() {
        const file = this.files[0];
        if (file) {
            const videoPreview = $('#video-preview')[0];
            const videoURL = URL.createObjectURL(file);
            videoPreview.src = videoURL;
            videoPreview.style.display = 'block';
        } else {
            $('#video-preview').hide();
        }
    });

    // Обработка отправки видео
    $('#video-message-form').submit(function(e) {
        e.preventDefault();

        const formData = new FormData(this);

        $.ajax({
            url: '/messages/send-video',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(result) {
                if (result.success) {
                    $('#video-message-form')[0].reset();
                    $('#video-preview').hide();
                    showAlert('Видео успешно отправлено', 'success');
                    loadMessageHistory();
                } else {
                    showAlert('Ошибка: ' + result.message, 'danger');
                }
            },
            error: function(error) {
                showAlert('Ошибка при отправке видео', 'danger');
                console.error('Error sending video:', error);
            }
        });
    });

    // Обработка предпросмотра аудио
    $('#audio').change(function() {
        const file = this.files[0];
        if (file) {
            const audioPreview = $('#audio-preview')[0];
            const audioURL = URL.createObjectURL(file);
            audioPreview.src = audioURL;
            audioPreview.style.display = 'block';
        } else {
            $('#audio-preview').hide();
        }
    });

    // Обработка отправки аудио
    $('#audio-message-form').submit(function(e) {
        e.preventDefault();

        const formData = new FormData(this);

        $.ajax({
            url: '/messages/send-audio',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(result) {
                if (result.success) {
                    $('#audio-message-form')[0].reset();
                    $('#audio-preview').hide();
                    showAlert('Аудио успешно отправлено', 'success');
                    loadMessageHistory();
                } else {
                    showAlert('Ошибка: ' + result.message, 'danger');
                }
            },
            error: function(error) {
                showAlert('Ошибка при отправке аудио', 'danger');
                console.error('Error sending audio:', error);
            }
        });
    });

    // Обработка предпросмотра документа
    $('#document').change(function() {
        const file = this.files[0];
        if (file) {
            $('#document-preview-name').text('Выбран файл: ' + file.name).show();
        } else {
            $('#document-preview-name').hide();
        }
    });

    // Обработка отправки документа
    $('#document-message-form').submit(function(e) {
        e.preventDefault();

        const formData = new FormData(this);

        $.ajax({
            url: '/messages/send-document',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(result) {
                if (result.success) {
                    $('#document-message-form')[0].reset();
                    $('#document-preview-name').hide();
                    showAlert('Документ успешно отправлен', 'success');
                    loadMessageHistory();
                } else {
                    showAlert('Ошибка: ' + result.message, 'danger');
                }
            },
            error: function(error) {
                showAlert('Ошибка при отправке документа', 'danger');
                console.error('Error sending document:', error);
            }
        });
    });

    // Обновляем историю сообщений каждые 30 секунд
    setInterval(loadMessageHistory, 30000);
});