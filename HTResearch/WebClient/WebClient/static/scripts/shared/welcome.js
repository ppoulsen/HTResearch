/**
 * Main script for the Welcome page. Creates a cookie to mark a user's initial visit.
 */

require(['shared/analytics', 'jquery'], function(Analytics, $) {
    'use strict';

    Analytics.startTracking();

    $('#create-cookie').click(function () {
        var expire = new Date();
        expire = new Date(expire.getTime() + 7776000000);
        document.cookie = "htresearchv2=amaterasu; path=/; expires=" + expire;

        window.location = '/get-started/';
    });
});