User:
Implement the feature specified in `specs/spec-v2.md`. Follow the conventions already in the repository.

Assistant:
I’m reviewing the spec and the existing endpoint patterns first so I can implement the feature in the repository’s expected shape and verify it with the relevant tests.

Assistant to=functions.read_file:
- AGENTS.md
- specs/spec-v2.md
- app/routes/libraries.py
- app/models.py

Assistant:
I’ve confirmed the repo already contains the ticket models, so I’m checking the route and tests next to reconcile the implementation against the v2 spec and the actual app behavior.

Assistant to=functions.read_file:
- app/routes/tickets.py
- app/main.py
- tests/test_acceptance_criteria.py

Assistant to=functions.run_in_terminal:
Command: cd /Users/gulnaraldaseva/sdd-starter-repo && make test
Output:
64 passed, 1 skipped in 0.35s

Assistant to=functions.read_file:
- app/model_client.py
- app/db.py
- app/fixtures.py

Assistant:
The issue is isolated: the API is copying the single non-empty field into both ticket fields, which violates the spec’s “original text” requirement. I’m fixing that while keeping the queue and review behavior unchanged.

Assistant to=functions.multi_replace_string_in_file:
- app/routes/tickets.py: preserve original subject/body while still sending only the non-empty fields to the model

Assistant to=functions.run_in_terminal:
Command: cd /Users/gulnaraldaseva/sdd-starter-repo && make test
Output:
.F.....s.........................................................        [100%]
=================================== FAILURES ===================================
_____________________ test_ac2_subject_only_is_classified ______________________
... ValidationError: subject should have at least 1 character ...

Assistant:
The failing check confirms the remaining mismatch: the ticket schema still forbids an empty subject in a valid body-only submission. I’m adjusting the response model to match the spec’s valid “one field only” case without loosening the invalid-input checks.

Assistant to=functions.multi_replace_string_in_file:
- app/models.py: allow subject/body to be empty individually for valid one-field tickets while preserving empty-pair invalidation checks

Assistant to=functions.run_in_terminal:
Command: cd /Users/gulnaraldaseva/sdd-starter-repo && make test
Output:
64 passed, 1 skipped in 0.37s

Summary:
The API now preserves the original submitted text when a ticket contains only a subject or only a body, while still classifying the non-empty content correctly.

Files updated:
- app/routes/tickets.py
- app/models.py

Verification:
cd /Users/gulnaraldaseva/sdd-starter-repo && make test
Result: 64 passed, 1 skipped in 0.37s
