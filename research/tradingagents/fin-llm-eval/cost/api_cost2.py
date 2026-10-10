"""Per-setup and per-scan (~110 tickers) OpenRouter cost. Prices: https://openrouter.ai/api/v1/models snapshot 2026-10-08."""
import json
P = {m['id']: (float(m['pricing']['prompt']) * 1e6, float(m['pricing']['completion']) * 1e6)
     for m in json.load(open('openrouter_models_2026-10-08.json'))['data']}
M = [('Claude Sonnet 5.5', 'anthropic/claude-sonnet-5.5'), ('Claude Sonnet 4.6', 'anthropic/claude-sonnet-4.6'), ('Claude Opus 5.5', 'anthropic/claude-opus-5.5'),
     ('GPT-5.6 Sol', 'openai/gpt-5.6-sol'), ('GPT-5.5', 'openai/gpt-5.5'), ('Grok 4.7', 'x-ai/grok-4.7'), ('Grok 4.3', 'x-ai/grok-4.3'),
     ('Gemini 3.8 Flash', 'google/gemini-3.8-flash'), ('DeepSeek V3.2', 'deepseek/deepseek-v3.2')]
S = [('aihf 2 personas (thinking, 2x1.3k in / 1.5k out)', 2600, 3000), ('TA measured (41.1k/5.9k)', 41100, 5900), ('TA strong realistic (120k/25k)', 120000, 25000)]
L = ['| model ($ in/out per M) | ' + ' | '.join(f'{s[0]}: per setup · per 110-ticker scan' for s in S) + ' |', '|---|' + '---|' * len(S)]
for n, m in M:
    c = [(i * P[m][0] + o * P[m][1]) / 1e6 for _, i, o in S]
    L.append(f'| {n} (${P[m][0]:g}/${P[m][1]:g}) | ' + ' | '.join(f'${x:.3f} · ${110*x:.2f}' for x in c) + ' |')
print('\n'.join(L))
