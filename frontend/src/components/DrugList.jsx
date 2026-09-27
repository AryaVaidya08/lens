import { useState } from "react";

function DrugList({
  drugs,
  selectedDrug,
  setSelectedDrug,
  onAddDrug,
  onRemoveDrug,
}) {
  const [search, setSearch] = useState("");

  const filteredDrugs = drugs.filter((drug) =>
    drug.name.toLowerCase().startsWith(search.toLowerCase())
  );

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
          onClick={onAddDrug}
        >
          + Add
        </button>
      </div>

      <input
        className="search-input"
        type="text"
        placeholder="Search drugs..."
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />

      <div className="list">
        {filteredDrugs.length > 0 ? (
          filteredDrugs.map((drug) => (
            <div
              key={drug.id}
              role="button"
              tabIndex={0}
              onClick={() => setSelectedDrug(drug)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  setSelectedDrug(drug);
                }
              }}
              className={`list-item ${
                selectedDrug?.id === drug.id ? "selected" : ""
              }`}
            >
              <div className="list-item-content">
                <strong>{drug.name}</strong><br />
                <span>{drug.id}</span>
              </div>

              <button
                type="button"
                className="delete-chat-button"
                onClick={(event) => {
                  event.stopPropagation();
                  onRemoveDrug(drug.id);
                }}
                title="Remove drug"
                aria-label={`Remove ${drug.name}`}
              >
                🗑️
              </button>
            </div>
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