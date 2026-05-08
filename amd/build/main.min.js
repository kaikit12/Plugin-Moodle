/**
 * Linh hồn Frontend (Logic AJAX hiển thị) của local_exercise_suggestion
 * Mở rộng cho luồng Dashboard.
 *
 * @module local_exercise_suggestion/main
 */
define(['jquery', 'core/ajax', 'core/templates', 'core/notification', 'core/modal_factory', 'core/modal_events'], 
    function ($, Ajax, Templates, Notification, ModalFactory, ModalEvents) {

    /**
     * Hàm render Skeleton HTML (Hiệu ứng đang tải)
     * @param {Object} container The jQuery element
     */
    function showLoadingSkeleton(container) {
        var skeletonHtml = `
            <div class="text-center" style="padding: 30px 10px;">
                <i class="fa fa-spinner fa-spin fa-3x" style="color: #667eea; margin-bottom: 15px;"></i>
                <h5 style="color: #555; font-size: 16px;">Vui lòng chờ</h5>
                <p style="color: #888; font-size: 14px;">AI đang tổng hợp dữ liệu từ các môn học của bạn...</p>
            </div>`;
        container.html(skeletonHtml);
    }

    return {
        /**
         * Hàm khởi tạo chính, được gọi từ trang Moodle
         */
        init: function () {
            $(document).ready(function () {
                var overlayVisible = false;

                // Lắng nghe sự kiện click trên nút "Chi tiết" bài tập
                $(document).on('click', '.btn-exercise-details', function (e) {
                    e.preventDefault();
                    var $btn = $(this);
                    
                    var exerciseId = $btn.data('id');
                    var courseId = $btn.data('courseid');
                    var title = $btn.data('title');
                    var sesskey = M.cfg.sesskey;

                    var originalHtml = $btn.html();
                    $btn.html('<i class="fa fa-spinner fa-spin"></i>').prop('disabled', true);

                    // Khởi tạo Modal (Chính giữa màn hình)
                    ModalFactory.create({
                        type: ModalFactory.types.DEFAULT,
                        title: 'Chi tiết bài tập: ' + title,
                        body: '<div class="text-center"><i class="fa fa-spinner fa-spin fa-3x"></i><p>Đang tải dữ liệu...</p></div>',
                        large: true
                    }).then(function (modal) {
                        modal.show();

                        // Destroy modal when hidden so it doesn't pile up in DOM
                        modal.getRoot().on(ModalEvents.hidden, function() {
                            modal.destroy();
                        });

                        // Call AJAX to get details
                        $.ajax({
                            url: M.cfg.wwwroot + '/local/exercise_suggestion/ajax.php',
                            type: 'POST',
                            dataType: 'json',
                            data: {
                                sesskey: sesskey,
                                action: 'get_exercise_details',
                                exerciseid: exerciseId,
                                courseid: courseId
                            },
                            success: function (response) {
                                if (response.status === 'success' && response.data) {
                                    var ex = response.data;
                                    var viewUrl = M.cfg.wwwroot + '/local/exercise_suggestion/index.php?courseid=' + courseId + '&action=view&exerciseid=' + exerciseId;
                                    
                                    var testcasesHtml = '';
                                    if (ex.test_cases && ex.test_cases.length > 0) {
                                        testcasesHtml = '<ul class="list-group list-group-flush" style="margin-top:10px;">';
                                        ex.test_cases.forEach(function(tc) {
                                            testcasesHtml += '<li class="list-group-item"><i class="fa fa-check text-success mr-2"></i> ' + tc.message + '</li>';
                                        });
                                        testcasesHtml += '</ul>';
                                    } else {
                                        testcasesHtml = '<p class="text-muted">Không có yêu cầu cụ thể.</p>';
                                    }
                                    
                                    var instructionsHtml = ex.instructions ? '<p>' + ex.instructions + '</p>' : '';

                                    var htmlBody = `
                                        <div>
                                            <h5>Mô tả:</h5>
                                            <p>${ex.description}</p>
                                            <h5 class="mt-4">Yêu cầu / Tiêu chí chấm điểm:</h5>
                                            ${instructionsHtml}
                                            ${testcasesHtml}
                                            
                                            <div class="mt-4">
                                                <span class="badge badge-info mb-2 p-2" style="font-size: 14px;">Mức độ: ${ex.difficulty}</span>
                                                <span class="badge badge-secondary mb-2 p-2 ml-2" style="font-size: 14px;"><i class="fa fa-clock-o"></i> ${ex.estimated_time} phút</span>
                                            </div>
                                        </div>
                                    `;
                                    modal.setBody(htmlBody);
                                    
                                    // Custom footer with "Thoát" and "Làm ngay" on the right
                                    var htmlFooter = `
                                        <button type="button" class="btn btn-secondary" data-action="hide">Thoát</button>
                                        <a href="${viewUrl}" class="btn btn-primary">Làm ngay <i class="fa fa-arrow-right"></i></a>
                                    `;
                                    modal.setFooter(htmlFooter);
                                    
                                } else {
                                    modal.setBody('<div class="alert alert-warning">Không thể lấy được chi tiết bài tập.</div>');
                                }
                                $btn.html(originalHtml).prop('disabled', false);
                            },
                            error: function () {
                                modal.setBody('<div class="alert alert-danger">Lỗi kết nối máy chủ.</div>');
                                $btn.html(originalHtml).prop('disabled', false);
                            }
                        });
                    }).catch(Notification.exception);
                });

                // Lắng nghe sự kiện click trên FAB Dashboard
                $(document).on('click', '.btn-suggest-exercise-dashboard', function (e) {
                    e.preventDefault();

                    var $btn = $(this);
                    var $overlay = $('#suggestion-dashboard-overlay');
                    var sesskey = M.cfg.sesskey;

                    // Toggle overlay
                    if (overlayVisible) {
                        $overlay.fadeOut(200);
                        overlayVisible = false;
                        return;
                    }

                    $overlay.fadeIn(200);
                    overlayVisible = true;

                    // Chỉ gọi dữ liệu khi chưa có (tránh gọi nhiều lần)
                    if ($overlay.data('loaded')) {
                        return;
                    }

                    // 1. Thay đổi UI để User biết hệ thống đang xử lý
                    var originalBtnHtml = $btn.html();
                    $btn.html('<i class="fa fa-spinner fa-spin"></i> Đang phân tích...');

                    showLoadingSkeleton($overlay);

                    // 2. Gọi AJAX lấy Dashboard Summary
                    $.ajax({
                        url: M.cfg.wwwroot + '/local/exercise_suggestion/ajax.php',
                        type: 'POST',
                        dataType: 'json',
                        data: {
                            sesskey: sesskey,
                            action: 'get_dashboard_summary'
                        },
                        success: function (response) {
                            if (response.status === 'success') {
                                // 3. Gọi hàm Template render của Moodle (Mustache JS)
                                Templates.render('local_exercise_suggestion/dashboard_suggestions', response.data)
                                    .done(function (html, js) {
                                        $overlay.hide().html(html).fadeIn(300);
                                        Templates.runTemplateJS(js);

                                        $overlay.data('loaded', true);
                                        $btn.html(originalBtnHtml);
                                    })
                                    .fail(Notification.exception);
                            } else {
                                Notification.addNotification({
                                    message: response.message || 'Lỗi không xác định từ Server.',
                                    type: 'error'
                                });
                                $btn.html(originalBtnHtml);
                                $overlay.fadeOut(200);
                                overlayVisible = false;
                            }
                        },
                        error: function (xhr) {
                            var errorMsg = 'Lỗi kết nối đến máy chủ.';
                            if (xhr.responseJSON && xhr.responseJSON.message) {
                                errorMsg = xhr.responseJSON.message;
                            }

                            Notification.addNotification({
                                message: errorMsg,
                                type: 'error'
                            });

                            $btn.html(originalBtnHtml);
                            $overlay.fadeOut(200);
                            overlayVisible = false;
                        }
                    });
                });
            });
        }
    };
});

