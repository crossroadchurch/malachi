let websocket;
let slide_type = "";
let current_item;
let service_items = [];
let current_slides = [];
let slide_index = -1;
let item_index = -1;
let screen_state = false;
let saved_text_size = parseInt(window.localStorage.getItem("text_size"));
let saved_text_mode = window.localStorage.getItem("text_mode");
const DAY_MODE = "day";
const NIGHT_MODE = "night";
const LINE_SEGMENT_REGEX = /\[[\w\+\¬#|\/"='' ]*\]/;

const DOM_dict = {};
function DOM_get(key) {
  if (!(key in DOM_dict)) {
    DOM_dict[key] = document.getElementById(key);
  }
  return DOM_dict[key];
}

function update_words() {
  let current_text = "";

  if (slide_type == "song") {
    let current_slide_lines = current_slides[slide_index].split(/\n/);
    for (const line of current_slide_lines) {
      current_text += "<p>";
      for (const segment of line.split(LINE_SEGMENT_REGEX)) {
        current_text += segment;
      }
      current_text += "</p>";
    }
  } else if (slide_type == "bible") {
    current_text = "<p>" + current_slides[slide_index] + "</p>";
  }
  DOM_get("currentslide").innerHTML = current_text;
}

function update_display_init(json_data) {
  Toastify({
    text: "Connected to Malachi server",
    gravity: "bottom",
    position: "left",
    style: { background: "#4caf50" },
  }).showToast();
  if (json_data.params.screen_state == "on") {
    screen_state = true;
    DOM_get("songarea").style.display = "block";
  } else {
    screen_state = false;
    DOM_get("songarea").style.display = "none";
  }
  update_service_overview_update(json_data);
}

function update_display_state(json_data) {
  if (json_data.params.state == "on") {
    screen_state = true;
    DOM_get("songarea").style.display = "block";
  } else {
    screen_state = false;
    DOM_get("songarea").style.display = "none";
  }
}

function load_current_item(cur_item) {
  slide_type = cur_item.type;
  current_slides = cur_item.slides;
}

function update_service_overview_update(json_data) {
  item_index = json_data.params.item_index;
  slide_index = json_data.params.slide_index;
  service_items = json_data.params.items;
  current_item = json_data.params.current_item;
  if (JSON.stringify(json_data.params.current_item) != "{}") {
    load_current_item(current_item);
  } else {
    load_current_item({ type: "none", slides: [], title: "" });
  }
  update_words();
}

function update_slide_index_update(json_data) {
  slide_index = json_data.params.slide_index;
  update_words();
}

function update_item_index_update(json_data) {
  item_index = json_data.params.item_index;
  slide_index = json_data.params.slide_index;
  current_item = json_data.params.current_item;
  load_current_item(current_item);
  update_words();
}

function increase_text_size() {
  saved_text_size += 5;
  window.localStorage.setItem("text_size", saved_text_size);
  DOM_get("songarea").style.fontSize = saved_text_size + "px";
}

function decrease_text_size() {
  if (saved_text_size > 20) {
    saved_text_size -= 5;
    window.localStorage.setItem("text_size", saved_text_size);
    DOM_get("songarea").style.fontSize = saved_text_size + "px";
  }
}

function update_day_night_mode(day_night_mode) {
  if (day_night_mode == NIGHT_MODE) {
    document.querySelector("body").style.backgroundColor = "#14161d";
    DOM_get("currentslide").style.color = "white";
    DOM_get("text_up_btn").classList.replace("light_button", "dark_button");
    DOM_get("text_down_btn").classList.replace("light_button", "dark_button");
    DOM_get("day_night_btn").classList.replace("light_button", "dark_button");
  } else {
    document.querySelector("body").style.backgroundColor = "white";
    DOM_get("currentslide").style.color = "#14161d";
    DOM_get("text_up_btn").classList.replace("dark_button", "light_button");
    DOM_get("text_down_btn").classList.replace("dark_button", "light_button");
    DOM_get("day_night_btn").classList.replace("dark_button", "light_button");
  }
}

function toggle_text_mode() {
  if (saved_text_mode == NIGHT_MODE) {
    saved_text_mode = DAY_MODE;
  } else {
    saved_text_mode = NIGHT_MODE;
  }
  window.localStorage.setItem("text_mode", saved_text_mode);
  update_day_night_mode(saved_text_mode);
}

function start_websocket() {
  websocket = null;
  websocket = new WebSocket("ws://" + window.location.hostname + ":9001/display");
  websocket.onmessage = function (event) {
    let json_data = JSON.parse(event.data);
    console.log(json_data);
    switch (json_data.action) {
      case "update.display-init":
        update_display_init(json_data);
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
      case "update.display-state":
        update_display_state(json_data);
        break;
      case "trigger.play-video":
      case "trigger.pause-video":
      case "trigger.stop-video":
      case "trigger.seek-video":
      case "update.video-loop":
      case "trigger.stop-audio":
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
  if (saved_text_size == null || isNaN(saved_text_size)) {
    saved_text_size = 60;
    window.localStorage.setItem("text_size", saved_text_size);
  }
  if (saved_text_mode == null) {
    saved_text_mode = NIGHT_MODE;
    window.localStorage.setItem("text_mode", saved_text_mode);
  }
  DOM_get("songarea").style.fontSize = saved_text_size + "px";
  update_day_night_mode(saved_text_mode);
  start_websocket();
});
