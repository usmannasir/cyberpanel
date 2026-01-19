/* Carousel */

$(document).ready(function() {

    $(".owl-carousel-1").owlCarousel({
        lazyLoad: true,
        items: 4,
        navigation: true,
        navigationText: ["<i class='glyph-icon icon-angle-left'></i>", "<i class='glyph-icon icon-angle-right'></i>"],
    });

    $(".owl-carousel-2").owlCarousel({
        lazyLoad: true,
        itemsCustom: [
            [0, 2],
            [450, 4],
            [600, 7],
            [700, 9],
            [1000, 10],
            [1200, 12],
            [1400, 13],
            [1600, 15]
        ],
        navigation: true,
        navigationText: ["<i class='glyph-icon icon-angle-left'></i>", "<i class='glyph-icon icon-angle-right'></i>"],
    });

    $(".owl-carousel-3").owlCarousel({
        lazyLoad: true,
        autoPlay: 3000,
        items: 2,
        stopOnHover: true,
        navigation: true,
        navigationText: ["<i class='glyph-icon icon-angle-left'></i>", "<i class='glyph-icon icon-angle-right'></i>"],
        paginationSpeed: 1000,
        goToFirstSpeed: 2000,
        singleItem: false,
        autoHeight: true,
        transitionStyle: "goDown"
    });

    $(".owl-carousel-4").owlCarousel({
        lazyLoad: true,
        autoPlay: 3000,
        items: 2,
        stopOnHover: true,
        navigation: false,
        paginationSpeed: 1000,
        goToFirstSpeed: 2000,
        singleItem: false,
        autoHeight: true,
        pagination: false,
        transitionStyle: "goDown"
    });

    $(".owl-carousel-5").owlCarousel({
        lazyLoad: true,
        autoPlay: 3000,
        items: 3,
        stopOnHover: true,
        navigation: false,
        paginationSpeed: 1000,
        goToFirstSpeed: 2000,
        singleItem: false,
        autoHeight: true,
        pagination: false,
        transitionStyle: "goDown"
    });

    $(".next").click(function() {
        owl.trigger('owl.next');
    })
    $(".prev").click(function() {
        owl.trigger('owl.prev');
    })

    $(".owl-slider-1").owlCarousel({
        lazyLoad: true,
        autoPlay: 3000,
        stopOnHover: true,
        navigation: true,
        navigationText: ["<i class='glyph-icon icon-angle-left'></i>", "<i class='glyph-icon icon-angle-right'></i>"],
        paginationSpeed: 1000,
        goToFirstSpeed: 2000,
        singleItem: true,
        autoHeight: true,
        transitionStyle: "goDown"
    });

    $(".owl-slider-2").owlCarousel({
        lazyLoad: true,
        autoPlay: 3000,
        stopOnHover: true,
        navigation: true,
        navigationText: ["<i class='glyph-icon icon-angle-left'></i>", "<i class='glyph-icon icon-angle-right'></i>"],
        paginationSpeed: 1000,
        goToFirstSpeed: 2000,
        singleItem: true,
        autoHeight: true,
        transitionStyle: "fade"
    });

    $(".owl-slider-3").owlCarousel({
        lazyLoad: true,
        autoPlay: 3000,
        stopOnHover: true,
        navigation: false,
        navigationText: ["<i class='glyph-icon icon-angle-left'></i>", "<i class='glyph-icon icon-angle-right'></i>"],
        paginationSpeed: 1000,
        goToFirstSpeed: 2000,
        singleItem: true,
        autoHeight: false
    });

    $(".owl-slider-4").owlCarousel({
        lazyLoad: true,
        autoPlay: 3000,
        stopOnHover: true,
        navigation: true,
        navigationText: ["<i class='glyph-icon icon-angle-left'></i>", "<i class='glyph-icon icon-angle-right'></i>"],
        paginationSpeed: 1000,
        goToFirstSpeed: 2000,
        singleItem: true,
        autoHeight: false
    });

    $(".owl-slider-5").owlCarousel({
        lazyLoad: true,
        autoPlay: 3000,
        stopOnHover: true,
        navigation: false,
        paginationSpeed: 1000,
        goToFirstSpeed: 2000,
        singleItem: true,
        autoHeight: true,
        transitionStyle: "goDown"
    });
});
