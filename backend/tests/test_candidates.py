"""Core candidate behaviour through the HTTP API (real routes + service + repository,
in-memory MongoDB, fake summariser)."""


def names(response):
    return [c["name"] for c in response.json()]


# --- create & validation ---------------------------------------------------


def test_create_sets_defaults_and_summary(client, make_candidate, summariser):
    c = make_candidate(phone=None, source=None)
    assert c["stage"] == "Applied"
    assert c["notes"] == []
    assert c["archived"] is False
    assert c["ai_summary"]["status"] == "ok"
    assert len(summariser.calls) == 1


def test_create_rejects_bad_email_and_blank_name(client):
    base = {"name": "A", "email": "a@example.com", "role": "Dev"}
    assert client.post("/api/candidates", json={**base, "email": "not-an-email"}).status_code == 422
    assert client.post("/api/candidates", json={**base, "name": "   "}).status_code == 422


def test_create_still_saves_when_ai_fails(client, make_candidate, summariser):
    summariser.raise_error = True
    c = make_candidate()
    assert c["ai_summary"]["status"] == "failed"
    assert client.get(f"/api/candidates/{c['id']}").status_code == 200


# --- list: filter & sort ---------------------------------------------------


def test_filter_by_stage_role_and_both(client, make_candidate):
    make_candidate(name="A", role="Engineer", stage="Interview")
    make_candidate(name="B", role="Engineer", stage="Applied")
    make_candidate(name="C", role="Analyst", stage="Interview")

    assert sorted(names(client.get("/api/candidates?stage=Interview"))) == ["A", "C"]
    assert sorted(names(client.get("/api/candidates?role=Engineer"))) == ["A", "B"]
    assert names(client.get("/api/candidates?stage=Interview&role=Engineer")) == ["A"]


def test_sort_by_stage_uses_pipeline_order_not_alphabetical(client, make_candidate):
    # Alphabetical would give Applied, Interview, Offer, Rejected, Screening.
    for stage in ["Rejected", "Interview", "Applied", "Offer", "Screening"]:
        make_candidate(name=stage, stage=stage)

    asc = names(client.get("/api/candidates?sort=stage&order=asc"))
    assert asc == ["Applied", "Screening", "Interview", "Offer", "Rejected"]
    desc = names(client.get("/api/candidates?sort=stage&order=desc"))
    assert desc == list(reversed(asc))


def test_sort_by_date_added(client, make_candidate):
    for name in ["first", "second", "third"]:
        make_candidate(name=name)
    assert names(client.get("/api/candidates")) == ["third", "second", "first"]  # default newest first
    assert names(client.get("/api/candidates?order=asc")) == ["first", "second", "third"]


def test_list_does_not_return_resume_text(client, make_candidate):
    make_candidate()
    item = client.get("/api/candidates").json()[0]
    assert "resume_text" not in item and "notes" not in item


def test_roles_endpoint_returns_distinct_roles(client, make_candidate):
    make_candidate(role="Engineer")
    make_candidate(role="Engineer")
    make_candidate(role="Analyst")
    assert client.get("/api/roles").json() == ["Analyst", "Engineer"]


# --- stage -----------------------------------------------------------------


def test_any_stage_can_move_to_any_stage(client, make_candidate):
    c = make_candidate(stage="Rejected")
    r = client.patch(f"/api/candidates/{c['id']}/stage", json={"stage": "Screening"})
    assert r.json()["stage"] == "Screening"
    r = client.patch(f"/api/candidates/{c['id']}/stage", json={"stage": "Offer"})
    assert r.json()["stage"] == "Offer"


def test_invalid_stage_rejected(client, make_candidate):
    c = make_candidate()
    assert client.patch(f"/api/candidates/{c['id']}/stage", json={"stage": "Hired"}).status_code == 422


# --- notes -----------------------------------------------------------------


def test_notes_are_appended_with_timestamps_and_earlier_notes_kept(client, make_candidate):
    c = make_candidate()
    client.post(f"/api/candidates/{c['id']}/notes", json={"text": "First call went well"})
    r = client.post(f"/api/candidates/{c['id']}/notes", json={"text": "Booked interview"})

    notes = r.json()["notes"]
    assert [n["text"] for n in notes] == ["First call went well", "Booked interview"]
    assert all(n["created_at"] for n in notes)


def test_empty_note_rejected(client, make_candidate):
    c = make_candidate()
    assert client.post(f"/api/candidates/{c['id']}/notes", json={"text": "  "}).status_code == 422


def test_update_cannot_overwrite_notes(client, make_candidate):
    c = make_candidate()
    client.post(f"/api/candidates/{c['id']}/notes", json={"text": "keep me"})
    r = client.patch(f"/api/candidates/{c['id']}", json={"notes": []})  # unknown field is ignored
    assert [n["text"] for n in r.json()["notes"]] == ["keep me"]


# --- edit & summary regeneration ------------------------------------------


def test_editing_contact_details_does_not_call_ai(client, make_candidate, summariser):
    c = make_candidate()
    r = client.patch(f"/api/candidates/{c['id']}", json={"phone": "0400 000 000"})
    assert r.json()["phone"] == "0400 000 000"
    assert len(summariser.calls) == 1  # only the create


def test_editing_resume_regenerates_summary(client, make_candidate, summariser):
    c = make_candidate()
    client.patch(f"/api/candidates/{c['id']}", json={"resume_text": "New resume with Go and Rust"})
    assert len(summariser.calls) == 2
    assert summariser.calls[-1][0] == "New resume with Go and Rust"


def test_resending_identical_resume_does_not_call_ai(client, make_candidate, summariser):
    c = make_candidate()
    client.patch(f"/api/candidates/{c['id']}", json={"resume_text": c["resume_text"]})
    assert len(summariser.calls) == 1


def test_regenerate_endpoint(client, make_candidate, summariser):
    summariser.raise_error = True
    c = make_candidate()
    summariser.raise_error = False
    r = client.post(f"/api/candidates/{c['id']}/summary")
    assert r.json()["ai_summary"]["status"] == "ok"


# --- archive & delete ------------------------------------------------------


def test_archived_hidden_by_default_and_shown_on_request(client, make_candidate):
    keep = make_candidate(name="Active")
    gone = make_candidate(name="Archived")
    r = client.post(f"/api/candidates/{gone['id']}/archive")
    assert r.json()["archived"] is True and r.json()["archived_at"]

    assert names(client.get("/api/candidates")) == ["Active"]
    assert sorted(names(client.get("/api/candidates?include_archived=true"))) == ["Active", "Archived"]
    # Archived candidate is still readable (data kept)
    assert client.get(f"/api/candidates/{gone['id']}").status_code == 200
    assert keep  # silence unused


def test_unarchive_restores(client, make_candidate):
    c = make_candidate()
    client.post(f"/api/candidates/{c['id']}/archive")
    r = client.post(f"/api/candidates/{c['id']}/unarchive")
    assert r.json()["archived"] is False and r.json()["archived_at"] is None
    assert len(client.get("/api/candidates").json()) == 1


def test_delete_is_permanent(client, make_candidate):
    c = make_candidate()
    assert client.delete(f"/api/candidates/{c['id']}").status_code == 204
    assert client.get(f"/api/candidates/{c['id']}").status_code == 404


# --- not found -------------------------------------------------------------


def test_unknown_and_malformed_ids_return_404(client):
    for bad_id in ["000000000000000000000000", "not-an-object-id"]:
        assert client.get(f"/api/candidates/{bad_id}").status_code == 404
        assert client.delete(f"/api/candidates/{bad_id}").status_code == 404
        assert client.post(f"/api/candidates/{bad_id}/notes", json={"text": "x"}).status_code == 404
        assert client.patch(f"/api/candidates/{bad_id}/stage", json={"stage": "Offer"}).status_code == 404
