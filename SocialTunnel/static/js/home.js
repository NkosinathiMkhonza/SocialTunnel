    // The page and API are served by the same Django site.
    const BACKEND_URL = window.location.origin;
    // Remember who the open message conversation is with.
    let activeConversation = "";
    // Track the latest conversation request so slower responses cannot replace a newer selection.
    let conversationRequestId = 0;

    const authForm = document.getElementById("auth-form");
    const authStatus = document.getElementById("auth-status");
    const appStatus = document.getElementById("app-status");

    // Show request results and errors beside the part of the page being used.
    function setStatus(element, message, kind = "") {
      element.textContent = message;
      element.className = `small mt-3${kind ? ` text-${kind}` : ""}`;
    }

    // Read the server's reply and turn unsuccessful replies into visible errors.
    async function readResponse(response) {
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = data.detail || data.error || Object.values(data).flat().join(" ");
        throw new Error(detail || `Request failed (${response.status}).`);
      }
      return data;
    }

    // Send a request to Django and include the saved login token when available.
    async function apiRequest(path, options = {}) {
      const token = localStorage.getItem("access_token");
      const headers = { "Content-Type": "application/json", ...options.headers };
      if (token) headers.Authorization = `Bearer ${token}`;
      const response = await fetch(`${BACKEND_URL}${path}`, { ...options, headers });
      return readResponse(response);
    }

    // Swap the login form for the signed-in area.
    function showDashboard(username = "") {
      document.getElementById("login-section").classList.add("hidden");
      document.getElementById("dashboard-section").classList.remove("hidden");
      document.getElementById("welcome-name").textContent = username || "friend";
    }

    // Return to the login form after logout or when the token is rejected.
    function showLogin() {
      document.getElementById("dashboard-section").classList.add("hidden");
      document.getElementById("login-section").classList.remove("hidden");
    }

    // Check the saved token with a protected endpoint and get the signed-in name.
    async function checkSignedInUser() {
      return apiRequest("/social_pipeline/new-feed/");
    }

    // Fetch active members, update the count, and create one safe button per username.
    async function fetchUserRegistry() {
      // Request the registry from the authenticated API endpoint.
      const registry = await apiRequest("/api/users/");
      // Reject unexpected data instead of showing an incorrect member count.
      if (!Array.isArray(registry.users) || typeof registry.total_user_count !== "number") {
        throw new Error("The active user list response was invalid.");
      }

      // Update the visible count and clear previous member buttons.
      const badge = document.getElementById("user-count-badge");
      const list = document.getElementById("user-registry-list");
      badge.textContent = String(registry.total_user_count);
      list.replaceChildren();

      // Show a helpful empty state when there are no other active members.
      if (registry.users.length === 0) {
        const emptyMessage = document.createElement("div");
        emptyMessage.className = "list-group-item text-secondary";
        emptyMessage.textContent = "No active members are available.";
        list.append(emptyMessage);
        return;
      }

      // Add a button for each member so selecting one opens that conversation.
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

    // Draw the conversation returned by Django; place our messages on the right.
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
        const meta = document.createElement("div");
        meta.className = "small text-secondary mb-1";
        // Un-comment the line below if your model supplies timestamps:
        // meta.textContent = `${message.sender} · ${new Date(message.timestamp).toLocaleString()}`;
        const content = document.createElement("div");
        content.textContent = message.message_text;
        bubble.append(meta, content);
        container.append(bubble);
      }
      container.scrollTop = container.scrollHeight;
    }

    // Ask Django for messages exchanged with the chosen username.
    async function loadConversation(username) {
      // Mark this request as current and disable sending until its messages arrive.
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

      // Request the selected user's conversation and ignore responses for old selections.
      try {
        const data = await apiRequest(`/api/messages/?username=${encodeURIComponent(username)}`);
        if (requestId !== conversationRequestId) return;

        // Enable the channel after a successful response and render its messages.
        activeConversation = data.conversation_with;
        document.getElementById("conversation-label").textContent = `Conversation with ${activeConversation}`;
        document.getElementById("message-text").disabled = false;
        document.getElementById("send-button").disabled = false;
        renderMessages(data.messages, activeConversation);
        setStatus(appStatus, "");
      } catch (error) {
        // Show an error only when this is still the latest selected channel.
        if (requestId !== conversationRequestId) return;
        document.getElementById("conversation-label").textContent =
          `Could not open conversation with ${username}.`;
        throw error;
      }
    }

    // Select a member, update the URL without navigating, and load that channel.
    async function selectUserChatChannel(username) {
      // Ignore empty selections and place the selected username in the chat form.
      const selectedUsername = username.trim();
      if (!selectedUsername) return;
      document.getElementById("recipient").value = selectedUsername;

      // Update only the query parameter; pushState does not reload the dashboard.
      const nextUrl = new URL(window.location.href);
      nextUrl.searchParams.set("username", selectedUsername);
      window.history.pushState({ username: selectedUsername }, "", nextUrl);

      // Load history for the selected channel and let callers display any errors.
      await loadConversation(selectedUsername);
    }

    // Restore a channel from the URL after sign-in or browser back/forward navigation.
    async function loadConversationFromLocation() {
      // Read the current username parameter without changing browser history.
      const username = new URL(window.location.href).searchParams.get("username");
      if (!username) {
        // Invalidate any outstanding request so it cannot reopen an older channel.
        conversationRequestId += 1;
        activeConversation = "";
        document.getElementById("message-text").disabled = true;
        document.getElementById("send-button").disabled = true;
        document.getElementById("conversation-label").textContent =
          "Choose a username to open a conversation.";
        return;
      }

      // Keep the recipient field and message channel synchronized with the URL.
      document.getElementById("recipient").value = username;
      await loadConversation(username);
    }

    // Load the member list and restore a URL-selected conversation after sign-in.
    async function initializeDashboard() {
      // Populate the member panel and report registry errors in the dashboard.
      try {
        await fetchUserRegistry();
      } catch (error) {
        setStatus(appStatus, error.message, "danger");
      }

      // Restore the query-selected conversation independently of registry success.
      try {
        await loadConversationFromLocation();
      } catch (error) {
        setStatus(appStatus, error.message, "danger");
      }
    }

    // Send login details to Django and receive the tokens used by later requests.
    async function authenticate(username, password) {
      return apiRequest("/api/token/", {
        method: "POST",
        body: JSON.stringify({ username, password })
      });
    }

    // Log in, save the returned tokens, and check that the signed-in area is available.
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

    // Create an account first, then log in so the new user can use the dashboard.
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

    // Open the conversation named in the username field and synchronize its URL.
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

    // Send a message to the open conversation and then show the updated history.
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

    // Remove this browser's saved tokens and return to the login form.
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

    // Reload the channel when browser back or forward changes the query parameter.
    window.addEventListener("popstate", async () => {
      // Ignore history changes while the visitor is signed out.
      if (!localStorage.getItem("access_token")) return;
      try {
        await loadConversationFromLocation();
      } catch (error) {
        setStatus(appStatus, error.message, "danger");
      }
    });

    // On a page reload, check a saved token before showing the signed-in area.
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
