import json
import time
import random
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
from .config_loader import CONFIG
from .utils import clean_title


class DataFetcher:
    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url

    def fetch_newsnow_data(self, platform_config: dict) -> Optional[str]:
        """获取NewsNow数据"""
        try:
            id_value = platform_config["id"]
            url = f"https://newsnow.busiyi.world/api/s?id={id_value}&latest"

            # 获取数据源特定的请求头
            source = platform_config.get("source", "newsnow")
            headers = CONFIG["SOURCE_HEADERS"].get(source, {}).copy()

            # 添加基础请求头
            base_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
                "Cache-Control": "no-cache",
            }
            base_headers.update(headers)

            proxies = None
            if self.proxy_url:
                proxies = {"http": self.proxy_url, "https": self.proxy_url}

            response = requests.get(
                url, proxies=proxies, headers=base_headers, timeout=10
            )
            response.raise_for_status()

            data_text = response.text
            data_json = json.loads(data_text)

            status = data_json.get("status", "未知")
            if status not in ["success", "cache"]:
                raise ValueError(f"响应状态异常: {status}")

            status_info = "最新数据" if status == "success" else "缓存数据"
            print(f"获取 {id_value} 成功（{status_info}）")
            return data_text

        except Exception as e:
            print(f"NewsNow请求失败: {e}")
            return None

    def fetch_tophub_data(self, platform_config: dict) -> Optional[str]:
        """获取Tophub数据，支持多页和任意请求参数"""
        try:
            request_interval = CONFIG["REQUEST_INTERVAL"] / 1000
            request_min_interval = CONFIG["REQUEST_MIN_INTERVAL"] / 1000
            request_max_interval = CONFIG["REQUEST_MAX_INTERVAL"] / 1000

            category = platform_config.get("category", "news")
            id = platform_config.get("id", "news")

            # 1. 优先使用params配置
            if "params" in platform_config:
                base_params = platform_config["params"].copy()
                pages = base_params.pop("page", [1])  # 提取page参数
            else:
                # 2. 兼容旧配置：order和page
                base_params = {}
                if "order" in platform_config:
                    base_params["order"] = platform_config["order"]
                pages = platform_config.get("page", [1])

            # 统一pages格式为列表
            if isinstance(pages, int):
                pages = [pages]
            elif not isinstance(pages, (list, tuple)):
                pages = [int(pages)]

            # 请求头准备
            source = platform_config.get("source", "tophub")
            headers = CONFIG["SOURCE_HEADERS"].get(source, {}).copy()
            base_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            base_headers.update(headers)

            proxies = None
            if self.proxy_url:
                proxies = {"http": self.proxy_url, "https": self.proxy_url}

            all_items = []
            for idx, current_page in enumerate(pages, 1):
                # 构建最终请求参数
                params = base_params.copy()
                params["p"] = current_page  # 确保页码参数正确

                url = f"https://tophub.today/c/{category}"
                response = requests.get(
                    url,
                    params=params,
                    headers=base_headers,
                    proxies=proxies,
                    timeout=15
                )
                response.raise_for_status()

                # 解析并收集数据
                page_result = json.loads(self.parse_tophub_html(response.text))
                items = page_result.get("items", [])
                all_items.extend(items)
                print(f"今日热榜: {id} 第 {current_page} 页抓取成功，共 {len(items)} 条")

                # 非最后一页随机等待
                if idx < len(pages):
                    wait_sec = random.uniform(request_min_interval, request_max_interval)
                    print(f"等待 {wait_sec:.2f} 秒后继续下一页...")
                    time.sleep(wait_sec)

            # 返回合并结果
            result = {"status": "success", "items": all_items}
            return json.dumps(result)

        except Exception as e:
            print(f"今日热榜 请求失败: {e}")
            return None
    #
    # def fetch_tophub_data1(self, platform_config: dict) -> Optional[str]:
    #     """获取Tophub数据"""
    #     try:
    #         # 获取配置参数
    #         category = platform_config.get("category", "news")
    #         order = platform_config.get("order", "")
    #         page = platform_config.get("page", 1)
    #
    #         # 构建URL
    #         base_url = f"https://tophub.today/c/{category}"
    #         params = {"p": page}
    #         if order:
    #             params["order"] = order
    #
    #         # 获取数据源特定的请求头
    #         source = platform_config.get("source", "tophub")
    #         headers = CONFIG["SOURCE_HEADERS"].get(source, {}).copy()
    #
    #         # 添加基础请求头
    #         base_headers = {
    #             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    #             "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    #             "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    #         }
    #         base_headers.update(headers)
    #
    #         # 设置代理
    #         proxies = None
    #         if self.proxy_url:
    #             proxies = {"http": self.proxy_url, "https": self.proxy_url}
    #
    #         # 发送请求
    #         response = requests.get(
    #             base_url,
    #             params=params,
    #             headers=base_headers,
    #             proxies=proxies,
    #             timeout=15
    #         )
    #         response.raise_for_status()
    #
    #         # 解析HTML
    #         return self.parse_tophub_html(response.text)
    #
    #     except Exception as e:
    #         print(f"Tophub请求失败: {e}")
    #         return None

    def parse_tophub_html(self, html_content: str) -> str:
        """解析Tophub HTML内容"""
        from bs4 import BeautifulSoup
        import re

        soup = BeautifulSoup(html_content, 'html.parser')
        result = {"status": "success", "items": []}

        # 查找所有新闻源卡片
        cards = soup.find_all('div', class_='cc-cd')

        for card in cards:
            # 提取新闻源信息
            source_name = ""
            source_link = card.find('a')
            if source_link:
                source_name_div = source_link.find('div', class_='cc-cd-lb')
                if source_name_div:
                    source_name = source_name_div.get_text(strip=True)

            # 提取时间信息
            time_info_div = card.find('div', class_='cc-cd-if')
            time_text = ""
            if time_info_div:
                time_span = time_info_div.find('span')
                if time_span:
                    time_text = time_span.get_text(strip=True)

            # 提取新闻条目
            news_items = card.find('div', class_='cc-cd-cb-l')
            if not news_items:
                continue

            items = news_items.find_all('a', rel='nofollow')
            for i, item in enumerate(items, 1):
                # 提取排名
                rank_span = item.find('span', class_='s')
                if rank_span:
                    # 清理排名中的特殊字符
                    rank_text = re.sub(r'\D', '', rank_span.get_text(strip=True))
                    rank = int(rank_text) if rank_text.isdigit() else i
                else:
                    rank = i

                # 提取标题
                title_span = item.find('span', class_='t')
                title = title_span.get_text(strip=True) if title_span else "无标题"

                # 提取URL
                url = item.get('href', '')

                # 添加到结果
                result["items"].append({
                    "title": title,
                    "url": url,
                    "mobileUrl": url,
                    "rank": rank,
                    "source": source_name,
                    # 注意,不能在这里添加date,否则会影响去重效果
                    # "date": time_text,
                })

        return json.dumps(result)

    def fetch_zqrb_data(self, platform_config: dict) -> Optional[str]:
        """获取证券日报网数据，支持时间过滤"""
        try:
            # 获取配置参数
            keyword = platform_config["keyword"]
            pages = platform_config.get("pages", 1)
            recent_days = CONFIG.get("RECENT_DAYS", 0)  # 0表示不过滤

            # 计算时间阈值
            cutoff_date = None
            if recent_days > 0:
                cutoff_date = datetime.now() - timedelta(days=recent_days)
                print(f"时间过滤: 只获取{cutoff_date.strftime('%Y-%m-%d')}之后的新闻")

            # 获取数据源特定的请求头
            source = platform_config.get("source", "zqrb")
            headers = CONFIG["SOURCE_HEADERS"].get(source, {}).copy()

            # 添加基础请求头
            base_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            base_headers.update(headers)

            proxies = None
            if self.proxy_url:
                proxies = {"http": self.proxy_url, "https": self.proxy_url}

            all_items = []
            for page in range(1, pages + 1):
                # 构建URL
                url = f"http://search.zqrb.cn/search.php"
                params = {
                    "src": "all",
                    "q": keyword,
                    "f": "_all",
                    "s": "newsdate_DESC",
                    "p": page
                }

                response = requests.get(
                    url,
                    params=params,
                    headers=base_headers,
                    proxies=proxies,
                    timeout=15
                )
                response.raise_for_status()

                # 解析HTML并过滤时间
                items = self.parse_zqrb_html(response.text, cutoff_date)
                all_items.extend(items)
                print(f"证券日报网: {keyword} 第 {page} 页抓取成功，共 {len(items)} 条")

                # 如果没有符合时间条件的新闻，提前停止
                if recent_days > 0 and len(items) == 0:
                    print(f"第 {page} 页没有符合时间条件的新闻，停止抓取")
                    break

                # 页间延迟
                if page < pages:
                    time.sleep(random.uniform(1, 2))

            # 返回结果
            result = {"status": "success", "items": all_items}
            return json.dumps(result)

        except Exception as e:
            print(f"证券日报网请求失败: {e}")
            return None

    def parse_zqrb_html(self, html_content: str, cutoff_date: Optional[datetime] = None) -> List[Dict]:
        """解析证券日报网HTML内容，支持时间过滤"""
        from bs4 import BeautifulSoup
        import re

        soup = BeautifulSoup(html_content, 'html.parser')
        items = []

        # 查找搜索结果项
        result_list = soup.find('dl', class_='result-list')
        if not result_list:
            return items

        # 提取每个结果项
        for idx, dt_item in enumerate(result_list.find_all('dt'), 1):
            # 标题和链接
            link = dt_item.find('a')
            if not link:
                continue

            title = link.get_text(strip=True)
            url = link.get('href', '')

            # 清理标题中的HTML标签
            title = re.sub(r'<[^>]+>', '', title)

            # 获取时间信息（从相邻的dd元素）
            time_str = None
            dd_item = dt_item.find_next_sibling('dd')
            if dd_item:
                time_info = dd_item.find('p', class_='field-info')
                if time_info:
                    time_match = re.search(r'时间:(\d{4}年\d{1,2}月\d{1,2}日)', time_info.get_text())
                    if time_match:
                        time_str = time_match.group(1)

            # 转换时间格式
            news_date = None
            if time_str:
                try:
                    # 将中文日期转换为标准格式
                    time_str = time_str.replace('年', '-').replace('月', '-').replace('日', '')
                    news_date = datetime.strptime(time_str, "%Y-%m-%d")
                except Exception:
                    pass

            # 时间过滤
            if cutoff_date and news_date and news_date < cutoff_date:
                continue  # 跳过过时的新闻

            # 添加到结果
            items.append({
                "title": title,
                "url": url,
                "mobileUrl": url,  # 使用相同URL
                "rank": idx,
                "source": "证券日报网",
                "date": news_date.strftime("%Y-%m-%d") if news_date else "未知"
            })

        return items

    def fetch_data(
            self,
            platform_config: dict,
            max_retries: int = 2,
            min_retry_wait: int = 3,
            max_retry_wait: int = 5,
    ) -> Tuple[Optional[str], str, str]:
        """获取指定平台数据，支持重试"""
        # 获取平台标识
        source_id = platform_config["id"]
        alias = platform_config.get("name", source_id)
        source_type = platform_config.get("source", "newsnow")

        retries = 0
        while retries <= max_retries:
            try:
                if source_type == "tophub":
                    response_data = self.fetch_tophub_data(platform_config)
                elif source_type == "zqrb":  # 新增证券日报网支持
                    response_data = self.fetch_zqrb_data(platform_config)
                else:
                    response_data = self.fetch_newsnow_data(platform_config)

                if response_data:
                    return response_data, source_id, alias
                else:
                    raise ValueError("未获取到有效响应数据")

            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    wait_time = random.uniform(min_retry_wait, max_retry_wait)
                    print(f"请求 {source_id} 失败: {e}. {wait_time:.2f}秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"请求 {source_id} 失败: {e}")
                    return None, source_id, alias

        return None, source_id, alias

    def crawl_websites(
            self,
            platforms_config: List[dict],
            request_interval: int = CONFIG["REQUEST_INTERVAL"],
    ) -> Tuple[Dict, Dict, List]:
        """爬取多个网站数据"""
        results = {}
        id_to_name = {}
        failed_ids = []

        for i, platform_config in enumerate(platforms_config):
            source_id = platform_config["id"]
            name = platform_config.get("name", source_id)

            id_to_name[source_id] = name
            response, _, _ = self.fetch_data(platform_config)

            if response:
                try:
                    data = json.loads(response)
                    results[source_id] = {}
                    for item in data.get("items", []):
                        title = item["title"]
                        url = item.get("url", "")
                        mobile_url = item.get("mobileUrl", "")
                        rank = item.get("rank", 1)
                        date = item.get("date", "")

                        # 保留原有数据结构
                        if title in results[source_id]:
                            results[source_id][title]["ranks"].append(rank)
                        else:
                            results[source_id][title] = {
                                "ranks": [rank],
                                "url": url,
                                "mobileUrl": mobile_url,
                                "date": date,
                            }
                except Exception as e:
                    print(f"处理 {source_id} 数据出错: {e}")
                    failed_ids.append(source_id)
            else:
                failed_ids.append(source_id)

            # 请求间隔控制
            if i < len(platforms_config) - 1:
                actual_interval = request_interval + random.randint(-10, 20)
                actual_interval = max(50, actual_interval)
                time.sleep(actual_interval / 1000)

        print(f"成功: {list(results.keys())}, 失败: {failed_ids}")
        return results, id_to_name, failed_ids
