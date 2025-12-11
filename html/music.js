let websocket;
let capo = 0;
let verse_order = "";
let played_key = "";
let slide_type = "";
let cur_song_id = -1;
let current_slides = [];
let current_title = "";
let part_counts = [];
let slide_index = -1;
let chord_pref = window.localStorage.getItem("chord_pref");
const FULL_CHORDS = "0";
const SIMPLE_CHORDS = "1";
const BASS_EMPHASIS = "2";
const BASS_ONLY = "3";
const SECTION_AND_FILLS_REGEX = /(\[\¬\].*\[\¬\])/;
const FILL_CHORD_REGEX = /(\[[\w\+\¬#|\/"='' ]*\])/;
const LINE_SEGMENT_REGEX = /(\[[\w\+#|\/"='' ]*\])/;
// prettier-ignore
const VALID_KEYS = ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B"];

const DOM_dict = {};
function DOM_get(key) {
  if (!(key in DOM_dict)) {
    DOM_dict[key] = document.getElementById(key);
  }
  return DOM_dict[key];
}

function parse_chord(chord) {
  let p_bass = "";
  let p_modifiers = "";
  let p_root = "";
  let bassless_chord = "";
  // Split out bass note, if valid
  if (chord.lastIndexOf("/") > -1) {
    bass = chord.substring(chord.lastIndexOf("/") + 1);
    if (VALID_KEYS.includes(bass)) {
      p_bass = bass;
      bassless_chord = chord.substring(0, chord.lastIndexOf("/") + 1);
    } else {
      bassless_chord = chord;
    }
  } else {
    bassless_chord = chord;
  }
  // Split out root note, if valid
  if (bassless_chord.length > 1 && ["b", "#"].includes(bassless_chord[1])) {
    root = bassless_chord.substring(0, 2);
    modifiers = bassless_chord.substring(2);
  } else {
    root = bassless_chord[0];
    modifiers = bassless_chord.substring(1);
  }
  if (VALID_KEYS.includes(root)) {
    p_root = root;
    p_modifiers = modifiers;
  } else {
    p_modifiers = bassless_chord;
  }
  return [p_root, p_modifiers, p_bass];
}

function get_chord_chunk_html(chord, prefix, prev_chord) {
  p_chord = parse_chord(chord);
  switch (chord_pref) {
    case SIMPLE_CHORDS:
      if (p_chord[1][0] == "m") {
        chord = p_chord[0] + "m";
      } else {
        chord = p_chord[0];
      }
      break;
    case BASS_EMPHASIS:
      if (p_chord[2] == "") {
        chord = p_chord[0] + "<span class='faded-chord'>" + p_chord[1] + "</span>";
      } else {
        chord = "<span class='faded-chord'>" + p_chord[0] + p_chord[1] + "</span>" + p_chord[2];
      }
      break;
    case BASS_ONLY:
      if (p_chord[2] == "") {
        chord = p_chord[0];
      } else {
        chord = p_chord[2];
      }
      break;
    default:
      chord = p_chord[0] + p_chord[1] + p_chord[2];
      break;
  }
  let chunk_text = "<span class='" + prefix + "chord-chunk'>" + chord + "</span>";
  if (chord == prev_chord) {
    // Don't display duplicate chords on the same line
    chunk_text = "<span class='" + prefix + "chord-chunk hidden-chord'>" + chord + "</span>";
  }
  return [chunk_text, chord];
}

function get_song_section_html(section, prefix, display_fill_toggle) {
  let section_and_fills = section.split(SECTION_AND_FILLS_REGEX).filter((x) => x != "");
  let s_text = "";
  let prev_chord = "";
  let cur_chord_tag = "";
  for (const section_part of section_and_fills) {
    if (section_part.includes("[¬]")) {
      // Process fill section (single line of chords)
      prev_chord = "";
      if (display_fill_toggle) {
        fill_chords = section_part.split(FILL_CHORD_REGEX).filter((x) => x != "" && x != "[¬]");
        for (const chord of fill_chords) {
          //prettier-ignore
          [cur_chord_tag, prev_chord] = get_chord_chunk_html(chord.slice(1, -1), "fill-", prev_chord);
          s_text += cur_chord_tag;
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
        prev_chord = "";
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
              seg = seg.replace(/\[[\s]?/, ""); // ? => * maybe
              seg = seg.replace(/[\s]?\]/, "");
              [cur_chord_tag, prev_chord] = get_chord_chunk_html(seg, prefix, prev_chord);
              if (prev_chunk_is_chord == true) {
                s_text += '</span><span class="' + prefix + 'lyric-chord-block">' + cur_chord_tag;
              } else {
                s_text += '<span class="' + prefix + 'lyric-chord-block">' + cur_chord_tag;
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

function update_verse_order() {
  let verse_list = "<ul>";
  if (slide_type == "song") {
    DOM_get("capoarea").style.display = "inline";
    let part_counts_sum = 0;
    for (const [idx, verse] of verse_order.split(" ").entries()) {
      if (slide_index >= part_counts_sum && slide_index < part_counts_sum + part_counts[idx]) {
        verse_list += "<li><span class='current-verse'>" + verse.toUpperCase() + "</span></li>";
      } else {
        verse_list += "<li>" + verse.toUpperCase() + "</li>";
      }
      part_counts_sum += part_counts[idx];
    }
    verse_list += "</ul>";
  } else if (slide_type != "none") {
    verse_list = "<ul><li>" + current_title + "</li></ul>";
    DOM_get("capoarea").style.display = "none";
  } else {
    DOM_get("capoarea").style.display = "none";
  }
  DOM_get("verseorder").innerHTML = verse_list;
}

function update_music() {
  DOM_get("playedkey").innerHTML = played_key;
  update_verse_order();

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
    current_text = "<div class ='nonsong-block'><p class='nonsong-line'>";
    current_text += current_slides[slide_index].replace(/\n/g, "</p><p class='nonsong-line'>");
    current_text += "</div>";
    if (slide_index < current_slides.length - 1) {
      next_text = "<div class ='next-nonsong-block'><p class='nonsong-line'>";
      next_text += current_slides[slide_index + 1].replace(/\n/g, "</p><p class='nonsong-line'>");
      next_text += "</div>";
    }
  } else if (slide_type == "video") {
    current_text = "<div class ='nonsong-block'><p class='nonsong-line'>";
    current_text += current_slides[0].replace(/\n/g, "</p><p class='nonsong-line'>");
    current_text += "</div>";
  }
  DOM_get("currentslide").innerHTML = current_text;
  DOM_get("nextslide").innerHTML = next_text;

  if (slide_type == "song") {
    process_chord_widths("currentslide", "");
    process_chord_widths("nextslide", "next-");
  }
}

function update_capo() {
  capo = parseInt(DOM_get("caposelect").value);
  if (capo != 0) {
    window.localStorage.setItem(cur_song_id.toString(), capo.toString());
  } else {
    window.localStorage.removeItem(cur_song_id.toString());
  }
  send_message("client.set-capo", { capo: capo });
}

function update_chord_style() {
  chord_pref = DOM_get("chordselect").value;
  window.localStorage.setItem("chord_pref", chord_pref);
  update_music();
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
      DOM_get("caposelect").value = capo;
      send_message("client.set-capo", { capo: capo });
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

function load_current_item(cur_item) {
  slide_type = cur_item.type;
  current_slides = cur_item.slides;
  current_title = cur_item["title"];
  cur_song_id = -1;
  verse_order = "";
  part_counts = [];
  played_key = "";
  if (slide_type == "song") {
    cur_song_id = cur_item["song-id"];
    if (cur_item["uses-chords"]) {
      played_key = cur_item["played-key"];
    }
    verse_order = cur_item["verse-order"];
    part_counts = cur_item["part-counts"];
  }
}

function update_service_overview_update(json_data) {
  slide_index = json_data.params.slide_index;
  if (JSON.stringify(json_data.params.current_item) != "{}") {
    load_current_item(json_data.params.current_item);
  } else {
    load_current_item({ type: "none", slides: [], title: "" });
  }
  capo_check_update_music();
}

function update_slide_index_update(json_data) {
  slide_index = json_data.params.slide_index;
  update_music();
}

function update_item_index_update(json_data) {
  slide_index = json_data.params.slide_index;
  load_current_item(json_data.params.current_item);
  capo_check_update_music();
}

function send_message(action, params) {
  params["lang"] = "en";
  websocket.send(JSON.stringify({ action: action, params: params }));
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
  if (chord_pref == null) {
    chord_pref = 0;
    window.localStorage.setItem("chord_pref", chord_pref);
  }
  DOM_get("chordselect").value = chord_pref;
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
