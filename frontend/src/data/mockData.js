export const drugs = [
    {
        id: "ozempic",
        name: "Ozempic",
        genericName: "semaglutide",
        manufacturer: "Novo Nordisk",
        category: "GLP-1 receptor agonist",
        description:
        "A once-weekly injectable medication used as part of the management of certain patients with type 2 diabetes.",
        indications: [
        "Type 2 diabetes management",
        "Reduction of certain cardiovascular risks in eligible patients",
        ],
        mechanism:
        "Semaglutide is a GLP-1 receptor agonist that helps regulate blood glucose and appetite.",
        safety:
        "Review the official prescribing information for contraindications, warnings, precautions, and patient-specific considerations.",
        commonAdverseReactions: [
        "Nausea",
        "Vomiting",
        "Diarrhea",
        "Abdominal pain",
        ],
    },
    {
        id: "humira",
        name: "Humira",
        genericName: "adalimumab",
        manufacturer: "AbbVie",
        category: "TNF inhibitor",
        description:
            "A biologic medication used to treat several inflammatory and autoimmune conditions.",
        indications: [
            "Rheumatoid arthritis",
            "Psoriatic arthritis",
            "Crohn's disease",
            "Ulcerative colitis",
        ],
        mechanism:
            "Adalimumab is a monoclonal antibody that binds to and inhibits tumor necrosis factor (TNF).",
        safety:
            "Review the official prescribing information for boxed warnings, contraindications, infections, and other precautions.",
        commonAdverseReactions: [
            "Injection-site reactions",
            "Upper respiratory infections",
            "Headache",
            "Rash",
        ],
    },
    {
        id: "dupixent",
        name: "Dupixent",
        genericName: "dupilumab",
        manufacturer: "Sanofi / Regeneron",
        category: "Monoclonal antibody",
        description:
            "A biologic medication used for several inflammatory conditions involving type 2 inflammation.",
        indications: [
            "Atopic dermatitis",
            "Asthma",
            "Chronic rhinosinusitis with nasal polyps",
        ],
        mechanism:
            "Dupilumab blocks signaling through the interleukin-4 and interleukin-13 pathways.",
        safety:
            "Review the official prescribing information for contraindications, warnings, precautions, and monitoring considerations.",
        commonAdverseReactions: [
            "Injection-site reactions",
            "Conjunctivitis",
            "Eye irritation",
            "Sore throat",
        ],
    },
];

export const chats = [
    {
        id: "chat-001",
        drugId: "ozempic",
        drugName: "Ozempic",
        timestamp: "Today, 2:34 PM",
        preview: "What are the common adverse reactions?",
        messages: [
            {
                id: "msg-001",
                role: "user",
                text: "What are the common adverse reactions?",
            },
            {
                id: "msg-002",
                role: "assistant",
                text:
                "Common adverse reactions include nausea, vomiting, diarrhea, and abdominal pain.",
            },
            {
                id: "msg-003",
                role: "user",
                text: "How frequently is it administered?",
            },
            {
                id: "msg-004",
                role: "assistant",
                text:
                "It is administered once weekly. Refer to the prescribing information for dosing and administration details.",
            },
        ],
    },
    {
        id: "chat-002",
        drugId: "humira",
        drugName: "Humira",
        timestamp: "Yesterday, 11:18 AM",
        preview: "How does this medication work?",
        messages: [
        {
            id: "msg-005",
            role: "user",
            text: "How does this medication work?",
        },
        {
            id: "msg-006",
            role: "assistant",
            text:
            "Adalimumab is a monoclonal antibody that binds to and inhibits tumor necrosis factor, or TNF.",
        },
        ],
    },

    {
        id: "chat-003",
        drugId: "dupixent",
        drugName: "Dupixent",
        timestamp: "Sep 24, 2026",
        preview: "What conditions is this used to treat?",
        messages: [
        {
            id: "msg-007",
            role: "user",
            text: "What conditions is this used to treat?",
        },
        {
            id: "msg-008",
            role: "assistant",
            text:
            "Dupixent is used for several inflammatory conditions, including atopic dermatitis, asthma, and chronic rhinosinusitis with nasal polyps.",
        },
        ],
    },
];

export const currentHCP = {
    id: "hcp-demo-001",
    name: "Dr. Maya Patel",
    specialty: "Endocrinology",
    familiarity: {
        ozempic: "expert",
        humira: "new",
        dupixent: "returning",
    },
};