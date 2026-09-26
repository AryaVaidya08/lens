import { useState } from "react";

function ChatView({ chat, onSendMessage }) {
  const [input, setInput] = useState("");

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
          <h3>{chat.drugName}</h3>
        </div>

        <span className="chat-date">{chat.timestamp}</span>
      </div>

      <div className="messages">
        {chat.messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.role}`}
          >
            <strong>
              {message.role === "user" ? "You" : "Copilot"}
            </strong>

            <p>{message.text}</p>
          </div>
        ))}
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