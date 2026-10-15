"""The existing four positional-proxy reviews, shared by local demos and UI."""

from .roles import PositionReview

EVIDENCE = (
    "https://github.com/4m4n5/fifa18-all-player-statistics/blob/"
    "dfa2c55b08f9c9dd0fb26e5db9585e026bf263a7/Complete/CompleteDataset.csv"
)

# Hand-reviewed name/age/club matches; these FIFA IDs are NOT Wyscout IDs.
# Inclusion is a demonstration decision based on the cited CM/CDM position proxy.
# Other Wyscout Midfielder entries stay unverified. Do not auto-expand this list.
DEMO_REVIEWS = {
    (3345, 2444): PositionReview(
        "included",
        EVIDENCE,
        "Thiago: FIFA 189509, age 26, Bayern, CDM/CAM/CM; demo positional proxy only.",
    ),
    (20475, 2444): PositionReview(
        "included",
        EVIDENCE,
        "Arturo Vidal: FIFA 181872, age 30, Bayern, CM/CDM; demo positional proxy only.",
    ),
    (224677, 2447): PositionReview(
        "included",
        EVIDENCE,
        "Julian Weigl: FIFA 222028, age 21, Dortmund, CM/CDM; demo positional proxy only.",
    ),
    (289711, 2975): PositionReview(
        "included",
        EVIDENCE,
        "Naby Keita: FIFA 220971, age 22, Leipzig, CAM/CDM/CM; demo positional proxy only.",
    ),
}
