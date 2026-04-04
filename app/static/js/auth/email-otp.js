/**
 * app/static/js/auth/email-otp.js
 * OTP verification page — handles "Send OTP" button click.
 *
 * Requires (loaded before this file):
 *   - jQuery 3.x (full build, not slim)
 *   - app/static/js/common/utils.js  (RequestManager, debounce, showNotification)
 */

(function ($) {
    'use strict';

    var otpRequestManager = new RequestManager();
    var lastEmailSent = null;  // Prevent duplicate sends for the same address

    /**
     * Send an OTP for the given email address.
     * Uses RequestManager to abort any in-flight request before firing a new one.
     */
    function sendOtp() {
        var emailID = $('#email').val().trim();

        if (!emailID) {
            showNotification('Please enter an email address.', 'warning');
            return;
        }

        // Basic email format check before hitting the server
        var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(emailID)) {
            showNotification('Please enter a valid email address.', 'warning');
            return;
        }

        // Skip if we already sent an OTP for this exact email
        if (emailID === lastEmailSent) {
            showNotification('OTP already sent to this address.', 'warning');
            return;
        }

        otpRequestManager.send({
            type: 'GET',
            async: true,
            url: '/auth/send_otp',
            data: { emailID: emailID },
            success: function (data) {
                $('#output').text(data.message);
                if (data.message === 'OTP Sent') {
                    lastEmailSent = emailID;
                    showNotification('OTP sent successfully.', 'success');
                } else {
                    showNotification(data.message, 'warning');
                }
            },
            error: function (xhr, status, error) {
                if (status !== 'abort') {
                    $('#output').text('Request failed. Please try again.');
                    showNotification('Could not send OTP. Please try again.', 'error');
                }
            }
        });
    }

    // Debounce the send so rapid button clicks don't fire multiple requests
    var debouncedSendOtp = debounce(sendOtp, 400);

    $(document).ready(function () {
        $('#btn-send-otp').on('click', debouncedSendOtp);

        // Reset the "already sent" guard when the user types a new email
        $('#email').on('input', function () {
            if ($(this).val().trim() !== lastEmailSent) {
                lastEmailSent = null;
            }
        });
    });

}(jQuery));
