import { useEffect, useMemo, useState } from "react";
import {
  getChats,
  deleteChat,
  renameChat,
  getDrugSummary,
  searchDrugs,
  askDrugQuestion,
  logEngagement,
  getPatients,
  getProfile,
  createPatient
} from "./api";
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
  const [extraDrugs, setExtraDrugs] = useState([]);
  const [hiddenDrugIds, setHiddenDrugIds] = useState([]);

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
    setExtraDrugs([]);
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
          drugName: chat.drug_name || chat.drug_id,
          title: chat.title || chat.question,
          timestamp: chat.asked_at || null,
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

  // Drugs a clinician has manually pinned via the "+ Add" search, on top
  // of the ones that auto-populate from their chat history. Kept
  // per-HCP in localStorage since it's a personal UI convenience, not
  // data the backend needs to own.
  useEffect(() => {
    if (!hcpId) return;

    try {
      const raw = localStorage.getItem(`lens_extra_drugs_${hcpId}`);
      setExtraDrugs(raw ? JSON.parse(raw) : []);
    } catch (err) {
      console.error("Failed to load saved drugs:", err);
      setExtraDrugs([]);
    }

    try {
      const raw = localStorage.getItem(`lens_hidden_drugs_${hcpId}`);
      setHiddenDrugIds(raw ? JSON.parse(raw) : []);
    } catch (err) {
      console.error("Failed to load hidden drugs:", err);
      setHiddenDrugIds([]);
    }
  }, [hcpId]);

  function handleAddDrug(drug) {
    setExtraDrugs((current) => {
      if (current.some((item) => item.id === drug.id)) return current;

      const updated = [...current, drug];

      try {
        localStorage.setItem(
          `lens_extra_drugs_${hcpId}`,
          JSON.stringify(updated)
        );
      } catch (err) {
        console.error("Failed to save drug:", err);
      }

      return updated;
    });

    setHiddenDrugIds((current) => {
      if (!current.includes(drug.id)) return current;

      const updated = current.filter((id) => id !== drug.id);

      try {
        localStorage.setItem(
          `lens_hidden_drugs_${hcpId}`,
          JSON.stringify(updated)
        );
      } catch (err) {
        console.error("Failed to save hidden drugs:", err);
      }

      return updated;
    });
  }

  // Removing a drug from the "Drug Information" list is a personal UI
  // preference (like pinning), not a backend-owned deletion, so it's
  // tracked the same way: a per-HCP id list in localStorage that's
  // subtracted from drugCatalog below.
  function handleRemoveDrug(drugId) {
    setHiddenDrugIds((current) => {
      if (current.includes(drugId)) return current;

      const updated = [...current, drugId];

      try {
        localStorage.setItem(
          `lens_hidden_drugs_${hcpId}`,
          JSON.stringify(updated)
        );
      } catch (err) {
        console.error("Failed to save hidden drugs:", err);
      }

      return updated;
    });

    setExtraDrugs((current) => {
      if (!current.some((item) => item.id === drugId)) return current;

      const updated = current.filter((item) => item.id !== drugId);

      try {
        localStorage.setItem(
          `lens_extra_drugs_${hcpId}`,
          JSON.stringify(updated)
        );
      } catch (err) {
        console.error("Failed to save drug:", err);
      }

      return updated;
    });

    setSelectedDrug((current) =>
      current?.id === drugId ? null : current
    );
  }

  async function handleSearchDrugs(query) {
    const results = await searchDrugs(query);
    return results.map((item) => ({ id: item.drug_id, name: item.name }));
  }

  // Drug Information auto-populates from every drug a chat has touched,
  // plus anything manually pinned via "+ Add" — no more static catalog.
  const drugCatalog = useMemo(() => {
    const byId = new Map();

    for (const chat of chats) {
      if (!byId.has(chat.drugId)) {
        byId.set(chat.drugId, { id: chat.drugId, name: chat.drugName });
      }
    }

    for (const drug of extraDrugs) {
      if (!byId.has(drug.id)) {
        byId.set(drug.id, drug);
      }
    }

    return Array.from(byId.values())
      .filter((drug) => !hiddenDrugIds.includes(drug.id))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [chats, extraDrugs, hiddenDrugIds]);

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
              timestamp: new Date().toISOString(),
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
            timestamp: new Date().toISOString(),
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
            drugCount={drugCatalog.length}
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
              drugs={drugCatalog}
              selectedDrug={selectedDrug}
              setSelectedDrug={setSelectedDrug}
              onSearchDrugs={handleSearchDrugs}
              onAddDrug={handleAddDrug}
            />

            <DrugDetails
              drug={selectedDrug}
              summary={drugSummary}
              loading={loadingDrug}
              error={error}
              onRemoveDrug={handleRemoveDrug}
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