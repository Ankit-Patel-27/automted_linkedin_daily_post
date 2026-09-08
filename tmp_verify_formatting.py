import sys
import types

m = types.ModuleType('groq')
class DummyGroq:
    pass
m.Groq = DummyGroq
sys.modules['groq'] = m

import post_generator

raw = '{"post_text": "This is a clean caption with braces {and quotes}. { \\\"post_text\\\": \\\"duplicate\\\" }"}'
out = post_generator.sanitize_post_text(raw, '#DataEngineering #DataPlatform')
print(out)
print('HAS_BRACES', '{' in out or '}' in out)
print('HAS_POST_TEXT', 'post_text' in out)
