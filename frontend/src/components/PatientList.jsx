import { useState } from "react";
import NewPatientForm from "./NewPatientForm";

function PatientList({ patients, selectedPatient, onSelect, onCreate }) {
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);

  const filteredPatients = patients.filter((patient) => {
    const name = `${patient.first_name} ${patient.last_name}`.toLowerCase();

    return name.includes(search.toLowerCase());
  });

  async function handleCreate(payload) {
    const created = await onCreate(payload);
    setShowForm(false);
    return created;
  }

  return (
    <div className="patient-list">
      <div className="patient-list-header">
        <div className="patient-list-header-top">
          <h2>Patients</h2>
          <button
            type="button"
            className="primary-button small"
            onClick={() => setShowForm((current) => !current)}
          >
            {showForm ? "Close" : "+ New Patient"}
          </button>
        </div>

        {showForm ? (
          <NewPatientForm onCreate={handleCreate} onCancel={() => setShowForm(false)} />
        ) : (
          <input
            type="text"
            placeholder="Search patients..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        )}
      </div>

      {filteredPatients.length === 0 ? (
        <div className="empty-state">
          {search ? "No patients found." : "No patients assigned."}
        </div>
      ) : (
        filteredPatients.map((patient) => {
          const name = `${patient.first_name} ${patient.last_name}`.trim();

          return (
            <button
              key={patient.patient_id}
              className={`patient-list-item ${
                selectedPatient?.patient_id === patient.patient_id
                  ? "selected"
                  : ""
              }`}
              onClick={() => onSelect(patient)}
            >
              <div className="patient-avatar">
                {patient.first_name?.[0]}
                {patient.last_name?.[0]}
              </div>

              <div className="patient-list-info">
                <strong>{name || "Unnamed patient"}</strong>
                <span>
                  {patient.age
                    ? `${patient.age} years old`
                    : "Age unavailable"}
                </span>
              </div>
            </button>
          );
        })
      )}
    </div>
  );
}

export default PatientList;