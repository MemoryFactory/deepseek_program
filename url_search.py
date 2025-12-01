import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
import re
import threading
import time
import chardet
from html import unescape
import random

class WebSearchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("网页关键词搜索工具 - 支持中文")
        self.root.geometry("1000x750")
        
        # 搜索控制标志
        self.stop_search_flag = False
        self.search_running = False
        
        # 创建界面组件
        self.create_widgets()
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 网址输入区域
        url_frame = ttk.Frame(main_frame)
        url_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(url_frame, text="目标网址:").grid(row=0, column=0, sticky=tk.W)
        self.url_entry = ttk.Entry(url_frame, width=80)
        self.url_entry.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        self.url_entry.insert(0, "https://")
        
        # 关键词输入区域
        keyword_frame = ttk.Frame(main_frame)
        keyword_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(keyword_frame, text="关键词:").grid(row=0, column=0, sticky=tk.W)
        self.keyword_entry = ttk.Entry(keyword_frame, width=80)
        self.keyword_entry.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        
        # 搜索选项区域
        options_frame = ttk.LabelFrame(main_frame, text="搜索选项", padding="10")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # 第一行选项
        row1_frame = ttk.Frame(options_frame)
        row1_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(row1_frame, text="搜索模式:").pack(side=tk.LEFT)
        
        # 搜索模式选项
        self.search_mode_var = tk.StringVar(value="1: 仅标题页翻页")
        self.mode_combo = ttk.Combobox(row1_frame, textvariable=self.search_mode_var, 
                                      width=25, state="readonly")
        self.mode_combo['values'] = [
            "0: 仅当前页面",
            "1: 仅标题页翻页", 
            "2: 标题页+内容页",
            "3: 标题页+内容页+深度链接",
            "5: 全面搜索"
        ]
        self.mode_combo.pack(side=tk.LEFT, padx=5)
        
        # 绑定事件，当选择模式时显示说明
        self.mode_combo.bind('<<ComboboxSelected>>', self.show_mode_description)
        
        # 显示当前模式说明的标签
        self.mode_desc_var = tk.StringVar(value="仅搜索论坛标题列表页，翻页但不进入具体帖子")
        ttk.Label(row1_frame, textvariable=self.mode_desc_var, 
                 foreground="blue", font=("Arial", 9)).pack(side=tk.LEFT, padx=10)
        
        # 第二行选项
        row2_frame = ttk.Frame(options_frame)
        row2_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(row2_frame, text="请求延时(秒):").pack(side=tk.LEFT)
        self.delay_var = tk.StringVar(value="2.0")
        self.delay_combo = ttk.Combobox(row2_frame, textvariable=self.delay_var, 
                                       values=["1.5", "2.0", "3.0", "4.0", "5.0"], width=8, state="readonly")
        self.delay_combo.pack(side=tk.LEFT, padx=5)
        
        self.case_sensitive_var = tk.BooleanVar()
        ttk.Checkbutton(row2_frame, text="区分大小写", 
                       variable=self.case_sensitive_var).pack(side=tk.LEFT, padx=20)
        
        ttk.Label(row2_frame, text="编码检测:").pack(side=tk.LEFT, padx=(20, 5))
        self.encoding_var = tk.StringVar(value="自动检测")
        self.encoding_combo = ttk.Combobox(row2_frame, textvariable=self.encoding_var, 
                                         values=["自动检测", "UTF-8", "GBK", "GB2312", "GB18030", 
                                                 "Big5", "ISO-8859-1", "Windows-1252"], width=12, state="readonly")
        self.encoding_combo.pack(side=tk.LEFT, padx=5)
        
        # 第三行选项
        row3_frame = ttk.Frame(options_frame)
        row3_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.include_html_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row3_frame, text="搜索HTML标签内文本", 
                       variable=self.include_html_var).pack(side=tk.LEFT, padx=5)
        
        self.remove_js_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row3_frame, text="移除JavaScript代码", 
                       variable=self.remove_js_var).pack(side=tk.LEFT, padx=20)
        
        self.search_titles_only_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row3_frame, text="仅搜索标题（标题页模式下）", 
                       variable=self.search_titles_only_var).pack(side=tk.LEFT, padx=20)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        self.search_button = ttk.Button(button_frame, text="开始搜索", command=self.start_search, width=15)
        self.search_button.pack(side=tk.LEFT, padx=10)
        
        self.stop_button = ttk.Button(button_frame, text="停止搜索", command=self.stop_search, 
                                     width=15, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=10)
        
        self.clear_button = ttk.Button(button_frame, text="清空结果", command=self.clear_results, width=15)
        self.clear_button.pack(side=tk.LEFT, padx=10)
        
        # 进度和统计区域
        stats_frame = ttk.Frame(main_frame)
        stats_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # 进度显示
        progress_frame = ttk.Frame(stats_frame)
        progress_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(progress_frame, text="状态:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.progress_var = tk.StringVar(value="准备就绪")
        progress_label = ttk.Label(progress_frame, textvariable=self.progress_var, 
                                  foreground="blue", font=("Arial", 10))
        progress_label.pack(side=tk.LEFT, padx=5)
        
        # 统计信息
        self.stats_var = tk.StringVar(value="找到 0 个匹配")
        stats_label = ttk.Label(stats_frame, textvariable=self.stats_var, 
                               foreground="green", font=("Arial", 10, "bold"))
        stats_label.pack(side=tk.RIGHT)
        
        # 结果显示区域
        result_frame = ttk.LabelFrame(main_frame, text="搜索结果", padding="5")
        result_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 创建文本框和滚动条
        self.result_text = scrolledtext.ScrolledText(result_frame, width=120, height=35, 
                                                    font=("Consolas", 9), wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
    
    def show_mode_description(self, event=None):
        """显示搜索模式说明"""
        mode_map = {
            "0: 仅当前页面": "仅搜索当前页面，不跟踪任何链接",
            "1: 仅标题页翻页": "仅搜索论坛标题列表页，翻页但不进入具体帖子",
            "2: 标题页+内容页": "搜索标题列表页并进入帖子内容，但不跟踪帖子内链接",
            "3: 标题页+内容页+深度链接": "搜索标题页、内容页及帖子内分页链接",
            "5: 全面搜索": "深度搜索，包括标题、内容和相关链接"
        }
        selected_mode = self.search_mode_var.get()
        if selected_mode in mode_map:
            self.mode_desc_var.set(mode_map[selected_mode])
        
    def start_search(self):
        url = self.url_entry.get().strip()
        keyword = self.keyword_entry.get().strip()
        
        if not url:
            messagebox.showerror("错误", "请输入目标网址")
            return
            
        if not keyword:
            messagebox.showerror("错误", "请输入关键词")
            return
            
        # 检查中文关键词
        if self.contains_chinese(keyword):
            self.log_message(f"检测到中文关键词: '{keyword}'", "info")
            
        # 重置停止标志
        self.stop_search_flag = False
        self.search_running = True
        
        # 更新按钮状态
        self.search_button.config(state='disabled')
        self.stop_button.config(state='normal')
        
        self.clear_results()
        
        # 在新线程中执行搜索，避免界面冻结
        search_thread = threading.Thread(target=self.perform_search, args=(url, keyword))
        search_thread.daemon = True
        search_thread.start()
        
    def stop_search(self):
        """停止搜索"""
        if self.search_running:
            self.stop_search_flag = True
            self.update_progress("正在停止搜索...")
            self.stop_button.config(state='disabled')
        
    def perform_search(self, start_url, keyword):
        try:
            self.update_progress("正在连接网站...")
            
            # 获取搜索参数
            mode_str = self.search_mode_var.get()
            mode_num = int(mode_str.split(":")[0])  # 提取模式数字
            case_sensitive = self.case_sensitive_var.get()
            delay = float(self.delay_var.get())
            
            # 执行搜索
            results = self.search_website(start_url, keyword, mode_num, case_sensitive, delay)
            
            # 显示结果
            if not self.stop_search_flag:
                self.display_results(results, keyword)
                self.update_progress("搜索完成")
            else:
                self.update_progress("搜索已停止")
                
        except Exception as e:
            self.log_message(f"搜索过程中发生错误: {str(e)}", "error")
            self.update_progress("搜索失败")
        finally:
            # 重置搜索状态
            self.search_running = False
            # 重新启用搜索按钮
            self.root.after(0, lambda: self.search_button.config(state='normal'))
            self.root.after(0, lambda: self.stop_button.config(state='disabled'))
    
    def search_website(self, start_url, keyword, search_mode, case_sensitive, delay):
        """搜索网站内容"""
        visited_urls = set()
        results = []
        
        # 准备关键词用于搜索
        search_keywords = self.prepare_keywords(keyword)
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        page_count = 0
        
        # 根据搜索模式决定初始搜索队列
        if search_mode == 0:
            # 仅当前页面，不跟踪任何链接
            urls_to_visit = [(start_url, 0, "page")]
            self.update_progress("模式0: 仅搜索当前页面")
        elif search_mode == 1:
            # 仅标题页翻页
            urls_to_visit = [(start_url, 0, "title_page")]
            self.update_progress("模式1: 仅搜索标题列表页（翻页不进入帖子）")
        elif search_mode == 2:
            # 标题页+内容页
            urls_to_visit = [(start_url, 0, "title_page")]
            self.update_progress("模式2: 搜索标题列表页和帖子内容")
        else:
            # 其他模式，正常搜索
            urls_to_visit = [(start_url, 0, "page")]
            self.update_progress(f"模式{search_mode}: 深度搜索")
        
        while urls_to_visit and not self.stop_search_flag:
            url, depth, page_type = urls_to_visit.pop(0)
            
            if url in visited_urls:
                continue
                
            try:
                page_count += 1
                self.update_progress(f"正在搜索第 {page_count} 页 ({page_type}): {self.truncate_url(url)}")
                
                # 添加随机延时防止反爬虫
                time.sleep(delay + random.uniform(0, 0.5))
                
                # 获取网页内容
                response = session.get(url, timeout=25)
                
                # 检测或指定编码
                encoding = self.detect_or_specify_encoding(response)
                response.encoding = encoding
                
                if response.status_code != 200:
                    self.log_message(f"页面 {self.truncate_url(url)} 返回状态码: {response.status_code}", "warning")
                    continue
                    
                # 解析网页内容
                page_content = self.parse_page_content(response.text, encoding)
                
                if not page_content:
                    self.log_message(f"页面 {self.truncate_url(url)} 内容为空或解析失败", "warning")
                    continue
                
                # 获取页面标题
                page_title = self.extract_page_title(response.text, encoding)
                
                # 根据页面类型和模式决定搜索策略
                if page_type == "title_page" and self.search_titles_only_var.get() and search_mode <= 1:
                    # 标题页模式下仅搜索标题
                    matches_info = self.search_titles_only(response.text, search_keywords, case_sensitive, encoding)
                else:
                    # 正常搜索内容
                    matches_info = self.search_keywords_in_content(page_content, search_keywords, case_sensitive)
                
                if matches_info['total_matches'] > 0:
                    # 保存结果
                    result_info = {
                        'url': url,
                        'title': page_title,
                        'contexts': matches_info['contexts'],
                        'count': matches_info['total_matches'],
                        'page_num': page_count,
                        'encoding': encoding,
                        'matched_keywords': matches_info['matched_keywords'],
                        'page_type': page_type
                    }
                    results.append(result_info)
                    
                    # 显示单个结果
                    self.display_single_result(result_info)
                
                # 标记为已访问
                visited_urls.add(url)
                
                # 根据搜索模式决定是否查找更多链接
                if search_mode > 0:  # 模式0不收集任何链接
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 根据搜索模式决定收集哪些链接
                    new_urls = []
                    
                    if search_mode == 1:
                        # 模式1: 仅收集标题页的分页链接
                        if page_type == "title_page":
                            # 查找分页链接，使用严格模式
                            pagination_urls = self.find_strict_pagination_links(soup, url, visited_urls)
                            for new_url in pagination_urls:
                                new_urls.append((new_url, depth + 1, "title_page"))
                                
                            self.log_message(f"在标题页找到 {len(pagination_urls)} 个分页链接", "info")
                    
                    elif search_mode == 2:
                        # 模式2: 收集标题页分页链接和内容链接
                        if page_type == "title_page":
                            # 查找分页链接
                            pagination_urls = self.find_pagination_links(soup, url, visited_urls)
                            for new_url in pagination_urls:
                                new_urls.append((new_url, depth + 1, "title_page"))
                            
                            # 查找内容链接（进入帖子）
                            content_urls = self.find_content_links(soup, url, visited_urls)
                            for new_url in content_urls:
                                new_urls.append((new_url, depth + 1, "content_page"))
                                
                            self.log_message(f"在标题页找到 {len(pagination_urls)} 个分页链接和 {len(content_urls)} 个内容链接", "info")
                        else:
                            # 在内容页不收集链接
                            pass
                    
                    elif search_mode >= 3:
                        # 模式3及以上: 正常收集链接
                        # 查找分页链接
                        pagination_urls = self.find_pagination_links(soup, url, visited_urls)
                        # 查找内容链接
                        content_urls = self.find_content_links(soup, url, visited_urls)
                        
                        # 合并链接
                        all_new_urls = list(set(pagination_urls + content_urls))
                        
                        for new_url in all_new_urls:
                            # 判断链接类型
                            if new_url in pagination_urls:
                                # 分页链接保持当前页面类型
                                new_urls.append((new_url, depth + 1, page_type))
                            else:
                                # 内容链接
                                if search_mode >= 3:
                                    new_urls.append((new_url, depth + 1, "content_page"))
                    
                    # 将新链接加入待访问队列
                    for new_url_info in new_urls:
                        new_url, new_depth, new_type = new_url_info
                        if (new_url not in visited_urls and 
                            new_url_info not in urls_to_visit):
                            urls_to_visit.append(new_url_info)
                            
            except requests.exceptions.Timeout:
                self.log_message(f"页面 {self.truncate_url(url)} 请求超时", "warning")
                continue
            except requests.exceptions.RequestException as e:
                self.log_message(f"访问 {self.truncate_url(url)} 时网络错误: {str(e)}", "warning")
                continue
            except Exception as e:
                self.log_message(f"处理 {self.truncate_url(url)} 时出错: {str(e)}", "error")
                continue
                
        return results
    
    def find_strict_pagination_links(self, soup, base_url, visited_urls):
        """严格查找分页链接 - 只识别类似&page=数字的链接"""
        pagination_urls = []
        
        # 解析当前URL
        parsed_base = urlparse(base_url)
        base_query = parse_qs(parsed_base.query)
        
        # 提取当前的page参数值（如果有）
        current_page = None
        for key in ['page', 'p', 'pg', 'paged', 'pn']:
            if key in base_query and base_query[key]:
                try:
                    current_page = int(base_query[key][0])
                    break
                except:
                    continue
        
        # 查找所有链接
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href')
            if not href:
                continue
                
            # 转换为完整URL
            full_url = urljoin(base_url, href)
            
            # 检查是否已访问过
            if full_url in visited_urls:
                continue
            
            # 解析链接URL
            parsed_link = urlparse(full_url)
            
            # 检查是否同一域名
            if parsed_link.netloc != parsed_base.netloc:
                continue
            
            # 检查路径是否相同（允许微小差异）
            if parsed_link.path != parsed_base.path:
                # 路径不同，但可能是分页的另一种形式，如 /page/2/
                if not re.search(r'/page/\d+/', parsed_link.path):
                    continue
            
            # 解析查询参数
            link_query = parse_qs(parsed_link.query)
            
            # 检查是否包含分页参数
            has_page_param = False
            page_param_name = None
            page_value = None
            
            for key in ['page', 'p', 'pg', 'paged', 'pn']:
                if key in link_query and link_query[key]:
                    try:
                        page_value = int(link_query[key][0])
                        has_page_param = True
                        page_param_name = key
                        break
                    except:
                        continue
            
            # 如果没有分页参数，检查路径中的数字
            if not has_page_param:
                match = re.search(r'/page/(\d+)/', parsed_link.path)
                if match:
                    page_value = int(match.group(1))
                    has_page_param = True
                    page_param_name = 'page'
            
            if not has_page_param:
                continue
            
            # 检查其他参数是否相同（除了分页参数）
            base_params_copy = base_query.copy()
            link_params_copy = link_query.copy()
            
            # 移除分页参数进行比较
            for key in ['page', 'p', 'pg', 'paged', 'pn']:
                if key in base_params_copy:
                    del base_params_copy[key]
                if key in link_params_copy:
                    del link_params_copy[key]
            
            # 比较参数
            if base_params_copy != link_params_copy:
                continue
            
            # 检查链接文本是否符合分页特征
            link_text = link.get_text(strip=True)
            
            # 常见的分页文本模式
            page_text_patterns = [
                r'^\d+$',  # 纯数字
                r'^下一页', r'^上一页',
                r'^Next', r'^Prev',
                r'^»', r'^«'
            ]
            
            is_page_text = False
            for pattern in page_text_patterns:
                if re.match(pattern, link_text):
                    is_page_text = True
                    break
            
            # 如果文本不是典型的分页文本，但URL明显是分页，也接受
            if not is_page_text and page_value is not None:
                # 检查当前页和链接页的关系
                if current_page is not None:
                    if abs(page_value - current_page) <= 10:  # 限制在10页范围内
                        is_page_text = True
            
            if is_page_text or page_value is not None:
                # 验证这是一个合理的分页链接
                if self.is_valid_url(full_url, base_url, visited_urls):
                    pagination_urls.append(full_url)
        
        # 去重并排序
        pagination_urls = list(set(pagination_urls))
        
        # 尝试按页码排序
        def extract_page_num(url):
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            
            for key in ['page', 'p', 'pg', 'paged', 'pn']:
                if key in query and query[key]:
                    try:
                        return int(query[key][0])
                    except:
                        pass
            
            # 检查路径中的页码
            match = re.search(r'/page/(\d+)/', parsed.path)
            if match:
                return int(match.group(1))
            
            return 0
        
        pagination_urls.sort(key=extract_page_num)
        
        return pagination_urls
    
    def search_titles_only(self, html_content, keywords, case_sensitive, encoding):
        """仅搜索页面中的标题（适用于论坛列表页）"""
        total_matches = 0
        contexts = []
        matched_keywords = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 首先尝试查找论坛帖子列表
            forum_titles = []
            
            # 常见论坛标题选择器
            title_selectors = [
                'a[href*="thread"]', 'a[href*="forum"]', 'a[href*="post"]',
                '.title a', '.subject a', '.threadtitle a',
                'h3 a', 'h4 a', '.list-subject a',
                '.xst',  # Discuz论坛常见class
                '.s xst',  # Discuz论坛
                '.new a',  # 新帖
                '.common a'  # 普通帖
            ]
            
            for selector in title_selectors:
                elements = soup.select(selector)
                for element in elements:
                    title_text = element.get_text(strip=True)
                    href = element.get('href', '')
                    
                    # 过滤太短的标题和非帖子链接
                    if (title_text and len(title_text) > 3 and 
                        not self.is_pagination_link_text(title_text) and
                        not href.startswith(('#', 'javascript:'))):
                        
                        # 检查是否是帖子链接（排除分页链接）
                        if any(keyword in href.lower() for keyword in ['thread', 'forum', 'post', 'tid=']):
                            forum_titles.append((title_text, href))
            
            # 如果没找到，尝试更通用的方法
            if not forum_titles:
                # 查找所有链接，根据文本长度和URL模式判断
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    title_text = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    # 过滤条件
                    if (len(title_text) >= 5 and len(title_text) <= 200 and
                        not self.is_pagination_link_text(title_text) and
                        not href.startswith(('#', 'javascript:')) and
                        'http' in href and
                        not any(keyword in href.lower() for keyword in ['page=', 'p=', 'logout', 'login'])):
                        
                        forum_titles.append((title_text, href))
            
            # 去重
            unique_titles = []
            seen = set()
            for title, href in forum_titles:
                if title not in seen:
                    seen.add(title)
                    unique_titles.append((title, href))
            
            # 搜索每个标题
            flags = 0 if case_sensitive else re.IGNORECASE
            
            for keyword in keywords:
                escaped_keyword = re.escape(keyword)
                try:
                    pattern = re.compile(escaped_keyword, flags)
                except re.error:
                    # 正则表达式编译失败，使用普通字符串搜索
                    for title, href in unique_titles:
                        if case_sensitive:
                            if keyword in title:
                                total_matches += 1
                                matched_keywords.append(keyword)
                                contexts.append(f"帖子标题: {title} (链接: {href})")
                        else:
                            if keyword.lower() in title.lower():
                                total_matches += 1
                                matched_keywords.append(keyword)
                                contexts.append(f"帖子标题: {title} (链接: {href})")
                    continue
                
                # 使用正则表达式搜索
                for title, href in unique_titles:
                    matches = list(pattern.finditer(title))
                    if matches:
                        total_matches += len(matches)
                        if keyword not in matched_keywords:
                            matched_keywords.append(keyword)
                        
                        # 高亮显示匹配的关键词
                        highlighted_title = title
                        for match in reversed(matches):  # 反向替换避免索引问题
                            start, end = match.span()
                            matched_text = title[start:end]
                            highlighted_title = highlighted_title[:start] + f"【{matched_text}】" + highlighted_title[end:]
                        
                        contexts.append(f"帖子标题: {highlighted_title} (链接: {href})")
            
        except Exception as e:
            self.log_message(f"搜索标题时出错: {str(e)}", "warning")
        
        return {
            'total_matches': total_matches,
            'contexts': contexts[:20],  # 只显示前20个匹配
            'matched_keywords': list(set(matched_keywords))
        }
    
    def is_pagination_link_text(self, text):
        """判断文本是否是分页链接文本"""
        text = text.strip().lower()
        
        # 常见分页文本
        pagination_texts = [
            '上一页', '下一页', '首页', '尾页', '末页',
            'prev', 'next', 'first', 'last',
            '«', '»', '<', '>',
            'page', 'pages', 'pager'
        ]
        
        if text in pagination_texts:
            return True
        
        # 纯数字（可能是页码）
        if re.match(r'^\d+$', text):
            return True
        
        return False
    
    def prepare_keywords(self, keyword_input):
        """准备关键词列表，支持多个关键词用空格或逗号分隔"""
        # 分割关键词
        separators = [' ', ',', '，', ';', '；']
        keywords = [keyword_input]
        
        for sep in separators:
            if sep in keyword_input:
                # 分割并去除空白字符
                keywords = [k.strip() for k in keyword_input.split(sep) if k.strip()]
                break
        
        # 去除重复的关键词
        unique_keywords = []
        for kw in keywords:
            if kw not in unique_keywords:
                unique_keywords.append(kw)
                
        return unique_keywords
    
    def detect_or_specify_encoding(self, response):
        """检测或指定网页编码"""
        user_encoding = self.encoding_var.get()
        
        if user_encoding != "自动检测":
            return user_encoding
        
        # 自动检测编码
        encodings_to_try = []
        
        # 1. 首先尝试从HTTP头获取
        if response.encoding:
            encodings_to_try.append(response.encoding)
        
        # 2. 从HTML meta标签获取
        meta_encoding = self.get_encoding_from_html(response.content[:5000])
        if meta_encoding:
            encodings_to_try.append(meta_encoding)
        
        # 3. 使用chardet检测
        try:
            detected = chardet.detect(response.content[:10000])
            if detected['encoding'] and detected['confidence'] > 0.7:
                encodings_to_try.append(detected['encoding'])
        except:
            pass
        
        # 4. 添加常见中文编码
        common_encodings = ['UTF-8', 'GBK', 'GB2312', 'GB18030', 'Big5', 'ISO-8859-1', 'Windows-1252']
        encodings_to_try.extend(common_encodings)
        
        # 去重
        unique_encodings = []
        for enc in encodings_to_try:
            if enc and enc not in unique_encodings:
                unique_encodings.append(enc)
        
        # 尝试每个编码
        for encoding in unique_encodings:
            try:
                # 尝试用该编码解码
                decoded = response.content.decode(encoding, errors='ignore')
                # 如果成功解码且包含常见中文字符，认为是正确编码
                if self.contains_chinese(decoded) or len(decoded) > 100:
                    return encoding
            except:
                continue
        
        # 如果所有编码都失败，使用UTF-8作为后备
        return 'UTF-8'
    
    def get_encoding_from_html(self, html_bytes):
        """从HTML meta标签获取编码"""
        try:
            # 转换为字符串进行查找
            html_str = html_bytes.decode('ascii', errors='ignore')
            
            # 查找charset声明
            charset_patterns = [
                r'charset=["\']?([\w-]+)["\']?',
                r'encoding=["\']?([\w-]+)["\']?'
            ]
            
            for pattern in charset_patterns:
                match = re.search(pattern, html_str, re.IGNORECASE)
                if match:
                    encoding = match.group(1).upper()
                    # 标准化编码名称
                    if encoding == 'GB2312':
                        encoding = 'GBK'
                    elif encoding == 'UTF8':
                        encoding = 'UTF-8'
                    return encoding
        except:
            pass
        
        return None
    
    def parse_page_content(self, html_content, encoding):
        """解析网页内容，提取可搜索的文本"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除脚本和样式
            if self.remove_js_var.get():
                for script in soup(["script", "style", "noscript"]):
                    script.decompose()
            
            # 获取文本内容
            if self.include_html_var.get():
                # 获取所有文本，包括HTML标签内的
                text = soup.get_text(separator=' ', strip=True)
            else:
                # 只获取可见文本
                for invisible in soup(['style', 'script', 'head', 'title', 'meta', '[document]']):
                    invisible.decompose()
                text = soup.get_text(separator=' ', strip=True)
            
            # 处理HTML实体
            text = unescape(text)
            
            # 移除多余空白字符
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
            
        except Exception as e:
            self.log_message(f"解析页面内容时出错: {str(e)}", "warning")
            return ""
    
    def search_keywords_in_content(self, content, keywords, case_sensitive):
        """在内容中搜索关键词"""
        total_matches = 0
        contexts = []
        matched_keywords = []
        
        flags = 0 if case_sensitive else re.IGNORECASE
        
        for keyword in keywords:
            # 对关键词进行转义，确保特殊字符被正确处理
            escaped_keyword = re.escape(keyword)
            
            # 编译正则表达式
            try:
                pattern = re.compile(escaped_keyword, flags)
            except re.error:
                # 如果正则表达式编译失败，使用普通字符串搜索
                if case_sensitive:
                    matches = content.count(keyword)
                else:
                    matches = content.lower().count(keyword.lower())
                
                if matches > 0:
                    total_matches += matches
                    matched_keywords.append(keyword)
                    # 找到第一个匹配的上下文
                    if case_sensitive:
                        idx = content.find(keyword)
                    else:
                        idx = content.lower().find(keyword.lower())
                    
                    if idx != -1:
                        start = max(0, idx - 100)
                        end = min(len(content), idx + len(keyword) + 100)
                        context = content[start:end].replace('\n', ' ').strip()
                        highlight_context = context.replace(
                            keyword, f"【{keyword}】" if case_sensitive else 
                            f"【{content[idx:idx+len(keyword)]}】"
                        )
                        contexts.append(f"关键词 '{keyword}' 匹配 {matches} 次: ...{highlight_context}...")
                continue
            
            # 使用正则表达式搜索
            matches = list(pattern.finditer(content))
            
            if matches:
                total_matches += len(matches)
                matched_keywords.append(keyword)
                
                # 获取前3个匹配的上下文
                for i, match in enumerate(matches[:3]):
                    start = max(0, match.start() - 100)
                    end = min(len(content), match.end() + 100)
                    context = content[start:end].replace('\n', ' ').strip()
                    
                    # 高亮显示匹配的关键词
                    highlighted = content[start:end]
                    highlighted = highlighted[:match.start()-start] + f"【{content[match.start():match.end()]}】" + highlighted[match.end()-start:]
                    
                    contexts.append(f"关键词 '{keyword}' 匹配 {i+1}: ...{highlighted}...")
        
        return {
            'total_matches': total_matches,
            'contexts': contexts,
            'matched_keywords': matched_keywords
        }
    
    def extract_page_title(self, html_content, encoding):
        """提取页面标题"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            title_tag = soup.find('title')
            
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
                # 处理编码问题
                if isinstance(title, bytes):
                    title = title.decode(encoding, errors='ignore')
                return title[:100]  # 限制标题长度
        except:
            pass
        
        return "无标题"
    
    def truncate_url(self, url, max_length=50):
        """缩短URL显示"""
        if len(url) <= max_length:
            return url
        return url[:max_length//2] + "..." + url[-max_length//2:]
    
    def find_pagination_links(self, soup, base_url, visited_urls):
        """查找分页链接（通用方法）"""
        pagination_urls = []
        
        # 查找常见的分页元素
        pagination_selectors = [
            '.pagination a',
            '.page-numbers a',
            '.pager a',
            '.pages a',
            'a.next',
            'a.prev',
            'a.page',
            '.next-page a',
            '.previous-page a',
            '.pagination li a',
            '.pager li a',
            '.page-links a',
            '.wp-pagenavi a'
        ]
        
        for selector in pagination_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self.is_valid_url(full_url, base_url, visited_urls):
                        pagination_urls.append(full_url)
        
        # 查找包含分页参数的链接
        page_patterns = [
            r'[?&](page|paged|pg|p)=\d+',
            r'[?&]page[ds]?=\d+',
            r'/\d+/$',  # 以数字结尾的路径，如 /page/2/
            r'/page/\d+/'
        ]
        
        for pattern in page_patterns:
            page_links = soup.find_all('a', href=re.compile(pattern))
            for link in page_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self.is_valid_url(full_url, base_url, visited_urls):
                        pagination_urls.append(full_url)
        
        # 查找中文分页文本
        chinese_page_texts = ['下一页', '上一页', '下一页>', '<上一页', '下页', '上页', 
                             '后页', '前页', '最后一页', '第一页', '末页', '首页']
        
        for text in chinese_page_texts:
            next_links = soup.find_all('a', string=text)
            for link in next_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self.is_valid_url(full_url, base_url, visited_urls):
                        pagination_urls.append(full_url)
        
        # 查找数字分页（1, 2, 3...）
        num_links = soup.find_all('a', string=re.compile(r'^\d+$'))
        for link in num_links:
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                if self.is_valid_url(full_url, base_url, visited_urls):
                    pagination_urls.append(full_url)
        
        return list(set(pagination_urls))  # 去重
    
    def find_content_links(self, soup, base_url, visited_urls):
        """查找内容链接"""
        content_urls = []
        
        # 查找可能是文章或内容的链接
        content_selectors = [
            'a[href*="thread"]',
            'a[href*="post"]',
            'a[href*="article"]',
            'a[href*="topic"]',
            'a[href*="view"]',
            'a[href*="read"]',
            'a[href*="bbs"]',
            'a[href*="forum"]',
            '.title a',
            '.content a',
            '.post-title a',
            '.thread-title a',
            '.article-title a',
            'h3 a',
            'h2 a',
            '.list-item a',
            '.post a',
            '.entry-title a'
        ]
        
        for selector in content_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self.is_valid_url(full_url, base_url, visited_urls):
                        content_urls.append(full_url)
        
        # 查找中文论坛常见链接
        chinese_link_texts = ['查看全文', '阅读更多', '详细内容', '全文', '更多', '回复', '评论']
        
        for text in chinese_link_texts:
            text_links = soup.find_all('a', string=re.compile(text))
            for link in text_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self.is_valid_url(full_url, base_url, visited_urls):
                        content_urls.append(full_url)
        
        # 查找可能包含内容的链接（通过链接文本长度判断）
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href')
            link_text = link.get_text(strip=True)
            
            if href and link_text and len(link_text) > 10 and len(link_text) < 200:
                # 链接文本较长，可能是内容链接
                full_url = urljoin(base_url, href)
                if (self.is_valid_url(full_url, base_url, visited_urls) and
                    not self.is_file_link(full_url) and
                    not re.search(r'\.(css|js|jpg|png|gif|pdf|zip|rar)$', full_url, re.IGNORECASE)):
                    
                    # 排除常见非内容链接
                    exclude_patterns = ['首页', '主页', 'home', 'login', '注册', 'signup', '登录']
                    if not any(pattern in link_text for pattern in exclude_patterns):
                        content_urls.append(full_url)
        
        return list(set(content_urls))  # 去重
    
    def is_valid_url(self, url, base_url, visited_urls):
        """检查URL是否有效"""
        if url in visited_urls:
            return False
        
        if not url.startswith(('http://', 'https://')):
            return False
        
        if not self.is_same_domain(base_url, url):
            return False
        
        if self.is_file_link(url):
            return False
        
        # 排除一些常见的不需要爬取的URL
        exclude_patterns = [
            r'logout',
            r'login',
            r'register',
            r'signup',
            r'admin',
            r'logout',
            r'edit',
            r'delete',
            r'\.rss$',
            r'\.xml$',
            r'feed',
            r'javascript:',
            r'^#'
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        return True
    
    def is_same_domain(self, url1, url2):
        """检查两个URL是否在同一域名下"""
        try:
            domain1 = urlparse(url1).netloc
            domain2 = urlparse(url2).netloc
            return domain1 == domain2
        except:
            return False
    
    def is_file_link(self, url):
        """检查是否是文件链接"""
        file_extensions = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico',
            '.zip', '.rar', '.7z', '.tar', '.gz',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv',
            '.css', '.js', '.exe', '.dmg', '.iso'
        ]
        url_lower = url.lower()
        return any(url_lower.endswith(ext) for ext in file_extensions)
    
    def contains_chinese(self, text):
        """检查文本是否包含中文"""
        # 中文Unicode范围
        chinese_ranges = [
            (0x4E00, 0x9FFF),    # 基本汉字
            (0x3400, 0x4DBF),    # 扩展A
            (0x20000, 0x2A6DF),  # 扩展B
            (0x2A700, 0x2B73F),  # 扩展C
            (0x2B740, 0x2B81F),  # 扩展D
            (0x2B820, 0x2CEAF),  # 扩展E
            (0xF900, 0xFAFF),    # 兼容汉字
            (0x2F800, 0x2FA1F)   # 兼容扩展
        ]
        
        for char in text:
            code = ord(char)
            for start, end in chinese_ranges:
                if start <= code <= end:
                    return True
        
        return False
    
    def display_single_result(self, result):
        """显示单个搜索结果"""
        separator = "=" * 90
        result_text = f"\n{separator}\n"
        
        # 显示页面类型
        page_type_desc = {
            "page": "普通页面",
            "title_page": "标题列表页",
            "content_page": "内容页面"
        }
        page_type = page_type_desc.get(result['page_type'], result['page_type'])
        
        result_text += f"页面 #{result['page_num']} ({page_type}): {result['title']}\n"
        result_text += f"网址: {result['url']}\n"
        result_text += f"编码: {result['encoding']}\n"
        result_text += f"匹配关键词: {', '.join(result['matched_keywords'])}\n"
        result_text += f"匹配数量: {result['count']} 个\n"
        
        for context in result['contexts']:
            result_text += f"{context}\n"
        
        result_text += f"{separator}\n"
        
        self.log_message(result_text, "result")
        
        # 更新统计信息
        self.root.after(0, lambda: self.stats_var.set(f"已搜索 {result['page_num']} 页，找到 {result['count']} 个匹配"))
    
    def display_results(self, results, keyword):
        """显示所有搜索结果汇总"""
        if not results:
            self.log_message("没有找到匹配的结果", "info")
            self.stats_var.set("找到 0 个匹配")
            return
        
        total_matches = sum(result['count'] for result in results)
        total_pages = len(results)
        
        # 按页面类型统计
        page_types = {}
        for result in results:
            page_type = result['page_type']
            page_types[page_type] = page_types.get(page_type, 0) + 1
        
        summary = "\n" + "=" * 90
        summary += f"\n✨ 搜索完成！\n"
        summary += f"搜索模式: {self.search_mode_var.get()}\n"
        summary += f"关键词: '{keyword}'\n"
        summary += f"总搜索页数: {total_pages}\n"
        
        # 显示页面类型统计
        if page_types:
            summary += "页面类型统计:\n"
            type_desc = {
                "page": "普通页面",
                "title_page": "标题列表页",
                "content_page": "内容页面"
            }
            for page_type, count in page_types.items():
                desc = type_desc.get(page_type, page_type)
                summary += f"  {desc}: {count} 页\n"
        
        summary += f"总匹配数量: {total_matches}\n"
        
        # 按关键词统计
        keyword_stats = {}
        for result in results:
            for kw in result['matched_keywords']:
                keyword_stats[kw] = keyword_stats.get(kw, 0) + result['count']
        
        if keyword_stats:
            summary += "关键词匹配统计:\n"
            for kw, count in keyword_stats.items():
                summary += f"  '{kw}': {count} 次\n"
        
        summary += "=" * 90 + "\n"
        
        self.log_message(summary, "info")
        self.stats_var.set(f"在 {total_pages} 个页面中找到 {total_matches} 个匹配")
    
    def log_message(self, message, msg_type="info"):
        """在文本框中添加消息"""
        def add_message():
            # 根据消息类型设置颜色
            if msg_type == "error":
                tag = "error"
                self.result_text.tag_config(tag, foreground="red", font=("Consolas", 9, "bold"))
            elif msg_type == "warning":
                tag = "warning"
                self.result_text.tag_config(tag, foreground="orange")
            elif msg_type == "result":
                tag = "result"
                self.result_text.tag_config(tag, foreground="darkblue")
            elif msg_type == "info":
                tag = "info"
                self.result_text.tag_config(tag, foreground="darkgreen", font=("Consolas", 9, "bold"))
            else:
                tag = "normal"
                self.result_text.tag_config(tag, foreground="black")
            
            # 插入消息
            self.result_text.insert(tk.END, message, (tag,))
            self.result_text.see(tk.END)
            self.root.update_idletasks()
        
        self.root.after(0, add_message)
    
    def update_progress(self, message):
        """更新进度消息"""
        self.root.after(0, lambda: self.progress_var.set(message))
    
    def clear_results(self):
        """清空结果文本框"""
        self.result_text.delete(1.0, tk.END)
        self.stats_var.set("找到 0 个匹配")
        self.progress_var.set("准备就绪")

def main():
    root = tk.Tk()
    app = WebSearchGUI(root)
    
    # 设置窗口图标和最小尺寸
    root.minsize(950, 700)
    
    # 绑定关闭窗口事件
    def on_closing():
        if app.search_running:
            app.stop_search()
            root.after(100, root.destroy)
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()