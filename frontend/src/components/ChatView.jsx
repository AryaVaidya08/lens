import { useEffect, useState } from "react";
import { formatRelativeTime } from "../utils/relativeTime";

function ChatView({ chat, onSendMessage, onRenameChat }) {
  const [input, setInput] = useState("");

  // Re-render periodically so the relative timestamp ("5 minutes ago") stays fresh.
  const [, setTick] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => setTick((tick) => tick + 1), 30000);
    return () => clearInterval(interval);
  }, []);

  if (!chat) {
    return (
      <section className="empty-state">
        <h3>Select a conversation</h3>
        <p>Choose a past conversation to continue chatting.</p>
      </section>
    );
  }

  const handleSubmit = (event) => {
    event.preventDefault();

    const message = input.trim();

    if (!message) {
      return;
    }

    onSendMessage(chat.id, message);
    setInput("");
  };

  return (
    <section className="chat-view">
      <div className="chat-header">
        <div>
          <span className="eyebrow">Conversation</span>

          <div className="chat-title-row">
            <h3>{chat.title || `${chat.drugName} - ${chat.question}`}</h3>

            <button
              type="button"
              className="rename-chat-button"
              onClick={() => {
                const newTitle = window.prompt(
                  "Rename conversation:",
                  chat.title || chat.drugName
                );

                if (newTitle === null) return;

                const trimmedTitle = newTitle.trim();

                if (!trimmedTitle) return;

                onRenameChat(chat.id, trimmedTitle);
              }}
              title="Rename conversation"
              aria-label="Rename conversation"
            >
              ✏️
            </button>
          </div>
        </div>

        <span className="chat-date">{formatRelativeTime(chat.timestamp)}</span>
      </div>

      <div className="messages">
        {chat.messages.map((message) =>
          message.loading ? (
            <div
              key={message.id}
              className="message assistant"
            >
              <strong>HCP Copilot</strong>

              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          ) : (
            <div
              key={message.id}
              className={`message ${message.role}`}
            >
              <strong>
                {message.role === "user"
                  ? "You"
                  : "HCP Copilot"}
              </strong>

              <p>{message.text}</p>
            </div>
          )
        )}
      </div>

      <form className="chat-input-area" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder={`Ask about ${chat.drugName}...`}
          value={input}
          onChange={(event) => setInput(event.target.value)}
        />

        <button type="submit">
          Send
        </button>
      </form>
    </section>
  );
}

export default ChatView;