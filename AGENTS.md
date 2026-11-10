# Branch maintenance

- Apply future code changes to both `main` (imperative UI) and `feature/training-declarative` (declarative UI), unless the user explicitly scopes a change to one branch.
- Keep the two UI implementations behaviorally aligned. Share backend behavior and transport contracts across the branches. Verify both branches before publishing.
