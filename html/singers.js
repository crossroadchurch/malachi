var websocket;
var played_key = "";
var slide_type = "";
var current_title = "";
var current_item;
var service_items = [];
var current_slides = [];
var part_counts = [];
var slide_index = -1;
var item_index = -1;

function update_music() {
  stop_running_video();

  document.getElementById("playedkey").innerHTML = played_key;
  verse_list = "";
  verse_control_list = "<ul>";

  if (slide_type == "song") {
    verse_list = verse_order.split(" ");
    part_counts_sum = 0;
    for (i = 0; i < verse_list.length; i++) {
      if (slide_index >= part_counts_sum && slide_index < part_counts_sum + part_counts[i]) {
        verse_control_list =
          verse_control_list +
          "<li><span class='current-verse'>" +
          verse_list[i].toUpperCase() +
          "</span></li>";
      } else {
        verse_control_list = verse_control_list + "<li>" + verse_list[i].toUpperCase() + "</li>";
      }
      part_counts_sum = part_counts_sum + part_counts[i];
    }
    verse_control_list = verse_control_list + "</ul>";
  } else if (slide_type != undefined) {
    verse_control_list = "<ul><li>" + current_title + "</li></ul>";
  }
  document.getElementById("verseorder").innerHTML = verse_control_list;

  if (slide_type == "song" || slide_type == "bible") {
    current_slide_lines = current_slides[slide_index].split(/\n/);
    current_text = "";
    for (line in current_slide_lines) {
      current_text = current_text + "<p>";
      current_line_segments = current_slide_lines[line].split(/\[[\w\+#\/"='' ]*\]/);
      for (var segment = 0; segment < current_line_segments.length; segment++) {
        cur_seg = current_line_segments[segment];
        current_text = current_text + cur_seg;
      }
      current_text = current_text + "</p>";
    }
    document.getElementById("currentslide").innerHTML = current_text;

    if (slide_index < current_slides.length - 1) {
      next_slide_lines = current_slides[slide_index + 1].split(/\n/);
    } else {
      next_slide_lines = [];
    }
    next_text = "";
    for (line in next_slide_lines) {
      next_text = next_text + "<p>";
      next_line_segments = next_slide_lines[line].split(/\[[\w\+#\/"='' ]*\]/);
      for (var segment = 0; segment < next_line_segments.length; segment++) {
        next_seg = next_line_segments[segment];
        next_text = next_text + next_seg;
      }
      next_text = next_text + "</p>";
    }
    document.getElementById("nextslide").innerHTML = next_text;
  } else if (slide_type == "video") {
    document.getElementById("currentslide").innerHTML = "";
    document.getElementById("nextslide").innerHTML = "";
    // Background load video, wait for trigger to display and start playback
    document.getElementById("songarea").style.display = "none";
    document.getElementById("video_item_src").setAttribute("src", current_item.url);
    document.getElementById("video_item").load();
  } else if (slide_type == "presentation") {
    document.getElementById("currentslide").innerHTML = "";
    document.getElementById("nextslide").innerHTML = "";
  } else {
    document.getElementById("currentslide").innerHTML = "";
    document.getElementById("nextslide").innerHTML = "";
  }
}

function resize_video_item() {
  video_ar = current_item.video_width / current_item.video_height;
  screen_ar = window.innerWidth / window.innerHeight;
  if (video_ar <= screen_ar) {
    left_pos = window.innerWidth * 0.5 * (1 - video_ar / screen_ar);
    document.getElementById("video_item").style.height = "100%";
    document.getElementById("video_item").style.width = "auto";
    document.getElementById("video_item").style.top = 0;
    document.getElementById("video_item").style.left = left_pos + "px";
  } else {
    top_pos = window.innerHeight * 0.5 * (1 - screen_ar / video_ar);
    document.getElementById("video_item").style.height = "auto";
    document.getElementById("video_item").style.width = "100%";
    document.getElementById("video_item").style.top = top_pos + "px";
    document.getElementById("video_item").style.left = 0;
  }
}

function stop_running_video() {
  document.getElementById("video_item").pause();
  document.getElementById("video_item").style.display = "none";
  document.getElementById("songarea").style.display = "block";
}

function start_websocket() {
  websocket = null;
  websocket = new WebSocket("ws://" + window.location.hostname + ":9001/monitor");
  websocket.onmessage = function (event) {
    json_data = JSON.parse(event.data);
    console.log(json_data);
    switch (json_data.action) {
      case "update.basic-init":
        Toastify({
          text: "Connected to Malachi server",
          gravity: "bottom",
          position: "left",
          style: { background: "#4caf50" },
        }).showToast();
      case "update.service-overview-update":
        item_index = json_data.params.item_index;
        slide_index = json_data.params.slide_index;
        service_items = json_data.params.items;
        current_item = json_data.params.current_item;
        if (JSON.stringify(json_data.params.current_item != "{}")) {
          slide_type = current_item.type;
          current_slides = current_item.slides;
          current_title = current_item.title;
          if (slide_type == "song") {
            played_key = current_item["played-key"];
            verse_order = current_item["verse-order"];
            part_counts = current_item["part-counts"];
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
        current_item = json_data.params.current_item;
        slide_type = current_item.type;
        current_slides = current_item.slides;
        current_title = current_item["title"];
        if (slide_type == "song") {
          played_key = current_item["played-key"];
          verse_order = current_item["verse-order"];
          part_counts = current_item["part-counts"];
        } else {
          verse_order = "";
          played_key = "";
          part_counts = [];
        }
        update_music();
        break;
      case "trigger.play-video":
        document.getElementById("songarea").style.display = "none";
        document.getElementById("video_item").style.display = "block";
        resize_video_item();
        document.getElementById("video_item").play();
        break;
      case "trigger.pause-video":
        document.getElementById("video_item").pause();
        break;
      case "trigger.stop-video":
        stop_running_video();
        document.getElementById("video_item").currentTime = 0.0;
        break;
      case "trigger.seek-video":
        document.getElementById("video_item").currentTime = json_data.params.seconds;
        break;
      case "response.unlock-socket":
      case "result.capture-update":
      case "update.capture-ready":
      case "update.stop-capture":
      case "update.video-loop":
        break;
      default:
        console.error("Unsupported event", json_data);
    }
  };
  websocket.onclose = function (event) {
    if (event.wasClean == false) {
      Toastify({
        text: "Connection was closed/refused by server\nReconnection attempt will be made in 5 seconds",
        gravity: "bottom",
        position: "left",
        duration: 4000,
        style: { background: "#f44337" },
      }).showToast();
      setTimeout(start_websocket, 5000);
    }
  };
}

let ready = (callback) => {
  if (document.readyState != "loading") {
    callback();
  } else {
    document.addEventListener("DOMContentLoaded", callback);
  }
};

ready(() => {
  document.getElementById("video_item").muted = "true";
  start_websocket();
});

// Adjust document body size based on ?size=n parameter, if it exists
params = window.location.search.slice(1);
body_size = "16px";
if (params != "") {
  param_arr = params.split("&");
  for (var i = 0; i < param_arr.length; i++) {
    param_pair = param_arr[i].split("=");
    if (param_pair[0] == "size") {
      body_size = param_pair[1] + "px";
    }
  }
}
document.querySelector("html").style.fontSize = body_size;
