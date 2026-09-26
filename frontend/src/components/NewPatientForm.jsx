import { useState } from "react";

const EMPTY_FORM = {
  first_name: "",
  last_name: "",
  sex: "",
  age: "",
  weight_kg: "",
  allergies: "",
  current_medications: "",
  medical_history: "",
  notes: "",
};

function NewPatientForm({ onCreate, onCancel }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function update(field) {
    return (event) => setForm((current) => ({ ...current, [field]: event.target.value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (!form.first_name.trim() || !form.last_name.trim()) {
      setError("First and last name are required.");
      return;
    }

    setSaving(true);
    try {
      await onCreate({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        sex: form.sex.trim() || null,
        age: form.age ? Number(form.age) : null,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : null,
        allergies: form.allergies.trim() || null,
        current_medications: form.current_medications.trim() || null,
        medical_history: form.medical_history.trim() || null,
        notes: form.notes.trim() || null,
      });
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err.message || "Unable to create patient.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="new-patient-form" onSubmit={handleSubmit}>
      <div className="new-patient-row">
        <label>
          First name
          <input value={form.first_name} onChange={update("first_name")} required />
        </label>
        <label>
          Last name
          <input value={form.last_name} onChange={update("last_name")} required />
        </label>
      </div>

      <div className="new-patient-row">
        <label>
          Sex
          <input value={form.sex} onChange={update("sex")} placeholder="e.g. Female" />
        </label>
        <label>
          Age
          <input type="number" min="0" value={form.age} onChange={update("age")} />
        </label>
        <label>
          Weight (kg)
          <input type="number" min="0" step="0.1" value={form.weight_kg} onChange={update("weight_kg")} />
        </label>
      </div>

      <label>
        Allergies
        <input value={form.allergies} onChange={update("allergies")} placeholder="e.g. Penicillin, none known" />
      </label>

      <label>
        Current medications
        <input value={form.current_medications} onChange={update("current_medications")} />
      </label>

      <label>
        Medical history
        <textarea rows={2} value={form.medical_history} onChange={update("medical_history")} />
      </label>

      <label>
        Notes
        <textarea rows={2} value={form.notes} onChange={update("notes")} />
      </label>

      {error && <div className="new-patient-error">{error}</div>}

      <div className="new-patient-actions">
        <button type="button" className="secondary-button" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button type="submit" className="primary-button" disabled={saving}>
          {saving ? "Adding..." : "Add patient"}
        </button>
      </div>
    </form>
  );
}

export default NewPatientForm;
