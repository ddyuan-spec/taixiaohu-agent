import sys, os
smart_dir = r'C:\Users\13364\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a16b62a291cd733e969550c\smart_agent'
sys.path.insert(0, smart_dir)
os.chdir(smart_dir)

from agent_service import get_agent_service

service = get_agent_service()
sid = 'test_web_debug'

# Round 1
r1 = service.process_message('你好，我最近失眠', sid)
print('Round 1: intent=%s, action=%s, state=%s' % (r1['intent'], r1['next_action'], r1['state']))
print('  Response: %s' % r1['response'][:80])
ctx = service.sessions[sid]
sym = ctx.short_term_memory.main_symptom if ctx.short_term_memory else None
print('  Symptom: %s' % sym)

# Round 2
r2 = service.process_message('有什么产品推荐吗', sid)
print('\nRound 2: intent=%s, action=%s, state=%s' % (r2['intent'], r2['next_action'], r2['state']))
print('  Response: %s' % r2['response'][:200])
print('  Products: %s' % r2.get('recommended_products', []))
sym = ctx.short_term_memory.main_symptom if ctx.short_term_memory else None
print('  Symptom: %s' % sym)
print('  Intent: %s' % ctx.current_intent)
