let websocket;
let played_key = "";
let slide_type = "";
let current_title = "";
let current_item;
let service_items = [];
let current_slides = [];
let part_counts = [];
let slide_index = -1;
let item_index = -1;

function update_music() {
  stop_running_video();

  document.getElementById("playedkey").innerHTML = played_key;
  let verse_list = "";
  let verse_control_list = "<ul>";

  if (slide_type == "song") {
    verse_list = verse_order.split(" ");
    let part_counts_sum = 0;
    for (let i = 0; i < verse_list.length; i++) {
      if (slide_index >= part_counts_sum && slide_index < part_counts_sum + part_counts[i]) {
        verse_control_list +=
          "<li><span class='current-verse'>" + verse_list[i].toUpperCase() + "</span></li>";
      } else {
        verse_control_list += "<li>" + verse_list[i].toUpperCase() + "</li>";
      }
      part_counts_sum += part_counts[i];
    }
    verse_control_list += "</ul>";
  } else if (slide_type != undefined) {
    verse_control_list = "<ul><li>" + current_title + "</li></ul>";
  }
  document.getElementById("verseorder").innerHTML = verse_control_list;

  let current_text = "";
  let next_text = "";

  if (slide_type == "song" || slide_type == "bible") {
    let current_slide_lines = current_slides[slide_index].split(/\n/);
    for (const line in current_slide_lines) {
      current_text += "<p>";
      let current_line_segments = current_slide_lines[line].split(/\[[\w\+#\/"='' ]*\]/);
      for (let segment = 0; segment < current_line_segments.length; segment++) {
        current_text += current_line_segments[segment];
      }
      current_text += "</p>";
    }
    document.getElementById("currentslide").innerHTML = current_text;

    let next_slide_lines = [];
    if (slide_index < current_slides.length - 1) {
      next_slide_lines = current_slides[slide_index + 1].split(/\n/);
    }
    for (const line in next_slide_lines) {
      next_text += "<p>";
      let next_line_segments = next_slide_lines[line].split(/\[[\w\+#\/"='' ]*\]/);
      for (let segment = 0; segment < next_line_segments.length; segment++) {
        next_text += next_line_segments[segment];
      }
      next_text += "</p>";
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
  const video_ar = current_item.video_width / current_item.video_height;
  const screen_ar = window.innerWidth / window.innerHeight;
  if (video_ar <= screen_ar) {
    const left_pos = window.innerWidth * 0.5 * (1 - video_ar / screen_ar);
    document.getElementById("video_item").style.height = "100%";
    document.getElementById("video_item").style.width = "auto";
    document.getElementById("video_item").style.top = 0;
    document.getElementById("video_item").style.left = left_pos + "px";
  } else {
    const top_pos = window.innerHeight * 0.5 * (1 - screen_ar / video_ar);
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

function update_basic_init(json_data) {
  Toastify({
    text: "Connected to Malachi server",
    gravity: "bottom",
    position: "left",
    style: { background: "#4caf50" },
  }).showToast();
  update_service_overview_update(json_data);
}

function update_service_overview_update(json_data) {
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
}

function update_slide_index_update(json_data) {
  slide_index = json_data.params.slide_index;
  update_music();
}

function update_item_index_update(json_data) {
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
}

function trigger_play_video() {
  document.getElementById("songarea").style.display = "none";
  document.getElementById("video_item").style.display = "block";
  resize_video_item();
  document.getElementById("video_item").play();
}

function trigger_pause_video() {
  document.getElementById("video_item").pause();
}

function trigger_stop_video() {
  stop_running_video();
  document.getElementById("video_item").currentTime = 0.0;
}

function trigger_seek_video(json_data) {
  document.getElementById("video_item").currentTime = json_data.params.seconds;
}

function start_websocket() {
  websocket = null;
  websocket = new WebSocket("ws://" + window.location.hostname + ":9001/monitor");
  websocket.onmessage = function (event) {
    let json_data = JSON.parse(event.data);
    console.log(json_data);
    switch (json_data.action) {
      case "update.basic-init":
        update_basic_init(json_data);
        break;
      case "update.service-overview-update":
        update_service_overview_update(json_data);
        break;
      case "update.slide-index-update":
        update_slide_index_update(json_data);
        break;
      case "update.item-index-update":
        update_item_index_update(json_data);
        break;
      case "trigger.play-video":
        trigger_play_video();
        break;
      case "trigger.pause-video":
        trigger_pause_video();
        break;
      case "trigger.stop-video":
        trigger_stop_video();
        break;
      case "trigger.seek-video":
        trigger_seek_video(json_data);
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
const params = window.location.search.slice(1);
let body_size = "16px";
if (params != "") {
  const param_arr = params.split("&");
  for (let i = 0; i < param_arr.length; i++) {
    let param_pair = param_arr[i].split("=");
    if (param_pair[0] == "size") {
      body_size = param_pair[1] + "px";
    }
  }
}
document.querySelector("html").style.fontSize = body_size;
