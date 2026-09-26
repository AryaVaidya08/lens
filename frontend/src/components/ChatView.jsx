function ChatView({ chat }) {
  if (!chat) {
    return (
      <section className="empty-state">
        <h3>Select a conversation</h3>
        <p>Choose a past conversation to view the interaction.</p>
      </section>
    );
  }

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
    </section>
  );
}

export default ChatView;