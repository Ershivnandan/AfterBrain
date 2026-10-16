// AfterBrain.jsx - Native Responsive AI Live Chat Copilot for Adobe After Effects
// Built for 100% inside-AE live chat, asset tagging, and responsive width/height docking.

(function(thisObj) {
    // Close existing standalone palette window if already open to prevent duplicate stacking
    if ($.global.afterBrainPalette && $.global.afterBrainPalette instanceof Window) {
        try { $.global.afterBrainPalette.close(); } catch(e) {}
    }

    function buildUI(thisObj) {
        var win = (thisObj instanceof Panel) ? thisObj : new Window("palette", "AfterBrain AI Live Chat", undefined, {resizeable: true});
        if (win !== null) {
            win.orientation = "column";
            win.alignChildren = ["fill", "fill"];
            win.spacing = 6;
            win.margins = 8;

            // 1. Header Bar (Responsive top)
            var header = win.add("group");
            header.orientation = "row";
            header.alignment = ["fill", "top"];

            var title = header.add("statictext", undefined, "🧠 AfterBrain Live Copilot");
            try {
                title.graphics.font = ScriptUI.newFont("Arial", "BOLD", 13);
            } catch(e) {}

            var statusTxt = header.add("statictext", undefined, "● Online (qwen3:8b)");
            statusTxt.alignment = ["right", "center"];

            // 2. Active Project Assets Bar
            var assetGroup = win.add("group");
            assetGroup.orientation = "row";
            assetGroup.alignment = ["fill", "top"];
            assetGroup.spacing = 4;

            var assetLbl = assetGroup.add("statictext", undefined, "Project Assets:");
            var assetDropdown = assetGroup.add("dropdownlist", undefined, ["(Click 'Scan' to list assets)"]);
            assetDropdown.alignment = ["fill", "center"];
            assetDropdown.selection = 0;

            var refreshBtn = assetGroup.add("button", undefined, "↻ Sync");
            refreshBtn.preferredSize.width = 50;

            // 3. Responsive Live Chat Stream (Listbox ensures NO text-selection bugs, NO copy cursor, and instant button clicks!)
            var chatList = win.add("listbox", undefined, [], {multiline: false});
            chatList.alignment = ["fill", "fill"];
            chatList.minimumSize = [180, 140];

            function addLogItems(items) {
                for (var i = 0; i < items.length; i++) {
                    chatList.add("item", items[i]);
                }
            }

            // Initial welcome guidance
            addLogItems([
                "✦ [AfterBrain AI Live Motion Copilot connected]",
                "1. Drag & drop character or background into After Effects.",
                "2. Click '↻ Sync' or '🔍 Scan' to index layers.",
                "3. Tag any asset: '@AlienBob is our funny alien hero'.",
                "4. Animate: 'Animate bg_tinku_garden with slow zoom' or 'Make @AlienBob wave'.",
                "─────────────────────────────────────────────────────────────"
            ]);

            // Helper to append message cleanly to listbox without text selection bugs
            function appendChat(sender, msg) {
                var time = new Date();
                var timeStr = (time.getHours() < 10 ? "0" : "") + time.getHours() + ":" + (time.getMinutes() < 10 ? "0" : "") + time.getMinutes();
                var headerItem = chatList.add("item", "[" + sender + " " + timeStr + "]");
                
                var cleanLines = msg.split("\n");
                for (var i = 0; i < cleanLines.length; i++) {
                    var line = cleanLines[i].replace(/^\s+|\s+$/g, "");
                    if (line.length > 0) {
                        chatList.add("item", "  " + line);
                    }
                }
                chatList.add("item", " "); // spacing separator

                // Auto-scroll to latest item
                try {
                    chatList.revealItem(chatList.items[chatList.items.length - 1]);
                } catch(e) {}

                // Keep input field ready
                try {
                    inputField.active = true;
                } catch(e) {}

                // Immediate After Effects UI repaint
                try {
                    win.layout.layout(true);
                    app.redraw();
                } catch(e) {}
            }

            // 4. Quick Action Chips (Responsive bottom group)
            var chipsGroup = win.add("group");
            chipsGroup.orientation = "row";
            chipsGroup.alignment = ["fill", "bottom"];
            chipsGroup.spacing = 4;

            var chipScan = chipsGroup.add("button", undefined, "🔍 Scan");
            var chipTag = chipsGroup.add("button", undefined, "🏷️ Tag");
            var chipWave = chipsGroup.add("button", undefined, "👋 Wave");
            var chipLip = chipsGroup.add("button", undefined, "🗣️ Lip-Sync");
            var chipClear = chipsGroup.add("button", undefined, "🧹 Clear");

            // 5. Input Bar & Send Button (Responsive bottom)
            var inputGroup = win.add("group");
            inputGroup.orientation = "row";
            inputGroup.alignment = ["fill", "bottom"];
            inputGroup.spacing = 6;

            var inputField = inputGroup.add("edittext", undefined, "");
            inputField.alignment = ["fill", "center"];
            inputField.minimumSize = [120, 26];

            var sendBtn = inputGroup.add("button", undefined, "Send ➔");
            sendBtn.preferredSize.width = 65;
            sendBtn.preferredSize.height = 26;

            // Robust JSON string extractor
            function extractJsonReply(raw) {
                var replyKey = '"reply":';
                var idx = raw.indexOf(replyKey);
                if (idx === -1) return "";
                var startQuote = raw.indexOf('"', idx + replyKey.length);
                if (startQuote === -1) return "";
                var result = "";
                var escape = false;
                for (var i = startQuote + 1; i < raw.length; i++) {
                    var c = raw.charAt(i);
                    if (escape) {
                        if (c === 'n') result += '\n';
                        else if (c === 't') result += '\t';
                        else if (c === '"') result += '"';
                        else if (c === '\\') result += '\\';
                        else result += c;
                        escape = false;
                    } else if (c === '\\') {
                        escape = true;
                    } else if (c === '"') {
                        break;
                    } else {
                        result += c;
                    }
                }
                return result;
            }

            var isSyncingDropdown = false;

            // Sync project assets into dropdown
            function syncAssets() {
                try {
                    var socket = new Socket();
                    socket.timeout = 10;
                    if (socket.open("127.0.0.1:8088", "binary")) {
                        var req = "GET /api/project_assets HTTP/1.0\r\nHost: 127.0.0.1:8088\r\nConnection: close\r\n\r\n";
                        socket.write(req);
                        var response = "";
                        while (!socket.eof) {
                            var chunk = socket.read(4096);
                            if (!chunk) break;
                            response += chunk;
                        }
                        socket.close();

                        isSyncingDropdown = true;
                        assetDropdown.removeAll();
                        var tagMatches = response.match(/"tag":\s*"([^"]+)"/g);
                        if (tagMatches && tagMatches.length > 0) {
                            for (var t = 0; t < tagMatches.length; t++) {
                                var tagName = tagMatches[t].replace(/"tag":\s*"/, "").replace(/"/, "");
                                assetDropdown.add("item", tagName);
                            }
                            assetDropdown.selection = 0;
                        } else {
                            assetDropdown.add("item", "(No imported image assets found)");
                            assetDropdown.selection = 0;
                        }
                        isSyncingDropdown = false;
                    }
                } catch(e) {
                    isSyncingDropdown = false;
                }
            }

            // Send live chat message to background AI
            function sendChatMessage(text) {
                var userMsg = text || inputField.text;
                userMsg = userMsg.replace(/^\s+|\s+$/g, "");
                if (!userMsg) return;

                appendChat("You 👤", userMsg);
                inputField.text = "";

                // Immediate visual feedback in After Effects UI
                appendChat("AfterBrain 🤖", "⏳ Thinking & applying in After Effects...");

                try {
                    var socket = new Socket();
                    socket.timeout = 45;
                    if (socket.open("127.0.0.1:8088", "binary")) {
                        var escapedMsg = userMsg.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\r/g, " ").replace(/\n/g, " ");
                        var jsonBody = '{"message": "' + escapedMsg + '"}';
                        var req = "POST /api/chat HTTP/1.0\r\n" +
                            "Host: 127.0.0.1:8088\r\n" +
                            "Content-Type: application/json; charset=utf-8\r\n" +
                            "Connection: close\r\n" +
                            "Content-Length: " + jsonBody.length + "\r\n\r\n" + jsonBody;

                        socket.write(req);

                        var response = "";
                        while (!socket.eof) {
                            var chunk = socket.read(4096);
                            if (!chunk) break;
                            response += chunk;
                        }
                        socket.close();

                        var cleanReply = extractJsonReply(response);
                        if (cleanReply) {
                            appendChat("AfterBrain 🤖", cleanReply);
                        } else {
                            appendChat("AfterBrain 🤖", response || "Execution finished in active composition.");
                        }

                        // Refresh asset tags
                        syncAssets();
                    } else {
                        appendChat("AfterBrain 🤖", "⚠️ Could not connect to AfterBrain background server on 127.0.0.1:8088.\n" +
                            "Please ensure python -m src.cli is running in your terminal!");
                    }
                } catch(err) {
                    appendChat("AfterBrain 🤖", "⚠️ Connection error: " + err.toString());
                }
            }

            // Event Handlers
            sendBtn.onClick = function() {
                sendChatMessage();
            };

            inputField.addEventListener("keydown", function(k) {
                if (k.keyName === "Enter") {
                    sendChatMessage();
                }
            });

            assetDropdown.onChange = function() {
                if (isSyncingDropdown) return;
                if (assetDropdown.selection && assetDropdown.selection.text && assetDropdown.selection.text.indexOf("@") === 0) {
                    inputField.text += " " + assetDropdown.selection.text + " ";
                    inputField.active = true;
                }
            };

            refreshBtn.onClick = function() {
                syncAssets();
                sendChatMessage("scan my project assets");
            };

            chipScan.onClick = function() {
                sendChatMessage("scan my project assets");
            };

            chipTag.onClick = function() {
                var selectedTag = (assetDropdown.selection && assetDropdown.selection.text.indexOf("@") === 0) ? assetDropdown.selection.text : "@MyCharacter";
                var tagInput = prompt("Tag an asset (e.g. '" + selectedTag + " is our goofy alien hero'):", selectedTag + " is our protagonist");
                if (tagInput) {
                    sendChatMessage(tagInput);
                }
            };

            chipWave.onClick = function() {
                var activeChar = (assetDropdown.selection && assetDropdown.selection.text.indexOf("@") === 0) ? assetDropdown.selection.text : "@AlienBob";
                sendChatMessage("Make " + activeChar + " wave enthusiastically and bounce up and down");
            };

            chipLip.onClick = function() {
                var activeChar = (assetDropdown.selection && assetDropdown.selection.text.indexOf("@") === 0) ? assetDropdown.selection.text : "@AlienBob";
                sendChatMessage("Lip sync " + activeChar + ": Hello everyone! Welcome to AfterBrain live AI animation!");
            };

            chipClear.onClick = function() {
                chatList.removeAll();
                addLogItems([
                    "✦ [AfterBrain AI Live Motion Copilot connected]",
                    "1. Drag & drop character or background into After Effects.",
                    "2. Click '↻ Sync' or '🔍 Scan' to index layers.",
                    "3. Tag any asset: '@AlienBob is our funny alien hero'.",
                    "4. Animate: 'Animate bg_tinku_garden with slow zoom' or 'Make @AlienBob wave'.",
                    "─────────────────────────────────────────────────────────────"
                ]);
                try {
                    inputField.active = true;
                } catch(e) {}
            };

            // Responsive Layout Handling on Width/Height Resize
            win.onResizing = function() {
                this.layout.resize();
            };
            win.onResize = function() {
                this.layout.resize();
            };

            win.layout.layout(true);
            syncAssets();

            // Store reference globally if palette window
            if (win instanceof Window) {
                $.global.afterBrainPalette = win;
            }

            return win;
        }
    }

    var afterBrainPal = buildUI(thisObj);
    if (afterBrainPal !== null && (afterBrainPal instanceof Window)) {
        afterBrainPal.center();
        afterBrainPal.show();
    }
})(this);
