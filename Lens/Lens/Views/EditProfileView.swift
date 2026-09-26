import SwiftUI
import UIKit

struct EditProfileView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss
    @State private var firstName: String
    @State private var lastName: String
    @State private var email: String
    @State private var professionalRole: String
    @State private var otherRole = ""
    @State private var credentials: String
    @State private var specialty: String
    @State private var otherSpecialty: String
    @State private var organization: String
    @State private var practiceSetting: String
    @State private var workPhone: String
    @State private var city: String
    @State private var region: String
    @State private var country: String
    @State private var currentPassword = ""
    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var isChangingPassword = false

    private let profileID: String
    private let originalEmail: String

    init(profile: HCP) {
        profileID = profile.id
        originalEmail = (profile.email ?? "").trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        var parts = profile.name.split(whereSeparator: { $0.isWhitespace }).map(String.init)
        let isDoctor = ["Dr.", "Dr"].contains(parts.first ?? "")
        if isDoctor { parts.removeFirst() }
        _firstName = State(initialValue: profile.firstName ?? parts.first ?? "")
        _lastName = State(initialValue: profile.lastName ?? parts.dropFirst().joined(separator: " "))
        _email = State(initialValue: profile.email ?? "")
        let role = profile.professionalRole ?? (isDoctor ? "Physician" : "")
        if !role.isEmpty && !ProfileOptions.roles.contains(role) {
            _professionalRole = State(initialValue: "Other")
            _otherRole = State(initialValue: role)
        } else {
            _professionalRole = State(initialValue: role)
        }
        _credentials = State(initialValue: profile.credentials ?? "")
        let knownSpecialty = HealthcareSpecialties.contains(profile.specialty)
        _specialty = State(initialValue: knownSpecialty ? profile.specialty : HealthcareSpecialties.other)
        _otherSpecialty = State(initialValue: knownSpecialty ? "" : profile.specialty)
        _organization = State(initialValue: profile.organization ?? "")
        _practiceSetting = State(initialValue: profile.practiceSetting ?? "")
        _workPhone = State(initialValue: profile.workPhone ?? "")
        _city = State(initialValue: profile.city ?? "")
        _region = State(initialValue: profile.region ?? "")
        _country = State(initialValue: profile.country ?? "")
    }

    private var emailLooksValid: Bool {
        email.trimmingCharacters(in: .whitespacesAndNewlines)
            .range(of: #"^[^\s@]+@[^\s@]+\.[^\s@]+$"#, options: .regularExpression) != nil
    }

    private var resolvedRole: String {
        professionalRole == "Other" ? otherRole.trimmingCharacters(in: .whitespacesAndNewlines) : professionalRole
    }

    private var resolvedSpecialty: String {
        specialty == HealthcareSpecialties.other
            ? otherSpecialty.trimmingCharacters(in: .whitespacesAndNewlines)
            : specialty
    }

    private var emailChanged: Bool {
        email.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() != originalEmail
    }

    private var hasRequiredFields: Bool {
        let required = [firstName, lastName, professionalRole, specialty]
        return required.allSatisfy { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
            && emailLooksValid
            && !resolvedRole.isEmpty
            && !resolvedSpecialty.isEmpty
            && (!emailChanged || !currentPassword.isEmpty)
    }

    var body: some View {
        NavigationStack {
            Form {
                personalDetails
                professionalDetails
                practiceDetails
                if let errorMessage {
                    Section {
                        Text(errorMessage).foregroundStyle(.red)
                    }
                }
                Section {
                    Button("Change password") { isChangingPassword = true }
                        .accessibilityIdentifier("profileEditor.changePassword")
                }
            }
            .scrollDismissesKeyboard(.interactively)
            .navigationTitle("Edit profile")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(isPresented: $isChangingPassword) {
                ChangePasswordView()
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .accessibilityIdentifier("profileEditor.cancel")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task { await save() }
                    }
                    .disabled(!hasRequiredFields || isSaving)
                    .accessibilityIdentifier("profileEditor.save")
                }
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
            if emailChanged {
                SecureField("Current password to change email", text: $currentPassword)
                    .textContentType(.password)
                    .accessibilityIdentifier("profileEditor.currentPassword")
            }
        } header: {
            Text("Personal details")
        } footer: {
            Text("Changing email requires your current password. Use Change password at the bottom of this screen to update the password.")
        }
    }

    private var professionalDetails: some View {
        Section {
            Picker("Professional role", selection: $professionalRole) {
                Text("Select a role").tag("")
                ForEach(ProfileOptions.roles, id: \.self) { Text($0).tag($0) }
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
                ForEach(ProfileOptions.practiceSettings, id: \.self) { Text($0).tag($0) }
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
            field("Country / region", prompt: "Country / region", text: $country, id: "country")
                .textContentType(.countryName)
        } header: {
            Text("Practice information · Optional")
        } footer: {
            Text("These fields match the placeholders on this screen and are written to MongoDB.")
        }
    }

    @MainActor
    private func save() async {
        errorMessage = nil
        isSaving = true
        defer { isSaving = false }
        do {
            let updated = try await APIClient.shared.updateProfile(
                hcpId: profileID,
                ProfileUpdateRequest(
                    firstName: firstName.trimmingCharacters(in: .whitespacesAndNewlines),
                    lastName: lastName.trimmingCharacters(in: .whitespacesAndNewlines),
                    email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                    professionalRole: resolvedRole,
                    specialty: resolvedSpecialty,
                    credentials: credentials.trimmingCharacters(in: .whitespacesAndNewlines),
                    organization: organization.trimmingCharacters(in: .whitespacesAndNewlines),
                    practiceSetting: practiceSetting,
                    workPhone: workPhone.trimmingCharacters(in: .whitespacesAndNewlines),
                    city: city.trimmingCharacters(in: .whitespacesAndNewlines),
                    region: region.trimmingCharacters(in: .whitespacesAndNewlines),
                    country: country.trimmingCharacters(in: .whitespacesAndNewlines),
                    currentPassword: emailChanged ? currentPassword : nil
                )
            )
            appState.selectedHCP = updated
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
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
