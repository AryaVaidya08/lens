# Clinic / hospital patient export

These files stand in for a hospital EHR or a doctor's practice database.
`app/clinic/ingest.py` parses them on startup (and when the app asks to refresh).

To point at a real system later, set:

```
CLINIC_API_URL=https://hospital.example/fhir/Patient
CLINIC_API_TOKEN=...
```

The remote payload can be a JSON array, `{ "patients": [...] }`, or a FHIR Bundle.
The iOS app never edits these records.
