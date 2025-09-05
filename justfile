default:
    @just --list

bump part="patch":
    uv run bump-my-version bump {{part}} --verbose

push:
    git push && git push --tags
