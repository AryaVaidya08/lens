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
                    Text("New accounts get a recovery code shown once. Patient folders appear after the clinic database is connected.")
                }

                #if DEBUG
                Section {
                    Button {
                        Task { await signIn(asDemo: true) }
                    } label: {
                        Label("Use demo account", systemImage: "person.crop.circle")
                    }
                    .disabled(isSigningIn)
                    .accessibilityIdentifier("auth.demoSignIn")
                } footer: {
                    Text("Explore Lens as Dr. Maya Patel with the sample patient records.")
                }
                #endif
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
    private func signIn(asDemo: Bool = false) async {
        guard !isSigningIn else { return }
        errorMessage = nil
        isSigningIn = true
        defer { isSigningIn = false }
        do {
            let auth = try await APIClient.shared.login(
                email: asDemo ? "maya.patel@lens.demo" : email.trimmingCharacters(in: .whitespacesAndNewlines),
                password: asDemo ? "demo" : password
            )
            APIClient.shared.sessionToken = auth.sessionToken
            var profile = auth.profile
            if let fetched = try? await APIClient.shared.getProfile(hcpId: auth.profile.id),
               fetched.id == auth.profile.id {
                profile = fetched
            }
            appState.applySession(profile: profile, token: auth.sessionToken, recoveryCode: auth.recoveryCode)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
