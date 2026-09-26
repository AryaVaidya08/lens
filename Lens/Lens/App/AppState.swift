//
//  App-wide observable state.
//
//  Single source of truth for "who is the demo user right now, what
//  drug are they looking at, and how familiar are they with it." Views
//  read/write this instead of passing data through init parameters.
//
//  Owned by: whole team — this is the shared contract between lanes.
//

import Foundation
import Combine

final class AppState: ObservableObject {
    @Published var selectedHCP: HCP?
    @Published var currentDrug: Drug?
    @Published var familiarityTier: String?

    // TODO: implement — add any additional shared state views need
    // (e.g. isDetecting, lastError) as the feature comes together.
}
