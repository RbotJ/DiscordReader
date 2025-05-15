"""
Test fixtures for trade setup messages.

This module contains sample messages for testing the parser functionality.
"""

# Simple message with a single ticker
SIMPLE_MESSAGE = """A+ Trade Setups — Wed May 14

1) SPY
❌ Rejection Near 588.87 (586.30, 584.50, 581.70) 
🔻 Breakdown Below 584.50 (581.70, 578.90, 576.20)
🔼 Breakout Above 588.87 (591.30, 593.80, 596.40) 
🔄 Bounce From 581.70 (584.50, 586.30, 588.00)
⚠️ Bias bullish while holding above 584.50, scalp watch on rejection at 588.87
"""

# Message with multiple tickers
MULTI_TICKER_MESSAGE = """A+ Trade Setups — Wed May 14

1) SPY
❌ Rejection Near 588.87 (586.30, 584.50, 581.70) 
🔻 Breakdown Below 584.50 (581.70, 578.90, 576.20)
🔼 Breakout Above 588.87 (591.30, 593.80, 596.40) 
🔄 Bounce From 581.70 (584.50, 586.30, 588.00)
⚠️ Bias bullish while holding above 584.50, scalp watch on rejection at 588.87

2) TSLA
❌ Rejection Near 344.93 (342.10, 338.90, 335.50) 
🔻 Breakdown Below 342.10 (338.90, 335.50, 332.30)
🔼 Breakout Above 344.93 (348.10, 351.80, 355.50) 
🔄 Bounce From 338.90 (342.10, 344.10, 346.20)
⚠️ Bias bullish above 342.10 — scalp watch on rejection at 344.93

3) NVDA
❌ Rejection Near 134.24 (132.10, 129.80, 127.50) 
🔻 Breakdown Below 132.10 (129.80, 127.50, 124.90)
🔼 Breakout Above 134.24 (137.30, 140.50, 143.80) 
🔄 Bounce From 129.80 (132.10, 134.00, 135.50)
⚠️ Bias bullish above 132.10 — scalp watch on rejection at 134.24
@everyone
"""

# Message with alternative format and aggressiveness indicators
ALTERNATE_FORMAT_MESSAGE = """A+ Trade Setups — Tue May 13

1) SPY
🔼 Aggressive Long Over 583.75 🔼 585.80, 587.90, 589.50 
🔼 Conservative Long Over 585.80 🔼 587.90, 589.50, 592.00
🔻 Aggressive Short Below 579.60 🔻 577.80, 576.30, 573.80 
🔻 Conservative Short Below 577.80 🔻 576.30, 573.80, 571.00 
❌ Rejection Short Near 583.75 🔻 581.50, 579.60, 577.80
🌀 Bounce Zone 571.00-573.00
⚠️Bullish momentum above 583.75 — bias flips bearish only if 579.60 breaks
"""

# Message with complex bias descriptions
COMPLEX_BIAS_MESSAGE = """A+ Trade Setups

1) SPY 
❌ Rejection Levels 564.10, 562.85, 562.25 
🔻 Breakdown: Agg 561.70 🔻 560.00, 558.50, 555.80 
🔻 Con 560.00 🔻 558.50, 555.80, 553.20 
🔼 Breakout: Agg 564.10 🔼 566.50, 568.80, 571.00 
🔼 Con 566.50 🔼 568.80, 571.00, 573.50 
🔄 Bounce: 560.00, 558.50, 555.80
⚠️ Bearish bias below 562.25; flips bullish on 564.10 reclaim
"""

# Message with different header format and no explicit date
NO_DATE_MESSAGE = """A+ Trade Setups

SPY
🔼 Breakout Entries Aggressive Above 568.12 🔼 569.80, 571.90, 574.40 
🔼 Breakout Entry Conservative Above 570.75 🔼 572.90, 575.30, 577.60
🔻 Breakdown Entry Aggressive Below 565.22 🔻 563.00, 560.80, 558.30 
🔻 Breakdown Entry  Conservative Below 562.38 🔻 560.10, 557.50, 555.20
🔁 Rejection Short Reject Near 568.12 🔻 565.70, 563.40, 561.10
📈 Bounce Zone Near 562.38 🔼 564.70, 566.90, 569.20
⚠️ Bullish over 568.12 — bears gain control under 562.38 — Watch 570.75 breakout — it must have higher momentum
"""

# Message with alternative ticker section format
DIVIDER_TICKER_MESSAGE = """A+ Trade Setups - Mon May 12

🔼 Breakout Entry Aggressive Above 582.54 🔼 586.25, 590.00, 595.50 
🔼 Breakout Entry Conservative Above 590.00 🔼 595.50, 602.00, 610.00
🔻 Breakdown Entry Aggressive Below 580.89 🔻 577.00, 572.50, 565.00 
🔻 Breakdown Entry Conservative Below 572.50 🔻 565.00, 558.00, 550.00
❌ Rejection Short Near 586.25 🔻 582.00, 577.00, 572.50
⚠️ Bias bullish above 580.89 but getting overheated -- watch rejection levels
—————————————————
TSLA 🔼 Breakout Entry Aggressive Above 323.47 🔼 328.00, 332.50, 336.90 
🔼 Breakout Entry Conservative Above 336.90 🔼 345.00, 352.20, 360.00
🔻 Breakdown Entry Aggressive Below 317.50 🔻 312.20, 307.50, 302.00 
🔻 Breakdown Entry Conservative Below 302.00 🔻 295.80, 290.00, 284.00
❌ Rejection Short Zone Near 336.90 🔻 328.00, 323.50, 318.00
⚠️ Bullish bias above 323.47 — scalp to 336.90 if early momentum continues
"""

# Malformed message with missing elements
MALFORMED_MESSAGE = """A+ Trade Setups

1) SPY
❌ Rejection Near x.xx
🔻 Breakdown Below ABC
⚠️ Bias bullish
"""

# Empty message
EMPTY_MESSAGE = """"""

# All sample messages for testing
ALL_SAMPLE_MESSAGES = [
    SIMPLE_MESSAGE,
    MULTI_TICKER_MESSAGE,
    ALTERNATE_FORMAT_MESSAGE,
    COMPLEX_BIAS_MESSAGE,
    NO_DATE_MESSAGE,
    DIVIDER_TICKER_MESSAGE,
    MALFORMED_MESSAGE,
    EMPTY_MESSAGE
]