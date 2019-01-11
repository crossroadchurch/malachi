var capo = 0;
var menustring = "";
var verse_order = "";
var played_key = "";
var slide_type = "";
var service_items = [];
var current_slides = [];
var part_counts = [];
var slide_index = -1;
var item_index = -1;
var websocket;

function update_music() {
  $("#playedkey").html(played_key);
  verse_control_list = "";
  verse_list = "";

  if (slide_type == "song"){
    verse_list = verse_order.split(" ");
    part_counts_sum = 0
    for (i=0; i < verse_list.length; i++){
      if ((slide_index >= part_counts_sum) && (slide_index < (part_counts_sum + part_counts[i]))) {
        verse_control_list = verse_control_list + 
          "<button class='verse-button current-verse-button' onclick='change_verse(" + part_counts_sum + ")'>" + 
          verse_list[i].toUpperCase() +
          "</button>";
      } else {
        verse_control_list = verse_control_list + 
          "<button class='verse-button' onclick='change_verse(" + part_counts_sum + ")'>" + 
          verse_list[i].toUpperCase() +
          "</button>";
      }
      part_counts_sum = part_counts_sum + part_counts[i];
    }
  } else if (slide_type != undefined) {
    verse_control_list = "<span class='non-song-title'>" + service_items[item_index] + "</span>";
  }
  $("#verseorder").html(verse_control_list);

  /* Update widths of verse buttons to make sure they can all be seen */
  header_width = $("#header").width();
  keyandcapo_width = $("#keyandcapo").width();
  button_margin = parseInt($(".verse-button").css("margin-right"));
  buttons_width = header_width-keyandcapo_width - (button_margin * verse_list.length);
  max_button_width = Math.floor(buttons_width / verse_list.length);
  pref_width = 6 * parseInt($("html").css("font-size")); /* 6rem */
  actual_width = Math.min(pref_width, max_button_width);
  $(".verse-button").css("width", actual_width + "px");

  if (slide_type == "song"){

    current_slide_lines = current_slides[slide_index].split(/(\n)/);
    current_text = '';

    for (line in current_slide_lines){
      if (current_slide_lines[line] == "\n"){
        current_text = current_text + '<br />';
      } else {
        current_line_segments = current_slide_lines[line].split(/(\[[\w\+#\/"='' ]*\])/);
        if (current_line_segments[0] != '') {
          // Process head of line
          current_text = current_text + '<span class="lyric-chord-block"><span class="lyric-chunk">' + current_line_segments[0] + '</span></span>';
        }
        // Process tail of line: <Tail> ::= (<Chord>|(<Chord><Lyric>))*
        prev_chunk_is_chord = false;
        hanging_lyric_pos = -1;
        for (segment=1; segment < current_line_segments.length; segment++){
          cur_seg = current_line_segments[segment];
          if (cur_seg.charAt(0) == "["){
            // Current is chord
            cur_seg = cur_seg.replace(/\[[\s]?/, '<span class="chord-chunk">');
            cur_seg = cur_seg.replace(/[\s]?\]/, "</span>");
            if (prev_chunk_is_chord == true) {
              current_text = current_text + '</span><span class="lyric-chord-block">' + cur_seg;
            } else {
              current_text = current_text + '<span class="lyric-chord-block">' + cur_seg;
            }
            prev_chunk_is_chord = true;
          } else {
            // Current is lyric
            if ((hanging_lyric_pos > 0) && (cur_seg.charAt(0).match(/[a-z]/i))) {
              current_text = current_text.slice(0, hanging_lyric_pos+1) + " midword" + current_text.slice(hanging_lyric_pos+1);
            }
            // recalc hanging_lyric_pos based on current_text length + offset
            hanging_lyric_pos = current_text.length + 23;
            current_text = current_text + '<span class="lyric-chunk">' + cur_seg + '</span></span>';
            prev_chunk_is_chord = false;
            if (!cur_seg.slice(-1).match(/[a-z]/i)){
              hanging_lyric_pos = -1;
            }
          }
        }
        if (prev_chunk_is_chord == true){
          current_text = current_text + '</span>';
        }
      }
    }
    $("#currentslide").html(current_text);

    if (slide_index < (current_slides.length - 1)){
      next_slide_lines = current_slides[slide_index + 1].split(/(\n)/);
    } else {
      next_slide_lines = [];
    }
    next_text = '';

    for (line in next_slide_lines){
      if (next_slide_lines[line] == "\n"){
        next_text = next_text + '<br />';
      } else {
        next_line_segments = next_slide_lines[line].split(/(\[[\w\+#\/"='' ]*\])/);
        if (next_line_segments[0] != '') {
          // Process head of line
          next_text = next_text + '<span class="next-lyric-chord-block"><span class="next-lyric-chunk">' + next_line_segments[0] + '</span></span>';
        }
        // Process tail of line: <Tail> ::= (<Chord>|(<Chord><Lyric>))*
        prev_chunk_is_chord = false;
        hanging_lyric_pos = -1;
        for (segment=1; segment < next_line_segments.length; segment++){
          cur_seg = next_line_segments[segment];
          if (cur_seg.charAt(0) == "["){
            // Current is chord
            cur_seg = cur_seg.replace(/\[[\s]?/, '<span class="next-chord-chunk">');
            cur_seg = cur_seg.replace(/[\s]?\]/, "</span>");
            if (prev_chunk_is_chord == true) {
              next_text = next_text + '</span><span class="next-lyric-chord-block">' + cur_seg;
            } else {
              next_text = next_text + '<span class="next-lyric-chord-block">' + cur_seg;
            }
            prev_chunk_is_chord = true;
          } else {
            // Current is lyric
            if ((hanging_lyric_pos > 0) && (cur_seg.charAt(0).match(/[a-z]/i))) {
              next_text = next_text.slice(0, hanging_lyric_pos+1) + " midword" + next_text.slice(hanging_lyric_pos+1);
            }
            // recalc hanging_lyric_pos based on current_text length + offset
            hanging_lyric_pos = next_text.length + 28;
            next_text = next_text + '<span class="next-lyric-chunk">' + cur_seg + '</span></span>';
            prev_chunk_is_chord = false;
            if (!cur_seg.slice(-1).match(/[a-z]/i)){
              hanging_lyric_pos = -1;
            }
          }
        }
        if (prev_chunk_is_chord == true){
          next_text = next_text + '</span>';
        }
      }
    }
    $("#nextslide").html(next_text);

    $('#currentslide>span').each(function(){
      element = $(this);
      if (element.children().length > 1){
        lyricWidth = $(element.children('.lyric-chunk')).width();
        chordOuterWidth = $(element.children('.chord-chunk')).outerWidth();
        if (lyricWidth < chordOuterWidth){
          if ($(element.children('.midword')).length > 0){
            spacerWidth = chordOuterWidth-element.width();
            element.append('<span class="midword-spacer">-</span>');
            if (spacerWidth < body_size_int){
              element.children('.midword-spacer').width(body_size_int);
            } else {
              element.children('.midword-spacer').width(spacerWidth);
            }
          } else {
            element.css("padding-right", chordOuterWidth-element.width());
          }
        }
      }
    });

  $('#nextslide>span').each(function(){
      element = $(this);
      if (element.children().length > 1){
        lyricWidth = $(element.children('.next-lyric-chunk')).width();
        chordOuterWidth = $(element.children('.next-chord-chunk')).outerWidth();
        if (lyricWidth < chordOuterWidth){
          if ($(element.children('.midword')).length > 0){
            spacerWidth = chordOuterWidth-element.width();
            element.append('<span class="next-midword-spacer">-</span>');
            if (spacerWidth < body_size_int){
              element.children('.next-midword-spacer').width(body_size_int);
            } else {
              element.children('.next-midword-spacer').width(spacerWidth);
            }
          } else {
            element.css("padding-right", chordOuterWidth-element.width());
          }
        }
      }
    });

  } else if (slide_type == "bible"){
    current_text = "<div class =\"nonsong-block\"><p class=\"nonsong-line\">";
    current_text = current_text + current_slides[slide_index].replace(/\n/g, "</p><p class=\"nonsong-line\">");
    current_text = current_text + "</div>";
    if (slide_index < (current_slides.length - 1)){
      next_text = "<div class =\"next-nonsong-block\"><p class=\"nonsong-line\">";
      next_text = next_text + current_slides[slide_index + 1].replace(/\n/g, "</p><p class=\"nonsong-line\">");
      next_text = next_text + "</div>";
    } else {
      next_text = "<div></div>";
    }
    $("#currentslide").html(current_text);
    $("#nextslide").html(next_text);
  } else if (slide_type == "video") {
    current_text = "<div class =\"nonsong-block\"><p class=\"nonsong-line\">";
    current_text = current_text + current_slides[0].replace(/\n/g, "</p><p class=\"nonsong-line\">");
    current_text = current_text + "</div>";
    $("#currentslide").html(current_text);
    $("#nextslide").html("");
  } else if (slide_type == "presentation") {
    if (slide_index < current_slides.length - 1){
      $("#currentslide").html(
          "<div class='two-image-div'><p>Current:</p><img class='pres-two-thumb' src = '" + current_slides[slide_index] + "' /></div>" + 
          "<div class='two-image-div'><p>Next:</p><img class='pres-two-thumb' src = '" + current_slides[slide_index+1] + "' /></div>");
    } else {
      $("#currentslide").html(
        "<div class='two-image-div'><p>Current:</p><img class='pres-two-thumb' src = '" + current_slides[slide_index] + "' /></div>" + 
        "<div class='two-image-div'></div>");
    }
    $("#nextslide").html("");
  } else {
    $("#currentslide").html("");
    $("#nextslide").html("");
  }
}


function update_menu(){
  if (service_items.length > 0) {
    temp_menu = "<ul class='jq-dropdown-menu'>";
    // Build up song choice menu, place divider at current song location
    for (i=0; i<service_items.length; i++){
      if (i != item_index) {
        temp_menu = temp_menu + "<li class='menu-song-item'><a onclick='change_song(" + i + ")' class='menu-song-link'>" + service_items[i] + "</a></li>";
      } else {
        temp_menu = temp_menu + "<li class='menu-song-current-item'><a>" + service_items[i] + "</a></li>";
      }
    }
    temp_menu = temp_menu + "</ul>";
  } else {
    temp_menu = "<ul class='jq-dropdown-menu'></ul>";
  }
  temp_menu = temp_menu + "</ul>";
  if (temp_menu != menustring) {
      $("#jq-dropdown-1").html(temp_menu);
      menustring = temp_menu;
  }
}

function display_on() {
  websocket.send(JSON.stringify({"action": "command.set-display-state", "params": {"state": "on"}}));
}

function display_off() {
  websocket.send(JSON.stringify({"action": "command.set-display-state", "params": {"state": "off"}}));
}

function transpose_up(){
  websocket.send(JSON.stringify({"action": "command.transpose-up", "params": {}}));
}

function transpose_down(){
  websocket.send(JSON.stringify({"action": "command.transpose-down", "params": {}}));
}

function update_capo(){
  capo = $("#caposelect").val();
  websocket.send(JSON.stringify({"action": "client.set-capo", "params": { "capo": capo }}));
}

function next_slide(event){
  event.preventDefault();
  websocket.send(JSON.stringify({"action": "command.next-slide", "params": {}}));
}

function previous_slide(event){
  event.preventDefault();
  websocket.send(JSON.stringify({"action": "command.previous-slide", "params": {}}));
}

function change_verse(id){
  websocket.send(JSON.stringify({"action": "command.goto-slide", "params": { "index": id }}));
}

function change_song(id){
  websocket.send(JSON.stringify({"action": "command.goto-item", "params": { "index": id }}));
}
  
$(document).ready(function(){
  websocket = new WebSocket("ws://" + window.location.hostname + ":9001/leader");
  websocket.onmessage = function (event) {
    json_data = JSON.parse(event.data);
    switch(json_data.action){
      case "update.leader-init":
      case "update.service-overview-update":
        item_index = json_data.params.item_index;
        slide_index = json_data.params.slide_index;
        service_items = json_data.params.items;
        if (JSON.stringify(json_data.params.current_item != "{}")){
          slide_type = json_data.params.current_item.type;
          current_slides = json_data.params.current_item.slides;
          if (slide_type == "song"){
            played_key = json_data.params.current_item["played-key"];
            verse_order = json_data.params.current_item["verse-order"];
            part_counts = json_data.params.current_item["part-counts"];
          } else {
            verse_order = "";
            part_counts = [];
          }
        } else {
          slide_type = "none";
          current_slides = [];
          verse_order = "";
          part_counts = [];
        }
        if (json_data.params.screen_state == "on"){
          $("body").css("border-top", "6px solid #4CAF50");
        } else {
          $("body").css("border-top", "6px solid red");
        }
        update_menu();
        update_music();
        break;
      case "update.slide-index-update":
        slide_index = json_data.params.slide_index;
        update_music();
        break;
      case "update.item-index-update":
        item_index = json_data.params.item_index;
        slide_index = json_data.params.slide_index;
        slide_type = json_data.params.current_item.type;
        current_slides = json_data.params.current_item.slides;
        if (slide_type == "song"){
          played_key = json_data.params.current_item["played-key"];
          verse_order = json_data.params.current_item["verse-order"];
          part_counts = json_data.params.current_item["part-counts"];
        } else {
          verse_order = "";
          played_key = "";
          part_counts = [];
        }
        update_menu();
        update_music();
        break;
      case "update.display-state":
        if (json_data.params.state == "on"){
          $("body").css("border-top", "6px solid #4CAF50");
        } else {
          $("body").css("border-top", "6px solid red");
        }
        break;
      case "response.set-display-state":
      case "response.next-slide":
      case "response.previous-slide":
      case "response.goto-slide":
      case "response.goto-item":
      case "response.transpose-up":
      case "response.transpose-down":
        console.log("Server response: [" + json_data.action + "], Status: [" + json_data.params.status + "], Details: [" + json_data.params.details + "]");
        break;
      default:
        console.error("Unsupported event", json_data);
    }
  }

  $("#caposelect").change(update_capo);
  $("#controller-next").on("click", next_slide);
  $("#controller-prev").on("click", previous_slide);
});


// Adjust document body size based on ?size=n parameter, if it exists
params = window.location.search.slice(1);
body_size_int = 16;
body_size = "16px";
if (params != ""){
  param_arr = params.split('&');
  for(var i=0; i<param_arr.length; i++){
    param_pair = param_arr[i].split('=');
    if (param_pair[0] == 'size'){
      body_size_int = parseInt(param_pair[1]);
      body_size = param_pair[1] + "px";
    }
  }
}
$("html").css("font-size", body_size);