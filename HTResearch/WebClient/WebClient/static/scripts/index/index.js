/**
 * Main script for the Index page.
 */

require(['shared/analytics',
    'shared/modal',
    'index/map',
    'index/newsloader',
    'index/heatmap',
    'index/searchquery',
    'underscore',
    'jquery',
    'jquery.tmpl',
    'bootstrap',
    'async!https://maps.googleapis.com/maps/api/js?sensor=false&libraries=visualization'],
    function(Analytics, Modal, Map, NewsLoader, HeatMap, SearchQuery, _, $) {
    'use strict';

    var map;
    var newsLoader;

    function initialize() {
        $('#home-nav').addClass('active');
        $('.search-div').show();
        var visited = getCookie("htresearchv2");
        if (!visited) {
            window.location = '/welcome';
        }

        map = new Map($('#map-canvas')[0]);
        newsLoader = new NewsLoader();

        Analytics.startTracking();
        HeatMap.initialize(map.getMap());

        /**
         * Put items to search for here.
         * Properties are as follows:
         *     name: Name of the item searched for, should match data-search attribute for search results panels and
         *         filter control.
         *     url: URL of ajax call to get the data.
         *     search: Function to get the data, can be used instead of url.
         *         function(query, ready) { ... }
         *             where query is the search query, and
         *             ready is the function to which the results should be passed.
         *     toggleSelector: Search results panel toggle selector.
         *     collapseSelector: Collapsible region selector.
         *     listSelector: Search results list selector.
         *     linkClass: Class that will be on each link in search results.
         *     linkText: Function to determine what text will be displayed on links.
         *     onclick: Handler for clicking link.
         */
        var searchItems = [
            {
                name: 'organization',
                url: '/api/search-organizations/',
                toggleSelector: '#organization-toggle',
                collapseSelector: '#collapse-organizations',
                listSelector: '#organization-search-list',
                linkClass: 'org-link',
                linkText: function(item) { return item.name || item.organization_url || ''; },
                onclick: showOrganizationModal
            },
            {
                name: 'contact',
                url: '/api/search-contacts/',
                toggleSelector: '#contact-toggle',
                collapseSelector: '#collapse-contacts',
                listSelector: '#contact-search-list',
                linkClass: 'contact-link',
                linkText: function(item) { return (item.first_name || '') + ' ' + (item.last_name || '') },
                onclick: showContactModal
            },
            {
                name: 'publication',
                url: '/api/search-publications/',
                toggleSelector: '#publication-toggle',
                collapseSelector: '#collapse-publications',
                listSelector: '#publication-search-list',
                linkClass: 'publication-link',
                linkText: function(item) { return item.title; },
                onclick: showPublicationModal
            },
            {
                name: 'news',
                search: function(query, ready) { newsLoader.search(query, ready); },
                toggleSelector: '#news-toggle',
                collapseSelector: '#collapse-news',
                listSelector: '#news-search-list',
                linkClass: 'news-link',
                linkText: function(item) { return item.title; },
                onclick: function(item) { window.open(item.link, '_blank'); }
            }
        ];

        // Update search when changing text input
        $('#search-box').bind("keyup change blur", _.debounce(function() {
            var searchText = $('#search-box').val().trim();

            SearchQuery.search(searchText, searchItems, map);
        }, 300));

        $('#search-settings-dropdown').click(function(e) {
            e.stopPropagation();
        });

        // Repeat search when setting items to visible; hide when setting to invisible
        $('#search-settings-dropdown :checkbox').change(function() {
            var show = $(this).is(':checked');
            if(show) {
                var searchText = $('#search-box').val().trim();
                SearchQuery.search(searchText, searchItems, map, true);
            } else {
                var searchItem = $(this).attr('data-search');
                $('.panel[data-search=' + searchItem + ']').slideUp();
            }
        });

        // Prevent search form submit on enter
        $('#search-box').bind('keyup keypress', function(e) {
            var code = e.keyCode || e.which;
            if (code === 13) {
                e.preventDefault();
                return false;
            }
        });

        // Prevent clicks on search settings dropdown from closing the menu
        $('.dropdown-menu').on('click', function(e) {
            if($(this).hasClass('dropdown-menu-form')) {
                e.stopPropagation();
            }
        });

        // Legend
        var three_ps_legend = document.createElement('div');
        $(three_ps_legend).css('margin-bottom', '5px');
        $(three_ps_legend).html($("#map-legend").html());
        map.pushControl(google.maps.ControlPosition.LEFT_BOTTOM, three_ps_legend);

        // Make news follow currently viewed region, if that setting is selected
        map.bind('idle', function() {
            var regional = $('.btn-regional').is('.active');
            if(regional) {
                newsLoader.loadNewsByRegion(map.getMap());
            }
        });

        // Update news when toggling regional news
        $('.btn-regional').click(function() {
            setTimeout(function() {
                var regional = $('.btn-regional').is('.active');
                if(regional) {
                    newsLoader.loadNewsByRegion(map.getMap());
                } else {
                    newsLoader.loadNews();
                }
            }, 0);
        });

        // Make the collapse icons for the search groups
        $('.search-anchor').on('click',function(){
            var group = (this.id).split('-')[0];
            var icon = $('#' + group + '-icon');
            var div = $($(this).attr('href'));

            if (div.hasClass('collapse')){
                icon.removeClass('glyphicon-collapse-down');
                icon.addClass('glyphicon-collapse-up');
            } else if (div.hasClass('in')){
                icon.removeClass('glyphicon-collapse-up');
                icon.addClass('glyphicon-collapse-down');
            }
        });

        // Initially load news
        newsLoader.loadNews();

        // Make tooltips work
        $('[rel=tooltip]').tooltip();

        // Resize map controls on window resize
        $('#map-canvas').bind('DOMSubtreeModified resize', function() {
            map.resizeControls();
        });
    }

    //Retrieve the cookie that is created upon first visiting the website
    function getCookie(name) {
        var arg = name + "=";
        var argLength = arg.length;
        var cookieLength = document.cookie.length;
        var i = 0;
        while (i < cookieLength) {
            var j = i + argLength;
            if (document.cookie.substring(i, j) === arg)
                return "here";
            i = document.cookie.indexOf(" ", i) + 1;
            if (i === 0) break;
        }
        return null;
    }

    // Show modals
    function showOrganizationModal(data) {
        // Turn off regional news
        $('.btn-regional').removeClass('active');

        // Shows news based on the selected organization
        // Remove parentheses from organization name, get part of name before comma if necessary
        var alteredOrgName = data.name.replace(/ *\([^)]*\) */g, '');
        alteredOrgName = alteredOrgName.split(',')[0];
        var query = '"' + alteredOrgName + '"';
        newsLoader.loadNews(query, alteredOrgName);

        if (data.latlng && data.latlng.length > 0 && data.latlng[0] && data.latlng[1]) {
            map.showInfo(data);
        }
        else {
            Modal.createModal(data, '#bs-modal', '#bs-org-modal-template');
        }
    }

    function showContactModal(data) {
        Modal.createModal(data, '#bs-modal', '#' + data['type'] + '-modal-template');
    }

    function showPublicationModal(data) {
        if(!data.content_url) {
            data.url_name = 'Google Scholar'
            data.content_url = "http://scholar.google.com/scholar?hl=en&q="+data.title.replace(/\s/g, '+');
        }
        else {
            data.url_name = data.content_url.substring(0,30) + (data.content_url.length > 30 ? '...' : '');
        }

        Modal.createModal(data, '#bs-modal', '#publication-modal-template');
    }

    $(function() {
       initialize();
    });
});
