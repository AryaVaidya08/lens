import { useEffect, useState } from "react";

function formatLocation(profile) {
  const cityRegion = [profile?.city, profile?.region]
    .filter(Boolean)
    .join(", ");

  return cityRegion || profile?.country || "Not set";
}

function Settings({
  profile,
  hcpId,
  onLogout,
  onUpdateProfile,
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    professional_role: "",
    specialty: "",
    credentials: "",
    organization: "",
    practice_setting: "",
    work_phone: "",
    city: "",
    region: "",
    country: "",
  });

  const resetForm = () => {
    setFormData({
      first_name: profile?.first_name || "",
      last_name: profile?.last_name || "",
      professional_role: profile?.professional_role || "",
      specialty: profile?.specialty || "",
      credentials: profile?.credentials || "",
      organization: profile?.organization || "",
      practice_setting: profile?.practice_setting || "",
      work_phone: profile?.work_phone || "",
      city: profile?.city || "",
      region: profile?.region || "",
      country: profile?.country || "",
    });
  };

  useEffect(() => {
    resetForm();
  }, [profile]);

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const handleEdit = () => {
    resetForm();
    setError("");
    setIsEditing(true);
  };

  const handleCancel = () => {
    resetForm();
    setError("");
    setIsEditing(false);
  };

  const handleSave = async () => {
    if (
      !formData.first_name.trim() ||
      !formData.last_name.trim() ||
      !formData.professional_role.trim() ||
      !formData.specialty.trim()
    ) {
      setError(
        "First name, last name, professional role, and specialty are required."
      );
      return;
    }

    try {
      setIsSaving(true);
      setError("");

      await onUpdateProfile({
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        professional_role: formData.professional_role.trim(),
        specialty: formData.specialty.trim(),
        credentials: formData.credentials.trim(),
        organization: formData.organization.trim(),
        practice_setting: formData.practice_setting.trim(),
        work_phone: formData.work_phone.trim(),
        city: formData.city.trim(),
        region: formData.region.trim(),
        country: formData.country.trim(),
      });

      setIsEditing(false);
    } catch (err) {
      console.error("Failed to update profile:", err);
      setError(err.message || "Unable to update profile.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="settings-page">
      <div className="dashboard-intro settings-header">
        <div>
          <h2>Settings</h2>
        </div>

        {!isEditing && (
          <button
            className="secondary-button"
            type="button"
            onClick={handleEdit}
          >
            Edit profile
          </button>
        )}
      </div>

      <section className="patient-section settings-section">
        <h3>Account</h3>

        {isEditing ? (
          <div className="settings-form">
            <div className="settings-form-grid">
              <label className="settings-field">
                <span>First name</span>
                <input
                  type="text"
                  name="first_name"
                  value={formData.first_name}
                  onChange={handleChange}
                />
              </label>

              <label className="settings-field">
                <span>Last name</span>
                <input
                  type="text"
                  name="last_name"
                  value={formData.last_name}
                  onChange={handleChange}
                />
              </label>

              <label className="settings-field">
                <span>Professional role</span>
                <input
                  type="text"
                  name="professional_role"
                  value={formData.professional_role}
                  onChange={handleChange}
                />
              </label>

              <label className="settings-field">
                <span>Specialty</span>
                <input
                  type="text"
                  name="specialty"
                  value={formData.specialty}
                  onChange={handleChange}
                />
              </label>

              <label className="settings-field">
                <span>Credentials</span>
                <input
                  type="text"
                  name="credentials"
                  value={formData.credentials}
                  onChange={handleChange}
                  placeholder="MD, DO, NP..."
                />
              </label>

              <label className="settings-field">
                <span>Organization</span>
                <input
                  type="text"
                  name="organization"
                  value={formData.organization}
                  onChange={handleChange}
                />
              </label>

              <label className="settings-field">
                <span>Practice setting</span>
                <input
                  type="text"
                  name="practice_setting"
                  value={formData.practice_setting}
                  onChange={handleChange}
                />
              </label>

              <label className="settings-field">
                <span>Work phone</span>
                <input
                  type="tel"
                  name="work_phone"
                  value={formData.work_phone}
                  onChange={handleChange}
                />
              </label>

              <label className="settings-field">
                <span>City</span>
                <input
                  type="text"
                  name="city"
                  value={formData.city}
                  onChange={handleChange}
                />
              </label>

              <label className="settings-field">
                <span>State / Region</span>
                <input
                  type="text"
                  name="region"
                  value={formData.region}
                  onChange={handleChange}
                />
              </label>

              <label className="settings-field">
                <span>Country</span>
                <input
                  type="text"
                  name="country"
                  value={formData.country}
                  onChange={handleChange}
                />
              </label>
            </div>

            <div className="settings-readonly">
              <div>
                <span>Email</span>
                <strong>{profile?.email || "Not set"}</strong>
              </div>

              <div>
                <span>HCP ID</span>
                <strong>{hcpId}</strong>
              </div>
            </div>

            {error && (
              <p className="settings-error">{error}</p>
            )}

            <div className="settings-form-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={handleCancel}
                disabled={isSaving}
              >
                Cancel
              </button>

              <button
                className="primary-button"
                type="button"
                onClick={handleSave}
                disabled={isSaving}
              >
                {isSaving ? "Saving..." : "Save changes"}
              </button>
            </div>
          </div>
        ) : (
          <div className="drug-meta profile-meta">
            <div>
              <span>Name</span>
              <strong>{profile?.name || "Not set"}</strong>
            </div>

            <div>
              <span>Professional Role</span>
              <strong>
                {profile?.professional_role || "Not set"}
              </strong>
            </div>

            <div>
              <span>Specialty</span>
              <strong>{profile?.specialty || "Not set"}</strong>
            </div>

            <div>
              <span>Credentials</span>
              <strong>{profile?.credentials || "Not set"}</strong>
            </div>

            <div>
              <span>Email</span>
              <strong>{profile?.email || "Not set"}</strong>
            </div>

            <div>
              <span>HCP ID</span>
              <strong>{hcpId}</strong>
            </div>

            <div>
              <span>Clinic</span>
              <strong>
                {profile?.organization ||
                  profile?.practice_setting ||
                  "Not set"}
              </strong>
            </div>

            <div>
              <span>Practice Setting</span>
              <strong>
                {profile?.practice_setting || "Not set"}
              </strong>
            </div>

            <div>
              <span>Work Phone</span>
              <strong>{profile?.work_phone || "Not set"}</strong>
            </div>

            <div>
              <span>Location</span>
              <strong>{formatLocation(profile)}</strong>
            </div>

            <div>
              <span>Workspace</span>
              <strong>Lens Clinical</strong>
            </div>
          </div>
        )}
      </section>

      <section className="patient-section settings-section">
        <h3>Notifications</h3>

        <label className="settings-toggle-row">
          <span>New drug reference updates</span>
          <input type="checkbox" defaultChecked disabled />
        </label>

        <label className="settings-toggle-row">
          <span>Weekly engagement summary</span>
          <input type="checkbox" disabled />
        </label>

        <label className="settings-toggle-row">
          <span>Patient chart changes</span>
          <input type="checkbox" defaultChecked disabled />
        </label>
      </section>

      <section className="patient-section settings-section">
        <h3>Appearance</h3>
        <p>
          Lens currently ships in a single theme. More options are
          coming soon.
        </p>
      </section>

      <section className="patient-section settings-section">
        <h3>About</h3>

        <div className="drug-meta profile-meta">
          <div>
            <span>Version</span>
            <strong>0.1.0 (hackathon build)</strong>
          </div>

          <div>
            <span>Build</span>
            <strong>GTHacks demo</strong>
          </div>
        </div>
      </section>

      <button
        className="primary-button settings-logout"
        type="button"
        onClick={onLogout}
      >
        Log out
      </button>
    </div>
  );
}

export default Settings;