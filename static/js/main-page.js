$(document).ready(function () {
    //$(".right-span").load("http://events.hackerdojo.com #primary");
    $('#inneriframe').attr('src', 'http://events.hackerdojo.com/');
    var test = true;
    if (test == true){
        $(".join").hide();
    }
    $( ".close_button" ).click(function(e) {
        e.preventDefault();
        $(".join").hide();
    });
    $(window).scroll(function() {
        var scrollPosition = window.pageYOffset;
        var windowSize     = window.innerHeight;
        var bodyHeight     = document.body.offsetHeight;
        if ($(window).scrollTop() > 50) { // > 100px from top - show div
            $(".join").addClass('visible');
        }
        else { // <= 100px from top - hide div
            $(".join").removeClass('visible');
        }
        if ((Math.max(bodyHeight - (scrollPosition + windowSize), 0) < 10)) { // scroll from bottom - hides to show footer
            $(".join").removeClass('visible');
        }
    });
});