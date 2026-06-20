# Changelog

## 1.1.9 - 2026-06-21

### Added
- Added `task_retries` for retrying task exceptions with result metadata for attempts and retry errors.
- Added `add_command` for direct external command execution.
- Added `add_shell_command` for shell command strings with pipes, redirects, globs, and command chaining.

### Changed
- Documented command task usage, shell command usage, and task retry examples in the README.

## 1.1.8 - 2026-06-20

### Fixed
- Updated the task lifecycle diagram to show the multiprocessing thread fallback path.
- Pointed README diagram image links at the `main` branch for the published release.

## 1.1.7 - 2026-06-13

### Fixed
- Restored fast task registration for dependency-free tasks by skipping cycle detection when `depends_on` is empty.

## 1.1.6 - 2026-06-13

### Fixed
- Replaced oversized README diagrams with compact PNG versions that fit better in GitHub and PyPI project pages.
- Pointed README diagram image links at the branch raw URLs so the compact images render before the branch is merged to `main`.

## 1.1.5 - 2026-06-13

### Fixed
- Fixed README diagram image URLs so GitHub branch views and PyPI render the generated PNG diagrams before the branch is merged to `main`.

## 1.1.4 - 2026-06-13

### Added
- Added deterministic multiprocessing picklability validation using `ForkingPickler`.
- Added opt-in thread fallback for unpicklable multiprocessing tasks with result metadata via `execution_mode` and `warning`.
- Added static README diagrams for PyPI-compatible rendering.
- Added tests for multiprocessing pickling failures, thread fallback, wrapper keyword handling, timeouts, aborts, and dependency edge cases.

### Fixed
- Prevented unpicklable multiprocessing tasks from hanging execution.
- Preserved terminated task results when timed-out or aborted thread/process workers finish later.
- Validated missing and cyclic task dependencies before execution can hang.
- Allowed task kwargs named `label` and `depends_on` through convenience APIs without colliding with framework metadata.

### Changed
- Expanded README guidance for dependency scheduling, execution modes, timeout semantics, background execution, and result metadata.
