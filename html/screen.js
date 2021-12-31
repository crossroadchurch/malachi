var websocket;
var current_item;
var loop_width = 0;
var loop_height = 0;
var loop_ar = 0;
var display_copyright = false;
var display_verseorder = false;
var song_background = { url: "none", width: 1, height: 1 };
var bible_background = { url: "none", width: 1, height: 1 };
var countdown_to = new Date();
var countdown_timer; // Interval reference
var screen_state = false;
var video_displayed = false;

function display_current_slide(slide_index) {
  current_slide = current_item.slides[slide_index];
  stop_running_video();
  copy_text = "<p></p>";
  if (current_item.type == "song") {
    slide_lines = current_slide.split(/\n/);
    slide_text = "<p>";
    for (line in slide_lines) {
      line_segments = slide_lines[line].split(/\[[\w\+#\/"='' ]*\]/);
      for (var segment = 0; segment < line_segments.length; segment++) {
        slide_text += line_segments[segment];
      }
      slide_text += "<br />";
    }
    slide_text += "</p>";

    verseorder = "<p>";
    verse_list = current_item["verse-order"].split(" ");
    part_counts_sum = 0;
    for (i = 0; i < verse_list.length; i++) {
      if (
        slide_index >= part_counts_sum &&
        slide_index < part_counts_sum + current_item["part-counts"][i]
      ) {
        verseorder =
          verseorder +
          "<span class='selected'>" +
          verse_list[i].toUpperCase() +
          "</span>";
      } else {
        verseorder =
          verseorder + "<span>" + verse_list[i].toUpperCase() + "</span>";
      }
      part_counts_sum = part_counts_sum + current_item["part-counts"][i];
    }
    verseorder = verseorder + "</p>";
  } else if (current_item.type == "presentation") {
    slide_text = "";
    verseorder = "<p></p>";
  } else if (current_item.type == "video") {
    slide_text = "";
    verseorder = "<p></p>";
    // Background load video, wait for trigger to display and start playback
    resize_video_item();
    $("#video_item_src").attr("src", current_item.url);
    $("#video_item").load();
  } else {
    slide_text = "<p>" + current_slide + "</p>";
    verseorder = "<p></p>";
  }
  $("#slide_area").html(slide_text);
  $("#verseorder_area").html(verseorder);
  if (current_item.copyright) {
    $("#copyright_area").html("<p>" + current_item.copyright + "</p>");
  } else {
    $("#copyright_area").html("<p></p>");
  }
  update_optional_areas();
}

function clear_current_slide() {
  stop_running_video();
  $("#slide_area").html("");
}

function update_optional_areas() {
  if (display_copyright && screen_state) {
    $("#copyright_area").css("display", "block");
  } else {
    $("#copyright_area").css("display", "none");
  }
  if (display_verseorder && screen_state) {
    $("#verseorder_area").css("display", "block");
  } else {
    $("#verseorder_area").css("display", "none");
  }
}

function stop_running_video() {
  video_displayed = false;
  document.getElementById("video_item").pause();
  $("#loop_video").css("display", "block");
  $("#video_item").css("display", "none");
}

function resize_video_item() {
  video_ar = current_item.video_width / current_item.video_height;
  screen_ar = window.innerWidth / window.innerHeight;
  if (video_ar <= screen_ar) {
    left_pos = window.innerWidth * 0.5 * (1 - video_ar / screen_ar);
    $("#video_item").css("height", "100%");
    $("#video_item").css("width", "auto");
    $("#video_item").css("top", "0");
    $("#video_item").css("left", left_pos);
  } else {
    top_pos = window.innerHeight * 0.5 * (1 - screen_ar / video_ar);
    $("#video_item").css("height", "auto");
    $("#video_item").css("width", "100%");
    $("#video_item").css("top", top_pos);
    $("#video_item").css("left", "0");
  }
}

function resize_loop() {
  if (loop_height > 0) {
    screen_ar = window.innerWidth / window.innerHeight;
    if (screen_ar <= loop_ar) {
      left_pos = window.innerWidth * -0.5 * (loop_ar / screen_ar - 1);
      $("#loop_video").css("height", "100%");
      $("#loop_video").css("width", "auto");
      $("#loop_video").css("top", 0);
      $("#loop_video").css("left", left_pos);
    } else {
      top_pos = window.innerHeight * -0.5 * (screen_ar / loop_ar - 1);
      $("#loop_video").css("height", "auto");
      $("#loop_video").css("width", "100%");
      $("#loop_video").css("top", top_pos);
      $("#loop_video").css("left", 0);
    }
  }
}

function update_from_style(style) {
  div_width = style["div-width-vw"];
  $("#slide_area").css("width", div_width + "vw");
  $("#slide_area").css("margin-left", (100 - div_width) / 2 + "vw");
  $("#slide_area").css("margin-top", style["margin-top-vh"] + "vh");
  $("#slide_area").css("font-size", style["font-size-vh"] + "vh");
  $("#slide_area").css("color", "#" + style["font-color"]);
  if (style["outline-style"] === "drop-shadow") {
    $("#slide_area").removeClass("outline");
    $("#slide_area").addClass("drop_shadow");
  } else if (style["outline-style"] === "text-outline") {
    $("#slide_area").addClass("outline");
    $("#slide_area").removeClass("drop_shadow");
  } else {
    $("#slide_area").removeClass("outline");
    $("#slide_area").removeClass("drop_shadow");
  }
  $("#countdown_p").css("font-size", style["countdown-size-vh"] + "vh");
  $("#countdown_h").css("font-size", style["countdown-h-size-vh"] + "vh");
  $("#countdown_h").html(style["countdown-h-text"]);
  $("#countdown_area").css("margin-top", style["countdown-top-vh"] + "vh");
  display_copyright = style["display-copyright"];
  console.log(display_copyright, "copyright state")
  display_verseorder = style["display-verseorder"];
  $("#copyright_area").css(
    "font-size",
    parseInt(style["copy-size-vh"]) / 10 + "vh"
  );
  $("#copyright_area").css("width", style["copy-width-vw"] + "vw");
  $("#verseorder_area").css(
    "font-size",
    parseInt(style["order-size-vh"]) / 10 + "vh"
  );
  $("#verseorder_area").css("width", style["order-width-vw"] + "vw");
  update_optional_areas();
  song_background.url = style["song-background-url"];
  song_background.width = style["song-background-w"];
  song_background.height = style["song-background-h"];
  bible_background.url = style["bible-background-url"];
  bible_background.width = style["bible-background-w"];
  bible_background.height = style["bible-background-h"];
  update_background();
}

function update_background() {
  var bg_url, bg_w, bg_h;
  if (current_item == null) {
    bg_url = song_background.url;
    bg_w = song_background.width;
    bg_h = song_background.height;
  } else if (current_item.type == "bible") {
    bg_url = bible_background.url;
    bg_w = bible_background.width;
    bg_h = bible_background.height;
  } else {
    bg_url = song_background.url;
    bg_w = song_background.width;
    bg_h = song_background.height;
  }
  // Only update background if it has changed since last checked
  if (bg_url == "none") {
    $("#bg_image").attr("src", "");
  } else {
    $("#bg_image").attr("src", bg_url);
  }
  image_ar = bg_w / bg_h;
  screen_ar = window.innerWidth / window.innerHeight;
  if (image_ar >= screen_ar) {
    left_pos = window.innerWidth * 0.5 * (1 - image_ar / screen_ar);
    $("#bg_image").css("height", "100%");
    $("#bg_image").css("width", "auto");
    $("#bg_image").css("top", "0");
    $("#bg_image").css("left", left_pos);
  } else {
    top_pos = window.innerHeight * 0.5 * (1 - screen_ar / image_ar);
    $("#bg_image").css("height", "auto");
    $("#bg_image").css("width", "100%");
    $("#bg_image").css("top", top_pos);
    $("#bg_image").css("left", "0");
  }
}

function decrease_countdown() {
  var countdown_left = Math.floor((countdown_to.getTime() - new Date().getTime())/1000);
  if (countdown_left >= 0) {
    $("#countdown_p").html(format_time(countdown_left));
  } else {
    clearInterval(countdown_timer);
    $("#countdown_area").css("display", "none");
  }
}

function stop_countdown() {
  $("#countdown_area").css("display", "none");
  countdown_to = new Date(); // Interval, if running, will stop on next call to decrease_countdown
}

function format_time(time_secs) {
  var mins = Math.floor(time_secs / 60);
  var secs = time_secs % 60;
  var time_str = mins + ":" + secs.toString().padStart(2, 0);
  return time_str;
}

function start_websocket() {
  websocket = null;
  websocket = new WebSocket(
    "ws://" + window.location.hostname + ":9001/display"
  );
  websocket.onmessage = function (event) {
    json_data = JSON.parse(event.data);
    console.log(json_data);
    switch (json_data.action) {
      case "update.display-init":
        if (json_data.params["video_loop"] !== "") {
          $("#loop_video_src").attr("src", json_data.params["video_loop"]);
          $("#loop_video").load();
          loop_height = json_data.params["loop-height"];
          loop_width = json_data.params["loop-width"];
          loop_ar = loop_width / loop_height;
          resize_loop();
        } else {
          $("#loop_video_src").attr("src", "/html/black-frame.mp4");
          $("#loop_video").load();
          loop_height = 0;
          loop_width = 0;
          loop_ar = 0;
        }
        update_from_style(json_data.params.style);
        if (json_data.params.screen_state == "on") {
          screen_state = true;
          $("#slide_area").css("display", "block");
        } else {
          screen_state = false;
          $("#slide_area").css("display", "none");
        }
        update_optional_areas();
        current_item = json_data.params.current_item;
        if (json_data.params.item_index != -1) {
          display_current_slide(json_data.params.slide_index);
        }
        break;

      case "update.style-update":
        update_from_style(json_data.params.style);
        break;

      case "update.service-overview-update":
      case "update.item-index-update":
        if (screen_state) {
          stop_countdown();
        }
        current_item = json_data.params.current_item;
        update_background();
        if (json_data.params.item_index != -1) {
          display_current_slide(json_data.params.slide_index);
        } else {
          clear_current_slide();
        }
        break;

      case "update.slide-index-update":
        stop_countdown();
        display_current_slide(json_data.params.slide_index);
        break;

      case "update.display-state":
        if (json_data.params.state == "on") {
          screen_state = true;
          stop_countdown();
          $("#slide_area").css("display", "block");
        } else {
          screen_state = false;
          $("#slide_area").css("display", "none");
        }
        update_optional_areas();
        break;

      case "update.video-loop":
        if (json_data.params.url !== "") {
          $("#loop_video_src").attr("src", json_data.params.url);
          $("#loop_video").load();
          loop_height = json_data.params["loop-height"];
          loop_width = json_data.params["loop-width"];
          loop_ar = loop_width / loop_height;
          resize_loop();
        } else {
          $("#loop_video_src").attr("src", "/html/black-frame.mp4");
          $("#loop_video").load();
          loop_height = 0;
          loop_width = 0;
          loop_ar = 0;
        }
        break;

      case "trigger.play-video":
        stop_countdown();
        $("#video_item").css("display", "block");
        $("#loop_video").css("display", "none");
        document.getElementById("video_item").play();
        video_displayed = true;
        break;

      case "trigger.pause-video":
        document.getElementById("video_item").pause();
        break;

      case "trigger.stop-video":
        video_displayed = false;
        stop_running_video();
        document.getElementById("video_item").currentTime = 0.0;
        break;

      case "trigger.seek-video":
        document.getElementById("video_item").currentTime =
          json_data.params.seconds;
        break;

      case "trigger.start-countdown":
        if (!screen_state && !video_displayed) {
          var now = new Date();
          countdown_to = new Date(now.getFullYear(), now.getMonth(), now.getDate(), json_data.params.hr, json_data.params.min, 0);
          var countdown_left = Math.floor((countdown_to.getTime() - now.getTime())/1000);
          if (countdown_left > 0){
            $("#countdown_area").css("display", "block");
            $("#countdown_p").html(format_time(countdown_left));
            clearInterval(countdown_timer);
            countdown_timer = setInterval(decrease_countdown, 1000);
          }
        }
        break;

      case "trigger.clear-countdown":
        stop_countdown();
        break;

      default:
        console.error("Unsupported event", json_data);
    }
  };
  websocket.onclose = function (event) {
    if (event.wasClean == false) {
      setTimeout(start_websocket, 5000);
    }
  };
}

$(document).ready(function () {
  start_websocket();

  // Mute foreground video element based on ?muted=true,false parameter, if it exists
  params = window.location.search.slice(1);
  video_muted = false;
  if (params != "") {
    param_arr = params.split("&");
    for (var i = 0; i < param_arr.length; i++) {
      param_pair = param_arr[i].split("=");
      if (param_pair[0] == "muted") {
        video_muted = param_pair[1] == "true";
      }
    }
  }
  $("#video_item").prop("muted", video_muted);
});

$(window).resize(function () {
  if (current_item !== undefined && current_item.type == "video") {
    resize_video_item();
  }
  resize_loop();
  update_background();
});
