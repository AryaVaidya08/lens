import { useEffect, useState } from "react";
import {
  getChats,
  deleteChat,
  renameChat,
  getDrugSummary,
  askDrugQuestion,
  logEngagement,
  getPatients,
  getProfile,
  createPatient
} from "./api";
import { drugs } from "./data/mockData";
import Header from "./components/Header";
import Dashboard from "./components/Dashboard";
import Settings from "./components/Settings";
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

  const [view, setView] = useState("dashboard");

  const [profile, setProfile] = useState(null);

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

    setHcpId(null);
    setProfile(null);
    setChats([]);
    setSelectedChat(null);
    setSelectedDrug(null);
    setPatients([]);
    setSelectedPatient(null);
    setView("dashboard");
  }

  async function handleDeleteChat(chatId) {
    if (!hcpId) return;

    const chat = chats.find((item) => item.id === chatId);
    if (!chat) return;

    const confirmed = window.confirm(
      "Delete this conversation? This cannot be undone."
    );

    if (!confirmed) return;

    try {
      await deleteChat(hcpId, chat.conversationId || chat.id);

      setChats((currentChats) =>
        currentChats.filter((item) => item.id !== chatId)
      );

      setSelectedChat((currentChat) =>
        currentChat?.id === chatId ? null : currentChat
      );
    } catch (err) {
      console.error("Failed to delete chat:", err);
      setError(`Failed to delete conversation: ${err.message}`);
    }
  }

  useEffect(() => {
    if (!hcpId) return;

    async function loadProfile() {
      try {
        const data = await getProfile(hcpId);
        setProfile(data);
      } catch (err) {
        console.error("Failed to load profile:", err);
      }
    }

    loadProfile();
  }, [hcpId]);

  useEffect(() => {
    if (!hcpId) return;

    async function loadChats() {
      setLoading(true);
      setError(null);

      try {
        const data = await getChats(hcpId);

        const formattedChats = data.map((chat) => ({
          id: chat.id,
          conversationId: chat.conversation_id || chat.id,
          drugId: chat.drug_id,
          drugName:
            drugs.find((drug) => drug.id === chat.drug_id)?.name ||
            chat.drug_id,
          title:
            chat.title ||
            `${chat.drugName} - ${chat.question}`,
          timestamp: chat.asked_at
            ? new Date(chat.asked_at).toLocaleString()
            : "",
          preview: chat.preview || chat.question,
          messages:
            chat.messages || [
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

  async function handleCreatePatient(payload) {
    if (!hcpId) return;

    const patient = await createPatient(hcpId, payload);
    setPatients((currentPatients) => [...currentPatients, patient]);
    setSelectedPatient(patient);
    return patient;
  }

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

    const loadingMessage = {
      id: `loading-${Date.now()}`,
      role: "assistant",
      text: "",
      loading: true,
    };

    // Immediately update the chat and move it to the top.
    setChats((currentChats) => {
      const updatedChats = currentChats.map((item) =>
        item.id === chatId
          ? {
              ...item,
              messages: [
                ...item.messages,
                userMessage,
                loadingMessage,
              ],
              preview: text,
              timestamp: "Just now",
            }
          : item
      );

      const updatedChat = updatedChats.find(
        (item) => item.id === chatId
      );

      const otherChats = updatedChats.filter(
        (item) => item.id !== chatId
      );

      return updatedChat
        ? [updatedChat, ...otherChats]
        : updatedChats;
    });

    // Immediately update the open conversation.
    setSelectedChat((currentChat) =>
      currentChat?.id === chatId
        ? {
            ...currentChat,
            messages: [
              ...currentChat.messages,
              userMessage,
              loadingMessage,
            ],
            preview: text,
            timestamp: "Just now",
          }
        : currentChat
    );

    try {
      const response = await askDrugQuestion(
        chat.drugId,
        hcpId,
        text,
        chat.conversationId
      );

      const assistantMessage = {
        id: `msg-${Date.now()}-assistant`,
        role: "assistant",
        text: response.answer_text,
      };

      // Remove loading message and add the real response.
      setChats((currentChats) =>
        currentChats.map((item) =>
          item.id === chatId
            ? {
                ...item,
                conversationId:
                  response.conversation_id ||
                  item.conversationId,
                messages: [
                  ...item.messages.filter(
                    (message) => !message.loading
                  ),
                  assistantMessage,
                ],
              }
            : item
        )
      );

      setSelectedChat((currentChat) =>
        currentChat?.id === chatId
          ? {
              ...currentChat,
              conversationId:
                response.conversation_id ||
                currentChat.conversationId,
              messages: [
                ...currentChat.messages.filter(
                  (message) => !message.loading
                ),
                assistantMessage,
              ],
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

      // Remove loading message even when the request fails.
      setChats((currentChats) =>
        currentChats.map((item) =>
          item.id === chatId
            ? {
                ...item,
                messages: [
                  ...item.messages.filter(
                    (message) => !message.loading
                  ),
                  errorMessage,
                ],
              }
            : item
        )
      );

      setSelectedChat((currentChat) =>
        currentChat?.id === chatId
          ? {
              ...currentChat,
              messages: [
                ...currentChat.messages.filter(
                  (message) => !message.loading
                ),
                errorMessage,
              ],
            }
          : currentChat
      );
    }
  }
  async function handleRenameChat(chatId, title) {
    if (!hcpId) return;

    const chat = chats.find((item) => item.id === chatId);
    if (!chat) return;

    try {
      const response = await renameChat(
        hcpId,
        chat.conversationId || chat.id,
        title
      );

      setChats((currentChats) =>
        currentChats.map((item) =>
          item.id === chatId
            ? {
                ...item,
                title: response.title,
              }
            : item
        )
      );

      setSelectedChat((currentChat) =>
        currentChat?.id === chatId
          ? {
              ...currentChat,
              title: response.title,
            }
          : currentChat
      );
    } catch (err) {
      console.error("Failed to rename chat:", err);
      setError(`Failed to rename conversation: ${err.message}`);
    }
  }

  if (!hcpId) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="app">
      <Header
        view={view}
        setView={setView}
        onLogout={handleLogout}
      />

      <main className="main-content">
        {error && <div className="error-banner">{error}</div>}

        {view === "dashboard" && (
          <Dashboard
            profile={profile}
            hcpId={hcpId}
            chatCount={chats.length}
            drugCount={drugs.length}
            patientCount={patients.length}
            setView={setView}
          />
        )}

        {view === "settings" && (
          <Settings
            profile={profile}
            hcpId={hcpId}
            onLogout={handleLogout}
          />
        )}

        {view === "chats" && (
          <div className="content-layout">
            <ChatList
              chats={chats}
              selectedChat={selectedChat}
              setSelectedChat={setSelectedChat}
              onDeleteChat={handleDeleteChat}
              onRenameChat={handleRenameChat}
              loading={loading}
            />
            <ChatView
              chat={selectedChat}
              onSendMessage={handleSendMessage}
              onRenameChat={handleRenameChat}
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
              onCreate={handleCreatePatient}
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