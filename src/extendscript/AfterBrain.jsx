// AfterBrain.jsx - AI Motion Copilot for Adobe After Effects
// UI matches modern Dark Theme Copilot:
// - Blue rounded bubbles on the RIGHT for user prompts
// - Dark slate rounded bubbles on the LEFT for AI responses
// - Responsive, scrollable message feed with auto-scroll and mouse wheel support
// - Direct deep composition control via local Ollama worker

(function(thisObj) {
    // Close existing standalone palette window if already open to prevent duplicate stacking
    if ($.global.afterBrainPalette && $.global.afterBrainPalette instanceof Window) {
        try { $.global.afterBrainPalette.close(); } catch(e) {}
    }

    function buildUI(thisObj) {
        var win = (thisObj instanceof Panel) ? thisObj : new Window("palette", "AnMCP AI Worker", undefined, {resizeable: true});
        if (win !== null) {
            win.orientation = "column";
            win.alignChildren = ["fill", "fill"];
            win.spacing = 6;
            win.margins = 8;

            try {
                win.graphics.backgroundColor = win.graphics.newBrush(win.graphics.BrushType.SOLID_COLOR, [0.11, 0.11, 0.11, 1]);
            } catch(e) {}

            // 1. Top Header Bar (Matching screenshot)
            var topBar = win.add("group");
            topBar.orientation = "row";
            topBar.alignment = ["fill", "top"];
            topBar.spacing = 6;

            var titleTxt = topBar.add("statictext", undefined, "AnMCP AI Worker (Ollama qwen3:8b)");
            try {
                titleTxt.graphics.font = ScriptUI.newFont("Segoe UI", "BOLD", 11);
                titleTxt.graphics.foregroundColor = titleTxt.graphics.newPen(titleTxt.graphics.PenType.SOLID_COLOR, [0.88, 0.88, 0.88, 1], 1);
            } catch(e) {
                try {
                    titleTxt.graphics.font = ScriptUI.newFont("Arial", "BOLD", 11);
                } catch(e2) {}
            }

            var statusIcon = topBar.add("statictext", undefined, "● Online");
            statusIcon.alignment = ["right", "center"];
            try {
                statusIcon.graphics.font = ScriptUI.newFont("Segoe UI", "REGULAR", 10);
                statusIcon.graphics.foregroundColor = statusIcon.graphics.newPen(statusIcon.graphics.PenType.SOLID_COLOR, [0.25, 0.85, 0.45, 1], 1);
            } catch(e) {}

            // 2. Active Layer Context Bar
            var contextBar = win.add("group");
            contextBar.orientation = "row";
            contextBar.alignment = ["fill", "top"];
            contextBar.spacing = 4;

            var contextLbl = contextBar.add("statictext", undefined, "Target Layer:");
            try {
                contextLbl.graphics.font = ScriptUI.newFont("Segoe UI", "REGULAR", 10);
                contextLbl.graphics.foregroundColor = contextLbl.graphics.newPen(contextLbl.graphics.PenType.SOLID_COLOR, [0.65, 0.65, 0.65, 1], 1);
            } catch(e) {}

            var assetDropdown = contextBar.add("dropdownlist", undefined, ["(Auto-detect composition layers)"]);
            assetDropdown.alignment = ["fill", "center"];
            assetDropdown.selection = 0;

            var syncBtn = contextBar.add("button", undefined, "↻ Sync");
            syncBtn.preferredSize.width = 50;

            // 3. Scrollable Chat Viewport (Matching screenshot)
            var chatRow = win.add("group");
            chatRow.orientation = "row";
            chatRow.alignment = ["fill", "fill"];
            chatRow.spacing = 2;

            var chatViewport = chatRow.add("group");
            chatViewport.orientation = "column";
            chatViewport.alignment = ["fill", "fill"];
            chatViewport.alignChildren = ["fill", "top"];

            var chatScrollContainer = chatViewport.add("group");
            chatScrollContainer.orientation = "column";
            chatScrollContainer.alignment = ["fill", "top"];
            chatScrollContainer.alignChildren = ["fill", "top"];
            chatScrollContainer.spacing = 10;
            chatScrollContainer.margins = 4;

            var scrollbar = chatRow.add("scrollbar");
            scrollbar.alignment = ["right", "fill"];
            scrollbar.preferredSize.width = 14;
            scrollbar.visible = false;

            function updateScroll() {
                try {
                    win.layout.layout(true);
                    var contentHeight = (chatScrollContainer.preferredSize && chatScrollContainer.preferredSize.height) ? chatScrollContainer.preferredSize.height : 0;
                    var viewHeight = 250;
                    try {
                        if (chatViewport.size && chatViewport.size.height > 0) {
                            viewHeight = chatViewport.size.height;
                        } else if (win.size && win.size.height > 0) {
                            viewHeight = win.size.height - 140;
                        }
                    } catch(e) {}

                    if (contentHeight > viewHeight && viewHeight > 0) {
                        scrollbar.visible = true;
                        scrollbar.minvalue = 0;
                        scrollbar.maxvalue = Math.max(0, contentHeight - viewHeight + 30);
                        scrollbar.value = scrollbar.maxvalue; // auto scroll to newest
                        chatScrollContainer.location = [0, -scrollbar.value];
                    } else {
                        scrollbar.visible = false;
                        chatScrollContainer.location = [0, 0];
                    }
                } catch(e) {}
            }

            scrollbar.onChanging = function() {
                chatScrollContainer.location = [0, -this.value];
            };
            scrollbar.onChange = function() {
                chatScrollContainer.location = [0, -this.value];
            };

            win.addEventListener("wheel", function(e) {
                if (scrollbar.visible && scrollbar.maxvalue > 0) {
                    var step = 30;
                    var nextVal = scrollbar.value - (e.delta * step);
                    nextVal = Math.max(0, Math.min(scrollbar.maxvalue, nextVal));
                    scrollbar.value = nextVal;
                    chatScrollContainer.location = [0, -nextVal];
                }
            });

            // Add Chat Bubble (AI on Left, Sender on Right)
            function addMessage(text, isAi) {
                var row = chatScrollContainer.add("group");
                row.orientation = "row";
                row.alignment = ["fill", "top"];

                var viewW = 320;
                try {
                    if (chatViewport.size && chatViewport.size.width > 0) {
                        viewW = chatViewport.size.width;
                    } else if (win.size && win.size.width > 0) {
                        viewW = win.size.width - 40;
                    }
                } catch(e) {}

                var availWidth = Math.max(180, viewW);
                var maxBubbleW = Math.max(160, Math.floor(availWidth * 0.80));

                if (isAi) {
                    // AI Response Bubble on the LEFT (Dark Charcoal #2A2A2A)
                    row.alignChildren = ["left", "top"];

                    var aiBubble = row.add("panel", undefined, "");
                    aiBubble.orientation = "column";
                    aiBubble.alignChildren = ["left", "top"];
                    aiBubble.margins = [14, 10, 14, 10];
                    aiBubble.spacing = 2;
                    aiBubble.maximumSize.width = maxBubbleW;

                    try {
                        aiBubble.graphics.backgroundColor = aiBubble.graphics.newBrush(aiBubble.graphics.BrushType.SOLID_COLOR, [0.20, 0.20, 0.20, 1]);
                    } catch(e) {}

                    var cleanLines = text.split("\n");
                    for (var i = 0; i < cleanLines.length; i++) {
                        var l = cleanLines[i].replace(/^\s+|\s+$/g, "");
                        if (l.length > 0) {
                            var aiTxt = aiBubble.add("statictext", undefined, l, {multiline: true});
                            aiTxt.maximumSize.width = maxBubbleW - 24;
                            try {
                                aiTxt.graphics.font = ScriptUI.newFont("Segoe UI", "REGULAR", 11);
                                aiTxt.graphics.foregroundColor = aiTxt.graphics.newPen(aiTxt.graphics.PenType.SOLID_COLOR, [0.93, 0.93, 0.93, 1], 1);
                            } catch(e) {}
                        }
                    }
                } else {
                    // Sender (User) Bubble on the RIGHT (Vivid Blue #1A73E8)
                    row.alignChildren = ["right", "top"];

                    var userBubble = row.add("panel", undefined, "");
                    userBubble.orientation = "column";
                    userBubble.alignChildren = ["left", "top"];
                    userBubble.margins = [14, 10, 14, 10];
                    userBubble.spacing = 2;
                    userBubble.maximumSize.width = maxBubbleW;

                    try {
                        userBubble.graphics.backgroundColor = userBubble.graphics.newBrush(userBubble.graphics.BrushType.SOLID_COLOR, [0.10, 0.46, 0.90, 1]);
                    } catch(e) {}

                    var uLines = text.split("\n");
                    for (var j = 0; j < uLines.length; j++) {
                        var ul = uLines[j].replace(/^\s+|\s+$/g, "");
                        if (ul.length > 0) {
                            var userTxt = userBubble.add("statictext", undefined, ul, {multiline: true});
                            userTxt.maximumSize.width = maxBubbleW - 24;
                            try {
                                userTxt.graphics.font = ScriptUI.newFont("Segoe UI", "REGULAR", 11);
                                userTxt.graphics.foregroundColor = userTxt.graphics.newPen(userTxt.graphics.PenType.SOLID_COLOR, [1, 1, 1, 1], 1);
                            } catch(e) {}
                        }
                    }
                }

                updateScroll();

                try {
                    app.redraw();
                } catch(e) {}

                return row;
            }

            function resetChat() {
                while (chatScrollContainer.children.length > 0) {
                    chatScrollContainer.remove(chatScrollContainer.children[0]);
                }
                addMessage("Hello! I am your AI Motion Copilot.\n\n" +
                    "• Animate scene: 'Animate bg_tinku_garden with slow zoom and pan'\n" +
                    "• Animate characters: 'Make AlienBob wave his right hand and jump'\n" +
                    "• Ask questions or control anything in your comp.", true);
            }

            // 4. Action Chips (Pill shortcuts)
            var chipsGroup = win.add("group");
            chipsGroup.orientation = "row";
            chipsGroup.alignment = ["fill", "bottom"];
            chipsGroup.spacing = 4;

            var chipScan = chipsGroup.add("button", undefined, "🔍 Scan");
            var chipTag = chipsGroup.add("button", undefined, "🏷️ Tag");
            var chipWave = chipsGroup.add("button", undefined, "👋 Wave");
            var chipLip = chipsGroup.add("button", undefined, "🗣️ Lip-Sync");
            var chipClear = chipsGroup.add("button", undefined, "🧹 Clear");

            // 5. Input Bar & Send Button (Matching screenshot)
            var inputWrapper = win.add("panel", undefined, "");
            inputWrapper.orientation = "row";
            inputWrapper.alignment = ["fill", "bottom"];
            inputWrapper.margins = [6, 4, 6, 4];
            inputWrapper.spacing = 6;

            try {
                inputWrapper.graphics.backgroundColor = inputWrapper.graphics.newBrush(inputWrapper.graphics.BrushType.SOLID_COLOR, [0.15, 0.15, 0.15, 1]);
            } catch(e) {}

            var inputField = inputWrapper.add("edittext", undefined, "");
            inputField.alignment = ["fill", "center"];
            inputField.minimumSize = [180, 26];

            var sendBtn = inputWrapper.add("button", undefined, "➤");
            sendBtn.preferredSize.width = 38;
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

                // Add Sender message to RIGHT (Blue bubble)
                addMessage(userMsg, false);
                inputField.text = "";

                // Immediate visual feedback on LEFT (Slate bubble)
                var pendingRow = addMessage("⏳ Thinking & applying in After Effects...", true);

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

                        // Remove pending card
                        try {
                            chatScrollContainer.remove(pendingRow);
                        } catch(e) {}

                        var cleanReply = extractJsonReply(response);
                        if (cleanReply) {
                            addMessage(cleanReply, true);
                        } else {
                            addMessage(response || "Execution finished in active composition.", true);
                        }

                        // Refresh asset tags
                        syncAssets();
                    } else {
                        try { chatScrollContainer.remove(pendingRow); } catch(e) {}
                        addMessage("⚠️ Could not connect to AfterBrain background server on 127.0.0.1:8088.\nPlease ensure python -m src.cli is running in your terminal!", true);
                    }
                } catch(err) {
                    try { chatScrollContainer.remove(pendingRow); } catch(e) {}
                    addMessage("⚠️ Connection error: " + err.toString(), true);
                }

                try { inputField.active = true; } catch(e) {}
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

            syncBtn.onClick = function() {
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
                sendChatMessage("Make " + activeChar + " wave his right hand and bounce up and down");
            };

            chipLip.onClick = function() {
                var activeChar = (assetDropdown.selection && assetDropdown.selection.text.indexOf("@") === 0) ? assetDropdown.selection.text : "@AlienBob";
                sendChatMessage("Lip sync " + activeChar + ": Hello everyone! Welcome to AfterBrain live AI animation!");
            };

            chipClear.onClick = function() {
                resetChat();
                try {
                    inputField.active = true;
                } catch(e) {}
            };

            // Responsive Layout Handling on Width/Height Resize
            win.onResizing = function() {
                this.layout.resize();
                updateScroll();
            };
            win.onResize = function() {
                this.layout.resize();
                updateScroll();
            };

            win.layout.layout(true);
            resetChat();
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
