[![make.fun · the-poster-for-a-place-that-i-2-20261121-0539](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/suwanangcrew025-ops/makefun-poster-nowhere/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/suwanangcrew025-ops/makefun-poster-nowhere/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)

# SOLMARA

A 1930s-style travel poster for a harbour town inside a drowned volcano
crater, where the sun sets straight through the crater gap into the bay.
White houses climb the terraced olive hill, a banded lighthouse keeps
watch from the umber headland, and sailboats cross the gold glitter
path on the teal sea.

`main.py` is pure Python (standard library only — no PIL, no font files):
it paints the scene into an RGB buffer, draws the name SOLMARA as stroke
geometry, and encodes the PNG by hand. It writes `entry.png`
(1024×1024, ≤ 1 MiB) to `$MAKEFUN_OUTPUT_DIR` (default `/output`),
deterministically, in about half a second.
