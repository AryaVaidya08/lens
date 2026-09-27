import { useState } from "react";

function ChatList({
  chats,
  selectedChat,
  setSelectedChat,
  onDeleteChat,
  onRenameChat,
}) {
  const [search, setSearch] = useState("");
  const [editingChatId, setEditingChatId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");

  const filteredChats = chats.filter((chat) => {
    const query = search.toLowerCase();

    return (
      (chat.title || chat.question).toLowerCase().includes(query) ||
      (chat.drugId || "").toLowerCase().includes(query)
    );
  });

  const startEditing = (event, chat) => {
    event.stopPropagation();

    setEditingChatId(chat.id);
    setEditingTitle(chat.title || chat.question);
  };

  const cancelEditing = () => {
    setEditingChatId(null);
    setEditingTitle("");
  };

  const saveEditing = async (event, chat) => {
    event?.stopPropagation();

    const trimmedTitle = editingTitle.trim();

    if (!trimmedTitle) {
      cancelEditing();
      return;
    }

    if (trimmedTitle === (chat.title || chat.question)) {
      cancelEditing();
      return;
    }

    await onRenameChat(chat.id, trimmedTitle);

    setEditingChatId(null);
    setEditingTitle("");
  };

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
            <div
              key={chat.id}
              className={`list-item ${
                selectedChat?.id === chat.id ? "selected" : ""
              }`}
              onClick={() => {
                if (editingChatId !== chat.id) {
                  setSelectedChat(chat);
                }
              }}
            >
              <div className="list-item-content">
                <div className="list-item-top">
                  {editingChatId === chat.id ? (
                    <div
                      className="chat-title-edit"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <input
                        className="chat-title-input"
                        type="text"
                        value={editingTitle}
                        autoFocus
                        maxLength={100}
                        onChange={(event) =>
                          setEditingTitle(event.target.value)
                        }
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            saveEditing(event, chat);
                          }

                          if (event.key === "Escape") {
                            cancelEditing();
                          }
                        }}
                        onBlur={() => saveEditing(null, chat)}
                      />
                    </div>
                  ) : (
                    <div className="chat-list-title">
                      <strong>{chat.title || chat.question}</strong>

                      <button
                        className="rename-chat-button"
                        onClick={(event) =>
                          startEditing(event, chat)
                        }
                        title="Rename conversation"
                        aria-label="Rename conversation"
                      >
                        ✏️
                      </button>
                    </div>
                  )}

                  <small>{chat.timestamp}</small>
                </div>

                <span>{chat.drugId}</span>
              </div>

              <button
                className="delete-chat-button"
                onClick={(event) => {
                  event.stopPropagation();
                  onDeleteChat(chat.id);
                }}
                title="Delete conversation"
                aria-label="Delete conversation"
              >
                🗑️
              </button>
            </div>
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