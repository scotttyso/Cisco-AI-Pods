.PHONY: sanity-ignore-sync sanity-ignore-check

sanity-ignore-sync:
	./scripts/sync-sanity-ignore.sh

sanity-ignore-check:
	@cmp -s tests/sanity/ignore-2.20.txt tests/sanity/ignore-2.16.txt || \
		(echo "Sanity ignore files are out of sync. Run: make sanity-ignore-sync" && exit 1)