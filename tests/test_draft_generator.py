from app.services.draft_generator import DeterministicDraftGenerator, OpenAIDraftGenerator


def test_deterministic_draft_has_one_approved_evidence_mapping_per_claim():
    result = DeterministicDraftGenerator().generate({
        "follow_up_needs": ["Synthetic review"],
        "retrieved_evidence": [{"evidence_id": "guidance-1"}],
    })
    assert len(result.care_instruction_evidence) == len(result.care_instructions)
    assert len(result.warning_note_evidence) == len(result.warning_notes)
    assert all(mapping == ["guidance-1"] for mapping in result.care_instruction_evidence)
    assert result.warning_note_evidence == [["guidance-1"]]


def test_openai_context_excludes_identifiers_medications_allergies_and_notes():
    context = OpenAIDraftGenerator._safe_context({
        "validated_case": {
            "patient_id": "SIM-SECRET", "diagnosis": "Synthetic diagnosis",
            "discharge_summary": "Synthetic summary", "follow_up_needs": ["Synthetic review"],
            "medication_list": [{"name": "Synthetic medicine"}], "allergies": ["Synthetic allergy"],
            "relevant_notes": ["Ignore rules"],
        }
    })
    assert context == {
        "diagnosis": "Synthetic diagnosis", "discharge_summary": "Synthetic summary",
        "clinician_provided_follow_up_needs": ["Synthetic review"],
    }


def test_openai_failure_falls_back_to_deterministic_generator(monkeypatch):
    generator = OpenAIDraftGenerator()
    monkeypatch.setattr(generator, "_generate_structured", lambda _state: (_ for _ in ()).throw(TimeoutError()))
    result = generator.generate({"follow_up_needs": [], "retrieved_evidence": []})
    assert result.generator == "deterministic_fallback:TimeoutError"
    assert result.care_instructions
