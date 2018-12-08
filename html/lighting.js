let websocket;
let enabled_button = "blackout";
let sliders_enabled = true;
let slider_map = {};
let text_map = {};



function update_swatch(){
    let r_in = $(slider_map[5]).slider("option", "value")/255;
    let g_in = $(slider_map[6]).slider("option", "value")/255;
    let b_in = $(slider_map[7]).slider("option", "value")/255;
    let w = $(slider_map[8]).slider("option", "value")/255;

    // RGBW to HSI from: https://github.com/Susensio/RGBWLed/blob/master/RGBWLed.cpp
    // Modified to add in weighting to intensity channel
    let w_weight = 2;  // Weighting was 1/3 in original code
    let r1 = r_in + (w*w_weight);
    let g1 = g_in + (w*w_weight);
    let b1 = b_in + (w*w_weight);
    let I = (r1+g1+b1)/3;

    let H = 0;
    let S;
    if (I == 0){
        S = 0;
    } else {
        let m = Math.min(r1, g1, b1);
        S = 1 - (m/I);
    }

    if ((r_in == g_in) && (g_in == b_in)){
        H = 0;
    } else {
        let prod = (r1*r1) + (g1*g1) + (b1*b1) - (r1*g1) - (r1*b1) - (g1*b1);
        let a = Math.min(Math.max((r1 - g1/2 - b1/2) / Math.sqrt(prod), -1), 1);
        if (g1 >= b1){
            H = Math.acos(a);
        } else {
            H = 2*Math.PI - Math.acos(a);
        }
    }

    I = Math.min(I, 1)

    // Formulae from http://users.utcluj.ro/~arthur/PI/Lab02/RGB_to_HSI.pdf

    if (H < 2.09439) {
        x = I * (1 - S);
        y = I * (1 + (S * Math.cos(H) / Math.cos(1.047196667-H)));
        z = 3 * I - (x + y);
        r_out = 255 * y;
        g_out = 255 * z;
        b_out = 255 * x;
    } else if (H < 4.188787) {
        H = H - 2.09439;
        x = I * (1 - S);
        y = I * (1 + (S * Math.cos(H) / Math.cos(1.047196667-H)));
        z = 3 * I - (x + y);
        r_out = 255 * x;
        g_out = 255 * y;
        b_out = 255 * z;
    } else {
        H = H - 4.188787;
        x = I * (1 - S);
        y = I * (1 + (S * Math.cos(H) / Math.cos(1.047196667-H)));
        z = 3 * I - (x + y);
        r_out = 255 * z;
        g_out = 255 * x;
        b_out = 255 * y;
    }

    $('#swatch').css('background', 'rgb('+r_out+","+g_out+","+b_out+")");
}

function restore_channels(){
    for(let channel in slider_map){
        $(slider_map[channel]).slider({animate:0});
        $(text_map[channel]).val($(slider_map[channel]).slider("option", "value"));
    }
    if (enabled_button == "blackout"){
        $("#blackout").button("enable");
    } else {
        $("#unblackout").button("enable");
    }
    sliders_enabled = true;
}

$(document).ready(function(){
    $("#ch5-slider").slider({
        orientation: "vertical",
        min: 0,
        max: 255,
        range: "min",
        value: 0,
        slide: function(event, ui){
            update_swatch();
            if (sliders_enabled == true){
                $("#ch5-text").val(ui.value);
                websocket.send(JSON.stringify({"action": "command.set-light-channel", "params": {"channel": 5, "value": ui.value}}));
            } else {
                return false;
            }
        }
    });
    $("#ch6-slider").slider({
        orientation: "vertical",
        min: 0,
        max: 255,
        range: "min",
        value: 0,
        slide: function(event, ui){
            update_swatch();
            if (sliders_enabled == true){
                $("#ch6-text").val(ui.value);
                websocket.send(JSON.stringify({"action": "command.set-light-channel", "params": {"channel": 6, "value": ui.value}}));
            } else {
                return false;
            }
        }
    });
    $("#ch7-slider").slider({
        orientation: "vertical",
        min: 0,
        max: 255,
        range: "min",
        value: 0,
        slide: function(event, ui){
            update_swatch();
            if (sliders_enabled == true){
                $("#ch7-text").val(ui.value);
                websocket.send(JSON.stringify({"action": "command.set-light-channel", "params": {"channel": 7, "value": ui.value}}));
            } else {
                return false;
            }
        }
    });
    $("#ch8-slider").slider({
        orientation: "vertical",
        min: 0,
        max: 255,
        range: "min",
        value: 0,
        slide: function(event, ui){
            update_swatch();
            if (sliders_enabled == true){
                $("#ch8-text").val(ui.value);
                websocket.send(JSON.stringify({"action": "command.set-light-channel", "params": {"channel": 8, "value": ui.value}}));
            } else {
                return false;
            }
        }
    });
    $("#ch5-slider").draggable();
    $("#ch6-slider").draggable();
    $("#ch7-slider").draggable();
    $("#ch8-slider").draggable();
    $("#blackout, #unblackout").button();
    $("#blackout").button("enable");
    $("#unblackout").button("disable");

    $("#blackout").click(function(event){
        event.preventDefault();
        websocket.send(JSON.stringify({"action": "command.blackout-lights", "params": {}}));
        $("#blackout").button("disable");
        enabled_button = "unblackout";
    });
    $("#unblackout").click(function(event){
        event.preventDefault();
        websocket.send(JSON.stringify({"action": "command.unblackout-lights", "params": {}}));
        $("#unblackout").button("disable");
        enabled_button = "blackout";
    });

    websocket = new WebSocket("ws://" + window.location.hostname + ":9001/lights");
    websocket.onmessage = function (event) {
        json_data = JSON.parse(event.data);
        console.log(json_data);
        switch(json_data.action){
            case "update.light-init":
                $("#ch5-slider").slider("value", json_data.params[0][1]);
                $("#ch5-text").val(json_data.params[0][1]);
                $("#ch6-slider").slider("value", json_data.params[1][1]);
                $("#ch6-text").val(json_data.params[1][1]);
                $("#ch7-slider").slider("value", json_data.params[2][1]);
                $("#ch7-text").val(json_data.params[2][1]);
                $("#ch8-slider").slider("value", json_data.params[3][1]);
                $("#ch8-text").val(json_data.params[3][1]);
                slider_map[5] = "#ch5-slider";
                slider_map[6] = "#ch6-slider";
                slider_map[7] = "#ch7-slider";
                slider_map[8] = "#ch8-slider";
                text_map[5] = "#ch5-text";
                text_map[6] = "#ch6-text";
                text_map[7] = "#ch7-text";
                text_map[8] = "#ch8-text";
                update_swatch();
                break;
            case "update.light-channel-update":
                channel = json_data.params.channel;
                value = json_data.params.value;
                if (channel in slider_map){
                    if (value != $(slider_map[channel]).slider("option", "value")){
                        $(slider_map[channel]).slider("value", value);
                        $(text_map[channel]).val(value);
                    }
                }
                break;
            case "update.light-channels-update":
                for(let item in json_data.params.channels){
                    channel = json_data.params.channels[item][0];
                    value = json_data.params.channels[item][1];
                    if (channel in slider_map){
                        if (value != $(slider_map[channel]).slider("option", "value")){
                            $(slider_map[channel]).slider("value", value);
                            $(text_map[channel]).val(value);
                        }
                    }
                }
                break;
            case "update.fade-update":
                for(let item in json_data.params.channels){
                    channel = json_data.params.channels[item][0];
                    value = json_data.params.channels[item][1];
                    sliders_enabled = false;
                    if (channel in slider_map){
                        $(slider_map[channel]).slider({animate:json_data.params.duration});
                        $(text_map[channel]).val("Fading");
                        $(slider_map[channel]).slider("value", value);
                    }
                    window.setTimeout(restore_channels, 4000);
                }
                break;
            case "response.set-light-channel":
                break;
            case "response.set-light-channels":
                break;
            case "response.blackout-lights":
                break;
            case "response.unblackout-lights":
                break;
            default:
                console.error("Unsupported event", json_data);
        }
    }
});