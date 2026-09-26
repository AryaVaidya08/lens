function Dashboard({ profile, hcpId, chatCount, drugCount, patientCount, setView }) {
  const name = profile?.name || "there";
  const specialty = profile?.specialty;

  const stats = [
    {
      key: "chats",
      label: "Chats",
      value: chatCount,
      hint: "Conversations with your assistant",
      view: "chats",
    },
    {
      key: "drugs",
      label: "Drug catalog",
      value: drugCount,
      hint: "Reference profiles available",
      view: "drugs",
    },
    {
      key: "patients",
      label: "Patients",
      value: patientCount,
      hint: "Under your care",
      view: "patients",
    },
  ];

  return (
    <div className="dashboard-page">
      <div className="dashboard-intro">
        <h2>Welcome back, {name}</h2>
        <p className="dashboard-lede">
          Here's where things stand across your workspace.
        </p>
      </div>

      <div className="drug-meta profile-meta">
        <div>
          <span>Specialty</span>
          <strong>{specialty || "Not set"}</strong>
        </div>
        <div>
          <span>HCP ID</span>
          <strong>{hcpId}</strong>
        </div>
      </div>

      <div className="stat-grid">
        {stats.map((stat) => (
          <button
            key={stat.key}
            className="stat-tile"
            onClick={() => setView(stat.view)}
          >
            <span className="stat-label">{stat.label}</span>
            <span className="stat-value">
              {String(stat.value ?? 0).padStart(2, "0")}
            </span>
            <span className="stat-hint">{stat.hint}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default Dashboard;
