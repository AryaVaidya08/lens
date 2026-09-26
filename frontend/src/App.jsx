import { useEffect, useState } from "react";
import {
  getChats,
  getDrugSummary,
  askDrugQuestion,
  logEngagement,
  getPatients,
  getPatient,
} from "./api";
import { drugs } from "./data/mockData";
import Sidebar from "./components/Sidebar";
import ChatList from "./components/ChatList";
import ChatView from "./components/ChatView";
import DrugList from "./components/DrugList";
import DrugDetails from "./components/DrugDetails";
import Login from "./components/Login";
import PatientList from "./components/PatientList";
import PatientDetails from "./components/PatientDetails";

function App() {
  const [hcpId, setHcpId] = useState(() =>
    localStorage.getItem("lens_hcp_id")
  );

  const [view, setView] = useState("chats");

  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [loadingPatients, setLoadingPatients] = useState(false);

  const [chats, setChats] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);

  const [selectedDrug, setSelectedDrug] = useState(null);
  const [drugSummary, setDrugSummary] = useState(null);

  const [loading, setLoading] = useState(false);
  const [loadingDrug, setLoadingDrug] = useState(false);

  const [error, setError] = useState(null);

  function handleLogin(profile) {
    setHcpId(profile.hcp_id);
    setError(null);
  }

  function handleLogout() {
    localStorage.removeItem("lens_session_token");
    localStorage.removeItem("lens_hcp_id");
    sessionStorage.removeItem("lens_active_patient");

    setHcpId(null);
    setChats([]);
    setSelectedChat(null);
    setSelectedDrug(null);
    setPatients([]);
    setSelectedPatient(null);
  }

  useEffect(() => {
    if (!hcpId) return;

    async function loadChats() {
      setLoading(true);
      setError(null);

      try {
        const data = await getChats(hcpId);

        const formattedChats = data.map((chat) => ({
          id: chat.id,
          drugId: chat.drug_id,
          drugName:
            drugs.find((drug) => drug.id === chat.drug_id)?.name ||
            chat.drug_id,
          timestamp: chat.asked_at
            ? new Date(chat.asked_at).toLocaleString()
            : "",
          preview: chat.question,
          messages: [
            {
              id: `${chat.id}-user`,
              role: "user",
              text: chat.question,
            },
            {
              id: `${chat.id}-assistant`,
              role: "assistant",
              text: chat.answer,
            },
          ],
        }));

        setChats(formattedChats);
      } catch (err) {
        console.error("Failed to load chats:", err);

        if (err.message.includes("401")) {
          handleLogout();
        } else {
          setError(`Failed to load chats: ${err.message}`);
        }
      } finally {
        setLoading(false);
      }
    }

    loadChats();
  }, [hcpId]);

  useEffect(() => {
    if (!hcpId) return;

    async function loadPatients() {
      setLoadingPatients(true);
      setError(null);

      try {
        const data = await getPatients(hcpId);
        setPatients(data.patients || []);
      } catch (err) {
        console.error("Failed to load patients:", err);

        if (err.message.includes("401")) {
          handleLogout();
        } else {
          setError(`Failed to load patients: ${err.message}`);
        }
      } finally {
        setLoadingPatients(false);
      }
    }

    loadPatients();
  }, [hcpId]);

  useEffect(() => {
    if (!selectedDrug || !hcpId) {
      setDrugSummary(null);
      return;
    }

    async function loadDrug() {
      setLoadingDrug(true);
      setError(null);

      try {
        const summary = await getDrugSummary(selectedDrug.id, hcpId);
        setDrugSummary(summary);
        await logEngagement(hcpId, selectedDrug.id);
      } catch (err) {
        console.error("Failed to load drug:", err);
        setError(err.message);
      } finally {
        setLoadingDrug(false);
      }
    }

    loadDrug();
  }, [selectedDrug, hcpId]);

  async function handleSendMessage(chatId, text) {
    const chat = chats.find((item) => item.id === chatId);

    if (!chat || !hcpId) return;

    const userMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      text,
    };

    setChats((currentChats) =>
      currentChats.map((item) =>
        item.id === chatId
          ? {
              ...item,
              messages: [...item.messages, userMessage],
              preview: text,
              timestamp: "Just now",
            }
          : item
      )
    );

    setSelectedChat((currentChat) =>
      currentChat?.id === chatId
        ? {
            ...currentChat,
            messages: [...currentChat.messages, userMessage],
            preview: text,
            timestamp: "Just now",
          }
        : currentChat
    );

    try {
      const response = await askDrugQuestion(chat.drugId, hcpId, text);

      const assistantMessage = {
        id: `msg-${Date.now()}-assistant`,
        role: "assistant",
        text: response.answer_text,
      };

      setChats((currentChats) =>
        currentChats.map((item) =>
          item.id === chatId
            ? {
                ...item,
                messages: [...item.messages, assistantMessage],
              }
            : item
        )
      );

      setSelectedChat((currentChat) =>
        currentChat?.id === chatId
          ? {
              ...currentChat,
              messages: [...currentChat.messages, assistantMessage],
            }
          : currentChat
      );
    } catch (err) {
      console.error("Failed to answer question:", err);

      const errorMessage = {
        id: `msg-${Date.now()}-error`,
        role: "assistant",
        text: `Sorry, I couldn't get an answer: ${err.message}`,
      };

      setSelectedChat((currentChat) =>
        currentChat?.id === chatId
          ? {
              ...currentChat,
              messages: [...currentChat.messages, errorMessage],
            }
          : currentChat
      );
    }
  }

  if (!hcpId) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="app">
      <Sidebar
        view={view}
        setView={setView}
        onLogout={handleLogout}
      />

      <main className="main-content">
        {error && <div className="error-banner">{error}</div>}

        {view === "chats" && (
          <div className="content-layout">
            <ChatList
              chats={chats}
              selectedChat={selectedChat}
              setSelectedChat={setSelectedChat}
              loading={loading}
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

            <DrugDetails
              drug={selectedDrug}
              summary={drugSummary}
              loading={loadingDrug}
              error={error}
            />
          </div>
        )}

        {view === "patients" && (
          <div className="content-layout">
            <PatientList
              patients={patients}
              selectedPatient={selectedPatient}
              onSelect={setSelectedPatient}
            />

            <PatientDetails
              patient={selectedPatient}
              loading={loadingPatients}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;