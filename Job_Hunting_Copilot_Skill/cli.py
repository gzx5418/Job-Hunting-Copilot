# -*- coding: utf-8 -*-
"""
求职智能体 - 交互式入口
===================================
  运行方式: python cli.py
  提供菜单式交互界面，供评审直接体验各 Pipeline 的闭环能力。
"""

import os
import sys

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AGENT_DIR)

from agent import AutoClawAgent


def print_header():
    print("\n" + "=" * 56)
    print("  AutoClaw Agent -- 求职智能体  |  交互式入口")
    print("  框架: AutoClaw  |  LLM: GLM-4-Plus  |  路径B: 原生Skill模式")
    print("=" * 56)


def print_menu():
    print("\n" + "-" * 56)
    print("  [1] 生成简历 -- 输入经历草稿 + 目标岗位 + JD")
    print("  [2] 搜索实习 -- 输入岗位关键词 + 城市")
    print("  [3] 文献调研 -- 输入研究主题")
    print("  [4] 证书识别 -- 输入证书照片路径，提取经历")
    print("  [5] 一站式全流程 -- 简历 + 岗位聚合")
    print("  [6] 多岗位简历对比 -- 同时生成多个岗位的定制简历")
    print("  [7] 模拟面试 -- 输入目标岗位，生成面试题并评估")
    print("  [8] 简历+面试一站式 -- 生成简历后自动进入面试练习")
    print("  [0] 退出")
    print("-" * 56)


def run_resume(agent):
    print("\n  [场景] 个性化简历生成（JD 定制版）")
    target_role = input("  目标岗位: ").strip()
    if not target_role:
        print("  [错误] 请输入目标岗位")
        return

    print("  请粘贴你的经历草稿（输入空行结束）:")
    lines = []
    while True:
        line = input("  > ")
        if not line:
            break
        lines.append(line)
    raw_text = "\n".join(lines)
    if not raw_text.strip():
        print("  [错误] 请输入经历草稿")
        return

    print("  请粘贴目标岗位 JD（输入空行结束）:")
    jd_lines = []
    while True:
        line = input("  > ")
        if not line:
            break
        jd_lines.append(line)
    jd_text = "\n".join(jd_lines)
    if not jd_text.strip():
        print("  [错误] 请输入岗位 JD")
        return

    result = agent.execute(
        user_input=f"帮我生成一份针对{target_role}的简历",
        target_role=target_role, raw_text=raw_text, jd_text=jd_text
    )
    _print_result(result)


def run_internship(agent):
    print("\n  [场景] 行业实习职位自动聚合")
    keyword = input("  岗位关键词: ").strip()
    if not keyword:
        print("  [错误] 请输入岗位关键词")
        return
    city = input("  目标城市: ").strip()
    if not city:
        print("  [错误] 请输入目标城市")
        return

    result = agent.execute(
        user_input=f"帮我找{city}的{keyword}",
        keyword=keyword, city=city,
        platforms=["zhipin", "shixiseng", "nowcoder"]
    )
    _print_result(result)


def run_literature(agent):
    print("\n  [场景] 全自动文献调研")
    topic = input("  研究主题: ").strip()
    if not topic:
        print("  [错误] 请输入研究主题")
        return

    result = agent.execute(
        user_input=f"帮我调研关于「{topic}」的学术文献",
        research_topic=topic
    )
    _print_result(result)


def run_ocr(agent):
    print("\n  [场景] 证书照片识别与经历提取")
    image_path = input("  证书照片路径: ").strip()
    if not image_path:
        print("  [错误] 请提供证书照片路径")
        return
    result = agent.execute(
        user_input="帮我从证书照片中提取经历信息",
        image_paths=[image_path]
    )
    _print_result(result)


def run_full(agent):
    print("\n  [场景] 一站式全流程")
    target_role = input("  目标岗位: ").strip()
    if not target_role:
        print("  [错误] 请输入目标岗位")
        return
    keyword = input("  实习关键词: ").strip()
    if not keyword:
        print("  [错误] 请输入实习关键词")
        return
    city = input("  目标城市: ").strip()
    if not city:
        print("  [错误] 请输入目标城市")
        return

    print("  请粘贴你的经历草稿（输入空行结束）:")
    lines = []
    while True:
        line = input("  > ")
        if not line:
            break
        lines.append(line)
    raw_text = "\n".join(lines)
    if not raw_text.strip():
        print("  [错误] 请输入经历草稿")
        return

    print("  请粘贴目标岗位 JD（输入空行结束）:")
    jd_lines = []
    while True:
        line = input("  > ")
        if not line:
            break
        jd_lines.append(line)
    jd_text = "\n".join(jd_lines)
    if not jd_text.strip():
        print("  [错误] 请输入岗位 JD")
        return

    result = agent.execute(
        user_input="一站式帮我找工作",
        target_role=target_role,
        keyword=keyword, city=city,
        platforms=["zhipin", "shixiseng"],
        raw_text=raw_text,
        jd_text=jd_text
    )
    _print_result(result)


def run_multi_resume(agent):
    print("\n  [场景] 多岗位简历对比生成")
    roles_input = input("  目标岗位（逗号分隔）: ").strip()
    if not roles_input:
        print("  [错误] 请输入目标岗位")
        return
    roles = [r.strip() for r in roles_input.split(",")]

    print("  请粘贴你的经历草稿（输入空行结束）:")
    lines = []
    while True:
        line = input("  > ")
        if not line:
            break
        lines.append(line)
    raw_text = "\n".join(lines)
    if not raw_text.strip():
        print("  [错误] 请输入经历草稿")
        return

    print("  请粘贴目标岗位 JD（输入空行结束）:")
    jd_lines = []
    while True:
        line = input("  > ")
        if not line:
            break
        jd_lines.append(line)
    jd_text = "\n".join(jd_lines)
    if not jd_text.strip():
        print("  [错误] 请输入岗位 JD")
        return

    for role in roles:
        print(f"\n  > 正在生成 [{role}] 定制简历...")
        result = agent.execute(
            user_input=f"帮我生成一份针对{role}的简历",
            target_role=role, raw_text=raw_text, jd_text=jd_text
        )
        _print_result(result)
    print(f"\n  [完成] 共生成 {len(roles)} 份定制简历，请查看 output/ 目录")


def run_interview(agent):
    print("\n  [场景] 模拟面试练习")
    target_role = input("  目标岗位: ").strip()
    if not target_role:
        print("  [错误] 请输入目标岗位")
        return
    interview_type = input("  面试类型 (behavioral/technical/comprehensive): ").strip()
    if not interview_type:
        interview_type = "comprehensive"
    try:
        num_questions = int(input("  题目数量: ").strip() or "5")
    except ValueError:
        print("  [警告] 无效数字，使用默认值 5")
        num_questions = 5

    print(f"\n  > 正在为 [{target_role}] 岗位生成面试题...")
    q_result = agent.execute(
        user_input=f"帮我准备{target_role}的面试",
        target_role=target_role,
        interview_type=interview_type,
        num_questions=num_questions
    )

    if q_result.get("status") != "success":
        _print_result(q_result)
        return

    questions = q_result.get("data", {}).get("questions", [])
    if not questions:
        print("  [错误] 未生成面试题")
        return

    print(f"\n  生成了 {len(questions)} 道面试题，请逐一回答：\n")

    interview_results = []
    for q in questions:
        print(f"  Q{q['id']}: {q['question']}")
        print(f"    [类型: {q['type']} | 难度: {q['difficulty']} | 考察: {q['dimension']}]")
        answer = input("  你的回答: ").strip()
        if not answer:
            print("  [跳过] 未输入回答")
            continue

        try:
            eval_result = agent.run_skill(
                "interview_scorer",
                question=q["question"],
                answer=answer,
                reference_points=q.get("reference_points", []),
                target_role=target_role
            )
            if eval_result.get("status") == "success":
                score_data = eval_result["data"]
                print(f"    → 得分: {score_data['score']}/100 (等级 {score_data['tier']})")
                for fb in score_data.get("feedback", [])[:2]:
                    print(f"    → {fb}")
                interview_results.append({
                    "id": q["id"],
                    "question": q["question"],
                    "answer": answer,
                    "score_data": score_data
                })
        except Exception as e:
            print(f"    [评估异常] {e}")

    if interview_results:
        print(f"\n  > 正在生成面试练习报告...")
        report_result = agent.execute(
            user_input="生成面试练习报告",
            target_role=target_role,
            interview_results=interview_results
        )
        _print_result(report_result)
    else:
        print("\n  [完成] 未收集到有效回答，跳过报告生成")


def run_resume_interview(agent):
    print("\n  [场景] 简历 + 面试一站式")
    target_role = input("  目标岗位: ").strip()
    if not target_role:
        print("  [错误] 请输入目标岗位")
        return

    print("  请粘贴你的经历草稿（输入空行结束）:")
    lines = []
    while True:
        line = input("  > ")
        if not line:
            break
        lines.append(line)
    raw_text = "\n".join(lines)
    if not raw_text.strip():
        print("  [错误] 请输入经历草稿")
        return

    print("  请粘贴目标岗位 JD（输入空行结束）:")
    jd_lines = []
    while True:
        line = input("  > ")
        if not line:
            break
        jd_lines.append(line)
    jd_text = "\n".join(jd_lines)
    if not jd_text.strip():
        print("  [错误] 请输入岗位 JD")
        return

    result = agent.execute(
        user_input=f"简历面试一站式准备{target_role}",
        target_role=target_role,
        raw_text=raw_text,
        jd_text=jd_text
    )
    _print_result(result)


def _print_result(result):
    if not result:
        print("  [错误] 无返回结果")
        return
    status = result.get("status", "unknown")
    if status == "success":
        print(f"  [OK] 执行成功")
        data = result.get("data", {})
        file_path = data.get("file_path", result.get("output", ""))
        if file_path:
            print(f"  [FILE] 输出文件: {file_path}")
        else:
            print(f"  [OUTPUT] {result.get('output', '无文件输出')}")
    elif status == "fallback":
        print(f"  [跳过] {result.get('message', '未匹配Pipeline')}")
    else:
        print(f"  [错误] {result.get('message', '未知错误')}")


def main():
    print_header()
    config_path = os.path.join(AGENT_DIR, "agent_config.json")
    agent = AutoClawAgent(config_path=config_path)

    handlers = {
        "1": run_resume,
        "2": run_internship,
        "3": run_literature,
        "4": run_ocr,
        "5": run_full,
        "6": run_multi_resume,
        "7": run_interview,
        "8": run_resume_interview,
    }

    while True:
        print_menu()
        choice = input("\n> 请选择: ").strip()
        if choice == "0":
            print("\n  再见！")
            break
        handler = handlers.get(choice)
        if handler:
            try:
                handler(agent)
            except Exception as e:
                print(f"  [异常] {e}")
        else:
            print("  无效选择，请重新输入")


if __name__ == "__main__":
    main()
