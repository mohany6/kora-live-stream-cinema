import re

with open(r'C:\Users\Mohany\Desktop\football-live-score-platform\scripts\czernik_banner.js', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

matches = re.findall(r'https?://[^\s\'\"\\]+', text)
print('Static URLs found in czernik_banner:', set(matches))

# Let's inspect where '/dnn2hkn8' is used
for m in re.finditer(r'/dnn2hkn8', text):
    start = max(0, m.start() - 100)
    end = min(len(text), m.end() + 100)
    print('Context around /dnn2hkn8:\n', text[start:end])
