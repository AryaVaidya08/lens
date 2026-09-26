import { currentHCP } from "../data/mockData";

function DrugDetails({ drug }) {
  if (!drug) {
    return (
      <section className="empty-state">
        <h3>Select a drug</h3>
        <p>Choose a drug to view its information.</p>
      </section>
    );
  }

  const familiarity = currentHCP.familiarity[drug.id];

  const familiarityLabels = {
    new: "New",
    returning: "Returning",
    expert: "Expert",
  };

  return (
    <section className="drug-details">
      <div className="drug-header">
        <div>
          <span className="eyebrow">Drug Profile</span>
          <h3>{drug.name}</h3>

          <p className="generic-name">
            {drug.genericName}
          </p>
        </div>

        <span className={`familiarity ${familiarity}`}>
          {familiarityLabels[familiarity] || "New"}
        </span>
      </div>

      <div className="drug-meta">
        <div>
          <span>Manufacturer</span>
          <strong>{drug.manufacturer}</strong>
        </div>

        <div>
          <span>Category</span>
          <strong>{drug.category}</strong>
        </div>
      </div>

      <div className="drug-section">
        <h4>Overview</h4>
        <p>{drug.description}</p>
      </div>

      <div className="drug-section">
        <h4>Indications</h4>

        <ul>
          {drug.indications.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div className="drug-section">
        <h4>Mechanism of Action</h4>
        <p>{drug.mechanism}</p>
      </div>

      <div className="drug-section">
        <h4>Common Adverse Reactions</h4>

        <ul>
          {drug.commonAdverseReactions.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div className="drug-section safety-section">
        <h4>Safety</h4>
        <p>{drug.safety}</p>
      </div>
    </section>
  );
}

export default DrugDetails;