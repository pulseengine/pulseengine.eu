# Adding Website Rebuild Trigger to Component Release Workflows

When a PulseEngine component (rivet, gale, sigil, etc.) publishes a release
that includes a compliance report, it should trigger a rebuild of
pulseengine.eu so the report appears on the website.

## Prerequisites

- `PULSEENGINE_DISPATCH_TOKEN` secret in the component repo
  - Fine-grained PAT with `contents: write` on `pulseengine/pulseengine.eu`
  - Or a GitHub App installation token scoped to pulseengine.eu

## Add to release workflow

After the step that creates the GitHub release, add:

````yaml
- name: Trigger website rebuild
  if: success()
  env:
    GH_TOKEN: ${{ secrets.PULSEENGINE_DISPATCH_TOKEN }}
  run: |
    gh api repos/pulseengine/pulseengine.eu/dispatches \
      --field event_type=compliance-report-updated \
      --field "client_payload[project]=${{ github.event.repository.name }}" \
      --field "client_payload[version]=${{ github.ref_name }}"
````

## Testing

1. Create a test release with a compliance report asset
2. Check that pulseengine.eu deploy workflow triggers
3. Verify the report appears at `pulseengine.eu/reports/<project>/<version>/compliance/`
