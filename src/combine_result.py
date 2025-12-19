import os
import json
import sys

def merge_benchmark_results(parent_dir="."):
    """
    合并父目录下所有子目录中的results.json文件
    
    参数:
    parent_dir (str): 包含所有benchmark子目录的父目录路径（默认为当前目录）
    """
    combined_data = []
    
    # 遍历父目录中的所有项目
    for entry in os.listdir(parent_dir):
        # 获取完整路径
        full_path = os.path.join(parent_dir, entry)
        
        # 只处理子目录
        if os.path.isdir(full_path):
            json_path = os.path.join(full_path, "results.json")
            
            # 确保results.json存在
            if os.path.exists(json_path):
                try:
                    # 读取JSON文件
                    with open(json_path, "r") as f:
                        data = json.load(f)
                    combined_data.append(data)
                except json.JSONDecodeError:
                    print(f"⚠️  {entry}/results.json 不是有效的JSON文件，已跳过")
                except Exception as e:
                    print(f"❌ 读取 {entry} 时发生错误: {str(e)}")
            else:
                print(f"⚠️  {entry} 中未找到results.json，已跳过")

    # 写入合并后的文件
    output_path = os.path.join(parent_dir, "combined_results.json")
    with open(output_path, "w") as f:
        json.dump(combined_data, f, indent=4, ensure_ascii=False)
    
    print(f"✅ 合并完成！结果已保存至 {output_path}")

if __name__ == "__main__":
    # 使用示例（默认处理当前目录）：
    # 如果要处理其他目录，可以改为 merge_benchmark_results("/path/to/parent/dir")
    merge_benchmark_results(sys.argv[1])