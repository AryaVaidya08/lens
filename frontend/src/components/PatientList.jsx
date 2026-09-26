import { useState } from "react";

function PatientList({ patients, selectedPatient, onSelect }) {
  const [search, setSearch] = useState("");

  const filteredPatients = patients.filter((patient) => {
    const name = `${patient.first_name} ${patient.last_name}`.toLowerCase();

    return name.includes(search.toLowerCase());
  });

  return (
    <div className="patient-list">
      <div className="patient-list-header">
        <h2>Patients</h2>

        <input
          type="text"
          placeholder="Search patients..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
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