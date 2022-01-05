let websocket;
const MAX_LIST_ITEMS = 50;
const MAX_VERSE_ITEMS = 2500;
const SELECTED_COLOR = "gold";
let service_list;
let service_sort_start;
let clicked_service_item, clicked_song_id;
let clicked_background, clicked_background_w, clicked_background_h;
let action_after_save;
let screen_state;
let icon_dict = {};
let aspect_ratio;
let video_timer = 0;
let video_interval;
let update_slider = true;
let valid_keys = [
  "C",
  "Db",
  "D",
  "Eb",
  "E",
  "F",
  "F#",
  "G",
  "Ab",
  "A",
  "Bb",
  "B",
];

icon_dict["bible"] = "/html/icons/icons8-literature-48.png";
icon_dict["song"] = "/html/icons/icons8-musical-notes-48.png";
icon_dict["presentation"] = "/html/icons/icons8-presentation-48.png";
icon_dict["video"] = "/html/icons/icons8-tv-show-48.png";

toastr_info_options = {
  closeButton: false,
  newestOnTop: true,
  progressBar: false,
  positionClass: "toast-bottom-center",
  preventDuplicates: false,
  showDuration: "300",
  hideDuration: "300",
  timeOut: "1500",
  extendedTimeOut: "300",
  showEasing: "swing",
  hideEasing: "linear",
  showMethod: "fadeIn",
  hideMethod: "fadeOut",
};

toastr_error_options = {
  closeButton: true,
  newestOnTop: true,
  progressBar: false,
  positionClass: "toast-bottom-full-width",
  preventDuplicates: false,
  progressBar: true,
  showDuration: "300",
  hideDuration: "300",
  timeOut: "0",
  extendedTimeOut: "0",
  showEasing: "swing",
  hideEasing: "linear",
  showMethod: "fadeIn",
  hideMethod: "fadeOut",
};

toastr_ws_close_options = {
  closeButton: false,
  newestOnTop: true,
  progressBar: false,
  positionClass: "toast-bottom-full-width",
  preventDuplicates: false,
  showDuration: "300",
  hideDuration: "300",
  timeOut: "2500",
  extendedTimeOut: "300",
  showEasing: "swing",
  hideEasing: "linear",
  showMethod: "fadeIn",
  hideMethod: "fadeOut",
};

function change_screen_state_flip() {
  str_state = $("#flip_screen_state").prop("checked") === true ? "on" : "off";
  websocket.send(
    JSON.stringify({
      action: "command.set-display-state",
      params: { state: str_state },
    })
  );
}

function add_verses() {
  verses = $("input[name=v_list]:checked");
  version = $("#select_b_version").val();
  if (verses.length > 0) {
    let range_start = $(verses[0]).attr("id").substr(2);
    let prev_id = range_start - 1;
    let v_id;
    for (v = 0; v < verses.length; v++) {
      v_id = $(verses[v]).attr("id").substr(2);
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
  $('#passage_list input[type="checkbox"]')
    .prop("checked", true)
    .checkboxradio("refresh");
}

function select_none_verses() {
  $('#passage_list input[type="checkbox"]')
    .prop("checked", false)
    .checkboxradio("refresh");
}

function load_service_preload() {
  websocket.send(
    JSON.stringify({ action: "request.all-services", params: {} })
  );
}

function load_service(force) {
  sel_radio = $("input[name=files]:checked").attr("id");
  sel_text = $("label[for=" + sel_radio + "]").text();
  websocket.send(
    JSON.stringify({
      action: "command.load-service",
      params: { filename: sel_text, force: force },
    })
  );
}

function save_service_as(elt) {
  f_name = $(elt).val();
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
  $(elt).val("");
}

function save_service(action_after) {
  action_after_save = action_after;
  websocket.send(
    JSON.stringify({ action: "command.save-service", params: {} })
  );
}

function delete_item() {
  websocket.send(
    JSON.stringify({
      action: "command.remove-item",
      params: { index: clicked_service_item },
    })
  );
}

function next_item() {
  websocket.send(JSON.stringify({ action: "command.next-item", params: {} }));
}

function previous_item() {
  websocket.send(
    JSON.stringify({ action: "command.previous-item", params: {} })
  );
}

function goto_item() {
  websocket.send(
    JSON.stringify({
      action: "command.goto-item",
      params: { index: clicked_service_item },
    })
  );
}

function next_slide() {
  websocket.send(JSON.stringify({ action: "command.next-slide", params: {} }));
}

function previous_slide() {
  websocket.send(
    JSON.stringify({ action: "command.previous-slide", params: {} })
  );
}

function goto_slide(idx) {
  websocket.send(
    JSON.stringify({ action: "command.goto-slide", params: { index: idx } })
  );
}

function song_search() {
  song_val = $("#song_search")
    .val()
    .replace(/[^0-9a-z ]/gi, "")
    .trim();
  if (song_val !== "") {
    websocket.send(
      JSON.stringify({
        action: "query.song-by-text",
        params: {
          "search-text": song_val,
        },
      })
    );
  } else {
    $("#song_list").html("");
  }
}

function bible_search() {
  if (
    $("input[name=b_search_type]:checked").attr("id") == "b_search_type_ref"
  ) {
    if ($("#bible_search").val().trim() !== "") {
      websocket.send(
        JSON.stringify({
          action: "query.bible-by-ref",
          params: {
            version: $("input[name=b_version]:checked").attr("data-bv"),
            "search-ref": $("#bible_search").val(),
          },
        })
      );
    } else {
      $("#passage_list div").html("");
    }
  } else {
    if ($("#bible_search").val().trim().length > 2) {
      websocket.send(
        JSON.stringify({
          action: "query.bible-by-text",
          params: {
            version: $("input[name=b_version]:checked").attr("data-bv"),
            "search-text": $("#bible_search").val(),
          },
        })
      );
    } else {
      toastr.options = toastr_info_options;
      toastr.warning(
        "Please enter at least three characters to search by text"
      );
    }
  }
}

function new_service(force) {
  websocket.send(
    JSON.stringify({ action: "command.new-service", params: { force: force } })
  );
}

function add_song() {
  websocket.send(
    JSON.stringify({
      action: "command.add-song-item",
      params: { "song-id": clicked_song_id },
    })
  );
}

function edit_song() {
  websocket.send(
    JSON.stringify({
      action: "request.full-song",
      params: { "song-id": clicked_song_id },
    })
  );
}

function refresh_presentations() {
  websocket.send(
    JSON.stringify({ action: "request.all-presentations", params: {} })
  );
}

function refresh_videos() {
  websocket.send(JSON.stringify({ action: "request.all-videos", params: {} }));
}

function refresh_loops() {
  websocket.send(JSON.stringify({ action: "request.all-loops", params: {} }));
}

function refresh_backgrounds() {
  websocket.send(
    JSON.stringify({ action: "request.all-backgrounds", params: {} })
  );
}

function video_tick() {
  video_timer += 1;
  if (update_slider == true) {
    $("#time_seek").val(video_timer).slider("refresh");
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
    $("#cd_time").val().split(":")[0],
    $("#cd_time").val().split(":")[1],
    0
  );
  var cd_length = Math.floor((target.getTime() - now.getTime()) / 1000);
  if (cd_length > 0) {
    websocket.send(
      JSON.stringify({
        action: "command.start-countdown",
        params: {
          hr: $("#cd_time").val().split(":")[0],
          min: $("#cd_time").val().split(":")[1],
        },
      })
    );
  } else {
    toastr.options = toastr_error_options;
    toastr.error("That time is in the past!", "Invalid countdown");
  }
}

function clear_countdown() {
  websocket.send(
    JSON.stringify({ action: "command.clear-countdown", params: {} })
  );
}

function start_presentation() {
  websocket.send(
    JSON.stringify({ action: "command.start-presentation", params: {} })
  );
}

function restore_loop() {
  websocket.send(
    JSON.stringify({ action: "command.restore-loop", params: {} })
  );
}

function create_song() {
  // Empty all fields on popup
  $("#e_title").val("");
  $("#e_author").val("");
  $("#e_book").val("");
  $("#e_number").val("");
  $("#e_book").val("");
  $("#e_copyright").val("");
  $("#e_lyrics").val("<V1>\n");
  $("#e_order").val("");
  $("input[name='e_key']").prop("checked", false).checkboxradio("refresh");
  $("#e_transpose").val(0);
  $("#e_transpose_div a").html("");
  // Switch into create song mode
  $("#edit_song_mode_header").css("display", "none");
  $("#create_song_mode_header").css("display", "block");
  // Display popup
  $("#popup_edit_song").css("width", window.innerWidth * 0.95);
  $("#popup_edit_song").popup("open");
}

function reset_edit_song_form() {
  $("label[for=e_title").css("color", "black");
  $("label[for=e_title").css("font-weight", "normal");
}

function save_song() {
  // Validation: title can't be empty, other validation carried out by server
  if ($("#e_title").val().trim() == "") {
    $("label[for=e_title").css("color", "red");
    $("label[for=e_title").css("font-weight", "bold");
  } else {
    reset_edit_song_form();
    let lyric_text = $("#e_lyrics").val();
    let lyric_lines = lyric_text.split("\n");
    let current_part = "";
    let current_lines = [];
    let parts = []; // parts = [ {part: "v1", lines: [line1, ..., line_n]}, ...]
    for (i in lyric_lines) {
      if (lyric_lines[i][0] == "<") {
        // New part, do we need to close out previous one?
        if (current_lines.length != 0) {
          part_obj = { part: current_part, lines: current_lines };
          parts.push(part_obj);
        }
        // Start new part
        current_part = lyric_lines[i]
          .substr(1, lyric_lines[i].length - 2)
          .toLowerCase();
        current_lines = [];
      } else {
        if (lyric_lines[i] != "") {
          // Skip completely blank lines
          current_lines.push(lyric_lines[i].replace(/\s+$/, "")); // Trim trailing whitespace only
        }
      }
    }
    // Add final part to parts
    if (current_lines.length != 0) {
      part_obj = { part: current_part, lines: current_lines };
      parts.push(part_obj);
    }

    let fields = {
      author: $("#e_author").val(),
      transpose_by: $("#e_transpose").val() % 12,
      lyrics_chords: parts,
      verse_order: $("#e_order").val().toLowerCase(),
      song_book_name: $("#e_book").val(),
      song_number: $("#e_number").val(),
      copyright: $("#e_copyright").val(),
    };
    // Deal with optional field
    if ($("input[name=e_key]:checked").attr("data-ek") != null) {
      fields["song_key"] = $("input[name=e_key]:checked").attr("data-ek");
    }

    if ($("#edit_song_mode_header").css("display") == "block") {
      fields["title"] = $("#e_title").val();
      websocket.send(
        JSON.stringify({
          action: "command.edit-song",
          params: {
            "song-id": clicked_song_id,
            fields: fields,
          },
        })
      );
    } else {
      websocket.send(
        JSON.stringify({
          action: "command.create-song",
          params: {
            title: $("#e_title").val(),
            fields: fields,
          },
        })
      );
    }
    $("#popup_edit_song").popup("close");
  }
}

function add_video(elt) {
  elt_text = $(elt).children().first().html();
  websocket.send(
    JSON.stringify({
      action: "command.add-video",
      params: { url: "./videos/" + elt_text.substr(elt_text.indexOf(">") + 1) },
    })
  );
}

function add_presentation(elt) {
  websocket.send(
    JSON.stringify({
      action: "command.add-presentation",
      params: {
        url: "./presentations/" + $(elt).children().first().html(),
      },
    })
  );
}

function set_loop(elt) {
  elt_text = $(elt).children().first().html();
  websocket.send(
    JSON.stringify({
      action: "command.set-loop",
      params: { url: "./loops/" + elt_text.substr(elt_text.indexOf(">") + 1) },
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
  $("#current_item_icon").attr("src", icon_dict[current_item.type]);
  $("#current_item_name").html(current_item.title);

  // Reset video seek track
  clearInterval(video_interval);
  video_timer = 0;
  $("#time_seek").val(video_timer).slider("refresh");

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
    $("#video_controls").css("display", "block");
    $("#time_seek").prop("max", current_item.duration).slider("refresh");
  } else {
    $("#video_controls").css("display", "none");
  }

  if (current_item.type == "presentation") {
    $("#presentation_controls").css("display", "block");
  } else {
    $("#presentation_controls").css("display", "none");
  }

  let item_list = "";
  for (let slide in current_item.slides) {
    if (current_item.type == "song") {
      slide_lines = current_item.slides[slide].split(/\n/);
      slide_text =
        "<p style='padding-left: 2em; white-space:normal;'><span style='margin-left:-2em; display:block; float:left; width:2em;'><strong>" +
        max_verse_order[slide] +
        "</strong></span>";
      for (line in slide_lines) {
        line_segments = slide_lines[line].split(/\[[\w\+#\/"='' ]*\]/);
        for (let segment = 0; segment < line_segments.length; segment++) {
          slide_text += line_segments[segment];
        }
        slide_text += "<br />";
      }
      slide_text += "</p>";
    } else {
      slide_text =
        "<p style='white-space:normal;'>" + current_item.slides[slide] + "</p>";
    }
    item_list +=
      "<li data-icon='false'><a class='i-item' data-id=" +
      slide +
      " href='#'>" +
      slide_text +
      "</a></li>";
  }
  $("#current_item_list").html(item_list);
  $("#current_item_list").listview("refresh");
  $("#current_item_list a.i-item").on("click", function (event, ui) {
    goto_slide($(this).data("id"));
  });

  // Indicate selection of slide_index
  indicate_current_slide(slide_index);
}

function indicate_current_slide(slide_index) {
  $("#current_item_list li a.i-item").removeClass("selected");
  if (slide_index != -1) {
    $(
      "#current_item_list li:nth-child(" + (slide_index + 1) + ") a.i-item"
    ).addClass("selected");
    item_top = $(
      "#current_item_list li:nth-child(" + (slide_index + 1) + ")"
    ).offset().top;
    item_height = $(
      "#current_item_list li:nth-child(" + (slide_index + 1) + ")"
    ).outerHeight();
    viewable_top = $("#current_item").offset().top;
    list_top = $("#current_item_list").offset().top;
    scroll_top = $("#current_item").scrollTop();
    window_height = $(window).height();
    if (item_top < viewable_top) {
      $("#current_item").scrollTop(item_top - list_top);
    } else if (item_top + item_height > window_height) {
      $("#current_item").scrollTop(
        8 + scroll_top + item_top + item_height - window_height
      );
    }
  }
}

function indicate_current_item(item_index) {
  $("#service_list li a.s-item").css("background-color", "");
  if (item_index != -1) {
    $("#service_list li:nth-child(" + (item_index + 1) + ") a.s-item").css(
      "background-color",
      SELECTED_COLOR
    );
  }
}

function update_style_sliders(style) {
  $("#s_width").val(style["div-width-vw"]).slider("refresh");
  $("#s_font_size").val(style["font-size-vh"]).slider("refresh");
  $("#s_lines").val(style["max-lines"]).slider("refresh");
  $("#s_margin").val(style["margin-top-vh"]).slider("refresh");
  $("input[name='o_style']").prop("checked", false).checkboxradio("refresh");
  $("input[data-ol='" + style["outline-style"] + "']")
    .prop("checked", true)
    .checkboxradio("refresh");
  $("#ch_size").val(style["countdown-h-size-vh"]).slider("refresh");
  $("#cd_text").val(style["countdown-h-text"]);
  $("#cd_size").val(style["countdown-size-vh"]).slider("refresh");
  $("#cd_top").val(style["countdown-top-vh"]).slider("refresh");
  $("#d_copyright")
    .prop("checked", style["display-copyright"])
    .flipswitch("refresh");
  $("#cp_size").val(style["copy-size-vh"]).slider("refresh");
  $("#cp_width").val(style["copy-width-vw"]).slider("refresh");
  $("#d_verseorder")
    .prop("checked", style["display-verseorder"])
    .flipswitch("refresh");
  $("#vo_size").val(style["order-size-vh"]).slider("refresh");
  $("#vo_width").val(style["order-width-vw"]).slider("refresh");
  $("#t_color").val(style["font-color"]);
  // Update background status items
  if (style["song-background-url"] == "none") {
    $("#song_bg_icon").attr("src", "");
  } else {
    $("#song_bg_icon").attr(
      "src",
      "./backgrounds/thumbnails/" + style["song-background-url"].substr(14)
    );
  }
  $("#song_bg").listview("refresh");
  if (style["bible-background-url"] == "none") {
    $("#bible_bg_icon").attr("src", "");
  } else {
    $("#bible_bg_icon").attr(
      "src",
      "./backgrounds/thumbnails/" + style["bible-background-url"].substr(14)
    );
  }
  $("#bible_bg").listview("refresh");
}

function json_toast_response(json_data, success_message, error_message) {
  if (json_data.params.status === "ok") {
    toastr.options = toastr_info_options;
    toastr.success(success_message);
  } else {
    toastr.options = toastr_error_options;
    toastr.error(
      json_data.params.details,
      error_message + " (" + json_data.params.status + ")"
    );
  }
}

function setup_service_list_handlers() {
  $("#service_list a.popup-trigger").on("click", function (event, ui) {
    if ($(this).parent().children().first().data("songid") !== undefined) {
      $("#btn_popup_edit_song").css("display", "inline-block");
      clicked_song_id = parseInt(
        $(this).parent().children().first().data("songid")
      );
    } else {
      $("#btn_popup_edit_song").css("display", "none");
    }
    clicked_service_item = $(this).data("id");
  });
  $("#service_list a.s-item").on("dblclick", function (event, ui) {
    clicked_service_item = $(this).data("id");
    goto_item();
  });
}

function update_transpose_slider() {
  if ($("input[name=e_key]:checked").attr("data-ek") != null) {
    e_val = $("input[name=e_key]:checked").attr("data-ek");
    e_idx = valid_keys.findIndex((element) => element == e_val)
    t_idx = parseInt($("#e_transpose").val(), 10);
    t_key = valid_keys[(e_idx + t_idx) % 12];
    $("#e_transpose_div a").html(t_key);
  }
}

function set_background_songs() {
  websocket.send(
    JSON.stringify({
      action: "command.edit-style-params",
      params: {
        style_params: [
          { param: "song-background-url", value: clicked_background },
          { param: "song-background-w", value: clicked_background_w },
          { param: "song-background-h", value: clicked_background_h },
        ],
      },
    })
  );
}

function set_background_bible() {
  websocket.send(
    JSON.stringify({
      action: "command.edit-style-params",
      params: {
        style_params: [
          { param: "bible-background-url", value: clicked_background },
          { param: "bible-background-w", value: clicked_background_w },
          { param: "bible-background-h", value: clicked_background_h },
        ],
      },
    })
  );
}

function set_background_both() {
  websocket.send(
    JSON.stringify({
      action: "command.edit-style-params",
      params: {
        style_params: [
          { param: "song-background-url", value: clicked_background },
          { param: "song-background-w", value: clicked_background_w },
          { param: "song-background-h", value: clicked_background_h },
          { param: "bible-background-url", value: clicked_background },
          { param: "bible-background-w", value: clicked_background_w },
          { param: "bible-background-h", value: clicked_background_h },
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

function start_websocket() {
  websocket = null;
  websocket = new WebSocket("ws://" + window.location.hostname + ":9001/app");
  websocket.onmessage = function (event) {
    json_data = JSON.parse(event.data);
    console.log(json_data);
    switch (json_data.action) {
      case "update.app-init":
        toastr.options = toastr_info_options;
        toastr.success("Connected to Malachi server");
        screen_state = json_data.params.screen_state;
        if (screen_state === "on") {
          bool_screen_state = true;
        } else {
          bool_screen_state = false;
        }
        $("#flip_screen_state").off();
        $("#flip_screen_state")
          .prop("checked", bool_screen_state)
          .flipswitch("refresh");
        $("#flip_screen_state").on("change", change_screen_state_flip);

        // Size screen_view div and current_item div based on style
        // Video width = 70% of container div, with padding-bottom set to enforce aspect ratio
        aspect_ratio = json_data.params.style["aspect-ratio"];
        aspect_padding = 70 / aspect_ratio + "%";
        $("#screen_view").css("padding-bottom", aspect_padding);
        video_height =
          (0.7 * parseInt($("#item_area").css("width"), 10)) / aspect_ratio;
        header_height = $("#item_header").height();
        $("#current_item").css(
          "height",
          window.innerHeight - video_height - header_height - 16
        );

        // Display style parameters in style tab
        update_style_sliders(json_data.params.style);

        // Populate service plan list
        service_list = "";
        for (let item in json_data.params.items) {
          if (json_data.params.items[item].type == "song") {
            service_list +=
              "<li><a class='s-item' data-id=" +
              item +
              " data-songid=" +
              json_data.params.items[item]["song-id"] +
              " href='#'>";
          } else {
            service_list +=
              "<li><a class='s-item' data-id=" + item + " href='#'>";
          }
          service_list +=
            "<img class='ui-li-icon' src='" +
            icon_dict[json_data.params.items[item].type] +
            "' />";
          service_list += json_data.params.items[item].title + "</a>";
          service_list +=
            "<a class='popup-trigger' href='#popup_service_item_options' data-id=" +
            item +
            " data-rel='popup'></li>";
        }
        $("#service_list").html(service_list);
        $("#service_list").listview("refresh");

        setup_service_list_handlers();
        indicate_current_item(json_data.params.item_index);

        // Populate current item title and list
        if (json_data.params.item_index != -1) {
          current_item = json_data.params.items[json_data.params.item_index];
          display_current_item(current_item, json_data.params.slide_index);
        } else {
          $("#video_controls").css("display", "none");
          $("#presentation_controls").css("display", "none");
          $("#current_item_icon").attr("src", icon_dict["song"]);
          $("#current_item_name").html("No current item");
          $("#current_item_list").html("");
          $("#current_item_list").listview("refresh");
        }

        // Populate Presentation, Video, Background and Loop lists
        websocket.send(
          JSON.stringify({ action: "request.all-presentations", params: {} })
        );
        websocket.send(
          JSON.stringify({ action: "request.all-videos", params: {} })
        );
        websocket.send(
          JSON.stringify({ action: "request.all-loops", params: {} })
        );
        websocket.send(
          JSON.stringify({ action: "request.all-backgrounds", params: {} })
        );

        // Populate Bible version list
        websocket.send(
          JSON.stringify({ action: "request.bible-versions", params: {} })
        );
        break;

      case "update.service-overview-update":
        // Populate service plan list
        service_list = "";
        for (let idx in json_data.params.items) {
          if (json_data.params.types[idx].substr(0, 4) == "song") {
            service_list +=
              "<li><a class='s-item' href='#' data-id=" +
              idx +
              " data-songid=" +
              json_data.params.types[idx].substr(5) +
              ">";
            service_list +=
              "<img class='ui-li-icon' src='" + icon_dict["song"] + "' />";
          } else {
            service_list +=
              "<li><a class='s-item' href='#' data-id=" + idx + ">";
            service_list +=
              "<img class='ui-li-icon' src='" +
              icon_dict[json_data.params.types[idx]] +
              "' />";
          }
          service_list += json_data.params.items[idx] + "</a>";
          service_list +=
            "<a class='popup-trigger' href='#popup_service_item_options' data-id=" +
            idx +
            " data-rel='popup'></li>";
        }
        $("#service_list").html(service_list);
        $("#service_list").listview("refresh");

        setup_service_list_handlers();
        indicate_current_item(json_data.params.item_index);

        // Populate current item list
        if (json_data.params.item_index != -1) {
          current_item = json_data.params.current_item;
          display_current_item(current_item, json_data.params.slide_index);
        } else {
          $("#video_controls").css("display", "none");
          $("#presentation_controls").css("display", "none");
          $("#current_item_icon").attr("src", icon_dict["song"]);
          $("#current_item_name").html("No current item");
          $("#current_item_list").html("");
          $("#current_item_list").listview("refresh");
        }
        break;

      case "update.slide-index-update":
        indicate_current_slide(json_data.params.slide_index);
        break;

      case "update.item-index-update":
        indicate_current_item(json_data.params.item_index);
        display_current_item(
          json_data.params.current_item,
          json_data.params.slide_index
        );
        break;

      case "update.display-state":
        screen_state = json_data.params.state;
        if (screen_state === "on") {
          bool_screen_state = true;
        } else {
          bool_screen_state = false;
        }
        $("#flip_screen_state").off();
        $("#flip_screen_state")
          .prop("checked", bool_screen_state)
          .flipswitch("refresh");
        $("#flip_screen_state").on("change", change_screen_state_flip);
        break;

      case "update.style-update":
        update_style_sliders(json_data.params.style);
        break;

      case "result.all-presentations":
        let pres_list = "";
        for (let url in json_data.params.urls) {
          pres_list +=
            "<li data-icon='plus'><a href='#'>" +
            json_data.params.urls[url].substring(16) +
            "</a>";
          pres_list +=
            "<a onclick='add_presentation($(this).parent());' href='javascript:void(0);'></li>";
        }
        $("#presentation_list").html(pres_list);
        $("#presentation_list").listview("refresh");
        break;

      case "result.all-videos":
        let vid_list = "";
        for (let url in json_data.params.urls) {
          vid_list +=
            "<li data-icon='plus'><a href='#' style='min-height:auto !important;'>";
          vid_list += "<img src='" + json_data.params.urls[url] + ".jpg' />";
          vid_list += "" + json_data.params.urls[url].substring(9) + "</a>";
          vid_list +=
            "<a onclick='add_video($(this).parent());' href='javascript:void(0);'></li>";
        }
        $("#video_list").html(vid_list);
        $("#video_list").listview("refresh");
        break;

      case "result.all-loops":
        let loop_list = "";
        for (let url in json_data.params.urls) {
          short_url = json_data.params.urls[url].substr(8);
          loop_list += "<li><a href='#' style='min-height:auto !important;'>";
          loop_list += "<img src='" + json_data.params.urls[url] + ".jpg' />";
          loop_list += "" + short_url + "</a>";
          loop_list +=
            "<a onclick='set_loop($(this).parent());' href='javascript:void(0);'></li>";
        }
        $("#loop_list").html(loop_list);
        $("#loop_list").listview("refresh");
        break;

      case "result.all-backgrounds":
        let bg_list = "";
        for (let bg in json_data.params.bg_data) {
          short_url = json_data.params.bg_data[bg]["url"].substr(14);
          bg_list += "<li><a href='#' style='min-height:auto !important;'>";
          bg_list += "<img src='./backgrounds/thumbnails/" + short_url + "' />";
          bg_list += "" + short_url + "</a>";
          bg_list +=
            "<a class='popup-trigger' href='#popup_background_options' data-id=" +
            json_data.params.bg_data[bg]["url"] +
            " data-width=" +
            json_data.params.bg_data[bg]["width"] +
            " data-height=" +
            json_data.params.bg_data[bg]["height"] +
            " data-rel='popup'></li>";
        }
        $("#background_list").html(bg_list);
        $("#background_list").listview("refresh");
        $("#background_list a.popup-trigger").on("click", function (event, ui) {
          clicked_background = $(this).data("id");
          clicked_background_w = $(this).data("width");
          clicked_background_h = $(this).data("height");
        });
        break;

      case "result.song-details":
        if (json_data.params.status == "ok") {
          let full_song = json_data.params["song-data"];
          $("#e_title").val(full_song["title"]);
          $("#e_author").val(full_song["author"]);
          $("#e_book").val(full_song["song-book-name"]);
          $("#e_number").val(full_song["song-number"]);
          $("#e_book").val(full_song["song-book-name"]);
          $("#e_copyright").val(full_song["copyright"]);
          lyrics = "";
          for (i in full_song["parts"]) {
            lyrics += "<" + full_song["parts"][i]["part"].toUpperCase() + ">\n";
            lyrics += full_song["parts"][i]["data"];
          }
          if (lyrics == "") {
            lyrics = "<V1>\n";
          }
          $("#e_lyrics").val(lyrics);
          $("#e_order").val(full_song["verse-order"].toUpperCase());
          $("input[name='e_key']").prop("checked", false).checkboxradio("refresh");
          $("input[data-ek='" + full_song["song-key"] + "']")
            .prop("checked", true)
            .checkboxradio("refresh");
          t_idx = full_song["transpose-by"];
          $("#e_transpose")
            .val((t_idx + 12) % 12)
            .slider("refresh"); // +12 needed to ensure remainder is in [0, 12)
          if ($("input[name=e_key]:checked").attr("data-ek") != null) {
            e_idx = valid_keys.findIndex((element) => element == full_song["song-key"])
            t_key = valid_keys[(e_idx + t_idx) % 12];
            $("#e_transpose_div a").html(t_key);
          }
          // Ensure that we are in edit song mode, rather than create song mode
          $("#edit_song_mode_header").css("display", "block");
          $("#create_song_mode_header").css("display", "none");
          $("#popup_edit_song").css("width", window.innerWidth * 0.95);
          $("#popup_edit_song").popup("open");
        }
        break;

      case "response.new-service":
        if (json_data.params.status == "unsaved-service") {
          $("#popup_new_service").popup("open");
        } else {
          json_toast_response(
            json_data,
            "New service started",
            "Problem starting new service"
          );
        }
        break;

      case "response.load-service":
        if (json_data.params.status == "unsaved-service") {
          $("#popup_save_before_load_service").popup("open");
        } else {
          json_toast_response(
            json_data,
            "Service loaded successfully",
            "Problem loading service"
          );
        }
        break;

      case "result.song-titles":
        let song_list = "";
        for (let song in json_data.params.songs) {
          if (song == MAX_LIST_ITEMS) {
            song_list += "<li>There are more items...</li>";
            break;
          }
          song_list +=
            "<li><a href='#'>" + json_data.params.songs[song][1] + "</a>";
          song_list +=
            "<a class='popup-trigger' href='#popup_song_item_options' data-id=" +
            json_data.params.songs[song][0] +
            " data-rel='popup'></li>";
        }
        $("#song_list").html(song_list);
        $("#song_list").listview("refresh");
        $("#song_list a.popup-trigger").on("click", function (event, ui) {
          clicked_song_id = $(this).data("id");
        });
        break;

      case "response.save-service":
        if (json_data.params.status == "unspecified-service") {
          cur_date = new Date();
          date_str = cur_date
            .toISOString()
            .replace("T", " ")
            .replace(/:/g, "-");
          $("#f_name").val(date_str.substr(0, date_str.length - 5) + ".json");
          $("#popup_save_service_as").popup("open");
        } else {
          // Save has been successful
          json_toast_response(
            json_data,
            "Service saved",
            "Problem saving service"
          );
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
        $("#load_files_radio div").html("");
        if (json_data.params.filenames.length != 0) {
          for (let file in json_data.params.filenames) {
            $("#load_files_radio div").append(
              '<input type="radio" name="files" id="files-' + file + '">'
            );
            $("#load_files_radio div").append(
              '<label for="files-' +
                file +
                '">' +
                json_data.params.filenames[file] +
                "</label>"
            );
          }
          $('#load_files_radio input[type="radio"]').checkboxradio();
          $("#files-0").prop("checked", true).checkboxradio("refresh"); // Select item 0
          $("#popup_btn_load_service").removeClass("ui-state-disabled");
        } else {
          $("#load_files_radio div").append(
            "<p><em>No saved service plans</em></p>"
          );
          $("#popup_btn_load_service").addClass("ui-state-disabled");
        }
        $("#load_files_radio").controlgroup("refresh");
        $("#popup_load_service").popup("open");
        break;

      case "result.bible-versions":
        $("#b_version_radios div").html("");
        json_data.params.versions.forEach(function (value, i) {
          $("#b_version_radios div").append(
            '<input type="radio" name="b_version" id="b_version_' +
              i +
              '" data-bv="' +
              value +
              '" />'
          );
          $("#b_version_radios div").append(
            '<label for="b_version_' + i + '">' + value + "</label>"
          );
        });
        $("input[name='b_version']").checkboxradio();
        $("input[name='b_version']:first").prop("checked", true).checkboxradio("refresh");
        $("#b_version_radios").controlgroup("refresh");
        // Attach event listener
        $("input[name='b_version']").on("change", function (event, ui) {
          if (
            $("#passage_list input").length > 0 &&
            $("#bible_search").val().trim() != ""
          ) {
            // A search has already been performed, so repeat the search with the new version
            bible_search();
          }
        });
        break;

      case "result.bible-verses":
        $("#passage_list div").html("");
        if (json_data.params.status !== "ok") {
          toastr.options = toastr_error_options;
          toastr.error(
            json_data.params.details,
            "Problem performing Bible search (" + json_data.params.status + ")"
          );
        }
        for (let v in json_data.params.verses) {
          if (v == MAX_VERSE_ITEMS) {
            break;
          }
          verse = json_data.params.verses[v];
          bible_ref = verse[1] + " " + verse[2] + ":" + verse[3];
          $("#passage_list div").append(
            '<input type="checkbox" data-mini="true" checked="checked" name="v_list" id="v-' +
              verse[0] +
              '">'
          );
          $("#passage_list div").append(
            '<label for="v-' +
              verse[0] +
              '">' +
              bible_ref +
              ": " +
              verse[4] +
              "</label>"
          );
        }

        $('#passage_list input[type="checkbox"]').checkboxradio();
        $("#passage_list").controlgroup("refresh");
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
        $("#time_seek").val(video_timer).slider("refresh");
        break;
      case "trigger.seek-video":
        video_timer = json_data.params.seconds;
        $("#time_seek").val(video_timer).slider("refresh");
        break;

      case "response.add-video":
        json_toast_response(
          json_data,
          "Video added to service",
          "Problem adding video"
        );
        break;

      case "response.add-song-item":
        json_toast_response(
          json_data,
          "Song added to service",
          "Problem adding song"
        );
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
        json_toast_response(
          json_data,
          "Video loop set",
          "Problem setting video loop"
        );
        break;

      case "response.clear-loop":
        json_toast_response(
          json_data,
          "Video loop cancelled",
          "Problem cancelling video loop"
        );
        break;

      case "response.add-bible-item":
        json_toast_response(
          json_data,
          "Bible passage added to service",
          "Problem adding Bible passage"
        );
        break;

      case "response.change-bible-version":
        json_toast_response(
          json_data,
          "Bible version changed",
          "Problem changing Bible version"
        );
        break;

      case "response.remove-item":
        json_toast_response(json_data, "Item removed", "Problem removing item");
        break;

      case "response.stop-capture":
        json_toast_response(
          json_data,
          "Capturing stopped",
          "Problem stopping capture"
        );
        break;

      case "response.start-capture":
        json_toast_response(
          json_data,
          "Capturing started",
          "Problem starting capture"
        );
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
        break; // No action required;
      default:
        console.error("Unsupported event", json_data);
    }
  };
  websocket.onclose = function (event) {
    if (event.wasClean == false) {
      toastr.options = toastr_ws_close_options;
      toastr.error(
        "Reconnection attempt will be made in 5 seconds",
        "Connection was closed/refused by server"
      );
      setTimeout(start_websocket, 5000);
    }
  };
}

$(document).ready(function () {
  $("#elements_area").tabs();
  $(".ui-tabs-anchor").keydown(function (event) {
    key_code = event.which ? event.which : event.keyCode;
    var e = $.Event("keydown");
    e.which = key_code;
    $("body").trigger(e);
    return false;
  });
  $("#service_list").sortable();
  $("#service_list").on("sortstart", function (event, ui) {
    service_sort_start = ui.item.index();
  });
  $("#service_list").on("sortupdate", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.move-item",
        params: {
          "from-index": service_sort_start,
          "to-index": ui.item.index(),
        },
      })
    );
  });

  $("#song_search_div .ui-input-clear").on("click", function (e) {
    song_search();
  });

  $("#bible_search_div .ui-input-clear").on("click", function (e) {
    bible_search();
  });
  $("#bible_search").on("keypress", function (e) {
    key_code = e.which ? e.which : e.keyCode;
    if (key_code == 13) {
      bible_search();
    }
  });

  $("#e_transpose").on("change", update_transpose_slider);
  $("input[name='e_key']").on("change", update_transpose_slider);

  $("#time_seek").parent().find("a").css("display", "none");

  $("#s_width").on("slidestop", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "div-width-vw",
          value: $("#s_width").val(),
        },
      })
    );
  });

  $("#s_font_size").on("slidestop", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "font-size-vh",
          value: $("#s_font_size").val(),
        },
      })
    );
  });

  $("#s_lines").on("slidestop", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "max-lines",
          value: $("#s_lines").val(),
        },
      })
    );
  });

  $("#s_margin").on("slidestop", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "margin-top-vh",
          value: $("#s_margin").val(),
        },
      })
    );
  });

  $("#t_color").on("change", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "font-color",
          value: $("#t_color").val(),
        },
      })
    );
  });

  $("input[name='o_style']").on("change", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "outline-style",
          value: $(this).attr("data-ol"),
        },
      })
    );
  });

  $("#ch_size").on("slidestop", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "countdown-h-size-vh",
          value: $("#ch_size").val(),
        },
      })
    );
  });

  $("#cd_text").on("input", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "countdown-h-text",
          value: $("#cd_text").val(),
        },
      })
    );
  });

  $("#cd_size").on("slidestop", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "countdown-size-vh",
          value: $("#cd_size").val(),
        },
      })
    );
  });

  $("#cd_top").on("slidestop", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "countdown-top-vh",
          value: $("#cd_top").val(),
        },
      })
    );
  });

  $("#d_copyright").on("change", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "display-copyright",
          value: $("#d_copyright").prop("checked"),
        },
      })
    );
  });

  $("#cp_size").on("slidestop", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "copy-size-vh",
          value: $("#cp_size").val(),
        },
      })
    );
  });

  $("#cp_width").on("slidestop", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "copy-width-vw",
          value: $("#cp_width").val(),
        },
      })
    );
  });

  $("#d_verseorder").on("change", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "display-verseorder",
          value: $("#d_verseorder").prop("checked"),
        },
      })
    );
  });

  $("#vo_size").on("slidestop", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "order-size-vh",
          value: $("#vo_size").val(),
        },
      })
    );
  });

  $("#vo_width").on("slidestop", function (event, ui) {
    websocket.send(
      JSON.stringify({
        action: "command.edit-style-param",
        params: {
          param: "order-width-vw",
          value: $("#vo_width").val(),
        },
      })
    );
  });

  document
    .getElementById("cd_time")
    .setAttribute(
      "value",
      new Date().getHours() + ":" + new Date().getMinutes()
    );

  start_websocket();
});

$(window).resize(function () {
  // Size screen_view div and current_item div based on style
  // Video width = 70% of container div, with padding-bottom set to enforce aspect ratio
  aspect_padding = 70 / aspect_ratio + "%";
  $("#screen_view").css("padding-bottom", aspect_padding);
  video_height =
    (0.7 * parseInt($("#item_area").css("width"), 10)) / aspect_ratio;
  $("#current_item").css("height", window.innerHeight - video_height - 16);
});

$(document).on("keydown", function (e) {
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
        $("#elements_area").tabs("option", "active", 0);
        break;
      case 50: // 2 - Song element
        $("#elements_area").tabs("option", "active", 1);
        $("#song_search").focus();
        break;
      case 51: // 3 - Bible element
        $("#elements_area").tabs("option", "active", 2);
        $("#bible_search").focus();
        break;
      case 52: // 4 - Video element
        $("#elements_area").tabs("option", "active", 3);
        break;
      case 53: // 5 - Styling control
        $("#elements_area").tabs("option", "active", 4);
        break;
    }
  }
});
