import os
from dotenv import load_dotenv

load_dotenv()

from agent_state import MutationState
from mutation_graph import build_mutation_graph

async def main():
    print("🚀 初始化 SafeAMP-Dual LangGraph 多智能体引擎...")
    graph = build_mutation_graph()
    
    initial_state = {
        "original_sequence": "GIGAVLKVLTTGLPALISWIKRKRQQ",
        "peptide_name": "Melittin",
        "current_candidate": "GIGAVLKVLTTGLPALISWIKRKRQQ",
        "step_count": 0
    }
    
    print("\n🔬 [Task Started] 原始序列: GIGAVLKVLTTGLPALISWIKRKRQQ (Melittin)")
    print("📡 正在调用 DeepSeek-V3 并流转 Agent...")
    
    final_state = await graph.ainvoke(initial_state)
    
    print("\n✅ [Task Finished]")
    print(f"📚 研究员文献上下文: {final_state.get('literature_context')[:100]}...")
    print(f"🧬 最终优选突变序列: {final_state.get('current_candidate')}")
    print(f"📊 计算指标: {final_state.get('metrics')}")
    print(f"⚖️ 审查员最终判决:\n{final_state.get('final_report', final_state.get('feedback'))}")
    print(f"🔄 总计迭代循环次数: {final_state.get('step_count')}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
