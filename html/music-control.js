let capo = 0;
let menustring = "";
let verse_order = "";
let played_key = "";
let noncapo_key = "";
let slide_type = "";
let service_items = [];
let current_slides = [];
let part_counts = [];
let slide_index = -1;
let item_index = -1;
let cur_song_id = -1;
let websocket;
const valid_keys = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
let music_options_visible = false;
let display_options_visible = false;
let service_options_visible = false;

function view_music_options(val) {
  music_options_visible = val;
  service_options_visible = false;
  display_options_visible = false;
  if (music_options_visible) {
    document.getElementById("currentslide").style.display = "none";
    document.getElementById("nextslide").style.display = "none";
    document.getElementById("service-options").style.display = "none";
    document.getElementById("service-options-btn").style.background = "gray";
    document.getElementById("display-options").style.display = "none";
    document.getElementById("display-options-btn").style.background = "gray";
    document.getElementById("music-options").style.display = "block";
    document.getElementById("music-options-btn").style.background = "#4CAF50";
  } else {
    document.getElementById("currentslide").style.display = "block";
    document.getElementById("nextslide").style.display = "block";
    document.getElementById("service-options").style.display = "none";
    document.getElementById("service-options-btn").style.background = "gray";
    document.getElementById("display-options").style.display = "none";
    document.getElementById("display-options-btn").style.background = "gray";
    document.getElementById("music-options").style.display = "none";
    document.getElementById("music-options-btn").style.background = "gray";
  }
}

function view_display_options(val) {
  display_options_visible = val;
  service_options_visible = false;
  music_options_visible = false;
  if (display_options_visible) {
    document.getElementById("currentslide").style.display = "none";
    document.getElementById("nextslide").style.display = "none";
    document.getElementById("service-options").style.display = "none";
    document.getElementById("service-options-btn").style.background = "gray";
    document.getElementById("display-options").style.display = "block";
    document.getElementById("display-options-btn").style.background = "#4CAF50";
    document.getElementById("music-options").style.display = "none";
    document.getElementById("music-options-btn").style.background = "gray";
  } else {
    document.getElementById("currentslide").style.display = "block";
    document.getElementById("nextslide").style.display = "block";
    document.getElementById("service-options").style.display = "none";
    document.getElementById("service-options-btn").style.background = "gray";
    document.getElementById("display-options").style.display = "none";
    document.getElementById("display-options-btn").style.background = "gray";
    document.getElementById("music-options").style.display = "none";
    document.getElementById("music-options-btn").style.background = "gray";
  }
}

function view_service_options(val) {
  service_options_visible = val;
  display_options_visible = false;
  music_options_visible = false;
  if (service_options_visible) {
    document.getElementById("currentslide").style.display = "none";
    document.getElementById("nextslide").style.display = "none";
    document.getElementById("service-options").style.display = "block";
    document.getElementById("service-options-btn").style.background = "#4CAF50";
    document.getElementById("display-options").style.display = "none";
    document.getElementById("display-options-btn").style.background = "gray";
    document.getElementById("music-options").style.display = "none";
    document.getElementById("music-options-btn").style.background = "gray";
  } else {
    document.getElementById("currentslide").style.display = "block";
    document.getElementById("nextslide").style.display = "block";
    document.getElementById("service-options").style.display = "none";
    document.getElementById("service-options-btn").style.background = "gray";
    document.getElementById("display-options").style.display = "none";
    document.getElementById("display-options-btn").style.background = "gray";
    document.getElementById("music-options").style.display = "none";
    document.getElementById("music-options-btn").style.background = "gray";
  }
}

function update_music() {
  document.getElementById("playedkey").innerHTML = played_key;
  if (played_key === "") {
    document.getElementById("music-options-btn").style.display = "none";
    view_music_options(false);
  } else {
    document.getElementById("music-options-btn").style.display = "inline-block";
    document.querySelectorAll("#key-buttons button").forEach((elt) => {
      elt.style.background = "gray";
    });
    document.querySelector(
      "#key-buttons button:nth-child(" + (valid_keys.indexOf(noncapo_key) + 1) + ")"
    ).style.background = "#4CAF50";
    document.querySelectorAll("#capo-buttons button").forEach((elt) => {
      elt.style.background = "gray";
    });
    document.querySelector("#capo-buttons button:nth-child(" + (capo + 1) + ")").style.background =
      "#4CAF50";
  }
  let verse_control_list = "";
  let verse_list = "";

  if (slide_type == "presentation") {
    document.getElementById("pres-controls").style.display = "inline-block";
  } else {
    document.getElementById("pres-controls").style.display = "none";
  }

  if (slide_type == "song") {
    verse_list = verse_order.split(" ");
    let part_counts_sum = 0;
    for (let i = 0; i < verse_list.length; i++) {
      if (slide_index >= part_counts_sum && slide_index < part_counts_sum + part_counts[i]) {
        verse_control_list +=
          "<button class='verse-button current-verse-button' onclick='change_verse(" +
          part_counts_sum +
          ")'>" +
          verse_list[i].toUpperCase() +
          "</button>";
      } else {
        verse_control_list +=
          "<button class='verse-button' onclick='change_verse(" +
          part_counts_sum +
          ")'>" +
          verse_list[i].toUpperCase() +
          "</button>";
      }
      part_counts_sum += part_counts[i];
    }
  } else if (slide_type != undefined) {
    verse_control_list = "<span class='non-song-title'>" + service_items[item_index] + "</span>";
  }
  document.getElementById("verseorder").innerHTML = verse_control_list;

  /* Update widths of verse buttons to make sure they can all be seen */
  const header_width = Math.floor(document.getElementById("header").offsetWidth);
  const keyandcapo_width = Math.ceil(document.getElementById("keyandcapo").offsetWidth);
  const button_margin = parseInt(
    getComputedStyle(document.querySelector(".verse-button")).marginRight
  );
  const buttons_width = header_width - keyandcapo_width - button_margin * verse_list.length;
  const max_button_width = Math.floor(buttons_width / verse_list.length);
  const pref_width = 6 * parseInt(document.querySelector("html").style.fontSize); /* 6rem */
  const actual_width = Math.min(pref_width, max_button_width);
  document.querySelectorAll(".verse-button").forEach((elt) => {
    elt.style.width = actual_width - 1 + "px";
  });

  let current_text = "";
  let next_text = "";

  if (slide_type == "song") {
    let current_slide_lines = current_slides[slide_index].split(/(\n)/);
    let prev_chunk_is_chord = false;
    let hanging_lyric_pos = -1;

    for (const line in current_slide_lines) {
      if (current_slide_lines[line] == "\n") {
        current_text += "<br />";
      } else {
        let current_line_segments = current_slide_lines[line].split(/(\[[\w\+#\/"='' ]*\])/);
        if (current_line_segments[0] != "") {
          // Process head of line
          current_text +=
            '<span class="lyric-chord-block"><span class="lyric-chunk">' +
            current_line_segments[0] +
            "</span></span>";
        }
        // Process tail of line: <Tail> ::= (<Chord>|(<Chord><Lyric>))*
        prev_chunk_is_chord = false;
        hanging_lyric_pos = -1;
        for (let segment = 1; segment < current_line_segments.length; segment++) {
          let cur_seg = current_line_segments[segment];
          if (cur_seg.charAt(0) == "[") {
            // Current is chord
            cur_seg = cur_seg.replace(/\[[\s]?/, '<span class="chord-chunk">');
            cur_seg = cur_seg.replace(/[\s]?\]/, "</span>");
            if (prev_chunk_is_chord == true) {
              current_text += '</span><span class="lyric-chord-block">' + cur_seg;
            } else {
              current_text += '<span class="lyric-chord-block">' + cur_seg;
            }
            prev_chunk_is_chord = true;
          } else {
            // Current is lyric
            if (hanging_lyric_pos > 0 && cur_seg.charAt(0).match(/[a-z]/i)) {
              current_text =
                current_text.slice(0, hanging_lyric_pos + 1) +
                " midword" +
                current_text.slice(hanging_lyric_pos + 1);
            }
            // recalc hanging_lyric_pos based on current_text length + offset
            hanging_lyric_pos = current_text.length + 23;
            current_text += '<span class="lyric-chunk">' + cur_seg + "</span></span>";
            prev_chunk_is_chord = false;
            if (!cur_seg.slice(-1).match(/[a-z]/i)) {
              hanging_lyric_pos = -1;
            }
          }
        }
        if (prev_chunk_is_chord == true) {
          current_text += "</span>";
        }
      }
    }
    document.getElementById("currentslide").innerHTML = current_text;

    let next_slide_lines = [];
    if (slide_index < current_slides.length - 1) {
      next_slide_lines = current_slides[slide_index + 1].split(/(\n)/);
    }
    let next_text = "";

    for (const line in next_slide_lines) {
      if (next_slide_lines[line] == "\n") {
        next_text += "<br />";
      } else {
        let next_line_segments = next_slide_lines[line].split(/(\[[\w\+#\/"='' ]*\])/);
        if (next_line_segments[0] != "") {
          // Process head of line
          next_text +=
            '<span class="next-lyric-chord-block"><span class="next-lyric-chunk">' +
            next_line_segments[0] +
            "</span></span>";
        }
        // Process tail of line: <Tail> ::= (<Chord>|(<Chord><Lyric>))*
        prev_chunk_is_chord = false;
        hanging_lyric_pos = -1;
        for (let segment = 1; segment < next_line_segments.length; segment++) {
          let cur_seg = next_line_segments[segment];
          if (cur_seg.charAt(0) == "[") {
            // Current is chord
            cur_seg = cur_seg.replace(/\[[\s]?/, '<span class="next-chord-chunk">');
            cur_seg = cur_seg.replace(/[\s]?\]/, "</span>");
            if (prev_chunk_is_chord == true) {
              next_text += '</span><span class="next-lyric-chord-block">' + cur_seg;
            } else {
              next_text += '<span class="next-lyric-chord-block">' + cur_seg;
            }
            prev_chunk_is_chord = true;
          } else {
            // Current is lyric
            if (hanging_lyric_pos > 0 && cur_seg.charAt(0).match(/[a-z]/i)) {
              next_text =
                next_text.slice(0, hanging_lyric_pos + 1) +
                " midword" +
                next_text.slice(hanging_lyric_pos + 1);
            }
            // recalc hanging_lyric_pos based on current_text length + offset
            hanging_lyric_pos = next_text.length + 28;
            next_text += '<span class="next-lyric-chunk">' + cur_seg + "</span></span>";
            prev_chunk_is_chord = false;
            if (!cur_seg.slice(-1).match(/[a-z]/i)) {
              hanging_lyric_pos = -1;
            }
          }
        }
        if (prev_chunk_is_chord == true) {
          next_text += "</span>";
        }
      }
    }
    document.getElementById("nextslide").innerHTML = next_text;

    document.querySelectorAll("#currentslide>span").forEach((element) => {
      if (element.children.length > 1) {
        const lyricWidth = parseInt(getComputedStyle(element.querySelector(".lyric-chunk")).width);
        const chordWidth = parseInt(getComputedStyle(element.querySelector(".chord-chunk")).width);
        if (lyricWidth < chordWidth) {
          if (element.querySelectorAll(".midword").length > 0) {
            const spacerWidth = chordWidth - parseInt(getComputedStyle(element).width);
            element.insertAdjacentHTML("beforeend", '<span class="midword-spacer">-</span>');
            if (spacerWidth < body_size_int) {
              element.querySelector(".midword-spacer").style.width = body_size_int + "px";
            } else {
              element.querySelector(".midword-spacer").style.width = spacerWidth + "px";
            }
          } else {
            element.style.paddingRight =
              chordWidth - parseInt(getComputedStyle(element).width) + "px";
          }
        }
      }
    });

    document.querySelectorAll("#nextslide>span").forEach((element) => {
      if (element.children.length > 1) {
        const lyricWidth = parseInt(
          getComputedStyle(element.querySelector(".next-lyric-chunk")).width
        );
        const chordWidth = parseInt(
          getComputedStyle(element.querySelector(".next-chord-chunk")).width
        );
        if (lyricWidth < chordWidth) {
          if (element.querySelectorAll(".midword").length > 0) {
            const spacerWidth = chordWidth - parseInt(getComputedStyle(element).width);
            element.insertAdjacentHTML("beforeend", '<span class="next-midword-spacer">-</span>');
            if (spacerWidth < body_size_int) {
              element.querySelector(".next-midword-spacer").style.width = body_size_int + "px";
            } else {
              element.querySelector(".next-midword-spacer").style.width = spacerWidth + "px";
            }
          } else {
            element.style.paddingRight =
              chordWidth - parseInt(getComputedStyle(element).width) + "px";
          }
        }
      }
    });
  } else if (slide_type == "bible") {
    current_text = '<div class ="nonsong-block"><p class="nonsong-line">';
    current_text += current_slides[slide_index].replace(/\n/g, '</p><p class="nonsong-line">');
    current_text += "</div>";
    if (slide_index < current_slides.length - 1) {
      next_text = '<div class ="next-nonsong-block"><p class="nonsong-line">';
      next_text += current_slides[slide_index + 1].replace(/\n/g, '</p><p class="nonsong-line">');
      next_text += "</div>";
    } else {
      next_text = "<div></div>";
    }
    document.getElementById("currentslide").innerHTML = current_text;
    document.getElementById("nextslide").innerHTML = next_text;
  } else if (slide_type == "video") {
    current_text = '<div class ="nonsong-block"><p class="nonsong-line">';
    current_text += current_slides[0].replace(/\n/g, '</p><p class="nonsong-line">');
    current_text += "</div>";
    document.getElementById("currentslide").innerHTML = current_text;
    document.getElementById("nextslide").innerHTML = "";
  } else {
    document.getElementById("currentslide").innerHTML = "";
    document.getElementById("nextslide").innerHTML = "";
  }
}

function update_menu() {
  let temp_menu = "";
  if (service_items.length > 0) {
    // Build up song choice menu, place divider at current song location
    for (let i = 0; i < service_items.length; i++) {
      if (i != item_index) {
        temp_menu += "<button class='menu-list-item' ";
        temp_menu += "onclick='change_song(" + i + ")'>";
        temp_menu += service_items[i] + "</button>";
      } else {
        temp_menu += "<button class='menu-list-item current-song-item'>";
        temp_menu += service_items[i] + "</button>";
      }
    }
  }
  if (temp_menu != menustring) {
    document.getElementById("service-options").innerHTML = temp_menu;
    menustring = temp_menu;
  }
}

function display_on() {
  view_display_options(false);
  websocket.send(
    JSON.stringify({
      action: "command.set-display-state",
      params: { state: "on" },
    })
  );
}

function display_off() {
  view_display_options(false);
  websocket.send(
    JSON.stringify({
      action: "command.set-display-state",
      params: { state: "off" },
    })
  );
}

function change_capo(new_capo) {
  capo = new_capo;
  if (capo != 0) {
    window.localStorage.setItem(cur_song_id.toString(), capo.toString());
  } else {
    window.localStorage.removeItem(cur_song_id.toString());
  }
  websocket.send(JSON.stringify({ action: "client.set-capo", params: { capo: capo } }));
  view_music_options(false);
}

function change_key(new_key) {
  if (played_key !== "") {
    const transpose_amount = (valid_keys.indexOf(new_key) - valid_keys.indexOf(noncapo_key)) % 12;
    websocket.send(
      JSON.stringify({
        action: "command.transpose-by",
        params: { amount: transpose_amount },
      })
    );
  }
  view_music_options(false);
}

function next_slide() {
  if (slide_type == "presentation") {
    websocket.send(JSON.stringify({ action: "command.next-presentation-slide", params: {} }));
  } else {
    websocket.send(JSON.stringify({ action: "command.next-slide", params: {} }));
  }
}

function previous_slide() {
  if (slide_type == "presentation") {
    websocket.send(JSON.stringify({ action: "command.prev-presentation-slide", params: {} }));
  } else {
    websocket.send(JSON.stringify({ action: "command.previous-slide", params: {} }));
  }
}

function start_presentation() {
  if (slide_type == "presentation") {
    websocket.send(JSON.stringify({ action: "command.start-presentation", params: {} }));
  }
}

function stop_presentation() {
  if (slide_type == "presentation") {
    websocket.send(JSON.stringify({ action: "command.stop-presentation", params: {} }));
  }
}

function n_s() {
  websocket.send(JSON.stringify({ action: "command.next-slide", params: {} }));
}

function p_s() {
  websocket.send(JSON.stringify({ action: "command.previous-slide", params: {} }));
}

function n_i() {
  websocket.send(JSON.stringify({ action: "command.next-item", params: {} }));
}

function p_i() {
  websocket.send(JSON.stringify({ action: "command.previous-item", params: {} }));
}

function change_verse(id) {
  websocket.send(JSON.stringify({ action: "command.goto-slide", params: { index: id } }));
}

function change_song(id) {
  view_service_options(false);
  websocket.send(JSON.stringify({ action: "command.goto-item", params: { index: id } }));
}

function capo_check_update_music() {
  if (cur_song_id != -1) {
    let saved_capo = window.localStorage.getItem(cur_song_id.toString());
    if (saved_capo == null) {
      saved_capo = 0;
    } else {
      saved_capo = parseInt(saved_capo);
    }
    if (saved_capo != capo) {
      capo = saved_capo;
      websocket.send(JSON.stringify({ action: "client.set-capo", params: { capo: capo } }));
    } else {
      update_music();
    }
  } else {
    update_music();
  }
}

function update_leader_init(json_data) {
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
  if (JSON.stringify(json_data.params.current_item != "{}")) {
    slide_type = json_data.params.current_item.type;
    current_slides = json_data.params.current_item.slides;
    if (slide_type == "song") {
      cur_song_id = json_data.params.current_item["song-id"];
      noncapo_key = json_data.params.current_item["non-capo-key"];
      played_key = json_data.params.current_item["played-key"];
      verse_order = json_data.params.current_item["verse-order"];
      part_counts = json_data.params.current_item["part-counts"];
    } else {
      cur_song_id = -1;
      verse_order = "";
      part_counts = [];
      noncapo_key = "";
      played_key = "";
    }
  } else {
    slide_type = "none";
    cur_song_id = -1;
    current_slides = [];
    verse_order = "";
    part_counts = [];
    noncapo_key = "";
    played_key = "";
  }
  if (json_data.params.screen_state == "on") {
    document.querySelector("body").style.borderTop = "6px solid #4CAF50";
  } else {
    document.querySelector("body").style.borderTop = "6px solid red";
  }
  update_menu();
  capo_check_update_music();
}

function update_slide_index_update(json_data) {
  slide_index = json_data.params.slide_index;
  update_music();
}

function update_item_index_update(json_data) {
  item_index = json_data.params.item_index;
  slide_index = json_data.params.slide_index;
  slide_type = json_data.params.current_item.type;
  current_slides = json_data.params.current_item.slides;
  if (slide_type == "song") {
    cur_song_id = json_data.params.current_item["song-id"];
    noncapo_key = json_data.params.current_item["non-capo-key"];
    played_key = json_data.params.current_item["played-key"];
    verse_order = json_data.params.current_item["verse-order"];
    part_counts = json_data.params.current_item["part-counts"];
  } else {
    cur_song_id = -1;
    verse_order = "";
    played_key = "";
    noncapo_key = "";
    part_counts = [];
  }
  update_menu();
  capo_check_update_music();
}

function update_display_state(json_data) {
  if (json_data.params.state == "on") {
    document.querySelector("body").style.borderTop = "6px solid #4CAF50";
  } else {
    document.querySelector("body").style.borderTop = "6px solid red";
  }
}

function start_websocket() {
  websocket = null;
  websocket = new WebSocket("ws://" + window.location.hostname + ":9001/leader");
  websocket.onmessage = function (event) {
    let json_data = JSON.parse(event.data);
    console.log(json_data);
    switch (json_data.action) {
      case "update.leader-init":
        update_leader_init(json_data);
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
      case "result.capture-update":
      case "update.stop-capture":
      case "update.capture-ready":
      case "response.set-display-state":
      case "response.next-slide":
      case "response.previous-slide":
      case "response.next-item":
      case "response.previous-item":
      case "response.next-presentation-slide":
      case "response.prev-presentation-slide":
      case "response.start-presentation":
      case "response.stop-presentation":
      case "response.goto-slide":
      case "response.goto-item":
      case "response.transpose-by":
      case "response.unlock-socket":
        break;
      default:
        console.error("Unsupported event", json_data);
    }
  };
  websocket.onclose = function (event) {
    console.log("Connection was closed/refused by server (error code " + event.code + ")");
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
  start_websocket();
});

// Adjust document body size based on ?size=n parameter, if it exists
const params = window.location.search.slice(1);
let body_size_int = 16;
let body_size = "16px";
if (params != "") {
  const param_arr = params.split("&");
  for (let i = 0; i < param_arr.length; i++) {
    let param_pair = param_arr[i].split("=");
    if (param_pair[0] == "size") {
      body_size_int = parseInt(param_pair[1]);
      body_size = param_pair[1] + "px";
    }
  }
}
document.querySelector("html").style.fontSize = body_size;
