let websocket;
let current_item;
let current_audio = "";
let current_parallel = false;
let loop_width = 0;
let loop_height = 0;
let loop_ar = 0;
let display_copyright = false;
let display_verseorder = false;
let song_background = { url: "none", width: 1, height: 1 };
let bible_background = { url: "none", width: 1, height: 1 };
let countdown_to = new Date();
let countdown_timer; // Interval reference
let notices_count = 0;
let notices_end_gap = 1;
let notices_cycle_gap = 1;
let notices_slide_time = 1;
let screen_state = false;
let video_displayed = false;
let video_muted = false;
let play_videos = true;
const LINE_SEGMENT_REGEX = /\[[\w\+\¬#|\/"='' ]*\]/;

const DOM_dict = {};
function DOM_get(key) {
  if (!(key in DOM_dict)) {
    DOM_dict[key] = document.getElementById(key);
  }
  return DOM_dict[key];
}

function display_current_slide(slide_index) {
  const current_slide = current_item.slides[slide_index];
  stop_running_video();
  let slide_text = "";
  let verseorder = "";
  let pl_left_text = "";
  let pl_right_text = "";
  current_parallel = false;
  if (current_item.type == "song") {
    let slide_lines = current_slide.split(/\n/);
    verseorder = "<p>";
    slide_text = "<p>";
    for (const line of slide_lines) {
      for (const segment of line.split(LINE_SEGMENT_REGEX)) {
        slide_text += segment;
      }
      slide_text += "<br />";
    }
    slide_text += "</p>";

    const verse_list = current_item["verse-order"].split(" ");
    let part_counts_sum = 0;
    for (const [idx, verse] of verse_list.entries()) {
      if (
        slide_index >= part_counts_sum &&
        slide_index < part_counts_sum + current_item["part-counts"][idx]
      ) {
        verseorder += "<span class='selected'>" + verse.toUpperCase() + "</span>";
      } else {
        verseorder += "<span>" + verse.toUpperCase() + "</span>";
      }
      part_counts_sum += current_item["part-counts"][idx];
    }
    verseorder += "</p>";
  } else if (current_item.type == "bible") {
    if (current_item.parallel_version == "") {
      slide_text = "<p>" + current_slide + "</p>";
      current_parallel = false;
    } else {
      pl_left_text = "<p>" + current_slide + "</p>";
      pl_right_text = "<p>" + current_item.parallel_slides[slide_index] + "</p>";
      current_parallel = true;
    }
    verseorder = "<p></p>";
  } else if (current_item.type == "presentation") {
    slide_text = "";
    verseorder = "<p></p>";
  } else if (current_item.type == "video") {
    slide_text = "";
    verseorder = "<p></p>";
    // Background load video, wait for trigger to display and start playback
    resize_video_item();
    if (play_videos) {
      DOM_get("video_item_src").setAttribute("src", current_item.url);
      DOM_get("video_item").load();
    } else {
      DOM_get("video_item").setAttribute("src", current_item.url + "_still.jpg");
    }
  } else {
    slide_text = "<p>" + current_slide + "</p>";
    verseorder = "<p></p>";
  }
  DOM_get("slide_area").innerHTML = slide_text;
  DOM_get("pl_left").innerHTML = pl_left_text;
  DOM_get("pl_right").innerHTML = pl_right_text;
  DOM_get("verseorder_area").innerHTML = verseorder;
  if (current_item.copyright) {
    DOM_get("copyright_area").innerHTML = "<p>" + current_item.copyright + "</p>";
  } else {
    DOM_get("copyright_area").innerHTML = "";
  }
  update_optional_areas();
}

function clear_current_slide() {
  stop_running_video();
  DOM_get("slide_area").innerHTML = "";
  DOM_get("pl_left").innerHTML = "";
  DOM_get("pl_right").innerHTML = "";
}

function update_optional_areas() {
  if (display_copyright && screen_state) {
    DOM_get("copyright_area").style.display = "block";
  } else {
    DOM_get("copyright_area").style.display = "none";
  }
  if (display_verseorder && screen_state) {
    DOM_get("verseorder_area").style.display = "block";
  } else {
    DOM_get("verseorder_area").style.display = "none";
  }
}

function load_notices(num_slides) {
  let notice_html = "";
  let query_suffix = Date.now();
  for (let slide = 0; slide < num_slides; slide++) {
    notice_html +=
      "<img id='notice_" +
      slide +
      "' class='notice' src='/notices/notices-" +
      slide +
      ".png?q=" +
      query_suffix +
      "' />";
  }
  notices_count = num_slides;
  DOM_get("notices_area").innerHTML = notice_html;
}

function stop_running_video() {
  video_displayed = false;
  if (play_videos) {
    DOM_get("loop_video").play();
    DOM_get("video_item").pause();
  }
  DOM_get("loop_video").style.display = "block";
  DOM_get("video_item").style.display = "none";
}

function resize_video_item() {
  const video_ar = current_item.video_width / current_item.video_height;
  const screen_ar = window.innerWidth / window.innerHeight;
  if (video_ar <= screen_ar) {
    const left_pos = window.innerWidth * 0.5 * (1 - video_ar / screen_ar);
    DOM_get("video_item").style.height = "100%";
    DOM_get("video_item").style.width = "auto";
    DOM_get("video_item").style.top = 0;
    DOM_get("video_item").style.left = left_pos + "px";
  } else {
    const top_pos = window.innerHeight * 0.5 * (1 - screen_ar / video_ar);
    DOM_get("video_item").style.height = "auto";
    DOM_get("video_item").style.width = "100%";
    DOM_get("video_item").style.top = top_pos + "px";
    DOM_get("video_item").style.left = 0;
  }
}

function resize_loop() {
  if (loop_height > 0) {
    const screen_ar = window.innerWidth / window.innerHeight;
    if (screen_ar <= loop_ar) {
      const left_pos = window.innerWidth * -0.5 * (loop_ar / screen_ar - 1);
      DOM_get("loop_video").style.height = "100%";
      DOM_get("loop_video").style.width = "auto";
      DOM_get("loop_video").style.top = 0;
      DOM_get("loop_video").style.left = left_pos + "px";
    } else {
      const top_pos = window.innerHeight * -0.5 * (screen_ar / loop_ar - 1);
      DOM_get("loop_video").style.height = "auto";
      DOM_get("loop_video").style.width = "100%";
      DOM_get("loop_video").style.top = top_pos + "px";
      DOM_get("loop_video").style.left = 0;
    }
  }
}

function update_from_style(style) {
  const div_width = style["div-width-vw"];
  const col_width = style["pl-width-vw"];
  DOM_get("slide_area").style.width = div_width + "vw";
  DOM_get("pl_left").style.width = col_width + "vw";
  DOM_get("pl_right").style.width = col_width + "vw";
  DOM_get("slide_area").style.marginLeft = (100 - div_width) / 2 + "vw";
  DOM_get("pl_left").style.marginLeft = (50 - col_width) / 2 + "vw";
  DOM_get("pl_right").style.marginLeft = 50 + (50 - col_width) / 2 + "vw";
  DOM_get("slide_area").style.marginTop = style["margin-top-vh"] + "vh";
  DOM_get("pl_columns").style.marginTop = style["margin-top-vh"] + "vh";
  DOM_get("slide_area").style.fontSize = style["font-size-vh"] + "vh";
  DOM_get("pl_columns").style.fontSize = style["pl-font-size-vh"] + "vh";
  DOM_get("slide_area").style.color = "#" + style["font-color"];
  if (style["outline-style"] == "drop-shadow") {
    DOM_get("slide_area").classList.remove("outline");
    DOM_get("slide_area").classList.add("drop_shadow");
    DOM_get("pl_columns").classList.remove("outline");
    DOM_get("pl_columns").classList.add("drop_shadow");
  } else if (style["outline-style"] == "text-outline") {
    DOM_get("slide_area").classList.add("outline");
    DOM_get("slide_area").classList.remove("drop_shadow");
    DOM_get("pl_columns").classList.add("outline");
    DOM_get("pl_columns").classList.remove("drop_shadow");
  } else {
    DOM_get("slide_area").classList.remove("outline");
    DOM_get("slide_area").classList.remove("drop_shadow");
    DOM_get("pl_columns").classList.add("outline");
    DOM_get("pl_columns").classList.remove("drop_shadow");
  }
  DOM_get("countdown_p").style.fontSize = style["countdown-size-vh"] + "vh";
  DOM_get("countdown_h").style.fontSize = style["countdown-h-size-vh"] + "vh";
  DOM_get("countdown_h").firstChild.textContent = style["countdown-h-text"];
  DOM_get("countdown_area").style.marginTop = style["countdown-top-vh"] + "vh";
  display_copyright = style["display-copyright"];
  display_verseorder = style["display-verseorder"];
  DOM_get("copyright_area").style.fontSize = parseInt(style["copy-size-vh"]) / 10 + "vh";
  DOM_get("copyright_area").style.width = style["copy-width-vw"] + "vw";
  DOM_get("verseorder_area").style.fontSize = parseInt(style["order-size-vh"]) / 10 + "vh";
  DOM_get("verseorder_area").style.width = style["order-width-vw"] + "vw";
  update_optional_areas();
  song_background.url = style["song-background-url"];
  song_background.width = style["song-background-w"];
  song_background.height = style["song-background-h"];
  bible_background.url = style["bible-background-url"];
  bible_background.width = style["bible-background-w"];
  bible_background.height = style["bible-background-h"];
  update_background();
  notices_end_gap = parseInt(style["notices-end-gap"]);
  notices_cycle_gap = parseInt(style["notices-cycle-gap"]);
  notices_slide_time = parseInt(style["notices-slide-time"]);
}

function update_background() {
  let bg_url, bg_w, bg_h;
  if (current_item == null) {
    bg_url = song_background.url;
    bg_w = song_background.width;
    bg_h = song_background.height;
  } else if (current_item.type == "bible") {
    bg_url = bible_background.url;
    bg_w = bible_background.width;
    bg_h = bible_background.height;
  } else {
    bg_url = song_background.url;
    bg_w = song_background.width;
    bg_h = song_background.height;
  }
  // Only update background if it has changed since last checked
  if (bg_url == "none") {
    DOM_get("bg_image").setAttribute("src", "");
  } else {
    DOM_get("bg_image").setAttribute("src", bg_url);
  }
  const image_ar = bg_w / bg_h;
  const screen_ar = window.innerWidth / window.innerHeight;
  if (image_ar >= screen_ar) {
    const left_pos = window.innerWidth * 0.5 * (1 - image_ar / screen_ar);
    DOM_get("bg_image").style.height = "100%";
    DOM_get("bg_image").style.width = "auto";
    DOM_get("bg_image").style.top = 0;
    DOM_get("bg_image").style.left = left_pos + "px";
  } else {
    const top_pos = window.innerHeight * 0.5 * (1 - screen_ar / image_ar);
    DOM_get("bg_image").style.height = "auto";
    DOM_get("bg_image").style.width = "100%";
    DOM_get("bg_image").style.top = top_pos + "px";
    DOM_get("bg_image").style.left = 0;
  }
}

function decrease_countdown() {
  let countdown_left = Math.floor((countdown_to.getTime() - new Date().getTime()) / 1000);
  if (countdown_left >= 0) {
    DOM_get("countdown_p").firstChild.textContent = format_time(countdown_left);
  } else {
    clearInterval(countdown_timer);
    DOM_get("countdown_area").style.display = "none";
    DOM_get("notices_area")
      .getAnimations({ subtree: true })
      .forEach((animation) => animation.cancel());
  }
}

function stop_countdown() {
  DOM_get("countdown_area").style.display = "none";
  countdown_to = new Date(); // Interval, if running, will stop on next call to decrease_countdown
  DOM_get("notices_area")
    .getAnimations({ subtree: true })
    .forEach((animation) => animation.cancel());
}

function format_time(time_secs) {
  let mins = Math.floor(time_secs / 60);
  let secs = time_secs % 60;
  let full_time = mins + ":" + String(secs).padStart(2, 0);
  return full_time;
}

function update_display_init(json_data) {
  if (json_data.params["video_loop"] !== "") {
    if (play_videos) {
      DOM_get("loop_video_src").setAttribute("src", json_data.params["video_loop"]);
      DOM_get("loop_video").load();
    } else {
      document
        .getElementById("loop_video")
        .setAttribute("src", json_data.params["video_loop"] + "_still.jpg");
    }
    loop_height = json_data.params["loop-height"];
    loop_width = json_data.params["loop-width"];
    loop_ar = loop_width / loop_height;
    resize_loop();
    if (play_videos) {
      DOM_get("loop_video").play();
    }
  } else {
    if (play_videos) {
      DOM_get("loop_video_src").setAttribute("src", "/html/black-frame.mp4");
      DOM_get("loop_video").load();
    } else {
      DOM_get("loop_video").setAttribute("src", "/html/black-frame.jpg");
    }
    loop_height = 0;
    loop_width = 0;
    loop_ar = 0;
  }
  update_from_style(json_data.params.style);
  current_item = json_data.params.current_item;
  if (json_data.params.item_index != -1) {
    display_current_slide(json_data.params.slide_index);
  }
  if (json_data.params.screen_state == "on") {
    screen_state = true;
    DOM_get("slide_area").style.display = "block";
    DOM_get("pl_columns").style.display = "block";
  } else {
    screen_state = false;
    DOM_get("slide_area").style.display = "none";
    DOM_get("pl_columns").style.display = "none";
  }
  update_optional_areas();
  load_notices(json_data.params["notices-count"]);
}

function update_item_index_update(json_data) {
  if (screen_state) {
    stop_countdown();
  }
  current_item = json_data.params.current_item;
  update_background();
  if (json_data.params.item_index != -1) {
    display_current_slide(json_data.params.slide_index);
  } else {
    clear_current_slide();
  }
}

function update_slide_index_update(json_data) {
  stop_countdown();
  display_current_slide(json_data.params.slide_index);
}

function update_display_state(json_data) {
  if (json_data.params.state == "on") {
    screen_state = true;
    stop_countdown();
    DOM_get("slide_area").style.display = "block";
    DOM_get("pl_columns").style.display = "block";
  } else {
    screen_state = false;
    DOM_get("slide_area").style.display = "none";
    DOM_get("pl_columns").style.display = "none";
  }
  update_optional_areas();
}

function update_video_loop(json_data) {
  if (json_data.params.url !== "") {
    if (play_videos) {
      DOM_get("loop_video_src").setAttribute("src", json_data.params.url);
      DOM_get("loop_video").load();
    } else {
      document
        .getElementById("loop_video")
        .setAttribute("src", json_data.params.url + "_still.jpg");
    }
    loop_height = json_data.params["loop-height"];
    loop_width = json_data.params["loop-width"];
    loop_ar = loop_width / loop_height;
    resize_loop();
    if (play_videos) {
      DOM_get("loop_video").play();
    }
  } else {
    if (play_videos) {
      DOM_get("loop_video_src").setAttribute("src", "/html/black-frame.mp4");
      DOM_get("loop_video").load();
    } else {
      DOM_get("loop_video").setAttribute("src", "/html/black-frame.jpg");
    }
    loop_height = 0;
    loop_width = 0;
    loop_ar = 0;
  }
}

function trigger_suspend_loop() {
  DOM_get("loop_video").style.display = "none";
  if (play_videos) {
    DOM_get("loop_video").pause();
  }
}

function trigger_restore_loop() {
  DOM_get("loop_video").style.display = "block";
  if (play_videos) {
    DOM_get("loop_video").play();
  }
}

function trigger_play_video() {
  stop_countdown();
  DOM_get("video_item").style.display = "block";
  DOM_get("loop_video").style.display = "none";
  if (play_videos) {
    DOM_get("loop_video").pause();
    DOM_get("video_item").play();
  }
  video_displayed = true;
}

function trigger_pause_video() {
  if (play_videos) {
    DOM_get("video_item").pause();
  }
}

function trigger_stop_video() {
  video_displayed = false;
  stop_running_video();
  if (play_videos) {
    DOM_get("video_item").currentTime = 0.0;
  }
}

function trigger_seek_video(json_data) {
  if (play_videos) {
    DOM_get("video_item").currentTime = json_data.params.seconds;
  }
}

function trigger_play_audio() {
  if (!video_muted && current_item) {
    if (current_item.audio != current_audio) {
      DOM_get("audio_item_src").src = "/audio/" + current_item.audio;
      DOM_get("audio_item").load();
      current_audio = current_item.audio;
    }
    DOM_get("audio_item").play();
  }
}

function trigger_pause_audio() {
  if (!video_muted) {
    DOM_get("audio_item").pause();
  }
}

function trigger_stop_audio() {
  if (!video_muted) {
    DOM_get("audio_item").pause();
    current_audio = "";
  }
}

function trigger_start_countdown(json_data) {
  if (!screen_state && !video_displayed) {
    const now = new Date();
    countdown_to = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
      json_data.params.hr,
      json_data.params.min,
      0
    );
    const countdown_left = Math.floor((countdown_to.getTime() - now.getTime()) / 1000);
    if (countdown_left > 0) {
      DOM_get("countdown_area").style.display = "block";
      DOM_get("countdown_p").firstChild.textContent = format_time(countdown_left);
      clearInterval(countdown_timer);
      countdown_timer = setInterval(decrease_countdown, 1000);
    }
    if (json_data.params.notices) {
      trigger_start_notices(
        notices_count,
        notices_slide_time,
        notices_cycle_gap,
        notices_end_gap,
        countdown_left
      );
    }
  }
}

function trigger_start_notices(num_slides, slide_time, cycle_gap, end_gap, total_time) {
  let cycle_time = num_slides * slide_time + cycle_gap;
  let active_time = total_time - end_gap;
  // Calculate start time of first (probably incomplete) cycle - cycle begins with "cycle gap"
  let initial_time = active_time - cycle_time * Math.ceil(active_time / cycle_time);
  let initial_slide;
  if (Math.abs(initial_time) < cycle_gap) {
    initial_slide = -1; // We are starting with "cycle gap"
  } else {
    initial_slide = Math.floor(Math.abs(initial_time + cycle_gap) / slide_time);
  }
  all_time_keyframes = [];
  all_opacity_values = [];
  for (let slide = 0; slide < num_slides; slide++) {
    time_kfs = [];
    opacity_vs = [];
    // Determine how long this slide is displayed for
    slide_duration = slide + 1 == num_slides ? slide_time : slide_time * 1.5;
    // Determine first time index that this slide is visible
    first_time = initial_time + cycle_gap + slide * slide_time;
    if (first_time <= -1 * slide_time) {
      first_time += cycle_time;
    }
    // Populate keyframes and values
    if (slide != initial_slide) {
      time_kfs.push(0);
      opacity_vs.push(0);
    }
    cur_time = first_time;
    while (cur_time < active_time) {
      // Slide on
      time_kfs.push(cur_time / total_time);
      opacity_vs.push(1);
      // Slide off
      time_kfs.push((cur_time + slide_duration) / total_time);
      opacity_vs.push(0);
      // Advance to next instance
      cur_time += cycle_time;
    }
    all_time_keyframes.push(time_kfs);
    all_opacity_values.push(opacity_vs);
  }
  // Adjust timings for first slide
  if (initial_slide != -1) {
    if (Math.abs(all_time_keyframes[initial_slide][0]) < (0.5 * slide_time) / total_time) {
      // Initial slide too short; don't display, and lengthen slide two instead
      all_opacity_values[initial_slide][0] = 0;
      if (initial_slide < num_slides - 1) {
        all_opacity_values[(initial_slide + 1) % num_slides][0] = 1;
      }
    }
    all_time_keyframes[initial_slide][0] = 0;
  }
  // Initiate animation - first clear any running animation
  DOM_get("notices_area")
    .getAnimations({ subtree: true })
    .forEach((animation) => animation.cancel());
  for (let slide = num_slides - 1; slide >= 0; slide--) {
    document.getElementById("notice_" + slide).animate(
      {
        opacity: all_opacity_values[slide],
        offset: all_time_keyframes[slide],
        easing: ["step-end"],
      },
      { duration: total_time * 1000, iterations: 1 }
    );
  }
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
      case "update.style-update":
        update_from_style(json_data.params.style);
        break;
      case "update.service-overview-update":
      case "update.item-index-update":
        update_item_index_update(json_data);
        break;
      case "update.slide-index-update":
        update_slide_index_update(json_data);
        break;
      case "update.display-state":
        update_display_state(json_data);
        break;
      case "update.video-loop":
        update_video_loop(json_data);
        break;
      case "update.notices-loaded":
        load_notices(json_data.params["slide-count"]);
        break;
      case "trigger.suspend-loop":
        trigger_suspend_loop();
        break;
      case "trigger.restore-loop":
        trigger_restore_loop();
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
      case "trigger.play-audio":
        trigger_play_audio();
        break;
      case "trigger.pause-audio":
        trigger_pause_audio();
        break;
      case "trigger.stop-audio":
        trigger_stop_audio();
        break;
      case "trigger.start-countdown":
        trigger_start_countdown(json_data);
        break;
      case "trigger.clear-countdown":
        stop_countdown();
        break;
      default:
        console.error("Unsupported event", json_data);
    }
  };
  websocket.onclose = function (event) {
    if (event.wasClean == false) {
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
  // Mute foreground video element based on ?muted=true,false parameter, if it exists
  // Play video elements based on ?videos=true,false parameter (default = true)
  const params = window.location.search.slice(1);
  if (params != "") {
    for (const param of params.split("&")) {
      let param_pair = param.split("=");
      if (param_pair[0] == "muted") {
        video_muted = param_pair[1] == "true";
      }
      if (param_pair[0] == "videos") {
        play_videos = param_pair[1] == "true";
      }
    }
  }
  // Mute video if requested
  DOM_get("video_item").muted = video_muted;

  start_websocket();
  window.addEventListener("resize", () => {
    if (current_item !== undefined && current_item.type == "video") {
      resize_video_item();
    }
    resize_loop();
    update_background();
  });
});
