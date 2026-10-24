# CB13 labeller audit definitions (CREATIVE_BATCH_13.md, verbatim)
1. **SPORTS-FEED**: a sports fee type or category (`sports_fees*`), a frozen sports series or slug list, or the frozen
   sports title regex (CB12 §0.4's list plus "vs.", "O/U", spread and moneyline forms). Reported, uncounted.
2. **PATH-SETTLED**: an asset term (frozen crypto, equity, index, commodity and FX lists) together with a price form
   ("Up or Down", above/below, reach/hit/dip, "price of", "close at/above", "between $"); or fee type
   `crypto_fees*`/`finance_prices_fees`.
3. **PUBLIC-STATISTIC**: a published number from a named statistical source (macro releases: CPI, inflation,
   unemployment, payrolls, GDP, jobless claims; temperature and precipitation; earthquake counts and magnitudes; box
   office; review and chart scores; post or tweet counts; poll and approval numbers); or `weather_fees`. Earthquake
   markets stay in this class (CB12-E is historical before 2026-10-01 plus its own live collector, §1.3).
4. **SCHEDULED-EVENT**: an event with a public date (elections, primaries, nominations, debates, award shows, Fed/FOMC
   and central-bank decisions, earnings, court rulings with a set date, speeches and mention markets, launches and
   votes with a scheduled time); or `mentions_fees`. Reported, uncounted.
5. **UNSCHEDULED-NEWS**: every other non-sports market, mostly "will X happen by <date>" (resign, out as, ceasefire,
   strike, invade, deal, release, indictment, announcement, death).
6. **UNKNOWN**: no title and no sidecar row. Excluded and counted (> 5% of SCREEN fills → GL fails).

**LOW = PATH-SETTLED ∪ PUBLIC-STATISTIC; NEWS = UNSCHEDULED-NEWS** (declared now, from CH128's prediction).

Audit label for each market: LOW (= PATH-SETTLED or PUBLIC-STATISTIC), NEWS (= UNSCHEDULED-NEWS), or other (= SPORTS-FEED, SCHEDULED-EVENT or UNKNOWN). Judge from title and slug alone (no sidecar fields are given).
