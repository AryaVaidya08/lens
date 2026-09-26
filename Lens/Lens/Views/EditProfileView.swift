import SwiftUI
import UIKit

/// UI preview only. All fields are temporary and never update the HCP or its cache.
struct EditProfileView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var firstName: String
    @State private var lastName: String
    @State private var email = ""
    @State private var professionalRole: String
    @State private var otherRole = ""
    @State private var credentials = ""
    @State private var specialty: String
    @State private var otherSpecialty: String
    @State private var organization = ""
    @State private var practiceSetting = ""
    @State private var workPhone = ""
    @State private var city = ""
    @State private var region = ""
    @State private var country = ""
    @State private var showingSaveNotice = false

    private static let roles = [
        "Physician", "Nurse Practitioner", "Physician Assistant", "Registered Nurse",
        "Clinical Nurse Specialist", "Nurse Anesthetist", "Midwife", "Pharmacist",
        "Dentist", "Optometrist", "Podiatrist", "Psychologist", "Therapist",
        "Dietitian / Nutritionist", "Social Worker", "Resident / Fellow",
        "Healthcare Student", "Other"
    ]
    private static let practiceSettings = [
        "Private Practice", "Hospital", "Outpatient Clinic", "Academic Medical Center",
        "Community Health Center", "Urgent Care", "Retail / Community Pharmacy",
        "Long-Term Care", "Home Health", "Telehealth", "Other"
    ]

    init(profile: HCP) {
        // Existing demo profiles only have a display name. Preserve all remaining
        // name components in the editable surname field instead of dropping them.
        var parts = profile.name.split(whereSeparator: { $0.isWhitespace }).map(String.init)
        let isDoctor = ["Dr.", "Dr"].contains(parts.first ?? "")
        if isDoctor { parts.removeFirst() }
        _firstName = State(initialValue: parts.first ?? "")
        _lastName = State(initialValue: parts.dropFirst().joined(separator: " "))
        _professionalRole = State(initialValue: isDoctor ? "Physician" : "")
        let knownSpecialty = HealthcareSpecialties.contains(profile.specialty)
        _specialty = State(initialValue: knownSpecialty ? profile.specialty : HealthcareSpecialties.other)
        _otherSpecialty = State(initialValue: knownSpecialty ? "" : profile.specialty)
    }

    private var emailLooksValid: Bool {
        email.trimmingCharacters(in: .whitespacesAndNewlines)
            .range(of: #"^[^\s@]+@[^\s@]+\.[^\s@]+$"#, options: .regularExpression) != nil
    }

    private var hasRequiredFields: Bool {
        let required = [firstName, lastName, professionalRole, specialty]
        return required.allSatisfy { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
            && emailLooksValid
            && (professionalRole != "Other" || !otherRole.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            && (specialty != HealthcareSpecialties.other || !otherSpecialty.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Label("Preview only — changes aren't saved yet.", systemImage: "info.circle")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                personalDetails
                professionalDetails
                practiceDetails
            }
            .scrollDismissesKeyboard(.interactively)
            .navigationTitle("Edit profile")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .accessibilityIdentifier("profileEditor.cancel")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        // TODO: connect profile updates when database support is ready.
                        showingSaveNotice = true
                    }
                    .disabled(!hasRequiredFields)
                    .accessibilityIdentifier("profileEditor.save")
                }
            }
            .alert("Profile editing preview", isPresented: $showingSaveNotice) {
                Button("Done") { dismiss() }
            } message: {
                Text("Saving changes isn't available yet. Your current profile is unchanged.")
            }
        }
    }

    private var personalDetails: some View {
        Section {
            field("First name", prompt: "Required", text: $firstName, id: "firstName")
                .textContentType(.givenName)
            field("Last name", prompt: "Required", text: $lastName, id: "lastName")
                .textContentType(.familyName)
            field("Email", prompt: "name@example.com", text: $email, id: "email", capitalization: .never)
                .textContentType(.emailAddress)
                .keyboardType(.emailAddress)
            if !email.isEmpty && !emailLooksValid {
                Text("Enter an email address such as name@example.com.")
                    .font(.footnote)
                    .foregroundStyle(.red)
            }
        } header: {
            Text("Personal details")
        } footer: {
            Text("First name, last name, and email are required. Email isn't verified in this preview.")
        }
    }

    private var professionalDetails: some View {
        Section {
            Picker("Professional role", selection: $professionalRole) {
                Text("Select a role").tag("")
                ForEach(Self.roles, id: \.self) { Text($0).tag($0) }
            }
            .pickerStyle(.menu)
            .accessibilityIdentifier("profileEditor.role")
            if professionalRole == "Other" {
                field("Your role", prompt: "Enter your role", text: $otherRole, id: "otherRole")
            }
            field("Credentials (optional)", prompt: "e.g. MD, DO, NP, PharmD", text: $credentials,
                  id: "credentials", capitalization: .characters)

            Picker("Primary specialty", selection: $specialty) {
                ForEach(HealthcareSpecialties.groups) { group in
                    Section(group.name) {
                        ForEach(group.specialties.sorted(), id: \.self) { Text($0).tag($0) }
                    }
                }
                Text(HealthcareSpecialties.other).tag(HealthcareSpecialties.other)
            }
            .pickerStyle(.menu)
            .accessibilityIdentifier("profileEditor.specialty")
            if specialty == HealthcareSpecialties.other {
                field("Your specialty", prompt: "Enter your specialty", text: $otherSpecialty, id: "otherSpecialty")
            }
        } header: {
            Text("Professional details")
        } footer: {
            Text("Choose your role and primary area of practice. Select Other if yours isn't listed.")
        }
    }

    private var practiceDetails: some View {
        Section {
            field("Practice or organization", prompt: "Clinic, hospital, or employer", text: $organization,
                  id: "organization")
                .textContentType(.organizationName)
            Picker("Practice setting", selection: $practiceSetting) {
                Text("Not specified").tag("")
                ForEach(Self.practiceSettings, id: \.self) { Text($0).tag($0) }
            }
            .pickerStyle(.menu)
            .accessibilityIdentifier("profileEditor.practiceSetting")
            field("Work phone", prompt: "Phone number", text: $workPhone, id: "workPhone", capitalization: .never)
                .textContentType(.telephoneNumber)
                .keyboardType(.phonePad)
            field("City", prompt: "City", text: $city, id: "city")
                .textContentType(.addressCity)
            field("State / province / region", prompt: "State, province, or region", text: $region, id: "region")
                .textContentType(.addressState)
            field("Country / region", prompt: "Country or region", text: $country, id: "country")
                .textContentType(.countryName)
        } header: {
            Text("Practice information · Optional")
        } footer: {
            Text("Add your professional contact and practice details if you'd like.")
        }
    }

    private func field(_ title: String, prompt: String, text: Binding<String>, id: String,
                       capitalization: TextInputAutocapitalization = .words) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.subheadline).foregroundStyle(.secondary)
            TextField(title, text: text, prompt: Text(prompt))
                .textInputAutocapitalization(capitalization)
                .autocorrectionDisabled()
                .accessibilityIdentifier("profileEditor.\(id)")
        }
        .padding(.vertical, 3)
    }
}
