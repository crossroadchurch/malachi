let websocket;
let slide_type = "";
let current_title = "";
let prev_title = "";
let next_title = "";
let current_item;
let service_items = [];
let current_slides = [];
let slide_index = -1;
let item_index = -1;
// DOM pointers
const DOM_dict = {};
// prettier-ignore
const DOM_KEYS = [
  "currentitem", "previtem", "nextitem", "currentslide", "nextslide"
];

function update_music() {
  let current_text = "";
  let next_text = "";

  if (slide_type == "song" || slide_type == "bible") {
    let current_slide_lines = current_slides[slide_index].split(/\n/);
    for (const line in current_slide_lines) {
      current_text += "<p>";
      let current_line_segments = current_slide_lines[line].split(/\[[\w\+\¬#\/"='' ]*\]/);
      for (let segment = 0; segment < current_line_segments.length; segment++) {
        current_text += current_line_segments[segment];
      }
      current_text += "</p>";
    }
    DOM_dict["currentslide"].innerHTML = current_text;

    let next_slide_lines = [];
    if (slide_index < current_slides.length - 1) {
      next_slide_lines = current_slides[slide_index + 1].split(/\n/);
    }
    for (const line in next_slide_lines) {
      next_text += "<p>";
      let next_line_segments = next_slide_lines[line].split(/\[[\w\+\¬#\/"='' ]*\]/);
      for (let segment = 0; segment < next_line_segments.length; segment++) {
        next_text += next_line_segments[segment];
      }
      next_text += "</p>";
    }
    DOM_dict["nextslide"].innerHTML = next_text;
  } else {
    DOM_dict["currentslide"].innerHTML = current_title;
    DOM_dict["nextslide"].innerHTML = "";
  }
  DOM_dict["currentitem"].innerHTML = current_title;
  DOM_dict["nextitem"].innerHTML = next_title;
  DOM_dict["previtem"].innerHTML = prev_title;
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

function load_current_item(cur_item) {
  slide_type = cur_item.type;
  current_slides = cur_item.slides;
  current_title = cur_item["title"];
  if (item_index > 0) {
    prev_title = service_items[item_index - 1];
  } else {
    prev_title = "";
  }
  if (item_index < service_items.length - 1) {
    next_title = service_items[item_index + 1];
  } else {
    next_title = "";
  }
}

function update_service_overview_update(json_data) {
  item_index = json_data.params.item_index;
  slide_index = json_data.params.slide_index;
  service_items = json_data.params.items;
  current_item = json_data.params.current_item;
  if (JSON.stringify(json_data.params.current_item) != "{}") {
    load_current_item(current_item);
  } else {
    slide_type = "none";
    current_slides = [];
    current_title = "";
    prev_title = "";
    next_title = "";
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
  load_current_item(current_item);
  update_music();
}

function toggle_screen() {
  websocket.send(JSON.stringify({ action: "command.toggle-display-state", params: {} }));
}

function prev_item() {
  websocket.send(JSON.stringify({ action: "command.previous-item", params: {} }));
}

function next_item() {
  websocket.send(JSON.stringify({ action: "command.next-item", params: {} }));
}

function prev_slide() {
  websocket.send(JSON.stringify({ action: "command.previous-slide", params: {} }));
}

function next_slide() {
  websocket.send(JSON.stringify({ action: "command.next-slide", params: {} }));
}

function generic_stop() {
  websocket.send(JSON.stringify({ action: "command.generic-stop", params: {} }));
}

function generic_play() {
  websocket.send(JSON.stringify({ action: "command.generic-play", params: {} }));
}

function restore_loop() {
  websocket.send(JSON.stringify({ action: "command.restore-loop", params: {} }));
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
      case "trigger.pause-video":
      case "trigger.stop-video":
      case "trigger.seek-video":
      case "trigger.stop-audio":
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
  // Setup DOM pointers
  for (const key of DOM_KEYS) {
    DOM_dict[key] = document.getElementById(key);
  }
  // Other setup tasks
  start_websocket();
});

// Adjust document body size based on ?size=n parameter, if it exists
const params = window.location.search.slice(1);
let body_size = "12px";
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
