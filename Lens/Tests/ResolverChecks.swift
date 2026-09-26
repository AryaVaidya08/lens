import Foundation

@main
struct ResolverChecks {
    static func main() {
        let barcode = DrugResolver.cacheKey(kind: "barcode", value: "0363323012345")
        precondition(DrugResolver.cacheKey(rawPayload: "barcode: 0363323012345") == barcode)
        let text = DrugResolver.cacheKey(kind: "text", value: "NDC: 00543 Ativan")
        precondition(DrugResolver.cacheKey(rawPayload: "text: NDC: 00543 Ativan") == text)
        precondition(DrugResolver.cacheKey(rawPayload: "no-colon") == nil)
        print("PASS: detection payload keys round-trip through the resolver")
    }
}
