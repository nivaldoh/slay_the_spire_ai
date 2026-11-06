#!/bin/sh
# Builds the speed mod from this folder; usage: build.sh JAVAC_HOME OUTPUT.jar
# Compiles against the installed game and ModTheSpire; neither enters the jar.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
game="/mnt/c/Program Files (x86)/Steam/steamapps/common/SlayTheSpire/desktop-1.0.jar"
mts="/mnt/c/Program Files (x86)/Steam/steamapps/workshop/content/646570/1605060445/ModTheSpire.jar"
work=$(mktemp -d)
"$1/bin/javac" --release 8 -g -nowarn -cp "$game:$mts" -d "$work" "$here/SpeedPatch.java"
cp "$here/ModTheSpire.json" "$work/"
"$1/bin/jar" --create --file "$2" -C "$work" .
rm -rf "$work"
