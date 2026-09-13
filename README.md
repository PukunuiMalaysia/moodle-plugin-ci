# Pukunui Moodle release validation

This reusable workflow provides the final hosted Moodle CI check for
`PukunuiMalaysia/moodle-marketplace-release`. Routine development testing runs in
the local Moodle lab. Plugin repositories must not add GitHub Moodle CI wrappers.

The central final-validation workflow supplies immutable, checksummed release and
upgrade artifacts and calls a reviewed full commit of this workflow. Only its
explicit manual final-validation action on `main` may run the Moodle matrix.
See the private release repository's operations guide for release preparation.

Public product documentation: [Pukunui documentation](https://pukunuimalaysia.github.io/moodle-docs/).
