$(function() {

    var $container = $('.isotope').imagesLoaded( function() {
        $container.isotope({
            itemSelector: '.item',
            layoutMode: 'masonry',
            masonry: {
                columnWidth: '.col-lg-2'
            }
        });
    });

    $('#filters').on('click', 'a', function(event) {
        var filterValue = $(this).attr('data-filter-value');

        $('#filters a').removeClass('active');

        $(this).addClass('active');

        $container.isotope({
            filter: filterValue
        });
    });

});

$(function() {

    $('#portfolio-grid').mixitup({
        showOnLoad: 'hover_2'
    });

});
