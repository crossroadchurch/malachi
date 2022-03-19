let capo = 0;
let verse_order = "";
let played_key = "";
let slide_type = "";
let cur_song_id = -1;
let current_slides = [];
let current_title = "";
let part_counts = [];
let slide_index = -1;
let websocket;
// DOM pointers
const DOM_dict = {};
const DOM_KEYS = ["playedkey", "capoarea", "verseorder", "currentslide", "nextslide", "caposelect"];

function update_music() {
  DOM_dict["playedkey"].innerHTML = played_key;
  let verse_control_list = "<ul>";
  let verse_list = "";

  if (slide_type == "song") {
    DOM_dict["capoarea"].style.display = "inline";
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
    DOM_dict["capoarea"].style.display = "none";
  } else {
    DOM_dict["capoarea"].style.display = "none";
  }
  DOM_dict["verseorder"].innerHTML = verse_control_list;

  let current_text = "";
  let next_text = "";
  let prev_chunk_is_chord = false;
  let hanging_lyric_pos = -1;

  if (slide_type == "song") {
    let current_slide_lines = current_slides[slide_index].split(/(\n)/);
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
    DOM_dict["currentslide"].innerHTML = current_text;

    let next_slide_lines = [];
    if (slide_index < current_slides.length - 1) {
      next_slide_lines = current_slides[slide_index + 1].split(/(\n)/);
    }

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
    DOM_dict["nextslide"].innerHTML = next_text;

    document.querySelectorAll("#currentslide>span").forEach((element) => {
      if (element.children.length > 1) {
        const lyricWidth = parseInt(getComputedStyle(element.querySelector(".lyric-chunk")).width);
        const chordWidth = parseInt(getComputedStyle(element.querySelector(".chord-chunk")).width);
        if (lyricWidth == 0) {
          element.querySelector(".lyric-chunk").innerHTML = "&nbsp;";
        }
        if (lyricWidth <= chordWidth) {
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
        if (lyricWidth == 0) {
          element.querySelector(".next-lyric-chunk").innerHTML = "&nbsp;";
        }
        if (lyricWidth <= chordWidth) {
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
    current_text = "<div class ='nonsong-block'><p class='nonsong-line'>";
    current_text += current_slides[slide_index].replace(/\n/g, "</p><p class='nonsong-line'>");
    current_text += "</div>";
    if (slide_index < current_slides.length - 1) {
      next_text = "<div class ='next-nonsong-block'><p class='nonsong-line'>";
      next_text += current_slides[slide_index + 1].replace(/\n/g, "</p><p class='nonsong-line'>");
      next_text += "</div>";
    } else {
      next_text = "<div></div>";
    }
    DOM_dict["currentslide"].innerHTML = current_text;
    DOM_dict["nextslide"].innerHTML = next_text;
  } else if (slide_type == "video") {
    current_text = "<div class ='nonsong-block'><p class='nonsong-line'>";
    current_text += current_slides[0].replace(/\n/g, "</p><p class='nonsong-line'>");
    current_text += "</div>";
    DOM_dict["currentslide"].innerHTML = current_text;
    DOM_dict["nextslide"].innerHTML = "";
  } else if (slide_type == "presentation") {
    DOM_dict["currentslide"].innerHTML = "";
    DOM_dict["nextslide"].innerHTML = "";
  } else {
    DOM_dict["currentslide"].innerHTML = "";
    DOM_dict["nextslide"].innerHTML = "";
  }
}

function update_capo() {
  capo = parseInt(DOM_dict["caposelect"].value);
  if (capo != 0) {
    window.localStorage.setItem(cur_song_id.toString(), capo.toString());
  } else {
    window.localStorage.removeItem(cur_song_id.toString());
  }
  websocket.send(JSON.stringify({ action: "client.set-capo", params: { capo: capo } }));
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
      DOM_dict["caposelect"].value = capo;
      websocket.send(JSON.stringify({ action: "client.set-capo", params: { capo: capo } }));
    } else {
      update_music();
    }
  } else {
    update_music();
  }
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
  slide_index = json_data.params.slide_index;
  if (JSON.stringify(json_data.params.current_item != "{}")) {
    slide_type = json_data.params.current_item.type;
    current_slides = json_data.params.current_item.slides;
    current_title = json_data.params.current_item["title"];
    if (slide_type == "song") {
      cur_song_id = json_data.params.current_item["song-id"];
      played_key = json_data.params.current_item["played-key"];
      verse_order = json_data.params.current_item["verse-order"];
      part_counts = json_data.params.current_item["part-counts"];
    } else {
      cur_song_id = -1;
      verse_order = "";
      part_counts = [];
    }
  } else {
    slide_type = "none";
    cur_song_id = -1;
    current_slides = [];
    verse_order = "";
    part_counts = [];
  }
  capo_check_update_music();
}

function update_slide_index_update(json_data) {
  slide_index = json_data.params.slide_index;
  update_music();
}

function update_item_index_update(json_data) {
  slide_index = json_data.params.slide_index;
  slide_type = json_data.params.current_item.type;
  current_slides = json_data.params.current_item.slides;
  current_title = json_data.params.current_item["title"];
  if (slide_type == "song") {
    cur_song_id = json_data.params.current_item["song-id"];
    played_key = json_data.params.current_item["played-key"];
    verse_order = json_data.params.current_item["verse-order"];
    part_counts = json_data.params.current_item["part-counts"];
  } else {
    cur_song_id = -1;
    verse_order = "";
    played_key = "";
    part_counts = [];
  }
  capo_check_update_music();
}

function start_websocket() {
  websocket = null;
  websocket = new WebSocket("ws://" + window.location.hostname + ":9001/basic");
  websocket.onmessage = function (event) {
    json_data = JSON.parse(event.data);
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
