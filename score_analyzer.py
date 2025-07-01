import pandas as pd
import numpy as np
import sys
import os
from rich.console import Console
from rich.table import Table

def print_rich_table(df):
    """
    使用 rich 库打印一个美观的富文本表格。
    """
    console = Console()
    table = Table(show_header=True, header_style="bold magenta", border_style="cyan", title_style="bold green")

    # 定义列
    # 为了美观，我们让第一列（分数）左对齐，其它数字列右对齐
    table.add_column("25分数", justify="center", style="cyan")
    table.add_column("位次", justify="right", style="green")
    table.add_column("24(新)", justify="right", style="white")
    table.add_column("24(旧)", justify="right", style="dim white")
    table.add_column("23(新)", justify="right", style="white")
    table.add_column("23(旧)", justify="right", style="dim white")

    # 添加数据行
    for _, row in df.iterrows():
        table.add_row(
            str(row['25分数']),
            str(row['位次']),
            str(row['24(新)']),
            str(row['24(旧)']),
            str(row['23(新)']),
            str(row['23(旧)'])
        )
    
    console.print(table)

def resource_path(relative_path):
    """ 获取资源的绝对路径，适用于开发环境和PyInstaller环境 """
    try:
        # PyInstaller 创建一个临时文件夹，并将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def find_equivalent_score(df, source_year, source_score, target_year):
    """
    (旧方法) 基于绝对位次查找等效分数。
    """
    try:
        source_rank_entry = df[(df['年份'] == source_year) & (df['档分'] == source_score)]
        if source_rank_entry.empty:
            return f"无记录", None, None
        source_rank = source_rank_entry['累计人数'].iloc[0]
        target_year_data = df[df['年份'] == target_year].copy()
        target_year_data['rank_diff'] = np.abs(target_year_data['累计人数'] - source_rank)
        closest_entry = target_year_data.loc[target_year_data['rank_diff'].idxmin()]
        return closest_entry['档分'], source_rank, closest_entry['累计人数']
    except Exception:
        return "错误", None, None

def find_equivalent_score_refined(df, source_year, source_score, target_year):
    """
    (新方法) 基于"竞争位置百分比" (位次 / 计划招生数) 查找等效分数。
    """
    try:
        source_admission = df[df['年份'] == source_year]['历史类计划招生人数'].iloc[0]
        target_admission = df[df['年份'] == target_year]['历史类计划招生人数'].iloc[0]
        source_rank_entry = df[(df['年份'] == source_year) & (df['档分'] == source_score)]
        if source_rank_entry.empty:
            return f"无记录", None, None, None
        source_rank = source_rank_entry['累计人数'].iloc[0]
        rank_percentage = source_rank / source_admission
        equivalent_rank = rank_percentage * target_admission
        target_year_data = df[df['年份'] == target_year].copy()
        target_year_data['rank_diff'] = np.abs(target_year_data['累计人数'] - equivalent_rank)
        closest_entry = target_year_data.loc[target_year_data['rank_diff'].idxmin()]
        return closest_entry['档分'], source_rank, closest_entry['累计人数'], equivalent_rank
    except Exception:
        return "错误", None, None, None

def analyze_score_range(df_merged, center_score, score_range):
    """
    对一个分数区间进行批量分析。
    """
    score_start = center_score + score_range
    score_end = center_score - score_range
    results_list = []
    
    for score in range(score_start, score_end - 1, -1):
        source_rank_entry = df_merged[(df_merged['年份'] == 2025) & (df_merged['档分'] == score)]
        if source_rank_entry.empty: continue
        rank_2025 = source_rank_entry['累计人数'].iloc[0]
        eq_score_2024_new, _, _, _ = find_equivalent_score_refined(df_merged, 2025, score, 2024)
        eq_score_2024_old, _, _ = find_equivalent_score(df_merged, 2025, score, 2024)
        eq_score_2023_new, _, _, _ = find_equivalent_score_refined(df_merged, 2025, score, 2023)
        eq_score_2023_old, _, _ = find_equivalent_score(df_merged, 2025, score, 2023)
        results_list.append({
            '25分数': score, '位次': rank_2025,
            '24(新)': eq_score_2024_new, '24(旧)': eq_score_2024_old,
            '23(新)': eq_score_2023_new, '23(旧)': eq_score_2023_old
        })

    if not results_list:
        print("\n[!] 在指定区间内未能计算出任何有效的等效分数。\n")
    else:
        results_df = pd.DataFrame(results_list)
        # 为了让rich正确处理列名，重命名DataFrame的列以匹配rich表格的定义
        results_df.columns = ["25分数", "位次", "24(新)", "24(旧)", "23(新)", "23(旧)"]
        print("\n" + "="*70)
        print(f"【2025年分数区间 {score_end}-{score_start} 新旧方法等效分数对比表】")
        print_rich_table(results_df)
        print("="*70 + "\n")

def get_rank(df, year, score):
    """
    根据年份和分数，查找对应的累计人数（位次）。
    """
    try:
        rank_entry = df[(df['年份'] == year) & (df['档分'] == score)]
        if rank_entry.empty:
            return None
        return rank_entry['累计人数'].iloc[0]
    except Exception:
        return None

def analyze_admission_probability(ranks_df):
    """
    模式3的主函数：分析专业录取概率。
    """
    console = Console()
    try:
        # --- 1. 加载学校录取数据 (根据用户反馈修改) ---
        path_admissions_data = resource_path('历年高校录取情况.csv')
        admissions_df = pd.read_csv(path_admissions_data, encoding='gbk')
        console.print("\n[bold cyan]专业录取数据加载成功！[/bold cyan]")

        # --- 2. 获取用户分数和位次 ---
        while True:
            user_score_str = input("\n> 请输入您2025年的高考分数 (或输入 'back' 返回): ")
            if user_score_str.lower() == 'back': return
            try:
                user_score = int(user_score_str)
                user_rank = get_rank(ranks_df, 2025, user_score)
                if user_rank is None:
                    console.print(f"[bold red]错误: 在2025年一分一段表中未找到分数 {user_score}。请重新输入。[/bold red]")
                    continue
                
                console.print(f"  您的分数 [bold green]{user_score}[/bold green] 在2025年对应的位次是 [bold green]{user_rank}[/bold green]。")
                console.print("  我们将使用此位次与2024年的录取数据进行比较。")
                break
            except ValueError:
                console.print("[bold red]输入无效，请输入一个纯数字分数。[/bold red]")

        while True: # 允许用户反复查询不同学校
            # --- 3. 选择学校 ---
            universities = admissions_df['学校名称'].unique()
            console.print("\n[bold]请选择要分析的大学：[/bold]")
            for i, name in enumerate(universities):
                console.print(f"  {i+1}: {name}")
            
            choice_str = input(f"\n> 请输入大学编号 (1-{len(universities)}) (或输入 'back' 重新输入分数): ")
            if choice_str.lower() == 'back': break
            try:
                choice = int(choice_str) - 1
                if not 0 <= choice < len(universities): raise ValueError
                selected_university = universities[choice]
            except ValueError:
                console.print("[bold red]输入无效，请输入列表中的正确编号。[/bold red]")
                continue

            # --- 4. 选择专业组 ---
            uni_df = admissions_df[admissions_df['学校名称'] == selected_university]
            prof_groups = uni_df['专业组编号'].unique()

            console.print(f"\n[bold]已选择: {selected_university}。请选择专业组：[/bold]")
            for i, name in enumerate(prof_groups):
                console.print(f"  {i+1}: 专业组 {name}")

            group_choice_str = input(f"\n> 请输入专业组编号 (1-{len(prof_groups)}): ")
            try:
                group_choice = int(group_choice_str) - 1
                if not 0 <= group_choice < len(prof_groups): raise ValueError
                selected_group = prof_groups[group_choice]
            except ValueError:
                console.print("[bold red]输入无效，请输入列表中的正确编号。[/bold red]")
                continue

            # --- 5. 分析并展示结果 ---
            group_df = uni_df[uni_df['专业组编号'] == selected_group]
            
            results = []
            for _, row in group_df.iterrows():
                min_score_2024 = row['2024最低分']
                headcount_2024 = row['2024录取人数']
                min_rank_2024 = get_rank(ranks_df, 2024, min_score_2024)

                if min_rank_2024 is None:
                    # 如果找不到位次，跳过这个专业并在结果中注明
                    results.append([row['专业名称'], min_score_2024, 'N/A', headcount_2024, '无法计算', '缺少2024年分数位次数据'])
                    continue

                rank_diff = min_rank_2024 - user_rank
                
                # --- 新的精确概率模型 ---
                # 使用S型函数（Sigmoid）来生成一个平滑的、精确的概率值。
                # 'x' 表示您的位次领先最低录取位次的幅度（以录取人数为单位）。
                if headcount_2024 > 0:
                    x = rank_diff / headcount_2024
                    prob_numeric = 1 / (1 + np.exp(-1.5 * x)) # k=1.5 使得曲线更敏感
                else: # 录取人数为0或未知的情况
                    prob_numeric = 1.0 if rank_diff > 0 else 0.0

                prob_val = f"{prob_numeric * 100:.2f}%"

                # 根据精确概率反向定义定性描述
                if prob_numeric > 0.95:   prob_level = "极高"
                elif prob_numeric > 0.80:  prob_level = "较高"
                elif prob_numeric > 0.60:  prob_level = "有希望"
                elif prob_numeric > 0.40:  prob_level = "边缘"
                elif prob_numeric > 0.15:  prob_level = "较低"
                else:                     prob_level = "极低"
                
                results.append([row['专业名称'], min_score_2024, min_rank_2024, headcount_2024, prob_level, prob_val])
            
            # 使用 rich.Table 显示结果
            table = Table(title=f"[bold green]{selected_university} - 专业组 {selected_group} 录取概率分析[/bold green]")
            table.add_column("专业名称", style="cyan")
            table.add_column("24年最低分", justify="right", style="magenta")
            table.add_column("24年最低位次", justify="right", style="green")
            table.add_column("24年录取人数", justify="right", style="blue")
            table.add_column("录取可能", justify="center", style="yellow")
            table.add_column("参考概率", justify="center", style="bold yellow")

            for res in results:
                table.add_row(str(res[0]), str(res[1]), str(res[2]), str(res[3]), str(res[4]), str(res[5]))
            
            console.print(table)


    except FileNotFoundError:
        console.print(f"[bold red]错误: 未找到学校录取数据文件 '历年高校录取情况.csv'。[/bold red]")
        console.print("请确保该文件存在于程序目录下。")
    except Exception as e:
        console.print(f"[bold red]处理过程中发生未知错误: {e}[/bold red]")

def main():
    """
    主函数，提供模式选择并分发任务。
    """
    try:
        # --- 数据加载 ---
        print("正在加载数据，请稍候...")
        path_ranks = resource_path('3年高考位次.csv')
        path_admissions = resource_path('3年高考人数变化与高校计划招生变化.csv')
        
        ranks_df = pd.read_csv(path_ranks, encoding='utf-8')
        ranks_df['档分'] = ranks_df['档分'].replace('100以下', '99').astype(int)
        admissions_df = pd.read_csv(path_admissions, encoding='gbk')
        admissions_df.columns = ['年份', '高考总人数', '历史类计划招生人数', '物理类计划招生人数']
        df_admissions_cleaned = admissions_df.copy()
        df_admissions_cleaned['高考总人数'] = df_admissions_cleaned['高考总人数'].str.replace('万', '').astype(float) * 10000
        df_merged = pd.merge(ranks_df, df_admissions_cleaned, on='年份')
        print("数据加载完毕！\n")
        
        # --- 模式选择 ---
        while True:
            mode = input("请选择分析模式:\n  1: 单点分数查询\n  2: 区间分数分析\n  3: 录取概率预测\n  (输入 'exit' 或 '退出' 来结束)\n> ")
            if mode.lower() in ['exit', '退出']:
                print("感谢使用，程序已退出。")
                break
            
            if mode == '1':
                # --- 单点查询模式 ---
                while True:
                    user_input = input("\n[单点模式] 请输入2025年分数 (或输入 'back' 返回主菜单): ")
                    if user_input.lower() == 'back': break
                    try:
                        score_to_check = int(user_input)
                        # 这里需要一个单点分析函数，我们复用V7的analyze_score
                        # 为了简洁，直接在这里实现
                        source_rank_entry = df_merged[(df_merged['年份'] == 2025) & (df_merged['档分'] == score_to_check)]
                        if source_rank_entry.empty:
                            print(f"\n[!] 在2025年的数据中未找到分数为 {score_to_check} 的记录。\n")
                            continue
                        rank_2025 = source_rank_entry['累计人数'].iloc[0]
                        eq_score_2024_new, _, _, _ = find_equivalent_score_refined(df_merged, 2025, score_to_check, 2024)
                        eq_score_2024_old, _, _ = find_equivalent_score(df_merged, 2025, score_to_check, 2024)
                        eq_score_2023_new, _, _, _ = find_equivalent_score_refined(df_merged, 2025, score_to_check, 2023)
                        eq_score_2023_old, _, _ = find_equivalent_score(df_merged, 2025, score_to_check, 2023)
                        results_df = pd.DataFrame([{
                            '25分数': score_to_check, '位次': rank_2025,
                            '24(新)': eq_score_2024_new, '24(旧)': eq_score_2024_old,
                            '23(新)': eq_score_2023_new, '23(旧)': eq_score_2023_old
                        }])
                        # 同样，重命名以匹配
                        results_df.columns = ["25分数", "位次", "24(新)", "24(旧)", "23(新)", "23(旧)"]
                        print("\n" + "="*70)
                        print(f"【2025年分数 {score_to_check} 的等效分数报告】")
                        print_rich_table(results_df)
                        print("="*70 + "\n")
                    except ValueError:
                        print("\n[!] 输入无效，请输入一个纯数字分数。\n")

            elif mode == '2':
                # --- 区间分析模式 ---
                try:
                    center_score_str = input("\n[区间模式] 请输入中心分数 (例如 538): ")
                    center_score = int(center_score_str)
                    range_str = input(f"[区间模式] 请输入以 {center_score} 为中心的范围 (例如 5): ")
                    score_range = int(range_str)
                    analyze_score_range(df_merged, center_score, score_range)
                except ValueError:
                    print("\n[!] 输入无效，请输入纯数字。\n")
            
            elif mode == '3':
                # --- 录取概率预测模式 ---
                analyze_admission_probability(df_merged)

            else:
                print("\n[!] 无效的模式选择，请输入 1, 2 或 3。\n")

    except FileNotFoundError as e:
        print(f"错误: 关键数据文件未找到 - {e}。")
    except KeyboardInterrupt:
        print("\n\n程序被手动终止。感谢使用！")
    except Exception as e:
        print(f"处理过程中发生未知错误: {e}")

if __name__ == '__main__':
    main() 