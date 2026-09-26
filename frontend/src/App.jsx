import { useState } from "react";

import { drugs, chats } from "./data/mockData";

import Sidebar from "./components/Sidebar";
import ChatList from "./components/ChatList";
import ChatView from "./components/ChatView";
import DrugList from "./components/DrugList";
import DrugDetails from "./components/DrugDetails";

function App() {
  const [view, setView] = useState("chats");
  const [selectedChat, setSelectedChat] = useState(null);
  const [selectedDrug, setSelectedDrug] = useState(null);

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

            <ChatView chat={selectedChat} />
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