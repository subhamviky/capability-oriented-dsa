# Security Policy

Report security-sensitive findings privately using GitHub's **Report a vulnerability** button (Security tab → Advisories), not in a public issue.

## Scope

This is a dependency-free reference library. It performs no I/O, networking, or persistence and reads only `DSA_*` environment variables. Relevant findings include, for example:

- inputs that make a kernel run unbounded (time or memory) despite a documented bound such as `maximum_paths` or `maximum_depth`;
- a validator that reports a corrupt structure as valid;
- `copy_on_read=True` returning an object that still aliases internal state.

Consumers of the standalone file own their copy: re-run the test suite after local modifications.
