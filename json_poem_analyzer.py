#main
import json
import requests
import time
import os
import glob
from collections import defaultdict


class PoetryAnalyzer:


    def __init__(self, api_key):
        self.api_key = api_key
        self.total_tokens = 0
        self.analysis_results = []
        self.processed_count = 0

    def analyze_poem(self, poem_data):
        """分析单首"""
        prompt = self._build_analysis_prompt(poem_data['content'])

        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                cleaned_content = self._clean_response(content)
                parsed_result = self._parse_json_result(cleaned_content)

                if parsed_result:
                    standardized = self._standardize_result(parsed_result)


                    analysis_record = {
                        'title': poem_data['title'],
                        'author': poem_data['author'],
                        'content': poem_data['content'],  #Retain the complete poetic content
                        'analysis': standardized,
                        'source_file': poem_data['source_file'],
                        'analysis_timestamp': time.time()
                    }

                    self.analysis_results.append(analysis_record)
                    self.processed_count += 1
                    return True

        except Exception as e:
            print(f"分析失败: {e}")

        return False

    def _build_analysis_prompt(self, content):
        return f"""请分析以下诗歌并输出JSON格式结果：

{content}

要求：
1. 分析创作年代（公元纪年，公元前用负值）
2. 识别相关花卉
3. 提取核心意象标签

输出格式：
{{"date": 年代, "flower": "花卉", "imagery": ["意象1", "意象2"]}}"""

    def _clean_response(self, content):
        content = content.replace('```json', '').replace('```', '').strip()
        return content

    def _parse_json_result(self, content):
        try:
            return json.loads(content)
        except:
            return None

    def _standardize_result(self, result):
        """标准化分析结果"""
        return {
            "date": self._standardize_date(result.get('date', 0)),
            "flower": self._standardize_flower(result.get('flower', '无')),
            "imagery": result.get('imagery', [])
        }

    def _standardize_date(self, date_val):
        """标准化日期"""
        try:
            if isinstance(date_val, (int, float)):
                return int(date_val)
            date_str = str(date_val)
            if '公元前' in date_str:
                return -int(date_str.replace('公元前', ''))
            return int(date_str) if date_str.isdigit() else 0
        except:
            return 0

    def _standardize_flower(self, flower):
        """标准化花卉名称"""
        mapping = {
            '梅': '梅花', '菊': '菊花', '莲': '莲花', '荷': '莲花',
            '桃': '桃花', '杏': '杏花', '牡丹': '牡丹', '桂': '桂花',
            '梨': '梨花', '海棠': '海棠', '兰': '兰花'
        }
        return mapping.get(flower, flower)

    def save_results(self, output_dir='analysis_output'):
        """统一目录"""
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 生成带时间戳的文件名
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f'poetry_analysis_{timestamp}.json'
        filepath = os.path.join(output_dir, filename)

        # 构建完整输出数据
        output_data = {
            'project': '唐宋词花卉意象分析',
            'analysis_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_processed': self.processed_count,
            'total_analyzed': len(self.analysis_results),
            'metadata': {
                'output_dir': output_dir,
                'file_created': timestamp,
                'api_tokens_used': self.total_tokens
            },
            'results': self.analysis_results
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"分析结果已保存到: {filepath}")
        return filepath

    def load_previous_results(self, output_dir='analysis_output'):
        #加载之前的分析结果
        if not os.path.exists(output_dir):
            return set(), 0

        try:
            #找到最新的分析文件
            json_files = glob.glob(os.path.join(output_dir, 'poetry_analysis_*.json'))
            if not json_files:
                return set(), 0

            latest_file = max(json_files, key=os.path.getctime)
            print(f"加载最新分析文件: {os.path.basename(latest_file)}")

            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 构建已分析诗词的索引
            analyzed_poems = set()
            for result in data.get('results', []):
                key = f"{result['title']}_{result['author']}"
                analyzed_poems.add(key)

            # 恢复计数和结果
            self.processed_count = data.get('total_processed', 0)
            self.analysis_results = data.get('results', [])
            self.total_tokens = data.get('metadata', {}).get('api_tokens_used', 0)

            print(f"已加载之前分析结果: {len(analyzed_poems)} 首诗词")
            return analyzed_poems, len(analyzed_poems)

        except Exception as e:
            print(f"加载之前结果失败: {e}")
            return set(), 0


class DataLoader:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.databases = ['SongSongs', 'TangPoems', 'TangPoems2']

    def scan_databases(self):
        """扫描数据库统计信息"""

        print("扫描数据库文件...")
        stats = {}
        total_files = 0
        total_poems_estimate = 0

        for db_name in self.databases:
            db_path = os.path.join(self.data_dir, db_name)
            if os.path.exists(db_path):
                json_files = glob.glob(os.path.join(db_path, '*.json'))
                file_count = len(json_files)
                stats[db_name] = file_count
                total_files += file_count

                # 估算诗词数量（基于文件数量）
                poems_estimate = file_count * 1000  # 假设每个文件约1000首
                total_poems_estimate += poems_estimate
                print(f"  {db_name}: {file_count} 个文件 (约{poems_estimate}首)")
            else:
                stats[db_name] = 0
                print(f"  {db_name}: 目录不存在")

        print(f"文件总数: {total_files}")
        print(f"估算诗词总数: {total_poems_estimate}")
        return stats, total_poems_estimate

    def load_poems(self, mode='sample', sample_size=100, sample_rate=0.01, limit=None):
        """load"""
        print("正在加载诗词数据...")
        all_poems = []

        for db_name in self.databases:
            db_path = os.path.join(self.data_dir, db_name)
            if not os.path.exists(db_path):
                continue

            json_files = glob.glob(os.path.join(db_path, '*.json'))
            print(f"处理 {db_name} 数据库 ({len(json_files)} 个文件)...")

            files_to_process = json_files
            if mode == 'sample' and len(json_files) > 5:
                files_to_process = json_files[:5]  # 采样时只处理前5个文件

            for json_file in files_to_process:
                poems = self._load_from_file(json_file, mode, sample_rate, sample_size)
                all_poems.extend(poems)

                if limit and len(all_poems) >= limit:
                    all_poems = all_poems[:limit]
                    break

            if limit and len(all_poems) >= limit:
                break

        print(f"成功加载 {len(all_poems)} 首诗词")
        return all_poems

    def _load_from_file(self, file_path, mode, sample_rate, sample_size):
        """从单个文件加载数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            poems = []
            if isinstance(data, list):
                items_to_process = data

                # 应用采样策略
                if mode == 'sample' and len(data) > sample_size:
                    import random
                    items_to_process = random.sample(data, sample_size)
                elif mode == 'rate' and sample_rate < 1.0:
                    items_to_process = [item for i, item in enumerate(data) if i % int(1/sample_rate) == 0]

                for item in items_to_process:
                    poem = self._extract_poem_data(item, file_path)
                    if poem:
                        poems.append(poem)

            return poems

        except Exception as e:
            print(f"文件读取失败 {file_path}: {e}")
            return []

    def _extract_poem_data(self, item, source_file):
        """提取诗词数据"""
        if not isinstance(item, dict):
            return None

        # 提取标题、作者、内容
        title = item.get('title') or '无题'
        author = item.get('author') or '未知'
        content = item.get('content') or ' '.join(item.get('paragraphs', []))

        if content and len(content.strip()) > 10:
            return {
                'title': str(title),
                'author': str(author),
                'content': str(content),  #  complete poetic content
                'source_file': os.path.basename(source_file)
            }

        return None


def calculate_cost_estimate(total_poems):
    """计算成本估算"""
    tokens_per_poem = 800
    total_tokens = total_poems * tokens_per_poem
    cost = total_tokens * 0.14 / 1000000

    print(f"\n估算:")
    print(f"  诗词数量: {total_poems}")
    print(f"  估算tokens: {total_tokens:,}")
    print(f"  估: {cost:.2f}")

    return cost


def main():
    """主函数"""

    # API密钥配置
    API_KEY = "sk-5176c49ed09c4af98b5ee37598df4f91"

    # 初始化分析器和数据加载器
    analyzer = PoetryAnalyzer(API_KEY)
    data_loader = DataLoader('data')

    # 扫描数据库
    stats, total_poems_estimate = data_loader.scan_databases()

    # 选择分析模式
    print("\n分析模式:")
    print("1. 抽样分析 (快速测试)")
    print("2. 完整分析 (处理所有数据)")
    print("3. 继续分析 (从上次停止处继续)")

    choice = input("请输入选择 (1/2/3): ").strip()

    if choice == '1':
        # 抽样分析模式
        sample_size = int(input("请输入抽样数量 (默认10): ") or "10")
        poems = data_loader.load_poems(mode='sample', sample_size=sample_size)
        calculate_cost_estimate(sample_size)

    elif choice == '2':
        # 完整分析模式
        limit = input("请输入处理数量限制 (enter表示无限制): ").strip()
        limit = int(limit) if limit else None
        poems = data_loader.load_poems(mode='full', limit=limit)
        poems_count = limit if limit else total_poems_estimate
        calculate_cost_estimate(poems_count)

    elif choice == '3':
        # 继续分析
        analyzed_poems, previous_count = analyzer.load_previous_results()
        poems = data_loader.load_poems(mode='full')

        # 过滤掉已分析的诗词
        original_count = len(poems)
        poems = [p for p in poems if f"{p['title']}_{p['author']}" not in analyzed_poems]
        print(f"过滤后待分析诗词: {len(poems)}/{original_count}")

    else:
        print("retry")
        return

    if not poems:
        print("empty")
        return

    # 开始分析
    print(f"\n开始诗词分析...")
    print(f"目标分析数量: {len(poems)} 首")

    success_count = 0
    start_time = time.time()

    for i, poem in enumerate(poems, 1):
        print(f"\n进度: {i}/{len(poems)}")
        print(f"诗词: 《{poem['title']}》 - {poem['author']}")

        if analyzer.analyze_poem(poem):
            success_count += 1
            print("分析成功")
        else:
            print("分析失败")

        # 每分析20首保存一次(or 10)
        #速度估算器
        if i % 20 == 0:
            analyzer.save_results()
            elapsed_time = time.time() - start_time
            poems_per_minute = i / (elapsed_time / 60)
            print(f"已保存检查点 | 速度: {poems_per_minute:.1f} 首/分钟")

        # 请求间隔
        time.sleep(1)

    # 最终保存
    if success_count > 0:
        final_file = analyzer.save_results()

        # 分析统计
        elapsed_time = time.time() - start_time


        print(f"\n分析完成统计:")
        print(f"总处理诗词: {analyzer.processed_count}")
        print(f"成功分析: {success_count}")
        print(f"成功率: {(success_count/len(poems))*100:.1f}%")
        print(f"总用时: {elapsed_time/60:.1f} 分钟")
        print(f"结果文件: {final_file}")

        # 样本结果
        print(f"\n样本分析结果:")
        for result in analyzer.analysis_results[:3]:
            analysis = result['analysis']
            print(f"《{result['title']}》 - {result['author']}")
            print(f"  诗句: {result['content'][:50]}...")
            print(f"  创作年代: {analysis['date']}")
            print(f"  相关花卉: {analysis['flower']}")
            print(f"  意象标签: {', '.join(analysis['imagery'])}")
    else:
        print("none")


if __name__ == "__main__":
    main()