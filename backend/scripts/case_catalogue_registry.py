# ruff: noqa: E501  (source URLs)
"""Write the case-catalogue registry (docs/research_lab/case_catalogue_registry.json).

EXPLORATORY_HISTORICAL. Each case is *reported* unusual pre-news trading from public reporting; no
case is treated as established insider activity. No private individual is named and no wallet
address is recorded. Maduro is excluded (detector tuning case, see CASE_STUDY_MADURO.md).
"""

from __future__ import annotations

from pathlib import Path

from astrolabe.research_lab.case_catalogue import CaseSpec, Source, registry_json

S = Source
OUT = Path(__file__).resolve().parents[2] / "docs" / "research_lab" / "case_catalogue_registry.json"

CASES = [
    CaseSpec(
        "nobel_peace_2025", "awards", "polymarket",
        "2025 Nobel Peace Prize awarded to Maria Corina Machado",
        "2025-10-10T09:00:00Z", "official announcement 11:00 Oslo (CEST)", 0.1, "official_probe",
        "Newly created or recently opened accounts bought the eventual winner at low odds in the "
        "hours before the announcement; price reported moving from low single digits to ~70% "
        "before 09:00 UTC. The Norwegian Nobel Institute opened a review of a possible leak.",
        slugs=['will-mara-corina-machado-win-the-nobel-peace-prize-in-2025'],
        reported_outcome="Machado: Yes",
        sources=[
            S("https://www.bloomberg.com/news/articles/2025-10-10/unusual-bets-on-nobel-peace-prize-winner-prompt-probe-into-leaks", "Bloomberg", "news"),
            S("https://www.theblock.co/post/374199/officials-probe-polymarket-over-suspicious-trades-predicting-nobel-peace-prize-winner-reports", "The Block", "news"),
            S("https://decrypt.co/343840/nobel-peace-prize-organizers-intestigating-polymarket-insider-trades", "Decrypt", "news"),
            S("https://protos.com/polymarket-traders-accused-of-insider-trading-nobel-peace-prize/", "Protos", "news"),
            S("https://cointelegraph.com/news/nobel-peace-prize-polymarket-investigation", "Cointelegraph", "news"),
        ]),
    CaseSpec(
        "israel_strikes_iran_jun2025", "war_geopolitics", "polymarket",
        "Israel's opening strikes on Iran (start of the 12-day war)",
        "2025-06-13T00:00:00Z", "first strikes ~03:00 Israel time 13 Jun 2025", 1.0, "charged",
        "An Israeli indictment (Feb 2026) alleges a reservist passed strike-timing information to "
        "a civilian who bet on Polymarket, reportedly winning ~$150k-163k on Israel military "
        "action against Iran; figures differ by outlet. Market-level timing not public.",
        slugs=['israel-military-action-against-iran-by-friday-477', 'israel-military-action-against-iran-before-july'],
        reported_outcome="Yes",
        sources=[
            S("https://www.timesofisrael.com/israeli-air-force-major-charged-with-using-classified-info-to-place-bets-on-polymarket/", "Times of Israel", "court"),
            S("https://www.theblock.co/post/389575/israeli-defense-reservist-civilian-indicted-over-alleged-insider-betting-on-polymarket-reports", "The Block", "news"),
            S("https://www.jns.org/israelis-indicted-on-charges-of-gambling-using-classified-information/", "JNS", "news"),
        ]),
    CaseSpec(
        "google_year_in_search_2025", "search_rankings", "polymarket",
        "Google 2025 Year in Search published",
        "2025-12-04T05:00:00Z", "publication 4 Dec 2025; most person markets closed ~07:30 UTC; exact time unconfirmed", 6.0,
        "charged",
        "One account won ~$1M across Year-in-Search markets (22 of 23 calls reported), "
        "including a low-probability top-person outcome; US federal charges (May 2026) allege use "
        "of confidential company data, sometimes within hours of access. Allegations untested.",
        slugs=['will-d4vd-be-the-1-searched-person-on-google-this-year', 'will-pope-leo-xiv-be-the-1-searched-person-on-google-this-year'],
        reported_outcome="d4vd: Yes (most searched person) and No on favourites",
        sources=[
            S("https://thedefiant.io/news/defi/polymarket-users-suspect-insider-trading-after-google-trend-markets-crown-surprise-winner", "The Defiant", "news"),
            S("https://crypto-economy.com/insider-trading-fears-emerge-after-1m-polymarket-win-on-google-search-activity/", "Crypto Economy", "news"),
            S("https://androidauthority.com/google-employee-accused-of-insider-trading-3672044/", "Android Authority", "news"),
            S("https://de.euronews.com/2026/05/28/google-ingenieur-wegen-angeblichen-polymarket-insiderhandels-uber-12-mio-dollar-angeklagt", "Euronews", "court"),
        ]),
    CaseSpec(
        "us_strikes_iran_feb2026", "war_geopolitics", "polymarket",
        "US-Israeli strikes on Iran, 28 Feb 2026",
        "2026-02-28T06:15:00Z", "Israeli announcement / sirens ~08:14 local; Tehran blasts that "
        "morning (exact UTC unconfirmed)", 2.0, "alleged",
        "Bubblemaps flagged six wallets created in February, mostly funded within 24h, that "
        "bought Yes on 'US strikes Iran by February 28, 2026?' hours before the strikes; ~$1.0-1.2M "
        "combined profit (estimates differ). Bloomberg and Al Jazeera covered the wider pattern.",
        slugs=['us-strikes-iran-by-february-28-2026-227-967-547-688-589-491-592-418-452-924-384-915-464-672-196-157-993-596-269-535-381-391-471-256-988-997-296-225-762-973-292-827-345-182-558-215-794-879-189-761', 'will-us-or-israel-strike-iran-by-february-28-2026-766'],
        reported_outcome="Yes",
        sources=[
            S("https://www.theblock.co/post/391650/fresh-accounts-netted-1-million-on-polymarket-hours-before-us-airstrikes-on-iran-bubblemaps", "The Block", "news"),
            S("https://www.forbes.com/sites/boazsobrado/2026/03/02/fresh-wallets-made-12m-on-polymarket-hours-before-iran-airstrikes/", "Forbes", "news"),
            S("https://cointelegraph.com/news/bubblemaps-polymarket-cluster-win-military-bets", "Cointelegraph (Bubblemaps)", "onchain_analyst"),
            S("https://aljazeera.com/news/2026/3/25/large-polymarket-wall-street-bets-on-trumps-war-news-under-scrutiny", "Al Jazeera", "news"),
        ]),
    CaseSpec(
        "khamenei_out_feb2026", "war_geopolitics", "polymarket",
        "Strike that killed Iran's Supreme Leader (28 Feb 2026)",
        "2026-02-28T06:15:00Z", "first news of the initial strike (as C04); death confirmed "
        "later", 3.0, "alleged",
        "An account reportedly made ~$553k on Khamenei markets, with a trade reported ~71 minutes "
        "before news of the initial strike; Polysights flagged new-wallet buying of 'Khamenei out' "
        "in mid-January. Resolution of the main contracts was disputed.",
        slugs=['khamenei-out-as-supreme-leader-of-iran-by-march-31'],
        reported_outcome="Yes",
        sources=[
            S("https://www.kjzz.org/npr-top-stories/2026-03-01/prediction-market-trader-magamyman-made-553-000-on-death-of-irans-supreme-leader", "NPR (KJZZ)", "news"),
            S("https://news.bgov.com/securities-law/polymarket-bettors-in-limbo-as-khameneis-time-of-death-debated", "Bloomberg Law", "news"),
            S("https://www.businesstoday.in/latest/trends/story/500-million-betting-frenzy-crypto-bets-on-khameneis-fate-puts-trump-linked-polymarket-under-lens-518841-2026-03-02", "Business Today", "news"),
        ]),
    CaseSpec(
        "us_iran_ceasefire_apr2026", "war_geopolitics", "polymarket",
        "US-Iran two-week ceasefire announced on Truth Social, 7 Apr 2026",
        "2026-04-07T22:30:00Z", "post ~6:30pm ET (AP); another outlet reports 4:30pm", 2.0,
        "alleged",
        "AP/Dune analysis: at least 50 wallets made their first-ever Polymarket trades as "
        "substantial Yes bets before the announcement; one wallet created that morning bought "
        "~$72k at ~8.8c. Market later marked disputed. A US senator requested answers.",
        slugs=['us-x-iran-ceasefire-by-april-7', 'us-x-iran-ceasefire-by-april-15'],
        reported_outcome="Yes",
        sources=[
            S("https://wtop.com/national/2026/04/newly-created-polymarket-accounts-bet-big-on-us-iran-ceasefire-in-hours-before-trumps-announcement/", "AP (via WTOP)", "news"),
            S("https://www.blumenthal.senate.gov/newsroom/press/release/blumenthal-demands-answers-from-polymarket-following-suspicious-bets-on-ceasefire", "US Senate office", "regulator"),
            S("https://www.kuow.org/stories/well-timed-bets-on-polymarket-tied-to-the-iran-war-draw-calls-for-investigations-from-lawmakers", "NPR (KUOW)", "news"),
        ]),
    CaseSpec(
        "axiom_zachxbt_feb2026", "corporate_crypto", "polymarket",
        "Investigator's exposé names Axiom (26 Feb 2026)",
        "2026-02-26T13:00:00Z", "release-hour market resolved 8-9am (ET assumed) = 13-14 UTC", 1.0, "alleged",
        "A market on which company an on-chain investigator would expose drew ~$40M; at least "
        "12 wallets, several fresh, bought the eventual answer at low odds (one at ~13.8%) before "
        "publication; ~$1M+ combined profit reported.",
        slugs=['will-axiom-be-accused-of-insider-trading'],
        reported_outcome="Axiom: Yes",
        sources=[
            S("https://www.coindesk.com/markets/2026/02/27/polymarket-bettors-appear-to-have-insider-traded-on-a-market-designed-to-catch-insider-traders", "CoinDesk", "news"),
            S("https://cointelegraph.com/news/suspected-insider-1-2m-zachxbt-axiom-expose", "Cointelegraph", "news"),
            S("https://decrypt.co/359223/y-combinator-backed-axiom-employees-accused-insider-trading-zachxbt", "Decrypt", "news"),
        ]),
    CaseSpec(
        "openai_model_dec2025", "corporate_tech", "polymarket",
        "OpenAI GPT-5.2 release (11 Dec 2025)",
        "2025-12-11T18:00:00Z", "launch day; exact time unconfirmed", 6.0, "speculative",
        "Several accounts bought 'OpenAI releases a new model by Dec 13' in the week before; four "
        "accounts gained ~$13k combined. Small sizes; no insider link confirmed.",
        slugs=['will-openai-release-a-new-frontier-model-by-december-13-683', 'will-openai-release-a-new-frontier-model-on-december-11'],
        reported_outcome="Yes",
        sources=[
            S("https://www.itiger.com/news/1128153844", "Tiger Brokers news", "news"),
            S("https://finance.yahoo.com/news/one-polymarket-user-made-more-164427975.html", "Yahoo Finance", "news"),
        ]),
    CaseSpec(
        "taylor_swift_engagement_aug2025", "entertainment", "polymarket",
        "Taylor Swift and Travis Kelce engagement announced (26 Aug 2025)",
        "2025-08-26T16:00:00Z", "Instagram post, US midday; exact time unconfirmed", 3.0,
        "speculative",
        "A small account bought Yes within ~15h of the announcement (~$2k stake, ~$3k profit) and "
        "reportedly moved the price from ~25% to ~45%; online speculation about the account's "
        "identity is unconfirmed and a fact-check called the leak claim speculative.",
        slugs=['taylor-swift-and-travis-kelce-engaged-in-2025'],
        reported_outcome="Yes",
        sources=[
            S("https://www.aol.com/polymarket-trader-made-50k-betting-174743223.html", "AOL", "news"),
            S("https://beincrypto.com/taylor-swift-polymarket-engagement-guitarist/", "BeInCrypto", "news"),
            S("https://casinobeats.com/2025/08/28/taylor-swift-engagement-foretold-by-prediction-market-price-changes-on-polymarket-kalshi/", "CasinoBeats", "news"),
        ]),
    CaseSpec(
        "pope_leo_may2025", "religion_announcements", "polymarket",
        "Cardinal Prevost elected Pope Leo XIV (8 May 2025)",
        "2025-05-08T16:07:00Z", "white smoke 18:07 Rome; name announced ~17:13 UTC", 0.1,
        "public_or_luck",
        "Contrast case: the winner was a 1-2% long shot; one account turned ~$1k into ~$64k. "
        "Reporting framed it as a market miss, not suspected leakage (the conclave is sealed).",
        slugs=['will-robert-francis-prevost-be-the-next-pope'],
        reported_outcome="Prevost: Yes",
        sources=[
            S("https://edition.cnn.com/2025/05/09/business/online-betting-markets-failed-pope", "CNN", "news"),
            S("https://www.nbcdfw.com/news/business/money-report/online-bettors-spent-over-40-million-gambling-on-the-identity-of-the-next-pope-one-winner-made-52000-on-a-longshot/3837659/", "CNBC (via NBC)", "news"),
        ]),
    CaseSpec(
        "nobel_peace_2026", "awards", "polymarket",
        "2026 Nobel Peace Prize announcement (9 Oct 2026)",
        "2026-10-09T09:00:00Z", "official announcement 11:00 Oslo", 0.1, "no_report",
        "Contrast case: same market family as nobel_peace_2025, no reported unusual pre-news "
        "activity (one sponsored piece described activity as ordinary).",
        slugs=["will-navi-pillay-win-the-nobel-peace-prize-in-2026"],
        reported_outcome="(no report; winner market used)",
        sources=[
            S("https://time.com/partner-content/prediction-markets/nobel-peace-prize-betting-surges-after-last-years-suspected-breach/", "TIME partner content", "sponsored"),
        ]),
]


def main() -> None:
    OUT.write_text(registry_json(CASES) + "\n")
    print(f"wrote {OUT} ({len(CASES)} cases)")


if __name__ == "__main__":
    main()
