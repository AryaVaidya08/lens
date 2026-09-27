from app.retrieval.ingest import parse_dossier_fields


def test_parse_dossier_fields_handles_new_raw_field_dump_format():
    # ibuprofen.txt is "field_name:\n  value" with no blank lines.
    fields = parse_dossier_fields("ibuprofen")
    assert "purpose" in fields
    assert "pain reliever" in fields["purpose"].lower()


def test_parse_dossier_fields_handles_old_curate_openfda_format():
    # tylenol.txt is the older "## Section Title\ntext" format produced by
    # scripts/curate_openfda.py. Two of the four seeded demo drugs (Advil,
    # Tylenol) are in this format, so if the parser only understands the
    # new raw-field-dump format, their /summary content silently degrades
    # to the "no additional information" fallback for every tier.
    fields = parse_dossier_fields("tylenol")
    assert "indications_and_usage" in fields
    assert "temporarily relieves" in fields["indications_and_usage"].lower()
    assert "dosage_and_administration" in fields
    assert "warnings" in fields
