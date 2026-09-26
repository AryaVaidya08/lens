function Sidebar({ view, setView }) {
    return (
        <aside className="sidebar">
        <h1>HCP Spatial Copilot</h1>

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
        </aside>
    );
}

export default Sidebar;