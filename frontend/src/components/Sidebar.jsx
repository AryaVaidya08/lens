function Sidebar({ view, setView, onLogout }) {
  return (
    <aside className="sidebar">
      <h1>HCP Spatial Copilot</h1>

      <div className="sidebar-nav">
        <button
          className={view === "chats" ? "active" : ""}
          onClick={() => setView("chats")}
        >
          💬 Past Chats
        </button>

        <button
          className={view === "drugs" ? "active" : ""}
          onClick={() => setView("drugs")}
        >
          💊 Drug Information
        </button>

        <button
          className={view === "patients" ? "active" : ""}
          onClick={() => setView("patients")}
        >
          👤 Patients
        </button>
      </div>

      <button className="logout-button" onClick={onLogout}>
        ↪ Log out
      </button>
    </aside>
  );
}

export default Sidebar;