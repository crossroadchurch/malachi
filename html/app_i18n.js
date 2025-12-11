let flip_css = new CSSStyleSheet();
document.adoptedStyleSheets.push(flip_css);

const i18n_ids = {
  current_item_name: {
    en: "No current item",
    es: "No hay ningún elemento actual",
  },
  audio_controls_text: {
    en: "Song recording:",
    es: "Audio de la canción:",
  },
  service_elt_text: {
    en: "Service",
    es: "Servicio",
  },
  song_elt_text: {
    en: "Songs",
    es: "Canciones",
  },
  bible_elt_text: {
    en: "Bible",
    es: "Biblia",
  },
  presentation_elt_text: {
    en: "Presentations",
    es: "Presentaciones",
  },
  video_elt_text: {
    en: "Videos",
    es: "Vídeos",
  },
  backgrounds_elt_text: {
    en: "Backgrounds",
    es: "Fondos",
  },
  styles_elt_text: {
    en: "Settings",
    es: "Config.",
  },
  new_service_btn: {
    en: "New",
    es: "Nuevo",
  },
  load_service_btn: {
    en: "Load",
    es: "Abrir",
  },
  save_service_btn: {
    en: "Save",
    es: "Guardar",
  },
  save_as_service_btn: {
    en: "Save as",
    es: "Guardar como",
  },
  export_service_btn: {
    en: "Export",
    es: "Exportar",
  },
  service_h3_text: {
    en: "Service plan",
    es: "Plan de servicio",
  },
  start_countdown_btn: {
    en: "Start countdown to:",
    es: "Comenzar la cuenta regresiva para:",
  },
  cancel_countdown_btn: {
    en: "Cancel countdown",
    es: "Cancelar cuenta regresiva",
  },
  import_notices_btn: {
    en: "Import notices",
    es: "Importar anuncios",
  },
  start_notices_btn: {
    en: "Start countdown with notices:",
    es: "Comenzar la cuenta regresiva con anuncios:",
  },
  songs_h3_text: {
    en: "Songs",
    es: "Canciones",
  },
  create_song_text: {
    en: "Create song",
    es: "Crear canción",
  },
  song_search_btn: {
    en: "Search",
    es: "Buscar",
  },
  bible_h3_text: {
    en: "Bible",
    es: "Biblia",
  },
  bible_search_btn: {
    en: "Search",
    es: "Buscar",
  },
  bible_select_all_btn: {
    en: "Select all",
    es: "Seleccionar todo",
  },
  bible_select_none_btn: {
    en: "Select none",
    es: "Seleccionar ninguno",
  },
  bible_add_to_btn: {
    en: "Add to service",
    es: "Añadir al servicio",
  },
  pres_h3_text: {
    en: "Presentations",
    es: "Presentaciones",
  },
  pres_import_btn: {
    en: "Import presentation",
    es: "Importar presentación",
  },
  videos_h3_text: {
    en: "Videos",
    es: "Videos",
  },
  videos_import_btn: {
    en: "Import video",
    es: "Importar vídeo",
  },
  loops_h3_text: {
    en: "Loops",
    es: "Vídeos de fondo:",
  },
  loops_import_btn: {
    en: "Import loop",
    es: "Importar vídeo de fondo",
  },
  clear_loop_btn: {
    en: "Clear loop",
    es: "Cancelar vídeo de fondo",
  },
  bgs_for_songs_text: {
    en: "Songs",
    es: "Canciones",
  },
  bgs_for_bible_text: {
    en: "Bible",
    es: "Biblia",
  },
  bgs_h3_text: {
    en: "Backgrounds",
    es: "Fondos",
  },
  bgs_import_btn: {
    en: "Import background",
    es: "Importar fondo",
  },
  settings_h3_text: {
    en: "Settings",
    es: "Configuración",
  },
  main_area_text: {
    en: "Main area",
    es: "Área principal",
  },
  s_width_text: {
    en: "Song area width (% of screen):",
    es: "Ancho del área de la canción (% de ancho de pantalla):",
  },
  s_font_size_text: {
    en: "Font size (% of screen height):",
    es: "Tamaño de letra (% de altura de pantalla):",
  },
  s_lines_text: {
    en: "Max lines per slide:",
    es: "Número máximo de líneas por diapositiva:",
  },
  s_margin_text: {
    en: "Top margin (% of screen height):",
    es: "Margen arriba (% de altura de pantalla):",
  },
  s_color_text: {
    en: "Song and Bible text colour:",
    es: "Color de letra para Canciones y Biblia:",
  },
  o_style_text: {
    en: "Text outline:",
    es: "Efecto tipográfico:",
  },
  o_drop_text: {
    en: "Drop shadow",
    es: "Sombra",
  },
  o_outline_text: {
    en: "Outlined",
    es: "Contorno",
  },
  o_none_text: {
    en: "None",
    es: "Ninguno",
  },
  sh_bible_text: {
    en: "Bible passages",
    es: "Pasajes bíblicos",
  },
  d_version_text: {
    en: "Default Bible version:",
    es: "Versión predeterminada de la Biblia:",
  },
  b_lines_text: {
    en: "Max Bible lines per slide:",
    es: "Número máximo de líneas de la Biblia por diapositiva:",
  },
  pl_width_text: {
    en: "Parallel column width (% of screen):",
    es: "Modo paralelo - ancho de columna (% de ancho de pantalla):",
  },
  pl_font_size_text: {
    en: "Parallel font size (% of screen height):",
    es: "Modo paralelo - tamaño de letra (% de altura de pantalla):",
  },
  pl_lines_text: {
    en: "Parallel max lines per slide:",
    es: "Modo paralelo - número máximo de líneas por diapositiva:",
  },
  sh_countdowns_text: {
    en: "Countdowns and notices",
    es: "Cuentas regresivas y anuncios",
  },
  ch_size_text: {
    en: "Header font size (% of screen height):",
    es: "Tamaño de letra para texto de arriba (% de altura de pantalla):",
  },
  cd_text_text: {
    en: "Header text:",
    es: "Texto de arriba:",
  },
  cd_size_text: {
    en: "Countdown font size (% of screen height):",
    es: "Tamaño de letra para cuenta regresiva (% de altura de pantalla):",
  },
  cd_top_text: {
    en: "Countdown top margin (% of screen height):",
    es: "Margen arriba para cuenta regresiva (% de altura de pantalla):",
  },
  nt_slide_text: {
    en: "Notices slide time (seconds):",
    es: "Duración de la diapositiva para anuncios (segundos):",
  },
  nt_cycle_text: {
    en: "Gap between notices cycles (seconds):",
    es: "Intervalo entre ciclos de anuncios (segundos):",
  },
  nt_end_text: {
    en: "Clear space at end of countdown (seconds):",
    es: "Espacio libre al fin de la cuenta regresvia (segundos):",
  },
  sh_copyright_text: {
    en: "Copyright area",
    es: "Área de derechos de autor",
  },
  d_copyright_text: {
    en: "Display copyright:",
    es: "Mostrar derechos de autor:",
  },
  cp_size_text: {
    en: "Copyright font size (0.1% of screen height):",
    es: "Tamaño de letra para derechos de autor (0.1% de altura de pantalla):",
  },
  cp_width_text: {
    en: "Copyright area width (% of screen width):",
    es: "Ancho de área de derechos de autor (% de ancho de pantalla):",
  },
  sh_verseorder_text: {
    en: "Verse order area",
    es: "Área de orden de versos",
  },
  d_verseorder_text: {
    en: "Display verse order:",
    es: "Mostrar el orden de los versos",
  },
  vo_size_text: {
    en: "Verse order font size (0.1% of screen height):",
    es: "Tamaño del orden de los versos (0.1% de altura de pantalla):",
  },
  vo_width_text: {
    en: "Verse order area width (% of screen width):",
    es: "Ancho de área del orden de los versos (% de ancho de pantalla):",
  },
  sh_appsettings_text: {
    en: "App settings",
    es: "Configuración de la aplicación",
  },
  app_lang_text: {
    en: "App language:",
    es: "Idioma de la aplicación:",
  },
  a_english_text: {
    en: "English",
    es: "Ingles",
  },
  a_spanish_text: {
    en: "Spanish",
    es: "Español",
  },
  at_scale_text: {
    en: "Song and Bible text size (scale by):",
    es: "Tamaño de letra para canciones y Biblia en la aplicación (factor de escala):",
  },
  sh_recyclebin_text: {
    en: "Song Recycle Bin",
    es: "Papelera de reciclaje para canciones",
  },
  recycle_bin_btn: {
    en: "Empty Song Recycle Bin",
    es: "Vaciar papelera de reciclaje para canciones",
  },
  about_h4_text: {
    en: "About Malachi",
    es: "Acerca de Malachi",
  },
  about_malachi_text: {
    en: "Malachi is open-source software, released under a ",
    es: "Malachi es un software de código abierto, publicado bajo una ",
  },
  about_gpl_text: {
    en: "GPL3 license.",
    es: "licencia GPL3.",
  },
  about_icons8_text: {
    en: "Some icons in Malachi are provided by ",
    es: "Algunos de los iconos de Malachi provienen de ",
  },
  updater_h3_text: {
    en: "Update Malachi",
    es: "Actualizar Malachi",
  },
  regular_intro_text: {
    en: "A new version of Malachi has been released - here's how to install it:",
    es: "Hay una actualización disponible para Malachi. Sigue estas instrucciones para instalarla.",
  },
  regular_step_1: {
    en: "Save the service if you want to load it later.",
    es: "Guarda el servicio si quieres abrirlo más tarde.",
  },
  regular_step_2: {
    en: "Click the <strong>Update Malachi</strong> button below.",
    es: "Haz clic en el botón <strong>Actualizar Malachi</strong> que aparece a continuación.",
  },
  regular_step_3: {
    en: "Wait for the green <em>Connected to Malachi server</em> message to be displayed in the bottom left of the app.",
    es: "Espera a que aparezca el mensaje <em>Conectado al servidor Malachi</em> en la esquina inferior izquierda de la aplicación.",
  },
  regular_step_4: {
    en: "Press <strong>Ctrl + Shift + R</strong> to refresh the app. Any other devices connected to Malachi will automatically reconnect to the server after a few seconds.",
    es: "Pulsa <strong>Ctrl + Mayús + R</strong> para actualizar la aplicación. Cualquier otro dispositivo conectado a Malachi se reconectará automáticamente al servidor después de unos segundos.",
  },
  updater_btn_text: {
    en: "Update Malachi",
    es: "Actualizar Malachi",
  },
  python_intro_text: {
    en: "The newest version of Malachi runs on a different version of Python. Here's how to update both Python and Malachi:",
    es: "La versión más reciente de Malachi requiere una versión diferente de Python. Sigue estas instrucciones para actualizar tanto Malachi como Python.",
  },
  python_step_1: {
    en: "Save the service if you want to load it later.",
    es: "Guarda el servicio si quieres abrirlo más tarde.",
  },
  python_step_2: {
    en: "Take a note of this Python version number: ",
    es: "Tome nota de este número de versión de Python: ",
  },
  python_step_3a: {
    en: "Follow the ",
    es: "Siga las ",
  },
  python_step_3b: {
    en: "manual update instructions",
    es: "instrucciones de actualización manual",
  },
  python_step_3c: {
    en: " on the Malachi wiki.",
    es: " en la wiki de Malachi.",
  },
  popup_new_header_text: {
    en: "Save service?",
    es: "¿Guardar servicio?",
  },
  popup_new_body_text: {
    en: "The current service has been modified.<br />Save these changes before starting a new service?",
    es: "El servicio actual ha sido modificado.<br />¿Guardar estos cambios antes de iniciar un nuevo servicio?",
  },
  popup_save_load_header_text: {
    en: "Save service?",
    es: "¿Guardar servicio?",
  },
  popup_save_load_body_text: {
    en: "The current service has been modified.<br />Save these changes before loading a different service?",
    es: "El servicio actual ha sido modificado.<br />¿Guardar estos cambios antes de abrir un otro servicio?",
  },
  popup_save_as_header_text: {
    en: "Save service as...",
    es: "Guardar servicio como...",
  },
  popup_save_as_body_text: {
    en: "Give the service a name:",
    es: "Dale un nombre al servicio:",
  },
  popup_load_header_text: {
    en: "Load service",
    es: "Abrir servicio",
  },
  popup_load_body_text: {
    en: "Choose service to load:",
    es: "Elija un servicio para abrir:",
  },
  popup_attach_header_text: {
    en: "Attach audio to song",
    es: "Adjuntar audio a la canción",
  },
  popup_attach_body_text: {
    en: "Choose audio to attach:",
    es: "Elige el audio que deseas adjuntar:",
  },
  popup_delete_header_text: {
    en: "Delete song?",
    es: "¿Eliminar canción?",
  },
  popup_delete_body_text: {
    en: "Are you sure that you want to delete the current song?<br />Deleted songs can be restored from the Song Recycle Bin in the Settings tab.",
    es: "¿Estás seguro de que deseas eliminar la canción actual?<br />Las canciones eliminadas se pueden restaurar desde la papelera de reciclaje para canciones en Configuración.",
  },
  popup_recycle_header_text: {
    en: "Empty Song Recycle Bin?",
    es: "¿Vaciar papelera de reciclaje para canciones?",
  },
  popup_recycle_body_text: {
    en: "Are you sure that you want to empty the Song Recycle Bin?<br />All Songs in the Recycle Bin will be deleted permanently.",
    es: "¿Estás seguro de que quieres vaciar la papelera de reciclaje para canciones?<br />Todas las canciones de la papelera de reciclaje se eliminarán de forma permanente.",
  },
  e_title_span: {
    en: "Song name:",
    es: "Nombre de la canción:",
  },
  e_author_label: {
    en: "Author:",
    es: "Autor:",
  },
  e_copyright_label: {
    en: "Copyright:",
    es: "Derechos de autor:",
  },
  e_book_label: {
    en: "Song book:",
    es: "Cancionero:",
  },
  e_number_label: {
    en: "Song number:",
    es: "Número de cancion:",
  },
  e_audio_label: {
    en: "Audio:",
    es: "Audio",
  },
  e_order_label: {
    en: "Verse order:",
    es: "Orden de los versos:",
  },
  e_key_label: {
    en: "Original key:",
    es: "Clave original:",
  },
  e_transpose_label: {
    en: "Transpose to:",
    es: "Transportar a:",
  },
  e_lyrics_label: {
    en: "Lyrics and chords:",
    es: "Letra y acordes:",
  },
  e_fills_label: {
    en: "Fills:",
    es: "Riffs:",
  },
};

const i18n_ids_attributes = {
  song_search: {
    attribute: "placeholder",
    en: "Lyric or title search",
    es: "Búsqueda de letras o título",
  },
  bible_search: {
    attribute: "placeholder",
    en: 'Search by reference (John 3:16-17) or words ("righteousness")',
    es: 'Busque versículos (John 3:16-17) o palabras ("justicia")',
  },
  bible_search_hint: {
    attribute: "data-tooltip",
    en: 'To search for verses containing particular word(s), enclose them in speech marks (e.g. "grace and peace")',
    es: 'Para buscar versículos que contengan palabras específicas, enciérrelas entre comillas (p.ej. "gracia y paz")',
  },
  f_name: {
    attribute: "placeholder",
    en: "Service name",
    es: "Nombre del servicio",
  },
  e_audio: {
    attribute: "placeholder",
    en: "No audio attached",
    es: "No hay audio adjunto",
  },
  e_order_hint: {
    attribute: "data-tooltip",
    en: "You can insert a fill into the order in the same way as a verse,\njust make sure to start it with a : (e.g. C1 :1 V2).",
    es: "Se puede insertar un riff en el orden de la misma manera que un verso,\nsólo asegúrese de comenzarlo con dos puntos (p.ej. C1 :1 V2).",
  },
  e_lyrics_hint: {
    attribute: "data-tooltip",
    en: "Use tags in angle brackets (e.g. <V1>) to indicate the start of sections.\n\nInsert a mandatory line break by placing [br] on a line by itself.\n\nPlace chords on the line before their lyrics and finish chord lines with @.\n\nUse # to pad out lyrics so that they line up with their chords.",
    es: "Utilice etiquetas entre corchetes angulares (p.ej. <V1>) para indicar\nel inicio de las secciones.\n\nInserte un salto de línea obligatorio colocando [br] en una línea por sí sola.\n\nColoque los acordes en la línea antes de sus letras y finalice\nlas líneas de acordes con @.\n\nUtilice # para mover las letras para que se alinee con sus acordes.",
  },
  e_fills_hint: {
    attribute: "data-tooltip",
    en: "Place one fill (intro, outro etc) per line.\n\nOnly use chords, there is no need to end the line with an @.",
    es: "Ponga un riff (introducción, final, etc) por línea.\n\nUtilice únicamente acordes, no es necesario terminar la línea con una @.",
  },
};

const i18n_classes = {
  ".i18n_save": {
    en: "Save",
    es: "Guardar",
  },
  ".i18n_discard": {
    en: "Discard",
    es: "Desechar",
  },
  ".i18n_cancel": {
    en: "Cancel",
    es: "Cancelar",
  },
  ".i18n_load": {
    en: "Load",
    es: "Abrir",
  },
  ".i18n_import": {
    en: "Import",
    es: "Importar",
  },
  ".i18n_attach": {
    en: "Attach",
    es: "Adjuntar",
  },
  ".i18n_delete": {
    en: "Delete song",
    es: "Eliminar canción",
  },
  ".i18n_empty": {
    en: "Empty Bin",
    es: "Vaciar papelera de reciclaje",
  },
  ".i18n_restore": {
    en: "Restore loop",
    es: "Reanudar vídeo de fondo",
  },
};

const i18n_strings = {
  toast_more_chars_needed: {
    en: "Please enter at least three characters to search by text",
    es: "Por favor, introduzca al menos tres caracteres para buscar por palabras",
  },
  toast_countdown_error: {
    en: "Invalid countdown\nThat time is in the past!",
    es: "Cuenta regresiva no válida\nEse tiempo ya es pasado",
  }, // MODIFY COUNTDOWN CODE so 24h gets added to times in past... removes need for this error condition
  create_song_mode: {
    en: "Create song",
    es: "Crear canción",
  },
  edit_song_mode: {
    en: "Edit song",
    es: "Editar canción",
  },
  importing_service: {
    en: "Importing service...",
    es: "Importando servicio...",
  },
  toast_connected_server: {
    en: "Connected to Malachi server",
    es: "Conectado al servidor Malachi",
  },
  no_current_item: {
    en: "No current item",
    es: "No hay ningún elemento actual",
  },
  toast_new_service_ok: {
    en: "New service started",
    es: "Nuevo servicio iniciado",
  },
  toast_new_service_error: {
    en: "Problem starting new service",
    es: "Problema al iniciar un nuevo servicio",
  },
  toast_load_service_ok: {
    en: "Service loaded successfully",
    es: "Servicio abierto exitosamente",
  },
  toast_load_service_error: {
    en: "Problem loading service",
    es: "Problema al abrir el servicio",
  },
  maximum_search_results: {
    en: "Maximum search results reached",
    es: "Se alcanzó el máximo de resultados de búsqueda.",
  },
  toast_save_service_ok: {
    en: "Service saved",
    es: "Servicio guardado",
  },
  toast_save_service_error: {
    en: "Problem saving service",
    es: "Problema al guardar el servicio",
  },
  no_saved_services: {
    en: "No saved service plans",
    es: "No se encontraron servicios guardados",
  },
  primary_version: {
    en: "Primary version:",
    es: "Versión principal:",
  },
  parallel_version: {
    en: "Parallel version:",
    es: "Versión paralela:",
  },
  default_version: {
    en: "Default Bible version:",
    es: "Versión predeterminada de la Biblia:",
  },
  toast_bible_search_ok: {
    en: "Bible search success",
    es: "Búsqueda bíblica exitosa",
  },
  toast_bible_search_error: {
    en: "Problem performing Bible search",
    es: "Problema al buscar de la Biblia",
  },
  no_audio_files_found: {
    en: "No audio files found",
    es: "No se encontraron archivos de audio",
  },
  updating_malachi: {
    en: "Updating Malachi...",
    es: "Actualizando Malachi...",
  },
  toast_service_export_ok: {
    en: "Service exported successfully",
    es: "Servicio exportado exitosamente",
  },
  toast_service_export_error: {
    en: "Problem exporting service",
    es: "Problema al exportar el servicio",
  },
  toast_video_added_ok: {
    en: "Video added to service",
    es: "Vídeo añadido al servicio",
  },
  toast_video_added_error: {
    en: "Problem adding video",
    es: "Problema al añadir el vídeo",
  },
  toast_song_added_ok: {
    en: "Song added to service",
    es: "Canción añadido al servicio",
  },
  toast_song_added_error: {
    en: "Problem adding song",
    es: "Problema al añadir la canción",
  },
  toast_song_edited_ok: {
    en: "Song edited",
    es: "Canción editada",
  },
  toast_song_edited_error: {
    en: "Problem editing song",
    es: "Problema al editar la canción",
  },
  toast_song_created_ok: {
    en: "Song added",
    es: "Canción añadida",
  },
  toast_song_created_error: {
    en: "Could not add song",
    es: "No se pudo añadir la canción",
  },
  toast_pres_added_ok: {
    en: "Presentation added to service",
    es: "Presentación añadida al servicio",
  },
  toast_pres_added_error: {
    en: "Problem adding presentation",
    es: "Problema al añadir la presentación",
  },
  toast_pres_import_ok: {
    en: "Presentation imported",
    es: "Presentación importada",
  },
  toast_pres_import_error: {
    en: "Problem importing presentation",
    es: "Problema al importar la presentación",
  },
  toast_bg_import_ok: {
    en: "Background imported",
    es: "Fondo importado",
  },
  toast_bg_import_error: {
    en: "Problem importing background",
    es: "Problema al importar el fondo",
  },
  toast_video_import_ok: {
    en: "Video imported",
    es: "Vídeo importado",
  },
  toast_video_import_error: {
    en: "Problem importing video",
    es: "Problema al importar el video",
  },
  toast_loop_import_ok: {
    en: "Loop imported",
    es: "Vídeo de fondo importado",
  },
  toast_loop_import_error: {
    en: "Problem importing loop",
    es: "Problema al importar el vídeo de fondo",
  },
  toast_audio_import_ok: {
    en: "Audio imported",
    es: "Audio importado",
  },
  toast_audio_import_error: {
    en: "Problem importing audio",
    es: "Problema al importar el audio",
  },
  toast_service_import_ok: {
    en: "Service imported",
    es: "Servicio importado",
  },
  toast_service_import_error: {
    en: "Problem importing service",
    es: "Problema al importar el servicio",
  },
  importing_notices: {
    en: "Importing notices...",
    es: "Importando los anuncios...",
  },
  import_notices: {
    en: "Import notices",
    es: "Importar los anuncios",
  },
  toast_notices_import_ok: {
    en: "Notices imported",
    es: "Anuncios importados",
  },
  toast_notices_import_error: {
    en: "Problem importing notices",
    es: "Problema al importar los anuncios",
  },
  toast_loop_set_ok: {
    en: "Video loop set",
    es: "Vídeo de fondo iniciado",
  },
  toast_loop_set_error: {
    en: "Problem setting video loop",
    es: "Problema al iniciar el vídeo de fondo",
  },
  toast_loop_cancel_ok: {
    en: "Video loop cancelled",
    es: "Vídeo de fondo cancelado",
  },
  toast_loop_cancel_error: {
    en: "Problem cancelling video loop",
    es: "Problema al cancelar vídeo de fondo",
  },
  toast_bible_add_ok: {
    en: "Bible passage added to service",
    es: "Pasaje bíblico añadida al servicio",
  },
  toast_bible_add_error: {
    en: "Problem adding Bible passage",
    es: "Problema al añadir el pasaje bíblico",
  },
  toast_version_change_ok: {
    en: "Bible version changed",
    es: "Versión bíblica cambiada",
  },
  toast_version_change_error: {
    en: "Problem changing Bible version",
    es: "Problema al cambiar la versión bíblica",
  },
  toast_parallel_change_ok: {
    en: "Parallel Bible version changed",
    es: "Versión bíblica paralela cambiada",
  },
  toast_parallel_change_error: {
    en: "Problem changing parallel Bible version",
    es: "Problema al cambiar la versión bíblica paralela",
  },
  toast_parallel_remove_ok: {
    en: "Parallel Bible version removed",
    es: "Versión bíblica paralela elimiada",
  },
  toast_parallel_remove_error: {
    en: "Problem removing parallel Bible version",
    es: "Problema al eliminar la versión bíblica paralela",
  },
  toast_item_remove_ok: {
    en: "Item removed",
    es: "Elemento eliminado",
  },
  toast_item_remove_error: {
    en: "Problem removing item",
    es: "Problema al eliminar el elemento",
  },
  toast_start_pres_ok: {
    en: "Starting presentation...",
    es: "Presentación iniciando...",
  },
  toast_start_pres_error: {
    en: "Problem starting presentation",
    es: "Problema al iniciar la presentación",
  },
  toast_delete_song_ok: {
    en: "Song deleted",
    es: "Canción eliminada",
  },
  toast_delete_song_error: {
    en: "Problem deleting song",
    es: "Problema al eliminar la canción",
  },
  toast_restore_song_ok: {
    en: "Song restored",
    es: "Canción restaurada",
  },
  toast_restore_song_error: {
    en: "Problem restoring song",
    es: "Problema al restaurar la canción",
  },
  toast_empty_bin_ok: {
    en: "Song Recycle Bin emptied",
    es: "Papelera de reciclaje para canciones vaciada",
  },
  toast_empty_bin_error: {
    en: "Problem emptying the Song Recycle Bin",
    es: "Problema al vaciar la papelera de reciclaje para canciones",
  },
  toast_connection_closed: {
    en: "Connection was closed/refused by server\nReconnection attempt will be made in 5 seconds",
    es: "La conexión fue cerrada o rechazada por el servidor\nSe realizará un intento de reconexión en 5 segundos",
  },
};

function apply_i18n(language) {
  // Add exception handling in case id doesn't exist due to typo...
  for (const i18n_id in i18n_ids) {
    document.getElementById(i18n_id).innerHTML = i18n_ids[i18n_id][language];
  }
  for (const i18n_id_at in i18n_ids_attributes) {
    document
      .getElementById(i18n_id_at)
      .setAttribute(
        i18n_ids_attributes[i18n_id_at]["attribute"],
        i18n_ids_attributes[i18n_id_at][language]
      );
  }
  for (const i18n_cls in i18n_classes) {
    document.querySelectorAll(i18n_cls).forEach((elt) => {
      elt.innerHTML = i18n_classes[i18n_cls][language];
    });
  }

  if (language == "en") {
    flip_css.replace(
      "#flip_screen_state::after { content: 'Screen OFF'; } #flip_screen_state:checked::after { content: 'Screen ON'; }"
    );
  } else if (language == "es") {
    flip_css.replace(
      "#flip_screen_state::after { content: 'Apagado'; } #flip_screen_state:checked::after { content: 'Encendido'; }"
    );
  }
}

function t8(str_id) {
  // Add exception handling
  return i18n_strings[str_id][app_language];
}
