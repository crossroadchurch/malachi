var websocket;
var played_key = "";
var slide_type = "";
var current_title = "";
var service_items = [];
var current_slides = [];
var part_counts = [];
var slide_index = -1;
var item_index = -1;

function update_music() {
  // First clear any capture image
  hide_capture_image();

  $("#playedkey").html(played_key);
  verse_list = "";
  verse_control_list = "<ul>";

  if (slide_type == "song"){
    verse_list = verse_order.split(" ");
    part_counts_sum = 0
    for (i=0; i < verse_list.length; i++){
      if ((slide_index >= part_counts_sum) && (slide_index < (part_counts_sum + part_counts[i]))) {
        verse_control_list = verse_control_list + 
          "<li><span class='current-verse'>" + verse_list[i].toUpperCase() + "</span></li>";
      } else {
        verse_control_list = verse_control_list +
          "<li>" + verse_list[i].toUpperCase() + "</li>";
      }
      part_counts_sum = part_counts_sum + part_counts[i];
    }
    verse_control_list = verse_control_list + "</ul>";
  } else if (slide_type != undefined) {
    verse_control_list = "<ul><li>" + current_title + "</li></ul>";
  }
  $("#verseorder").html(verse_control_list);

  if ((slide_type == "song") || (slide_type == "bible")){
    current_slide_lines = current_slides[slide_index].split(/\n/);
    current_text = '';
    for (line in current_slide_lines){
      current_text = current_text + "<p>";
      current_line_segments = current_slide_lines[line].split(/\[[\w\+#\/"='' ]*\]/);
      for (var segment=0; segment < current_line_segments.length; segment++){
        cur_seg = current_line_segments[segment];
        current_text = current_text + cur_seg;
      }
      current_text = current_text + "</p>"
    }
    $("#currentslide").html(current_text);

    if (slide_index < (current_slides.length - 1)){
      next_slide_lines = current_slides[slide_index + 1].split(/\n/);
    } else {
      next_slide_lines = [];
    }
    next_text = '';
    for (line in next_slide_lines){
      next_text = next_text + "<p>";
      next_line_segments = next_slide_lines[line].split(/\[[\w\+#\/"='' ]*\]/);
      for (var segment=0; segment < next_line_segments.length; segment++){
        next_seg = next_line_segments[segment];
        next_text = next_text + next_seg;
      }
      next_text = next_text + "</p>"
    }
    $("#nextslide").html(next_text);
  } else if (slide_type == "video") {
    current_text = "<div class =\"nonsong-block\"><p class=\"nonsong-line\">";
    current_text = current_text + current_slides[0].replace(/\n/g, "</p><p class=\"nonsong-line\">");
    current_text = current_text + "</div>";
    $("#currentslide").html(current_text);
    $("#nextslide").html("");
  } else if (slide_type == "presentation"){
    $("#currentslide").html("<img class='pres-thumb' src = '" + current_slides[slide_index] + "' />");
    $("#nextslide").html("");
  } else {
    $("#currentslide").html("");
    $("#nextslide").html("");
  }
}

function display_capture_image(url, cap_w, cap_h){
  // Bypass caching to ensure new images are always loaded when using same urls
  document.getElementById('captureimage').src = url + "#" + new Date().getTime();
  $('#captureimage').css('display', 'block');
  $('#songarea').css('display', 'none');
  capture_ar = cap_w / cap_h;
  screen_ar = window.innerWidth / window.innerHeight;
  console.log("CAR: " + capture_ar + ", SAR: " + screen_ar);
  if (capture_ar <= screen_ar){
    left_pos = window.innerWidth * 0.5 * (1 - (capture_ar/screen_ar));
    $('#captureimage').css('height', window.innerHeight + "px");
    $('#captureimage').css('width', 'auto');
    $('#captureimage').css('top', '0px');
    $('#captureimage').css('left', left_pos + "px");
  } else {
    top_pos = window.innerHeight * 0.5 * (1 - (screen_ar/capture_ar));
    $('#captureimage').css('height', 'auto');
    $('#captureimage').css('width', window.innerWidth + "px");
    $('#captureimage').css('top', top_pos + "px");
    $('#captureimage').css('left', '0px');
  }
}

function hide_capture_image(){
  $('#captureimage').attr('src', '');
  $('#captureimage').css('display', 'none');
  $('#songarea').css('display', 'block');
}

function start_websocket(){
  websocket = null;
  websocket = new WebSocket("ws://" + window.location.hostname + ":9001/monitor");
  websocket.onmessage = function (event) {
    json_data = JSON.parse(event.data);
    console.log(json_data);
    switch(json_data.action){
      case "update.basic-init":
        toastr.options.positionClass = "toast-bottom-center";
        toastr.success("Connected to Malachi server");
      case "update.service-overview-update":
        item_index = json_data.params.item_index;
        slide_index = json_data.params.slide_index;
        service_items = json_data.params.items;
        if (JSON.stringify(json_data.params.current_item != "{}")){
          slide_type = json_data.params.current_item.type;
          current_slides = json_data.params.current_item.slides;
          current_title = json_data.params.current_item.title;
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
          current_title = "";
          verse_order = "";
          part_counts = [];
        }
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
        current_title = json_data.params.current_item["title"];
        if (slide_type == "song"){
          played_key = json_data.params.current_item["played-key"];
          verse_order = json_data.params.current_item["verse-order"];
          part_counts = json_data.params.current_item["part-counts"];
        } else {
          verse_order = "";
          played_key = "";
          part_counts = [];
        }
        update_music();
        break;
      case "update.capture-update":
        display_capture_image(json_data.params.capture_url, json_data.params.width, json_data.params.height);
        break;
      case "update.stop-capture":
        hide_capture_image();
        break;
      default:
        console.error("Unsupported event", json_data);
    }
  }
  websocket.onclose = function(event){
    if (event.wasClean == false){
      toastr.options.positionClass = "toast-bottom-full-width";
      toastr.options.timeOut = "3500";
      toastr.error("Reconnection attempt will be made in 5 seconds", "Connection was closed/refused by server");
      setTimeout(start_websocket, 5000);
    }
  }
}

$(document).ready(function(){
  start_websocket();
});

// Adjust document body size based on ?size=n parameter, if it exists
params = window.location.search.slice(1);
body_size = "16px";
if (params != ""){
  param_arr = params.split('&');
  for(var i=0; i<param_arr.length; i++){
    param_pair = param_arr[i].split('=');
    if (param_pair[0] == 'size'){
      body_size = param_pair[1] + "px";
    }
  }
}
$("html").css("font-size", body_size);