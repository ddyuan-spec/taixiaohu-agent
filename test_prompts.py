"""
Prompt模块测试文件
"""

import sys
sys.path.insert(0, 'C:\\Users\\13364\\AppData\\Roaming\\TRAE SOLO CN\\ModularData\\ai-agent\\work-mode-projects\\6a16b62a291cd733e969550c\\smart_agent')

from prompts import (
    PromptManager, get_prompt_manager,
    SYSTEM_PROMPT, SAFETY_GUARD_PROMPT, SYMPTOM_COLLECTOR_PROMPT
)
from orchestrator import create_context, UserProfile


def test_prompt_manager():
    """测试Prompt管理器"""
    print("=" * 50)
    print("测试1: Prompt管理器基本功能")
    print("=" * 50)
    
    pm = get_prompt_manager()
    
    # 测试获取Prompt
    system_prompt = pm.get_prompt('system')
    assert len(system_prompt) > 0
    print(f"✓ System Prompt长度: {len(system_prompt)} 字符")
    
    # 测试列出所有Prompt
    prompt_list = pm.list_prompts()
    print(f"✓ 共有 {len(prompt_list)} 个Prompt:")
    for name in prompt_list:
        print(f"  - {name}")
    
    print("\nPrompt管理器测试通过！\n")


def test_prompt_rendering():
    """测试Prompt渲染"""
    print("=" * 50)
    print("测试2: Prompt渲染")
    print("=" * 50)
    
    pm = get_prompt_manager()
    
    # 测试变量替换
    variables = {
        'age': 58,
        'gender': '男',
        'chronic_diseases': '高血压'
    }
    
    # 使用 symptom_collector prompt 测试
    rendered = pm.render_prompt('symptom_collector', variables)
    assert '症状分析模块' in rendered
    print(f"✓ Prompt渲染成功，长度: {len(rendered)} 字符")
    
    print("\nPrompt渲染测试通过！\n")


def test_context_rendering():
    """测试上下文渲染"""
    print("=" * 50)
    print("测试3: 上下文渲染")
    print("=" * 50)
    
    pm = get_prompt_manager()
    context = create_context("user_001")
    
    # 设置画像
    context.profile.age = 58
    context.profile.gender = "男"
    context.profile.chronic_diseases = "高血压"
    context.profile.update_completeness()
    
    # 测试上下文转换
    variables = pm._context_to_dict(context)
    assert variables['age'] == 58
    assert variables['gender'] == '男'
    print(f"✓ 上下文转换成功")
    print(f"  - 年龄: {variables['age']}")
    print(f"  - 性别: {variables['gender']}")
    print(f"  - 慢病: {variables['chronic_diseases']}")
    
    print("\n上下文渲染测试通过！\n")


def test_full_prompt_building():
    """测试完整Prompt构建"""
    print("=" * 50)
    print("测试4: 完整Prompt构建")
    print("=" * 50)
    
    pm = get_prompt_manager()
    context = create_context("user_002")
    
    # 设置上下文
    context.profile.age = 65
    context.profile.gender = "女"
    context.profile.chronic_diseases = "糖尿病"
    context.profile.update_completeness()
    
    context.short_term_memory.main_symptom = "失眠"
    context.short_term_memory.duration = "2周"
    
    # 构建完整Prompt
    full_prompt = pm.build_full_prompt(
        'symptom_collector',
        '我最近总是睡不着',
        context
    )
    
    assert '泰小虎' in full_prompt
    assert '症状分析模块' in full_prompt
    assert '失眠' in full_prompt
    print(f"✓ 完整Prompt构建成功，长度: {len(full_prompt)} 字符")
    print(f"\nPrompt预览（前500字符）:\n{full_prompt[:500]}...")
    
    print("\n完整Prompt构建测试通过！\n")


def test_all_prompts():
    """测试所有Prompt是否可访问"""
    print("=" * 50)
    print("测试5: 所有Prompt可访问性")
    print("=" * 50)
    
    pm = get_prompt_manager()
    
    required_prompts = [
        'system', 'orchestrator', 'safety_guard', 'intent_router',
        'profile_extractor', 'symptom_collector', 'recommendation_engine',
        'product_consult', 'knowledge_qa', 'boundary_handler',
        'customer_service', 'disclaimer', 'profile_collect', 'welcome'
    ]
    
    for prompt_name in required_prompts:
        prompt = pm.get_prompt(prompt_name)
        assert len(prompt) > 0, f"Prompt {prompt_name} 为空"
        print(f"✓ {prompt_name}: {len(prompt)} 字符")
    
    print("\n所有Prompt可访问性测试通过！\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Prompt模块测试套件")
    print("=" * 60 + "\n")
    
    try:
        test_prompt_manager()
        test_prompt_rendering()
        test_context_rendering()
        test_full_prompt_building()
        test_all_prompts()
        
        print("=" * 60)
        print("✅ 所有Prompt测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    run_all_tests()
