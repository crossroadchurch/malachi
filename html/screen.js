let websocket;
let current_item;

function display_current_slide(slide_index){
    current_slide = current_item.slides[slide_index];
    if (current_item.type == "song"){
        slide_lines = current_slide.split(/\n/);
        slide_text = "<p>";
        for (line in slide_lines){
            line_segments = slide_lines[line].split(/\[[\w\+#\/"='' ]*\]/);
            for (let segment=0; segment < line_segments.length; segment++){
            slide_text += line_segments[segment];
            }
            slide_text += "<br />";
        }
        slide_text += "</p>";
    } else if (current_item.type == "presentation"){
        slide_text = "";
    } else if (current_item.type == "video"){
        slide_text = "";
    } else {
        slide_text = "<p>" + current_slide + "</p>";
    }
    $('#slide_area').html(slide_text);
}

$(document).ready(function(){
    websocket = new WebSocket("ws://" + window.location.hostname + ":9001/display");
    websocket.onmessage = function (event) {
        json_data = JSON.parse(event.data);
        console.log(json_data);
        switch(json_data.action){
            case "update.display-init":
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

            default:
                console.error("Unsupported event", json_data);
        }
    }
});