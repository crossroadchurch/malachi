let capo = 0;
let verse_order = "";
let played_key = "";
let slide_type = "";
let cur_song_id = -1;
let current_slides = [];
let current_title = "";
let part_counts = [];
let slide_index = -1;
let bass_pref = window.localStorage.getItem("bass_pref");
const BASS_CSS = ["guitar-root", "hybrid-root", "bass-root"];
let websocket;
// DOM pointers
const DOM_dict = {};
// prettier-ignore
const DOM_KEYS = ["playedkey", "capoarea", "verseorder", "currentslide", "nextslide", "caposelect", "bassselect"];
// prettier-ignore
const VALID_KEYS = ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B"];

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

function get_chord_chunk_html(chord, prefix) {
  p_chord = parse_chord(chord);
  if (p_chord[2] == "") {
    // Chord doesn't have a bass note
    // prettier-ignore
    chord = p_chord[0] + "<span class='" + BASS_CSS[bass_pref] + "'>" + p_chord[1] + "</span>";
  } else {
    // prettier-ignore
    chord = "<span class='" + BASS_CSS[bass_pref] + "'>" + p_chord[0] + p_chord[1] + "</span>" + p_chord[2];
  }
  let chunk_text = "<span class='" + prefix + "chord-chunk'>" + chord + "</span>";
  return chunk_text;
}

function get_song_section_html(section, prefix, display_fill_toggle) {
  let section_and_fills = section.split(/(\[\¬\].*\[\¬\])/).filter((x) => x != "");
  let slide_text = "";
  for (const section_part of section_and_fills) {
    if (section_part.includes("[¬]")) {
      // Process fill section (single line of chords)
      if (display_fill_toggle) {
        fill_chords = section_part
          .split(/(\[[\w\+\¬#\/"='' ]*\])/)
          .filter((x) => x != "" && x != "[¬]");
        for (const chord of fill_chords) {
          slide_text += get_chord_chunk_html(chord.slice(1, -1), "fill-");
        }
        slide_text += "<br />";
      }
      display_fill_toggle = !display_fill_toggle;
    } else {
      // Process regular lyrics and chords
      let slide_lines = section_part.split(/(\n)/);
      let prev_chunk_is_chord = false;
      let hanging_lyric_pos = -1;
      for (const line of slide_lines) {
        if (line == "\n") {
          slide_text += "<br />";
        } else {
          let line_segments = line.split(/(\[[\w\+#\/"='' ]*\])/);
          if (line_segments[0] != "") {
            // Process head of line
            slide_text +=
              '<span class="' +
              prefix +
              'lyric-chord-block"><span class="' +
              prefix +
              'lyric-chunk">' +
              line_segments[0] +
              "</span></span>";
          }
          // Process tail of line: <Tail> ::= (<Chord>|(<Chord><Lyric>))*
          prev_chunk_is_chord = false;
          hanging_lyric_pos = -1;
          for (let segment = 1; segment < line_segments.length; segment++) {
            let seg = line_segments[segment];
            if (seg.charAt(0) == "[") {
              // Current is chord
              seg = seg.replace(/\[[\s]?/, ""); // ? => * maybe
              seg = seg.replace(/[\s]?\]/, "");
              seg = get_chord_chunk_html(seg, prefix);
              if (prev_chunk_is_chord == true) {
                slide_text += '</span><span class="' + prefix + 'lyric-chord-block">' + seg;
              } else {
                slide_text += '<span class="' + prefix + 'lyric-chord-block">' + seg;
              }
              prev_chunk_is_chord = true;
            } else {
              // Current is lyric
              if (hanging_lyric_pos > 0 && seg.charAt(0).match(/[a-z]/i)) {
                slide_text =
                  slide_text.slice(0, hanging_lyric_pos + 1) +
                  " midword" +
                  slide_text.slice(hanging_lyric_pos + 1);
              }
              // recalc hanging_lyric_pos based on current_text length + offset
              hanging_lyric_pos = slide_text.length + 23 + prefix.length;
              slide_text += '<span class="' + prefix + 'lyric-chunk">' + seg + "</span></span>";
              prev_chunk_is_chord = false;
              if (!seg.slice(-1).match(/[a-z]/i)) {
                hanging_lyric_pos = -1;
              }
            }
          }
          if (prev_chunk_is_chord == true) {
            slide_text += "</span>";
          }
        }
      }
      slide_text += "<br />";
    }
  }
  return { text: slide_text, toggle: display_fill_toggle };
}

function process_chord_widths(slide_id, prefix) {
  document.querySelectorAll("#" + slide_id + ">span").forEach((element) => {
    if (element.children.length > 1) {
      const lyricWidth = parseInt(
        getComputedStyle(element.querySelector("." + prefix + "lyric-chunk")).width
      );
      const chordWidth = parseInt(
        getComputedStyle(element.querySelector("." + prefix + "chord-chunk")).width
      );
      if (lyricWidth == 0) {
        element.querySelector("." + prefix + "lyric-chunk").innerHTML = "&nbsp;";
      }
      if (lyricWidth <= chordWidth) {
        if (element.querySelectorAll(".midword").length > 0) {
          const spacerWidth = chordWidth - parseInt(getComputedStyle(element).width);
          element.insertAdjacentHTML(
            "beforeend",
            '<span class="' + prefix + 'midword-spacer">-</span>'
          );
          if (spacerWidth < body_size_int) {
            element.querySelector("." + prefix + "midword-spacer").style.width =
              body_size_int + "px";
          } else {
            element.querySelector("." + prefix + "midword-spacer").style.width = spacerWidth + "px";
          }
        } else {
          element.style.paddingRight =
            chordWidth - parseInt(getComputedStyle(element).width) + body_size_int + "px";
        }
      }
    }
  });
}

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
  if (slide_type == "song") {
    current_result = get_song_section_html(current_slides[slide_index], "", true);
    DOM_dict["currentslide"].innerHTML = current_result.text;
    if (slide_index < current_slides.length - 1) {
      next_result = get_song_section_html(
        current_slides[slide_index + 1],
        "next-",
        current_result.toggle
      );
      DOM_dict["nextslide"].innerHTML = next_result.text;
    } else {
      DOM_dict["nextslide"].innerHTML = "";
    }
    process_chord_widths("currentslide", "");
    process_chord_widths("nextslide", "next-");
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

function update_bass() {
  bass_pref = parseInt(DOM_dict["bassselect"].value);
  window.localStorage.setItem("bass_pref", bass_pref);
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

function load_current_item(cur_item) {
  slide_type = cur_item.type;
  current_slides = cur_item.slides;
  current_title = cur_item["title"];
  if (slide_type == "song") {
    cur_song_id = cur_item["song-id"];
    if (cur_item["uses-chords"]) {
      played_key = cur_item["played-key"];
    } else {
      played_key = "";
    }
    verse_order = cur_item["verse-order"];
    part_counts = cur_item["part-counts"];
  } else {
    cur_song_id = -1;
    verse_order = "";
    part_counts = [];
    played_key = "";
  }
}

function update_service_overview_update(json_data) {
  slide_index = json_data.params.slide_index;
  if (JSON.stringify(json_data.params.current_item) != "{}") {
    load_current_item(json_data.params.current_item);
  } else {
    slide_type = "none";
    cur_song_id = -1;
    current_slides = [];
    verse_order = "";
    part_counts = [];
    played_key = "";
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
  if (bass_pref == null) {
    bass_pref = 0;
    window.localStorage.setItem("bass_pref", bass_pref);
  }
  DOM_dict["bassselect"].value = parseInt(bass_pref);
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
