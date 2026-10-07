#pragma once
#ifdef __EMSCRIPTEN__

#include <string>

// Mounts the IndexedDB-backed /storage the game writes to, and reads what a
// previous session left there.
void WebCache_Mount(const char* path);
void WebCache_Load();
void WebCache_Save();
void WebCache_SaveNoWait();

// Blocks until the player picks a file in the browser and writes it to destPath.
// Returns 1 when a file was written, 0 when the picker was cancelled.
int WebFilePicker_PickInto(const char* title, const char* accept, int maxBytes, const char* destPath);

int WebConfirm(const char* title, const char* text);
void WebAlert(const char* title, const char* text);

// Swaps the canvas for the loading screen while the game blocks the page, and back.
void WebShowLoading(const char* status);
void WebShowGame();

#endif // __EMSCRIPTEN__
