function DrugDetails({ drug, summary, loading, error, onRemoveDrug }) {
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
        <div className="drug-header">
          <h3>{drug.name}</h3>
          <button
            type="button"
            className="secondary-button small remove-button"
            onClick={() => onRemoveDrug(drug.id)}
          >
            Remove
          </button>
        </div>
        <p>Loading drug information...</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="drug-details">
        <div className="drug-header">
          <h3>{drug.name}</h3>
          <button
            type="button"
            className="secondary-button small remove-button"
            onClick={() => onRemoveDrug(drug.id)}
          >
            Remove
          </button>
        </div>
        <p>{error}</p>
      </section>
    );
  }

  return (
    <section className="drug-details">
      <div className="drug-header">
        <div>
          <span className="eyebrow">Drug Profile</span>
          <h3>{summary?.name || drug.name}</h3>
        </div>

        <button
          type="button"
          className="secondary-button small remove-button"
          onClick={() => onRemoveDrug(drug.id)}
        >
          Remove
        </button>
      </div>

      <div className="drug-section">
        <h4>{summary?.headline || "Overview"}</h4>

        {summary?.summary_source === "unavailable" && (
          <p>AI summary unavailable. Reference text is not shown until Grok rewrites it.</p>
        )}
        {(summary?.bullets || []).length ? (
          <ul>
            {summary.bullets.map((bullet, index) => (
              <li key={`${index}-${bullet.slice(0, 24)}`}>
                {bullet}
              </li>
            ))}
          </ul>
        ) : (
          <p>No generated summary yet.</p>
        )}
      </div>
    </section>
  );
}

export default DrugDetails;
