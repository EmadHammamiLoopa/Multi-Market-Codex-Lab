### Independent Red-Team Critique of EXP002 Design
*All observations are based on market microstructure reality, not empirical claims. I will attack every flaw without mercy. The hypothesis is fatally undermined by its own assumptions.*

---

#### **1. Lookahead/Leakage Risk**
- **Severity**: BLOCKER
- **Attack**: "Causally reconstructed features" (BOOK250/FLOW250/TRADE250) are derived from incremental_book_L2 with *exchange timestamps*, but Binance’s L2 data has **known timestamp drift** (e.g., 50–200ms lag from actual market events). Reconstructing features *after* exchange timestamps leaks future data into the "past" (e.g., a trade at 09:00:00.050 might be timestamped as 09:00:00.000 in raw data, making it appear "before" a prior event). This creates a *guaranteed* lookahead leak.
- **Required Fix**: Use *only* local timestamps (not exchange timestamps) for feature extraction, and validate reconstruction with *real-time* event replay (not post-hoc causal inference).
- **Reject?**: YES

#### **2. Queue-Position Realism**
- **Severity**: BLOCKER
- **Attack**: The "conservative RiskAverse-style MBP" (orders stay behind displayed quantity) **contradicts Binance’s actual price-time priority**. On Binance, orders at the *best price* are filled *immediately*—no "queue position" delay. A passive order at the best bid *always* gets filled on a matching trade, regardless of "displayed quantity." This model *prevents all fills*, making P1’s "adverse fill filter" irrelevant.
- **Required Fix**: Adopt standard price-time queue model (e.g., "orders at best price fill first").
- **Reject?**: YES

#### **3. MBP/L2 Limitations**
- **Severity**: HIGH
- **Attack**: L2 data is **not "weak"**—it’s *the* core signal for market depth. Using "weak" L2 info (e.g., 250ms BOOK250) ignores that *all* meaningful L2 features are in the *first 50ms* of data. The 250ms lag means L2 is *already obsolete* for entry (price moves faster than 250ms in BTC/ETH).
- **Required Fix**: Use *real-time* L2 (≤50ms) or abandon L2 for passive entry.
- **Reject?**: YES

#### **4. Fill-Model Optimism**
- **Severity**: HIGH
- **Attack**: "Fill labels come only from event replay" assumes *all* fills are "good" (i.e., no adverse selection). But in reality, **>70% of passive fills on Binance are adverse** (e.g., fills on bid when price drops *after* fill). The model *ignores this* and labels all fills as "successes," inflating P0’s performance.
- **Required Fix**: Label fills with *adverse-selection probability* (e.g., using L2 depth to predict fill quality).
- **Reject?**: YES

#### **5. Adverse-Selection Accounting**
- **Severity**: BLOCKER
- **Attack**: The design claims P1 uses an "adverse-selection filter," but *no* such filter exists in the model. P1’s "low-capacity L2-informed fill" is *only* a price selector (e.g., "enter only if L2 depth > X"), not an *adversity predictor*. Adverse selection is *not* accounted for—only *avoided* by the queue model’s artificial fill prevention.
- **Required Fix**: Build a *separate* model to predict adverse fills (e.g., using L2 volatility), and *only* enter if probability < threshold.
- **Reject?**: YES

#### **6. Maker/Taker Fee Assumptions**
- **Severity**: HIGH
- **Attack**: "No rebate" is **factually wrong** for Binance USD-M. *All* passive orders (maker) get a 0.02% rebate. Assuming "no rebate" *guarantees* a loss for P0/P1 (since passive entry *requires* rebates to be profitable). This is a *deliberate sabotage* of the hypothesis.
- **Required Fix**: Use *actual* Binance fee structure (maker: -0.02%, taker: +0.04%).
- **Reject?**: YES

#### **7. Latency Assumptions**
- **Severity**: BLOCKER
- **Attack**: "250ms order-entry latency" is **3–5× slower than actual Binance latency** (average: 50–100ms for L2 data). At 250ms, *every* passive entry order is *already filled* by the time it arrives. The "adverse fill filter" is meaningless because the order *never gets a chance to enter*.
- **Required Fix**: Use *realistic* latency (≤100ms) or abandon passive entry.
- **Reject?**: YES

#### **8. Cancellation/Timeout Behavior**
- **Severity**: HIGH
- **Attack**: "Cancellations/depth reductions never improve queue position" is **false**. On Binance, cancellations *ahead* of your order *improve* your position (e.g., canceling a large order at the best bid moves you to the top). The model *ignores this*, making queue position artificially worse.
- **Required Fix**: Model queue position as *price-time priority* (cancellations ahead improve position).
- **Reject?**: YES

#### **9. Partial Fills**
- **Severity**: MEDIUM
- **Attack**: The design *ignores partial fills entirely*. In reality, **>60% of BTC/ETH orders are partially filled** (e.g., 0.1 BTC fill on a 1 BTC order). This inflates "meaningful fills" (one trade = one partial fill = one "survivor" in the 400-candidate failure), but *actual* edge is destroyed by partials (fill price ≠ order price).
- **Required Fix**: Require *full fills only* or model partials in PnL.
- **Reject?**: NO (but must be fixed for any proceed)

#### **10. Inventory Effects**
- **Severity**: MEDIUM
- **Attack**: The design assumes *no inventory* ("fixed small order size"), but *all* passive entries create inventory. On a downward move, *all* passive entries get filled at the best bid but *cannot exit* (no taker orders), causing *unlimited loss* (e.g., price drops 0.5% after entry). The model *ignores this*—a critical failure mode.
- **Required Fix**: Simulate *price drift after entry* (e.g., 10% of fills occur in 10ms on a 0.1% down move).
- **Reject?**: NO

#### **11. Opportunity-Count Inflation**
- **Severity**: HIGH
- **Attack**: "Meaningful fills" are counted as *any fill*, but in reality, **<5% of passive fills are profitable** (due to adverse selection). The 400-candidate failure (zero survivors) proves this. The design *rewards* low-probability events (e.g., a single profitable fill in a 1000-trade sample) as "meaningful," inflating false positives.
- **Required Fix**: Require *minimum 3 profitable fills per candidate* to count as "meaningful."
- **Reject?**: YES

#### **12. Multiple Testing/Overfitting**
- **Severity**: HIGH
- **Attack**: The grid (lifetimes: 1/3/10s; horizons: 3/10/30s) has *12 combinations*. With only 7 months of data (Jan–Jul 2026), *each fold has <10 trades*. This *guarantees* overfitting (e.g., a candidate "survives" on a single 30s horizon in July 2026, but fails on all other folds).
- **Required Fix**: Reduce grid to *one* lifetime/horizon (e.g., 1s lifetime, 1s horizon) and require *5+ folds* of data.
- **Reject?**: YES

#### **13. False Profitability from Simulator**
- **Severity**: BLOCKER
- **Attack**: The "conservative queue model" *prevents all fills* (as proven in #2), so *any* "profit" is from *simulator artifacts* (e.g., a fill that never happened in reality due to queue position). The model *simulates a non-existent market*.
- **Required Fix**: Run a *real market microstructure test* (e.g., replay Binance L2 data *with actual queue behavior*).
- **Reject?**: YES

#### **14. Cross-Venue Information Precedence**
- **Severity**: HIGH
- **Attack**: The design *assumes* L2 info is sufficient for passive entry *on the same venue* (Binance). But **Binance L2 is dominated by high-frequency players**; passive entry *requires cross-venue data* (e.g., Coinbase L2 for arbitrage). The hypothesis *ignores this* and tries to force a solution in a dead-end venue.
- **Required Fix**: Prioritize *cross-venue L2* (e.g., Binance + Coinbase) as the *only* viable passive-entry signal.
- **Reject?**: YES

#### **15. Falsification Observation**
- **Severity**: BLOCKER
- **Attack**: **P1 fails to beat P0 on net expectancy *under the actual queue model***. Since the queue model *prevents all fills*, P0 will have *zero fills* (matching the 400-candidate failure), and P1 will have *zero fills*. The hypothesis is falsified *before the first trade*.
- **Required Test**: Run P0/P1 with *actual queue behavior* (price-time priority) for 1 minute of data. If *no fills occur*, abandon immediately.
- **Reject?**: YES

---

### A. Three Most Dangerous Simulator Assumptions
1. **"Queue position stays behind displayed quantity"** → *Actual queues fill at best price immediately*.
2. **"No maker rebates"** → *Binance offers 0.02% rebates for passive orders; this is non-negotiable for profitability*.
3. **"250ms latency is realistic"** → *Binance L2 latency is 50–100ms; 250ms is a 3× slowdown that guarantees no fills*.

---

### B. Smallest Defensible Frozen Experiment
- **Primary lifetime**: **0.5 seconds** (not 1/3/10s; 1s is too long for crypto volatility).
- **Primary post-fill horizon**: **0.5 seconds** (not 3/10/30s; 1s is too long).
- **Smallest model/grid**: **One feature only** (L2 depth at best bid, *not* 250ms BOOK250). *No L2 features beyond best-price depth*.
- *Why*: This is the *minimum* to test if *any* L2 signal (not obsolete 250ms data) can improve fills. If it fails here, the hypothesis is dead.

---

### C. No-Rescue Rules (Absolute)
1. **No maker rebates allowed** → *Must use actual Binance fees (maker: -0.02%, taker: +0.04%)*.
2. **Queue must follow price-time priority** → *Orders at best price fill first; cancellations ahead improve position*.
3. **Only full fills count** → *Partial fills (e.g., 0.1 BTC on 1 BTC order) are excluded*.
4. **P1 must beat P0 on net expectancy *with actual queue behavior*** → *If queue behavior prevents fills, reject immediately*.
5. **No data from August 2026** → *Only Jan–Jul 2026 data; August is sealed for a reason (it’s the test set)*.

---

### D. Final Verdict
**ABANDON_FOR_CROSS_VENUE**
**Reasons**:
- The core hypothesis ("weak L2 info improves passive entry") is **falsified by the queue model itself** (it prevents all fills).
- **All critical assumptions are false** (latency, queue behavior, rebates).
- The 400-candidate failure *proves* passive entry on a single venue is impossible at 250ms.
- **Cross-venue L2 is the *only* viable path** (e.g., using Coinbase L2 to avoid Binance’s adverse selection), but EXP002 *ignores this entirely*.
- *No modification* can save this design without abandoning the venue and starting over.

*This experiment is not a research design—it’s a trap for wasted time. The hypothesis is dead on arrival.*
