import yaml
import os
import re
import shutil
import time
from aistudio_sdk.snapshot_download import snapshot_download

COMMON_ARGS = {
    "revision": "master",
}

def clean_name(name):
    """清理名称，移除空格和路径符号"""
    # 移除空格、斜杠、点等特殊字符，只保留字母数字和下划线
    return re.sub(r'[^\w]', '_', name)

def check_model_path_exists(model_config):
    """检查MODEL_NAME_OR_PATH指定的路径是否存在"""
    model_path = model_config.get('MODEL_NAME_OR_PATH', '')
    if not model_path:
        print(f"警告: MODEL_NAME_OR_PATH 未定义")
        return False
    
    # 检查路径是否存在
    if os.path.exists(model_path):
        print(f"模型路径存在: {model_path}")
        return True
    else:
        print(f"警告: 模型路径不存在: {model_path}")
        return False

def download_model(repo_id: str, max_retries: int = 3, BASE_DIR: str = "./models"):
    local_dir = os.path.join(BASE_DIR, repo_id)
    os.makedirs(local_dir, exist_ok=True)

    for attempt in range(1, max_retries + 1):
        try:
            res = snapshot_download(repo_id=repo_id, local_dir=local_dir, **COMMON_ARGS)
            return True
        except Exception as e:
            if attempt < max_retries:
                time.sleep(5)
            else:
                print(f" Skip: {repo_id} after {max_retries} retries")
                return False


def replace_variables_in_file(file_path, model_config):
    """在文件中替换变量值"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 遍历模型配置中的所有键值对（除了name）
    for key, value in model_config.items():
        if key == 'name':
            continue
            
        # 处理特殊格式的值
        if isinstance(value, list) and all(isinstance(item, list) for item in value):
            # 二维数组格式
            formatted_value = repr(value)
        elif isinstance(value, list):
            # 一维数组格式
            formatted_value = repr(value)
        elif isinstance(value, str):
            # 字符串格式
            formatted_value = f'"{value}"'
        else:
            # 数字或其他类型
            formatted_value = str(value)
        
        # 在文件中查找并替换变量
        pattern = rf'{key}\s*=\s*[^\n]+'
        replacement = f'{key} = {formatted_value}'
        
        # 使用正则表达式替换
        content = re.sub(pattern, replacement, content)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    # 读取YAML文件
    with open('./scripts/regression/ci_model_unittest_config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 获取模型列表
    model_list = config.get('model_ci_test_config_list', [])
    
    # 模板文件列表
    template_files = [
        './scripts/regression/test_dpo.py',
        './scripts/regression/test_sft.py', 
        './scripts/regression/test_pt.py'
    ]
    
    # 遍历模型列表
    for model_config in model_list:
        name = model_config.get('name', '')
        
        # 跳过name为"tiny-random-qwen3"的模型
        if name == "tiny-random-qwen3":
            print(f"跳过默认模型: {name}")
            continue
        
        print(f"处理模型: {name}")
        
        # 检查模型路径是否存在
        if not check_model_path_exists(model_config):
            print(f"跳过模型 {name}，因为模型路径不存在")
            aistudio_repo_id = model_config.get('AISTUDIO_REPO_ID', '')
            if aistudio_repo_id:
                print(f"从Aistudio上下载模型: {name}")
                if download_model(aistudio_repo_id):
                    print(f"成功下载模型: {name}")
                else:
                    print(f"下载模型失败: {name}")
                    exit(1)
            else:
                print(f"本地不存在模型且未提供AISTUDIO_REPO_ID，无法下载模型: {name}")
                exit(1)
        # 清理名称用于文件名
        script_name = clean_name(name)
        
        # 复制并重命名模板文件
        for template_file in template_files:
            if not os.path.exists(template_file):
                print(f"警告: 模板文件不存在: {template_file}")
                continue
            
            # 获取基础名称
            base_name = os.path.basename(template_file)
            name_without_ext = os.path.splitext(base_name)[0]
            
            # 生成新文件名
            new_filename = f"./scripts/regression/{name_without_ext}_{script_name}.py"
            
            # 复制文件
            shutil.copy2(template_file, new_filename)
            print(f"已创建: {new_filename}")
            
            # 替换文件中的变量
            replace_variables_in_file(new_filename, model_config)
            print(f"已更新变量: {new_filename}")

if __name__ == "__main__":
    main()