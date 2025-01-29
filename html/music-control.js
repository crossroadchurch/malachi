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
const SECTION_AND_FILLS_REGEX = /(\[\¬\].*\[\¬\])/;
const FILL_CHORD_REGEX = /(\[[\w\+#|\/"=''\¬ ]*\])/;
const LINE_SEGMENT_REGEX = /(\[[\w\+#|\/"='' ]*\])/;
// DOM pointers
const DOM_dict = {};
// prettier-ignore
const DOM_KEYS = [
  "currentslide", "nextslide", "service_options", "service_options_btn", 
  "display_options", "display_options_btn", "music_options", "music_options_btn",
  "playedkey", "pres_controls", "verseorder", "header", "keyandcapo",
];

function view_music_options(val) {
  music_options_visible = val;
  service_options_visible = false;
  display_options_visible = false;
  if (music_options_visible) {
    DOM_dict["currentslide"].style.display = "none";
    DOM_dict["nextslide"].style.display = "none";
    DOM_dict["service_options"].style.display = "none";
    DOM_dict["service_options_btn"].style.background = "gray";
    DOM_dict["display_options"].style.display = "none";
    DOM_dict["display_options_btn"].style.background = "gray";
    DOM_dict["music_options"].style.display = "block";
    DOM_dict["music_options_btn"].style.background = "#4CAF50";
  } else {
    DOM_dict["currentslide"].style.display = "block";
    DOM_dict["nextslide"].style.display = "block";
    DOM_dict["service_options"].style.display = "none";
    DOM_dict["service_options_btn"].style.background = "gray";
    DOM_dict["display_options"].style.display = "none";
    DOM_dict["display_options_btn"].style.background = "gray";
    DOM_dict["music_options"].style.display = "none";
    DOM_dict["music_options_btn"].style.background = "gray";
  }
}

function view_display_options(val) {
  display_options_visible = val;
  service_options_visible = false;
  music_options_visible = false;
  if (display_options_visible) {
    DOM_dict["currentslide"].style.display = "none";
    DOM_dict["nextslide"].style.display = "none";
    DOM_dict["service_options"].style.display = "none";
    DOM_dict["service_options_btn"].style.background = "gray";
    DOM_dict["display_options"].style.display = "block";
    DOM_dict["display_options_btn"].style.background = "#4CAF50";
    DOM_dict["music_options"].style.display = "none";
    DOM_dict["music_options_btn"].style.background = "gray";
  } else {
    DOM_dict["currentslide"].style.display = "block";
    DOM_dict["nextslide"].style.display = "block";
    DOM_dict["service_options"].style.display = "none";
    DOM_dict["service_options_btn"].style.background = "gray";
    DOM_dict["display_options"].style.display = "none";
    DOM_dict["display_options_btn"].style.background = "gray";
    DOM_dict["music_options"].style.display = "none";
    DOM_dict["music_options_btn"].style.background = "gray";
  }
}

function view_service_options(val) {
  service_options_visible = val;
  display_options_visible = false;
  music_options_visible = false;
  if (service_options_visible) {
    DOM_dict["currentslide"].style.display = "none";
    DOM_dict["nextslide"].style.display = "none";
    DOM_dict["service_options"].style.display = "block";
    DOM_dict["service_options_btn"].style.background = "#4CAF50";
    DOM_dict["display_options"].style.display = "none";
    DOM_dict["display_options_btn"].style.background = "gray";
    DOM_dict["music_options"].style.display = "none";
    DOM_dict["music_options_btn"].style.background = "gray";
  } else {
    DOM_dict["currentslide"].style.display = "block";
    DOM_dict["nextslide"].style.display = "block";
    DOM_dict["service_options"].style.display = "none";
    DOM_dict["service_options_btn"].style.background = "gray";
    DOM_dict["display_options"].style.display = "none";
    DOM_dict["display_options_btn"].style.background = "gray";
    DOM_dict["music_options"].style.display = "none";
    DOM_dict["music_options_btn"].style.background = "gray";
  }
}

function get_song_section_html(section, prefix, display_fill_toggle) {
  let section_and_fills = section.split(SECTION_AND_FILLS_REGEX).filter((x) => x != "");
  let s_text = "";
  for (const section_part of section_and_fills) {
    if (section_part.includes("[¬]")) {
      // Process fill section (single line of chords)
      if (display_fill_toggle) {
        fill_chords = section_part.split(FILL_CHORD_REGEX).filter((x) => x != "" && x != "[¬]");
        for (const chord of fill_chords) {
          s_text += "<span class='fill-chord-chunk'>" + chord.slice(1, -1) + "</span>";
        }
        s_text += "<br />";
      }
      display_fill_toggle = !display_fill_toggle;
    } else {
      // Process regular lyrics and chords
      let slide_lines = section_part.split(/(\n)/);
      let prev_chunk_is_chord = false;
      let hanging_lyric_pos = -1;
      for (const line of slide_lines) {
        if (line == "\n") {
          s_text += "<br />";
        } else {
          let segments = line.split(LINE_SEGMENT_REGEX);
          if (segments[0] != "") {
            // Process head of line
            s_text += '<span class="' + prefix + 'lyric-chord-block">';
            s_text += '<span class="' + prefix + 'lyric-chunk">' + segments[0] + "</span></span>";
          }
          // Process tail of line: <Tail> ::= (<Chord>|(<Chord><Lyric>))*
          prev_chunk_is_chord = false;
          hanging_lyric_pos = -1;
          for (let segment = 1; segment < segments.length; segment++) {
            let seg = segments[segment];
            if (seg.charAt(0) == "[") {
              // Current is chord
              seg = seg.replace(/\[[\s]?/, '<span class="' + prefix + 'chord-chunk">');
              seg = seg.replace(/[\s]?\]/, "</span>");
              if (prev_chunk_is_chord == true) {
                s_text += '</span><span class="' + prefix + 'lyric-chord-block">' + seg;
              } else {
                s_text += '<span class="' + prefix + 'lyric-chord-block">' + seg;
              }
              prev_chunk_is_chord = true;
            } else {
              // Current is lyric
              if (hanging_lyric_pos > 0 && seg.charAt(0).match(/[a-z]/i)) {
                s_text =
                  s_text.slice(0, hanging_lyric_pos + 1) +
                  " midword" +
                  s_text.slice(hanging_lyric_pos + 1);
              }
              // recalc hanging_lyric_pos based on current_text length + offset
              hanging_lyric_pos = s_text.length + 23 + prefix.length;
              s_text += '<span class="' + prefix + 'lyric-chunk">' + seg + "</span></span>";
              prev_chunk_is_chord = false;
              if (!seg.slice(-1).match(/[a-z]/i)) {
                hanging_lyric_pos = -1;
              }
            }
          }
          if (prev_chunk_is_chord == true) {
            s_text += "</span>";
          }
        }
      }
      s_text += "<br />";
    }
  }
  return { text: s_text, toggle: display_fill_toggle };
}

function process_chord_widths(slide_id, prefix) {
  const chunks = document.querySelectorAll("#" + slide_id + ">span");
  for (let i = 0; i < chunks.length; i++) {
    const chunk = chunks[i];
    if (chunk.children.length <= 1) {
      continue;
    }
    const cur_left = chunk.getBoundingClientRect().left;
    const next_left = i < chunks.length - 1 ? chunks[i + 1].getBoundingClientRect().left : 1000000;
    const midword = chunk.querySelectorAll(".midword").length > 0;
    const l_width = chunk.querySelector("." + prefix + "lyric-chunk").getBoundingClientRect().width;
    const c_width = chunk.querySelector("." + prefix + "chord-chunk").getBoundingClientRect().width;
    if (l_width == 0) {
      chunk.querySelector("." + prefix + "lyric-chunk").innerHTML = "&nbsp;";
    }

    if (midword) {
      if (l_width <= c_width) {
        // Hyphen to space out lyrics over long chords
        const spacer_width = c_width - parseInt(getComputedStyle(chunk).width);
        chunk.insertAdjacentHTML(
          "beforeend",
          '<span class="' + prefix + 'midword-spacer">-</span>'
        );
        if (spacer_width < body_size_int) {
          chunk.querySelector("." + prefix + "midword-spacer").style.width = body_size_int + "px";
        } else {
          chunk.querySelector("." + prefix + "midword-spacer").style.width = spacer_width + "px";
        }
      } else if (next_left < cur_left) {
        // Hyphen at end of line
        chunk.insertAdjacentHTML(
          "beforeend",
          '<span class="' + prefix + 'midword-spacer">-</span>'
        );
        chunk.querySelector("." + prefix + "midword-spacer").style.width = body_size_int + "px";
      }
    } else {
      if (l_width <= c_width) {
        chunk.style.paddingRight =
          c_width - parseInt(getComputedStyle(chunk).width) + body_size_int + "px";
      }
    }
  }
}

function update_played_key() {
  DOM_dict["playedkey"].innerHTML = played_key;
  if (played_key === "") {
    DOM_dict["music_options_btn"].style.display = "none";
    view_music_options(false);
  } else {
    DOM_dict["music_options_btn"].style.display = "inline-block";
    document.querySelectorAll("#key_buttons button").forEach((elt) => {
      elt.style.background = "gray";
    });
    document.querySelector(
      "#key_buttons button:nth-child(" + (valid_keys.indexOf(noncapo_key) + 1) + ")"
    ).style.background = "#4CAF50";
    document.querySelectorAll("#capo_buttons button").forEach((elt) => {
      elt.style.background = "gray";
    });
    document.querySelector("#capo_buttons button:nth-child(" + (capo + 1) + ")").style.background =
      "#4CAF50";
  }
}

function update_verse_order() {
  let verse_list = "";
  let verses = verse_order.split(" ");
  if (slide_type == "song") {
    let part_counts_sum = 0;
    for (const [idx, verse] of verses.entries()) {
      if (slide_index >= part_counts_sum && slide_index < part_counts_sum + part_counts[idx]) {
        verse_list +=
          "<button class='verse-button current-verse-button' onclick='change_verse(" +
          part_counts_sum +
          ")'>" +
          verse.toUpperCase() +
          "</button>";
      } else {
        verse_list +=
          "<button class='verse-button' onclick='change_verse(" +
          part_counts_sum +
          ")'>" +
          verse.toUpperCase() +
          "</button>";
      }
      part_counts_sum += part_counts[idx];
    }
  } else if (slide_type != "none") {
    verse_list = "<span class='non-song-title'>" + service_items[item_index] + "</span>";
  }
  DOM_dict["verseorder"].innerHTML = verse_list;

  /* Update widths of verse buttons to make sure they can all be seen */
  const header_width = Math.floor(DOM_dict["header"].offsetWidth);
  const keyandcapo_width = Math.ceil(DOM_dict["keyandcapo"].offsetWidth);
  const button_margin = parseInt(
    getComputedStyle(document.querySelector(".verse-button")).marginRight
  );
  const buttons_width = header_width - keyandcapo_width - button_margin * verses.length;
  const max_button_width = Math.floor(buttons_width / verses.length);
  const pref_width = 6 * parseInt(document.querySelector("html").style.fontSize); /* 6rem */
  const actual_width = Math.min(pref_width, max_button_width);
  document.querySelectorAll(".verse-button").forEach((elt) => {
    elt.style.width = actual_width - 1 + "px";
  });
}

function update_music() {
  update_played_key();
  update_verse_order();

  if (slide_type == "presentation") {
    DOM_dict["pres_controls"].style.display = "inline-block";
  } else {
    DOM_dict["pres_controls"].style.display = "none";
  }

  let current_text = "";
  let next_text = "";
  if (slide_type == "song") {
    current_result = get_song_section_html(current_slides[slide_index], "", true);
    current_text = current_result.text;
    if (slide_index < current_slides.length - 1) {
      // prettier-ignore
      next_text = get_song_section_html(current_slides[slide_index + 1], "next-", current_result.toggle).text;
    }
  } else if (slide_type == "bible") {
    current_text = '<div class ="nonsong-block"><p class="nonsong-line">';
    current_text += current_slides[slide_index].replace(/\n/g, '</p><p class="nonsong-line">');
    current_text += "</div>";
    if (slide_index < current_slides.length - 1) {
      next_text = '<div class ="next-nonsong-block"><p class="nonsong-line">';
      next_text += current_slides[slide_index + 1].replace(/\n/g, '</p><p class="nonsong-line">');
      next_text += "</div>";
    }
  } else if (slide_type == "video") {
    current_text = '<div class ="nonsong-block"><p class="nonsong-line">';
    current_text += current_slides[0].replace(/\n/g, '</p><p class="nonsong-line">');
    current_text += "</div>";
  }

  DOM_dict["currentslide"].innerHTML = current_text;
  DOM_dict["nextslide"].innerHTML = next_text;

  if (slide_type == "song") {
    process_chord_widths("currentslide", "");
    process_chord_widths("nextslide", "next-");
  }
}

function update_menu() {
  let temp_menu = "";
  if (service_items.length > 0) {
    // Build up song choice menu, place divider at current song location
    for (const [idx, item] of service_items.entries()) {
      if (idx != item_index) {
        temp_menu += "<button class='menu-list-item' ";
        temp_menu += "onclick='change_song(" + idx + ")'>";
        temp_menu += item + "</button>";
      } else {
        temp_menu += "<button class='menu-list-item current-song-item'>";
        temp_menu += item + "</button>";
      }
    }
  }
  if (temp_menu != menustring) {
    DOM_dict["service_options"].innerHTML = temp_menu;
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

function load_current_item(cur_item) {
  slide_type = cur_item.type;
  current_slides = cur_item.slides;
  cur_song_id = -1;
  played_key = "";
  noncapo_key = "";
  verse_order = "";
  part_counts = [];
  if (slide_type == "song") {
    cur_song_id = cur_item["song-id"];
    noncapo_key = cur_item["non-capo-key"];
    if (cur_item["uses-chords"]) {
      played_key = cur_item["played-key"];
    }
    verse_order = cur_item["verse-order"];
    part_counts = cur_item["part-counts"];
  }
}

function update_service_overview_update(json_data) {
  item_index = json_data.params.item_index;
  slide_index = json_data.params.slide_index;
  service_items = json_data.params.items;
  if (JSON.stringify(json_data.params.current_item) != "{}") {
    load_current_item(json_data.params.current_item);
  } else {
    load_current_item({ type: "none", slides: [] });
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
  load_current_item(json_data.params.current_item);
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
  for (const key of DOM_KEYS) {
    DOM_dict[key] = document.getElementById(key);
  }
  start_websocket();
});

// Adjust document body size based on ?size=n parameter, if it exists
const params = window.location.search.slice(1);
let body_size_int = 16;
let body_size = "16px";
if (params != "") {
  for (const param of params.split("&")) {
    let param_pair = param.split("=");
    if (param_pair[0] == "size") {
      body_size_int = parseInt(param_pair[1]);
      body_size = param_pair[1] + "px";
    }
  }
}
document.querySelector("html").style.fontSize = body_size;
