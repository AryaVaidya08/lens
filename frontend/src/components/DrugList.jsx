import { useState } from "react";

function DrugList({ drugs, selectedDrug, setSelectedDrug }) {
  const [search, setSearch] = useState("");

  const filteredDrugs = drugs.filter((drug) => {
    const query = search.toLowerCase();

    return (
      drug.name.toLowerCase().includes(query) ||
      drug.genericName.toLowerCase().includes(query) ||
      drug.category.toLowerCase().includes(query)
    );
  });

  return (
    <div className="list-panel">
      <div className="panel-header">
        <div>
          <h2>Drug Information</h2>
          <p>{drugs.length} medications</p>
        </div>
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
            <button
              key={drug.id}
              onClick={() => setSelectedDrug(drug)}
              className={`list-item ${
                selectedDrug?.id === drug.id ? "selected" : ""
              }`}
            >
              <strong>{drug.name}</strong>
              <span>{drug.genericName}</span>
              <small>{drug.category}</small>
            </button>
          ))
        ) : (
          <div className="list-empty">
            <strong>No drugs found</strong>
            <span>Try a different search.</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default DrugList;