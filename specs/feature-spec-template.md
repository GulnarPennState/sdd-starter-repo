# Feature Specification — <feature name>

> Template for the Week 5 session and assignment. One feature per specification. If you are standing
> up a new system rather than adding to an existing one, you want a directory of these, not one long
> document.
>
> Fill every section. If a section does not apply, write *"n/a — <why>"* rather than deleting it; the
> empty section is information too.

**Status:** draft | in review | approved
**Author:**
**Reviewers:**
**Date:**

---
x
## 1. Intent

What problem this solves and for whom, in three or four sentences. Written so someone who has never
seen the codebase understands why this is worth building. No implementation detail here.

## 2. User stories

- As a `<role>`, I want `<capability>` so that `<outcome>`.
- …

Keep these small. If a story needs the word "and" twice, it is probably two stories.

## 3. Acceptance criteria

Numbered, concrete, and testable. Each one should be something you can write an assertion against.

1. Given `<state>`, when `<action>`, then `<observable result>`.
2. …

**Include the unhappy paths.** Empty input, bad input, no results, permission denied, the thing being
down. This is where specifications earn their keep — it is the part an agent will not invent for you.

## 4. Scope and non-goals

**In scope:**

**Explicitly out of scope:** — the section that stops an agent from helpfully building three more
things you did not ask for. Name the adjacent features you are *not* doing.

## 5. Interfaces and contracts

Endpoints, function signatures, data shapes, events. Request and response examples. What callers can
rely on, and what is allowed to change later.

## 6. Constraints

Only the rows that apply to your feature; delete the rest.

- **Design system / UI:** which component library, which existing patterns. No new components, no new
  colors.
- **Security:** authentication, authorization, data handling, anything that touches user data.
- **Performance:** limits that matter, with numbers.
- **Compatibility:** what must not break.
- **Other:** accessibility, localization, licensing.

*On a real team, most of this section comes from the skills your spec-authoring skill references,
rather than from your memory.*

## 7. Test plan

What gets tested at which level — unit, integration, end to end. Map the tests back to the acceptance
criteria in §3 by number; a criterion with no test is a criterion nobody is going to check.

## 8. Open questions

Things you do not know yet, and who can answer them. An honest open question is worth more than a
confident guess, because the guess is what the agent will build.

---

## Review checklist

Before this specification goes to an agent:

- [ ] Could someone who has never spoken to me build from this without asking me a question?
- [ ] Is every acceptance criterion testable as written?
- [ ] Are the unhappy paths covered?
- [ ] Does §4 name what we are *not* building?
- [ ] Are the constraints specific enough to constrain? ("Follow our design system" is not; naming the
      library and the components is.)
- [ ] Have the people who own the constraints — UX, QE, security — actually seen this?
