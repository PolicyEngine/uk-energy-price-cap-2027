# Energy price cap, January to March 2027: household bills

The analysis behind PolicyEngine's post on what the energy price cap for 1 January to 31 March 2027 would mean for household energy bills in Great Britain, by income decile.

## Status

Ofgem announces the cap for January to March 2027 on 25 November 2026 ([Ofgem's notice of the October cap](https://www.ofgem.gov.uk/publications/changes-energy-price-cap-between-1-october-and-31-december-2026)). Until then, the January rates are Cornwall Insight's final forecast of 18 November 2026 ([press release](https://www.cornwall-insight.com/press-releases/energy-bills-set-for-steep-rise-in-january/)): a typical dual-fuel Direct Debit bill of £2,166 a year, against Ofgem's current cap of £1,723 ([rates](https://www.ofgem.gov.uk/your-energy-supply/your-energy-bill/energy-price-cap-unit-rates-and-standing-charges)).

## What it does

`run_cap.py`:

1. Calculates each household's electricity and gas spending for 2026-27 in PolicyEngine UK and restates it at October to December 2026 prices with the engine's energy price indices (2026Q4 level over the fiscal-year level, per fuel).
2. Removes the 5% VAT at which Microcosm prices electricity, since domestic electricity in Great Britain carries no VAT from 1 October 2026.
3. Applies, per fuel, the ratio of the January typical bill (Cornwall Insight) to the October typical bill (Ofgem's rates at 2,500 kWh electricity and 9,500 kWh gas).
4. Leaves out Northern Ireland, which the Ofgem cap does not cover. Households do not change their use.
5. Reports, for Great Britain and by income decile (equivalised HBAI net income before housing costs, person-weighted): average bills before and after, the change, spending as a share of HBAI net income, households spending more than 10% of net income on energy, and four household examples computed from the published rates alone.

`results/results.json` is the output behind the post's tables and charts. It holds weighted aggregates only: no record identifiers, weights or record counts. `check_floor.py` prints the number of survey households behind each published cell; the smallest (Great Britain households with zero income, as Households Below Average Income statistics reset negative incomes to zero) rests on 183 survey households, and each income decile on more than 1,700.

## Model and data

| Component | Version |
|---|---|
| policyengine | 6.20.2 |
| policyengine-uk | 2.177.7 |
| policyengine-core | 3.34.10 |
| Microcosm UK | build `uk-frs-calibration-attempt-20261115T104657Z-fcfac709`, SHA-256 `301d2fe5e7805c5a6242b37843cb118445aefd59a0593833362ab5a6e2f9ba90` |

policyengine 6.20.2 certifies that engine and dataset pair. `run_cap.py` refuses any other installed versions or a file with another SHA-256.

## How to run

```bash
uv sync
HUGGING_FACE_TOKEN=<read token> uv run python download_data.py
uv run python run_cap.py
uv run python check_floor.py   # optional: survey households per cell (stdout only)
```

The dataset is in the private Hugging Face dataset `policyengine/populace-uk-private`, so the download needs a token with read access. `MICROCOSM_DATASET` points the scripts at a file elsewhere. A national run takes about a minute and several gigabytes of memory.

## Updating for Ofgem's announcement

When Ofgem publishes the January to March 2027 cap:

1. In `run_cap.py`, replace `JAN_FORECAST_BILL` with Ofgem's typical annual bill for each fuel (GB average, Direct Debit, at 2,500 kWh electricity and 9,500 kWh gas) and `JAN_FORECAST_UNIT` with its unit rates. The script backs the standing charges out of those two; or set them from Ofgem's rates directly.
2. Rerun `run_cap.py` and `check_floor.py`.
3. Update the post's tables, charts and key results from `results/results.json`.

## Limits

- The cap covers default tariffs; the script applies the change to every household, including those on fixed tariffs.
- It applies the Direct Debit change to every household; the data do not separate Direct Debit from standard credit.
- It scales each fuel's spending by one factor, so it overstates the rise for households that use less than the typical amount and understates it for those that use more.
- January rates are held for a full year, as in Ofgem's typical bill.

The method for restating spending follows PolicyEngine's [energy price cap model](https://github.com/PolicyEngine/uk-energy-price-cap-jan-2027/blob/engine-2.177.7-microcosm-9e18f010/src/uk_energy_price_cap/model_run.py).

## Licence

[GNU Affero General Public License v3.0](LICENSE), like other PolicyEngine repositories.
