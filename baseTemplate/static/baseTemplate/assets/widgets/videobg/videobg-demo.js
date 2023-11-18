$(function() {
    "use strict";
    $('.video-example-1').videoBG({
        mp4: '../assets/image-resources/video/tablet.mp4',
        ogv: '../assets/image-resources/video/tablet.ogv',
        webm: '../assets/image-resources/video/tablet.webm',
        //poster:'../assets/image-resources/dummy.jpg',
        scale: true,
        opacity: 1,
        position: "relative",
        height: '100%',
        width: '100%',
        zIndex: 0
    });
});

$(function() {
    "use strict";
    $('.video-example-2').videoBG({
        mp4: '../assets/image-resources/video/cars.mp4',
        ogv: '../assets/image-resources/video/cars.ogv',
        webm: '../assets/image-resources/video/cars.webm',
        //poster:'../assets/image-resources/dummy.jpg',
        scale: true,
        opacity: 1,
        position: "relative",
        height: '100%',
        width: '100%',
        zIndex: 0
    });
});

$(function() {
    "use strict";
    $('.video-example-3').videoBG({
        mp4: '../assets/image-resources/video/sun.mp4',
        ogv: '../assets/image-resources/video/sun.ogv',
        webm: '../assets/image-resources/video/sun.webm',
        //poster:'../assets/image-resources/dummy.jpg',
        scale: true,
        opacity: 1,
        position: "relative",
        height: '100%',
        width: '100%',
        zIndex: 0
    });
});

$(function() {
    "use strict";
    $('video,audio').each(function() {
        this.muted = true
    });
});
