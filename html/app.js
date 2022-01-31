let websocket;
const MAX_LIST_ITEMS = 50;
const MAX_VERSE_ITEMS = 2500;
const SELECTED_COLOR = "gold";
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
let update_slider = true;
let valid_keys = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
let drag_data = { start_idx: -1, dy: -1, max_idx: -1 };

style_dict["s_width"] = "div-width-vw";
style_dict["s_font_size"] = "font-size-vh";
style_dict["s_lines"] = "max-lines";
style_dict["s_margin"] = "margin-top-vh";
style_dict["ch_size"] = "countdown-h-size-vh";
style_dict["cd_size"] = "countdown-size-vh";
style_dict["cd_top"] = "countdown-top-vh";
style_dict["cp_size"] = "copy-size-vh";
style_dict["cp_width"] = "copy-width-vw";
style_dict["vo_size"] = "order-size-vh";
style_dict["vo_width"] = "order-width-vw";

icon_dict["bible"] = "/html/icons/icons8-literature-48.png";
icon_dict["song"] = "/html/icons/icons8-musical-notes-48.png";
icon_dict["presentation"] = "/html/icons/icons8-presentation-48.png";
icon_dict["video"] = "/html/icons/icons8-tv-show-48.png";

drag_dict["/html/icons/icons8-literature-48.png"] = "drag_bible_icon";
drag_dict["/html/icons/icons8-musical-notes-48.png"] = "drag_song_icon";
drag_dict["/html/icons/icons8-presentation-48.png"] = "drag_presentation_icon";
drag_dict["/html/icons/icons8-tv-show-48.png"] = "drag_video_icon";

function change_screen_state_flip() {
  str_state = document.getElementById("flip_screen_state").checked ? "on" : "off";
  websocket.send(
    JSON.stringify({
      action: "command.set-display-state",
      params: { state: str_state },
    })
  );
}

function add_verses() {
  verses = document.querySelectorAll("input[name=v_list]:checked");
  version = document.querySelector("input[name=b_version]:checked").getAttribute("data-bv");
  if (verses.length > 0) {
    let range_start = verses[0].id.substr(2);
    let prev_id = range_start - 1;
    let v_id;
    for (v = 0; v < verses.length; v++) {
      v_id = verses[v].id.substr(2);
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
  document.querySelectorAll("#passage_list input[type=checkbox]").forEach((elt) => {
    elt.checked = true;
  });
}

function select_none_verses() {
  document.querySelectorAll("#passage_list input[type=checkbox]").forEach((elt) => {
    elt.checked = false;
  });
}

function load_service_preload() {
  websocket.send(JSON.stringify({ action: "request.all-services", params: {} }));
}

function load_service(force) {
  document.getElementById("popup_save_before_load_service").style.display = "none";
  document.getElementById("popup_load_service").style.display = "none";
  if (document.querySelectorAll("input[name=files]").length > 0) {
    sel_radio = parseInt(document.querySelector("input[name=files]:checked").id.substring(6));
    sel_text = document.querySelector(
      "#load_files_radio .ml_row:nth-child(" + (sel_radio + 1) + ") .ml_text"
    ).innerText;
    websocket.send(
      JSON.stringify({
        action: "command.load-service",
        params: { filename: sel_text, force: force },
      })
    );
  }
}

function open_save_service_popup() {
  document.getElementById("popup_save_service_as").style.display = "flex";
}

function open_export_service_popup() {
  document.getElementById("popup_export_service_as").style.display = "flex";
}

function save_service_as() {
  f_name = document.getElementById("f_name").value;
  document.getElementById("popup_save_service_as").style.display = "none";
  // Replace invalid characters to avoid errors and prevent file being saved in other directories
  clean_name = f_name.replace(/[\\\/\"\':;*<>|]/g, "");
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
  document.getElementById("f_name").value = "";
}

function export_service_as() {
  f_name = document.getElementById("exp_name").value;
  document.getElementById("popup_export_service_as").style.display = "none";
  // Replace invalid characters to avoid errors and prevent file being saved in other directories
  clean_name = f_name.replace(/[\\\/\"\':;*<>|]/g, "");
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
  document.getElementById("exp_name").value = "";
}

function save_service(action_after) {
  document.getElementById("popup_new_service").style.display = "none";
  document.getElementById("popup_save_before_load_service").style.display = "none";
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
  song_val = document
    .getElementById("song_search")
    .value.replace(/[^0-9a-z ]/gi, "")
    .trim();
  remote_val = parseInt(
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
    document.getElementById("song_list").innerHTML = "";
  }
}

function bible_search() {
  if (document.querySelector("input[name=b_search_type]:checked").id == "b_search_type_ref") {
    if (document.getElementById("bible_search").value.trim() !== "") {
      websocket.send(
        JSON.stringify({
          action: "query.bible-by-ref",
          params: {
            version: document
              .querySelector("input[name=b_version]:checked")
              .getAttribute("data-bv"),
            "search-ref": document.getElementById("bible_search").value.trim(),
          },
        })
      );
    } else {
      document.getElementById("passage_list").innerHTML = "";
    }
  } else {
    if (document.getElementById("bible_search").value.trim().length > 2) {
      websocket.send(
        JSON.stringify({
          action: "query.bible-by-text",
          params: {
            version: document
              .querySelector("input[name=b_version]:checked")
              .getAttribute("data-bv"),
            "search-text": document.getElementById("bible_search").value.trim(),
          },
        })
      );
    } else {
      toast_error("Please enter at least three characters to search by text");
    }
  }
}

function new_service(force) {
  document.getElementById("popup_new_service").style.display = "none";
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
  if (update_slider == true) {
    document.getElementById("time_seek").value = video_timer;
  }
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

function start_countdown() {
  var now = new Date();
  var target = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate(),
    document.getElementById("cd_time").value.split(":")[0],
    document.getElementById("cd_time").value.split(":")[1],
    0
  );
  var cd_length = Math.floor((target.getTime() - now.getTime()) / 1000);
  if (cd_length > 0) {
    websocket.send(
      JSON.stringify({
        action: "command.start-countdown",
        params: {
          hr: document.getElementById("cd_time").value.split(":")[0],
          min: document.getElementById("cd_time").value.split(":")[1],
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
  document.getElementById("e_title").value = "";
  document.getElementById("e_author").value = "";
  document.getElementById("e_book").value = "";
  document.getElementById("e_number").value = "";
  document.getElementById("e_book").value = "";
  document.getElementById("e_copyright").value = "";
  document.getElementById("e_lyrics").value = "<V1>\n";
  document.getElementById("e_order").value = "";
  document.querySelectorAll("input[name='e_key']").forEach((elt) => {
    elt.checked = false;
  });
  document.querySelector("input[data-lr='0']").checked = true;
  document.querySelector("input[data-lr='1']").checked = false;
  document.getElementById("e_transpose").value = 0;
  document.getElementById("e_transpose_out").value = "-";
  // Switch into create song mode
  document.getElementById("popup_edit_mode").innerHTML = "Create song";
  // Display popup
  document.getElementById("popup_edit_song").style.display = "flex";
}

function reset_edit_song_form() {
  document.getElementById("e_title_span").style.color = "black";
  document.getElementById("e_title_span").style.fontWeight = "normal";
}

function save_song() {
  // Validation: title can't be empty, other validation carried out by server
  if (document.getElementById("e_title").value.trim() == "") {
    document.getElementById("e_title_span").style.color = "red";
    document.getElementById("e_title_span").style.fontWeight = "bold";
  } else {
    reset_edit_song_form();
    let lyric_text = document.getElementById("e_lyrics").value;
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
        current_part = line.substr(1, line.length - 2).toLowerCase();
        current_lines = [];
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

    let fields = {
      author: document.getElementById("e_author").value,
      transpose_by: document.getElementById("e_transpose").value % 12,
      lyrics_chords: parts,
      verse_order: document.getElementById("e_order").value.toLowerCase(),
      song_book_name: document.getElementById("e_book").value,
      song_number: document.getElementById("e_number").value,
      copyright: document.getElementById("e_copyright").value,
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

    if (document.getElementById("popup_edit_mode").innerText == "Edit song") {
      fields["title"] = document.getElementById("e_title").value;
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
            title: document.getElementById("e_title").value,
            fields: fields,
          },
        })
      );
    }
    document.getElementById("popup_edit_song").style.display = "none";
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
  document.getElementById("current_item_icon").setAttribute("src", icon_dict[current_item.type]);
  document.getElementById("current_item_name").innerHTML = current_item.title;

  // Reset video seek track
  clearInterval(video_interval);
  video_timer = 0;
  document.getElementById("time_seek").value = video_timer;

  if (current_item.type == "song") {
    min_verse_order = current_item["verse-order"].split(" ");
    part_counts = current_item["part-counts"];
    max_verse_order = [];
    for (i = 0; i < min_verse_order.length; i++) {
      for (j = 0; j < part_counts[i]; j++) {
        max_verse_order.push(min_verse_order[i].toUpperCase());
      }
    }
  }

  if (current_item.type == "video") {
    document.getElementById("video_controls").style.display = "block";
    document.getElementById("time_seek").max = current_item.duration;
  } else {
    document.getElementById("video_controls").style.display = "none";
  }

  if (current_item.type == "presentation") {
    document.getElementById("presentation_controls").style.display = "block";
  } else {
    document.getElementById("presentation_controls").style.display = "none";
  }

  let item_list = "";
  for (const [idx, slide] of current_item.slides.entries()) {
    if (current_item.type == "song") {
      slide_lines = slide.split(/\n/);
      slide_text =
        "<p class='ml_songlyric'><span class='ml_songpart'>" + max_verse_order[idx] + "</span>";
      for (const line of slide_lines) {
        line_segments = line.split(/\[[\w\+#\/"='' ]*\]/);
        for (const segment of line_segments) {
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
  document.getElementById("current_item_list").innerHTML = item_list;

  // Indicate selection of slide_index
  indicate_current_slide(slide_index);
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
    item_top =
      document
        .querySelector("#current_item_list div.ml_row:nth-child(" + (slide_index + 1) + ")")
        .getBoundingClientRect().top + document.body.scrollTop;
    item_height = document.querySelector(
      "#current_item_list div.ml_row:nth-child(" + (slide_index + 1) + ")"
    ).offsetHeight;
    viewable_top =
      document.getElementById("current_item").getBoundingClientRect().top + document.body.scrollTop;
    list_top =
      document.getElementById("current_item_list").getBoundingClientRect().top +
      document.body.scrollTop;
    scroll_top = document.getElementById("current_item").scrollTop;
    window_height = window.innerHeight;
    if (item_top < viewable_top) {
      document.getElementById("current_item").scrollTop = item_top - list_top;
    } else if (item_top + item_height > window_height) {
      document.getElementById("current_item").scrollTop =
        8 + scroll_top + item_top + item_height - window_height;
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

function update_style_sliders(style) {
  document.getElementById("s_width").value = style[style_dict["s_width"]];
  document.getElementById("s_width_out").value = style[style_dict["s_width"]];
  document.getElementById("s_font_size").value = style[style_dict["s_font_size"]];
  document.getElementById("s_font_size_out").value = style[style_dict["s_font_size"]];
  document.getElementById("s_lines").value = style[style_dict["s_lines"]];
  document.getElementById("s_lines_out").value = style[style_dict["s_lines"]];
  document.getElementById("s_margin").value = style[style_dict["s_margin"]];
  document.getElementById("s_margin_out").value = style[style_dict["s_margin"]];
  document.querySelectorAll("input[name='o_style']").forEach((elt) => {
    elt.checked = false;
  });
  document.querySelector("input[data-ol='" + style["outline-style"] + "']").checked = true;
  document.getElementById("ch_size").value = style[style_dict["ch_size"]];
  document.getElementById("ch_size_out").value = style[style_dict["ch_size"]];
  document.getElementById("cd_size").value = style[style_dict["cd_size"]];
  document.getElementById("cd_size_out").value = style[style_dict["cd_size"]];
  document.getElementById("cd_top").value = style[style_dict["cd_top"]];
  document.getElementById("cd_top_out").value = style[style_dict["cd_top"]];
  document.getElementById("cd_text").value = style["countdown-h-text"];
  document.getElementById("d_copyright").checked = style["display-copyright"];
  document.getElementById("cp_size").value = style[style_dict["cp_size"]];
  document.getElementById("cp_size_out").value = style[style_dict["cp_size"]];
  document.getElementById("cp_width").value = style[style_dict["cp_width"]];
  document.getElementById("cp_width_out").value = style[style_dict["cp_width"]];
  document.getElementById("d_verseorder").checked = style["display-verseorder"];
  document.getElementById("vo_size").value = style[style_dict["vo_size"]];
  document.getElementById("vo_size_out").value = style[style_dict["vo_size"]];
  document.getElementById("vo_width").value = style[style_dict["vo_width"]];
  document.getElementById("vo_width_out").value = style[style_dict["vo_width"]];
  document.getElementById("t_color").value = style["font-color"];
  // Update background status items
  if (style["song-background-url"] == "none") {
    document.getElementById("song_bg_icon").setAttribute("src", "");
  } else {
    document
      .getElementById("song_bg_icon")
      .setAttribute("src", "./backgrounds/thumbnails/" + style["song-background-url"].substr(14));
  }
  if (style["bible-background-url"] == "none") {
    document.getElementById("bible_bg_icon").setAttribute("src", "");
  } else {
    document
      .getElementById("bible_bg_icon")
      .setAttribute("src", "./backgrounds/thumbnails/" + style["bible-background-url"].substr(14));
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
    e_val = document.querySelector("input[name=e_key]:checked").getAttribute("data-ek");
    e_idx = valid_keys.findIndex((element) => element == e_val);
    t_idx = parseInt(document.getElementById("e_transpose").value, 10);
    t_key = valid_keys[(e_idx + t_idx) % 12];
    document.getElementById("e_transpose_out").value = t_key;
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

function close_popup(elt_id) {
  document.getElementById(elt_id).style.display = "none";
}

function close_save_as_popup() {
  document.getElementById("f_name").value = "";
  document.getElementById("popup_save_service_as").style.display = "none";
}

function close_export_as_popup() {
  document.getElementById("exp_name").value = "";
  document.getElementById("popup_export_service_as").style.display = "none";
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

function drag_start(event) {
  drag_target = event.target;
  if (event.target.tagName == "IMG") {
    const idx = event.target.getAttribute("data-idx");
    drag_target = document.querySelector("#service_list .ml_row[data-idx='" + idx + "']");
  }
  // Setup ghost image
  const ghost_id = drag_dict[drag_target.querySelector("img").src.substr(21)];
  document.querySelectorAll(".ml_drag_icon").forEach((elt) => {
    elt.style.display = "none";
  });
  document.getElementById(ghost_id).style.display = "inline";
  document.getElementById("ghost_text").innerText = drag_target.innerText;
  const bounds = drag_target.getBoundingClientRect();
  const parent_bounds = document.getElementById("service_list").getBoundingClientRect();
  drag_data.start_idx = (bounds.top - parent_bounds.top) / bounds.height;
  drag_data.dy = bounds.height;
  drag_data.max_idx = document.getElementById("service_list").children.length - 1;
  event.dataTransfer.setDragImage(document.getElementById("drag_ghost"), 0, 0);
}

function drag_over(event) {
  event.preventDefault();
}

function drag_drop(event) {
  const base_y = document.getElementById("service_list").getBoundingClientRect().top;
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

function start_websocket() {
  websocket = null;
  websocket = new WebSocket("ws://" + window.location.hostname + ":9001/app");
  websocket.onmessage = function (event) {
    json_data = JSON.parse(event.data);
    console.log(json_data);
    switch (json_data.action) {
      case "update.app-init":
        Toastify({
          text: "Connected to Malachi server",
          gravity: "bottom",
          position: "left",
          style: { background: "#4caf50" },
        }).showToast();
        screen_state = json_data.params.screen_state;
        if (screen_state === "on") {
          bool_screen_state = true;
        } else {
          bool_screen_state = false;
        }
        document.getElementById("flip_screen_state").checked = bool_screen_state;

        // Size screen_view div and current_item div based on style
        // Video width = 70% of container div, with padding-bottom set to enforce aspect ratio
        aspect_ratio = json_data.params.style["aspect-ratio"];
        aspect_padding = 70 / aspect_ratio + "%";
        document.getElementById("screen_view").style.paddingBottom = aspect_padding;
        video_height =
          (0.7 * parseInt(getComputedStyle(document.getElementById("item_area")).width, 10)) /
          aspect_ratio;
        header_height = parseInt(
          getComputedStyle(document.getElementById("item_header")).height,
          10
        );
        document.getElementById("current_item").style.height =
          window.innerHeight - video_height - header_height - 16 + "px";

        // Display style parameters in style tab
        update_style_sliders(json_data.params.style);

        // Populate service plan list
        service_list = "";
        for (const [idx, item] of json_data.params.items.entries()) {
          service_list += "<div class='ml_row' draggable='true' data-idx='" + idx + "' ";
          service_list += "ondragstart='drag_start(event)'>";
          service_list += "<a href='#' class='ml_button ml_icon ml_icon_display' ";
          service_list += "onclick='goto_item(" + idx + ")'></a>";
          service_list += "<div class='ml_text' ondblclick='goto_item(" + idx + ")'>";
          service_list += "<img class='ml_small_icon' src='" + icon_dict[item.type] + "' ";
          service_list += "data-idx='" + idx + "' draggable='false' />";
          service_list += item.title + "</div>";
          if (item.type == "song") {
            service_list += "<a href='#' class='ml_button ml_icon ml_icon_edit' ";
            service_list += "onclick='edit_song(" + item["song-id"] + ")'></a>";
          }
          service_list += "<a href='#' class='ml_button ml_icon ml_icon_minus' ";
          service_list += "onclick='delete_item(" + idx + ")'></a>";
          service_list += "</div>";
        }
        document.getElementById("service_list").innerHTML = service_list;
        indicate_current_item(json_data.params.item_index);

        // Populate current item title and list
        if (json_data.params.item_index != -1) {
          current_item = json_data.params.items[json_data.params.item_index];
          display_current_item(current_item, json_data.params.slide_index);
        } else {
          document.getElementById("video_controls").style.display = "none";
          document.getElementById("presentation_controls").style.display = "none";
          document.getElementById("current_item_icon").setAttribute("src", icon_dict["song"]);
          document.getElementById("current_item_name").innerHTML = "No current item";
          document.getElementById("current_item_list").innerHTML = "";
        }

        // Populate Presentation, Video, Background and Loop lists
        websocket.send(JSON.stringify({ action: "request.all-presentations", params: {} }));
        websocket.send(JSON.stringify({ action: "request.all-videos", params: {} }));
        websocket.send(JSON.stringify({ action: "request.all-loops", params: {} }));
        websocket.send(JSON.stringify({ action: "request.all-backgrounds", params: {} }));

        // Populate Bible version list
        websocket.send(JSON.stringify({ action: "request.bible-versions", params: {} }));
        break;

      case "update.service-overview-update":
        // Populate service plan list
        service_list = "";
        for (const [idx, item] of json_data.params.items.entries()) {
          service_list += "<div class='ml_row' draggable='true' data-idx='" + idx + "' ";
          service_list += "ondragstart='drag_start(event)'>";
          service_list += "<a href='#' class='ml_button ml_icon ml_icon_display' ";
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
            service_list += "<a href='#' class='ml_button ml_icon ml_icon_edit' ";
            service_list +=
              "onclick='edit_song(" + json_data.params.types[idx].substr(5) + ")'></a>";
          }
          service_list += "<a href='#' class='ml_button ml_icon ml_icon_minus' ";
          service_list += "onclick='delete_item(" + idx + ")'></a>";
          service_list += "</div>";
        }
        document.getElementById("service_list").innerHTML = service_list;
        indicate_current_item(json_data.params.item_index);

        // Populate current item list
        if (json_data.params.item_index != -1) {
          current_item = json_data.params.current_item;
          display_current_item(current_item, json_data.params.slide_index);
        } else {
          document.getElementById("video_controls").style.display = "none";
          document.getElementById("presentation_controls").style.display = "none";
          document.getElementById("current_item_icon").setAttribute("src", icon_dict["song"]);
          document.getElementById("current_item_name").innerHTML = "No current item";
          document.getElementById("current_item_list").innerHTML = "";
        }
        break;

      case "update.slide-index-update":
        indicate_current_slide(json_data.params.slide_index);
        break;

      case "update.item-index-update":
        indicate_current_item(json_data.params.item_index);
        display_current_item(json_data.params.current_item, json_data.params.slide_index);
        break;

      case "update.display-state":
        screen_state = json_data.params.state;
        if (screen_state === "on") {
          bool_screen_state = true;
        } else {
          bool_screen_state = false;
        }
        document.getElementById("flip_screen_state").checked = bool_screen_state;
        break;

      case "update.style-update":
        update_style_sliders(json_data.params.style);
        break;

      case "result.all-presentations":
        let pres_list = "";
        for (const url of json_data.params.urls) {
          pres_list += "<div class='ml_row'>";
          pres_list += "<div class='ml_text'>" + url.substring(16) + "</div>";
          pres_list += "<a href='#' class='ml_button ml_icon ml_icon_plus' ";
          pres_list += "onclick='add_presentation(\"" + url + "\");'></a>";
          pres_list += "</div>";
        }
        document.getElementById("presentation_list").innerHTML = pres_list;
        break;

      case "result.all-videos":
        let vid_list = "";
        for (const url of json_data.params.urls) {
          vid_list += "<div class='ml_row'>";
          vid_list += "<img src='" + url + ".jpg' />";
          vid_list += "<div class='ml_text'>" + url.substring(9) + "</div>";
          vid_list += "<a href='#' class='ml_button ml_icon ml_icon_plus' ";
          vid_list += "onclick='add_video(\"" + url + "\");'></a>";
          vid_list += "</div>";
        }
        document.getElementById("video_list").innerHTML = vid_list;
        break;

      case "result.all-loops":
        let loop_list = "";
        for (const url of json_data.params.urls) {
          loop_list += "<div class='ml_row'>";
          loop_list += "<img src='" + url + ".jpg' />";
          loop_list += "<div class='ml_text'>" + url.substring(8) + "</div>";
          loop_list += "<a href='#' class='ml_button ml_icon ml_icon_plus' ";
          loop_list += "onclick='set_loop(\"" + url + "\");'></a>";
          loop_list += "</div>";
        }
        document.getElementById("loop_list").innerHTML = loop_list;
        break;

      case "result.all-backgrounds":
        let bg_list = "";
        for (const bg of json_data.params.bg_data) {
          short_url = bg["url"].substring(14);
          fn_params = "'" + bg["url"] + "', " + bg["width"] + ", " + bg["height"];
          bg_list += "<div class='ml_row'>";
          bg_list += "<img src='./backgrounds/thumbnails/" + short_url + "'/>";
          bg_list += "<div class='ml_text'>" + short_url + "</div>";
          bg_list += "<a href='#' class='ml_button ml_icon ml_icon_song' ";
          bg_list += 'onclick="set_background_songs(' + fn_params + ');"></a>';
          bg_list += "<a href='#' class='ml_button ml_icon ml_icon_bible' ";
          bg_list += 'onclick="set_background_bible(' + fn_params + ');"></a>';
          bg_list += "</div>";
        }
        document.getElementById("background_list").innerHTML = bg_list;
        break;

      case "result.song-details":
        if (json_data.params.status == "ok") {
          let full_song = json_data.params["song-data"];
          document.getElementById("e_title").value = full_song["title"];
          document.getElementById("e_author").value = full_song["author"];
          document.getElementById("e_book").value = full_song["song-book-name"];
          document.getElementById("e_number").value = full_song["song-number"];
          document.getElementById("e_book").value = full_song["song-book-name"];
          document.getElementById("e_copyright").value = full_song["copyright"];
          document.querySelectorAll("input[name=e_remote]").forEach((elt) => {
            elt.checked = false;
          });
          document.querySelector("input[data-lr='" + full_song["remote"] + "']").checked = true;
          lyrics = "";
          for (const part of full_song["parts"]) {
            lyrics += "<" + part["part"].toUpperCase() + ">\n";
            lyrics += part["data"];
          }
          if (lyrics == "") {
            lyrics = "<V1>\n";
          }
          document.getElementById("e_lyrics").value = lyrics;
          document.getElementById("e_order").value = full_song["verse-order"].toUpperCase();
          document.querySelectorAll("input[name=e_key]").forEach((elt) => {
            elt.checked = false;
          });
          t_idx = full_song["transpose-by"];
          document.getElementById("e_transpose").value = (t_idx + 12) % 12; // +12 needed to ensure remainder is in [0, 12)
          if (full_song["song-key"]) {
            document.querySelector("input[data-ek='" + full_song["song-key"] + "']").checked = true;
            e_idx = valid_keys.findIndex((element) => element == full_song["song-key"]);
            t_key = valid_keys[(e_idx + t_idx) % 12];
            document.getElementById("e_transpose_out").value = t_key;
          } else {
            document.getElementById("e_transpose_out").value = "-";
          }
          // Ensure that we are in edit song mode, rather than create song mode
          document.getElementById("popup_edit_mode").innerHTML = "Edit song";
          document.getElementById("popup_edit_song").style.display = "flex";
          editing_song_id = full_song["song-id"];
        }
        break;

      case "response.new-service":
        if (json_data.params.status == "unsaved-service") {
          document.getElementById("popup_new_service").style.display = "flex";
        } else {
          json_toast_response(json_data, "New service started", "Problem starting new service");
        }
        break;

      case "response.load-service":
        if (json_data.params.status == "unsaved-service") {
          document.getElementById("popup_save_before_load_service").style.display = "flex";
        } else {
          json_toast_response(json_data, "Service loaded successfully", "Problem loading service");
        }
        break;

      case "response.export-service":
        json_toast_response(
          json_data,
          "Service exported successfully",
          "Problem exporting service"
        );
        break;

      case "result.song-titles":
        let song_list = "";
        for (const [idx, song] of json_data.params.songs.entries()) {
          if (idx < MAX_LIST_ITEMS) {
            song_list += "<div class='ml_row'>";
            song_list += "<div class='ml_text'>" + song[1] + "</div>";
            song_list += "<a href='#' class='ml_button ml_icon ml_icon_edit' ";
            song_list += "onclick='edit_song(" + song[0] + ");'></a>";
            song_list += "<a href='#' class='ml_button ml_icon ml_icon_plus' ";
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
        document.getElementById("song_list").innerHTML = song_list;
        break;

      case "response.save-service":
        if (json_data.params.status == "unspecified-service") {
          cur_date = new Date();
          date_str = cur_date.toISOString().replace("T", " ").replace(/:/g, "-");
          document.getElementById("f_name").value =
            date_str.substr(0, date_str.length - 5) + ".json";
          document.getElementById("popup_save_service_as").style.display = "flex";
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
        break;

      case "result.all-services":
        files_list = "";
        if (json_data.params.filenames.length != 0) {
          for (const [idx, file] of json_data.params.filenames.entries()) {
            files_list += "<div class='ml_row'>";
            files_list += "<div class='ml_radio_div'>";
            files_list += "<input type='radio' data-role='none' ";
            files_list += "name='files' id='files-" + idx + "' /></div>";
            files_list += "<div class='ml_text'>" + file + "</div>";
            files_list += "</div>";
          }
          document.getElementById("load_files_radio").innerHTML = files_list;
          document.querySelectorAll("#load_files_radio input[type=radio]").forEach((elt) => {
            elt.checked = false;
          });
          document.getElementById("files-0").checked = true;
        } else {
          files_list += "<div class='ml_row'><div class='ml_text'>";
          files_list += "<em>No saved service plans</em></div><div>";
          document.getElementById("load_files_radio").innerHTML = files_list;
        }
        document.getElementById("popup_load_service").style.display = "flex";
        break;

      case "result.bible-versions":
        radios_html = "";
        for (const [idx, version] of json_data.params.versions.entries()) {
          radios_html += '<input type="radio" name="b_version" id="b_version_' + idx;
          radios_html += '" data-bv="' + version + '" data-role="none"/>';
          radios_html += '<label for="b_version_' + idx + '">' + version + "</label>";
        }
        document.getElementById("b_version_radios").innerHTML = radios_html;
        document.querySelector('input[name="b_version"]:first-of-type').checked = true;
        // Attach event listener
        document.querySelectorAll('input[name="b_version"]').forEach((elt) => {
          elt.addEventListener("change", (e) => {
            if (
              document.querySelectorAll("#passage_list input").length > 0 &&
              document.getElementById("bible_search").value.trim() != ""
            ) {
              // A search has already been performed, so repeat the search with the new version
              bible_search();
            }
          });
        });
        break;

      case "result.bible-verses":
        let bible_list = "";
        if (json_data.params.status !== "ok") {
          json_toast_response(json_data, "Bible search success", "Problem performing Bible search");
        }
        for (const [idx, verse] of json_data.params.verses.entries()) {
          if (idx < MAX_VERSE_ITEMS) {
            bible_ref = verse[1] + " " + verse[2] + ":" + verse[3];
            bible_list += "<div class='ml_row ml_expand_row'>";
            bible_list += "<div class='ml_check_div'>";
            bible_list += "<input type='checkbox' data-role='none' checked='checked' ";
            bible_list += "name='v_list' id='v-" + verse[0] + "' /></div>";
            bible_list += "<div class='ml_text ml_multitext'><p class='ml_bibleverse'>";
            bible_list += "<strong>" + bible_ref + "</strong>&nbsp; " + verse[4];
            bible_list += "</p></div>";
            bible_list += "</div>";
          }
        }
        document.getElementById("passage_list").innerHTML = bible_list;
        break;

      case "trigger.play-video":
        video_interval = setInterval(video_tick, 1000);
        break;
      case "trigger.pause-video":
        clearInterval(video_interval);
        break;
      case "trigger.stop-video":
        clearInterval(video_interval);
        video_timer = 0;
        document.getElementById("time_seek").value = video_timer;
        break;
      case "trigger.seek-video":
        video_timer = json_data.params.seconds;
        document.getElementById("time_seek").value = video_timer;
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

      case "response.remove-item":
        json_toast_response(json_data, "Item removed", "Problem removing item");
        break;

      case "response.stop-capture":
        json_toast_response(json_data, "Capturing stopped", "Problem stopping capture");
        break;

      case "response.start-capture":
        json_toast_response(json_data, "Capturing started", "Problem starting capture");
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
      case "response.start-presentation":
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
  document.getElementById("flip_screen_state").addEventListener("change", change_screen_state_flip);

  document.getElementById("song_search").addEventListener("keypress", (e) => {
    key_code = e.which ? e.which : e.keyCode;
    if (key_code == 13) {
      song_search();
    }
  });

  document.querySelector('input[data-lrs="0"]').checked = true;
  document.querySelector('input[data-lrs="1"]').checked = false;
  document.querySelectorAll('input[name="lr_search"]').forEach((elt) => {
    elt.addEventListener("change", song_search);
  });

  document.getElementById("bible_search").addEventListener("keypress", (e) => {
    key_code = e.which ? e.which : e.keyCode;
    if (key_code == 13) {
      bible_search();
    }
  });

  document.getElementById("e_transpose").addEventListener("change", update_transpose_slider);
  document.querySelectorAll('input[name="e_key"]').forEach((elt) => {
    elt.addEventListener("change", update_transpose_slider);
  });

  document.getElementById("t_color").addEventListener("input", (e) => {
    e.target.style.backgroundColor = "#" + e.target.value;
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "font-color",
          value: e.target.value,
        },
      })
    );
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

  document.getElementById("cd_text").addEventListener("input", (e) => {
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

  document.getElementById("d_copyright").addEventListener("change", (e) => {
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

  document.getElementById("d_verseorder").addEventListener("change", (e) => {
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

  document.getElementById("cd_time").value =
    String((new Date().getHours() + 1) % 24).padStart(2, "0") + ":00";

  start_websocket();
});

window.addEventListener("resize", (e) => {
  // Size screen_view div and current_item div based on style
  // Video width = 70% of container div, with padding-bottom set to enforce aspect ratio
  aspect_padding = 70 / aspect_ratio + "%";
  document.getElementById("screen_view").style.paddingBottom = aspect_padding;
  video_height =
    (0.7 * parseInt(getComputedStyle(document.getElementById("item_area")).width, 10)) /
    aspect_ratio;
  document.getElementById("current_item").style.height =
    window.innerHeight - video_height - 16 + "px";
});

document.addEventListener("keydown", (e) => {
  key_code = e.which ? e.which : e.keyCode;
  let tag = e.target.tagName.toLowerCase();
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
