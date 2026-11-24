#!/usr/bin/env bash
# Rebuild AppleCore-1.2.1.jar from the original AppleCore-1.2.0.jar.
#
#   ./build.sh <AppleCore-1.2.0.jar> <vineflower.jar> <output jar>
#
# Decompiles the jar, applies patch.py to the two teleport command classes, compiles them against the original jar and
# the Paper API, and lets build.py put them back. Needs JDK 21, Python 3 and Maven on PATH; Maven is only
# used to resolve the Paper API for the compile classpath (through the AppleVoicechatMute pom).
# Vineflower: https://repo1.maven.org/maven2/org/vineflower/vineflower/1.11.1/vineflower-1.11.1.jar
set -euo pipefail

original=$(realpath "$1")
vineflower=$(realpath "$2")
output=$(realpath -m "$3")
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

pkg=fun/applecube/core/module/teleport
mkdir -p "$work/dec" "$work/src/$pkg" "$work/out"
# the whole jar, not just the two classes: with the other classes missing Vineflower names things differently
java -jar "$vineflower" -q "$original" "$work/dec" >/dev/null
cp "$work/dec/$pkg/RequestCommands.java" "$work/dec/$pkg/TeleportCommands.java" "$work/src/$pkg/"
python3 "$here/patch.py" "$work/src/$pkg"

mvn -q -B -f "$here/../../plugins/AppleVoicechatMute/pom.xml" dependency:build-classpath \
    -Dmdep.outputFile="$work/classpath.txt" -Dmdep.includeScope=provided
javac -nowarn -proc:none -encoding UTF-8 -cp "$original:$(cat "$work/classpath.txt")" -d "$work/out" "$work/src/$pkg"/*.java
python3 "$here/build.py" "$original" "$work/out" "$output"
