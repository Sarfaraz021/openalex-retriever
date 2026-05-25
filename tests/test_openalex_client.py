from openalex_client import classify_institution, OpenAlexClient


def test_classifies_clear_medical_university_as_high_confidence_school():
    result = classify_institution("Lusaka Apex Medical University", "education")

    assert result["category"] == "medical_school"
    assert result["confidence"] == "high"
    assert result["is_medical_school"] is True


def test_classifies_research_institute_as_related_not_school():
    result = classify_institution("Kenya Medical Research Institute", "facility")

    assert result["category"] == "related_medical_institution"
    assert result["confidence"] == "low"
    assert result["is_medical_school"] is False


def test_sample_strict_mode_excludes_related_institutions():
    client = OpenAlexClient()
    results = client.list_african_medical_schools(sample=True, strict_only=True, min_confidence="medium")

    assert len(results) == 2
    assert all(row["is_medical_school"] for row in results)
    assert "Kenya Medical Research Institute" not in {row["display_name"] for row in results}


def test_sample_broad_mode_includes_related_institutions():
    client = OpenAlexClient()
    results = client.list_african_medical_schools(sample=True, strict_only=False, min_confidence="low")

    names = {row["display_name"] for row in results}
    assert "Kenya Medical Research Institute" in names
