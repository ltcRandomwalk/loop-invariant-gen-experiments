import os
import argparse

def main():
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description='查找目录下所有.c文件并输出相对路径')
    parser.add_argument('-d', '--directory', default='.', help='要搜索的目录（默认为当前目录）')
    parser.add_argument('-o', '--output', default='c_files.txt', help='输出文件路径（默认为c_files.txt）')
    args = parser.parse_args()

    # 获取目标目录和输出路径的绝对路径
    base_dir = os.path.abspath(args.directory)
    output_path = os.path.abspath(args.output)

    # 确保目标目录存在
    if not os.path.isdir(base_dir):
        print(f"错误：目录不存在 '{base_dir}'")
        return

    # 收集所有.c文件的相对路径
    c_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.c'):
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, start=base_dir)
                c_files.append(rel_path)

    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # 写入输出文件
    try:
        with open(output_path, 'w') as f:
            f.write('\n'.join(c_files))
        print(f"找到 {len(c_files)} 个.c文件，结果已保存至 '{output_path}'")
    except IOError as e:
        print(f"写入文件时出错：{e}")

if __name__ == '__main__':
    main()