function DrugDetails({ drug, summary, loading, error }) {
  if (!drug) {
    return (
      <section className="empty-state">
        <h3>Select a drug</h3>
        <p>Choose a drug to view its information.</p>
      </section>
    );
  }

  if (loading) {
    return (
      <section className="drug-details">
        <h3>{drug.name}</h3>
        <p>Loading drug information...</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="drug-details">
        <h3>{drug.name}</h3>
        <p>{error}</p>
      </section>
    );
  }

  const labels = {
    new: "New",
    returning: "Returning",
    expert: "Expert",
  };

  const tier = summary?.tier || "new";

  return (
    <section className="drug-details">
      <div className="drug-header">
        <div>
          <span className="eyebrow">Drug Profile</span>
          <h3>{summary?.name || drug.name}</h3>
        </div>

        <span className={`familiarity ${tier}`}>
          {labels[tier] || "New"}
        </span>
      </div>

      <div className="drug-section">
        <h4>{summary?.headline || "Overview"}</h4>

        {(summary?.full_bullets || summary?.bullets || []).length ? (
          <ul>
            {(summary.full_bullets || summary.bullets).map((bullet, index) => (
              <li key={`${index}-${bullet.slice(0, 24)}`}>
                {bullet}
              </li>
            ))}
          </ul>
        ) : (
          <p>No information available.</p>
        )}
      </div>
    </section>
  );
}

export default DrugDetails;