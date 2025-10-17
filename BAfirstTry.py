"""
ts花卉意象分析系统
使用DeepSeek API分析诗词，返回标准化的JSON格式数据的第一次尝试
不作测试用
API调用、JSON解析、数据标准化
"""

import json
import requests
import time


class PoemFlowerAnalyzer:
    """
    此Analyzer实现了调用DeepSeek API分析诗词中的花卉意象，
    return standardize JSON data
    """

    def __init__(self, api_key):
        """
        初始化Analyzer
        Args:
            api_key (str): DeepSeek API key
            my new API_KEY = "sk-5176c49ed09c4af98b5ee37598df4f91"
        """
        self.api_key = api_key
        self.total_tokens_used = 0  # token使用统计
        print("诗词花卉分析器初始化完成")

    def build_analysis_prompt(self, poem_text):
        """
        bap构建分析提示词 - set for output JSON type

        Args:
            poem_text (str): poems text content

        Returns:
            str: 格式化后的prompts
        """
        prompt = f"""你好，请严格按JSON格式分析以下诗歌：

诗歌内容：
{poem_text}

输出要求：
- date: 成诗年月（用公元纪年，直接用数字，公元前用负值）
- flower: 相关花卉名称（使用完整名称，如无则写"无"）
- imagery: 意象情感标签数组（中文关键词）

重点：
1. date字段使用公元纪年数字（公元前用负值）
2. flower字段使用完整的花卉名称
3. imagery字段使用简洁的关键词标签

只输出JSON格式，不要任何其他文字说明！！！"""
        return prompt

    def call_deepseek_api(self, prompt):
        """
        CALLL DeepSeek API

        Args:
            prompt (str): prompt text

        Returns:
            dict: API响应数据
        """
        # 配置 deepseek API https://api.deepseek.com/v1/chat/completions
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的诗歌分析专家，必须严格按照用户要求的JSON格式输出。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # 低温度确保输出稳定(?)
            "stream": False
        }

        try:
            # sent API request
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()  # 如果状态码不是200，error

            # 解析响应
            result = response.json()
            return result

        except requests.exceptions.Timeout:
            print("API request timed out")
            return None
        except requests.exceptions.ConnectionError:
            print("internet connect error")
            return None
        except Exception as e:
            print(f"overwhelmed: {e}")
            return None

    def parse_api_response(self, api_response):
        """
        解析API响应，提取和清理文本内容

        Args:
            api_response (dict): API返回的原始数j
        Returns:
            str: 清理后的文本内容
        """
        if not api_response or 'choices' not in api_response:
            return None

        # 提取响应内容
        response_content = api_response['choices'][0]['message']['content']

        # 清理文本   清除 markdown 数据块标记
        cleaned_content = response_content.replace('```json', '').replace('```', '').strip()

        return cleaned_content

    def safe_json_parse(self, json_text):
        """
        安全解析JSON文本(包括错误处理）

        Args:
            json_text (str): 待解析的JSON文本
        Returns:
            dict: 解析后的dict，解析失败返回默认值
        """
        if not json_text:
            return self.get_default_result()

        try:
            #直接解析
            return json.loads(json_text)
        except json.JSONDecodeError:
            try:
                #第一次解析失败，清理后解析
                cleaned_text = json_text.strip()

                # 检查JSON对象是否是完整的
                if cleaned_text.startswith('{') and cleaned_text.endswith('}'):
                    return json.loads(cleaned_text)
                else:
                    #提取JSON部分
                    start_index = cleaned_text.find('{')
                    end_index = cleaned_text.rfind('}') + 1

                    if start_index != -1 and end_index != 0:
                        json_str = cleaned_text[start_index:end_index]
                        return json.loads(json_str)
                    else:
                        # 无有效的JSON
                        raise ValueError("无有效的JSON")
            except Exception as e:
                print(f"JSON解析失败: {e}")
                print(f"原始文本: {json_text}")
                return self.get_default_result()

    def get_default_result(self):
        """
        获取默认的分析结果（用于错误处理）

        Returns:
            dict: 默认的分析结果
        """
        return {
            "date": 0,
            "flower": "无",
            "imagery": []
        }

    def standardize_flower_name(self, flower_name):
        """
        花卉名称将简称转为全称
        Args:
            flower_name (str): 原始花卉名称
        Returns:
            str: 标准化后的花卉名称
        """
        # 花卉名称映射字典
        flower_mapping = {
            # 梅花相关
            '梅': '梅花', '寒梅': '梅花', '红梅': '梅花', '白梅': '梅花',
            # 菊花相关
            '菊': '菊花', '秋菊': '菊花', '黄菊': '菊花', '残菊': '菊花',
            # 莲花/荷花相关
            '莲': '莲花', '荷': '莲花', '芙蓉': '莲花', '芙蕖': '莲花',
            # 其他花卉
            '桃': '桃花', '杏': '杏花', '牡丹': '牡丹',
            '桂': '桂花', '梨': '梨花', '海棠': '海棠',
            '兰': '兰花', '茉莉': '茉莉', '芍药': '芍药', '水仙': '水仙'
        }

        # 返回映射后的名称，如果找不到映射返回原名称
        return flower_mapping.get(flower_name, flower_name)

    def standardize_date(self, date_value):
        """
        标准化日期格式，使用公元纪年
        Args:
            date_value: 原始日期值
        Returns:
            int: 标准化后的公元纪年
        """
        try:
            # 如果已经是数字，直接返回
            if isinstance(date_value, (int, float)):
                return int(date_value)

            # 处理字符串格式的日期
            date_str = str(date_value).strip()

            # 处理公元前日期
            if '公元前' in date_str:
                year = int(date_str.replace('公元前', '').strip())
                return -year  # 公元前使用负值

            # 处理公元后日期
            if '公元' in date_str:
                year = int(date_str.replace('公元', '').strip())
                return year

            # 处理数字
            if date_str.isdigit() or (date_str.startswith('-') and date_str[1:].isdigit()):
                return int(date_str)

            # 无法解析
            return 0

        except (ValueError, TypeError):
            # 解析失败
            return 0

    def analyze_single_poem(self, title, author, content):
        """
        MAIN analyze way

        Args:
            title (str)
            author (str)
            content (str)
        Returns:
            分析结果和元数据
        """
        print(f"正在分析: 《{title}》 - {author}")

        # 1. 构建提示词
        prompt = self.build_analysis_prompt(content)

        # 2. 调用API
        api_response = self.call_deepseek_api(prompt)
        if not api_response:
            print(f"   API调用失败")
            return self.create_error_result(title, author, content)

        # 3. 解析API响应
        response_text = self.parse_api_response(api_response)
        if not response_text:
            print(f"   响应解析失败")
            return self.create_error_result(title, author, content)

        # 4. 解析JSON
        parsed_result = self.safe_json_parse(response_text)

        # 5. 标准化结果
        standardized_result = self.standardize_analysis_result(parsed_result)

        # 6. token使用量
        self.total_tokens_used += len(prompt) * 1.4 + len(response_text) * 1.4

        print(f"      分析成功")
        print(f"      年代: {standardized_result['date']}")
        print(f"      花卉: {standardized_result['flower']}")
        print(f"      意象: {', '.join(standardized_result['imagery'])}")

        # 返回完整结果
        return {
            'title': title,
            'author': author,
            'content': content,
            'standardized_result': standardized_result,
            'raw_response': response_text
        }

    def standardize_analysis_result(self, raw_result):
        """
        标准化分析结果，确保数据格式一致
        Args:
            raw_result (dict): 原始分析结果
        Returns:
            dict: 标准化分析结果
        """
        # 创建标准化的结果字典
        standardized = {
            "date": raw_result.get('date', 0),
            "flower": raw_result.get('flower', '无'),
            "imagery": raw_result.get('imagery', [])
        }

        # 标准化花卉名称
        standardized['flower'] = self.standardize_flower_name(standardized['flower'])

        # 标准化日期格式
        standardized['date'] = self.standardize_date(standardized['date'])

        # 确保意象标签是列表格式
        if not isinstance(standardized['imagery'], list):
            if isinstance(standardized['imagery'], str):
                standardized['imagery'] = [standardized['imagery']]
            else:
                standardized['imagery'] = []

        return standardized

    def create_error_result(self, title, author, content):
        """
        错误结果记录
        Args:
            title (str)
            author (str)
            content (str)
        Returns:
            错误结果
        """
        return {
            'title': title,
            'author': author,
            'content': content,
            'standardized_result': self.get_default_result(),
            'error': '分析失败'
        }

    def batch_analyze(self, poems_data, batch_delay=1):
        # dont work
        """
        批量分析诗词数据(try)
        Args:
            poems_data (list)
            batch_delay (int): 间隔时间
        Returns:
            分析结果列表
        """
        print("开始批量分析诗词...")
        print(f"总共需要分析 {len(poems_data)} 首诗词")

        results = []
        start_time = time.time()

        for i, poem in enumerate(poems_data, 1):
            # 显示进度信息
            if i % 5 == 0 or i == 1 or i == len(poems_data):
                elapsed_time = time.time() - start_time
                print(f"进度: {i}/{len(poems_data)}")

            # 分析单首诗词
            result = self.analyze_single_poem(
                poem.get('title', f'诗词_{i}'),
                poem.get('author', '未知'),
                poem.get('content', '')
            )

            results.append(result)

            # 显示成本统计
            if i % 10 == 0:
                cost = self.total_tokens_used * 0.14 / 1000000
                print(f"已使用 {self.total_tokens_used:,} tokens, 估算成本: ¥{cost:.4f}")

            # 请求间隔
            time.sleep(batch_delay)

        # 完成统计
        end_time = time.time()
        total_time = end_time - start_time
        success_count = len([r for r in results if 'error' not in r])

        print(f"\n批量分析完成！")
        print(f"成功: {success_count}/{len(poems_data)} (成功率: {success_count / len(poems_data) * 100:.1f}%)")
        print(f"用时: {total_time / 60:.1f} 分钟")
        print(f"tokens: {self.total_tokens_used:,}, 估算成本: ¥{self.total_tokens_used * 0.14 / 1000000:.4f}")

        return results

    def export_results(self, results, output_file='poem_analysis_results_fromFirstTry.json'):
        """
        导出分析结果到JSON文件

        Arg
            results (list)
            output_file (str)
        Returns:
            文件路径
        """
        print(f"\n正在导出结果到文件: {output_file}")

        # 准备导出数据
        export_data = []

        for result in results:
            record = {
                'title': result['title'],
                'author': result['author'],
                'analysis_result': result['standardized_result']
            }

            # record['content'] = result.get('content', '')原始内容

            export_data.append(record)

        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"结果导出完成 共导出 {len(export_data)} 条记录")
        return output_file

    def display_sample_results(self, results, num_samples=3):
        """
        样本分析结果
        Args:
            results (list)
            num_samples (int)
        """
        print(f"\n样本分析结果 (前{num_samples}首):")
        print("=" * 60)

        successful_results = [r for r in results if 'error' not in r][:num_samples]

        for i, result in enumerate(successful_results, 1):
            std_result = result['standardized_result']
            print(f"\n{i}. 《{result['title']}》 - {result['author']}")
            print(f"   标准JSON: {json.dumps(std_result, ensure_ascii=False)}")
            print(f"   年代: {std_result['date']}")
            print(f"   花卉: {std_result['flower']}")
            print(f"   意象: {', '.join(std_result['imagery'])}")
            print(f"   预览: {result['content'][:50]}...")


def main():
    # 1. API key
    API_KEY = "sk-5176c49ed09c4af98b5ee37598df4f91"

    # 2. analyzer
    analyzer = PoemFlowerAnalyzer(API_KEY)

    # 3. 测试数据
    sample_poems = [
        {
            'title': '题都城南庄',
            'author': '崔护',
            'content': '去年今日此门中，人面桃花相映红。人面不知何处去，桃花依旧笑春风。'
        },
        {
            'title': '梅花',
            'author': '王安石',
            'content': '墙角数枝梅，凌寒独自开。遥知不是雪，为有暗香来。'
        },
        {
            'title': '饮酒',
            'author': '陶渊明',
            'content': '采菊东篱下，悠然见南山。山气日夕佳，飞鸟相与还。'
        },
        {
            'title': '静夜思',
            'author': '李白',
            'content': '床前明月光，疑是地上霜。举头望明月，低头思故乡。'
        }
    ]

    print("=" * 60)
    print("诗词花卉意象分析系统")
    print("=" * 60)

    # 4. 批量分析(if)
    results = analyzer.batch_analyze(sample_poems, batch_delay=1)

    # 5. 显示样本结果
    analyzer.display_sample_results(results)

    # 6. 导出结果
    output_file = analyzer.export_results(results)

    print(f"结果文件: {output_file}")
    print("分析器通过")


if __name__ == "__main__":
    main()