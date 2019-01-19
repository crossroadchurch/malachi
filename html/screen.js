var websocket;
var current_item;
var loop_width = 0;
var loop_height = 0;
var loop_ar = 0;

function display_current_slide(slide_index){
    current_slide = current_item.slides[slide_index];
    if (current_item.type == "song"){
        stop_running_video();
        slide_lines = current_slide.split(/\n/);
        slide_text = "<p>";
        for (line in slide_lines){
            line_segments = slide_lines[line].split(/\[[\w\+#\/"='' ]*\]/);
            for (var segment=0; segment < line_segments.length; segment++){
            slide_text += line_segments[segment];
            }
            slide_text += "<br />";
        }
        slide_text += "</p>";
    } else if (current_item.type == "presentation"){
        stop_running_video();
        slide_text = "";
    } else if (current_item.type == "video"){
        slide_text = "";
        // Background load video, wait for trigger to display and start playback
        resize_video_item();
        $('#video_item_src').attr('src', current_item.url);
        $('#video_item').load();
    } else {
        stop_running_video();
        slide_text = "<p>" + current_slide + "</p>";
    }
    $('#slide_area').html(slide_text);
}

function stop_running_video(){
    document.getElementById('video_item').pause();
    $('#loop_video').css('display', 'block');
    $('#video_item').css('display', 'none');
}

function resize_video_item(){
    video_ar = current_item.video_width / current_item.video_height;
    screen_ar = window.innerWidth / window.innerHeight;
    if (video_ar <= screen_ar){
        left_pos = window.innerWidth * 0.5 * (1 - (video_ar/screen_ar));
        $('#video_item').css('height', '100%');
        $('#video_item').css('width', 'auto');
        $('#video_item').css('top', '0');
        $('#video_item').css('left', left_pos);
    } else {
        top_pos = window.innerHeight * 0.5 * (1 - (screen_ar/video_ar));
        $('#video_item').css('height', 'auto');
        $('#video_item').css('width', '100%');
        $('#video_item').css('top', top_pos);
        $('#video_item').css('left', '0');
    }
}

function resize_loop(){
    if (loop_height > 0){
        screen_ar = window.innerWidth / window.innerHeight;
        if (screen_ar <= loop_ar){
            left_pos = window.innerWidth * -0.5 * ((loop_ar/screen_ar)-1);
            $('#loop_video').css('height', '100%');
            $('#loop_video').css('width', 'auto');
            $('#loop_video').css('top', 0);
            $('#loop_video').css('left', left_pos);
        } else {
            top_pos = window.innerHeight * -0.5 * ((screen_ar/loop_ar)-1);
            $('#loop_video').css('height', 'auto');
            $('#loop_video').css('width', '100%');
            $('#loop_video').css('top', top_pos);
            $('#loop_video').css('left', 0);
        }
    }
}

function update_from_style(style){
    div_width = style["div-width-vw"];
    $('#slide_area').css("width", div_width + "vw");
    $('#slide_area').css("margin-left", ((100-div_width)/2) + "vw");
    $('#slide_area').css("margin-top", style["margin-top-vh"] + "vh");
    $('#slide_area').css("font-size", style["font-size-vh"] + "vh");
}

$(document).ready(function(){
    websocket = new WebSocket("ws://" + window.location.hostname + ":9001/display");
    websocket.onmessage = function (event) {
        json_data = JSON.parse(event.data);
        console.log(json_data);
        switch(json_data.action){
            case "update.display-init":
                if (json_data.params["video_loop"] !== ""){
                    $('#loop_video_src').attr('src', json_data.params["video_loop"]);
                    $('#loop_video').load();
                    loop_height = json_data.params["loop-height"];
                    loop_width = json_data.params["loop-width"];
                    loop_ar = loop_width / loop_height;
                    resize_loop();
                } else {
                    $('#loop_video_src').attr('src', '');
                    $('#loop_video').load();
                    loop_height = 0;
                    loop_width = 0;
                    loop_ar = 0;
                }
                update_from_style(json_data.params.style);
                if (json_data.params.screen_state == "on"){
                    $('#slide_area').css("display", "block");
                } else {
                    $('#slide_area').css("display", "none");
                }
                current_item = json_data.params.current_item;
                if (json_data.params.item_index != -1){
                    display_current_slide(json_data.params.slide_index);
                }
                break;

            case "update.style-update":
                update_from_style(json_data.params.style);
                break;

            case "update.service-overview-update":
            case "update.item-index-update":
                current_item = json_data.params.current_item;
                if (json_data.params.item_index != -1){
                    display_current_slide(json_data.params.slide_index);
                }
                break;

            case "update.slide-index-update":
                display_current_slide(json_data.params.slide_index);
                break;

            case "update.display-state":
                if (json_data.params.state == "on"){
                    $('#slide_area').css("display", "block");
                } else {
                    $('#slide_area').css("display", "none");
                }
                break;

            case "update.video-loop":
                if (json_data.params.url !== ""){
                    $('#loop_video_src').attr('src', json_data.params.url);
                    $('#loop_video').load();
                    loop_height = json_data.params["loop-height"];
                    loop_width = json_data.params["loop-width"];
                    loop_ar = loop_width / loop_height;
                    resize_loop();
                } else {
                    $('#loop_video_src').attr('src', '');
                    $('#loop_video').load();
                    loop_height = 0;
                    loop_width = 0;
                    loop_ar = 0;
                }
                break;

            case "trigger.play-video":
                $('#video_item').css('display', 'block');
                $('#loop_video').css('display', 'none');
                document.getElementById('video_item').play();
                break;

            case "trigger.pause-video":
                document.getElementById('video_item').pause();
                break;

            case "trigger.stop-video":
                stop_running_video();
                document.getElementById('video_item').currentTime = 0.0;
                break;

            case "trigger.seek-video":
                document.getElementById('video_item').currentTime = json_data.params.seconds;
                break;

            default:
                console.error("Unsupported event", json_data);
        }
    }

    // Mute foreground video element based on ?muted=true,false parameter, if it exists
    params = window.location.search.slice(1);
    video_muted = false;
    if (params != ""){
        param_arr = params.split('&');
        for(var i=0; i<param_arr.length; i++){
            param_pair = param_arr[i].split('=');
            if (param_pair[0] == 'muted'){
                video_muted = param_pair[1] == 'true';
            }
        }
    }
    $('#video_item').prop('muted', video_muted);
});

$(window).resize(function(){
    if (current_item.type == "video"){
        resize_video_item();
    }
    resize_loop();
});