let websocket;
const MAX_LIST_ITEMS = 10;
const SELECTED_COLOR = 'gold';
let service_list;
let service_sort_start;
let clicked_service_item;
let action_after_save;
let screen_state;
let icon_dict = {};
icon_dict["bible"] = "/html/icons/icons8-literature-48.png";
icon_dict["song"] = "/html/icons/icons8-musical-notes-48.png";
icon_dict["presentation"] = "/html/icons/icons8-presentation-48.png";
icon_dict["video"] = "/html/icons/icons8-tv-show-48.png";

function change_screen_state_flip(){
    str_state = ($('#flip_screen_state').prop("checked") === true) ? "on" : "off";
    websocket.send(JSON.stringify({"action": "command.set-display-state", "params": {"state": str_state}}));
}

function add_verses(){
    verses = $('input[name=v_list]:checked');
    version = $('#select_b_version').val();
    if (verses.length > 0){
        let range_start = $(verses[0]).attr('id').substr(2);
        let prev_id = range_start - 1;
        let v_id;
        for(v=0; v<verses.length; v++){
            v_id = $(verses[v]).attr('id').substr(2);
            if (v_id - prev_id == 1){
                // Range continues from previous verse
                prev_id = v_id;
            } else {
                // Entering new range, so close old one and add that to the service
                websocket.send(JSON.stringify({
                    "action": "command.add-bible-item",
                    "params": {
                        "version": version,
                        "start-verse": range_start,
                        "end-verse": prev_id
                    }
                }));
                range_start = v_id;
                prev_id = v_id;
            }
        }
        // Add final range to the service
        websocket.send(JSON.stringify({
            "action": "command.add-bible-item",
            "params": {
                "version": version,
                "start-verse": range_start,
                "end-verse": v_id
            }
        }));
    }
}

function select_all_verses(){
    $('#passage_list input[type="checkbox"]').prop("checked", true).checkboxradio('refresh');
}

function select_none_verses(){
    $('#passage_list input[type="checkbox"]').prop("checked", false).checkboxradio('refresh');
}

function load_service_preload(){
    websocket.send(JSON.stringify({"action":"request.all-services", "params": {}}));
}

function load_service(force){
    sel_radio = $('input[name=files]:checked').attr('id');
    sel_text = $('label[for=' + sel_radio + ']').text();
    websocket.send(JSON.stringify({
        "action":"command.load-service", 
        "params":{"filename": sel_text, "force": force}
    }));
}

function save_service_as(elt){
    f_name = $(elt).val();
    // TODO: Add extra input sanitization here...
    if (f_name.endsWith(".json") == false){
        f_name += ".json";
    }
    websocket.send(JSON.stringify({
        "action": "command.save-service-as", 
        "params": {"filename": f_name}
    }));
    // Reset input for next time
    $(elt).val("");
}

function save_service(action_after){
    action_after_save = action_after;
    websocket.send(JSON.stringify({"action": "command.save-service", "params": {}}));
}

function delete_item(){
    websocket.send(JSON.stringify({"action": "command.remove-item", "params": {"index": clicked_service_item}}));
}

function next_item(){
    websocket.send(JSON.stringify({"action": "command.next-item", "params": {}}));
}

function previous_item(){
    websocket.send(JSON.stringify({"action": "command.previous-item", "params": {}}));
}

function goto_item(){
    websocket.send(JSON.stringify({"action": "command.goto-item", "params": {"index": clicked_service_item}}));
}

function next_slide(){
    websocket.send(JSON.stringify({"action": "command.next-slide", "params": {}}));
}

function previous_slide(){
    websocket.send(JSON.stringify({"action": "command.previous-slide", "params": {}}));
}

function goto_slide(idx){
    websocket.send(JSON.stringify({"action": "command.goto-slide", "params": {"index": idx}}));
}

function song_search(){
    websocket.send(JSON.stringify({"action": "query.song-by-text", "params": {"search-text": $('#song_search').val()}}));
}

function bible_search(){
    if ($('input[name=b_search_type]:checked').attr('id') == "b_search_type_ref"){
        websocket.send(JSON.stringify({
            "action": "query.bible-by-ref",
            "params": {
                "version": $('#select_b_version').val(),
                "search-ref": $('#bible_search').val()
        }}));
    } else {
        websocket.send(JSON.stringify({
            "action": "query.bible-by-text",
            "params": {
                "version": $('#select_b_version').val(),
                "search-text": $('#bible_search').val()
        }}));
    }
}

function new_service(force){
    websocket.send(JSON.stringify({"action": "command.new-service", "params": {"force": force}}));
}

function add_song(song_id){
    websocket.send(JSON.stringify({"action": "command.add-song-item", "params": {"song-id": song_id}}));
}

function add_video(elt){
    websocket.send(JSON.stringify({"action": "command.add-video", "params": {"url": $(elt).children().first().html()}}));
}

function add_presentation(elt){
    websocket.send(JSON.stringify({"action": "command.add-presentation", "params": {"url": $(elt).children().first().html()}}));
}

function toggle_display_state(){
    if (screen_state === "on"){
        websocket.send(JSON.stringify({"action": "command.set-display-state", "params": {"state": "off"}}));
    } else {
        websocket.send(JSON.stringify({"action": "command.set-display-state", "params": {"state": "on"}}));
    }
}

function display_current_item(current_item, slide_index){
    let current_item_header = '';
    current_item_header += "<li><img class='ui-li-icon' src='" + icon_dict[current_item.type] + "' />";
    current_item_header += current_item.title + "</a></li>";
    $("#current_item_title").html(current_item_header);
    $("#current_item_title").listview('refresh');

    let item_list = "";
    for (let slide in current_item.slides){
        if (current_item.type == "song"){
            slide_lines = current_item.slides[slide].split(/\n/);
            slide_text = "<p style='white-space:normal;'>";
            for (line in slide_lines){
              line_segments = slide_lines[line].split(/\[[\w\+#\/"='' ]*\]/);
              for (let segment=0; segment < line_segments.length; segment++){
                slide_text += line_segments[segment];
              }
              slide_text += "<br />";
            }
            slide_text += "</p>";
        } else if (current_item.type == "presentation"){
            slide_text = "<img style='width:50%;' src='" + current_item.slides[slide] + "' />";
        } else {
            slide_text = "<p style='white-space:normal;'>" + current_item.slides[slide] + "</p>";
        }
        item_list += "<li data-icon='false'><a class='i-item' data-id=" + slide + " href='#'>" + slide_text + "</a></li>"
    }
    $("#current_item_list").html(item_list);
    $("#current_item_list").listview('refresh');
    $("#current_item_list a.i-item").on('click', function(event, ui){
        goto_slide($(this).data('id'));
    });

    // Indicate selection of slide_index
    indicate_current_slide(slide_index);
}

function indicate_current_slide(slide_index){
    $("#current_item_list li a.i-item").css('background-color', '');
    if (slide_index != -1){
        $("#current_item_list li:nth-child(" + (slide_index+1) + ") a.i-item").css('background-color', SELECTED_COLOR);
    }
}

function indicate_current_item(item_index){
    $("#service_list li a.s-item").css('background-color', '');
    if (item_index != -1){
        $("#service_list li:nth-child(" + (item_index+1) + ") a.s-item").css('background-color', SELECTED_COLOR);
    }
}

$(document).ready(function(){
    $("#elements_area").tabs();
    $("#service_list").sortable();
    $("#service_list").on("sortstart", function(event, ui){
        service_sort_start = ui.item.index();
    });
    $("#service_list").on("sortupdate", function(event, ui){
        websocket.send(JSON.stringify({
            "action": "command.move-item",
            "params": {"from-index": service_sort_start, "to-index": ui.item.index()}
        }));
    });

    websocket = new WebSocket("ws://" + window.location.hostname + ":9001/app");
    websocket.onmessage = function (event) {
        json_data = JSON.parse(event.data);
        switch(json_data.action){
            case "update.app-init":
                screen_state = json_data.params.screen_state;
                bool_screen_state = (screen_state === "on") ? true : false;
                $('#flip_screen_state').off();
                $('#flip_screen_state').prop('checked', bool_screen_state).flipswitch('refresh');
                $('#flip_screen_state').on('change', change_screen_state_flip);
                
                // Populate service plan list
                service_list = "";
                for (let item in json_data.params.items){
                    service_list += "<li><a class='s-item' data-id=" + item + " href='#'>";
                    service_list += "<img class='ui-li-icon' src='" + icon_dict[json_data.params.items[item].type] + "' />";
                    service_list += json_data.params.items[item].title + "</a>";
                    service_list += "<a class='popup-trigger' href='#popup_service_item_options' data-id=" + item + " data-rel='popup'></li>";
                }
                $("#service_list").html(service_list);
                $("#service_list").listview('refresh');
                $("#service_list a.popup-trigger").on('click', function(event, ui){
                    clicked_service_item = $(this).data('id');
                });
                $("#service_list a.s-item").on('dblclick', function(event, ui){
                    clicked_service_item = $(this).data('id');
                    goto_item();
                });
                
                indicate_current_item(json_data.params.item_index);

                // Populate current item title and list
                // TODO: Deal with case of item_index = -1
                current_item = json_data.params.items[json_data.params.item_index];
                display_current_item(current_item, json_data.params.slide_index);

                // Populate Presentation and Video lists
                websocket.send(JSON.stringify({"action": "request.all-presentations", "params": {}}));
                websocket.send(JSON.stringify({"action": "request.all-videos", "params": {}}));

                // Populate Bible version list
                websocket.send(JSON.stringify({"action": "request.bible-versions", "params": {}}));
                break;

            case "update.service-overview-update":
                // Populate service plan list
                service_list = "";
                for (let idx in json_data.params.items){
                    service_list += "<li><a class='s-item' href='#' data-id=" + idx + ">";
                    service_list += "<img class='ui-li-icon' src='" + icon_dict[json_data.params.types[idx]] + "' />";
                    service_list += json_data.params.items[idx] + "</a>";
                    service_list += "<a class='popup-trigger' href='#popup_service_item_options' data-id=" + idx + " data-rel='popup'></li>";
                }
                $("#service_list").html(service_list);
                $("#service_list").listview('refresh');
                $("#service_list a.popup-trigger").on('click', function(event, ui){
                    clicked_service_item = $(this).data('id');
                });
                $("#service_list a.s-item").on('dblclick', function(event, ui){
                    clicked_service_item = $(this).data('id');
                    goto_item();
                });

                indicate_current_item(json_data.params.item_index);

                // Populate current item list
                display_current_item(json_data.params.current_item, json_data.params.slide_index);
                break;

            case "update.slide-index-update":
                indicate_current_slide(json_data.params.slide_index);
                break;

            case "update.item-index-update":
                indicate_current_item(json_data.params.item_index);
                display_current_item(json_data.params.current_item, json_data.params.slide_index);
                break;

            case "update.display-state":
                screen_state = json_data.params.state;
                bool_screen_state = (screen_state === "on") ? true : false;
                $('#flip_screen_state').off();
                $('#flip_screen_state').prop('checked', bool_screen_state).flipswitch('refresh');
                $('#flip_screen_state').on('change', change_screen_state_flip);
                break;

            case "result.all-presentations":
                let pres_list = "";
                for (let url in json_data.params.urls){
                    pres_list +="<li data-icon='plus'><a href='#'>" + json_data.params.urls[url] + "</a>";
                    pres_list += "<a onclick='add_presentation($(this).parent());' href='javascript:void(0);'></li>";
                }
                $("#presentation_list").html(pres_list);
                $("#presentation_list").listview('refresh');
                break;

            case "result.all-videos":
                let vid_list = "";
                for (let url in json_data.params.urls){
                    vid_list +="<li data-icon='plus'><a href='#'>" + json_data.params.urls[url] + "</a>";
                    vid_list += "<a onclick='add_video($(this).parent());' href='javascript:void(0);'></li>";
                }
                $("#video_list").html(vid_list);
                $("#video_list").listview('refresh');
                break;

            case "response.new-service":
                if (json_data.params.status == "unsaved-service"){
                    $('#popup_new_service').popup('open');
                }
                break;

            case "response.load-service":
                if (json_data.params.status == "unsaved-service"){
                    $('#popup_save_before_load_service').popup('open');
                }
                // TODO: Deal with other errors
                break;

            case "result.song-titles":
                let song_list = "";
                for (let song in json_data.params.songs){
                    if (song == MAX_LIST_ITEMS) {
                        song_list += "<li>There are more items...</li>"
                        break;
                    }
                    song_list += "<li data-icon='plus'><a href='#'>" + json_data.params.songs[song][1] + "</a>";
                    song_list += "<a onclick='add_song(" + json_data.params.songs[song][0] + ");' href='javascript:void(0);'></li>";
                }
                $("#song_list").html(song_list);
                $("#song_list").listview('refresh');
                break;

            case "response.save-service":
                if (json_data.params.status == "unspecified-service"){
                    $('#popup_save_service_as').popup('open');
                } else {
                    // Save has been successful
                    if (action_after_save == 'new'){
                        action_after_save = 'none';
                        new_service(true);
                    } else if (action_after_save == 'load'){
                        action_after_save = 'none';
                        load_service(true);
                    }
                }
                break;

            case "result.all-services":
                $('#load_files_radio div').html('');
                for (let file in json_data.params.filenames){
                    $('#load_files_radio div').append('<input type="radio" name="files" id="files-' + file + '">');
                    $('#load_files_radio div').append('<label for="files-'+ file +'">' + json_data.params.filenames[file] + '</label>');
                }
                $('#load_files_radio input[type="radio"]').checkboxradio();
                $('#files-0').prop("checked", true).checkboxradio('refresh');  // Select item 0
                // TODO: Case of no files params.filenames
                $('#load_files_radio').controlgroup('refresh');
                $('#popup_load_service').popup('open');
                break;

            case "result.bible-versions":
                $('#select_b_version').html('');
                for (let v in json_data.params.versions){
                    $('#select_b_version').append('<option value="' + json_data.params.versions[v] + '">' + json_data.params.versions[v] + '</option>');
                }
                $('#select_b_version').val(json_data.params.versions[0]).change()
                break;

            case "result.bible-verses":
                $('#passage_list div').html('');
                for (let v in json_data.params.verses){
                    verse = json_data.params.verses[v];
                    bible_ref = verse[1] + " " + verse[2] + ":" + verse[3];
                    $('#passage_list div').append('<input type="checkbox" data-mini="true" checked="checked" name="v_list" id="v-' + verse[0] + '">');
                    $('#passage_list div').append('<label for="v-'+ verse[0] +'">' + bible_ref + ": " + verse[4] + '</label>');
                }
                $('#passage_list input[type="checkbox"]').checkboxradio();
                $('#passage_list').controlgroup('refresh');
                break;

            case "response.add-song-item":
            case "response.move-item":
            case "response.next-item":
            case "response.previous-item":
            case "response.goto-item":
            case "response.next-slide":
            case "response.previous-slide":
            case "response.goto-slide":
            case "response.remove-item":
            case "response.set-display-state":
            case "response.add-video":
            case "response.add-presentation":
            case "response.add-bible-item": // Error handling required?
                break;  // No action required;
            default:
                console.error("Unsupported event", json_data);
        }
    }
});

$(document).on('keypress', function(e){
    key_code = e.which ? e.which : e.keyCode;
    let tag = e.target.tagName.toLowerCase();
    if (tag != 'input' && tag != 'textarea'){
        switch(key_code){
            case 38: // Up arrow
                previous_slide();
                break;
            case 40: // Down arrow
                next_slide();
                break;
            case 33: // PG_UP
                previous_item();
                break;
            case 34: // PG_DOWN
                next_item();
                break;
            case 84: // T
            case 116: // t
                toggle_display_state();
                break;
        }
    }
})