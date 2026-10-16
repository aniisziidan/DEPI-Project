# US pizza-box price check, October 2026

65 listings from 28 sellers, read from search-result extracts on 16 Oct 2026 (the network policy blocked opening the pages). Averages use regular single-case prices of plain or stock-print boxes from mainstream sellers; premium, custom-print, clearance and outlier listings are recorded but excluded. Data: `data/us_pizza_box_prices_2026-10-16.csv`.

## What pizzerias pay per box (regular case-of-50 prices)

| Size | Listings | Sellers | Average | Median | Range | Cheapest regular price | Best bulk or sale price | Model BASE listing |
|---|---:|---:|---:|---:|---|---|---|---:|
| 10" | 1 | 1 | $0.260 | $0.260 | $0.260–$0.260 | $0.260 (WebstaurantStore) | — | — |
| 12" | 10 | 6 | $0.439 | $0.445 | $0.320–$0.553 | $0.320 (WebstaurantStore) | $0.300 (WebstaurantStore, 2+ bundles) | $0.300 |
| 14" | 18 | 10 | $0.572 | $0.545 | $0.380–$0.899 | $0.380 (WebstaurantStore) | $0.340 (Costco Business Center, sale; last seen 7 Dec 2025) | $0.390 |
| 16" | 13 | 8 | $0.639 | $0.610 | $0.470–$0.817 | $0.470 (WebstaurantStore) | $0.388 (Costco Business Center, sale price per tracker) | $0.450 |
| 18" | 1 | 1 | $0.580 | $0.580 | $0.580–$0.580 | $0.580 (WebstaurantStore) | — | — |

## Average by buying channel

| Size | Cash-and-carry and club | Marketplace and general retail | Online restaurant supply |
|---|---:|---:|---:|
| 10" | — | — | $0.260 |
| 12" | $0.432 | — | $0.442 |
| 14" | $0.563 | $0.608 | $0.550 |
| 16" | $0.589 | $0.798 | $0.627 |
| 18" | — | — | $0.580 |

## Operator and trade reports (not averaged)

- 16" — $0.36 per box: PMQ Think Tank (operator forum), 16x16 boxes (undated; excludes shipping). https://thinktank.pmq.com/t/70-cents-a-box/14608
- 14" — $0.20 per box: Quora (former chain employee), Large 14 inch box at a Pizza Hut store (chain contract price; anecdote). https://www.quora.com/What-is-the-cost-of-custom-pizza-boxes-compared-to-standard-pizza-boxes
- 14" — $0.38 per box: Pizza Today (operator column), Large box in per-pizza food costing (operator costing figure). https://pizzatoday.com/departments/our-experts/well-maintain-food-costs
- 12" — $0.27 per box: Pizza Marketplace (trade interview), Blank 12 inch box (about 2020; 0.48 with liners and folding labour). https://www.pizzamarketplace.com/articles/biodegradable-pizza-box-promises-restaurateurs-cost-savings/

## What-if: BigBoxPizza sells at prices based on the market average

The model's BASE listing prices are the cheapest online prices (WebstaurantStore). Replacing them with the market averages (12" scaled to E-flute: $0.351; 14" $0.572; 16" $0.639) and keeping every cost and the 20% E-flute discount and 25% buyer margin:

| Configuration | Buyer price (avg) | Gross margin, model | Gross margin, market average | Margin after all costs, market average | Result, first shipment | Result, repeat shipment | Margin after all costs, repeat |
|---|---:|---:|---:|---:|---:|---:|---:|
| Quoted 60,000 mix, one 40' HC | $0.330 | −21.5% | +10.5% | −13.0% | −$2,544 | $23 | +0.1% |
| Full 40' HC, equal mix | $0.330 | −9.7% | +19.2% | −0.6% | −$163 | $2,404 | +9.6% |
| Full 40' HC, 14" only | $0.343 | −20.7% | +17.6% | −2.0% | −$511 | $2,056 | +8.0% |
| Full 40' HC, 16" only | $0.383 | −6.0% | +25.4% | +5.7% | $1,442 | $4,009 | +15.9% |
| Full 40' HC, 12" only | $0.264 | +1.3% | +15.8% | −3.1% | −$852 | $1,715 | +6.2% |
