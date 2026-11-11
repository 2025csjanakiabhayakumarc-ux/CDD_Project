# Merge-Conflict Resolution Demo

## Scenario

Two team members independently edited `rules.yaml` on separate feature branches
that both branched from `develop`:

| Branch | Author | Change |
|--------|--------|--------|
| `conflict-demo/member1-adds-email` | Member 1 | Added `email` to required and missing-values lists |
| `conflict-demo/member3-adds-phone` | Member 3 | Added `phone` to the same lists + raised `max_errors` from 10 to 50 |

Both branches modify the **same lines** (the column lists under `required_columns`
and `missing_values`), so Git cannot auto-merge them.

---

## Step 1 — Merge branch A (clean)

```bash
git checkout develop
git merge conflict-demo/member1-adds-email --no-ff
```

This merges cleanly because `develop` has not diverged from branch A's base.

---

## Step 2 — Merge branch B (conflict)

```bash
git merge conflict-demo/member3-adds-phone
```

**Output:**

```
Auto-merging rules.yaml
CONFLICT (content): Merge conflict in rules.yaml
Automatic merge failed; fix conflicts and then commit the result.
```

---

## Step 3 — Inspect the conflict markers

Git inserts conflict markers into `rules.yaml`.  The file now looks like this:

```yaml
required_columns:
  columns:
    - name
    - age
<<<<<<< HEAD
    - email          # ← from branch A (already merged)
=======
    - phone          # ← from branch B (being merged)
>>>>>>> conflict-demo/member3-adds-phone

missing_values:
  columns:
    - name
    - age
<<<<<<< HEAD
    - email
=======
    - phone
>>>>>>> conflict-demo/member3-adds-phone

duplicates:
  subset: []

validation:
  max_errors: 50     # ← merged cleanly (only branch B touched this line)
```

### Reading the markers

| Marker | Meaning |
|--------|---------|
| `<<<<<<< HEAD` | Start of the current branch's version |
| `=======` | Divider between the two versions |
| `>>>>>>> conflict-demo/member3-adds-phone` | End of the incoming branch's version |

---

## Step 4 — Resolve

We want **both** columns, so we delete the markers and keep both lines:

```yaml
required_columns:
  columns:
    - name
    - age
    - email
    - phone

missing_values:
  columns:
    - name
    - age
    - email
    - phone

duplicates:
  subset: []

validation:
  max_errors: 50
```

---

## Step 5 — Complete the merge

```bash
git add rules.yaml
git commit -m "merge: resolve conflict — keep both email and phone columns"
```

---

## Before vs. After diffs

### Before resolution (conflict markers present)

```diff
 required_columns:
   columns:
     - name
     - age
+<<<<<<< HEAD
+    - email
+=======
+    - phone
+>>>>>>> conflict-demo/member3-adds-phone
```

### After resolution (clean file)

```diff
 required_columns:
   columns:
     - name
     - age
+    - email
+    - phone
```

---

## Git log after resolution

```
991a6df merge: resolve conflict — keep both email and phone columns
c5cf7b2 Merge branch 'conflict-demo/member1-adds-email' into develop
539e1c3 feat(config): require phone column, raise max_errors to 50
8c8aad8 feat(config): require email column in rules.yaml
42201c1 chore: add base rules.yaml config
```

---

## Key takeaways

1. **Conflicts happen when two branches edit the same lines** — not just the same file.
2. **Git marks the boundaries clearly** with `<<<<<<<`, `=======`, `>>>>>>>`.
3. **The developer decides the resolution** — Git never guesses. You can keep one side, the other, both, or write something entirely new.
4. **Non-overlapping changes merge cleanly** — `max_errors: 50` came through without conflict because only one branch touched that line.
5. **After resolving, `git add` + `git commit` completes the merge.**
