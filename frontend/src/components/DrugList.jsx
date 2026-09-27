import { useRef, useState } from "react";

const SEARCH_DEBOUNCE_MS = 300;

function DrugList({ drugs, selectedDrug, setSelectedDrug, onSearchDrugs, onAddDrug }) {
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [addQuery, setAddQuery] = useState("");
  const [addResults, setAddResults] = useState([]);
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState("");
  const debounceRef = useRef(null);

  const filteredDrugs = drugs.filter((drug) =>
    drug.name.toLowerCase().startsWith(search.toLowerCase())
  );

  function toggleAdd() {
    setShowAdd((current) => !current);
    setAddQuery("");
    setAddResults([]);
    setAddError("");
  }

  function handleAddQueryChange(event) {
    const value = event.target.value;
    setAddQuery(value);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    const trimmed = value.trim();
    if (!trimmed) {
      setAddResults([]);
      setAddLoading(false);
      return;
    }

    setAddLoading(true);

    debounceRef.current = setTimeout(async () => {
      try {
        const results = await onSearchDrugs(trimmed);
        setAddResults(results);
        setAddError("");
      } catch (err) {
        console.error("Drug search failed:", err);
        setAddError(err.message);
      } finally {
        setAddLoading(false);
      }
    }, SEARCH_DEBOUNCE_MS);
  }

  function handleAdd(drug) {
    onAddDrug(drug);
    setSelectedDrug(drug);
    toggleAdd();
  }

  return (
    <div className="list-panel">
      <div className="panel-header">
        <div>
          <h2>Drug Information</h2>
          <p>{drugs.length} medications</p>
        </div>

        <button
          type="button"
          className="primary-button small"
          onClick={toggleAdd}
        >
          {showAdd ? "Close" : "+ Add"}
        </button>
      </div>

      <input
        className="search-input"
        type="text"
        placeholder={
          showAdd ? "Search the full drug catalog..." : "Search drugs..."
        }
        value={showAdd ? addQuery : search}
        autoFocus={showAdd}
        onChange={showAdd ? handleAddQueryChange : (event) => setSearch(event.target.value)}
      />

      {showAdd && addError && (
        <div className="error-banner">{addError}</div>
      )}

      <div className="list">
        {showAdd ? (
          addLoading ? (
            <div className="list-empty">
              <strong>Searching…</strong>
            </div>
          ) : addResults.length > 0 ? (
            addResults.map((drug) => (
              <button
                key={drug.id}
                type="button"
                className="list-item"
                onClick={() => handleAdd(drug)}
              >
                <strong>{drug.name}</strong>
                <span>{drug.id}</span>
              </button>
            ))
          ) : (
            <div className="list-empty">
              <strong>
                {addQuery.trim() ? "No matches" : "Search the catalog"}
              </strong>
              <span>
                {addQuery.trim()
                  ? "Try a different drug name."
                  : "Start typing a drug name to add it."}
              </span>
            </div>
          )
        ) : filteredDrugs.length > 0 ? (
          filteredDrugs.map((drug) => (
            <button
              key={drug.id}
              onClick={() => setSelectedDrug(drug)}
              className={`list-item ${
                selectedDrug?.id === drug.id ? "selected" : ""
              }`}
            >
              <strong>{drug.name}</strong>
              <span>{drug.id}</span>
            </button>
          ))
        ) : (
          <div className="list-empty">
            <strong>No drugs found</strong>
            <span>
              {drugs.length === 0
                ? "Ask a question about a drug, or add one, to see it here."
                : "Try a different search."}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export default DrugList;
