// Browser storage and file picking, adapted from Ghostship's src/port/web (MIT).
#ifdef __EMSCRIPTEN__
#include "WebUtils.h"

#include <emscripten.h>
#include <SDL2/SDL_timer.h>
#include "ship/Context.h"

// clang-format off
EM_JS(void, js_idbfs_mount, (const char* cpath), {
    var path = UTF8ToString(cpath);
    try {
        FS.mkdir(path);
    } catch (e) {}
    FS.mount(IDBFS, {}, path);
});

// Returns 0 on success.
EM_ASYNC_JS(int, js_idbfs_sync, (int populate), {
    return await new Promise(function(resolve) {
        FS.syncfs(!!populate, function(err) {
            if (err) {
                console.error('[WebStorage] sync failed:', err);
            }
            resolve(err ? 1 : 0);
        });
    });
});

// An in-page message box, since the browser's alert() and confirm() block the whole tab.
// Leave noLabel empty for a single button. Returns 1 for the first button.
EM_ASYNC_JS(int, js_prompt, (const char* ctitle, const char* ctext, const char* cyes, const char* cno), {
    var title = UTF8ToString(ctitle);
    var text = UTF8ToString(ctext);
    var yesLabel = UTF8ToString(cyes);
    var noLabel = UTF8ToString(cno);
    return await new Promise(function(resolve) {
        var overlay = document.createElement('div');
        overlay.className = 'sk-prompt';
        var panel = document.createElement('div');
        panel.className = 'sk-prompt-panel';
        if (title) {
            var heading = document.createElement('h2');
            heading.textContent = title;
            panel.appendChild(heading);
        }
        var body = document.createElement('p');
        body.textContent = text;
        panel.appendChild(body);
        function addButton(label, result) {
            var button = document.createElement('button');
            button.textContent = label;
            button.addEventListener('click', function() {
                if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
                resolve(result);
            });
            panel.appendChild(button);
            return button;
        }
        var yes = addButton(yesLabel, 1);
        if (noLabel) addButton(noLabel, 0);
        overlay.appendChild(panel);
        document.body.appendChild(overlay);
        yes.focus();
    });
});

static void js_alert(const char* text) {
    js_prompt("", text, "OK", "");
}

EM_JS(void, js_idbfs_sync_nowait, (), {
    FS.syncfs(false, function(err) {
        if (err) {
            console.error('[WebStorage] sync failed:', err);
        }
    });
});

// Safari only opens a file dialog from inside a user gesture, and the game loop is not one,
// so this shows an in-page prompt and opens the dialog from its button's click handler.
EM_ASYNC_JS(int, js_pick_into, (const char* ctitle, const char* caccept, int maxBytes, const char* cdest), {
    var title = UTF8ToString(ctitle);
    var accept = UTF8ToString(caccept);
    var dest = UTF8ToString(cdest);
    return await new Promise(function(resolve) {
        var overlay = document.createElement('div');
        overlay.className = 'sk-prompt';
        var panel = document.createElement('div');
        panel.className = 'sk-prompt-panel';
        var label = document.createElement('p');
        label.textContent = title;
        var input = document.createElement('input');
        input.type = 'file';
        input.accept = accept;
        input.style.display = 'none';
        var choose = document.createElement('button');
        choose.textContent = 'Choose file';
        var cancel = document.createElement('button');
        cancel.textContent = 'Cancel';
        var settled = false;
        function finish(result) {
            if (settled) return;
            settled = true;
            if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
            resolve(result);
        }
        input.addEventListener('change', function(evt) {
            var file = evt.target.files[0];
            if (!file) { finish(0); return; }
            if (file.size > maxBytes) {
                label.textContent = file.name + ' is too large to be a ROM. Choose another file.';
                input.value = '';
                return;
            }
            // One read at a time; Cancel still works and makes the pending read a no-op.
            choose.disabled = true;
            label.textContent = 'Reading ' + file.name + '...';
            file.arrayBuffer().then(function(buf) {
                if (settled) return;
                try {
                    FS.writeFile(dest, new Uint8Array(buf));
                    finish(1);
                } catch (e) {
                    console.error('[WebFilePicker] write failed:', e);
                    finish(0);
                }
            }, function() { finish(0); });
        });
        choose.addEventListener('click', function() { input.click(); });
        cancel.addEventListener('click', function() { finish(0); });
        panel.appendChild(label);
        panel.appendChild(input);
        panel.appendChild(choose);
        panel.appendChild(cancel);
        overlay.appendChild(panel);
        document.body.appendChild(overlay);
    });
});
// clang-format on

// Writing back mirrors the app directory into IndexedDB, deleting whatever it lacks, so it
// stays off when loading failed and the directory may be missing saved files.
static bool sWriteBackEnabled = false;

void WebCache_Mount(const char* path) {
    static bool sMounted = false;
    if (sMounted) {
        return;
    }
    sMounted = true;
    js_idbfs_mount(path);
}

void WebCache_Load(void) {
    if (js_idbfs_sync(1) == 0) {
        sWriteBackEnabled = true;
    } else {
        js_alert("Spaghetti Kart could not load its files from browser storage. "
                 "Nothing from this session will be saved. Reload the page to try again.");
    }
}

void WebCache_Save(void) {
    static int sFailedWrites = 0;
    if (!sWriteBackEnabled) {
        return;
    }
    if (js_idbfs_sync(0) == 0) {
        sFailedWrites = 0;
    } else if (++sFailedWrites == 3) {
        js_alert("Spaghetti Kart could not write to browser storage, so recent progress is not saved. "
                 "The browser may be out of storage space for this site.");
    }
}

void WebCache_SaveNoWait(void) {
    if (sWriteBackEnabled) {
        js_idbfs_sync_nowait();
    }
}

int WebConfirm(const char* title, const char* text) {
    return js_prompt(title, text, "Yes", "No");
}

void WebAlert(const char* title, const char* text) {
    js_prompt(title, text, "OK", "");
}

void WebShowLoading(const char* status) {
    // clang-format off
    EM_ASM({ if (Module.showLoading) Module.showLoading(UTF8ToString($0)); }, status);
    // clang-format on
    // Let the page paint before the caller blocks it.
    emscripten_sleep(0);
}

void WebShowGame() {
    // clang-format off
    EM_ASM({ if (Module.showGame) Module.showGame(); });
    // clang-format on
}

int WebFilePicker_PickInto(const char* title, const char* accept, int maxBytes, const char* destPath) {
    return js_pick_into(title, accept, maxBytes, destPath);
}

#endif // __EMSCRIPTEN__
