let capo = 0;
let verse_order = "";
let played_key = "";
let slide_type = "";
let current_slides = [];
let part_counts = [];
let slide_index = -1;
let websocket;

function update_music() {
  $("#playedkey").html(played_key);
  verse_control_list = "<ul>";
  verse_list = "";

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
            if (spacerWidth < 16){ // TODO: Replace with relative size condition
              element.children('.midword-spacer').width(16);
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
            if (spacerWidth < 16){ // TODO: Replace with relative size condition
              element.children('.next-midword-spacer').width(16);
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

function update_capo(){
  capo = $("#caposelect").val();
  websocket.send(JSON.stringify({"action": "client.set-capo", "params": { "capo": capo }}));
}

$(document).ready(function(){
  websocket = new WebSocket("ws://" + window.location.hostname + ":9001/basic");
  websocket.onmessage = function (event) {
    json_data = JSON.parse(event.data);
    switch(json_data.action){
      case "update.service-overview-update":
        slide_index = json_data.params.slide_index;
        if (JSON.stringify(json_data.params.current_item != "{}")){
          slide_type = json_data.params.current_item.type;
          current_slides = json_data.params.current_item.slides;
          current_title = json_data.params.current_item["title"];
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
        update_music();
        break;
      case "update.slide-index-update":
        slide_index = json_data.params.slide_index;
        update_music();
        break;
      case "update.item-index-update":
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
      default:
        console.error("Unsupported event", json_data);
    }
  }
  $("#caposelect").change(update_capo);
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