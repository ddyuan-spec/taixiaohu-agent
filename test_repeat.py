#!/usr/bin/env python3
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent import TaiXiaoHuAgent

agent = TaiXiaoHuAgent()

# 模拟对话
print("=== 测试重复输入检测 ===")
print()

# 第一轮
result1 = agent.process_message("头疼")
print(f"用户: 头疼")
print(f"AI: {result1['response'][:80]}...")
print()

# 第二轮 - 这应该不是重复
result2 = agent.process_message("4")
print(f"用户: 4")
print(f"AI: {result2['response'][:80]}...")
print()

# 检查是否被判定为重复
is_repeat = agent._is_repeat_input("4")
print(f"_is_repeat_input('4') = {is_repeat}")
print(f"期望: False")
