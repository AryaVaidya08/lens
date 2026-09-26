import { useState } from "react";

function ChatList({ chats, selectedChat, setSelectedChat }) {
  const [search, setSearch] = useState("");

  const filteredChats = chats.filter((chat) => {
    const query = search.toLowerCase();

    return (
      chat.drugName.toLowerCase().includes(query) ||
      chat.preview.toLowerCase().includes(query)
    );
  });

  return (
    <div className="list-panel">
      <div className="panel-header">
        <div>
          <h2>Past Chats</h2>
          <p>{chats.length} conversations</p>
        </div>
      </div>

      <input
        className="search-input"
        type="text"
        placeholder="Search conversations..."
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />

      <div className="list">
        {filteredChats.length > 0 ? (
          filteredChats.map((chat) => (
            <button
              key={chat.id}
              onClick={() => setSelectedChat(chat)}
              className={`list-item ${
                selectedChat?.id === chat.id ? "selected" : ""
              }`}
            >
              <div className="list-item-top">
                <strong>{chat.drugName}</strong>
                <small>{chat.timestamp}</small>
              </div>

              <span>{chat.preview}</span>
            </button>
          ))
        ) : (
          <div className="list-empty">
            <strong>No conversations found</strong>
            <span>Try a different search.</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default ChatList;