function Settings({ profile, hcpId, onLogout }) {
  return (
    <div className="settings-page">
      <div className="dashboard-intro">
        <h2>Settings</h2>
        <p className="dashboard-lede">
          Placeholder preferences for now — this page fills in once the rest
          of the app settles.
        </p>
      </div>

      <section className="patient-section settings-section">
        <h3>Account</h3>
        <div className="drug-meta profile-meta">
          <div>
            <span>Name</span>
            <strong>{profile?.name || "Not set"}</strong>
          </div>
          <div>
            <span>Specialty</span>
            <strong>{profile?.specialty || "Not set"}</strong>
          </div>
          <div>
            <span>HCP ID</span>
            <strong>{hcpId}</strong>
          </div>
          <div>
            <span>Workspace</span>
            <strong>Lens Clinical</strong>
          </div>
        </div>
      </section>

      <section className="patient-section settings-section">
        <h3>Notifications</h3>
        <label className="settings-toggle-row">
          <span>New drug reference updates</span>
          <input type="checkbox" defaultChecked disabled />
        </label>
        <label className="settings-toggle-row">
          <span>Weekly engagement summary</span>
          <input type="checkbox" disabled />
        </label>
        <label className="settings-toggle-row">
          <span>Patient chart changes</span>
          <input type="checkbox" defaultChecked disabled />
        </label>
      </section>

      <section className="patient-section settings-section">
        <h3>Appearance</h3>
        <p>Lens currently ships in a single theme. More options are coming soon.</p>
      </section>

      <section className="patient-section settings-section">
        <h3>About</h3>
        <div className="drug-meta profile-meta">
          <div>
            <span>Version</span>
            <strong>0.1.0 (hackathon build)</strong>
          </div>
          <div>
            <span>Build</span>
            <strong>GTHacks demo</strong>
          </div>
        </div>
      </section>

      <button className="primary-button settings-logout" onClick={onLogout}>
        Log out
      </button>
    </div>
  );
}

export default Settings;
