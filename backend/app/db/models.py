"""
Document shapes stored in MongoDB.

hcps hold the clinician account plus an ordered list of patient_ids.
Each id points at one document in patients. Passwords are stored hashed.
"""

# hcps (this is the clinician account collection — there is no `users`):
# {
#   _id, name, specialty, email, password_hash,
#   first_name, last_name, professional_role, credentials,
#   organization, practice_setting, work_phone, city, region, country,
#   patient_ids: [patient_id, ...],
#   created_at, account_source: "register" | "seed"
# }
# patients: {
#   _id, hcp_id, external_id, source, first_name, last_name, age, weight_kg, sex,
#   medical_history, allergies, current_medications, notes
# }
# Written only by app/clinic/sync.py from a clinic/EHR export.
# drugs:      { _id: str, name: str, barcode: str }
# engagements:{ _id: "hcp_id:drug_id", hcp_id, drug_id, touch_count, last_seen }
# chats:      { hcp_id, drug_id, question, answer, asked_at }
