function DrugAddPanel({
  query,
  results,
  loading,
  error,
  onQueryChange,
  onSelectDrug,
  onCancel,
}) {
  return (
    <section className="drug-add-panel">
      <div className="drug-add-header">
        <div>
          <span className="eyebrow">Drug Information</span>
          <h2>Add a Drug</h2>
          <p>
            Search the full drug catalog and add a medication to your
            Drug Information list.
          </p>
        </div>

        <button
          type="button"
          className="secondary-button"
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>

      <div className="drug-add-search">
        <input
          type="text"
          placeholder="Search the full drug catalog..."
          value={query}
          autoFocus
          onChange={onQueryChange}
        />
      </div>

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <div className="drug-add-results">
        {loading ? (
          <div className="list-empty">
            <strong>Searching…</strong>
          </div>
        ) : results.length > 0 ? (
          results.map((drug) => (
            <button
              key={drug.id}
              type="button"
              className="drug-add-result"
              onClick={() => onSelectDrug(drug)}
            >
              <strong>{drug.name}</strong>
              <span>{drug.id}</span>
            </button>
          ))
        ) : (
          <div className="list-empty">
            <strong>
              {query.trim()
                ? "No matches"
                : "Search the catalog"}
            </strong>

            <span>
              {query.trim()
                ? "Try a different drug name."
                : "Start typing a drug name to add it."}
            </span>
          </div>
        )}
      </div>
    </section>
  );
}

export default DrugAddPanel;