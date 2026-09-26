import logo from "../../img/logo-icon-removebg.png";

const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard" },
  { key: "chats", label: "Chats" },
  { key: "drugs", label: "Drug Information" },
  { key: "patients", label: "Patients" },
];

function Header({ view, setView, onLogout }) {
  return (
    <header className="app-header">
      <div className="app-header-inner">
        <button
          className="brand-mark"
          onClick={() => setView("dashboard")}
          aria-label="Go to dashboard"
        >
          <img src={logo} alt="" className="brand-logo" />
          <span className="brand-word">Lens</span>
        </button>

        <nav className="header-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              className={view === item.key ? "active" : ""}
              onClick={() => setView(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="header-actions">
          <button
            className={`icon-button ${view === "settings" ? "active" : ""}`}
            onClick={() => setView("settings")}
            title="Settings"
            aria-label="Settings"
          >
            <svg viewBox="0 0 20 20" width="17" height="17" fill="none">
              <path
                d="M10 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z"
                stroke="currentColor"
                strokeWidth="1.4"
              />
              <path
                d="M16.3 12.3c-.15.36-.1.78.13 1.1l.06.08a1.4 1.4 0 1 1-2.28 1.65l-.05-.08a1.35 1.35 0 0 0-1.1-.6c-.4 0-.77.2-1 .53a1.4 1.4 0 0 1-2.72 0 1.14 1.14 0 0 0-1-.53c-.44 0-.86.23-1.1.6l-.05.08a1.4 1.4 0 1 1-2.28-1.65l.06-.08c.23-.32.28-.74.13-1.1a1.14 1.14 0 0 0-.93-.66h-.1a1.4 1.4 0 0 1 0-2.8h.1c.42-.02.79-.28.93-.66.15-.36.1-.78-.13-1.1l-.06-.08A1.4 1.4 0 1 1 6.24 5.3l.05.08c.24.32.65.51 1.1.6.4 0 .77-.2 1-.53a1.4 1.4 0 0 1 2.72 0c.23.33.6.53 1 .53.44 0 .85-.23 1.1-.6l.05-.08a1.4 1.4 0 1 1 2.28 1.65l-.06.08c-.23.32-.28.74-.13 1.1.14.38.51.64.93.66h.1a1.4 1.4 0 0 1 0 2.8h-.1c-.42.02-.79.28-.93.66Z"
                stroke="currentColor"
                strokeWidth="1.1"
              />
            </svg>
          </button>

          <button
            className="icon-button"
            onClick={onLogout}
            title="Log out"
            aria-label="Log out"
          >
            <svg viewBox="0 0 20 20" width="17" height="17" fill="none">
              <path
                d="M8 3.5H5a1.5 1.5 0 0 0-1.5 1.5v10A1.5 1.5 0 0 0 5 16.5h3"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
              />
              <path
                d="M12.5 13.5 16 10l-3.5-3.5M16 10H7.5"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
