import copy
import json
import urllib.request
from pathlib import Path


UPSTREAM = "https://www.iamparadox.dev/jellyfin/plugins/manifest.json"

# We will take official Jellyfin 12.1 packages...
SOURCE_ABI = "12.1.0.0"

# ...and expose them to Jellyfin 12.2.
TARGET_ABI = "12.2.0.0"

OUTPUT = Path("manifest.json")


print(f"Downloading upstream manifest from:")
print(UPSTREAM)

request = urllib.request.Request(
    UPSTREAM,
    headers={
        # Deliberately NOT a Jellyfin-Server/12.2 User-Agent.
        # The upstream site currently returns [] to Jellyfin 12.2.
        "User-Agent": "IAmParadox-Jellyfin-12.2-Compat-Mirror/1.0"
    },
)

with urllib.request.urlopen(request, timeout=60) as response:
    upstream_manifest = json.load(response)


output_manifest = []

aliased = []
native = []
skipped = []


for plugin in upstream_manifest:
    versions = plugin.get("versions", [])

    # First see whether the developer has now published a REAL 12.2 build.
    official_12_2 = [
        version
        for version in versions
        if version.get("targetAbi") == TARGET_ABI
    ]

    if official_12_2:
        # Keep the newest official 12.2 package.
        chosen = max(
            official_12_2,
            key=lambda version: version.get("timestamp", "")
        )

        new_plugin = copy.deepcopy(plugin)
        new_plugin["versions"] = [copy.deepcopy(chosen)]
        output_manifest.append(new_plugin)

        native.append(plugin.get("name", "Unknown"))
        continue

    # Otherwise find official 12.1 builds.
    official_12_1 = [
        version
        for version in versions
        if version.get("targetAbi") == SOURCE_ABI
    ]

    if not official_12_1:
        skipped.append(plugin.get("name", "Unknown"))
        continue

    # Select the newest official 12.1 build.
    source = max(
        official_12_1,
        key=lambda version: version.get("timestamp", "")
    )

    # Clone it.
    compat = copy.deepcopy(source)

    # This is the ONLY compatibility field we alter.
    compat["targetAbi"] = TARGET_ABI

    old_changelog = compat.get("changelog") or ""

    compat["changelog"] = (
        "UNOFFICIAL TEMPORARY JELLYFIN 12.2 COMPATIBILITY ALIAS. "
        "This is the developer's official Jellyfin 12.1 binary, "
        "presented to Jellyfin as compatible with 12.2. "
        "It has NOT been rebuilt for 12.2.\n\n"
        + old_changelog
    )

    new_plugin = copy.deepcopy(plugin)

    # Only publish our relevant 12.2-compatible catalogue entry.
    new_plugin["versions"] = [compat]

    output_manifest.append(new_plugin)
    aliased.append(plugin.get("name", "Unknown"))


OUTPUT.write_text(
    json.dumps(output_manifest, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)


print()
print("==========================================")
print("Jellyfin 12.2 compatibility manifest built")
print("==========================================")
print()

print("12.1 packages aliased to 12.2:")
for name in aliased:
    print(f"  + {name}")

print()

print("Official/native 12.2 packages:")
if native:
    for name in native:
        print(f"  + {name}")
else:
    print("  None yet")

print()

print(f"Skipped because they have no 12.1/12.2 build: {len(skipped)}")
print()
print(f"Wrote {len(output_manifest)} plugins to {OUTPUT}")
