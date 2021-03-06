/**
 * Provides an interface for performing searches against the database.
 *
 * @module searchquery
 */
define(['underscore', 'jquery', 'jquery-ui', 'jquery.slinky'], function(_, $) {
    var lastSearchedText;

    var searchBox = $('#search-box');
    var searchResultsContainer = $('#search-results-div');
    var searchResultsDivScroll = $('#search-results-div-scroll');

    // Focus search box when typing
    $(document).keypress(function() {
        searchBox.focus();
    });

    // Focus search box when hovering over search results
    searchResultsContainer.hover(function() {
        searchBox.focus();
    });

    // Clear and blur search box using escape
    $(document).keydown(function(e) {
        if(e.keyCode === $.ui.keyCode.ESCAPE) {
            searchBox.val('').blur();
        }
    });

    // Hover to select search result
    $(document).on('mouseenter', '#search-results-div li', function() {
        searchResultsContainer.find('li').removeClass('active');
        $(this).addClass('active');
    });

    searchResultsContainer.slinky();

    $('#search-results-div-scroll > .panel > .panel-heading').click(function() {
        var count = $.inArray(this, $('#search-results-div-scroll > .panel:visible > .panel-heading'));
        var paddingTop = $(this).parent().innerHeight() - $(this).parent().height();
        $(this).parent().parent().scrollTop($(this).parent().parent().scrollTop() +
            ($(this).parent().position().top - (paddingTop * count)));
    });

    // Move within search results by using up/down keys
    // Click link using enter
    searchBox.keydown(function(e) {
        if(e.keyCode === $.ui.keyCode.UP) {
            moveSelection(-1);
            e.preventDefault();
        } else if(e.keyCode === $.ui.keyCode.DOWN) {
            moveSelection(+1);
            e.preventDefault();
        } else if(e.keyCode === $.ui.keyCode.ENTER) {
            clickSelection();
        }
    });

    // Set the result selection index
    function setSelection(index) {
        var visibleResults = searchResultsContainer.find('.panel:visible li');
        var resultCount = visibleResults.length || 1;

        index = ((index % resultCount) + resultCount) % resultCount;

        var selection = visibleResults.eq(index);

        visibleResults.removeClass('active');
        selection.addClass('active');

        if(selection.length) {
           // Scroll to selection
            var top = selection.offset().top - searchResultsDivScroll.offset().top - searchResultsDivScroll.height() / 2
                + selection.height() / 2 + searchResultsDivScroll.scrollTop();
            searchResultsDivScroll.animate({ scrollTop: top }, { duration: 200, queue: false });
        }
    }

    // Move the result selection index by an amount (usually +/- 1)
    function moveSelection(amount) {
        var visibleResults = searchResultsContainer.find('.panel:visible li');
        var index = visibleResults.index(searchResultsContainer.find('li.active'));
        index += amount;
        setSelection(index);
    }

    // Click the current selection
    function clickSelection() {
        searchResultsContainer.find('li.active').find('a').click();
    }

    /**
     * Performs a search against the Mongo database.
     *
     * @param {string} searchText The search text.
     * @param {object} searchItems A set of search items to be used for displaying results.
     * @param {object} map The Google Map object associated with the search.
     * @param {boolean} reload Whether or not to reload results for the same query.
     */
    function search(searchText, searchItems, map, reload) {
        if (!reload && lastSearchedText === searchText)
            return;
        lastSearchedText = searchText;

        map.removeAllMarkers();

        var searchDiv = $("#search-box-div");
        if (searchText) {
            searchDiv.css("pointer-events", "auto");

            // Perform each search
            _.each(searchItems, function(searchItem) {
                // See if we want to search for this item
                var shouldSearch = $(':checkbox:checked[data-search=' + searchItem.name + ']').length > 0;
                if(shouldSearch) {
                    var searchQuery = searchBox.val();
                    // Search begin
                    startAjaxSearch();
                    // See if we should do a custom search or just an ajax call
                    var searchFn = searchItem.search || ajaxSearch;
                    // Retrieve search results
                    searchFn(searchQuery, function(results) {
                        // Show search results for this item
                        displaySearchResults(searchItem, results, map);
                        // Search end
                        endAjaxSearch();
                        // Select first result
                        setSelection(0);
                    }, searchItem, function(fail) {
                        // Search end
                        endAjaxSearch();
                    });
                } else {
                    // Hide panel
                    $(searchItem.toggleSelector).closest('.panel').hide();
                }
            });
            searchResultsContainer.slideDown();
        } else {
            searchDiv.css("pointer-events", "none");
            searchResultsContainer.slideUp();
        }
    }

    // Default ajax search function
    function ajaxSearch(searchQuery, ready, searchItem, fail) {
        // Do an ajax call with the given url
        $.ajax({
            type: 'GET',
            url: searchItem.url,
            data: {
                'search_text': searchQuery,
                'csrfmiddlewaretoken': $('input[name=csrfmiddlewaretoken]').val()
            },
            dataType: 'html'
        }).done(function(data) {
            var results = JSON.parse(data).results;
            ready(results);
            $('.empty-panel').text('No Results');
        }).fail(function(data) {
            console.log(searchItem.name, 'search failed');
                $('.empty-panel').text('Error occurred: HTTP '+data.status);
            fail(data);
            ready([]);
        });
    }

    // Display search results for a specific type of item
    function displaySearchResults(searchItem, results, map) {
        // Clear previous results
        $(searchItem.listSelector).html('');
        // Show number of results
        var resultCount = results.length;
        var resultsString = resultCount
            + ' result'
            + (resultCount == 1 ? '' : 's');
        $(searchItem.toggleSelector).find('.count').text(resultsString);
        // Hide or show panel based on availability of results
        if(resultCount) {
            // Show panel
            $(searchItem.toggleSelector).closest('.panel').show();
            // Display results
            _.each(results, function(item) {
                $('<a>' + searchItem.linkText(item) + '</a>')
                    .addClass(searchItem.linkClass)
                    .attr('href', 'javascript:void(0)')
                    .click(function() {
                        if(searchItem.onclick) {
                            searchItem.onclick(item);
                        }
                    })
                    .data(item)
                    .wrap('<li></li>')
                    .parent()
                    .appendTo(searchItem.listSelector);

                map.plotMarker(item);
            });
            if (results.length) {
                $(searchItem.toggleSelector).closest('.panel').show();
            } else {
                $(searchItem.toggleSelector).closest('.panel').hide();
            }
            $(searchItem.toggleSelector).click(function (e) {
                e.preventDefault();
            });
            $('.modal').modal({ show: false });
        } else {
            // Hide panel
            $(searchItem.toggleSelector).closest('.panel').hide();
        }
        checkForResults();
    }

    function checkForResults() {
        var check = $('.search-results-panel').is(':visible');
        if(!check) {
            $('.empty-panel').show();
        }
        else {
            $('.empty-panel').hide();
        }
    }

    //Display the loading indicator if searches are pending
    var searchesPending = 0;
    function startAjaxSearch() {
        searchesPending++;
        if (searchesPending === 1) {
            $('#search-ajax-loader').removeClass('hidden');
        }
    }

    //Similarly, hide the loading indicator if no searches are pending
    function endAjaxSearch() {
        searchesPending--;
        if (searchesPending === 0) {
            $('#search-ajax-loader').addClass('hidden');
        }
    }

    return { search: search };
});