# Symbolic links for ADLC5 scaffolding (source from every script that links).
# shellcheck shell=bash
#
# Git for Windows' ln -s silently deep-copies by default, so a "shared" file
# would quietly stop tracking its store. nativestrict creates real Windows
# symlinks and fails when the OS refuses them (Developer Mode off, no admin):
# https://www.msys2.org/docs/symlinks/

case "$(uname -s)" in
  MINGW*|MSYS*) export MSYS="${MSYS:+$MSYS }winsymlinks:nativestrict" ;;
esac

# adlc5_symlink [ln options] TARGET LINK — ln -s that explains a refusal.
adlc5_symlink() {
  local link="${*: -1}"
  if ! ln -s "$@"; then
    echo "ERROR: could not create symbolic link ${link}." >&2
    case "$(uname -s)" in
      MINGW*|MSYS*) echo "  Windows needs Developer Mode (Settings > System > For developers) or an elevated shell to create symlinks; ADLC5 does not fall back to copies." >&2 ;;
    esac
    return 1
  fi
}
