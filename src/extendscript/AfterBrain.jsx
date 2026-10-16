// AfterBrain.jsx - Windows Copilot Chat UI for Adobe After Effects
// Features: AI on Left side, Sender (User) on Right side, native ScriptUI cards,
// auto-scrolling, zero cursor/selection bugs, and deep After Effects composition control.

(function(thisObj) {
    // Close existing standalone palette window if already open to prevent duplicate stacking
    if ($.global.afterBrainPalette && $.global.afterBrainPalette instanceof Window) {
        try { $.global.afterBrainPalette.close(); } catch(e) {}
    }

    function buildUI(thisObj) {
        var win = (thisObj instanceof Panel) ? thisObj : new Window("palette", "Copilot - Motion AI", undefined, {resizeable: true});
        if (win !== null) {
            win.orientation = "column";
            win.alignChildren = ["fill", "fill"];
            win.spacing = 6;
            win.margins = 8;

            // 1. Windows Copilot Header Bar
            var header = win.add("group");
            header.orientation = "row";
            header.alignment = ["fill", "top"];
            header.spacing = 6;

            var copilotTitle = header.add("statictext", undefined, "✦ Copilot");
            try {
                copilotTitle.graphics.font = ScriptUI.newFont("Segoe UI", "BOLD", 14);
                copilotTitle.graphics.foregroundColor = copilotTitle.graphics.newPen(copilotTitle.graphics.PenType.SOLID_COLOR, [0.15, 0.55, 0.95, 1], 1);
            } catch(e) {
                try {
                    copilotTitle.graphics.font = ScriptUI.newFont("Arial", "BOLD", 13);
                } catch(e2) {}
            }

            var subTitle = header.add("statictext", undefined, "Motion AI");
            try {
                subTitle.graphics.font = ScriptUI.newFont("Segoe UI", "REGULAR", 10);
            } catch(e) {}

            var statusTxt = header.add("statictext", undefined, "● Online (qwen3:8b)");
            statusTxt.alignment = ["right", "center"];
            try {
                statusTxt.graphics.font = ScriptUI.newFont("Segoe UI", "REGULAR", 10);
                statusTxt.graphics.foregroundColor = statusTxt.graphics.newPen(statusTxt.graphics.PenType.SOLID_COLOR, [0.2, 0.8, 0.4, 1], 1);
            } catch(e) {}

            // 2. Active Layer / Project Asset Context Bar
            var assetGroup = win.add("group");
            assetGroup.orientation = "row";
            assetGroup.alignment = ["fill", "top"];
            assetGroup.spacing = 4;

            var assetLbl = assetGroup.add("statictext", undefined, "Layer Context:");
            try {
                assetLbl.graphics.font = ScriptUI.newFont("Segoe UI", "REGULAR", 10);
            } catch(e) {}

            var assetDropdown = assetGroup.add("dropdownlist", undefined, ["(Click 'Scan' to list project layers)"]);
            assetDropdown.alignment = ["fill", "center"];
            assetDropdown.selection = 0;

            var refreshBtn = assetGroup.add("button", undefined, "↻ Sync");
            refreshBtn.preferredSize.width = 50;

            // 3. Copilot Chat Viewport (AI on Left, Sender on Right)
            var chatViewport = win.add("group");
            chatViewport.orientation = "row";
            chatViewport.alignment = ["fill", "fill"];
            chatViewport.spacing = 2;

            var chatScrollContainer = chatViewport.add("group");
            chatScrollContainer.orientation = "column";
            chatScrollContainer.alignment = ["fill", "fill"];
            chatScrollContainer.alignChildren = ["fill", "top"];
            chatScrollContainer.spacing = 8;

            var scrollbar = chatViewport.add("scrollbar");
            scrollbar.alignment = ["right", "fill"];
            scrollbar.preferredSize.width = 14;
            scrollbar.visible = false;

            function getTimeString() {
                var d = new Date();
                var h = (d.getHours() < 10 ? "0" : "") + d.getHours();
                var m = (d.getMinutes() < 10 ? "0" : "") + d.getMinutes();
                return h + ":" + m;
            }

            function updateScroll() {
                try {
                    win.layout.layout(true);
                    var contentHeight = (chatScrollContainer.preferredSize && chatScrollContainer.preferredSize.height) ? chatScrollContainer.preferredSize.height : 0;
                    var viewHeight = 250;
                    try {
                        if (chatViewport.size && chatViewport.size.height > 0) {
                            viewHeight = chatViewport.size.height;
                        } else if (win.size && win.size.height > 0) {
                            viewHeight = win.size.height - 180;
                        }
                    } catch(e) {}

                    if (contentHeight > viewHeight && viewHeight > 0) {
                        scrollbar.visible = true;
                        scrollbar.minvalue = 0;
                        scrollbar.maxvalue = Math.max(0, contentHeight - viewHeight + 20);
                        scrollbar.value = scrollbar.maxvalue; // auto scroll to newest message
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

            // Add Copilot chat card (AI on LEFT, Sender on RIGHT)
            function addMessage(sender, text, isAi) {
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
                var maxBubbleW = Math.max(160, Math.floor(availWidth * 0.82));

                if (isAi) {
                    // AI Copilot message aligned to the LEFT
                    row.alignChildren = ["left", "top"];

                    var aiCard = row.add("panel", undefined, "");
                    aiCard.orientation = "column";
                    aiCard.alignChildren = ["left", "top"];
                    aiCard.margins = [10, 6, 10, 8];
                    aiCard.spacing = 3;
                    aiCard.maximumSize.width = maxBubbleW;

                    var aiHeader = aiCard.add("statictext", undefined, "✦ Copilot 🤖  " + getTimeString());
                    try {
                        aiHeader.graphics.font = ScriptUI.newFont("Segoe UI", "BOLD", 10);
                        aiHeader.graphics.foregroundColor = aiHeader.graphics.newPen(aiHeader.graphics.PenType.SOLID_COLOR, [0.2, 0.6, 1.0, 1], 1);
                    } catch(e) {}

                    var lines = text.split("\n");
                    for (var i = 0; i < lines.length; i++) {
                        var l = lines[i].replace(/^\s+|\s+$/g, "");
                        if (l.length > 0) {
                            var aiLine = aiCard.add("statictext", undefined, l, {multiline: true});
                            aiLine.maximumSize.width = maxBubbleW - 20;
                        }
                    }
                } else {
                    // Sender / User message aligned to the RIGHT
                    row.alignChildren = ["right", "top"];

                    var userCard = row.add("panel", undefined, "");
                    userCard.orientation = "column";
                    userCard.alignChildren = ["right", "top"];
                    userCard.margins = [10, 6, 10, 8];
                    userCard.spacing = 3;
                    userCard.maximumSize.width = maxBubbleW;

                    var userHeader = userCard.add("statictext", undefined, "You 👤  " + getTimeString());
                    try {
                        userHeader.graphics.font = ScriptUI.newFont("Segoe UI", "BOLD", 10);
                        userHeader.graphics.foregroundColor = userHeader.graphics.newPen(userHeader.graphics.PenType.SOLID_COLOR, [0.3, 0.85, 0.6, 1], 1);
                    } catch(e) {}

                    var uLines = text.split("\n");
                    for (var j = 0; j < uLines.length; j++) {
                        var ul = uLines[j].replace(/^\s+|\s+$/g, "");
                        if (ul.length > 0) {
                            var userLine = userCard.add("statictext", undefined, ul, {multiline: true});
                            userLine.maximumSize.width = maxBubbleW - 20;
                        }
                    }
                }

                updateScroll();

                try {
                    app.redraw();
                } catch(e) {}

                return row;
            }

            // Initial Copilot Welcome Card on the LEFT
            function resetChat() {
                while (chatScrollContainer.children.length > 0) {
                    chatScrollContainer.remove(chatScrollContainer.children[0]);
                }
                addMessage("✦ Copilot", "Welcome to AfterBrain Copilot! I have direct control over your After Effects composition.\n\n" +
                    "• Animate backgrounds: 'Animate bg_tinku_garden with cinematic slow zoom'\n" +
                    "• Animate characters: 'Make @AlienBob wave and jump'\n" +
                    "• Control cameras & typography with natural language.", true);
            }

            // 4. Copilot Suggestion Action Chips
            var chipsGroup = win.add("group");
            chipsGroup.orientation = "row";
            chipsGroup.alignment = ["fill", "bottom"];
            chipsGroup.spacing = 4;

            var chipScan = chipsGroup.add("button", undefined, "🔍 Scan");
            var chipTag = chipsGroup.add("button", undefined, "🏷️ Tag");
            var chipWave = chipsGroup.add("button", undefined, "👋 Wave");
            var chipLip = chipsGroup.add("button", undefined, "🗣️ Lip-Sync");
            var chipClear = chipsGroup.add("button", undefined, "🧹 New Topic");

            // 5. Copilot Input Bar & Send Button
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

                // Add Sender message to RIGHT
                addMessage("You", userMsg, false);
                inputField.text = "";

                // Immediate visual feedback on LEFT
                var pendingRow = addMessage("✦ Copilot", "⏳ Thinking & applying in After Effects...", true);

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
                            addMessage("✦ Copilot", cleanReply, true);
                        } else {
                            addMessage("✦ Copilot", response || "Execution finished in active composition.", true);
                        }

                        // Refresh asset tags
                        syncAssets();
                    } else {
                        try { chatScrollContainer.remove(pendingRow); } catch(e) {}
                        addMessage("✦ Copilot", "⚠️ Could not connect to AfterBrain background server on 127.0.0.1:8088.\n" +
                            "Please ensure python -m src.cli is running in your terminal!", true);
                    }
                } catch(err) {
                    try { chatScrollContainer.remove(pendingRow); } catch(e) {}
                    addMessage("✦ Copilot", "⚠️ Connection error: " + err.toString(), true);
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
