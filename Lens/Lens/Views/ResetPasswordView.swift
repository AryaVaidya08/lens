import Combine
import SwiftUI

struct ResetPasswordView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var email = ""
    @State private var recoveryCode = ""
    @State private var newPassword = ""
    @State private var confirmPassword = ""
    @State private var resetToken: String?
    @State private var expiresAt: Date?
    @State private var now = Date()
    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var newRecoveryCode: String?

    private var remaining: TimeInterval {
        guard let expiresAt else { return 0 }
        return max(0, expiresAt.timeIntervalSince(now))
    }

    private var isExpired: Bool { resetToken != nil && remaining <= 0 }

    private var canVerify: Bool {
        email.contains("@")
            && !recoveryCode.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !isSaving
    }

    private var canReset: Bool {
        resetToken != nil
            && !isExpired
            && newPassword.count >= 8
            && newPassword == confirmPassword
            && !isSaving
    }

    var body: some View {
        NavigationStack {
            Form {
                if let newRecoveryCode {
                    Section("Save this new recovery code") {
                        Text(newRecoveryCode)
                            .font(.title3.monospaced())
                            .textSelection(.enabled)
                        Text("The previous code no longer works. Sign in with your new password.")
                            .foregroundStyle(.secondary)
                    }
                } else if resetToken != nil {
                    Section {
                        if isExpired {
                            Text("This reset expired after 15 minutes. Start again.")
                                .foregroundStyle(.red)
                        } else {
                            Text("This reset expires in \(countdown) and can be used only once.")
                                .foregroundStyle(.secondary)
                        }
                        SecureField("New password (8+ characters)", text: $newPassword)
                            .textContentType(.newPassword)
                            .accessibilityIdentifier("reset.password")
                        SecureField("Confirm new password", text: $confirmPassword)
                            .textContentType(.newPassword)
                    }
                } else {
                    Section {
                        TextField("Email", text: $email)
                            .textContentType(.username)
                            .keyboardType(.emailAddress)
                            .textInputAutocapitalization(.never)
                            .accessibilityIdentifier("reset.email")
                        SecureField("Recovery code", text: $recoveryCode)
                            .textInputAutocapitalization(.characters)
                            .accessibilityIdentifier("reset.recoveryCode")
                    } footer: {
                        Text("After this checks out, you have 15 minutes to set a new password. That step works only once.")
                    }
                }
                if let errorMessage {
                    Section { Text(errorMessage).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Reset password")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(newRecoveryCode == nil ? "Cancel" : "Done") { dismiss() }
                }
                if newRecoveryCode == nil {
                    ToolbarItem(placement: .confirmationAction) {
                        if resetToken == nil {
                            Button("Continue") { Task { await startReset() } }
                                .disabled(!canVerify)
                                .accessibilityIdentifier("reset.continue")
                        } else {
                            Button("Reset") { Task { await finishReset() } }
                                .disabled(!canReset)
                                .accessibilityIdentifier("reset.submit")
                        }
                    }
                }
            }
            .onReceive(Timer.publish(every: 1, on: .main, in: .common).autoconnect()) { date in
                now = date
            }
        }
    }

    private var countdown: String {
        let total = Int(remaining.rounded(.down))
        return String(format: "%d:%02d", total / 60, total % 60)
    }

    @MainActor
    private func startReset() async {
        errorMessage = nil
        isSaving = true
        defer { isSaving = false }
        do {
            let started = try await APIClient.shared.requestPasswordReset(
                email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                recoveryCode: recoveryCode.trimmingCharacters(in: .whitespacesAndNewlines)
            )
            resetToken = started.resetToken
            expiresAt = Date().addingTimeInterval(TimeInterval(started.expiresIn))
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @MainActor
    private func finishReset() async {
        guard let resetToken, !isExpired else {
            errorMessage = "This reset expired after 15 minutes. Start again."
            return
        }
        errorMessage = nil
        isSaving = true
        defer { isSaving = false }
        do {
            let result = try await APIClient.shared.resetPassword(
                email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                resetToken: resetToken,
                newPassword: newPassword
            )
            newRecoveryCode = result.recoveryCode
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
