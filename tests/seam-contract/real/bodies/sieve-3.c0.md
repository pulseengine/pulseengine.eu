Perennial by design (repo-hygiene): this issue is the living seam contract for sieve's CLI/JSON interface, not a task, and stays open. It is updated in the same change as any interface change, with consumers notified before a tag carries it.

Shipped in v0.1.0 (https://github.com/pulseengine/sieve/releases/tag/v0.1.0). `seam-check.py --party pulseengine/sieve`: exit 0 at the tag.