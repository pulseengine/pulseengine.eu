+++
title = "Measure your own repository"
template = "docs.html"
description = "Run the scripts behind our process posts on any git repository, and calibrate the classifier before you trust it"
weight = 90
+++

The numbers in [The machine arrived before the factory](/blog/the-machine-arrived-before-the-factory/) come from three scripts in this site's repository. They run on any git repository, not only ours, so you can check whether what we saw holds for your code.

They need `python3`, `git` and, for the issue tables, an authenticated [`gh`](https://cli.github.com/). Nothing else is installed.

```sh
git clone https://github.com/pulseengine/pulseengine.eu
cd pulseengine.eu/scripts
```

## One repository in depth

[`factory-metrics.py`](https://github.com/pulseengine/pulseengine.eu/blob/main/scripts/factory-metrics.py) prints a table per month: changes merged, files per change, the feature and fix share, how old the code a fix touched was, lines of source, and the issue backlog.

```sh
git clone https://github.com/<owner>/<repo>            # a FULL clone: line counts read file contents
./factory-metrics.py <repo> --issues <owner>/<repo> \
    --ext .rs \                                         # your source extensions, e.g. .py .ts .go
    --maintainers <login> [<login> ...] \               # logins that count as the project's own
    --line-age 2026-10 \                                # also blame the lines October's fixes changed
    --json <repo>.json
```

Two flags decide whether the output means anything for your project:

- **`--maintainers`.** Agents usually commit and file issues under a person's account, so the repository owner alone is rarely the whole team. Without it, every maintainer counts as an external author. On our own repositories that turns 2 external authors into 262.
- **`--ext`.** Line counts and fix age only look at these extensions. The default is `.rs`.

`--line-age` is slower, and it is the number to use for any claim about defect age. The default fix age counts days since the fixed *file* last changed. That is only a lower bound on the age of the *lines* a fix changed, and on our repositories it read 6 days where the changed lines were 177 days old. The script's header explains both.

[`factory-charts.py`](https://github.com/pulseengine/pulseengine.eu/blob/main/scripts/factory-charts.py) turns two such JSON files into the small-multiples figure:

```sh
./factory-charts.py mine=<repo>.json theirs=<other>.json > figure.svg
```

## Every repository at once

[`factory-census.py`](https://github.com/pulseengine/pulseengine.eu/blob/main/scripts/factory-census.py) runs the same measures over a directory of clones and tallies how many repositories show each pattern, so a result from two of them can be checked against the rest. Exclude forks, because their history is someone else's.

```sh
./factory-census.py <dir-of-clones> --issues-org <org> --json census.json
```

It only lets a repository vote when it has at least 20 changes, three active months, and conventional-commit prefixes on at least half of them, because a feature or fix share means nothing without the prefixes. Each pattern comes with a one-sided sign test, one repository one vote, so a few large repositories cannot outvote the rest.

## What these scripts cannot see

They read commit metadata and messages, so they measure what authors *said* a change was. "fix" relies on conventional-commit prefixes, or on a keyword rule where there are none, and the keyword rule is not reliable. If your project does not use the prefixes, classify the messages with a model instead, and calibrate it first: score it against commits whose label you already know, in both your population and a human-written one, before you trust a single share it reports. The follow-up post describes that method in detail.
