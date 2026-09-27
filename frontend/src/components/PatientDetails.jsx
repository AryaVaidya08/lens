function PatientDetails({ patient }) {
  if (!patient) {
    return (
      <div className="patient-details empty-state">
        Select a patient to view their chart.
      </div>
    );
  }

  const fullName = `${patient.first_name} ${patient.last_name}`.trim();

  return (
    <div className="patient-details">
        <div className="patient-header">
            <div className="patient-header-info">
                <div className="patient-avatar large">
                {patient.first_name?.[0]}
                {patient.last_name?.[0]}
                </div>

                <div>
                <h2>{fullName || "Unnamed patient"}</h2>
                <p>
                    {patient.age ? `${patient.age} years old` : "Age unavailable"}
                    {patient.sex ? ` • ${patient.sex}` : ""}
                </p>
                </div>
            </div>
        </div>

      <section className="patient-section">
        <h3>Allergies</h3>
        <div className="patient-alert">
          {patient.allergies || "No allergies recorded."}
        </div>
      </section>

      <section className="patient-section">
        <h3>Current Medications</h3>
        <p>
          {patient.current_medications || "No current medications recorded."}
        </p>
      </section>

      <section className="patient-section">
        <h3>Medical History</h3>
        <p>
          {patient.medical_history || "No medical history recorded."}
        </p>
      </section>

      <section className="patient-section">
        <h3>Notes</h3>
        <p>{patient.notes || "No notes recorded."}</p>
      </section>
    </div>
  );
}

export default PatientDetails;