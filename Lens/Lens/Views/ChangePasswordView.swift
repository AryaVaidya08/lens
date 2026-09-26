import SwiftUI

struct ChangePasswordView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss
    @State private var currentPassword = ""
    @State private var newPassword = ""
    @State private var confirmPassword = ""
    @State private var isSaving = false
    @State private var errorMessage: String?

    private var canSubmit: Bool {
        currentPassword.count >= 1
            && newPassword.count >= 8
            && newPassword == confirmPassword
            && newPassword != currentPassword
            && !isSaving
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    SecureField("Current password", text: $currentPassword)
                        .textContentType(.password)
                    SecureField("New password (8+ characters)", text: $newPassword)
                        .textContentType(.newPassword)
                    SecureField("Confirm new password", text: $confirmPassword)
                        .textContentType(.newPassword)
                } footer: {
                    Text("This signs out other sessions and issues a new recovery code.")
                }
                if let errorMessage {
                    Section { Text(errorMessage).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Change password")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { Task { await save() } }
                        .disabled(!canSubmit)
                }
            }
        }
    }

    @MainActor
    private func save() async {
        errorMessage = nil
        isSaving = true
        defer { isSaving = false }
        do {
            let auth = try await APIClient.shared.changePassword(current: currentPassword, new: newPassword)
            APIClient.shared.sessionToken = auth.sessionToken
            appState.applySession(profile: auth.profile, token: auth.sessionToken, recoveryCode: auth.recoveryCode)
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
