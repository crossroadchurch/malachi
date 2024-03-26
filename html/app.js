let websocket;
const MAX_LIST_ITEMS = 50;
const MAX_VERSE_ITEMS = 2500;
const SELECTED_COLOR = "gold";
let saved_current_item = null;
let service_sort_start;
let editing_song_id;
let action_after_save;
let screen_state;
let icon_dict = {};
let drag_dict = {};
let style_dict = {};
let aspect_ratio;
let video_timer = 0;
let video_interval;
let valid_keys = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
let drag_data = { start_idx: -1, dy: -1, max_idx: -1 };
let saved_style = null;
const LINE_SEGMENT_REGEX = /\[[\w\+\¬#\/"='' ]*\]/;

// DOM pointers
const DOM_dict = {};
// prettier-ignore
const DOM_KEYS = [
  "flip_screen_state", "audio_controls", "video_controls", "presentation_controls",
  "current_item_list", "current_item_icon", "current_item_name", "current_item",
  "screen_view", "item_area", "item_header", "song_search", "bible_search",
  "cd_time", "time_seek", "ghost_text", "drag_ghost",
  "song_list", "passage_list", "service_list", "presentation_list",
  "video_list", "loop_list", "background_list", "b_version_radios",
  "b_main_version_radios", "b_alt_version_radios", "bible_controls",
  "e_title", "e_author", "e_book", "e_number", "e_audio", "e_copyright", "e_lyrics", "e_fills",
  "e_order", "e_transpose", "e_transpose_out", "e_title_span", "line_numbers",
  "s_width", "s_width_out", "s_font_size", "s_font_size_out", "s_lines", "s_lines_out",
  "pl_width", "pl_width_out", "pl_font_size", "pl_font_size_out", "pl_lines", "pl_lines_out",
  "s_margin", "s_margin_out", "ch_size", "ch_size_out", "cd_size", "cd_size_out",
  "cd_top", "cd_top_out", "cd_text", "d_copyright", "cp_size", "cp_size_out",
  "cp_width", "cp_width_out", "d_verseorder", "vo_size", "vo_size_out",
  "vo_width", "vo_width_out", "at_scale", "at_scale_out", "song_bg_icon", "bible_bg_icon",
  "tc_red", "tc_red_out", "tc_green", "tc_green_out", "tc_blue", "tc_blue_out", "tc_preview",
  "popup_new_service", "popup_load_service", "popup_save_before_load_service",
  "popup_save_service_as", "popup_export_service_as", "f_name", "exp_name",
  "popup_edit_mode", "popup_edit_song", "load_files_radio",
  "popup_attach_audio", "attach_audio_radio", "d_version_radios"
];

style_dict["s_width"] = "div-width-vw";
style_dict["s_font_size"] = "font-size-vh";
style_dict["s_lines"] = "max-lines";
style_dict["s_margin"] = "margin-top-vh";
style_dict["font_color"] = "font-color";
style_dict["ch_size"] = "countdown-h-size-vh";
style_dict["cd_size"] = "countdown-size-vh";
style_dict["cd_top"] = "countdown-top-vh";
style_dict["cp_size"] = "copy-size-vh";
style_dict["cp_width"] = "copy-width-vw";
style_dict["vo_size"] = "order-size-vh";
style_dict["vo_width"] = "order-width-vw";
style_dict["pl_width"] = "pl-width-vw";
style_dict["pl_font_size"] = "pl-font-size-vh";
style_dict["pl_lines"] = "pl-max-lines";
style_dict["d_version"] = "default-version";
style_dict["at_scale"] = "app-text-scale";

icon_dict["bible"] = "/html/icons/icons8-literature-48.png";
icon_dict["song"] = "/html/icons/icons8-musical-notes-48.png";
icon_dict["presentation"] = "/html/icons/icons8-presentation-48.png";
icon_dict["video"] = "/html/icons/icons8-tv-show-48.png";

drag_dict["icons8-literature-48.png"] = "drag_bible_icon";
drag_dict["icons8-musical-notes-48.png"] = "drag_song_icon";
drag_dict["icons8-presentation-48.png"] = "drag_presentation_icon";
drag_dict["icons8-tv-show-48.png"] = "drag_video_icon";

function change_screen_state_flip() {
  const str_state = DOM_dict["flip_screen_state"].checked ? "on" : "off";
  websocket.send(
    JSON.stringify({
      action: "command.set-display-state",
      params: { state: str_state },
    })
  );
}

function add_verses() {
  let verses = document.querySelectorAll("#passage_list .ml_row.selected .ml_text");
  const version = document.querySelector("input[name=b_version]:checked").getAttribute("data-bv");
  if (verses.length > 0) {
    let range_start = verses[0].id.substring(2);
    let prev_id = range_start - 1;
    let v_id;
    for (v = 0; v < verses.length; v++) {
      v_id = verses[v].id.substring(2);
      if (v_id - prev_id == 1) {
        // Range continues from previous verse
        prev_id = v_id;
      } else {
        // Entering new range, so close old one and add that to the service
        websocket.send(
          JSON.stringify({
            action: "command.add-bible-item",
            params: {
              version: version,
              "start-verse": range_start,
              "end-verse": prev_id,
            },
          })
        );
        range_start = v_id;
        prev_id = v_id;
      }
    }
    // Add final range to the service
    websocket.send(
      JSON.stringify({
        action: "command.add-bible-item",
        params: {
          version: version,
          "start-verse": range_start,
          "end-verse": v_id,
        },
      })
    );
  }
}

function select_all_verses() {
  document.querySelectorAll("#passage_list .ml_row").forEach((elt) => {
    if (!elt.classList.contains("selected")) {
      elt.classList.add("selected");
    }
  });
}

function select_none_verses() {
  document.querySelectorAll("#passage_list .ml_row").forEach((elt) => {
    if (elt.classList.contains("selected")) {
      elt.classList.remove("selected");
    }
  });
}

function load_service_preload() {
  websocket.send(JSON.stringify({ action: "request.all-services", params: {} }));
}

function load_service(force) {
  DOM_dict["popup_save_before_load_service"].style.display = "none";
  DOM_dict["popup_load_service"].style.display = "none";
  const sel_text = document.querySelector("#load_files_radio .selected .ml_text").innerText;
  websocket.send(
    JSON.stringify({
      action: "command.load-service",
      params: { filename: sel_text, force: force },
    })
  );
}

function open_save_service_popup() {
  DOM_dict["popup_save_service_as"].style.display = "flex";
}

function open_export_service_popup() {
  DOM_dict["popup_export_service_as"].style.display = "flex";
}

function save_service_as() {
  const f_name = DOM_dict["f_name"].value;
  DOM_dict["popup_save_service_as"].style.display = "none";
  // Replace invalid characters to avoid errors and prevent file being saved in other directories
  let clean_name = f_name.replace(/[\\\/\"\':;*<>|]/g, "");
  if (clean_name.endsWith(".json") == false) {
    clean_name += ".json";
  }
  websocket.send(
    JSON.stringify({
      action: "command.save-service-as",
      params: { filename: clean_name },
    })
  );
  // Reset input for next time
  DOM_dict["f_name"].value = "";
}

function export_service_as() {
  const f_name = DOM_dict["exp_name"].value;
  DOM_dict["popup_export_service_as"].style.display = "none";
  // Replace invalid characters to avoid errors and prevent file being saved in other directories
  let clean_name = f_name.replace(/[\\\/\"\':;*<>|]/g, "");
  if (clean_name.endsWith(".zip") == false) {
    clean_name += ".zip";
  }
  websocket.send(
    JSON.stringify({
      action: "command.export-service",
      params: { filename: clean_name },
    })
  );
  // Reset input for next time
  DOM_dict["exp_name"].value = "";
}

function save_service(action_after) {
  DOM_dict["popup_new_service"].style.display = "none";
  DOM_dict["popup_save_before_load_service"].style.display = "none";
  action_after_save = action_after;
  websocket.send(JSON.stringify({ action: "command.save-service", params: {} }));
}

function delete_item(idx) {
  websocket.send(
    JSON.stringify({
      action: "command.remove-item",
      params: { index: idx },
    })
  );
}

function next_item() {
  websocket.send(JSON.stringify({ action: "command.next-item", params: {} }));
}

function previous_item() {
  websocket.send(JSON.stringify({ action: "command.previous-item", params: {} }));
}

function goto_item(idx) {
  websocket.send(
    JSON.stringify({
      action: "command.goto-item",
      params: { index: idx },
    })
  );
}

function next_slide() {
  websocket.send(JSON.stringify({ action: "command.next-slide", params: {} }));
}

function previous_slide() {
  websocket.send(JSON.stringify({ action: "command.previous-slide", params: {} }));
}

function goto_slide(idx) {
  websocket.send(JSON.stringify({ action: "command.goto-slide", params: { index: idx } }));
}

function song_search() {
  const song_val = document
    .getElementById("song_search")
    .value.replace(/[^0-9a-z ]/gi, "")
    .trim();
  const remote_val = parseInt(
    document.querySelector("input[name=lr_search]:checked").getAttribute("data-lrs")
  );
  if (song_val !== "") {
    websocket.send(
      JSON.stringify({
        action: "query.song-by-text",
        params: {
          "search-text": song_val,
          remote: remote_val,
        },
      })
    );
  } else {
    DOM_dict["song_list"].innerHTML = "";
  }
}

function bible_search() {
  const search_text = DOM_dict["bible_search"].value.trim();
  const search_version = document
    .querySelector("input[name=b_version]:checked")
    .getAttribute("data-bv");
  if (document.querySelector("input[name=b_search_type]:checked").id == "b_search_type_ref") {
    if (search_text !== "") {
      websocket.send(
        JSON.stringify({
          action: "query.bible-by-ref",
          params: {
            version: search_version,
            "search-ref": search_text,
          },
        })
      );
    } else {
      DOM_dict["passage_list"].innerHTML = "";
    }
  } else {
    if (search_text.length > 2) {
      websocket.send(
        JSON.stringify({
          action: "query.bible-by-text",
          params: {
            version: search_version,
            "search-text": search_text,
          },
        })
      );
    } else {
      toast_error("Please enter at least three characters to search by text");
    }
  }
}

function new_service(force) {
  DOM_dict["popup_new_service"].style.display = "none";
  websocket.send(JSON.stringify({ action: "command.new-service", params: { force: force } }));
}

function add_song(s_id) {
  websocket.send(
    JSON.stringify({
      action: "command.add-song-item",
      params: { "song-id": s_id },
    })
  );
}

function edit_song(s_id) {
  websocket.send(
    JSON.stringify({
      action: "request.full-song",
      params: { "song-id": s_id },
    })
  );
}

function refresh_presentations() {
  websocket.send(JSON.stringify({ action: "request.all-presentations", params: {} }));
}

function refresh_videos() {
  websocket.send(JSON.stringify({ action: "request.all-videos", params: {} }));
}

function refresh_loops() {
  websocket.send(JSON.stringify({ action: "request.all-loops", params: {} }));
}

function refresh_backgrounds() {
  websocket.send(JSON.stringify({ action: "request.all-backgrounds", params: {} }));
}

function video_tick() {
  video_timer += 1;
  DOM_dict["time_seek"].value = video_timer;
}

function play_video() {
  websocket.send(JSON.stringify({ action: "command.play-video", params: {} }));
}

function pause_video() {
  websocket.send(JSON.stringify({ action: "command.pause-video", params: {} }));
}

function stop_video() {
  websocket.send(JSON.stringify({ action: "command.stop-video", params: {} }));
}

function play_audio() {
  websocket.send(JSON.stringify({ action: "command.play-audio", params: {} }));
}

function pause_audio() {
  websocket.send(JSON.stringify({ action: "command.pause-audio", params: {} }));
}

function stop_audio() {
  websocket.send(JSON.stringify({ action: "command.stop-audio", params: {} }));
}

function start_countdown() {
  const now = new Date();
  const target_time = DOM_dict["cd_time"].value;
  const target = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate(),
    target_time.split(":")[0],
    target_time.split(":")[1],
    0
  );
  const cd_length = Math.floor((target.getTime() - now.getTime()) / 1000);
  if (cd_length > 0) {
    websocket.send(
      JSON.stringify({
        action: "command.start-countdown",
        params: {
          hr: target_time.split(":")[0],
          min: target_time.split(":")[1],
        },
      })
    );
  } else {
    toast_error("Invalid countdown\nThat time is in the past!");
  }
}

function clear_countdown() {
  websocket.send(JSON.stringify({ action: "command.clear-countdown", params: {} }));
}

function start_presentation() {
  websocket.send(JSON.stringify({ action: "command.start-presentation", params: {} }));
}

function restore_loop() {
  websocket.send(JSON.stringify({ action: "command.restore-loop", params: {} }));
}

function create_song() {
  // Empty all fields on popup
  DOM_dict["e_title"].value = "";
  DOM_dict["e_author"].value = "";
  DOM_dict["e_book"].value = "";
  DOM_dict["e_number"].value = "";
  DOM_dict["e_audio"].value = "";
  DOM_dict["e_copyright"].value = "";
  DOM_dict["e_lyrics"].value = "<V1>\n";
  DOM_dict["e_fills"].value = "";
  DOM_dict["e_order"].value = "";
  document.querySelectorAll("input[name='e_key']").forEach((elt) => {
    elt.checked = false;
  });
  document.querySelector("input[data-ek='C']").checked = true;
  document.querySelector("input[data-lr='0']").checked = true;
  document.querySelector("input[data-lr='1']").checked = false;
  DOM_dict["e_transpose"].value = 0;
  DOM_dict["e_transpose_out"].value = "C";
  // Switch into create song mode
  DOM_dict["popup_edit_mode"].innerHTML = "Create song";
  // Display popup
  DOM_dict["popup_edit_song"].style.display = "flex";
}

function reset_edit_song_form() {
  DOM_dict["e_title_span"].style.color = "black";
  DOM_dict["e_title_span"].style.fontWeight = "normal";
}

function save_song() {
  // Validation: title can't be empty, other validation carried out by server
  if (DOM_dict["e_title"].value.trim() == "") {
    DOM_dict["e_title_span"].style.color = "red";
    DOM_dict["e_title_span"].style.fontWeight = "bold";
  } else {
    reset_edit_song_form();
    let lyric_text = DOM_dict["e_lyrics"].value;
    let lyric_lines = lyric_text.split("\n");
    let current_part = "";
    let current_lines = [];
    let parts = []; // parts = [ {part: "v1", lines: [line1, ..., line_n]}, ...]
    for (const line of lyric_lines) {
      if (line[0] == "<") {
        // New part, do we need to close out previous one?
        if (current_lines.length != 0) {
          part_obj = { part: current_part, lines: current_lines };
          parts.push(part_obj);
        }
        // Start new part
        if (line[line.length - 1] == ">") {
          current_part = line.substr(1, line.length - 2).toLowerCase();
        } else {
          // Tag has not been ended
          current_part = line.substr(1, line.length - 1).toLowerCase();
        }
        current_lines = [];
      } else if (line[0] == "[") {
        // Only [br] lines should start with [, this ensures no mismatched brackets occur
        current_lines.push("[br]");
      } else {
        if (line != "") {
          // Skip completely blank lines
          current_lines.push(line.replace(/\s+$/, "")); // Trim trailing whitespace only
        }
      }
    }
    // Add final part to parts
    if (current_lines.length != 0) {
      part_obj = { part: current_part, lines: current_lines };
      parts.push(part_obj);
    }
    // fills = [fill_1, fill_2, ...] can be empty array
    let fill_array = DOM_dict["e_fills"].value.trim().split("\n");
    if (fill_array.length == 1 && fill_array[0] == "") {
      fill_array = [];
    }

    let fields = {
      author: DOM_dict["e_author"].value,
      transpose_by: DOM_dict["e_transpose"].value % 12,
      lyrics_chords: parts,
      fills: fill_array,
      verse_order: DOM_dict["e_order"].value.toLowerCase(),
      song_book_name: DOM_dict["e_book"].value,
      song_number: DOM_dict["e_number"].value,
      audio: DOM_dict["e_audio"].value,
      copyright: DOM_dict["e_copyright"].value,
    };
    // Deal with optional field
    if (document.querySelectorAll("input[name=e_key]:checked").length > 0) {
      fields["song_key"] = document
        .querySelector("input[name=e_key]:checked")
        .getAttribute("data-ek");
    }

    fields["remote"] = parseInt(
      document.querySelector("input[name=e_remote]:checked").getAttribute("data-lr")
    );

    if (DOM_dict["popup_edit_mode"].innerText == "Edit song") {
      fields["title"] = DOM_dict["e_title"].value;
      websocket.send(
        JSON.stringify({
          action: "command.edit-song",
          params: {
            "song-id": editing_song_id,
            fields: fields,
          },
        })
      );
    } else {
      websocket.send(
        JSON.stringify({
          action: "command.create-song",
          params: {
            title: DOM_dict["e_title"].value,
            fields: fields,
          },
        })
      );
    }
    DOM_dict["popup_edit_song"].style.display = "none";
  }
}

function add_video(vid_url) {
  websocket.send(
    JSON.stringify({
      action: "command.add-video",
      params: { url: vid_url },
    })
  );
}

function add_presentation(pres_url) {
  websocket.send(
    JSON.stringify({
      action: "command.add-presentation",
      params: {
        url: pres_url,
      },
    })
  );
}

function set_loop(loop_url) {
  websocket.send(
    JSON.stringify({
      action: "command.set-loop",
      params: { url: loop_url },
    })
  );
}

function clear_loop() {
  websocket.send(JSON.stringify({ action: "command.clear-loop", params: {} }));
}

function toggle_display_state() {
  if (screen_state === "on") {
    websocket.send(
      JSON.stringify({
        action: "command.set-display-state",
        params: { state: "off" },
      })
    );
  } else {
    websocket.send(
      JSON.stringify({
        action: "command.set-display-state",
        params: { state: "on" },
      })
    );
  }
}

function display_current_item(current_item, slide_index) {
  saved_current_item = current_item;
  DOM_dict["current_item_icon"].setAttribute("src", icon_dict[current_item.type]);
  DOM_dict["current_item_name"].innerHTML = current_item.title;

  // Reset video seek track
  clearInterval(video_interval);
  video_timer = 0;
  DOM_dict["time_seek"].value = video_timer;
  let max_verse_order = [];

  if (current_item.type == "song") {
    const min_verse_order = current_item["verse-order"].split(" ");
    const part_counts = current_item["part-counts"];
    for (i = 0; i < min_verse_order.length; i++) {
      for (j = 0; j < part_counts[i]; j++) {
        max_verse_order.push(min_verse_order[i].toUpperCase());
      }
    }
  }

  if (current_item.type == "song" && current_item["audio"] != "") {
    DOM_dict["audio_controls"].style.display = "block";
  } else {
    DOM_dict["audio_controls"].style.display = "none";
  }

  if (current_item.type == "video") {
    DOM_dict["video_controls"].style.display = "block";
    DOM_dict["time_seek"].max = current_item.duration;
  } else {
    DOM_dict["video_controls"].style.display = "none";
  }

  if (current_item.type == "presentation") {
    DOM_dict["presentation_controls"].style.display = "block";
  } else {
    DOM_dict["presentation_controls"].style.display = "none";
  }

  if (current_item.type == "bible") {
    DOM_dict["bible_controls"].style.display = "block";
    // Indicate current version and, if applicable, parallel version
    indicate_bible_versions(current_item.version, current_item.parallel_version);
  } else {
    DOM_dict["bible_controls"].style.display = "none";
  }

  let item_list = "";
  let slide_text = "";
  for (const [idx, slide] of current_item.slides.entries()) {
    if (current_item.type == "song") {
      let slide_lines = slide.split(/\n/);
      slide_text =
        "<p class='ml_songlyric'><span class='ml_songpart'>" + max_verse_order[idx] + "</span>";
      for (const line of slide_lines) {
        for (const segment of line.split(LINE_SEGMENT_REGEX)) {
          slide_text += segment;
        }
        slide_text += "<br />";
      }
      slide_text += "</p>";
    } else {
      slide_text = "<p>" + slide + "</p>";
    }
    item_list += "<div class='ml_row ml_expand_row'>";
    item_list += "<div class='ml_text ml_multitext' onclick='goto_slide(" + idx + ")'>";
    item_list += slide_text + "</div>";
    item_list += "</div>";
  }
  DOM_dict["current_item_list"].innerHTML = item_list;

  // Stop audio playback if necessary
  stop_audio();

  // Indicate selection of slide_index
  indicate_current_slide(slide_index);
}

function indicate_bible_versions(version, pl_version) {
  document.querySelectorAll("#b_main_version_radios input").forEach((elt) => {
    elt.checked = false;
  });
  document
    .querySelectorAll("#b_main_version_radios input[data-bv='" + version + "']")
    .forEach((elt) => {
      elt.checked = true;
    });
  document.querySelectorAll("#b_alt_version_radios input").forEach((elt) => {
    elt.checked = false;
  });
  if (pl_version != "") {
    document
      .querySelectorAll("#b_alt_version_radios input[data-bv='" + pl_version + "']")
      .forEach((elt) => {
        elt.checked = true;
      });
  }
}

function indicate_current_slide(slide_index) {
  document.querySelectorAll("#current_item_list div.ml_text").forEach((elt) => {
    elt.classList.remove("selected");
  });
  if (slide_index != -1) {
    document
      .querySelector(
        "#current_item_list div.ml_row:nth-child(" + (slide_index + 1) + ") div.ml_text"
      )
      .classList.add("selected");
    const item_top =
      document
        .querySelector("#current_item_list div.ml_row:nth-child(" + (slide_index + 1) + ")")
        .getBoundingClientRect().top + document.body.scrollTop;
    const item_height = document.querySelector(
      "#current_item_list div.ml_row:nth-child(" + (slide_index + 1) + ")"
    ).offsetHeight;
    const viewable_top =
      DOM_dict["current_item"].getBoundingClientRect().top + document.body.scrollTop;
    const list_top =
      DOM_dict["current_item_list"].getBoundingClientRect().top + document.body.scrollTop;
    const scroll_top = DOM_dict["current_item"].scrollTop;
    const window_height = window.innerHeight;
    if (item_top < viewable_top) {
      DOM_dict["current_item"].scrollTop = item_top - list_top;
    } else if (item_top + item_height > 0.9 * window_height) {
      DOM_dict["current_item"].scrollTop =
        8 + scroll_top + item_top + item_height - 0.9 * window_height;
    }
  }
}

function indicate_current_item(item_index) {
  document.querySelectorAll("#service_list div.ml_row div.ml_text").forEach((elt) => {
    elt.style.backgroundColor = "";
  });
  if (item_index != -1) {
    document.querySelector(
      "#service_list div.ml_row:nth-child(" + (item_index + 1) + ") div.ml_text"
    ).style.backgroundColor = SELECTED_COLOR;
  }
}

function update_text_scale(style) {
  DOM_dict["current_item_list"].style.fontSize = style[style_dict["at_scale"]] + "em";
  DOM_dict["passage_list"].style.fontSize = style[style_dict["at_scale"]] + "em";
}

function update_style_sliders(style) {
  saved_style = style;
  DOM_dict["s_width"].value = style[style_dict["s_width"]];
  DOM_dict["s_width_out"].value = style[style_dict["s_width"]];
  DOM_dict["s_font_size"].value = style[style_dict["s_font_size"]];
  DOM_dict["s_font_size_out"].value = style[style_dict["s_font_size"]];
  DOM_dict["s_lines"].value = style[style_dict["s_lines"]];
  DOM_dict["s_lines_out"].value = style[style_dict["s_lines"]];
  DOM_dict["s_margin"].value = style[style_dict["s_margin"]];
  DOM_dict["s_margin_out"].value = style[style_dict["s_margin"]];
  DOM_dict["tc_red"].value = parseInt(style[style_dict["font_color"]].slice(0, 2), 16);
  DOM_dict["tc_red_out"].value = parseInt(style[style_dict["font_color"]].slice(0, 2), 16);
  DOM_dict["tc_green"].value = parseInt(style[style_dict["font_color"]].slice(2, 4), 16);
  DOM_dict["tc_green_out"].value = parseInt(style[style_dict["font_color"]].slice(2, 4), 16);
  DOM_dict["tc_blue"].value = parseInt(style[style_dict["font_color"]].slice(4, 6), 16);
  DOM_dict["tc_blue_out"].value = parseInt(style[style_dict["font_color"]].slice(4, 6), 16);
  update_color_preview();
  document.querySelectorAll("input[name='d_version']").forEach((elt) => {
    elt.checked = false;
  });
  document
    .querySelectorAll("input[data-dv='" + style[style_dict["d_version"]] + "']")
    .forEach((elt) => {
      elt.checked = true;
    });
  DOM_dict["pl_width"].value = style[style_dict["pl_width"]];
  DOM_dict["pl_width_out"].value = style[style_dict["pl_width"]];
  DOM_dict["pl_font_size"].value = style[style_dict["pl_font_size"]];
  DOM_dict["pl_font_size_out"].value = style[style_dict["pl_font_size"]];
  DOM_dict["pl_lines"].value = style[style_dict["pl_lines"]];
  DOM_dict["pl_lines_out"].value = style[style_dict["pl_lines"]];
  document.querySelectorAll("input[name='o_style']").forEach((elt) => {
    elt.checked = false;
  });
  document.querySelector("input[data-ol='" + style["outline-style"] + "']").checked = true;
  DOM_dict["ch_size"].value = style[style_dict["ch_size"]];
  DOM_dict["ch_size_out"].value = style[style_dict["ch_size"]];
  DOM_dict["cd_size"].value = style[style_dict["cd_size"]];
  DOM_dict["cd_size_out"].value = style[style_dict["cd_size"]];
  DOM_dict["cd_top"].value = style[style_dict["cd_top"]];
  DOM_dict["cd_top_out"].value = style[style_dict["cd_top"]];
  DOM_dict["cd_text"].value = style["countdown-h-text"];
  DOM_dict["d_copyright"].checked = style["display-copyright"];
  DOM_dict["cp_size"].value = style[style_dict["cp_size"]];
  DOM_dict["cp_size_out"].value = style[style_dict["cp_size"]];
  DOM_dict["cp_width"].value = style[style_dict["cp_width"]];
  DOM_dict["cp_width_out"].value = style[style_dict["cp_width"]];
  DOM_dict["d_verseorder"].checked = style["display-verseorder"];
  DOM_dict["vo_size"].value = style[style_dict["vo_size"]];
  DOM_dict["vo_size_out"].value = style[style_dict["vo_size"]];
  DOM_dict["vo_width"].value = style[style_dict["vo_width"]];
  DOM_dict["vo_width_out"].value = style[style_dict["vo_width"]];
  DOM_dict["at_scale"].value = style[style_dict["at_scale"]];
  DOM_dict["at_scale_out"].value = style[style_dict["at_scale"]];
  // Update background status items
  if (style["song-background-url"] == "none") {
    DOM_dict["song_bg_icon"].setAttribute("src", "");
  } else {
    DOM_dict["song_bg_icon"].setAttribute(
      "src",
      "./backgrounds/thumbnails/" + style["song-background-url"].substr(14)
    );
  }
  if (style["bible-background-url"] == "none") {
    DOM_dict["bible_bg_icon"].setAttribute("src", "");
  } else {
    DOM_dict["bible_bg_icon"].setAttribute(
      "src",
      "./backgrounds/thumbnails/" + style["bible-background-url"].substr(14)
    );
  }
}

function json_toast_response(json_data, success_message, error_message) {
  if (json_data.params.status === "ok") {
    Toastify({
      text: success_message,
      gravity: "bottom",
      position: "left",
      style: { background: "#4caf50" },
    }).showToast();
  } else {
    Toastify({
      text: error_message + " (" + json_data.params.status + ")\n" + json_data.params.details,
      gravity: "bottom",
      position: "left",
      duration: -1,
      close: true,
      style: { background: "#f44337" },
    }).showToast();
  }
}

function toast_error(error_details) {
  Toastify({
    text: error_details,
    gravity: "bottom",
    position: "left",
    duration: -1,
    close: true,
    style: { background: "#f44337" },
  }).showToast();
}

function update_transpose_slider() {
  if (document.querySelectorAll("input[name=e_key]:checked").length > 0) {
    const e_val = document.querySelector("input[name=e_key]:checked").getAttribute("data-ek");
    const e_idx = valid_keys.findIndex((element) => element == e_val);
    const t_idx = parseInt(DOM_dict["e_transpose"].value, 10);
    const t_key = valid_keys[(e_idx + t_idx) % 12];
    DOM_dict["e_transpose_out"].value = t_key;
  }
}

function set_background_songs(bg_url, bg_w, bg_h) {
  websocket.send(
    JSON.stringify({
      action: "command.edit-style-params",
      params: {
        style_params: [
          { param: "song-background-url", value: bg_url },
          { param: "song-background-w", value: bg_w },
          { param: "song-background-h", value: bg_h },
        ],
      },
    })
  );
}

function set_background_bible(bg_url, bg_w, bg_h) {
  websocket.send(
    JSON.stringify({
      action: "command.edit-style-params",
      params: {
        style_params: [
          { param: "bible-background-url", value: bg_url },
          { param: "bible-background-w", value: bg_w },
          { param: "bible-background-h", value: bg_h },
        ],
      },
    })
  );
}

function remove_song_background() {
  websocket.send(
    JSON.stringify({
      action: "command.edit-style-params",
      params: {
        style_params: [
          { param: "song-background-url", value: "none" },
          { param: "song-background-w", value: 1 },
          { param: "song-background-h", value: 1 },
        ],
      },
    })
  );
}

function remove_bible_background() {
  websocket.send(
    JSON.stringify({
      action: "command.edit-style-params",
      params: {
        style_params: [
          { param: "bible-background-url", value: "none" },
          { param: "bible-background-w", value: 1 },
          { param: "bible-background-h", value: 1 },
        ],
      },
    })
  );
}

function style_slider_input(elt) {
  document.getElementById(elt.id + "_out").value = elt.value;
}

function style_slider_change(elt) {
  websocket.send(
    JSON.stringify({
      action: "command.edit-style-param",
      params: {
        param: style_dict[elt.id],
        value: elt.value,
      },
    })
  );
}

function update_color_preview() {
  p_color =
    "#" +
    parseInt(DOM_dict["tc_red"].value).toString(16).padStart(2, "0") +
    parseInt(DOM_dict["tc_green"].value).toString(16).padStart(2, "0") +
    parseInt(DOM_dict["tc_blue"].value).toString(16).padStart(2, "0");
  DOM_dict["tc_preview"].style.backgroundColor = p_color;
}

function color_slider_change(elt) {
  update_color_preview();
}

function save_color_sliders() {
  s_color =
    parseInt(DOM_dict["tc_red"].value).toString(16).padStart(2, "0") +
    parseInt(DOM_dict["tc_green"].value).toString(16).padStart(2, "0") +
    parseInt(DOM_dict["tc_blue"].value).toString(16).padStart(2, "0");
  websocket.send(
    JSON.stringify({
      action: "command.edit-style-param",
      params: {
        param: style_dict["font_color"],
        value: s_color,
      },
    })
  );
}

function close_popup(elt_id) {
  document.getElementById(elt_id).style.display = "none";
}

function close_save_as_popup() {
  DOM_dict["f_name"].value = "";
  DOM_dict["popup_save_service_as"].style.display = "none";
}

function close_export_as_popup() {
  DOM_dict["exp_name"].value = "";
  DOM_dict["popup_export_service_as"].style.display = "none";
}

function load_element(short_elt) {
  document.querySelectorAll(".element_button").forEach((elt) => {
    elt.classList.remove("active_element");
  });
  document.querySelectorAll(".element_panel").forEach((elt) => {
    elt.style.display = "none";
  });
  document.getElementById(short_elt + "_element").style.display = "block";
  document.getElementById(short_elt + "_elt_button").classList.add("active_element");
}

function expand_section(short_elt) {
  document.querySelectorAll(".style_header").forEach((elt) => {
    elt.classList.remove("style_header_expanded");
  });
  document.querySelectorAll(".style_group").forEach((elt) => {
    elt.classList.remove("style_group_expanded");
  });
  document.getElementById("sh_" + short_elt).classList.add("style_header_expanded");
  document.getElementById("sg_" + short_elt).classList.add("style_group_expanded");
}

function drag_start(event) {
  const drag_target = event.target;
  if (event.target.tagName == "IMG") {
    const idx = event.target.getAttribute("data-idx");
    drag_target = document.querySelector("#service_list .ml_row[data-idx='" + idx + "']");
  }
  // Setup ghost image
  const target_img = drag_target
    .querySelector("img")
    .src.substr(drag_target.querySelector("img").src.lastIndexOf("/") + 1);
  const ghost_id = drag_dict[target_img];
  document.querySelectorAll(".ml_drag_icon").forEach((elt) => {
    elt.style.display = "none";
  });
  document.getElementById(ghost_id).style.display = "inline";
  DOM_dict["ghost_text"].innerText = drag_target.innerText;
  const bounds = drag_target.getBoundingClientRect();
  const parent_bounds = DOM_dict["service_list"].getBoundingClientRect();
  drag_data.start_idx = (bounds.top - parent_bounds.top) / bounds.height;
  drag_data.dy = bounds.height;
  drag_data.max_idx = DOM_dict["service_list"].children.length - 1;
  event.dataTransfer.setDragImage(DOM_dict["drag_ghost"], 0, 0);
}

function drag_over(event) {
  event.preventDefault();
}

function drag_drop(event) {
  const base_y = DOM_dict["service_list"].getBoundingClientRect().top;
  const idx_unbounded = parseInt((event.clientY - base_y) / drag_data.dy);
  const end_idx = Math.max(Math.min(idx_unbounded, drag_data.max_idx), 0);
  websocket.send(
    JSON.stringify({
      action: "command.move-item",
      params: {
        "from-index": drag_data.start_idx,
        "to-index": end_idx,
      },
    })
  );
}

function update_app_init(json_data) {
  Toastify({
    text: "Connected to Malachi server",
    gravity: "bottom",
    position: "left",
    style: { background: "#4caf50" },
  }).showToast();
  screen_state = json_data.params.screen_state;
  DOM_dict["flip_screen_state"].checked = screen_state === "on";

  // Size screen_view div and current_item div based on style
  // Video width = 70% of container div, with padding-bottom set to enforce aspect ratio
  const aspect_ratio = json_data.params.style["aspect-ratio"];
  const aspect_padding = 70 / aspect_ratio + "%";
  DOM_dict["screen_view"].style.paddingBottom = aspect_padding;
  const video_height =
    (0.7 * parseInt(getComputedStyle(DOM_dict["item_area"]).width, 10)) / aspect_ratio;
  const header_height = parseInt(getComputedStyle(DOM_dict["item_header"]).height, 10);
  DOM_dict["current_item"].style.height =
    window.innerHeight - video_height - header_height - 24 + "px";

  // Display style parameters in style tab
  update_style_sliders(json_data.params.style);
  update_text_scale(json_data.params.style);

  // Populate service plan list
  let service_list = "";
  for (const [idx, item] of json_data.params.items.entries()) {
    service_list += "<div class='ml_row' draggable='true' data-idx='" + idx + "' ";
    service_list += "ondragstart='drag_start(event)'>";
    service_list += "<a class='ml_button ml_icon ml_icon_display' ";
    service_list += "onclick='goto_item(" + idx + ")'></a>";
    service_list += "<div class='ml_text' ondblclick='goto_item(" + idx + ")'>";
    service_list += "<img class='ml_small_icon' src='" + icon_dict[item.type] + "' ";
    service_list += "data-idx='" + idx + "' draggable='false' />";
    service_list += item.title + "</div>";
    if (item.type == "song") {
      service_list += "<a class='ml_button ml_icon ml_icon_edit' ";
      service_list += "onclick='edit_song(" + item["song-id"] + ")'></a>";
    }
    service_list += "<a class='ml_button ml_icon ml_icon_minus' ";
    service_list += "onclick='delete_item(" + idx + ")'></a>";
    service_list += "</div>";
  }
  DOM_dict["service_list"].innerHTML = service_list;
  indicate_current_item(json_data.params.item_index);

  // Populate current item title and list
  if (json_data.params.item_index != -1) {
    const current_item = json_data.params.items[json_data.params.item_index];
    display_current_item(current_item, json_data.params.slide_index);
  } else {
    DOM_dict["video_controls"].style.display = "none";
    DOM_dict["presentation_controls"].style.display = "none";
    DOM_dict["current_item_icon"].setAttribute("src", icon_dict["song"]);
    DOM_dict["current_item_name"].innerHTML = "No current item";
    DOM_dict["current_item_list"].innerHTML = "";
  }

  // Populate Presentation, Video, Background and Loop lists
  websocket.send(JSON.stringify({ action: "request.all-presentations", params: {} }));
  websocket.send(JSON.stringify({ action: "request.all-videos", params: {} }));
  websocket.send(JSON.stringify({ action: "request.all-loops", params: {} }));
  websocket.send(JSON.stringify({ action: "request.all-backgrounds", params: {} }));

  // Populate Bible version list
  websocket.send(JSON.stringify({ action: "request.bible-versions", params: {} }));
}

function update_service_overview_update(json_data) {
  // Populate service plan list
  let service_list = "";
  for (const [idx, item] of json_data.params.items.entries()) {
    service_list += "<div class='ml_row' draggable='true' data-idx='" + idx + "' ";
    service_list += "ondragstart='drag_start(event)'>";
    service_list += "<a class='ml_button ml_icon ml_icon_display' ";
    service_list += "onclick='goto_item(" + idx + ")'></a>";
    service_list += "<div class='ml_text' ondblclick='goto_item(" + idx + ")'>";
    if (json_data.params.types[idx].substr(0, 4) == "song") {
      service_list += "<img class='ml_small_icon' src='" + icon_dict["song"] + "' ";
      service_list += "data-idx='" + idx + "' draggable='false' />";
    } else {
      service_list +=
        "<img class='ml_small_icon' src='" + icon_dict[json_data.params.types[idx]] + "' ";
      service_list += "data-idx='" + idx + "' draggable='false' />";
    }
    service_list += item + "</div>";
    if (json_data.params.types[idx].substr(0, 4) == "song") {
      service_list += "<a class='ml_button ml_icon ml_icon_edit' ";
      service_list += "onclick='edit_song(" + json_data.params.types[idx].substr(5) + ")'></a>";
    }
    service_list += "<a class='ml_button ml_icon ml_icon_minus' ";
    service_list += "onclick='delete_item(" + idx + ")'></a>";
    service_list += "</div>";
  }
  DOM_dict["service_list"].innerHTML = service_list;
  indicate_current_item(json_data.params.item_index);

  // Populate current item list
  if (json_data.params.item_index != -1) {
    const current_item = json_data.params.current_item;
    display_current_item(current_item, json_data.params.slide_index);
  } else {
    DOM_dict["video_controls"].style.display = "none";
    DOM_dict["presentation_controls"].style.display = "none";
    DOM_dict["current_item_icon"].setAttribute("src", icon_dict["song"]);
    DOM_dict["current_item_name"].innerHTML = "No current item";
    DOM_dict["current_item_list"].innerHTML = "";
  }
}

function update_display_state(json_data) {
  screen_state = json_data.params.state;
  DOM_dict["flip_screen_state"].checked = screen_state === "on";
  document.activeElement?.blur();
}

function result_all_presentations(json_data) {
  let pres_list = "";
  for (const url of json_data.params.urls) {
    pres_list += "<div class='ml_row'>";
    pres_list += "<div class='ml_text'>" + url.substring(16) + "</div>";
    pres_list += "<a class='ml_button ml_icon ml_icon_plus' ";
    pres_list += "onclick='add_presentation(\"" + url + "\");'></a>";
    pres_list += "</div>";
  }
  DOM_dict["presentation_list"].innerHTML = pres_list;
}

function result_all_videos(json_data) {
  let vid_list = "";
  for (const url of json_data.params.urls) {
    vid_list += "<div class='ml_row'>";
    vid_list += "<img src='" + url + ".jpg' />";
    vid_list += "<div class='ml_text'>" + url.substring(9) + "</div>";
    vid_list += "<a class='ml_button ml_icon ml_icon_plus' ";
    vid_list += "onclick='add_video(\"" + url + "\");'></a>";
    vid_list += "</div>";
  }
  DOM_dict["video_list"].innerHTML = vid_list;
}

function result_all_loops(json_data) {
  let loop_list = "";
  for (const url of json_data.params.urls) {
    loop_list += "<div class='ml_row'>";
    loop_list += "<img src='" + url + ".jpg' />";
    loop_list += "<div class='ml_text'>" + url.substring(8) + "</div>";
    loop_list += "<a class='ml_button ml_icon ml_icon_plus' ";
    loop_list += "onclick='set_loop(\"" + url + "\");'></a>";
    loop_list += "</div>";
  }
  DOM_dict["loop_list"].innerHTML = loop_list;
}

function result_all_backgrounds(json_data) {
  let bg_list = "";
  for (const bg of json_data.params.bg_data) {
    short_url = bg["url"].substring(14);
    fn_params = "'" + bg["url"] + "', " + bg["width"] + ", " + bg["height"];
    bg_list += "<div class='ml_row'>";
    bg_list += "<img src='./backgrounds/thumbnails/" + short_url + "'/>";
    bg_list += "<div class='ml_text'>" + short_url + "</div>";
    bg_list += "<a class='ml_button ml_icon ml_icon_song' ";
    bg_list += 'onclick="set_background_songs(' + fn_params + ');"></a>';
    bg_list += "<a class='ml_button ml_icon ml_icon_bible' ";
    bg_list += 'onclick="set_background_bible(' + fn_params + ');"></a>';
    bg_list += "</div>";
  }
  DOM_dict["background_list"].innerHTML = bg_list;
}

function result_song_details(json_data) {
  if (json_data.params.status == "ok") {
    let full_song = json_data.params["song-data"];
    DOM_dict["e_title"].value = full_song["title"];
    DOM_dict["e_author"].value = full_song["author"];
    DOM_dict["e_book"].value = full_song["song-book-name"];
    DOM_dict["e_number"].value = full_song["song-number"];
    DOM_dict["e_audio"].value = full_song["audio"];
    DOM_dict["e_copyright"].value = full_song["copyright"];
    document.querySelectorAll("input[name=e_remote]").forEach((elt) => {
      elt.checked = false;
    });
    document.querySelector("input[data-lr='" + full_song["remote"] + "']").checked = true;
    let lyrics = "";
    for (const part of full_song["parts"]) {
      lyrics += "<" + part["part"].toUpperCase() + ">\n";
      lyrics += part["data"];
    }
    if (lyrics == "") {
      lyrics = "<V1>\n";
    }
    DOM_dict["e_lyrics"].value = lyrics;

    let fills_array = full_song["fills"];
    let fills_dom = "";
    for (const fill_elt of fills_array) {
      fills_dom += fill_elt + "\n";
    }
    DOM_dict["e_fills"].value = fills_dom.trim();
    update_line_numbers(fills_dom.trim());

    DOM_dict["e_order"].value = full_song["verse-order"].toUpperCase();
    document.querySelectorAll("input[name=e_key]").forEach((elt) => {
      elt.checked = false;
    });
    const t_idx = full_song["transpose-by"];
    DOM_dict["e_transpose"].value = (t_idx + 12) % 12; // +12 needed to ensure remainder is in [0, 12)
    if (full_song["song-key"]) {
      document.querySelector("input[data-ek='" + full_song["song-key"] + "']").checked = true;
      const e_idx = valid_keys.findIndex((element) => element == full_song["song-key"]);
      const t_key = valid_keys[(e_idx + t_idx) % 12];
      DOM_dict["e_transpose_out"].value = t_key;
    } else {
      DOM_dict["e_transpose_out"].value = "-";
    }
    // Ensure that we are in edit song mode, rather than create song mode
    DOM_dict["popup_edit_mode"].innerHTML = "Edit song";
    DOM_dict["popup_edit_song"].style.display = "flex";
    editing_song_id = full_song["song-id"];
  }
}

function response_new_service(json_data) {
  if (json_data.params.status == "unsaved-service") {
    DOM_dict["popup_new_service"].style.display = "flex";
  } else {
    json_toast_response(json_data, "New service started", "Problem starting new service");
  }
}

function response_load_service(json_data) {
  if (json_data.params.status == "unsaved-service") {
    DOM_dict["popup_save_before_load_service"].style.display = "flex";
  } else {
    json_toast_response(json_data, "Service loaded successfully", "Problem loading service");
  }
}

function result_song_titles(json_data) {
  let song_list = "";
  for (const [idx, song] of json_data.params.songs.entries()) {
    if (idx < MAX_LIST_ITEMS) {
      song_list += "<div class='ml_row'>";
      song_list += "<div class='ml_text'>" + song[1] + "</div>";
      song_list += "<a class='ml_button ml_icon ml_icon_edit' ";
      song_list += "onclick='edit_song(" + song[0] + ");'></a>";
      song_list += "<a class='ml_button ml_icon ml_icon_plus' ";
      song_list += "onclick='add_song(" + song[0] + ");'></a>";
      song_list += "</div>";
    } else {
      song_list += "<div class='ml_row'>";
      song_list +=
        "<div class='ml_text'>Maximum search results reached (" + MAX_LIST_ITEMS + ")</div>";
      song_list += "</div>";
      break;
    }
  }
  DOM_dict["song_list"].innerHTML = song_list;
}

function response_save_service(json_data) {
  if (json_data.params.status == "unspecified-service") {
    const cur_date = new Date();
    const date_str = cur_date.toISOString().replace("T", " ").replace(/:/g, "-");
    DOM_dict["f_name"].value = date_str.substring(0, date_str.length - 5) + ".json";
    DOM_dict["popup_save_service_as"].style.display = "flex";
  } else {
    // Save has been successful
    json_toast_response(json_data, "Service saved", "Problem saving service");
    if (action_after_save == "new") {
      action_after_save = "none";
      new_service(true);
    } else if (action_after_save == "load") {
      action_after_save = "none";
      load_service(true);
    }
  }
}

function select_file(idx) {
  document.querySelectorAll("#load_files_radio .ml_row").forEach((elt) => {
    if (elt.classList.contains("selected")) {
      elt.classList.remove("selected");
    }
  });
  DOM_dict["load_files_radio"].childNodes[idx].classList.add("selected");
}

function result_all_services(json_data) {
  let files_list = "";
  if (json_data.params.filenames.length != 0) {
    for (const [idx, file] of json_data.params.filenames.entries()) {
      files_list += "<div class='ml_row' id='files-" + idx + "' ";
      files_list += "onclick=select_file(" + idx + ")>";
      files_list += "<div class='ml_text'>" + file + "</div>";
      files_list += "</div>";
    }
    DOM_dict["load_files_radio"].innerHTML = files_list;
    document.getElementById("files-0").classList.add("selected");
  } else {
    files_list += "<div class='ml_row'><div class='ml_text'>";
    files_list += "<em>No saved service plans</em></div><div>";
    DOM_dict["load_files_radio"].innerHTML = files_list;
  }
  DOM_dict["popup_load_service"].style.display = "flex";
  DOM_dict["load_files_radio"].scrollTop = 0;
}

function result_bible_versions(json_data) {
  let radios_html = "";
  let radios_main_html = "<span>Primary version:</span>";
  let radios_alt_html = "<span>Parallel version:</span>";
  let radios_def_html = "<span>Default Bible version:</span>";
  for (const [idx, version] of json_data.params.versions.entries()) {
    radios_html += '<input type="radio" name="b_version" id="b_version_' + idx;
    radios_main_html += '<input type="radio" name="b_main_version" id="b_main_version_' + idx;
    radios_alt_html += '<input type="checkbox" name="b_alt_version" id="b_alt_version_' + idx;
    radios_def_html += '<input type="radio" name="d_version" id="d_version_' + idx;
    radios_html += '" data-bv="' + version + '" data-role="none"/>';
    radios_main_html += '" data-bv="' + version + '" data-role="none"/>';
    radios_alt_html += '" data-bv="' + version + '" data-role="none"/>';
    radios_def_html += '" data-dv="' + version + '" data-role="none"/>';
    radios_html += '<label for="b_version_' + idx + '">' + version + "</label>";
    radios_main_html += '<label for="b_main_version_' + idx + '">' + version + "</label>";
    radios_alt_html += '<label for="b_alt_version_' + idx + '">' + version + "</label>";
    radios_def_html += '<label for="d_version_' + idx + '">' + version + "</label>";
  }
  DOM_dict["b_version_radios"].innerHTML = radios_html;
  DOM_dict["b_main_version_radios"].innerHTML = radios_main_html;
  DOM_dict["b_alt_version_radios"].innerHTML = radios_alt_html;
  DOM_dict["d_version_radios"].innerHTML = radios_def_html;

  // Attach event listeners
  document.querySelectorAll('input[name="b_version"]').forEach((elt) => {
    elt.addEventListener("change", (e) => {
      if (
        document.querySelectorAll("#passage_list input").length > 0 &&
        DOM_dict["bible_search"].value.trim() != ""
      ) {
        // A search has already been performed, so repeat the search with the new version
        bible_search();
      }
    });
  });
  document.querySelectorAll('input[name="b_main_version"]').forEach((elt) => {
    elt.addEventListener("change", (e) => {
      new_version = document
        .querySelector("input[name=b_main_version]:checked")
        .getAttribute("data-bv");
      websocket.send(
        JSON.stringify({
          action: "command.change-bible-version",
          params: {
            version: new_version,
          },
        })
      );
    });
  });
  document.querySelectorAll('input[name="b_alt_version"]').forEach((elt) => {
    elt.addEventListener("change", (e) => {
      new_version = e.target.getAttribute("data-bv");
      if (e.target.checked) {
        websocket.send(
          JSON.stringify({
            action: "command.change-bible-pl-version",
            params: {
              version: new_version,
            },
          })
        );
      } else {
        websocket.send(
          JSON.stringify({
            action: "command.remove-bible-pl-version",
            params: {},
          })
        );
      }
    });
  });
  if (saved_current_item != null && saved_current_item.type == "bible") {
    indicate_bible_versions(saved_current_item.version, saved_current_item.parallel_version);
  }
  document.querySelectorAll('input[name="d_version"]').forEach((elt) => {
    elt.addEventListener("change", (e) => {
      new_version = document.querySelector("input[name=d_version]:checked").getAttribute("data-dv");
      websocket.send(
        JSON.stringify({
          action: "command.edit-style-param",
          params: {
            param: style_dict["d_version"],
            value: new_version,
          },
        })
      );
    });
  });
  // Force style sliders and search version to update to reflect default Bible version
  document.querySelectorAll("input[name='b_version']").forEach((elt) => {
    elt.checked = false;
  });
  if (saved_style) {
    update_style_sliders(saved_style);
    // Use querySelectorAll to enable graceful fail if saved Bible version no longer available
    document
      .querySelectorAll(
        "#b_version_radios input[data-bv='" + saved_style[style_dict["d_version"]] + "']"
      )
      .forEach((elt) => {
        elt.checked = true;
      });
  } else {
    document.querySelector('input[name="b_version"]:first-of-type').checked = true;
  }
}

function trigger_play_video() {
  video_interval = setInterval(video_tick, 1000);
}

function trigger_pause_video() {
  clearInterval(video_interval);
}

function trigger_stop_video() {
  clearInterval(video_interval);
  video_timer = 0;
  DOM_dict["time_seek"].value = video_timer;
}

function trigger_seek_video(json_data) {
  video_timer = json_data.params.seconds;
  DOM_dict["time_seek"].value = video_timer;
}

function result_bible_verses(json_data) {
  let bible_list = "";
  if (json_data.params.status !== "ok") {
    json_toast_response(json_data, "Bible search success", "Problem performing Bible search");
  }
  for (const [idx, verse] of json_data.params.verses.entries()) {
    if (idx < MAX_VERSE_ITEMS) {
      bible_ref = verse[1] + " " + verse[2] + ":" + verse[3];
      bible_list += "<div class='ml_row ml_expand_row selected'>";
      bible_list += "<div class='ml_text ml_multitext' name='v_list' ";
      bible_list += "id='v-" + verse[0] + "' onclick='toggle_verse(" + idx;
      bible_list += ")'><p class='ml_bibleverse'>";
      bible_list += "<strong>" + bible_ref + "</strong>&nbsp; " + verse[4];
      bible_list += "</p></div>";
      bible_list += "</div>";
    }
  }
  DOM_dict["passage_list"].innerHTML = bible_list;
}

function toggle_verse(idx) {
  if (DOM_dict["passage_list"].childNodes[idx].classList.contains("selected")) {
    DOM_dict["passage_list"].childNodes[idx].classList.remove("selected");
  } else {
    DOM_dict["passage_list"].childNodes[idx].classList.add("selected");
  }
}

function remove_audio() {
  DOM_dict["e_audio"].value = "";
}

function audio_popup_preload() {
  websocket.send(JSON.stringify({ action: "request.all-audio", params: {} }));
}

function select_audio(idx) {
  document.querySelectorAll("#attach_audio_radio .ml_row").forEach((elt) => {
    if (elt.classList.contains("selected")) {
      elt.classList.remove("selected");
    }
  });
  DOM_dict["attach_audio_radio"].childNodes[idx].classList.add("selected");
}

function show_audio_popup(json_data) {
  let mp3_list = "";
  if (json_data.params.urls.length != 0) {
    for (const [idx, url] of json_data.params.urls.entries()) {
      mp3_list += "<div class='ml_row' id='mp3-" + idx + "' ";
      mp3_list += "onclick=select_audio(" + idx + ")>";
      mp3_list += "<div class='ml_text'>" + url + "</div>";
      mp3_list += "</div>";
    }
    DOM_dict["attach_audio_radio"].innerHTML = mp3_list;
    document.getElementById("mp3-0").classList.add("selected");
  } else {
    mp3_list += "<div class='ml_row'><div class='ml_text'>";
    mp3_list += "<em>No audio files found</em></div><div>";
    DOM_dict["attach_audio_radio"].innerHTML = mp3_list;
  }
  DOM_dict["popup_edit_song"].style.display = "none";
  DOM_dict["popup_attach_audio"].style.display = "flex";
  DOM_dict["popup_attach_audio"].scrollTop = 0;
}

function attach_audio() {
  const sel_text = document.querySelector(
    "#attach_audio_radio .ml_row.selected .ml_text"
  ).innerText;
  DOM_dict["e_audio"].value = sel_text;
  close_attach_audio_popup();
}

function close_attach_audio_popup() {
  DOM_dict["popup_edit_song"].style.display = "flex";
  DOM_dict["popup_attach_audio"].style.display = "none";
}

function update_line_numbers(fill_text) {
  const number_of_lines = fill_text.split("\n").length;
  DOM_dict["line_numbers"].innerHTML = Array(number_of_lines)
    .fill()
    .map((_, i) => "<span>:" + (i + 1) + "</span>")
    .join("");
}

function start_websocket() {
  websocket = null;
  websocket = new WebSocket("ws://" + window.location.hostname + ":9001/app");
  websocket.onmessage = function (event) {
    json_data = JSON.parse(event.data);
    console.log(json_data);
    switch (json_data.action) {
      case "update.app-init":
        update_app_init(json_data);
        break;
      case "update.service-overview-update":
        update_service_overview_update(json_data);
        break;
      case "update.slide-index-update":
        indicate_current_slide(json_data.params.slide_index);
        break;
      case "update.item-index-update":
        indicate_current_item(json_data.params.item_index);
        display_current_item(json_data.params.current_item, json_data.params.slide_index);
        break;
      case "update.display-state":
        update_display_state(json_data);
        break;
      case "update.style-update":
        update_style_sliders(json_data.params.style);
        update_text_scale(json_data.params.style);
        break;
      case "result.all-audio":
        show_audio_popup(json_data);
        break;
      case "result.all-presentations":
        result_all_presentations(json_data);
        break;
      case "result.all-videos":
        result_all_videos(json_data);
        break;
      case "result.all-loops":
        result_all_loops(json_data);
        break;
      case "result.all-backgrounds":
        result_all_backgrounds(json_data);
        break;
      case "result.song-details":
        result_song_details(json_data);
        break;
      case "response.new-service":
        response_new_service(json_data);
        break;
      case "response.load-service":
        response_load_service(json_data);
        break;
      case "response.export-service":
        json_toast_response(
          json_data,
          "Service exported successfully",
          "Problem exporting service"
        );
        break;
      case "result.song-titles":
        result_song_titles(json_data);
        break;
      case "response.save-service":
        response_save_service(json_data);
        break;
      case "result.all-services":
        result_all_services(json_data);
        break;
      case "result.bible-versions":
        result_bible_versions(json_data);
        break;
      case "result.bible-verses":
        result_bible_verses(json_data);
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
      case "response.add-video":
        json_toast_response(json_data, "Video added to service", "Problem adding video");
        break;
      case "response.add-song-item":
        json_toast_response(json_data, "Song added to service", "Problem adding song");
        break;
      case "response.edit-song":
        json_toast_response(json_data, "Song edited", "Problem editing song");
        break;
      case "response.create-song":
        json_toast_response(json_data, "Song added", "Could not add song");
        break;
      case "response.add-presentation":
        json_toast_response(
          json_data,
          "Presentation added to service",
          "Problem adding presentation"
        );
        break;
      case "response.set-loop":
        json_toast_response(json_data, "Video loop set", "Problem setting video loop");
        break;
      case "response.clear-loop":
        json_toast_response(json_data, "Video loop cancelled", "Problem cancelling video loop");
        break;
      case "response.add-bible-item":
        json_toast_response(
          json_data,
          "Bible passage added to service",
          "Problem adding Bible passage"
        );
        break;
      case "response.change-bible-version":
        json_toast_response(json_data, "Bible version changed", "Problem changing Bible version");
        break;
      case "response.change-bible-pl-version":
        json_toast_response(
          json_data,
          "Parallel Bible version changed",
          "Problem changing parallel Bible version"
        );
        break;
      case "response.remove-bible-pl-version":
        json_toast_response(
          json_data,
          "Parallel Bible version removed",
          "Problem removing parallel Bible version"
        );
        break;
      case "response.remove-item":
        json_toast_response(json_data, "Item removed", "Problem removing item");
        break;
      case "response.stop-capture":
        json_toast_response(json_data, "Capturing stopped", "Problem stopping capture");
        break;
      case "response.start-capture":
        json_toast_response(json_data, "Capturing started", "Problem starting capture");
        break;
      case "response.start-presentation":
        json_toast_response(json_data, "Starting presentation...", "Problem starting presentation");
        break;
      case "update.video-loop":
      case "update.capture-update":
      case "update.start-capture":
      case "update.stop-capture":
      case "response.move-item":
      case "response.next-item":
      case "response.previous-item":
      case "response.goto-item":
      case "response.next-slide":
      case "response.previous-slide":
      case "response.goto-slide":
      case "response.set-display-state":
      case "response.play-video":
      case "response.pause-video":
      case "response.stop-video":
      case "response.play-audio":
      case "response.pause-audio":
      case "response.stop-audio":
      case "response.edit-style-param":
      case "response.edit-style-params":
      case "response.change-capture-rate":
      case "response.start-countdown":
      case "trigger.start-countdown":
      case "response.clear-countdown":
      case "trigger.clear-countdown":
      case "trigger.restore-loop":
      case "response.restore-loop":
      case "trigger.suspend-loop":
      case "trigger.play-audio":
      case "trigger.pause-audio":
      case "trigger.stop-audio":
        break; // No action required;
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
  for (const key of DOM_KEYS) {
    DOM_dict[key] = document.getElementById(key);
  }
  DOM_dict["flip_screen_state"].addEventListener("change", change_screen_state_flip);

  DOM_dict["song_search"].addEventListener("keypress", (e) => {
    const key_code = e.which ? e.which : e.keyCode;
    if (key_code == 13) {
      song_search();
    }
  });

  document.querySelector('input[data-lrs="0"]').checked = true;
  document.querySelector('input[data-lrs="1"]').checked = false;
  document.querySelectorAll('input[name="lr_search"]').forEach((elt) => {
    elt.addEventListener("change", song_search);
  });

  DOM_dict["bible_search"].addEventListener("keypress", (e) => {
    const key_code = e.which ? e.which : e.keyCode;
    if (key_code == 13) {
      bible_search();
    }
  });

  DOM_dict["e_transpose"].addEventListener("change", update_transpose_slider);
  document.querySelectorAll('input[name="e_key"]').forEach((elt) => {
    elt.addEventListener("change", update_transpose_slider);
  });

  DOM_dict["e_fills"].addEventListener("keyup", (event) => {
    update_line_numbers(event.target.value);
  });

  DOM_dict["e_fills"].addEventListener("blur", (event) => {
    // Remove any blank lines from fill list
    let fill_lines = event.target.value
      .split("\n")
      .filter((x) => x.trim() != "")
      .join("\n");
    event.target.value = fill_lines;
    update_line_numbers(fill_lines);
  });

  document.querySelectorAll("input[name='o_style']").forEach((elt) => {
    elt.addEventListener("change", (e) => {
      websocket.send(
        JSON.stringify({
          action: "command.edit-style-param",
          params: {
            param: "outline-style",
            value: elt.getAttribute("data-ol"),
          },
        })
      );
    });
  });

  DOM_dict["cd_text"].addEventListener("blur", (e) => {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "countdown-h-text",
          value: e.target.value,
        },
      })
    );
  });

  DOM_dict["d_copyright"].addEventListener("change", (e) => {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "display-copyright",
          value: e.target.checked,
        },
      })
    );
  });

  DOM_dict["d_verseorder"].addEventListener("change", (e) => {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "display-verseorder",
          value: e.target.checked,
        },
      })
    );
  });

  DOM_dict["cd_time"].value = String((new Date().getHours() + 1) % 24).padStart(2, "0") + ":00";

  window.addEventListener("resize", (e) => {
    // Size screen_view div and current_item div based on style
    // Video width = 70% of container div, with padding-bottom set to enforce aspect ratio
    const aspect_padding = 70 / aspect_ratio + "%";
    DOM_dict["screen_view"].style.paddingBottom = aspect_padding;
    const video_height =
      (0.7 * parseInt(getComputedStyle(DOM_dict["item_area"]).width, 10)) / aspect_ratio;
    DOM_dict["current_item"].style.height = window.innerHeight - video_height - 24 + "px";
  });

  start_websocket();
});

document.addEventListener("keydown", (e) => {
  const key_code = e.which ? e.which : e.keyCode;
  const tag = e.target.tagName.toLowerCase();
  if (tag != "input" && tag != "textarea") {
    switch (key_code) {
      case 38: // Up arrow
        previous_slide();
        break;
      case 40: // Down arrow
        next_slide();
        break;
      case 33: // PG_UP
        previous_item();
        break;
      case 34: // PG_DOWN
        next_item();
        break;
      case 84: // T
      case 116: // t
        toggle_display_state();
        break;
      case 49: // 1 - Service element
        load_element("service");
        break;
      case 50: // 2 - Song element
        load_element("song");
        break;
      case 51: // 3 - Bible element
        load_element("bible");
        break;
      case 52: // 4 - Presentation element
        load_element("presentation");
        break;
      case 53: // 5 - Video element
        load_element("video");
        break;
      case 54: // 6 - Backgrounds element
        load_element("backgrounds");
        break;
      case 55: // 7 - Styles element
        load_element("styles");
        break;
    }
  }
});
