---
title: Pukunui Moodle Plugin CI
---

# Pukunui Moodle Plugin CI

Pukunui Moodle Plugin CI is the reusable GitHub Actions workflow used by Pukunui Moodle plugin repositories for Marketplace-oriented validation across maintained Moodle, PHP, and database combinations.

## What it checks

Caller repositories can run PHP lint, PHP Mess Detector, Moodle CodeSniffer with zero warnings, PHPDoc validation, plugin validation, upgrade savepoints, Mustache lint, frontend lint, PHPUnit, and Behat. The central matrix covers supported PHP releases with PostgreSQL and MariaDB.

## Using the workflow

Create a small caller workflow in the plugin repository that is triggered for pull requests and relevant branch pushes, grants only read permissions unless a job explicitly needs more, and calls:

```yaml
jobs:
  ci:
    uses: PukunuiMalaysia/moodle-plugin-ci/.github/workflows/ci.yml@main
```

Use an immutable release tag or commit SHA for third-party consumers. A plugin with a narrower Moodle support range should pass the workflow inputs documented by the reusable workflow instead of running an unrelated default matrix.

Do not pass production credentials or broadly inherit secrets. CI logs and artifacts must not contain tokens, private URLs, database dumps, or personal data.

## Support

- [Report a CI problem or request an improvement](https://github.com/PukunuiMalaysia/moodle-docs/issues/new?template=feature.yml)
- [Pukunui Plugin Subscription Terms & Support Policy](https://pukunui.com/docs/policy-moodle-marketplace/)
- [Pukunui Malaysia](https://pukunui.com/home/location/malaysia/)

Original documentation copyright Pukunui Sdn Bhd and contributors, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
