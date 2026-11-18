"""Energy price cap, January to March 2027: household bills by income decile.

Certified pair: policyengine 6.20.2 bundle, policyengine-uk 2.177.7,
policyengine-core 3.34.10, Microcosm build
uk-frs-calibration-attempt-20261115T104657Z-fcfac709 (SHA-256 301d2fe5...).

Method (reused from PolicyEngine/uk-energy-price-cap-jan-2027, drill 11,
model_run.py):
1. Each household's fiscal 2026-27 electricity and gas spend from the model,
   restated to an annual spend at October to December 2026 prices with the
   engine's own indices (2026Q4 quarterly level over the fiscal-year level),
   fuel by fuel.
2. The model's spend is priced at 5% VAT (domestic_energy_vat.py); domestic
   electricity is zero-rated in Great Britain from 1 October 2026, so
   electricity spend is divided by 1.05 to give the October to December bill.
   Ofgem's October rates and Cornwall Insight's January forecast both carry
   0% VAT on electricity and 5% on gas.
3. January to March 2027 bill = October to December bill x a factor per fuel:
   Cornwall Insight's forecast typical bill for that fuel over the typical
   bill for that fuel at Ofgem's October to December rates (same 2026
   typical consumption values, 2,500 kWh electricity, 9,500 kWh gas).
4. Great Britain only (Northern Ireland is outside the Ofgem cap). Static:
   households do not change how much they use.
Income shares are decile totals: sum of spend over sum of HBAI net income
before housing costs (hbai_household_net_income), the income that ranks the
deciles.
"""

import hashlib
import os
import json
import sys
from pathlib import Path

import numpy as np

BUILD = "uk-frs-calibration-attempt-20261115T104657Z-fcfac709"
# Path to the build's file (see README); MICROCOSM_DATASET overrides it.
DATASET = Path(
    os.environ.get(
        "MICROCOSM_DATASET",
        f"data/releases/microcosm-uk-2024-25-national/{BUILD}/microcosm_uk_2024_25.h5",
    )
)
SHA256 = "301d2fe5e7805c5a6242b37843cb118445aefd59a0593833362ab5a6e2f9ba90"
YEAR = 2026
DAYS = 365

# ---- Cap inputs (Cornwall Insight forecast, 18 November 2026). ----
TDCV = {"electricity": 2500, "gas": 9500}
# Ofgem, GB average Direct Debit, 1 October to 31 December 2026 (p/kWh, p/day;
# 0% VAT on electricity, 5% on gas).
OCT = {
    "electricity": {"unit": 26.32, "standing": 54.83},
    "gas": {"unit": 7.97, "standing": 29.68},
}
# Cornwall Insight final forecast for 1 January to 31 March 2027
# (18 November 2026), typical bill per fuel, GBP a year.
JAN_FORECAST_BILL = {"electricity": 1017.09, "gas": 1148.80}
JAN_FORECAST_UNIT = {"electricity": 32.54, "gas": 10.90}
ENERGY_INPUT_VAT = 0.05


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def typical_bill(rates, fuel, kwh=None):
    kwh = TDCV[fuel] if kwh is None else kwh
    return (kwh * rates[fuel]["unit"] + DAYS * rates[fuel]["standing"]) / 100


def main(out_path="results/results.json"):
    from importlib import metadata

    versions = {
        p: metadata.version(p)
        for p in ("policyengine", "policyengine-uk", "policyengine-core")
    }
    assert versions == {
        "policyengine": "6.20.2",
        "policyengine-uk": "2.177.7",
        "policyengine-core": "3.34.10",
    }, versions
    assert sha256(DATASET) == SHA256

    oct_bill = {f: typical_bill(OCT, f) for f in TDCV}
    factor = {f: JAN_FORECAST_BILL[f] / oct_bill[f] for f in TDCV}
    # Cornwall's standing charges are printed to the penny per day; back them
    # out of the fuel totals so the typical bill reproduces exactly.
    jan_standing = {
        f: (JAN_FORECAST_BILL[f] * 100 - TDCV[f] * JAN_FORECAST_UNIT[f]) / DAYS
        for f in TDCV
    }
    JAN = {
        f: {"unit": JAN_FORECAST_UNIT[f], "standing": jan_standing[f]}
        for f in TDCV
    }

    from policyengine_uk import Microsimulation

    sim = Microsimulation(dataset=str(DATASET))
    p = sim.tax_benefit_system.parameters.gov.economic_assumptions.energy_prices
    to_q4 = {
        f: float(getattr(p.quarterly, f)("2026-10-01"))
        / float(getattr(p.fiscal_year, f)(f"{YEAR}-01-01"))
        for f in TDCV
    }

    def calc(v):
        return np.asarray(sim.calculate(v, YEAR, map_to="household").values)

    w = calc("household_weight").astype(float)
    country = calc("country").astype(str)
    decile = calc("household_income_decile").astype(int)
    # HBAI net income before housing costs: the income that ranks the deciles.
    net = calc("hbai_household_net_income").astype(float)
    pe_net = calc("household_net_income").astype(float)
    elec_fy = calc("electricity_consumption").astype(float)
    gas_fy = calc("gas_consumption").astype(float)

    gb = country != "NORTHERN_IRELAND"
    elec_q4 = elec_fy * to_q4["electricity"] / (1 + ENERGY_INPUT_VAT)
    gas_q4 = gas_fy * to_q4["gas"]
    before = elec_q4 + gas_q4
    after = elec_q4 * factor["electricity"] + gas_q4 * factor["gas"]
    change = after - before

    def wmean(x, m):
        return float(np.sum(x[m] * w[m]) / np.sum(w[m]))

    def wmedian(x, m):
        order = np.argsort(x[m])
        xs, ws = x[m][order], w[m][order]
        c = np.cumsum(ws)
        return float(xs[np.searchsorted(c, c[-1] / 2)])

    dual = gb & (elec_q4 > 0) & (gas_q4 > 0)
    elec_only = gb & (elec_q4 > 0) & (gas_q4 == 0)

    out = {
        "versions": versions,
        "dataset": {"build": DATASET.parent.name, "sha256": SHA256},
        "inputs": {
            "oct_typical_bill": oct_bill,
            "oct_typical_total": sum(oct_bill.values()),
            "jan_forecast_bill": JAN_FORECAST_BILL,
            "jan_forecast_total": sum(JAN_FORECAST_BILL.values()),
            "factor": factor,
            "jan_standing_p_per_day_backed_out": jan_standing,
            "to_q4": to_q4,
        },
        "decile_values_present": sorted(set(decile[gb].tolist())),
        "gb": {
            "households_m": float(w[gb].sum() / 1e6),
            "households_dual_fuel_m": float(w[dual].sum() / 1e6),
            "households_electric_only_m": float(w[elec_only].sum() / 1e6),
            "households_no_energy_spend_m": float(
                w[gb & (before <= 0)].sum() / 1e6
            ),
            "elec_total_bn_fy_model": float(np.sum(elec_fy[gb] * w[gb]) / 1e9),
            "gas_total_bn_fy_model": float(np.sum(gas_fy[gb] * w[gb]) / 1e9),
            "before_total_bn": float(np.sum(before[gb] * w[gb]) / 1e9),
            "after_total_bn": float(np.sum(after[gb] * w[gb]) / 1e9),
            "change_total_bn": float(np.sum(change[gb] * w[gb]) / 1e9),
            "mean_before": wmean(before, gb),
            "mean_after": wmean(after, gb),
            "mean_change": wmean(change, gb),
            "median_before": wmedian(before, gb),
            "dual_mean_before": wmean(before, dual),
            "dual_median_before": wmedian(before, dual),
            "dual_mean_change": wmean(change, dual),
            "elec_only_mean_before": wmean(before, elec_only),
            "elec_only_mean_change": wmean(change, elec_only),
            "share_of_income_before": float(
                np.sum(before[gb] * w[gb]) / np.sum(net[gb] * w[gb])
            ),
            "share_of_income_after": float(
                np.sum(after[gb] * w[gb]) / np.sum(net[gb] * w[gb])
            ),
            "spend_over_10pct_income_before_m": float(
                w[gb & (before > 0) & ((net <= 0) | (before > 0.1 * net))].sum() / 1e6
            ),
            "spend_over_10pct_income_after_m": float(
                w[gb & (after > 0) & ((net <= 0) | (after > 0.1 * net))].sum() / 1e6
            ),
            "share_of_household_net_income_before": float(np.sum(before[gb] * w[gb]) / np.sum(pe_net[gb] * w[gb])),
            "net_income_nonpositive_m": float(w[gb & (net <= 0)].sum() / 1e6),
        },
        "deciles": [],
    }
    for d in range(1, 11):
        m = gb & (decile == d)
        out["deciles"].append(
            {
                "decile": d,
                "households_m": float(w[m].sum() / 1e6),
                "mean_net_income": wmean(net, m),
                "mean_elec_before": wmean(elec_q4, m),
                "mean_gas_before": wmean(gas_q4, m),
                "mean_before": wmean(before, m),
                "mean_after": wmean(after, m),
                "mean_change": wmean(change, m),
                "share_before": float(
                    np.sum(before[m] * w[m]) / np.sum(net[m] * w[m])
                ),
                "share_after": float(
                    np.sum(after[m] * w[m]) / np.sum(net[m] * w[m])
                ),
                "share_before_household_net_income": float(np.sum(before[m] * w[m]) / np.sum(pe_net[m] * w[m])),
                "median_hh_share_before": wmedian(np.where(net > 0, before / np.where(net > 0, net, 1), np.inf), m),
                "median_hh_share_after": wmedian(np.where(net > 0, after / np.where(net > 0, net, 1), np.inf), m),
                "share_dual_fuel": float(w[m & dual].sum() / w[m].sum()),
            }
        )

    # Household examples: arithmetic on published rates, not model output.
    examples = {
        "typical_dual_fuel": {"electricity": 2500, "gas": 9500},
        "low_dual_fuel_half_typical": {"electricity": 1250, "gas": 4750},
        "high_dual_fuel_double_typical": {"electricity": 5000, "gas": 19000},
        "electric_only_typical_electricity": {"electricity": 2500, "gas": 0},
    }
    ex_out = {}
    for name, kwh in examples.items():
        row = {}
        for label, rates in (("oct", OCT), ("jan", JAN)):
            e = typical_bill(rates, "electricity", kwh["electricity"])
            g = typical_bill(rates, "gas", kwh["gas"]) if kwh["gas"] > 0 else 0
            row[label] = {"electricity": e, "gas": g, "total": e + g}
        row["change"] = row["jan"]["total"] - row["oct"]["total"]
        row["change_pct"] = row["change"] / row["oct"]["total"]
        ex_out[name] = row
    out["examples"] = ex_out

    Path(out_path).write_text(json.dumps(out, indent=2))
    print(json.dumps(out["gb"], indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:2])
