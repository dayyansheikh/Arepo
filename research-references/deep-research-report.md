# Predictive Market Metrics: A Cross-Asset Research and Deployment Framework, with an Arepo and Polymarket Audit

## Executive summary

A durable forecasting edge rarely comes from one indicator. It normally comes from combining five things:

\[
\text{Useful edge}
=
\text{new information}
\times
\text{correct timing}
\times
\text{appropriate model}
\times
\text{execution feasibility}
\times
\text{out-of-sample stability}
\]

A metric can be strongly correlated with prices and still be useless because it reacts after the price, disappears after transaction costs, depends on revised data, or was selected from hundreds of failed alternatives.

The most defensible hierarchy of metrics is:

| Horizon | Highest-priority metrics | Why they rank highly | Main limitation |
|---|---|---|---|
| Intraday | Order-flow imbalance, multi-level book imbalance, spread, depth, liquidity replenishment, aggressive signed flow, cross-venue lead-lag, announcement surprises | They measure the immediate imbalance between demand and available liquidity | Predictability decays rapidly and is often consumed by spread, latency and adverse selection |
| Days to weeks | Earnings revisions, standardised earnings surprise, post-announcement drift, medium-term momentum, futures basis, funding, positioning changes, attention shocks, inventory surprises | They represent information that takes time to diffuse or positions that must unwind | Crowding, event clustering and changing market regimes |
| Months | Profitability, valuation, investment, carry, trend, yield-curve slope, credit spreads, leverage and default-risk measures, commodity inventories | They are tied to persistent cash-flow, risk-premium or business-cycle mechanisms | Slow turnover, structural breaks and large drawdowns during regime changes |

Short-horizon order-book signals have strong empirical support in conventional limit-order markets. Cont, Kukanov and Stoikov found that short-interval price changes are more robustly related to order-flow imbalance than to raw trade volume, while later work found queue imbalance and stationary order-flow features predictive over approximately the next few price changes. These findings support using flow and book information for seconds-to-minutes forecasting, but not extrapolating it into day or week forecasts. citeturn3search6turn3search15turn16search6

At days-to-months horizons, momentum is among the most repeatedly documented return predictors. Equity momentum was established by Jegadeesh and Titman, while time-series momentum has been documented across equity indices, currencies, commodities and government-bond futures. Its economic interpretation remains contested, however, and momentum strategies can experience sudden reversals. citeturn4search0turn4search10

For equities, the most useful event-specific metrics are analyst revision breadth, standardised unexpected earnings, changes in margins and cash flows, options-implied distributions, and high-quality alternative measures of company activity. Earnings information can continue to predict later announcement-period returns, which is the foundation of post-earnings-announcement drift. Profitability and investment characteristics also possess longer-horizon cross-sectional information, although factor effects are not universal across countries or periods. citeturn7search12turn4search6turn5search1turn5search13

For default prediction, market and accounting variables should be combined. Leverage, profitability, cash holdings, equity returns, equity volatility, market capitalisation and market-to-book measures have demonstrated incremental failure-prediction information. Structural distance-to-default remains useful, but empirical work indicates that its functional form is more valuable than treating the full Merton model as literally correct. citeturn6search0turn7search3turn7search9

For macroeconomic regime changes, the yield curve, credit spreads, inflation expectations, labour-market diffusion, volatility and cross-asset correlation should be treated as a system rather than isolated indicators. Yield-curve slope has historically been a strong recession predictor at multi-quarter horizons, while Markov-switching and state-space models provide a formal framework for estimating latent regimes. citeturn8search1turn8search5turn8search6

For currencies, simple macroeconomic fair-value models are weak short-term forecasting tools. The classic Meese-Rogoff result found that structural exchange-rate models struggled to beat a random walk. More promising variables include order flow at short horizons, interest-rate differentials and carry, global risk conditions, terms of trade, and persistent trend. citeturn9search6turn9search0turn9search2

For commodities, physical inventories and futures-curve structure are the most economically grounded variables. Low inventories reduce the system’s ability to absorb supply or demand shocks, often producing backwardation and higher volatility. CFTC positioning is useful as a crowding and regime variable, but the categories describe trader types rather than the motivations behind each position. citeturn9search1turn9search11turn13search3

For cryptoassets, the highest-priority metrics are price momentum, market and size factors, perpetual funding, futures basis, open interest, liquidation pressure and exchange order flow. Network activity and realised-capitalisation measures can provide medium-term context, but many popular on-chain indicators have been validated mainly by vendors or in-sample charts rather than independent cost-adjusted research. Academic evidence supports crypto-specific momentum, investor attention and network-related factors, but not the indiscriminate use of every available blockchain metric. citeturn10search1turn10search8turn10search0turn10search2

For prediction markets, price should be described as a market-implied probability estimate, not an objective probability. Under restrictive assumptions it can approximate the mean belief of traders, but risk preferences, wealth, heterogeneous beliefs, liquidity, transaction costs and contract ambiguity can separate market price from physical probability. citeturn19search0turn19search5turn19search15

The central conclusion for Arepo is therefore cautious:

> Arepo should rank markets for investigation, estimate calibrated probabilities or short-horizon repricing distributions using separately validated specialist models, explain the evidence and uncertainty, and test whether any apparent divergence survives executable prices and costs. It should not describe an anomaly score as alpha.

This conclusion follows both the external evidence and the supplied Arepo research mandate. fileciteturn0file0

## Predictive framework and evidence hierarchy

**Predictive power is target-dependent.** A feature cannot be called predictive without specifying what it predicts. “Price movement” might mean the next midpoint change, a five-minute executable return, a one-week relative return, a volatility increase, a threshold crossing, or eventual event resolution. These are different statistical problems with different optimal inputs.

A sound research programme therefore begins by defining:

\[
y_{i,t,h}
=
g\left(
P_{i,t+h},
P_{i,t},
\text{execution assumptions},
\text{benchmark}
\right)
\]

where \(i\) identifies the asset or market, \(t\) is the information cut-off, \(h\) is the forecast horizon, and \(g\) defines the target.

### Core target classes

| Target | Example label | Appropriate use |
|---|---|---|
| Direction | \(\mathbf{1}[r_{t,t+h}>0]\) | Alerts and directional ranking |
| Return | \(r_{t,t+h}\) | Expected-return modelling |
| Relative return | \(r_i-r_{\text{benchmark}}\) | Equity selection and factor research |
| Volatility | \(\sum r^2\), realised variance or future range | Position sizing and risk alerts |
| Jump | \(\mathbf{1}[|r|>k\sigma]\) | Event detection and liquidity preparation |
| Event outcome | \(Y\in\{0,1\}\) | Earnings beats, defaults, elections and prediction-market resolution |
| Time to event | \(\tau\) or hazard \(h(t)\) | Default, downgrade and regime-transition modelling |
| Executable payoff | realised cash flow after spread, fees and fill assumptions | Claims of tradable value |
| Calibration error | \(Y-p\) or conditional reliability error | Prediction-market calibration models |

A feature may predict a price change without predicting the underlying event. For example, an attention shock can cause temporary buying pressure even when it provides no new information about company cash flows. Google search attention was found to predict positive short-term price pressure and later reversal, illustrating the distinction between predicting investor behaviour and predicting fundamental value. citeturn18search0turn18search2

Conversely, a feature can predict an underlying event without immediately producing a profitable price forecast. A credit-risk measure might correctly identify increasing default probability while the bond or CDS market incorporates the same information at the same time.

### Evidence grades used in this report

| Grade | Meaning |
|---|---|
| **A** | Strong direct evidence, replicated across markets, samples or periods, with a coherent economic mechanism |
| **B** | Credible direct evidence, but sensitive to market structure, horizon, sample or implementation |
| **C** | Strong evidence in related assets, but requiring validation in the intended market |
| **D** | Plausible research hypothesis with limited direct evidence |
| **Reject** | Misleading, non-causal, unimplementable, or unsupported in its proposed use |

A grade refers to the feature’s value for research, not guaranteed profitability. An A-grade descriptive or forecasting relationship may still be untradeable after costs.

### Foundational metrics and formulas

| Metric | Definition | Rationale | Typical frequency | Key preprocessing |
|---|---|---|---|---|
| Log return | \(r_t=\ln(P_t/P_{t-1})\) | Additive through time and approximately scale-free | Tick to monthly | Corporate actions, futures rolls, stale quotes |
| Probability-point change | \(\Delta p_t=p_t-p_{t-1}\) | Direct interpretation in percentage points | Tick to daily | Ensure bounded valid prices |
| Logit change | \(\Delta\ell_t=\log\frac{p_t}{1-p_t}-\log\frac{p_{t-1}}{1-p_{t-1}}\) | Treats equivalent odds changes more consistently near 0 and 1 | Tick to daily | Clip \(p\) to \([\epsilon,1-\epsilon]\) |
| Momentum | \(M_{t,L}=P_t/P_{t-L}-1\) or cumulative return | Captures delayed information diffusion and trend persistence | Daily to monthly | Skip most recent period when testing cross-sectional equity momentum |
| Realised volatility | \(RV=\sum_{j=1}^{n} r_j^2\) | Estimates current information arrival and risk state | Intraday to daily | Remove bad ticks, account for microstructure noise |
| Standardised move | \(z_t=(r_t-\mu_{t,L})/\sigma_{t,L}\) | Compares a move with the asset’s recent distribution | Any | Use only observations strictly before \(t\) for the reference distribution |
| Order-book imbalance | \(OBI=(D_b-D_a)/(D_b+D_a)\) | Measures asymmetry in resting liquidity | Millisecond to second | Consistent depth bands and sequence reconstruction |
| Microprice | \(\frac{aD_b+bD_a}{D_a+D_b}\) | Adjusts midpoint towards the side with lower available opposing liquidity | Millisecond to second | Valid best bid and ask, non-zero depth |
| Order-flow imbalance | Signed changes in bid and ask queues caused by submissions, cancellations and executions | Captures changes in pressure, not merely the static book | Event-level | Sequence numbers, deduplication, cancellation treatment |
| Carry | Expected income or roll return relative to financing cost | Compensates for holding or balance-sheet risk | Daily to monthly | Contract matching, funding and collateral |
| Basis | \(F_t-S_t\), often annualised | Reflects carry, convenience yield, financing and positioning | Intraday to daily | Match maturity and settlement |
| Standardised unexpected earnings | \((EPS-\widehat{EPS})/\sigma_{\text{forecast error}}\) | Measures the magnitude of the earnings surprise | Quarterly | Point-in-time analyst forecasts and split adjustment |
| Revision breadth | \((N_{\uparrow}-N_{\downarrow})/(N_{\uparrow}+N_{\downarrow})\) | Measures the direction and breadth of analyst information changes | Daily to monthly | Preserve publication timestamps |
| Yield-curve slope | \(y_{\text{long}}-y_{\text{short}}\) | Summarises expected policy, growth and term premium | Daily to monthly | Constant maturity and release-vintage controls |
| Distance to default | Approximate distance between asset value and default boundary in volatility units | Maps balance-sheet leverage and asset volatility into default risk | Daily to quarterly | Iterative asset-value estimation and debt maturity mapping |
| MVRV | Market capitalisation divided by realised capitalisation | Compares current crypto valuation with an on-chain cost-basis proxy | Block to daily | Entity adjustments, lost coins, UTXO methodology |
| Abnormal attention | Current log attention minus a trailing robust baseline | Detects unexpected public interest | Hourly to weekly | Ambiguous keywords, sampling changes and seasonality |
| Logical residual | Observed probability relationship minus required probabilistic relationship | Detects inconsistent related contracts | Tick to daily | Validate that contracts are genuinely comparable |

For binary prediction contracts, probability-point changes are easier to explain, while logit changes are often statistically better behaved. A move from 0.01 to 0.02 is one probability point but doubles the implied odds; a move from 0.50 to 0.51 is also one point but is far smaller in odds terms. Both transformations should be retained, with the transformation selected before testing.

### Why simple correlation is not enough

A useful feature must satisfy several layers:

\[
\text{Candidate metric}
\rightarrow
\text{incremental forecast information}
\rightarrow
\text{stable out-of-sample information}
\rightarrow
\text{economic significance}
\rightarrow
\text{executable value}
\]

Correlation tests only the first part, and often incompletely. A metric may correlate with future returns because both variables react to a third variable, because the feature contains future information, or because observations overlap.

Granger causality asks whether lagged values of \(X\) improve forecasts of \(Y\) conditional on lagged \(Y\) and other included variables. It is a predictive ordering test, not proof that changing \(X\) would cause \(Y\) to change. citeturn15search17

Mutual information can identify non-linear dependence, but finite-sample estimates are sensitive to dimension, estimator choice and serial dependence. The Kraskov estimator uses nearest-neighbour distances to reduce the limitations of simple histogram estimators, but it still requires resampling-based significance tests and careful tuning. citeturn15search0

SHAP assigns additive feature attributions to model predictions. It is useful for explanation and debugging, but a large SHAP value is not evidence that a feature is causal, stable or tradeable. Correlated features can divide or redistribute attribution in unintuitive ways. citeturn15search1turn15search4

## Ranked metric atlas by asset class and horizon

The following rankings combine empirical strength, economic rationale, data availability, cross-market transferability and likely survival after costs. They are not universal performance rankings.

### Cross-asset ranking by horizon

| Rank | Intraday | Grade | Days to weeks | Grade | Months | Grade |
|---:|---|:---:|---|:---:|---|:---:|
| 1 | Order-flow imbalance | A | Earnings surprises and revisions for equities | A | Profitability, valuation and investment for equities | A |
| 2 | Multi-level book and queue imbalance | A | Medium-term momentum and trend | A | Time-series trend across liquid futures | A |
| 3 | Spread, depth and liquidity resilience | A | Carry, funding and futures basis | A/B | Yield-curve and credit-cycle variables | A/B |
| 4 | Aggressive signed trade flow | A/B | Post-announcement drift | A/B | Structural and reduced-form default risk | A |
| 5 | Cross-venue lead-lag and basis | B | Commodity inventory and curve changes | A/B | Commodity inventory scarcity and term structure | A/B |
| 6 | Scheduled announcement surprise | A | Positioning and crowding changes | B | Currency carry and global risk exposure | A/B |
| 7 | Volatility, jumps and spread widening | A/B | Options-implied distribution changes | B | Crypto market, size and momentum factors | B |
| 8 | Cancellation and replenishment failure | B | Attention and sentiment shocks | B/C | Long-horizon sentiment conditioning | B/C |
| 9 | Price momentum over a few events | B | Crypto exchange flows, funding and liquidation pressure | B/C | On-chain valuation and adoption measures | C |
| 10 | Static trade size or raw volume alone | C | Generic technical oscillators | C/D | Standalone chart patterns | D |

Order-flow imbalance ranks above raw volume because queue changes encode both liquidity provision and liquidity removal. In the Cont, Kukanov and Stoikov sample, price changes had a robust approximately linear relationship with order-flow imbalance and the coefficient varied inversely with market depth. citeturn3search6

Momentum ranks highly at intermediate horizons because it has been documented across assets. It should nevertheless be implemented as a family of horizon-specific features rather than one arbitrary lookback. A one-hour trend, a six-month trend and a twelve-month cross-sectional momentum feature represent different mechanisms. citeturn4search0turn4search10

Generic indicators such as RSI, MACD and moving-average crossovers are transformations of the same price history. They can be useful basis functions, but testing dozens of overlapping versions gives the illusion of independent evidence. Their inclusion should be justified by incremental out-of-sample value after simpler return, trend and volatility variables are already present.

### Equities

| Rank | Metric family | Best horizon | Event or price target | Rationale | Recommended construction | Grade |
|---:|---|---|---|---|---|:---:|
| 1 | Earnings revisions and SUE | Days to months | Earnings surprise and post-event return | Analysts and companies reveal information gradually | Revision breadth, magnitude, age, dispersion and SUE | A |
| 2 | Profitability and cash-flow quality | Months | Cross-sectional return and fundamental deterioration | Persistent operating strength affects future cash flows | Gross profits/assets, operating profitability, cash conversion | A |
| 3 | Momentum | Weeks to months | Relative return | Delayed diffusion, underreaction and trend-following demand | Six-to-twelve-month return, often excluding the latest month | A |
| 4 | Valuation and investment | Months to years | Expected relative return | Prices paid relative to fundamentals and corporate investment behaviour | Book-to-market, earnings yield, free-cash-flow yield, asset growth | A/B |
| 5 | Order flow and liquidity | Seconds to hours | Next price change and execution risk | Immediate imbalance in informed and uninformed demand | OFI, queue imbalance, spread, depth and impact | A/B |
| 6 | Options-implied information | Days to months | Volatility, tail risk and event magnitude | Options aggregate expectations about distribution and demand for protection | IV term structure, skew, variance risk premium, implied jump | B |
| 7 | Credit-equity information | Days to months | Default, downgrade and equity downside | Debt and equity encode different parts of the capital structure | CDS spread, bond spread, distance to default | B |
| 8 | Attention and text sentiment | Days to weeks | Temporary pressure and information diffusion | Attention affects which information is processed and traded | Abnormal search volume, timestamped news tone, novelty | B |
| 9 | Short interest and borrow cost | Weeks to months | Negative information and crowding | Informed shorting versus squeeze risk | Utilisation, fee, days-to-cover and change | B/C |
| 10 | Alternative operating data | Weeks to quarters | Revenue and earnings surprise | Measures activity before official results | Transactions, web use, app use, hiring and geospatial activity | C |

Gross profitability has demonstrated cross-sectional predictive power comparable with traditional value measures, while the Fama-French five-factor framework formalises profitability and investment as major return dimensions. These factors should be treated as conditional expected-return variables, not guarantees that an apparently cheap or profitable company will rise. citeturn4search6turn5search1

**Recommended earnings-surprise feature set**

\[
SUE_i =
\frac{EPS_i-\operatorname{Consensus}_{i,t^-}}
{\operatorname{SD}(\text{historical forecast errors}_i)}
\]

The consensus must be the version observable immediately before the earnings release. Additional features should include revision breadth, forecast dispersion, age of the consensus, management-guidance changes, sector peers’ surprises, options-implied move and pre-announcement return.

Bernard and Thomas found that later earnings-announcement returns were predictable from earlier earnings information, supporting the view that markets sometimes incompletely process the serial structure of earnings. citeturn7search12

Alternative data should be assigned a lower initial evidence grade because coverage changes, vendor revisions, sample selection and publication lags can dominate the underlying signal. A dataset should be rejected when historical values were reconstructed using methods that differ from the live product, when company coverage depends on later success, or when the timestamp of availability cannot be established.

### Foreign exchange

| Rank | Metric family | Best horizon | Rationale | Feature examples | Grade |
|---:|---|---|---|---|:---:|
| 1 | Dealer or venue order flow | Minutes to days | Captures immediate information and inventory transfer | Signed flow, OFI, cross-venue pressure | A/B |
| 2 | Interest-rate differential and carry | Weeks to months | Compensation for funding and global risk | Spot-forward carry, real-rate differential | A |
| 3 | Trend and momentum | Weeks to months | Persistent price adjustment and positioning | One, three, six and twelve-month trend | A |
| 4 | Macro surprise differential | Minutes to weeks | Relative monetary-policy and growth news | Standardised release surprise by country | B |
| 5 | Global risk regime | Days to months | Carry currencies load on global risk appetite | Equity volatility, credit spread and funding stress | A/B |
| 6 | Options risk reversal and implied volatility | Days to months | Measures directional hedging and tail demand | 25-delta risk reversal, butterfly, term structure | B |
| 7 | Terms of trade and commodity linkage | Weeks to months | Commodity exporters’ income and policy outlook | Export basket return and price index | B |
| 8 | CFTC positioning | Weeks | Crowding and forced-unwind risk | Leveraged-fund net position z-score | B/C |
| 9 | Purchasing-power or valuation gap | Years | Slow equilibrium anchor | Real effective exchange-rate deviation | B/C |
| 10 | Standalone macro fair-value regression | Months | Frequently unstable out of sample | Monetary and output differentials | C |

The exchange-rate literature provides a warning against overconfidence. Meese and Rogoff found that structural models failed to beat a random walk at horizons from one to twelve months even when supplied with realised future explanatory variables. In contrast, Evans and Lyons found that order-flow information improved shorter-horizon forecasts in their sample. The implication is that the timing and market transmission of information may matter more than a static macro fair-value equation. citeturn9search6turn9search0

Carry should be modelled jointly with global risk and crowding. High-interest-rate currencies may earn positive average excess returns while remaining exposed to severe losses during funding stress. citeturn9search2turn9search5

### Cryptoassets

| Rank | Metric family | Best horizon | Rationale | Feature examples | Grade |
|---:|---|---|---|---|:---:|
| 1 | Spot and perpetual order flow | Milliseconds to hours | Immediate price discovery and leveraged pressure | OFI, aggressive flow and cross-exchange imbalance | A/B |
| 2 | Momentum and market factor | Days to months | Strong crypto-specific trend and common-factor structure | Market return, time-series and cross-sectional momentum | B |
| 3 | Funding, basis and open interest | Hours to weeks | Leverage demand and carry imbalance | Annualised basis, funding z-score, OI change | B |
| 4 | Liquidation and margin stress | Seconds to hours | Forced trades can amplify movement | Liquidation notional relative to depth | B/C |
| 5 | Cross-venue lead-lag | Milliseconds to minutes | Fragmented venues incorporate information at different speeds | Lead venue return and lagging quote residual | B |
| 6 | Exchange net flows | Hours to weeks | Potential selling supply or custody migration | Entity-adjusted exchange inflow and outflow | C |
| 7 | Stablecoin supply and transfer activity | Days to months | Measures crypto-native liquidity conditions | Supply change, exchange balances and velocity | C |
| 8 | Network adoption and fee activity | Weeks to months | Measures demand for blockspace or protocol use | Active entities, fees, transfer value | B/C |
| 9 | Realised-capitalisation metrics | Weeks to months | Approximate investor cost basis and unrealised gain state | MVRV, realised profit and loss | C |
| 10 | Raw wallet counts and unfiltered transactions | Any | Easily distorted by internal transfers, batching and Sybil activity | None without entity adjustment | Reject/C |

Liu and Tsyvinski found that crypto returns were associated with crypto-specific momentum, attention and network factors rather than conventional production-based asset-pricing variables. Later work found that market, size and momentum factors captured substantial cross-sectional structure. These results support a compact factor model, not hundreds of highly correlated on-chain ratios. citeturn10search1turn10search8

Realised capitalisation values units at the price when they last moved, and MVRV divides market capitalisation by realised capitalisation. These are useful descriptive constructs, but vendor claims about exact cycle tops or bottoms should not be treated as independent validation. citeturn10search0turn10search2

At high frequency, cross-venue signals require exceptional timestamp discipline. A 2026 Polymarket and Binance dataset reported an apparent fast lead-lag relationship, but its walk-forward model did not outperform the probability already embedded in Polymarket’s book and produced a negative simulated payoff after stated costs. This is a valuable null result because it shows that detectable latency does not automatically create executable alpha. citeturn16academia37

### Commodities

| Rank | Metric family | Best horizon | Rationale | Feature examples | Grade |
|---:|---|---|---|---|:---:|
| 1 | Physical inventories | Weeks to months | Scarcity changes convenience yield and shock sensitivity | Inventory level, days of use and seasonal z-score | A |
| 2 | Futures curve and basis | Days to months | Aggregates inventories, financing and convenience yield | Front-to-back spread, curve slope and roll yield | A |
| 3 | Weather and crop conditions | Days to months | Direct supply and demand effects | Degree days, rainfall anomaly and crop progress | A/B |
| 4 | Production, refinery and transport constraints | Days to months | Identifies physical bottlenecks | Outages, utilisation, exports and freight | A/B |
| 5 | CFTC positioning | Weeks | Measures crowding and participant composition | Managed-money and producer positions | B |
| 6 | Momentum | Weeks to months | Trend persistence across futures | Multi-horizon time-series momentum | A |
| 7 | Options-implied skew and volatility | Days to months | Measures scarcity and tail hedging | Call skew, term structure and implied jump | B |
| 8 | Currency and real-rate conditions | Weeks to months | Affect financing and global demand | US dollar and real-yield changes | B |
| 9 | Satellite or shipping activity | Days to months | Measures physical flows before official releases | Vessel tracking and storage estimates | C |
| 10 | Unadjusted headline inventories | Weeks | Seasonal and definitional changes create false signals | Raw level alone | C |

Gorton, Hayashi and Rouwenhorst found that commodity risk premia varied with physical inventories and that basis and past returns contained inventory-related information. Low inventory has also been associated with backwardation and greater volatility. citeturn9search1turn9search11

The CFTC publishes weekly positions based on Tuesday open interest and groups traders by reported business purpose. The Commission explicitly warns that it does not know the specific reason for each position. COT data should therefore be used as positioning context, not as a literal classification of every trade as hedging or speculation. citeturn13search3turn13search4

### Government and corporate bonds

| Rank | Metric family | Best horizon | Rationale | Feature examples | Grade |
|---:|---|---|---|---|:---:|
| 1 | Yield-curve level, slope and curvature | Days to quarters | Encodes policy, inflation, growth and term premium | PCA factors and key-rate spreads | A |
| 2 | Credit spreads and spread momentum | Days to months | Forward-looking default and liquidity compensation | OAS, CDS and excess bond premium | A |
| 3 | Macro release surprises | Minutes to weeks | Reprices policy and cash-flow expectations | Inflation, payroll and activity surprise | A |
| 4 | Forward-rate return factor | Months | Predicts time variation in bond risk premia | Cochrane-Piazzesi tent-shaped factor | A/B |
| 5 | Inflation breakevens and real yields | Days to months | Separates inflation compensation and real discount rates | Breakeven change and real-curve slope | A/B |
| 6 | Liquidity and dealer flow | Minutes to days | Important in fragmented OTC markets | TRACE flow, bid-ask proxy and price impact | B |
| 7 | Structural default measures | Days to months | Links equity volatility and balance-sheet leverage to debt risk | Distance to default | A/B |
| 8 | Issuance and supply calendar | Days to months | Dealer balance-sheet and duration supply | Net issuance and auction concession | B |
| 9 | Positioning and futures basis | Days to weeks | Measures hedging pressure and relative-value crowding | CFTC positions and cash-futures basis | B |
| 10 | Rating alone | Months | Discrete, slow and often lagging | Rating level without market information | C |

Ang and Piazzesi found that macro variables and latent yield-curve factors jointly explained substantial yield variation, particularly at short and intermediate maturities. Cochrane and Piazzesi identified a forward-rate combination that predicted one-year excess bond returns in their sample. Both results justify modelling the full curve rather than selecting one maturity in isolation. citeturn8search6turn8search15

### Event-prediction metrics

| Underlying event | Highest-priority metrics | Model family | Frequency | Important caveat |
|---|---|---|---|---|
| Earnings surprise | Revision breadth, forecast dispersion, guidance, peer results, margins, activity data and options-implied move | Regularised regression, gradient boosting or hierarchical Bayesian model | Daily with quarterly labels | Consensus must be point-in-time |
| Corporate default | Equity volatility, poor equity return, leverage, profitability, cash, market capitalisation, credit spreads and distance to default | Dynamic logit, hazard or survival model | Daily to monthly | Delisting and censoring must be handled |
| Recession or regime shift | Yield-curve slope, credit spreads, unemployment claims, inflation, breadth, volatility and cross-asset correlation | Markov switching, state-space or hazard model | Daily to monthly | Macro data revisions create leakage |
| Commodity shortage | Inventory relative to seasonal demand, curve inversion, options skew, outages and weather | State-space or regime model | Hourly to weekly | Physical data may be delayed |
| Crypto deleveraging | Funding, basis, OI, liquidations, collateral flows, stablecoin liquidity and depth | Hazard or classification model | Seconds to hourly | Venue coverage and double counting |
| Prediction-market resolution | Market probability, time to expiry, category, spread, depth, public forecasts and logical relationships | Calibrated hierarchical logistic or beta calibration | Tick to daily | Contract semantics and resolution rules dominate |
| Short-horizon repricing | OFI, multi-level imbalance, aggressive flow, spread, replenishment and cross-venue movement | Logistic, GAM, boosting or sequence model | Event-level | Predictable movement may be smaller than spread |

Campbell, Hilscher and Szilagyi’s failure model combined accounting and market variables, including leverage, profitability, size, prior returns, volatility, cash and valuation. Such variables should enter a dynamic hazard model rather than a static “distress score” applied without industry, age or macro controls. citeturn7search3

## Data, preprocessing, feature engineering and event alignment

### Recommended data architecture

The correct unit of storage is not a cleaned daily table. It is an immutable, timestamped observation with both event time and availability time.

A minimum record should contain:

| Field | Purpose |
|---|---|
| `event_time` | When the economic or market event occurred |
| `received_time` | When the system received it |
| `available_time` | Earliest time a model could legally have used it |
| `source_time` | Timestamp declared by the source |
| `ingest_version` | Version of the parser and normaliser |
| `entity_id` | Stable asset, company, contract or market identifier |
| `source_id` | Original source identifier |
| `raw_value` | Unmodified value |
| `normalised_value` | Research-ready value |
| `revision_id` | Identifies later restatements or revisions |
| `quality_flags` | Stale, missing, crossed, duplicated or inferred |
| `provenance` | Prospective, historical point-in-time, reconstructed or synthetic |

The distinction between `event_time` and `available_time` is essential. A macroeconomic value labelled “June” may be released in July and revised in August. Using the final June value to predict a July price introduces future information.

ALFRED preserves historical vintages of FRED series and exposes dates when observations were released or revised. It should be preferred over downloading the latest macro series for historical tests. citeturn14search3turn14search5turn14search6

SEC EDGAR’s APIs provide submissions and extracted XBRL facts, with submissions generally updated in less than a second and XBRL data typically in under a minute, although delays can be longer at busy times. The SEC also offers nightly bulk archives. Original filing timestamps and amendments should be retained rather than collapsing directly to the latest value. citeturn13search0turn13search11

### Recommended datasets and APIs

| Domain | Preferred sources | Data | Frequency or granularity | Research notes |
|---|---|---|---|---|
| US company fundamentals | SEC EDGAR APIs and bulk archives | Filings, submissions and XBRL facts | Event-level | Primary source; normalise tags carefully |
| Equity returns and corporate actions | Exchange feeds, CRSP or equivalent institutional dataset | Trades, quotes, returns, delistings and actions | Tick to daily | Include delisting returns and historical membership |
| Analyst forecasts | I/B/E/S or equivalent point-in-time provider | EPS forecasts, revisions and dispersion | Event-level | Store each forecast version |
| Options | OPRA or institutional options dataset | Quotes, trades and implied distributions | Tick to daily | Filter stale and crossed markets |
| US macro | FRED and ALFRED | Rates, activity and financial conditions | Daily to quarterly | Use vintages for backtests |
| Labour data | BLS Public Data API | Employment, inflation and wages | Monthly and quarterly | Version 2 supports broader registered use citeturn14search4 |
| National accounts | BEA data services | GDP, income and industry accounts | Monthly to annual | Preserve release calendars and revisions |
| Energy | EIA API v2 | Inventories, generation, demand and production | Hourly to annual | API supports dataset-specific frequencies and facets citeturn14search0turn14search2 |
| Futures positioning | CFTC Public Reporting Environment | Legacy, disaggregated and financial-futures COT | Weekly | Historical series and API access are available citeturn13search3turn13search7 |
| Corporate bonds | FINRA TRACE | Transactions and aggregate reports | Trade-level to monthly | Detailed historical data may require licensing citeturn13search5turn13search10 |
| Crypto network | Native nodes and Coin Metrics | Blocks, transfers, fees and entity-adjusted metrics | Block to daily | Retain chain reorganisations and metric definitions |
| Crypto markets | Exchange REST and WebSocket feeds | Trades, books, funding and liquidations | Millisecond to hourly | Synchronise venue clocks and sequence numbers |
| Attention | Google Trends and licensed search data | Search intensity | Hourly to weekly | Sampling and keyword ambiguity require repeated snapshots |
| News and text | Official releases, filings and licensed timestamped news | Text, entities and event time | Millisecond to daily | Separate novelty, tone and relevance |
| Weather | NOAA and national meteorological agencies | Forecasts and realised weather | Hourly to seasonal | Store the forecast vintage, not only realised weather |
| Prediction markets | Polymarket Gamma, Data, CLOB and WebSocket APIs | Metadata, trades, positions, books and history | Tick to daily | Full details appear in the Arepo section |

### Preprocessing requirements by data type

**Prices and quotes.** Adjust equities for splits and distributions, but retain unadjusted prices for execution simulation. Futures require continuous-series logic that does not create artificial roll returns. Order books must be reconstructed using sequence numbers, snapshots and incremental updates. Crossed books, stale quotes, zero depth and invalid prices should be flagged rather than silently repaired.

**Fundamentals.** Map changing accounting tags to stable concepts. Distinguish fiscal period end, filing acceptance time and the period to which a value refers. Amendments must not overwrite the historical first release.

**Analyst data.** Use only forecasts timestamped before the prediction cut-off. Consensus should be reconstructed from active forecasts, with controls for analyst age, stale estimates, coverage and forecast dispersion.

**Macroeconomic data.** Use the value available at the time, not the revised final value. Standardise announcement surprises using the historical distribution known before that release:

\[
Surprise_t =
\frac{Actual_t-Consensus_t}
{\widehat{\sigma}_{t^-}(Actual-Consensus)}
\]

**Text.** Remove duplicated syndicated articles and repeated corporate boilerplate. Features should distinguish tone from novelty, uncertainty, subject relevance and source credibility. A negative article published after the price moved is not a leading signal.

**On-chain data.** Apply entity clustering where defensible, exclude known exchange-internal movements when measuring flows, account for contract migrations, bridge activity, batching and chain reorganisations. A blockchain timestamp is not necessarily the time information reached market participants.

**Alternative data.** Track vendor coverage and methodology versions. Missingness is often informative, but it may also be caused by vendor outages or coverage expansion. The model should receive explicit availability and quality features rather than an imputed number alone.

### Feature engineering principles

The safest features are transformations that reflect an economic mechanism:

\[
\text{Feature}
=
\frac{\text{current state}-\text{relevant expected state}}
{\text{historical uncertainty}}
\]

Examples include inventory relative to seasonal expectations, earnings relative to consensus, volume relative to the same time of day, and spread relative to the asset’s own liquidity regime.

Useful feature families include:

| Family | Recommended features |
|---|---|
| Level | Current valuation, spread, inventory or probability |
| Change | First difference, log change or logit change |
| Acceleration | Change in change, flow acceleration or revision acceleration |
| Surprise | Actual minus expected, scaled by historical forecast error |
| Relative value | Asset minus peer, curve or cross-venue benchmark |
| Regime interaction | Signal multiplied by liquidity, volatility or sentiment state |
| Persistence | Number and duration of consecutive observations with the same sign |
| Breadth | Fraction of related assets, analysts or contracts agreeing |
| Concentration | HHI, entropy, Gini or top-\(k\) share |
| Quality | Age, coverage, missingness, source agreement and timestamp uncertainty |
| Capacity | Available depth, expected impact and fill probability |

A static book imbalance should be complemented by order-flow imbalance, cancellation flow and replenishment. Two books can have the same imbalance while one is stable and the other is losing bids rapidly.

A robust large-trade feature can be defined as:

\[
A_t =
\frac{\log(1+q_t)-\operatorname{median}_{t-L:t^-}\log(1+q)}
{1.4826\operatorname{MAD}_{t-L:t^-}\log(1+q)}
\]

This is generally preferable to labelling every trade above a fixed dollar amount as “large”.

Concentration should use several views:

\[
HHI=\sum_i s_i^2,
\qquad
N_{\mathrm{effective}}=\frac{1}{HHI},
\qquad
Entropy=-\sum_i s_i\log s_i
\]

A high holder concentration can indicate fragility or low participation. It does not prove that the holder is informed.

### Models for regime changes

Regimes should usually be latent variables, not hand-labelled retrospectively using knowledge of the subsequent crash.

A simple Markov-switching model assumes:

\[
r_t \mid S_t=k
\sim
\mathcal{N}(\mu_k,\sigma_k^2)
\]

with transition probabilities:

\[
P(S_t=j \mid S_{t-1}=i)=p_{ij}
\]

Hamilton’s framework provides the foundation for estimating recurring discrete economic regimes. citeturn8search5

Useful regime inputs include yield-curve slope, credit spreads, realised and implied volatility, equity breadth, cross-asset correlation, market liquidity, funding stress, inflation surprises and commodity-curve state.

Regime models should output probabilities such as \(P(S_t=\text{stress}\mid\mathcal{F}_t)\), not absolute statements that a regime has changed. A transition alert should require persistence or posterior odds above a pre-registered threshold.

## Statistical validation, backtesting and explainability

### Predictive-power tests

| Method | What it measures | Correct use | Main failure mode |
|---|---|---|---|
| Pearson correlation | Linear association | Initial diagnostic for continuous variables | Outliers, non-linearity and common trends |
| Spearman correlation | Monotonic rank association | Cross-sectional signals and robust screening | Ignores economic magnitude |
| Information coefficient | Cross-sectional correlation of signal with future return | Factor ranking by date | Overlapping returns and changing universe |
| Granger test | Incremental predictive information in lagged values | Time-series lead-lag testing | Omitted variables and mistaken causal interpretation |
| Mutual information | General statistical dependence | Non-linear feature screening | Biased high-dimensional estimation |
| Linear coefficient and \(t\)-statistic | Conditional marginal association | Interpretable baseline models | Serial correlation and multiple testing |
| Permutation importance | OOS loss deterioration when a feature is permuted | Model-level predictive contribution | Invalid when time structure or feature dependence is ignored |
| Drop-column importance | OOS performance change after retraining without a feature | More reliable incremental value test | Computational cost |
| SHAP | Local additive attribution | Explanation and error analysis | Not causal; correlated features complicate attribution |
| Ablation study | Performance without a family or source | Testing whether complexity adds value | Must be performed fully out of sample |
| Economic backtest | Cost-adjusted payoff | Executability assessment | Unrealistic fills, survivorship and data leakage |

For a cross-sectional factor:

\[
IC_t =
\operatorname{SpearmanCorr}
\left(
s_{i,t},
r_{i,t\rightarrow t+h}
\right)
\]

The report should include mean IC, IC standard deviation, information ratio, percentage of positive periods, turnover, sector or category neutrality, and confidence intervals based on date-level block resampling.

Feature importance must be calculated on untouched validation or test data. In-sample tree importance mainly reveals how a model fitted the training sample.

### Required validation protocol

A defensible protocol is:

1. Define the target, horizon, universe, execution price and costs before feature testing.
2. Build immutable point-in-time data with explicit availability timestamps.
3. Divide data chronologically into research, validation and untouched test periods.
4. Group related observations so the same event, company, market or complementary contract cannot appear on both sides of a split.
5. Purge observations whose target windows overlap the validation or test interval.
6. Apply an embargo after split boundaries when features or labels have persistent dependence.
7. Select models and thresholds using walk-forward validation only.
8. Evaluate once on the frozen test set.
9. Run a prospective shadow period using frozen code and thresholds.
10. Deploy only after predefined statistical, economic and operational acceptance criteria are met.

For overlapping \(h\)-period labels, observations near the boundary must be removed:

\[
[t_i,t_i+h]
\cap
[t_{\text{test,start}},t_{\text{test,end}}]
\neq \varnothing
\quad\Rightarrow\quad
i\text{ is purged from training}
\]

Prediction markets require additional grouping. YES and NO tokens from the same binary market are complements, not independent observations. Outcomes within the same multi-outcome event, semantically duplicated contracts and markets sharing the same resolution source should also be grouped.

### Multiple testing

Multiple-testing correction is required as soon as more than one inferential hypothesis is tested within the same research family. There is no defensible rule that permits testing 20 features freely and correcting only from feature 21.

If independent tests each use a 5 per cent significance level, the probability of at least one false positive is:

\[
P(\text{at least one false positive})
=
1-(1-0.05)^m
\]

| Number of tests \(m\) | False-positive probability under the global null |
|---:|---:|
| 1 | 5.0% |
| 2 | 9.8% |
| 10 | 40.1% |
| 20 | 64.2% |
| 100 | 99.4% |

In finance, tests are correlated, but correlation does not make unrestricted search harmless. Harvey, Liu and Zhu concluded that newly proposed factors require a substantially higher statistical hurdle than the traditional \(t>2\), with a benchmark around \(t>3\) in their analysis of the factor literature. citeturn12search12turn12search20

The research registry must count:

- every feature definition,
- every lookback,
- every winsorisation rule,
- every universe filter,
- every model,
- every regularisation setting,
- every entry threshold,
- every exit horizon,
- every cost assumption inspected before selecting the winner.

False-discovery-rate methods are appropriate when identifying a set of potentially useful features. Family-wise error controls are more appropriate when a single false claim would be costly. White’s Reality Check and Hansen’s Superior Predictive Ability test compare many strategies against a benchmark while accounting for data snooping. citeturn15search7turn15search8

The Probability of Backtest Overfitting framework uses combinatorially symmetric cross-validation to estimate the probability that the configuration selected in sample will underperform out of sample. citeturn12search5turn12search8

The Deflated Sharpe Ratio adjusts apparent Sharpe performance for the number of trials, non-normal returns and selection bias. citeturn12search0turn12search19

### Cost and execution modelling

| Asset class | Minimum cost model |
|---|---|
| Equities | Bid-ask spread, commissions, market impact, participation limit, borrow fee, locate availability and corporate actions |
| FX | Bid-ask spread, venue or prime-broker fee, rollover, funding, last-look rejection and latency |
| Crypto | Maker or taker fee, spread, depth impact, funding, liquidation risk, withdrawal limits and venue fragmentation |
| Commodities | Spread, brokerage, exchange fee, roll cost, expiry rules, position limits and market impact |
| Government bonds | Dealer spread, futures hedge, financing, benchmark mismatch and liquidity by issue |
| Corporate bonds | TRACE-observed liquidity, dealer mark-up, minimum size, stale pricing and partial fills |
| Prediction markets | Executable bid or ask, fee schedule, level-by-level depth, slippage, fill probability, capital lock-up and resolution risk |

Midpoint returns are useful for measuring information content but are not executable returns. A buy should normally enter at the ask or at a modelled passive fill probability. Exiting requires the future bid for a sale. A backtest that buys and sells at midpoints effectively receives half the spread twice.

Capacity should be estimated using order-book depth and a maximum participation rule:

\[
q_{\text{trade}}
\leq
\min
\left(
q_{\text{desired}},
\eta \times \text{visible depth},
\kappa \times \text{recent volume}
\right)
\]

where \(\eta\) and \(\kappa\) are chosen before evaluation.

### Forecast and trading metrics

| Category | Required metrics |
|---|---|
| Binary forecast quality | Brier score, log loss, calibration intercept, calibration slope, reliability diagram, discrimination and sharpness |
| Continuous forecast quality | MAE, RMSE, rank correlation, directional accuracy and economic loss |
| Ranking quality | IC, precision at \(k\), recall at \(k\), NDCG where appropriate and turnover |
| Trading quality | Gross return, net return, drawdown, turnover, hit rate with denominator, realised spread, slippage, fill rate and capacity |
| Statistical reliability | HAC or clustered errors, block-bootstrap confidence intervals, test-period stability and multiple-test adjustment |
| Product quality | False-alert burden, signal persistence, explanation fidelity, data freshness and proportion of alerts later invalidated |

For binary forecasts:

\[
Brier = \frac{1}{N}\sum_{i=1}^{N}(p_i-y_i)^2
\]

\[
LogLoss =
-\frac{1}{N}\sum_{i=1}^{N}
\left[
y_i\log p_i+(1-y_i)\log(1-p_i)
\right]
\]

A reliability diagram compares predicted probabilities with realised frequencies. Calibration slope below one often indicates predictions are too extreme; slope above one indicates insufficient dispersion. Proper scoring rules can be decomposed into calibration or reliability and resolution components, allowing a model to be rewarded for both honest probabilities and meaningful separation of easy from difficult events. citeturn19search16turn19academia48

### Research-to-deployment flow

```mermaid
flowchart LR
    A[Pre-register hypothesis and target] --> B[Ingest immutable point-in-time data]
    B --> C[Validate timestamps, identifiers and quality]
    C --> D[Build simple economically motivated features]
    D --> E[Baseline model and univariate diagnostics]
    E --> F[Purged walk-forward validation]
    F --> G[Multiple-testing and robustness controls]
    G --> H[Untouched out-of-sample test]
    H --> I[Spread, slippage, fill and capacity simulation]
    I --> J[Prospective shadow deployment]
    J --> K[Production with frozen model version]
    K --> L[Monitor calibration, drift, costs and incidents]
    L --> M{Stable and useful?}
    M -->|Yes| K
    M -->|No| N[Retire, recalibrate or return to research]
    N --> A
```

A practical programme should spend more time in prospective shadow evaluation than in optimising historical parameters. Historical tests establish plausibility; prospective observation tests whether the complete data and decision pipeline works as believed.

## Prediction markets and the Arepo audit

### What prediction-market prices mean

A binary contract paying one unit if an event occurs has a price between zero and one. Under strong assumptions, the equilibrium price may approximate traders’ average belief. Wolfers and Zitzewitz showed sufficient conditions under which price corresponds to mean belief and argued that prices are often close to mean beliefs in a broader class of models. Manski showed that under heterogeneous beliefs the equilibrium price reveals little about belief dispersion and only partially identifies the centre of the belief distribution. citeturn19search0turn19search5

The safest product wording is:

> The market price is the cost of obtaining the contract’s state-contingent payoff. It often functions as a useful market-implied probability estimate, but it can differ from the physical probability because of spread, fees, risk preferences, trader wealth, heterogeneous beliefs, liquidity, market-making incentives and contract-resolution risk.

Different price representations should be used for different tasks:

| Price | Correct use |
|---|---|
| Best bid | Immediately executable sale price |
| Best ask | Immediately executable purchase price |
| Midpoint | Descriptive central quote and calibration research where both sides exist |
| Microprice | Very short-horizon movement estimate in a live order book |
| Last trade | Trade-event analysis, with staleness controls |
| Volume-weighted execution price | Capacity-aware backtests |
| Calibrated probability | Outcome forecasting after category, horizon and liquidity adjustment |

Prediction markets can be reasonably calibrated while retaining systematic conditional biases. Page and Clemen found that favourite-longshot bias increased with time to expiry, with low-probability events overpriced and high-probability events underpriced at longer horizons. The economic exploitability was more limited once discounting was considered. citeturn19search1turn19search2

Manipulation should not be inferred from unusual price movement alone. Theory and experiments indicate that attempted manipulation does not necessarily reduce observers’ forecasting accuracy, because it can attract informed counter-trading. citeturn19search3turn19search10

### Current Polymarket data atlas

The current official documentation index should be crawled dynamically because Polymarket’s API surface is changing. The August 2026 index includes Gamma, Data, CLOB market data and trading, Bridge, rewards, builders, relayer, RFQ, Predictions, Perps and multiple WebSocket channels. citeturn17view0

| Family | Principal host or channel | Authentication | Key data for Arepo | Point-in-time considerations | Recommended storage |
|---|---|---|---|---|---|
| Gamma | `gamma-api.polymarket.com` | Public for core discovery | Events, markets, tags, series, sports metadata, search and profiles | Primarily current or metadata state; fields may be edited | Snapshot changes plus slowly changing dimensions |
| Data API | `data-api.polymarket.com` | Mostly public read endpoints | Trades, activity, holders, positions, open interest, leaderboards and live volume | Historical coverage and derivation vary by endpoint | Append raw responses with request parameters |
| CLOB REST | `clob.polymarket.com` | Public market data; authentication for user and trading data | Books, bid and ask prices, midpoint, spread, tick size, last trade and price history | Current book endpoints are not historical books | Store every snapshot and incremental update |
| Market WebSocket | Official public market channel | Subscription-based public feed | Book, price and market lifecycle updates | Requires sequence and reconnection handling | Event log plus periodic full snapshots |
| CLOB authenticated trading | CLOB host | Signed API credentials | Orders, user trades and order status | Not required for a read-only Arepo product | Out of scope except for fee and execution documentation |
| Bridge | Official Bridge API | Depends on operation | Supported assets, quotes and transaction status | Operational, not forecasting data | Reject for core research |
| Rewards and makers | Gamma or CLOB documented endpoints | Mixed | Reward configurations, maker rebates and RFQ | Can affect liquidity provision incentives | Daily snapshots for liquidity research |
| Relayer and builders | Official relayer and builder APIs | Authenticated for private operations | Builder volume and transaction services | Mainly infrastructure data | Out of scope for read-only core |
| Predictions | Official Predictions API family | Endpoint-dependent | Prediction-market product interfaces | Newly evolving family | Evaluate separately from legacy CLOB assumptions |
| Perps | Official Perps REST and WebSockets | Public and authenticated channels | Books, trades, funding, index and derivatives state | Different product and payoff structure | Separate schema and model namespace |

The official index documents public midpoint, last-trade, market-price, order-book, spread, tick-size and price-history endpoints, along with current positions, closed positions, holders, user trades, user activity, open interest and live volume. It also documents cursor-based keyset pagination for markets and events. citeturn17view0

Polymarket’s official rate limits differ by family and route. Current documentation should be read at runtime rather than hard-coded indefinitely. citeturn17view2

The official changelog indicates material platform changes, including the CLOB V2 production transition in April 2026. Historical collectors must record API and matching-engine versions because field semantics and market behaviour may change across versions. citeturn17view3

**Identifier map**

\[
\text{Event}
\rightarrow
\{\text{markets or conditions}\}
\rightarrow
\{\text{outcome token IDs}\}
\rightarrow
\{\text{book, trades and positions}\}
\]

| Identifier | Role | Storage rule |
|---|---|---|
| Event ID | Groups related market questions | Stable primary entity key |
| Event slug | Human-readable discovery key | Do not use as sole primary key |
| Market ID or condition ID | Defines a tradable question or condition | Map explicitly between Gamma and CLOB representations |
| Market slug | Human-readable market reference | Store history of changes |
| Token or asset ID | Identifies a specific outcome contract | Primary key for book and quote data |
| Outcome label | Human description such as YES, NO or candidate name | Store with token and valid-time interval |
| Wallet or proxy address | Public participant identifier | Treat as pseudonymous, not personal identity |
| Transaction hash | On-chain event identifier | Preserve for deduplication and provenance |
| Order ID | CLOB order identifier | Relevant for authenticated or reconstructed order events |
| Series and tags | Organisational metadata | Many-to-many mapping |
| Resolution identifier | Connects the contract to its oracle or settlement process | Preserve rule text and source version |

Complementary outcomes, multi-outcome markets, negative-risk structures and combo contracts require relationship tables. A semantic similarity score alone is insufficient to assert a mathematical relationship.

### Polymarket-specific evidence

The strongest current Polymarket-specific research is recent and predominantly preprint-level, so it should receive lower confidence than mature replicated market-microstructure literature.

A 2026 dataset paper integrates Polymarket metadata, fill-level records and oracle events from October 2020 to March 2026, illustrating why market, token, trade and resolution identifiers must be reconciled across multiple layers. citeturn16search0turn16academia36

A 2026 order-book study joined public WebSocket data to on-chain trades and reported that trade direction inferred only from the public book feed agreed with on-chain ground truth only around 59 per cent of the time. Its implementation recommendation is important: trade direction and maker-taker interpretation should be sourced from authoritative fill or on-chain events rather than guessed from quote changes. citeturn16academia39

A 2026 study of NBA markets found that directly executable single-market arbitrage was rare and short-lived, while combinatorial opportunities were often constrained to very small sizes by shallow depth. citeturn16academia38

The synchronised Polymarket-Binance study produced a null out-of-sample result despite observable lead-lag patterns. This supports a strict separation between market description, forecast improvement and tradeable edge. citeturn16academia37

### Audit of the supplied Arepo implementation

The repository shows several good design instincts:

| Existing design choice | Assessment |
|---|---|
| Separating signal strength from data-quality confidence | Mathematically sensible and should be retained |
| Disclosing that implied probability is spread and fee contaminated | Correct |
| Capping book-only anomaly scores | Sensible protection against overinterpreting one snapshot |
| Labelling reconstructed history separately from prospective evaluation | Essential |
| Avoiding claims that wallet concentration proves insider activity | Correct |
| Describing the product as research prioritisation rather than automatic trading | Correct |

The main weaknesses are more fundamental.

| Current implementation issue | Why it matters | Classification | Required change |
|---|---|---|---|
| `movement_1h` is generated from the last four observations rather than a clock-time hour | Observation spacing can vary, so the same field can represent minutes or days | Incorrectly labelled | Compute true time-window returns or rename to `movement_last_4_observations` |
| Rolling z-score uses a short fixed observation window | Irregular sampling changes the effective horizon and distribution | Under-engineered | Use clock-time windows, minimum effective observations and session-aware baselines |
| The current observation appears in its own z-score reference window | This pulls the mean and variance towards the event being measured | Statistically weak | Estimate baseline from \(t-L\) through \(t^-\), then score \(t\) |
| Additive probability changes are used for all price regions | One point near 0.01 has a different odds meaning from one point near 0.50 | Incomplete | Retain probability-point and logit changes |
| Composite weights, caps and thresholds are fixed by judgement | The score has no calibrated probabilistic meaning | Arbitrary but transparent | Treat as temporary UI heuristic or replace with validated models |
| Weights are renormalised over whichever components are available | A score of 0.6 can mean different things under different missing-data patterns | Misleading comparability | Use missingness indicators and fixed model semantics |
| Evidence families are described as independent | Price, volatility, movement and flow variables can be highly correlated | Mathematically unjustified | Use “distinct evidence families” and estimate dependence |
| Direction is largely inherited from the sign of the return z-score | One recent move can force a directional narrative | Overconfident | Permit “no directional view”; require a target-specific model |
| Research Priority combines evidence magnitude, family count and fixed quality multipliers | It is neither probability, expected value nor estimated information gain | Plausible but unvalidated | Rename as heuristic until trained and validated |
| Fixed liquidity and spread thresholds are applied across markets | Appropriate thresholds depend on price, category, horizon and market age | Underfitted | Use conditional percentiles or fitted liquidity-risk models |
| Historical reconstruction uses currently discoverable active markets | Resolved and delisted markets can be underrepresented | Survivorship risk | Build an immutable historical market universe |
| Historical order books are absent from reconstruction | Historical signals differ from the live model | Model mismatch | Call it “price-only retrospective”, never a replay of the full live signal |
| Entry assumes midpoint plus half the spread and default fees are zero | Does not model actual level depth, queue, fill probability or category fees | Optimistic execution | Use executable quotes and level-by-level fills |
| No full capacity model | Small theoretical edges may not scale | Incomplete | Report maximum executable size and expected impact |
| Resolution checking is metadata-based rather than a canonical settlement history | Outcome labels and settlement timing can be wrong | Data-risk issue | Store oracle and final-settlement provenance |
| Forced composite scoring precedes definition of a specific prediction target | Descriptive anomaly is confused with prediction | Core modelling flaw | Build separate horizon and outcome models |

The current anomaly weights allocate a majority of score mass to price-derived variables, so apparently diverse components may mostly reflect the same recent move. The family-count bonus then creates a second source of score inflation when correlated symptoms fire together.

A suitable replacement is a set of specialist models:

| Model | Target | Core features | Output |
|---|---|---|---|
| Calibration model | Final resolution | Market price, time to close, category, spread, liquidity and rule complexity | Calibrated event probability |
| Repricing model | Midpoint or executable move over fixed horizon | OFI, book, flow, jump, spread and external event data | Distribution of future price change |
| Liquidity model | Spread, impact and fill probability | Depth, cancellations, replenishment, volatility and market age | Expected execution cost and capacity |
| Logical-consistency model | Constraint violation persistence | Related market probabilities and contract logic | Constraint residual with uncertainty |
| Event-latency model | Time until market absorbs public news | News timestamp, market activity and category | Repricing hazard |
| Data-quality model | Reliability of current observation | Freshness, source agreement, gaps and reconstruction status | Quality score and reason codes |

A final ensemble should combine only calibrated specialist outputs. It should not average raw z-scores from unrelated targets.

### Defensible Arepo terminology

| Term | Recommended meaning |
|---|---|
| Hypothesis | A falsifiable statement linking defined evidence to a defined target and horizon |
| Directional view | Model probability of an upward or downward move exceeds a pre-registered threshold after costs |
| Horizon | Exact wall-clock period or final resolution, never a number of irregular observations |
| Signal strength | Magnitude of forecast divergence relative to its estimated uncertainty |
| Confidence | Empirically estimated reliability of the model and data, not the size of the signal |
| Research Priority | Ranking of expected investigation value, explicitly not return or probability |
| Evidence family | Group of related measurements representing one economic mechanism |
| Expected move | Conditional distribution or quantiles of the selected price target |
| Invalidation condition | Observable event or threshold that would contradict the hypothesis |
| Data quality | Freshness, completeness, provenance, source agreement and timestamp confidence |
| Tag | Short description of a measured fact, not an unverified interpretation |

A provisional Research Priority can be defined as:

\[
RP =
100\times
\operatorname{PercentileRank}
\left[
\frac{
\text{forecast divergence}
\times
\text{model reliability}
\times
\text{evidence novelty}
\times
\text{actionability}
}{
\text{resolution risk}
+
\text{data uncertainty}
+
\text{estimated investigation cost}
}
\right]
\]

Until its components are trained and validated, Arepo should call this an **investigation ranking**, not a mathematical estimate of opportunity.

An alert should require all of the following: fresh data, a defined horizon, adequate liquidity, a persistent rather than single-tick signal, calibrated model reliability, no unresolved contract ambiguity, and either a forecast divergence large relative to uncertainty or a material logical inconsistency. A claim of potential tradeability additionally requires positive expected value under executable quotes, fees, slippage and fill assumptions.

## Deployment roadmap, code and implementation brief

### Model architecture recommendation

Start with interpretable baselines:

| Problem | Baseline | Next model if justified |
|---|---|---|
| Binary event probability | Regularised logistic regression | Hierarchical logistic or Bayesian GAM |
| Calibration | Logistic, isotonic or beta calibration | Hierarchical category and time-conditioned calibration |
| Short-horizon direction | Logistic regression with stationary flow inputs | Gradient boosting or compact sequence model |
| Return magnitude | Robust linear or quantile regression | Boosted quantile model |
| Default or transition timing | Cox or discrete-time hazard model | Survival boosting or Bayesian hazard model |
| Regime state | Gaussian hidden Markov model | State-space model with covariates |
| Logical consistency | Deterministic constraints plus uncertainty bands | Probabilistic graphical model |
| Liquidity and impact | Generalised additive model | Gradient boosting with monotonic constraints |

Complex machine learning is justified only when it improves frozen out-of-sample performance over a regularised baseline, maintains calibration, remains stable across regimes and categories, and provides operationally faithful explanations.

Isotonic calibration is flexible but can overfit small samples. Platt calibration is stable but assumes a logistic correction. Beta calibration is attractive for probability inputs because it can model asymmetric distortions near zero and one. Hierarchical calibration is recommended for Arepo because categories and time-to-expiry bands may have different bias while still sharing information across sparse groups.

### Sample calculation and evaluation code

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss


EPS = 1e-6


def probability_logit(price: pd.Series) -> pd.Series:
    """Convert valid probability prices to log odds."""
    clipped = price.astype(float).clip(EPS, 1.0 - EPS)
    return np.log(clipped / (1.0 - clipped))


def probability_features(price: pd.Series) -> pd.DataFrame:
    """Return both intuitive probability-point changes and logit changes."""
    p = price.astype(float)
    return pd.DataFrame(
        {
            "probability_change": p.diff(),
            "logit_change": probability_logit(p).diff(),
        },
        index=price.index,
    )


def order_book_imbalance(
    bid_size: pd.Series,
    ask_size: pd.Series,
) -> pd.Series:
    """Static depth imbalance in [-1, 1]."""
    denominator = bid_size + ask_size
    return ((bid_size - ask_size) / denominator).where(denominator > 0)


def microprice(
    best_bid: pd.Series,
    best_ask: pd.Series,
    bid_size: pd.Series,
    ask_size: pd.Series,
) -> pd.Series:
    """Depth-weighted estimate of the next efficient quote."""
    denominator = bid_size + ask_size
    value = (best_ask * bid_size + best_bid * ask_size) / denominator
    return value.where(denominator > 0)


def cross_sectional_information_coefficient(
    frame: pd.DataFrame,
    date_column: str,
    signal_column: str,
    future_return_column: str,
    minimum_assets: int = 20,
) -> pd.Series:
    """Calculate one Spearman information coefficient for each date."""
    results: dict[pd.Timestamp, float] = {}

    for date, group in frame.groupby(date_column, sort=True):
        usable = group[[signal_column, future_return_column]].dropna()
        if len(usable) < minimum_assets:
            continue

        ic, _ = spearmanr(
            usable[signal_column],
            usable[future_return_column],
        )
        results[pd.Timestamp(date)] = float(ic)

    return pd.Series(results, name="information_coefficient")


@dataclass(frozen=True)
class WalkForwardSplit:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def walk_forward_splits(
    dates: pd.Series,
    train_days: int,
    test_days: int,
    embargo_days: int,
) -> Iterator[WalkForwardSplit]:
    """Generate expanding walk-forward splits with a time embargo."""
    unique_dates = pd.DatetimeIndex(pd.to_datetime(dates).dropna().unique()).sort_values()

    test_start_index = train_days + embargo_days
    while test_start_index < len(unique_dates):
        test_end_index = min(test_start_index + test_days - 1, len(unique_dates) - 1)

        yield WalkForwardSplit(
            train_start=unique_dates[0],
            train_end=unique_dates[test_start_index - embargo_days - 1],
            test_start=unique_dates[test_start_index],
            test_end=unique_dates[test_end_index],
        )
        test_start_index = test_end_index + 1


def evaluate_binary_walk_forward(
    frame: pd.DataFrame,
    features: list[str],
    label: str,
    time_column: str,
) -> pd.DataFrame:
    """Fit only on past data and score each future walk-forward block."""
    data = frame.copy()
    data[time_column] = pd.to_datetime(data[time_column], utc=True)
    data = data.sort_values(time_column)

    rows: list[dict[str, float | str]] = []

    for split in walk_forward_splits(
        data[time_column],
        train_days=365,
        test_days=30,
        embargo_days=7,
    ):
        train = data[
            (data[time_column] >= split.train_start)
            & (data[time_column] <= split.train_end)
        ].dropna(subset=features + [label])

        test = data[
            (data[time_column] >= split.test_start)
            & (data[time_column] <= split.test_end)
        ].dropna(subset=features + [label])

        if len(train) < 500 or len(test) < 50:
            continue
        if train[label].nunique() < 2 or test[label].nunique() < 2:
            continue

        model = LogisticRegression(
            penalty="l2",
            C=0.1,
            max_iter=2_000,
            class_weight="balanced",
        )
        model.fit(train[features], train[label])

        probability = model.predict_proba(test[features])[:, 1]

        rows.append(
            {
                "test_start": str(split.test_start),
                "test_end": str(split.test_end),
                "observations": float(len(test)),
                "brier": brier_score_loss(test[label], probability),
                "log_loss": log_loss(
                    test[label],
                    np.clip(probability, EPS, 1.0 - EPS),
                ),
            }
        )

    return pd.DataFrame(rows)
```

This code is deliberately a baseline. Production research must additionally group observations by event, purge overlapping labels, save model and data versions, estimate costs and preserve every tested configuration.

### Monitoring specification

| Monitor | Trigger | Action |
|---|---|---|
| Data freshness | Source age exceeds asset-specific threshold | Suppress or downgrade output |
| Missingness | Coverage differs materially from training | Activate missing-data warning or abstain |
| Feature drift | PSI, Wasserstein distance or quantile shift exceeds limit | Investigate source or regime change |
| Prediction drift | Output distribution moves without corresponding feature explanation | Inspect pipeline and calibration |
| Calibration drift | Rolling Brier, intercept or slope breaches confidence band | Recalibrate or suspend |
| IC or ranking decay | Rolling OOS IC falls below pre-registered bound | Reduce reliance or retire |
| Cost drift | Realised spread or slippage exceeds model | Update execution model, not historical labels |
| Alert instability | Signal repeatedly enters and exits threshold | Add hysteresis and persistence requirements |
| Capacity decay | Available depth falls below minimum | Suppress tradeability claim |
| Source disagreement | Primary sources conflict | Flag and withhold directional view |
| Resolution ambiguity | Rule or oracle status changes | Suspend outcome model |
| Explanation fidelity | Displayed explanation does not match actual model inputs | Block release |

Models should be versioned with the exact feature schema, training range, code commit, source versions, hyperparameters, calibration model and acceptance results. A prediction record must be reproducible after the fact.

### Implementation phases and acceptance criteria

| Phase | Priority | Deliverable | Acceptance criterion |
|---|---|---|---|
| Point-in-time foundation | Must implement | Immutable raw event, quote, trade, metadata and resolution store | Historical value can be reconstructed exactly as known at any cut-off |
| Identifier and relationship layer | Must implement | Event, condition, token and resolution mapping | No complementary outcome crosses validation folds |
| Target definitions | Must implement | Exact labels for repricing, resolution and executable return | Every UI signal names its target and horizon |
| Baseline calibration model | Must implement | Hierarchical or regularised event-probability model | Better OOS Brier or log loss than unadjusted midpoint with valid confidence interval |
| Liquidity and cost model | Must implement | Spread, impact, fill and capacity estimates | No “potentially executable” claim without positive cost-adjusted value |
| Research Priority redesign | Should implement | Transparent investigation-ranking model | Stable rankings and no probability-like wording |
| Short-horizon flow model | Research first | OFI, multi-level depth and replenishment model | Improvement over midpoint or no-change baseline in purged walk-forward tests |
| Cross-market constraint engine | Should implement | Deterministic logical relationships with semantic review | Precision target met on human-validated relationships |
| Wallet features | Research first | Concentration and activity-history features | Incremental OOS value after liquidity and market-age controls |
| Complex sequence models | Speculative | LSTM, transformer or event-stream model | Clear incremental OOS value over stationary flow baseline |
| Identity or insider inference | Reject | None | Must never be implemented from public wallet behaviour alone |

A suggested calendar is:

| Period | Work |
|---|---|
| First month | Repair field semantics, timestamps, identifiers, point-in-time storage and resolution provenance |
| Second month | Define labels, baselines, grouped walk-forward splits and calibration evaluation |
| Third month | Build liquidity, cost and logical-consistency models |
| Fourth month | Run frozen historical test and begin prospective shadow evaluation |
| Following three to six months | Accumulate prospective evidence, monitor null results and refine only through registered experiments |
| After prospective acceptance | Limited deployment with abstention, monitoring and versioned explanations |

### Claude Code handoff brief

**Product objective**

Arepo is a read-only prediction-market intelligence system. It identifies markets worth investigating, estimates carefully defined probabilities or repricing distributions, explains the evidence and uncertainty, states what would confirm or invalidate each hypothesis, and reports prospective and point-in-time historical performance. It does not place trades or claim proven alpha.

**Approved core data**

Use official Polymarket Gamma data for discovery and metadata, Data API records for public activity, positions, holders and trades where documented, CLOB REST for current books and prices, the public market WebSocket for prospective book reconstruction, and authoritative fill or on-chain records for trade direction. Store oracle and settlement events separately.

**Out-of-scope data**

Bridge, relayer, private trading, withdrawal and account-management endpoints are out of scope for the core read-only product. Perpetuals must use a separate model and schema because their payoff and funding structure differ from binary prediction contracts.

**Required data rules**

Store raw responses immutably. Record source, event, received and available timestamps. Never overwrite historical metadata or outcomes. Never reconstruct historical order books from current state. Preserve model version and calculation version on every signal. Group complementary and related contracts during validation.

**Required targets**

Implement separate labels for five-minute repricing, one-hour repricing, twenty-four-hour repricing, seven-day repricing, final resolution and executable return. Each label must state entry quote, exit quote, spread, fees, slippage, fill rule, liquidity cap, unresolved treatment and censoring rule.

**Required features**

Use probability-point and logit returns, true clock-time momentum, trailing volatility excluding the current observation, spread, relative spread, multi-level depth, OFI, cancellation flow, replenishment, microprice divergence, trade-flow imbalance, robust abnormal trade size, time to resolution, category, liquidity, rule complexity, cross-market constraint residuals and data-quality features.

Wallet concentration may include top-\(k\) share, HHI, entropy and effective participant count. It must never be described as proof of informed or insider activity.

**Required models**

Create separate calibration, repricing, liquidity, event-latency and logical-consistency models. Begin with regularised logistic regression, GAMs, hierarchical models and survival models. Introduce boosting or sequence models only after they produce stable incremental walk-forward value.

**Signal strength**

Define signal strength as forecast divergence divided by forecast uncertainty, then map it to a bounded display scale. Do not define it as a weighted average of unrelated anomalies.

**Confidence**

Calculate model reliability and data quality separately. Model confidence should reflect OOS calibration and uncertainty. Data confidence should reflect freshness, completeness, provenance and source agreement. Display both when useful.

**Research Priority**

Research Priority is an investigation-ranking percentile. It is not probability, expected profit or confidence. Train or calibrate its components against measured user or research value where possible. Until then, label it explicitly as heuristic.

**Alert rules**

Alert only when the data are fresh, the target and horizon are defined, evidence persists, the model is within its validated domain, liquidity exceeds a minimum, and no material resolution ambiguity exists. A tradeability statement additionally requires positive expected payoff after executable spread, fees, slippage and fill probability.

**Replay rules**

Prospective replay may show the exact frozen model and data available at the historical timestamp. Reconstructed price-only analysis must be labelled “historical price-only reconstruction”. It must not display unavailable historical order-book, wallet or flow evidence. Current metadata must not be used to alter the historical universe.

**Anti-overfitting controls**

Maintain a complete experiment ledger. Use grouped, purged and embargoed walk-forward validation. Hold out categories and regimes. Apply false-discovery or family-wise corrections across all tried features, parameters and thresholds. Report null and negative configurations. Use White Reality Check or SPA where many strategies are compared, and calculate PBO and Deflated Sharpe where return strategies are selected.

**Tests**

Unit tests must cover all formulas and boundary conditions. Data tests must cover duplicate sequence numbers, stale quotes, crossed books, missing outcomes, identifier conflicts and timestamp ordering. Integration tests must reconstruct the same signal from a frozen fixture. Backtest tests must demonstrate that post-cut-off information cannot change eligibility, features, labels or execution prices.

**Acceptance criteria**

A forecast model must beat the unadjusted market-price baseline on an untouched test set using proper scoring rules, with uncertainty bounds and no severe subgroup deterioration. A repricing model must improve over no-change and midpoint baselines. A tradeability claim requires positive prospective cost-adjusted performance, adequate fill rate and acceptable capacity. A feature must be removed when it lacks incremental walk-forward value, is unstable, or cannot be reconstructed point in time.

**Features to remove or rename immediately**

Rename `movement_1h` unless it uses a true one-hour interval. Remove claims that evidence families are independent. Permit neutral hypotheses. Stop presenting the existing composite anomaly score as if it were target-specific predictive evidence. Separate current-state demonstrations from historical replays. Do not use default zero fees for profitability claims.

**Unresolved experiments**

Priority experiments are calibration by probability, category, liquidity and time to resolution; probability-point versus logit movement; top-level versus multi-level OFI; cancellation and replenishment; cost-adjusted persistence after large trades; wallet concentration after controlling for liquidity; logical constraint persistence; and prospective comparison of raw midpoint, calibrated probability and external forecast combinations.

**Strict research constraint**

No Arepo component may claim alpha unless it has positive, prospective or untouched out-of-sample evidence after executable spread, slippage, fees, fill probability, liquidity limits, capacity and resolution risk. A statistically unusual observation is not itself a forecast, and a correct forecast is not automatically a profitable trade.