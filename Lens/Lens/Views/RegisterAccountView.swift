import SwiftUI

struct RegisterAccountView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss
    @State private var firstName = ""
    @State private var lastName = ""
    @State private var email = ""
    @State private var password = ""
    @State private var confirmPassword = ""
    @State private var issuedRecovery: String?
    @State private var professionalRole = "Physician"
    @State private var otherRole = ""
    @State private var specialty = "Primary Care"
    @State private var otherSpecialty = ""
    @State private var isSaving = false
    @State private var errorMessage: String?

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

    private var canSubmit: Bool {
        !firstName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !lastName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && emailLooksValid
            && password.count >= 8
            && password == confirmPassword
            && !resolvedRole.isEmpty
            && !resolvedSpecialty.isEmpty
            && !isSaving
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Your name") {
                    TextField("First name", text: $firstName)
                        .textContentType(.givenName)
                        .accessibilityIdentifier("register.firstName")
                    TextField("Last name", text: $lastName)
                        .textContentType(.familyName)
                }
                Section("Sign-in details") {
                    TextField("Email", text: $email)
                        .textContentType(.username)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                    SecureField("Password (8+ characters)", text: $password)
                        .textContentType(.newPassword)
                        .accessibilityIdentifier("register.password")
                    SecureField("Confirm password", text: $confirmPassword)
                        .textContentType(.newPassword)
                }
                Section {
                    Picker("Professional role", selection: $professionalRole) {
                        ForEach(ProfileOptions.roles, id: \.self) { Text($0).tag($0) }
                    }
                    if professionalRole == "Other" {
                        TextField("Your role", text: $otherRole)
                    }
                    Picker("Primary specialty", selection: $specialty) {
                        ForEach(HealthcareSpecialties.groups) { group in
                            Section(group.name) {
                                ForEach(group.specialties.sorted(), id: \.self) { Text($0).tag($0) }
                            }
                        }
                        Text(HealthcareSpecialties.other).tag(HealthcareSpecialties.other)
                    }
                    if specialty == HealthcareSpecialties.other {
                        TextField("Your specialty", text: $otherSpecialty)
                    }
                } header: {
                    Text("Specialty")
                } footer: {
                    Text("The scan brief leads with what matters in this specialty. Add clinic details later in Settings.")
                }
                if let errorMessage {
                    Section {
                        Text(errorMessage).foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Create account")
            .navigationBarTitleDisplayMode(.inline)
            .alert("Save your recovery code", isPresented: Binding(
                get: { issuedRecovery != nil },
                set: { if !$0 { issuedRecovery = nil; dismiss() } }
            )) {
                Button("I saved it") { issuedRecovery = nil; dismiss() }
            } message: {
                Text(issuedRecovery ?? "")
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Create") {
                        Task { await create() }
                    }
                    .disabled(!canSubmit)
                    .accessibilityIdentifier("register.submit")
                }
            }
        }
    }

    @MainActor
    private func create() async {
        errorMessage = nil
        isSaving = true
        defer { isSaving = false }
        do {
            let auth = try await APIClient.shared.register(
                RegisterRequest(
                    firstName: firstName.trimmingCharacters(in: .whitespacesAndNewlines),
                    lastName: lastName.trimmingCharacters(in: .whitespacesAndNewlines),
                    email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                    password: password,
                    professionalRole: resolvedRole,
                    specialty: resolvedSpecialty
                )
            )
            APIClient.shared.sessionToken = auth.sessionToken
            appState.applySession(profile: auth.profile, token: auth.sessionToken, recoveryCode: auth.recoveryCode)
            if let code = auth.recoveryCode {
                issuedRecovery = code
            } else {
                dismiss()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
