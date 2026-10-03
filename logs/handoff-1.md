Implement the feature specified in `specs/spec-v1.md`. Follow the conventions already in the repository.

## Assistant transcript

User: Implement the feature specified in `specs/spec-v1.md`. Follow the conventions already in the repository.

Assistant: I’m starting by reading the feature spec and the relevant implementation/test patterns so I can implement the required endpoint cleanly and verify it against the repo’s conventions.

Assistant to=functions.read_file: spec-v1.md
Assistant to=functions.read_file: app/routes/libraries.py
Assistant to=functions.read_file: app/models.py

Assistant: I’ve confirmed the feature is a ticket-triage API matching the repo’s pattern: model-backed routes, explicit request/response models, and repository-specific error handling. I’m checking the model task and route wiring next so the implementation lands in the right shape.

Assistant to=functions.grep_search: query "ticket|pending_review|/tickets|model_unavailable|model_timeout"
Assistant to=functions.read_file: app/main.py
Assistant to=functions.read_file: app/model_client.py
Assistant to=functions.read_file: app/routes/summary.py
Assistant to=functions.read_file: app/fixtures.py
Assistant to=functions.read_file: app/db.py
Assistant to=functions.read_file: tests/test_libraries.py
Assistant to=functions.read_file: specs/README.md

Assistant to=functions.multi_replace_string_in_file: Add ticket models and DB schema needed for ticket triage, and register the ticket router in the app.

Assistant to=functions.create_file: app/routes/tickets.py

Assistant: The feature is in place; I’m running the project’s required verification now to confirm the new ticket queue and the existing library endpoints still behave correctly together.

Assistant to=functions.run_in_terminal: cd /Users/gulnaraldaseva/sdd-starter-repo && make test

Result: 53 passed in 0.26s

Assistant to=functions.run_in_terminal: direct API smoke test for POST /tickets, GET /tickets, PATCH /tickets/{id}/review

Output: POST 201 pending_review 0.86
LIST 200 1
ACCEPT 200 accepted
CHANGE 200 changed high identity

Assistant to=functions.multi_replace_string_in_file: Tighten the review workflow to use atomic updates so a pending-ticket review cannot be accepted twice under concurrent requests, while keeping the existing 404/409/422 behavior.

Assistant to=functions.run_in_terminal: cd /Users/gulnaraldaseva/sdd-starter-repo && make test

Result: 53 passed in 0.19s

Final status: The feature described in `specs/spec-v1.md` has been implemented and verified against the repository’s test suite.
