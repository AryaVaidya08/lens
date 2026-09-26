import SwiftUI

struct PersonaPickerView: View {
    @EnvironmentObject var appState: AppState
    @State private var email = ""
    @State private var password = ""
    @State private var isSigningIn = false
    @State private var errorMessage: String?
    @State private var isShowingRegister = false
    @State private var isShowingReset = false

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Text("Sign in with your email and password. Create an account if you don't have one yet.")
                        .foregroundStyle(.secondary)
                }

                Section("Sign in") {
                    TextField("Email", text: $email)
                        .textContentType(.username)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .accessibilityIdentifier("auth.email")
                    SecureField("Password", text: $password)
                        .textContentType(.password)
                        .accessibilityIdentifier("auth.password")
                    Button {
                        Task { await signIn() }
                    } label: {
                        if isSigningIn {
                            ProgressView()
                        } else {
                            Text("Sign in")
                        }
                    }
                    .disabled(isSigningIn || email.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || password.isEmpty)
                    .accessibilityIdentifier("auth.signIn")
                    Button("Forgot password") { isShowingReset = true }
                        .accessibilityIdentifier("auth.forgotPassword")
                    if let errorMessage {
                        Text(errorMessage)
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }
                }

                Section {
                    Button("Create an account") { isShowingRegister = true }
                        .accessibilityIdentifier("auth.createAccount")
                } footer: {
                    Text("New accounts get a recovery code shown once. Patient folders appear after the clinic database is connected. There is no guest or demo bypass.")
                }
            }
            .navigationTitle("Welcome to Lens")
            .sheet(isPresented: $isShowingRegister) {
                RegisterAccountView()
            }
            .sheet(isPresented: $isShowingReset) {
                ResetPasswordView()
            }
        }
    }

    @MainActor
    private func signIn() async {
        errorMessage = nil
        isSigningIn = true
        defer { isSigningIn = false }
        do {
            let auth = try await APIClient.shared.login(
                email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                password: password
            )
            APIClient.shared.sessionToken = auth.sessionToken
            appState.applySession(profile: auth.profile, token: auth.sessionToken, recoveryCode: auth.recoveryCode)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
