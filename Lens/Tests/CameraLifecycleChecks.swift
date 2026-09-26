@main
struct CameraLifecycleChecks {
    static func main() {
        var camera = CameraSessionLifecycle()
        precondition(camera.handle(.active(true)) == nil)
        precondition(camera.handle(.visible(true)) == nil)
        precondition(camera.handle(.layoutReady) == .start)
        precondition(camera.handle(.layoutReady) == nil)
        for _ in 0..<500 {
            precondition(camera.handle(.visible(false)) == .stop)
            precondition(camera.handle(.visible(false)) == nil)
            precondition(camera.handle(.layoutReady) == nil)
            precondition(camera.handle(.visible(true)) == .start)
            precondition(camera.handle(.visible(true)) == nil)
            precondition(camera.handle(.active(false)) == .stop)
            precondition(camera.handle(.active(true)) == .start)
        }
        precondition(camera.handle(.active(false)) == .stop)
        precondition(camera.handle(.visible(false)) == nil)
        precondition(camera.handle(.active(true)) == nil)
        precondition(camera.handle(.visible(true)) == .start)

        var lateLayout = CameraSessionLifecycle()
        precondition(lateLayout.handle(.active(true)) == nil)
        precondition(lateLayout.handle(.visible(true)) == nil)
        precondition(lateLayout.handle(.visible(false)) == nil)
        precondition(lateLayout.handle(.layoutReady) == nil)
        precondition(lateLayout.handle(.visible(true)) == .start)
        print("PASS: camera first layout, 500 tab/background cycles, duplicate events, hidden foreground, late layout")
    }
}
