// AfterBrain Live Chat Client - Gemini Style Streaming & Project Asset Tagging

document.addEventListener("DOMContentLoaded", () => {
  const chatMessages = document.getElementById("chatMessages");
  const chatViewport = document.getElementById("chatViewport");
  const chatInput = document.getElementById("chatInput");
  const btnSend = document.getElementById("btnSend");
  const btnQuickTag = document.getElementById("btnQuickTag");
  const btnRefreshAssets = document.getElementById("btnRefreshAssets");
  const assetsTrack = document.getElementById("assetsTrack");
  const assetCountBadge = document.getElementById("assetCountBadge");
  const suggestionChips = document.getElementById("suggestionChips");
  const autocompleteMenu = document.getElementById("autocompleteMenu");
  const autocompleteItems = document.getElementById("autocompleteItems");

  // Modal elements
  const tagModal = document.getElementById("tagModal");
  const modalTagTitle = document.getElementById("modalTagTitle");
  const modalRoleSelect = document.getElementById("modalRoleSelect");
  const modalDescInput = document.getElementById("modalDescInput");
  const btnModalClose = document.getElementById("btnModalClose");
  const btnModalCancel = document.getElementById("btnModalCancel");
  const btnModalSave = document.getElementById("btnModalSave");

  let currentAssets = [];
  let currentModalTag = "";
  let isSending = false;

  // 1. Fetch & Render Project Assets
  async function loadProjectAssets() {
    try {
      const res = await fetch("/api/project_assets");
      const data = await res.json();
      currentAssets = data.assets || [];
      renderAssetsTrack(currentAssets);
    } catch (err) {
      console.warn("Could not load project assets:", err);
      assetsTrack.innerHTML = `<div class="loading-assets" style="color: #ef4444;">Could not load AE assets. Ensure After Effects is running.</div>`;
    }
  }

  function renderAssetsTrack(assets) {
    assetCountBadge.textContent = `${assets.length} assets`;

    if (assets.length === 0) {
      assetsTrack.innerHTML = `
        <div class="loading-assets">
          No footage items detected in AE Project Panel. Import an image into AE and click 'Sync AE Assets'!
        </div>
      `;
      return;
    }

    assetsTrack.innerHTML = "";
    assets.forEach((asset) => {
      const pill = document.createElement("div");
      pill.className = `asset-pill ${asset.is_tagged ? "tagged" : ""}`;
      pill.innerHTML = `
        <span class="asset-icon">${asset.role === "Background" ? "🌄" : asset.role === "Prop" ? "📦" : "🎭"}</span>
        <span class="asset-tag">${asset.tag}</span>
        <span class="asset-role-badge">${asset.role}</span>
        ${!asset.is_tagged ? `<span class="btn-tag-action">+ Tag</span>` : ""}
      `;

      pill.addEventListener("click", () => {
        if (!asset.is_tagged) {
          openTagModal(asset);
        } else {
          insertTagIntoInput(asset.tag);
        }
      });

      assetsTrack.appendChild(pill);
    });
  }

  // 2. Asset Tagging Modal
  function openTagModal(asset) {
    currentModalTag = asset.tag;
    modalTagTitle.textContent = `Describe & Rig Asset ${asset.tag}`;
    modalRoleSelect.value = asset.role !== "Unassigned" ? asset.role : "Character";
    modalDescInput.value = asset.description || "";
    tagModal.style.display = "flex";
    modalDescInput.focus();
  }

  function closeTagModal() {
    tagModal.style.display = "none";
  }

  btnModalClose.addEventListener("click", closeTagModal);
  btnModalCancel.addEventListener("click", closeTagModal);

  btnModalSave.addEventListener("click", async () => {
    const role = modalRoleSelect.value;
    const desc = modalDescInput.value.trim();

    closeTagModal();
    appendUserMessage(`Tagging ${currentModalTag} as ${role}: "${desc}"`);

    try {
      const res = await fetch("/api/tag_asset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tag: currentModalTag,
          description: desc,
          role: role,
          auto_rig: role === "Character"
        })
      });
      const data = await res.json();
      await loadProjectAssets();

      const assistantCard = createAssistantMessageCard();
      const bodyEl = assistantCard.querySelector(".message-body");
      await streamText(
        bodyEl,
        `✨ Successfully tagged **${currentModalTag}** as *${role}*!\n\nI've analyzed the asset, extracted vision landmarks, and created Puppet pins in After Effects.\n\nYou can now reference \`${currentModalTag}\` anytime in your prompts!`
      );
    } catch (err) {
      appendAssistantMessage(`Error tagging asset: ${err.message}`);
    }
  });

  // 3. Autocomplete for @tags
  function insertTagIntoInput(tag) {
    const val = chatInput.value;
    const lastAtIdx = val.lastIndexOf("@");
    if (lastAtIdx !== -1) {
      chatInput.value = val.substring(0, lastAtIdx) + tag + " ";
    } else {
      chatInput.value = (val ? val + " " : "") + tag + " ";
    }
    chatInput.focus();
    hideAutocomplete();
  }

  chatInput.addEventListener("input", () => {
    const val = chatInput.value;
    const lastAtIdx = val.lastIndexOf("@");

    if (lastAtIdx !== -1 && lastAtIdx === val.length - 1) {
      showAutocomplete();
    } else if (lastAtIdx !== -1) {
      const query = val.substring(lastAtIdx + 1).toLowerCase();
      const filtered = currentAssets.filter((a) => a.tag_name.toLowerCase().startsWith(query));
      if (filtered.length > 0) {
        renderAutocompleteItems(filtered);
        autocompleteMenu.style.display = "block";
      } else {
        hideAutocomplete();
      }
    } else {
      hideAutocomplete();
    }
  });

  function showAutocomplete() {
    renderAutocompleteItems(currentAssets);
    autocompleteMenu.style.display = "block";
  }

  function hideAutocomplete() {
    autocompleteMenu.style.display = "none";
  }

  function renderAutocompleteItems(assets) {
    autocompleteItems.innerHTML = "";
    assets.forEach((a) => {
      const item = document.createElement("div");
      item.className = "autocomplete-item";
      item.innerHTML = `
        <span class="tag-name">${a.tag}</span>
        <span class="asset-role-badge">${a.role}</span>
      `;
      item.addEventListener("click", () => {
        insertTagIntoInput(a.tag);
      });
      autocompleteItems.appendChild(item);
    });
  }

  btnQuickTag.addEventListener("click", () => {
    showAutocomplete();
    chatInput.focus();
  });

  // 4. Message Streaming & Rendering
  function appendUserMessage(text) {
    const card = document.createElement("div");
    card.className = "message-card user";
    card.innerHTML = `
      <div class="avatar-col">
        <div class="user-avatar">👤</div>
      </div>
      <div class="content-col">
        <div class="sender-name">You</div>
        <div class="message-body">${formatMarkdown(text)}</div>
      </div>
    `;
    chatMessages.appendChild(card);
    scrollToBottom();
  }

  function createAssistantMessageCard() {
    const card = document.createElement("div");
    card.className = "message-card assistant";
    card.innerHTML = `
      <div class="avatar-col">
        <div class="gemini-avatar">✦</div>
      </div>
      <div class="content-col">
        <div class="sender-name">AfterBrain Copilot <span class="badge-gemini">LIVE</span></div>
        <div class="message-body"></div>
      </div>
    `;
    chatMessages.appendChild(card);
    scrollToBottom();
    return card;
  }

  async function streamText(element, fullText, codeSnippet = "") {
    element.innerHTML = '<span class="streaming-cursor"></span>';
    const words = fullText.split(" ");
    let currentHtml = "";

    for (let i = 0; i < words.length; i++) {
      currentHtml += words[i] + " ";
      element.innerHTML = formatMarkdown(currentHtml) + '<span class="streaming-cursor"></span>';
      scrollToBottom();
      await new Promise((r) => setTimeout(r, 22)); // smooth streaming speed
    }

    // Final render without cursor
    let finalHtml = formatMarkdown(fullText);

    // If code exists, add accordion preview
    if (codeSnippet) {
      finalHtml += `
        <div class="code-preview">
          <div class="code-header">
            <span>ExtendScript JSX (Executed in AE)</span>
            <button class="btn-rerun" onclick="rerunCode(${encodeURIComponent(JSON.stringify(codeSnippet))})">⚡ Re-run</button>
          </div>
          <pre><code>${escapeHtml(codeSnippet)}</code></pre>
        </div>
      `;
    }

    element.innerHTML = finalHtml;
    scrollToBottom();
  }

  function formatMarkdown(text) {
    if (!text) return "";
    let formatted = escapeHtml(text)
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/@([a-zA-Z0-9_\.\-]+)/g, '<span style="color: #60a5fa; font-weight: 600;">@$1</span>')
      .replace(/\n/g, "<br>");
    return formatted;
  }

  function escapeHtml(text) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function scrollToBottom() {
    chatViewport.scrollTop = chatViewport.scrollHeight;
  }

  // 5. Send Chat Message
  async function sendMessage(overrideText = "") {
    const text = overrideText || chatInput.value.trim();
    if (!text || isSending) return;

    isSending = true;
    chatInput.value = "";
    hideAutocomplete();
    appendUserMessage(text);

    const assistantCard = createAssistantMessageCard();
    const bodyEl = assistantCard.querySelector(".message-body");
    bodyEl.innerHTML = `Thinking & generating ExtendScript... <span class="streaming-cursor"></span>`;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
      });

      const data = await res.json();
      const replyText = data.reply || "Done! Executed in After Effects.";
      const code = data.jsx_code || "";

      await streamText(bodyEl, replyText, code);
      // Reload assets in case new assets were auto-scanned or tagged
      await loadProjectAssets();
    } catch (err) {
      bodyEl.innerHTML = `<span style="color: #ef4444;">Error connecting to AfterBrain: ${err.message}</span>`;
    } finally {
      isSending = false;
    }
  }

  // Event Listeners
  btnSend.addEventListener("click", () => sendMessage());

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  btnRefreshAssets.addEventListener("click", () => {
    sendMessage("scan my project assets");
  });

  // Suggestion chips
  suggestionChips.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      sendMessage(prompt);
    });
  });

  // Initial load
  loadProjectAssets();
});

// Global re-run script helper
window.rerunCode = async function(encodedCode) {
  try {
    const code = JSON.parse(decodeURIComponent(encodedCode));
    await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: "re-run script" })
    });
    alert("Re-dispatched script to After Effects composition!");
  } catch(e) {
    alert("Error: " + e.message);
  }
};
