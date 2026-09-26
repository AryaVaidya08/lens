import Foundation

enum ProfileOptions {
    static let roles = [
        "Physician", "Nurse Practitioner", "Physician Assistant", "Registered Nurse",
        "Clinical Nurse Specialist", "Nurse Anesthetist", "Midwife", "Pharmacist",
        "Dentist", "Optometrist", "Podiatrist", "Psychologist", "Therapist",
        "Dietitian / Nutritionist", "Social Worker", "Resident / Fellow",
        "Healthcare Student", "Other"
    ]

    static let practiceSettings = [
        "Private Practice", "Hospital", "Outpatient Clinic", "Academic Medical Center",
        "Community Health Center", "Urgent Care", "Retail / Community Pharmacy",
        "Long-Term Care", "Home Health", "Telehealth", "Other"
    ]

    static let sexes = ["Female", "Male", "Other", "Prefer not to say"]
}
