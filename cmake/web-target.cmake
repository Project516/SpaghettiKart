# Browser build settings that need the game target. cmake/web.cmake runs
# before the target exists.

# torch's src/lib/web.cpp is embind glue that only the standalone build uses. The port
# drives Companion from C++, so drop it rather than pull embind into the link.
get_target_property(TORCH_SOURCES torch SOURCES)
list(FILTER TORCH_SOURCES EXCLUDE REGEX "src/lib/web\\.cpp$")
set_property(TARGET torch PROPERTY SOURCES ${TORCH_SOURCES})

target_link_options(${PROJECT_NAME} PRIVATE
  -sUSE_SDL=2
  -sUSE_WEBGL2=1
  -sFULL_ES3=1
  -sINITIAL_MEMORY=536870912
  -sALLOW_MEMORY_GROWTH=1
  # The N64 heap and the extracted archive both want more than the 2 GB wasm32
  # default, and a browser tab has to be able to grow into it.
  -sMAXIMUM_MEMORY=4294967296
  # main() returning has to tear the runtime down, or the tab keeps a canvas that
  # stopped drawing.
  -sEXIT_RUNTIME=1
  -sSTACK_SIZE=5242880
  -sPTHREAD_POOL_SIZE=16
  -sDEFAULT_PTHREAD_STACK_SIZE=4194304
  # The frame loop blocks; Asyncify lets it yield to the browser. Torch is excluded,
  # see src/port/web/asyncify-remove.txt.
  -sASYNCIFY=1
  "-sASYNCIFY_REMOVE=@${CMAKE_SOURCE_DIR}/src/port/web/asyncify-remove.txt"
  -sASYNCIFY_STACK_SIZE=8388608
  # Binaryen's inliner merges single-caller functions, which grows the functions
  # Asyncify has to instrument. Capping it keeps that bounded.
  -sBINARYEN_EXTRA_PASSES=-ocimfs=1000
  -sASSERTIONS=1
  # Keep the name section so a trap in the browser points at a function instead of
  # a bare offset.
  -g
  -sFORCE_FILESYSTEM=1
  -sEXPORTED_FUNCTIONS=_main,_malloc,_free
  -sEXPORTED_RUNTIME_METHODS=FS,ccall,cwrap,UTF8ToString,stringToUTF8
  # config.yml, yamls/ and meta/ drive the in-tab ROM extraction, and the port's own
  # o2r holds the fonts. Saves and the generated mk64.o2r live in IndexedDB under /storage.
  "--preload-file=${WEB_PRELOAD_DIR}@/"
  -lidbfs.js
)

# The link preloads this directory, so it has to be filled before the link runs.
add_custom_command(
  TARGET ${PROJECT_NAME}
  PRE_LINK
  COMMENT "Staging the preloaded game files..."
  COMMAND
    ${CMAKE_COMMAND} -DSOURCE_DIR=${CMAKE_SOURCE_DIR}
    -DDESTINATION_DIR=${WEB_PRELOAD_DIR}
    -P ${CMAKE_SOURCE_DIR}/cmake/StageRuntimeFiles.cmake
  COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${CMAKE_BINARY_DIR}/spaghetti.o2r" "${WEB_PRELOAD_DIR}/spaghetti.o2r"
  COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${CMAKE_SOURCE_DIR}/gamecontrollerdb.txt" "${WEB_PRELOAD_DIR}/gamecontrollerdb.txt"
  VERBATIM)

add_custom_command(
  TARGET ${PROJECT_NAME}
  POST_BUILD
  COMMENT "Staging the web shell..."
  COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${CMAKE_SOURCE_DIR}/src/port/web/shell.html"
          "$<TARGET_FILE_DIR:${PROJECT_NAME}>/spaghettikart.html"
  COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${CMAKE_SOURCE_DIR}/src/port/web/coi-serviceworker.js"
          "$<TARGET_FILE_DIR:${PROJECT_NAME}>/coi-serviceworker.js"
  COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${CMAKE_SOURCE_DIR}/src/port/web/CNAME"
          "$<TARGET_FILE_DIR:${PROJECT_NAME}>/CNAME"
  VERBATIM)
