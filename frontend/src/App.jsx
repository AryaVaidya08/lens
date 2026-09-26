import { useState } from "react";

import { drugs, chats as initialChats } from "./data/mockData";

import Sidebar from "./components/Sidebar";
import ChatList from "./components/ChatList";
import ChatView from "./components/ChatView";
import DrugList from "./components/DrugList";
import DrugDetails from "./components/DrugDetails";

function App() {
  const [view, setView] = useState("chats");

  const [chats, setChats] = useState(initialChats);

  const [selectedChat, setSelectedChat] = useState(null);
  const [selectedDrug, setSelectedDrug] = useState(null);

  const handleSendMessage = (chatId, text) => {
    const userMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      text,
    };

    const assistantMessage = {
      id: `msg-${Date.now()}-assistant`,
      role: "assistant",
      text:
        "Thanks for your question. This is a mock response for the frontend demo. The production version will use the drug information backend.",
    };

    setChats((currentChats) =>
      currentChats.map((chat) => {
        if (chat.id !== chatId) {
          return chat;
        }

        return {
          ...chat,
          messages: [
            ...chat.messages,
            userMessage,
            assistantMessage,
          ],
          preview: text,
          timestamp: "Just now",
        };
      })
    );

    setSelectedChat((currentChat) => {
      if (!currentChat || currentChat.id !== chatId) {
        return currentChat;
      }

      return {
        ...currentChat,
        messages: [
          ...currentChat.messages,
          userMessage,
          assistantMessage,
        ],
        preview: text,
        timestamp: "Just now",
      };
    });
  };

  return (
    <div className="app">
      <Sidebar
        view={view}
        setView={setView}
      />

      <main className="main-content">
        {view === "chats" && (
          <div className="content-layout">
            <ChatList
              chats={chats}
              selectedChat={selectedChat}
              setSelectedChat={setSelectedChat}
            />

            <ChatView
              chat={selectedChat}
              onSendMessage={handleSendMessage}
            />
          </div>
        )}

        {view === "drugs" && (
          <div className="content-layout">
            <DrugList
              drugs={drugs}
              selectedDrug={selectedDrug}
              setSelectedDrug={setSelectedDrug}
            />

            <DrugDetails drug={selectedDrug} />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;