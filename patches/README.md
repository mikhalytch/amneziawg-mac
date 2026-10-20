# Darwin patch series

Apply the files in `series` in order to an exported `amneziawg-tools` tree.
`just prepare` does this with `git apply --check` followed by `git apply`.
The patches never modify the upstream submodule checkout.

Patches 01 and 02 reproduce all functional source changes from
`77garuda/amnezia-wg-mac` at commit
`7d3d26246fe5ccf3f6f5f5978c77f6dc55b0acba`. They were derived against tools
`v1.0.20260618-2`; that Darwin script is identical at the current pin,
`v3.1.20260812` (`ee0f0a9aa34ff0a0da4b3433b9512781cfe02843`).

Patch 03 adds the separately documented exclusion-route safety and SaveConfig
corrections on 2026-10-07. Patch 04 makes DNS updates idempotent on 2026-10-20
to avoid redundant preference writes during route-monitor callbacks. It still
corrects externally changed settings and preserves original DNS for cleanup.
All patches are GPL-2.0; original upstream
copyright/SPDX notices remain in the patched file.

When upstream changes, review its Darwin script, then regenerate the affected
patches against that revision using `a/src/wg-quick/darwin.bash` and
`b/src/wg-quick/darwin.bash` paths. Keep fixes separate from the custom extension.
Retire any change that upstream has incorporated. Run `just check-patches` and
`just test` before recording updated gitlinks and the README versions table.
