$(document).ready(function () {
    //$('#inneriframe').attr('src', 'http://events.hackerdojo.com/');
    //loads the iframe after the rest of the page is loaded
    var test = true;
    if (test == true){
        $(".join").hide();
    }
    $( ".close_button" ).click(function(e) {
        //this button closes the "join hackerdojo" popin
        e.preventDefault();
        $(".join").hide();
    });
    $(window).scroll(function() {
    // this function calculates where the scrollbar is and then shows or hide the "join hackerdojo" popin
        var scrollPosition = window.pageYOffset;
        var windowSize     = window.innerHeight;
        var bodyHeight     = document.body.offsetHeight;
        if ($(window).scrollTop() > 50) { // > 100px from top - show div
            $(".join").addClass('visible');
        }
        else { // <= 100px from top - hide div
            $(".join").removeClass('visible');
        }
        if ((Math.max(bodyHeight - (scrollPosition + windowSize), 0) < 10)) {
        //scroll distance to bottom - hides to show footer
            $(".join").removeClass('visible');
        }
    });
});