    const BACKEND_URL = window.location.origin;
    let activeConversation = "";
    let conversationRequestId = 0;

    const authForm = document.getElementById("auth-form");
    const authStatus = document.getElementById("auth-status");
    const appStatus = document.getElementById("app-status");

    function setStatus(element, message, kind = "") {
      element.textContent = message;
      element.className = `small mt-3${kind ? ` text-${kind}` : ""}`;
    }

    async function readResponse(response) {
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = data.detail || data.error || Object.values(data).flat().join(" ");
        throw new Error(detail || `Request failed (${response.status}).`);
      }
      return data;
    }

    async function apiRequest(path, options = {}) {
      const token = localStorage.getItem("access_token");
      const headers = { "Content-Type": "application/json", ...options.headers };
      if (token) headers.Authorization = `Bearer ${token}`;
      const response = await fetch(`${BACKEND_URL}${path}`, { ...options, headers });
      return readResponse(response);
    }

    function showDashboard(username = "") {
      document.getElementById("login-section").classList.add("hidden");
      document.getElementById("dashboard-section").classList.remove("hidden");
      document.getElementById("welcome-name").textContent = username || "friend";
    }

    function showLogin() {
      document.getElementById("dashboard-section").classList.add("hidden");
      document.getElementById("login-section").classList.remove("hidden");
    }

    async function checkSignedInUser() {
      return apiRequest("/social_pipeline/new-feed/");
    }

    async function fetchUserRegistry() {
      const registry = await apiRequest("/api/users/");
      if (!Array.isArray(registry.users) || typeof registry.total_user_count !== "number") {
        throw new Error("The active user list response was invalid.");
      }

      const badge = document.getElementById("user-count-badge");
      const list = document.getElementById("user-registry-list");
      badge.textContent = String(registry.total_user_count);
      list.replaceChildren();

      if (registry.users.length === 0) {
        const emptyMessage = document.createElement("div");
        emptyMessage.className = "list-group-item text-secondary";
        emptyMessage.textContent = "No active members are available.";
        list.append(emptyMessage);
        return;
      }

      for (const user of registry.users) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "list-group-item list-group-item-action";
        button.textContent = user.username;
        button.addEventListener("click", async () => {
          try {
            await selectUserChatChannel(user.username);
          } catch (error) {
            setStatus(appStatus, error.message, "danger");
          }
        });
        list.append(button);
      }
    }

    function renderMessages(messages, username) {
      const container = document.getElementById("messages");
      container.replaceChildren();
      if (!messages.length) {
        const empty = document.createElement("p");
        empty.className = "small text-secondary mb-0";
        empty.textContent = `No messages with ${username} yet.`;
        container.append(empty);
        return;
      }

      for (const message of messages) {
        const bubble = document.createElement("div");
        bubble.className = `message-bubble border rounded p-2 mb-2${message.is_mine ? " message-mine" : ""}`;
        const content = document.createElement("div");
        content.textContent = message.message_text;
        bubble.append(content);
        container.append(bubble);
      }
      container.scrollTop = container.scrollHeight;
    }

    async function loadConversation(username) {
      const requestId = ++conversationRequestId;
      activeConversation = "";
      document.getElementById("message-text").disabled = true;
      document.getElementById("send-button").disabled = true;
      document.getElementById("conversation-label").textContent = `Loading conversation with ${username}…`;
      const messageList = document.getElementById("messages");
      messageList.replaceChildren();
      const loadingMessage = document.createElement("p");
      loadingMessage.className = "small text-secondary mb-0";
      loadingMessage.textContent = "Loading messages…";
      messageList.append(loadingMessage);

      try {
        const data = await apiRequest(`/api/messages/?username=${encodeURIComponent(username)}`);
        if (requestId !== conversationRequestId) return;

        activeConversation = data.conversation_with;
        document.getElementById("conversation-label").textContent = `Conversation with ${activeConversation}`;
        document.getElementById("message-text").disabled = false;
        document.getElementById("send-button").disabled = false;
        renderMessages(data.messages, activeConversation);
        setStatus(appStatus, "");
      } catch (error) {
        if (requestId !== conversationRequestId) return;
        document.getElementById("conversation-label").textContent =
          `Could not open conversation with ${username}.`;
        throw error;
      }
    }

    async function selectUserChatChannel(username) {
      const selectedUsername = username.trim();
      if (!selectedUsername) return;
      document.getElementById("recipient").value = selectedUsername;

      const nextUrl = new URL(window.location.href);
      nextUrl.searchParams.set("username", selectedUsername);
      window.history.pushState({ username: selectedUsername }, "", nextUrl);

      await loadConversation(selectedUsername);
    }

    async function loadConversationFromLocation() {
      const username = new URL(window.location.href).searchParams.get("username");
      if (!username) {
        conversationRequestId += 1;
        activeConversation = "";
        document.getElementById("message-text").disabled = true;
        document.getElementById("send-button").disabled = true;
        document.getElementById("conversation-label").textContent =
          "Choose a username to open a conversation.";
        return;
      }

      document.getElementById("recipient").value = username;
      await loadConversation(username);
    }

    async function initializeDashboard() {
      try {
        await fetchUserRegistry();
      } catch (error) {
        setStatus(appStatus, error.message, "danger");
      }

      try {
        await loadConversationFromLocation();
      } catch (error) {
        setStatus(appStatus, error.message, "danger");
      }
    }

    async function authenticate(username, password) {
      return apiRequest("/api/token/", {
        method: "POST",
        body: JSON.stringify({ username, password })
      });
    }

    authForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const username = document.getElementById("username").value.trim();
      const password = document.getElementById("password").value;
      setStatus(authStatus, "Signing in…");
      try {
        const tokens = await authenticate(username, password);
        localStorage.setItem("access_token", tokens.access);
        localStorage.setItem("refresh_token", tokens.refresh);
        const account = await checkSignedInUser();
        showDashboard(account.current_user || username);
        await initializeDashboard();
        setStatus(authStatus, "");
      } catch (error) {
        setStatus(authStatus, error.message, "danger");
      }
    });

    document.getElementById("signup-button").addEventListener("click", async () => {
      const username = document.getElementById("username").value.trim();
      const password = document.getElementById("password").value;
      if (!username || !password) {
        setStatus(authStatus, "Enter a username and password to create an account.", "danger");
        return;
      }
      setStatus(authStatus, "Creating account…");
      try {
        await apiRequest("/api/register/", {
          method: "POST",
          body: JSON.stringify({ username, password })
        });
        const tokens = await authenticate(username, password);
        localStorage.setItem("access_token", tokens.access);
        localStorage.setItem("refresh_token", tokens.refresh);
        const account = await checkSignedInUser();
        showDashboard(account.current_user || username);
        await initializeDashboard();
        setStatus(authStatus, "");
      } catch (error) {
        setStatus(authStatus, error.message, "danger");
      }
    });

    document.getElementById("conversation-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const username = document.getElementById("recipient").value.trim();
      if (!username) return;
      try {
        await selectUserChatChannel(username);
      } catch (error) {
        setStatus(appStatus, error.message, "danger");
      }
    });

    document.getElementById("message-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const field = document.getElementById("message-text");
      const message = field.value.trim();
      if (!activeConversation || !message) return;
      const button = document.getElementById("send-button");
      button.disabled = true;
      try {
        await apiRequest("/api/messages/", {
          method: "POST",
          body: JSON.stringify({ recipient: activeConversation, message })
        });
        field.value = "";
        await loadConversation(activeConversation);
        setStatus(appStatus, "Message sent.", "success");
      } catch (error) {
        setStatus(appStatus, error.message, "danger");
      } finally {
        button.disabled = false;
      }
    });

    document.getElementById("logout-button").addEventListener("click", () => {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      activeConversation = "";
      conversationRequestId += 1;
      const nextUrl = new URL(window.location.href);
      nextUrl.searchParams.delete("username");
      window.history.replaceState({}, "", nextUrl);
      showLogin();
      setStatus(authStatus, "You have been logged out.", "success");
    });

    window.addEventListener("popstate", async () => {
      if (!localStorage.getItem("access_token")) return;
      try {
        await loadConversationFromLocation();
      } catch (error) {
        setStatus(appStatus, error.message, "danger");
      }
    });

    window.addEventListener("DOMContentLoaded", async () => {
      if (!localStorage.getItem("access_token")) return;
      try {
        const account = await checkSignedInUser();
        showDashboard(account.current_user);
        await initializeDashboard();
      } catch (error) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        showLogin();
      }
    });
