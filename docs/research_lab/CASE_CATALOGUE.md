# Case catalogue: reported unusual pre-news trading (held-out set)

**Status:** EXPLORATORY_HISTORICAL, `evidence_role: exploratory_historical`. Every case here is *reported*
unusual pre-news trading taken from public reporting. Nothing in this catalogue is evidence or proof of
insider activity, and AREPO makes no such claim. No private individual is named and no wallet address is
recorded.

Role: HELD-OUT evaluation set for the frozen unusual-flow detector (`UNUSUAL_FLOW_PROGRAMME.md` section 2
and 6). Maduro is the only tuning case and is excluded here. These cases are never used to change the
detector.

## Case-list hash (pinned before reading `UNUSUAL_FLOW_DETECTOR.md`)

`sha256("\n".join(sorted(condition_ids)))` over the 16 markets below:

**`6cea3fc56a1df06abd91da4a0d8fd20b1ba6c983f689dbe08b66999be02e8ebc`**

Pinned 2026-10-12 by the catalogue agent, which had not opened `UNUSUAL_FLOW_DETECTOR.md` at this
commit. Any case added later goes to the `post_freeze` bucket and is reported separately.

| case_id | market_id | condition_id | slug (truncated) |
|---|---|---|---|
| `nobel_peace_2025` | 560868 | `0x14a3dfeba8b22a32feb0f10763db68bc4d2abeb5bff90e9ae20de53793b35a1d` | `will-mara-corina-machado-win-the-nobel-peace-prize-in-2025` |
| `israel_strikes_iran_jun2025` | 551651 | `0x7f39808829da93cfd189807f13f6d86a0e604835e6f9482d8094fac46b3abaac` | `israel-military-action-against-iran-by-friday-477` |
| `israel_strikes_iran_jun2025` | 532742 | `0xd25ff3223a2233f6cd96a349455ca3237931c64358792f90c5f02d8cc39be38d` | `israel-military-action-against-iran-before-july` |
| `google_year_in_search_2025` | 635246 | `0xea17b1284d10617a57f910b2ea63bdef481b1724a4b899d454ff104bea67b657` | `will-d4vd-be-the-1-searched-person-on-google-this-year` |
| `google_year_in_search_2025` | 635230 | `0xb9b05c3a14c6a7c1c6c00a8c214ed154d4232a885f98ebfd01889204ed252931` | `will-pope-leo-xiv-be-the-1-searched-person-on-google-this-year` |
| `us_strikes_iran_feb2026` | 1198423 | `0x3488f31e6449f9803f99a8b5dd232c7ad883637f1c86e6953305a2ef19c77f20` | `us-strikes-iran-by-february-28-2026-227-967-547-688-589-491-592-418-45` |
| `us_strikes_iran_feb2026` | 1198479 | `0xdc4b9ecbfac2c8e98fe18b35c4578a3c64e34ddfe16b1cf8a98ab3ad9d06c088` | `will-us-or-israel-strike-iran-by-february-28-2026-766` |
| `khamenei_out_feb2026` | 916732 | `0x70909f0ba8256a89c301da58812ae47203df54957a07c7f8b10235e877ad63c2` | `khamenei-out-as-supreme-leader-of-iran-by-march-31` |
| `us_iran_ceasefire_apr2026` | 1706788 | `0x4c5701bcde0b8fb7d7f48c8e9d20245a6caa58c61a77f981fad98f2bfa0b1bc7` | `us-x-iran-ceasefire-by-april-7` |
| `us_iran_ceasefire_apr2026` | 1569627 | `0x773abaa5fe55e5cde51a261f444b7921652a4e059ead6b3be9fe56499c2d4609` | `us-x-iran-ceasefire-by-april-15` |
| `axiom_zachxbt_feb2026` | 1419011 | `0x804bc34275d7d610dea3293c06105e925ebfcd6e454813aa27d59a882d50e86d` | `will-axiom-be-accused-of-insider-trading` |
| `openai_model_dec2025` | 822860 | `0x4df1db0ea210284e2d79a237b9a50f62ca905d60cb05c6f763e94f3b0055d15e` | `will-openai-release-a-new-frontier-model-by-december-13-683` |
| `openai_model_dec2025` | 897817 | `0x4edfcf9fd9889864290d34f1902ef51420989e5922b8208bf46bc0689ce6adbe` | `will-openai-release-a-new-frontier-model-on-december-11` |
| `taylor_swift_engagement_aug2025` | 516906 | `0x89ac32e18929185f5bd0dc00e70337571f546e64ae5cd16dceb6026ac2679c1e` | `taylor-swift-and-travis-kelce-engaged-in-2025` |
| `pope_leo_may2025` | 525015 | `0x14197a2979391a7bb1e6918582334640f309c22c7718f824c9fa1e149302662f` | `will-robert-francis-prevost-be-the-next-pope` |
| `nobel_peace_2026` | 637072 | `0x9d010461e21b5f1cf40cb88ec75b84c326873ae1f1df91a031ff4fd5dfee9423` | `will-navi-pillay-win-the-nobel-peace-prize-in-2026` |

Machine-readable registry (events, news times, credibility status, sources):
`docs/research_lab/case_catalogue_registry.json` (written by `backend/scripts/case_catalogue_registry.py`).

Results, data availability and per-case timelines: pending (sections follow in later commits).
