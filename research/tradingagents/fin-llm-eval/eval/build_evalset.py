"""Builds eval set with programmatically computed ground truth."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import json
T = dict(rev=(4820,5615), cogs=(2940,3312), opex=(1105,1286), ebit=(775,1017), intexp=(62,58),
         pretax=(713,959), tax=(150,201), ni=(563,758), shares=(412,405), cfo=(910,1148), capex=(285,342),
         debt=(1450,1320), equity=(2900,3410), cash=(640,815), da=(190,205))
TABLE = """Northwind Devices Inc. — selected financial data (USD millions, except per-share data)
| Line item                         | FY2024 | FY2025 |
|-----------------------------------|--------|--------|
| Revenue                           | 4,820  | 5,615  |
| Cost of goods sold                | 2,940  | 3,312  |
| Operating expenses (SG&A + R&D)   | 1,105  | 1,286  |
| Operating income (EBIT)           | 775    | 1,017  |
| Depreciation & amortization       | 190    | 205    |
| Interest expense                  | 62     | 58     |
| Pre-tax income                    | 713    | 959    |
| Income tax expense                | 150    | 201    |
| Net income                        | 563    | 758    |
| Diluted weighted avg. shares (m)  | 412    | 405    |
| Cash flow from operations         | 910    | 1,148  |
| Capital expenditures              | 285    | 342    |
| Total debt                        | 1,450  | 1,320  |
| Cash and equivalents              | 640    | 815    |
| Total shareholders' equity        | 2,900  | 3,410  |
| Current assets (FY2025 only)      |   —    | 2,180  |
| Inventory (FY2025 only)           |   —    | 610    |
| Current liabilities (FY2025 only) |   —    | 1,240  |
"""
r=lambda k,i=1:T[k][i]
eps25=r('ni')/r('shares'); eps24=T['ni'][0]/T['shares'][0]
fcf=r('cfo')-r('capex'); mcap=46.80*r('shares')
gm24=(T['rev'][0]-T['cogs'][0])/T['rev'][0]*100; gm25=(r('rev')-r('cogs'))/r('rev')*100
items=[
 ("rev_growth","What was the year-over-year revenue growth from FY2024 to FY2025, in percent?",(r('rev')/T['rev'][0]-1)*100,"pct"),
 ("gross_margin","What was the gross margin in FY2025, in percent?",gm25,"pct"),
 ("op_margin","What was the operating margin in FY2025, in percent?",r('ebit')/r('rev')*100,"pct"),
 ("eps","What was diluted EPS in FY2025, in USD per share?",eps25,"num"),
 ("eps_growth","By what percent did diluted EPS grow from FY2024 to FY2025?",(eps25/eps24-1)*100,"pct"),
 ("fcf","What was free cash flow (CFO minus capex) in FY2025, in USD millions?",fcf,"num"),
 ("fcf_margin","What was the free cash flow margin (FCF / revenue) in FY2025, in percent?",fcf/r('rev')*100,"pct"),
 ("de_ratio","What was the debt-to-equity ratio (total debt / total equity) at FY2025? Give a decimal ratio.",r('debt')/r('equity'),"num"),
 ("netdebt_ebitda","What was net debt / EBITDA in FY2025, where net debt = total debt - cash and EBITDA = EBIT + D&A? Give a decimal ratio.",(r('debt')-r('cash'))/(r('ebit')+r('da')),"num"),
 ("tax_rate","What was the effective tax rate in FY2025, in percent?",r('tax')/r('pretax')*100,"pct"),
 ("int_cov","What was interest coverage (EBIT / interest expense) in FY2025? Give the multiple as a number.",r('ebit')/r('intexp'),"num"),
 ("quick_ratio","What was the quick ratio ((current assets - inventory) / current liabilities) at FY2025?",(2180-610)/1240,"num"),
 ("roe_avg","What was FY2025 return on equity using AVERAGE shareholders' equity of FY2024 and FY2025, in percent?",r('ni')/((T['equity'][0]+r('equity'))/2)*100,"pct"),
 ("gm_pp","By how many percentage points did gross margin change from FY2024 to FY2025? (positive = expansion)",gm25-gm24,"pp"),
 ("pe","If the share price is $46.80, what is the P/E ratio based on FY2025 diluted EPS?",46.80/eps25,"num"),
 ("fcf_yield","If the share price is $46.80, what is the FY2025 free-cash-flow yield (FCF / market cap, market cap = price x diluted shares), in percent?",fcf/mcap*100,"pct"),
]
evals=[]
for qid,q,a,kind in items:
    evals.append(dict(id=qid,type="table",turns=[q],answer=round(a,4),kind=kind))
evals.append(dict(id="cagr",type="standalone",turns=["A company's revenue grew from $1,200M in 2021 to $2,050M in 2025 (4 years). What was the compound annual growth rate (CAGR), in percent?"],answer=round(((2050/1200)**0.25-1)*100,4),kind="pct",table=False))
evals.append(dict(id="down_up",type="standalone",turns=["A stock bought at $80.00 falls 25% and then rises 25% from that lower level. What is the final price in USD?"],answer=75.0,kind="num",table=False))
# ConvFinQA-style multi-turn (scored per turn)
evals.append(dict(id="conv",type="multiturn",turns=["What was the change in cash flow from operations from FY2024 to FY2025, in USD millions?",
   "And what is that change as a percentage of the FY2024 value?"],answers=[238.0,round(238/910*100,4)],kind="multi"))
# qualitative
RISK = """Excerpt from Item 1A (Risk Factors), Northwind Devices Inc.:
"Approximately 38% of our FY2025 revenue came from two customers, and the loss of either could materially reduce our revenue. Substantially all of our chips are fabricated by a single foundry in Taiwan; geopolitical tensions or natural disasters could disrupt supply. Our $1.32 billion of debt includes a $600 million term loan with a floating rate tied to SOFR, so higher interest rates increase our interest expense. We are subject to export controls that restrict sales of certain products to customers in China, which represented 14% of FY2025 revenue. We are a defendant in a patent-infringement lawsuit seeking $250 million in damages; an adverse outcome could harm our results.\""""
evals.append(dict(id="risk_summary",type="qual",turns=[RISK+"\n\nSummarize the three most material risks for an equity investor in exactly three bullet points, each under 25 words."],kind="qual"))
evals.append(dict(id="leverage_view",type="qual",turns=["Using the table, is Northwind's balance-sheet leverage a concern for a long-term investor? Answer in 2-3 sentences and cite at least two specific ratios with their values."],kind="qual",table=True))
json.dump(dict(table=TABLE,risk=RISK,items=evals),open((_SCANNER_ROOT + "/fin-llm-eval/eval/evalset.json"),"w"),indent=1,ensure_ascii=False)
for e in evals: print(e['id'], e.get('answer', e.get('answers','')))
print(len(evals))
