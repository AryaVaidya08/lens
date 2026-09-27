import Foundation

/// Display choices for the profile preview, not credential or billing codes.
/// Medical fields informed by ABMS: https://abms.org/member-boards/specialty-subspecialty-certificates/
/// Broader provider fields: https://taxonomy.nucc.org/
enum HealthcareSpecialties {
    struct Group: Identifiable {
        let name: String
        let specialties: [String]
        var id: String { name }
    }

    static let other = "Other / not listed"

    static let groups: [Group] = [
        Group(name: "Primary and preventive care", specialties: [
            "Primary Care", "Family Medicine", "Internal Medicine", "Geriatric Medicine",
            "Hospital Medicine", "Preventive Medicine", "Public Health",
            "Occupational Medicine", "Aerospace Medicine", "Sports Medicine"
        ]),
        Group(name: "Medical specialties", specialties: [
            "Allergy and Immunology", "Cardiology", "Clinical Cardiac Electrophysiology",
            "Interventional Cardiology", "Dermatology", "Endocrinology", "Gastroenterology",
            "Hematology", "Hematology and Oncology", "Hepatology", "Infectious Disease",
            "Medical Genetics", "Nephrology", "Oncology", "Pulmonology", "Rheumatology",
            "Sleep Medicine"
        ]),
        Group(name: "Acute care and symptom management", specialties: [
            "Anesthesiology", "Critical Care Medicine", "Emergency Medicine",
            "Urgent Care", "Medical Toxicology", "Pain Medicine", "Hospice and Palliative Medicine"
        ]),
        Group(name: "Surgical specialties", specialties: [
            "General Surgery", "Cardiothoracic Surgery", "Colorectal Surgery", "Neurosurgery",
            "Ophthalmology", "Orthopedic Surgery", "Otolaryngology (ENT)", "Pediatric Surgery",
            "Plastic Surgery", "Surgical Oncology", "Transplant Surgery", "Trauma Surgery",
            "Urology", "Vascular Surgery"
        ]),
        Group(name: "Women's health", specialties: [
            "Obstetrics and Gynecology", "Gynecologic Oncology", "Maternal-Fetal Medicine",
            "Reproductive Endocrinology and Infertility", "Urogynecology"
        ]),
        Group(name: "Pediatrics", specialties: [
            "Pediatrics", "Adolescent Medicine", "Developmental-Behavioral Pediatrics",
            "Neonatology", "Pediatric Cardiology", "Pediatric Critical Care",
            "Pediatric Emergency Medicine", "Pediatric Endocrinology", "Pediatric Gastroenterology",
            "Pediatric Hematology and Oncology", "Pediatric Infectious Disease",
            "Pediatric Nephrology", "Pediatric Pulmonology", "Pediatric Rheumatology"
        ]),
        Group(name: "Neurology and behavioral health", specialties: [
            "Neurology", "Child Neurology", "Epilepsy", "Neuromuscular Medicine",
            "Vascular Neurology", "Psychiatry", "Child and Adolescent Psychiatry",
            "Geriatric Psychiatry", "Addiction Medicine", "Addiction Psychiatry",
            "Psychology", "Behavioral Health Counseling"
        ]),
        Group(name: "Diagnostics and cancer treatment", specialties: [
            "Pathology", "Diagnostic Radiology", "Interventional Radiology",
            "Neuroradiology", "Nuclear Medicine", "Radiation Oncology"
        ]),
        Group(name: "Rehabilitation and allied health", specialties: [
            "Physical Medicine and Rehabilitation", "Physical Therapy", "Occupational Therapy",
            "Speech-Language Pathology", "Audiology", "Respiratory Therapy",
            "Nutrition and Dietetics", "Clinical Pharmacy", "Community Pharmacy",
            "Dentistry", "Oral and Maxillofacial Surgery", "Optometry", "Podiatry",
            "Nursing", "Midwifery", "Clinical Social Work"
        ])
    ]

    static func contains(_ specialty: String) -> Bool {
        groups.contains { $0.specialties.contains(specialty) }
    }
}
