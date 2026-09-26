/// Keeps a retained camera view resumable without starting before its first layout
/// or allowing a late layout callback to start capture while another tab is open.
struct CameraSessionLifecycle {
    enum Event { case layoutReady, visible(Bool), active(Bool) }
    enum Action { case start, stop }

    private var isReady = false
    private var isVisible = false
    private var isActive = false
    private var isRunning = false

    mutating func handle(_ event: Event) -> Action? {
        switch event {
        case .layoutReady: isReady = true
        case .visible(let value): isVisible = value
        case .active(let value): isActive = value
        }
        let shouldRun = isReady && isVisible && isActive
        guard shouldRun != isRunning else { return nil }
        isRunning = shouldRun
        return shouldRun ? .start : .stop
    }
}
