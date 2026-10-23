# Driver model, scenarios, sensitivity and reverse valuation (`KOD-FCFF-v1`)

The workstation has one transparent annual model for ordinary operating companies, in `kod/workstation/model.py`. It works out what an analyst's stated
assumptions imply. It is not a fair value, a forecast made by KOD, or a recommendation. Every number comes from an assumption set the analyst saved with a
rationale. Filed history can suggest starting values, but never fills a forecast silently. Nothing here places an order or reads a market feed.

## Formula

These quantities are computed in this order, for forecast years t = 1 … N. All rates are fractions, and every quantity is an exact decimal with
34 significant digits.

| Quantity | Definition |
|---|---|
| Revenue[t] | Revenue[t−1] × (1 + growth[t]), with Revenue[0] = base revenue of a stated fiscal year |
| EBIT[t] | Revenue[t] × operating_margin[t] |
| Taxes[t] | max(EBIT[t], 0) × cash_tax_rate[t]. A loss earns no tax credit in this model; this is declared, not hidden |
| NOPAT[t] | EBIT[t] − Taxes[t] |
| D&A[t] | Revenue[t] × depreciation_rate[t] |
| Capex[t] | Revenue[t] × capex_rate[t], a nonnegative investment amount |
| ΔNWC[t] | (Revenue[t] − Revenue[t−1]) × nwc_rate[t]. Positive consumes cash; a shrinking business releases it |
| FCFF[t] | NOPAT[t] + D&A[t] − Capex[t] − ΔNWC[t] |
| DF[t] | 1 / (1 + discount_rate)^t, discounted at the end of each year |
| TV[N] | NOPAT[N] × (1 + g) × (1 − g / terminal_roic) / (discount_rate − g). This is the value-driver perpetuity: reinvestment is g / terminal_roic of NOPAT |
| EV | Σ FCFF[t] × DF[t] + TV[N] × DF[N] |
| Equity | EV + cash − debt − other_senior_claims + other_adjustments |
| Per share | Equity / share_count |

The test `workstation_tests/test_gate_e.py` works an example by hand, year by year. The evaluation
([evaluation/README.md](evaluation/README.md), task T5) recomputes a per-share value with a separate implementation of this table.

## Assumption set

An assumption set is a JSON object, validated completely before it is saved. Every problem is listed at once, and nothing invalid is stored.

| Field | Meaning and rule |
|---|---|
| `horizon_years` | Integer, 1 to 30 |
| `base.revenue`, `base.fiscal_year_end` | Positive decimal text, and the date of the fiscal year it belongs to |
| `currency` | Three-letter code. Nothing is converted between currencies anywhere |
| `valuation_date` | A date. A bridge or share count dated after it is refused for a per-share value |
| `revenue_growth`, `operating_margin`, `cash_tax_rate`, `depreciation_rate`, `capex_rate`, `nwc_rate` | Either one value for every year, or a list with exactly one value per year. Ranges: growth −0.95 to 5; margin −2 to 1; tax 0 to 1; D&A 0 to 1; capex 0 to 2; NWC −2 to 2 |
| `discount_rate`, `terminal_growth`, `terminal_roic` | Discount rate 0.001 to 1; terminal growth −0.5 to 0.2; terminal ROIC 0.001 to 10. The discount rate must exceed terminal growth, and g / terminal ROIC must not exceed 100% |
| `bridge.cash`, `bridge.debt`, `bridge.other_senior_claims`, `bridge.other_adjustments`, `bridge.as_of` | Nonnegative amounts (the formula applies the sign) and the balance-sheet date |
| `shares.count`, `shares.as_of`, `shares.basis` | Positive count, its date, and a stated basis (for example "diluted shares at the valuation date, analyst-reviewed"). The analyst selects the count; KOD never picks it |
| `treatments` | One declared choice each for stock compensation, leases, convertibles, non-controlling interests and tax losses. "not_modelled" is allowed and stays visible as a limitation |
| `sources` | Optional observation ids the analyst cites for any input |

Numbers are decimal text, never binary floats. Values outside a range are refused, not clipped.

### Statuses

- **ok:** a per-share value. It needs a complete, dated bridge in the scenario's currency and a selected share count.
- **ev_only:** enterprise value only. The reasons say what is missing for a per-share value.
- **invalid:** for example, terminal reinvestment above 100%.
- **not_applicable:** the operating-company model does not fit the business.

Warnings accompany results:

- an operating loss in any year;
- final-year NOPAT that is not positive;
- a terminal value above 75% of enterprise value;
- equity that is not positive.

### Business types outside the model

The business type comes from the SIC code in the preserved SEC submissions response. It is `not_applicable` for:

- banks and credit institutions (SIC 6000–6199);
- insurers (6300–6411);
- REITs (6798).

The dossier also marks the cash-flow ratios not applicable for them. Where no submissions response is preserved, the business type is unknown, and the
model runs with that stated.

## Versions and scenarios

An assumption set is identified by its company, its scenario label (`bear`, `base` or `bull`) and its name.

- **Saving.** Each save creates a new immutable version with its author, time, rationale and the version it replaced. Saving identical assumptions is refused.
- **Labels.** The scenario labels attach no probabilities.
- **Recorded runs.** Running a version records a calculation whose inputs are the version and the observations it cites. The calculation's information time
  is the version's own save time, under the observed day-end policy. When a version is revised, the old version's calculations are marked superseded.
  `scenarios.changed_fields` lists exactly what changed, and the thesis review trace shows it.

A dossier at a cutoff lists, for each set, the latest version saved at or before the cutoff. A scenario written later is absent from an earlier dossier.

### Suggestions from history

`suggest_from_history` shows reference values beside the form, each with its observation ids:

- the latest eligible fiscal year's revenue;
- that year's operating margin, capex and D&A as shares of revenue;
- last year's growth.

They are suggestions to accept or change. No growth path is extrapolated, and nothing is applied without the analyst saving it.

## Sensitivity grid

`model.sensitivity` takes two different parameters, each with 1 to 9 values. The parameters can be revenue growth, operating margin, discount rate,
terminal growth or capex rate.

- **Held values.** Every other assumption is held at its saved value, and the held values are listed with the grid.
- **Yearly assumptions.** A single grid value replaces the whole yearly path with that level. It is not a shift.
- **Invalid cells.** A cell whose pair is invalid (for example, discount rate ≤ terminal growth) says so instead of showing a number.
- **What-if.** Opening a cell shows a what-if result that is not saved. To keep it, save a new version.

## Reverse valuation

`model.reverse` solves for one parameter (revenue growth, operating margin, discount rate or terminal growth) so that the value per share equals a stated
positive target, with everything else fixed.

1. **Bracket.** The solve uses an explicit bracket. The defaults are growth −0.5 to 1.5, margin −0.5 to 0.8, discount rate 0.02 to 0.40 and terminal growth
   −0.05 to 0.08. The analyst can narrow the bracket.
2. **Sampling.** Before solving, the model is sampled at 41 points across the bracket. Each sample must be defined and must move strictly in one direction.
   Otherwise the result is one of these:
   - `invalid_bracket`: undefined somewhere in the bracket;
   - `not_monotonic`: a solution would not be unique; sample values are shown;
   - `no_solution`: the target lies outside the range the bracket produces; the range is shown.
3. **Bisection.** It stops within 0.0001 per share or after 200 iterations (`not_converged`). The result shows the solved level, the residual and a
   check value.
4. **Other cases.** `ev_only` and `not_applicable` carry through from the model.

The answer is labelled "the level required under this model and these assumptions". It is not a statement of what the market believes.

## Prices and market context

Prices are entered by hand or imported from a strict CSV (`kod/workstation/prices.py`; see [DATA_SOURCES.md](DATA_SOURCES.md)). Each price records:

- currency, source, session, time zone and adjustment (`raw`, `split_adjusted` or `total_return`);
- the coverage of the feed it came from.

A daily close counts as available from midnight after its trading day in that time zone.

The market context of a scenario uses the latest **raw** close eligible at the cutoff. It shows the price, the implied market value (price × the scenario's
selected share count) and the per-share value as a percentage above or below the price. The comparison is withheld, with the reason, when:

- the price is adjusted;
- the currencies differ;
- no share count is selected.

A share count dated differently from the price is noted.

## Limitations, stated rather than modelled

- **One annual explicit forecast.** There is no quarterly model, mid-year discounting, explicit balance sheet, debt schedule, or option or dilution
  modelling beyond the declared treatments.
- **No conversion and no blending.** There is no currency conversion and no probability-weighted blend of scenarios.
- **Some businesses are not covered.** Banks, insurers and REITs are not modelled. A company with unknown SIC is run with its business type stated as
  unknown.
- **Analyst inputs.** The bridge and share count are analyst inputs with dates. KOD does not derive them from filings.
- **Not a fair value.** The result is not a fair value or a target price, and nothing here is a recommendation to buy or sell.
