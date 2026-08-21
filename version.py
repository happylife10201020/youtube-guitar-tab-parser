"""Single source of truth for the app version.

Rule (Semantic Versioning, MAJOR.MINOR.PATCH):
- MAJOR: breaking change in how the app is used, or a ground-up rework
- MINOR: new user-visible feature (e.g. auto-update, new output mode)
- PATCH: bug fix or internal change with no new feature

Release flow: bump this string in the same commit as the change, then push a
matching git tag `v<version>` (e.g. v1.2.0). CI refuses to build a release
whose tag does not match this file.
"""

APP_VERSION = "1.1.3"
