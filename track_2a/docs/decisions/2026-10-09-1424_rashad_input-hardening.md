## Input hardening (2026-10-09, from 14:24 UTC)

Branch `rashad/input-hardening`, from `main` at `25ed5fa` (after PR #12). Run with Claude Code on
Rashad's instructions. No model calls; the test split was not used.

- **The input is read as bytes and split on `b"\n"` only; `str.splitlines()` is not used on it.** `splitlines()` also breaks at U+2028, U+0085 and other characters that JSON allows raw inside a string, which cut such a claim's line in two and lost the case.
- **Per line: a trailing `"\r"` is removed, a UTF-8 byte order mark on the first line too, and the line is decoded with `errors="replace"`.** Windows line ends and a byte order mark must not cost a case; one byte that is not UTF-8 used to stop the whole run with no output file.
- **A final line break ends the last line; it does not start an empty one.** The progress log counts lines as before (`[1/2]`).
- **The output file (and `--raw`) is opened before the first case; each response is written and flushed as soon as it is ready.** A run that is stopped (time limit, out of memory) keeps every answer it already gave.
- **A repeated id is answered once, from its first line; later lines with the same id are logged and skipped.** The scorer counts an id with two responses as wrong; the first line is the one the input names first.
- **Ids are compared as their JSON text.** Any JSON value can be an id; a list or object would not fit in a set.
- **The three expected-failure tests now pass without the markers; the invalid-UTF-8 test expects the bad line to be answered too.** Its bytes sit inside a claim string, so after replacement the line is valid JSON with an id.
- **`STUB_SLOW` delays the fake model's answer after the call is logged (3 s by default, `Config.slow_seconds`).** The test sees the second request arrive and then reads the output file while that case still waits.
- **CI runs the examples a second time with `--context-a embed-e5-small`.** Since session 7 the default context answers the task A example without loading e5, so the first run no longer shows that the model loads as a non-root user on a read-only filesystem; with the plain `ADD --chmod=644` Dockerfile form (P11) the first run passes and the second fails (both checked locally as uid 1001).
- **In that CI step, `make` failures and the fallback check are tested explicitly (`PIPESTATUS`, `if grep`).** GitHub runs steps with `bash -e` without `pipefail`, and `! grep` in the middle of a script does not stop it.
- **The local image for the CI check was this branch's `src/` copied onto the existing image.** Docker Hub answered the base image pull with HTTP 429 in this sandbox; the Dockerfile and requirements have not changed since that image was built, and CI builds the real image.
