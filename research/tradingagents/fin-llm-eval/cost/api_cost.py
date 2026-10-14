"""Daily API cost for ~10 setups/day via OpenRouter. Prices pulled live from https://openrouter.ai/api/v1/models on 2026-10-08
(snapshot saved next to this file). Token budgets: measured on the box where available (see results.md section 7)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import json
P = {m['id']: (float(m['pricing']['prompt']) * 1e6, float(m['pricing']['completion']) * 1e6)
     for m in json.load(open((_SCANNER_ROOT + '/fin-llm-eval/cost/openrouter_models_2026-10-08.json')))['data']}
MODELS = ['anthropic/claude-sonnet-5.5', 'openai/gpt-5.6-sol', 'anthropic/claude-sonnet-4.6', 'x-ai/grok-4.7', 'anthropic/claude-opus-5.5',
          'google/gemini-3.8-flash', 'deepseek/deepseek-v3.2']
# (label, input tokens per setup, output tokens per setup incl. reasoning)
S = [('aihf 2 personas, no thinking (2 x 1.3k in / 0.15k out)', 2 * 1300, 2 * 150),
     ('aihf 2 personas, with thinking (2 x 1.3k in / 1.5k out)', 2 * 1300, 2 * 1500),
     ('TradingAgents as measured (41k in / 5.9k out, 500-tok cap)', 41100, 5900),
     ('TradingAgents realistic strong model (120k in / 25k out)', 120000, 25000)]
N, DAYS = 10, 21
print('| scenario | ' + ' | '.join(f'{m.split("/")[1]} (${P[m][0]:g}/${P[m][1]:g})' for m in MODELS) + ' |')
print('|---|' + '---|' * len(MODELS))
for lab, i, o in S:
    cells = []
    for m in MODELS:
        d = N * (i * P[m][0] + o * P[m][1]) / 1e6; cells.append(f'${d:.2f}/day · ${d*DAYS:.0f}/mo')
    print(f'| {lab} | ' + ' | '.join(cells) + ' |')
