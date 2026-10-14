# Explicitly synthetic Wyscout metadata

These tiny records were hand-authored for loader tests. The clubs, players,
matches, and affiliation values are fictional; no third-party records were
copied. Competition `426` and season `181137` are the configured public-release
identifiers, not evidence that these synthetic matches occurred.

The two matches deliberately list player `101` for different historical teams.
All player `currentTeamId` values disagree with the match sheets. Player `109`
is an unused substitute, and player `777` and team `203` are unreferenced
metadata. Substitutions exercise a list, JSON null, and the source's string
`"null"` convention. Substitute minutes are inert fixture fields, not calculated
or consumed by Milestone 1a.

`events_Germany.json` is also entirely synthetic. It includes the transferred
player `101`, unknown player ID `0`, unresolved player ID `998`, and globally
known but unlisted player `777`. Empty tags/positions and blank subtypes are
intentional validation cases. These events are not a sample from a real match.
