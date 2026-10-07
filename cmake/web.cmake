# Browser build, configured with emcmake. SDL2, zlib and libpng come from
# emscripten ports; everything else is fetched and built from source with the
# same -pthread flags so every object can share wasm memory. Ogg and vorbis are
# built from source because emscripten only ships them without the -mt variants
# that -pthread asks for.

include(FetchContent)

# ogg and vorbis still declare cmake_minimum_required below 3.5.
set(CMAKE_POLICY_VERSION_MINIMUM 3.5)
set(CMAKE_POLICY_DEFAULT_CMP0077 NEW)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)

set(USE_OPENGLES ON CACHE BOOL "" FORCE)
add_compile_definitions(USE_OPENGLES=1)

set(WEB_PORT_FLAGS -sUSE_SDL=2 -sUSE_ZLIB=1 -sUSE_LIBPNG=1)

# The link options preload this directory, and a POST_BUILD step fills it.
set(WEB_PRELOAD_DIR ${CMAKE_BINARY_DIR}/web-preload)
add_compile_options(-pthread -fexceptions ${WEB_PORT_FLAGS})
add_link_options(-pthread -fexceptions ${WEB_PORT_FLAGS})

# The find modules below need the port libraries on disk at configure time.
execute_process(
    COMMAND ${EMSCRIPTEN_ROOT_PATH}/embuilder build zlib libpng-mt sdl2-mt
    RESULT_VARIABLE WEB_EMBUILDER_RESULT
)
if(NOT WEB_EMBUILDER_RESULT EQUAL 0)
    message(FATAL_ERROR "embuilder failed to build the emscripten ports")
endif()

set(WEB_SYSROOT "${EMSCRIPTEN_SYSROOT}")
if(NOT WEB_SYSROOT)
    set(WEB_SYSROOT "${CMAKE_SYSROOT}")
endif()
set(ZLIB_INCLUDE_DIR "${WEB_SYSROOT}/include" CACHE PATH "" FORCE)
set(ZLIB_LIBRARY "${WEB_SYSROOT}/lib/wasm32-emscripten/libz.a" CACHE FILEPATH "" FORCE)
set(PNG_PNG_INCLUDE_DIR "${WEB_SYSROOT}/include" CACHE PATH "" FORCE)
set(PNG_LIBRARY "${WEB_SYSROOT}/lib/wasm32-emscripten/libpng-mt.a" CACHE FILEPATH "" FORCE)

add_library(SDL2::SDL2 INTERFACE IMPORTED GLOBAL)
set_target_properties(SDL2::SDL2 PROPERTIES
    INTERFACE_COMPILE_OPTIONS "-sUSE_SDL=2"
    INTERFACE_LINK_OPTIONS "-sUSE_SDL=2"
)
set(SDL2_FOUND TRUE)
set(SDL2_INCLUDE_DIRS "")

set(tinyxml2_BUILD_TESTING OFF)
FetchContent_Declare(tinyxml2
    GIT_REPOSITORY https://github.com/leethomason/tinyxml2.git
    GIT_TAG 10.0.0
    GIT_SHALLOW TRUE
    OVERRIDE_FIND_PACKAGE
)
set(JSON_BuildTests OFF)
FetchContent_Declare(nlohmann_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
    GIT_SHALLOW TRUE
    OVERRIDE_FIND_PACKAGE
)
FetchContent_Declare(spdlog
    GIT_REPOSITORY https://github.com/gabime/spdlog.git
    GIT_TAG v1.15.3
    GIT_SHALLOW TRUE
    OVERRIDE_FIND_PACKAGE
)
set(INSTALL_DOCS OFF)
FetchContent_Declare(libzip
    GIT_REPOSITORY https://github.com/nih-at/libzip.git
    GIT_TAG v1.11.4
    GIT_SHALLOW TRUE
    OVERRIDE_FIND_PACKAGE
)
FetchContent_Declare(Ogg
    GIT_REPOSITORY https://github.com/xiph/ogg.git
    GIT_TAG v1.3.5
    GIT_SHALLOW TRUE
    OVERRIDE_FIND_PACKAGE
)
FetchContent_Declare(Vorbis
    GIT_REPOSITORY https://github.com/xiph/vorbis.git
    GIT_TAG v1.3.7
    GIT_SHALLOW TRUE
    OVERRIDE_FIND_PACKAGE
)

FetchContent_MakeAvailable(tinyxml2 nlohmann_json spdlog libzip Ogg Vorbis)

# libultraship links libzip privately, so its headers are not on the game's include path
# the way a system libzip's would be. zipconf.h is generated into the build tree.
include_directories("${libzip_SOURCE_DIR}/lib" "${libzip_BINARY_DIR}")

# libultraship's crash handler calls backtrace() without including <execinfo.h>,
# which Emscripten has no equivalent of.
include_directories("${CMAKE_SOURCE_DIR}/cmake/web-include")

# The names Spaghetti Kart links, which the platform Find modules create elsewhere.
add_library(Ogg::ogg ALIAS ogg)
add_library(Vorbis::vorbis ALIAS vorbis)
add_library(Vorbis::vorbisenc ALIAS vorbisenc)
add_library(Vorbis::vorbisfile ALIAS vorbisfile)
