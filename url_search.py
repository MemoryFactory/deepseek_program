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
        
        # 网址输入框
        self.url_entry = ttk.Entry(url_frame, width=70)
        self.url_entry.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        self.url_entry.insert(0, "https://")
        
        # 清除和粘贴按钮
        button_container = ttk.Frame(url_frame)
        button_container.grid(row=0, column=2, padx=(5, 0))
        
        # 清除按钮
        self.clear_url_button = ttk.Button(
            button_container, 
            text="清除", 
            command=self.clear_url,
            width=6
        )
        self.clear_url_button.pack(side=tk.LEFT, padx=(0, 2))
        
        # 粘贴按钮
        self.paste_url_button = ttk.Button(
            button_container, 
            text="粘贴", 
            command=self.paste_to_url,
            width=6
        )
        self.paste_url_button.pack(side=tk.LEFT)
        
        # 关键词输入区域
        keyword_frame = ttk.Frame(main_frame)
        keyword_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(keyword_frame, text="关键词:").grid(row=0, column=0, sticky=tk.W)
        
        # 关键词输入框
        self.keyword_entry = ttk.Entry(keyword_frame, width=70)
        self.keyword_entry.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        
        # 关键词清除和粘贴按钮
        keyword_button_container = ttk.Frame(keyword_frame)
        keyword_button_container.grid(row=0, column=2, padx=(5, 0))
        
        # 关键词清除按钮
        self.clear_keyword_button = ttk.Button(
            keyword_button_container, 
            text="清除", 
            command=self.clear_keyword,
            width=6
        )
        self.clear_keyword_button.pack(side=tk.LEFT, padx=(0, 2))
        
        # 关键词粘贴按钮
        self.paste_keyword_button = ttk.Button(
            keyword_button_container, 
            text="粘贴", 
            command=self.paste_to_keyword,
            width=6
        )
        self.paste_keyword_button.pack(side=tk.LEFT)
        
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
        self.mode_desc_var = tk.StringVar(value="仅搜索论坛标题列表页，通过页码+1方式翻页")
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
        
        ttk.Label(row2_frame, text="最大翻页:").pack(side=tk.LEFT, padx=(20, 5))
        self.max_pages_var = tk.StringVar(value="20")
        self.max_pages_combo = ttk.Combobox(row2_frame, textvariable=self.max_pages_var,
                                           values=["10", "20", "50", "100", "200"], width=8, state="readonly")
        self.max_pages_combo.pack(side=tk.LEFT, padx=5)
        
        self.case_sensitive_var = tk.BooleanVar()
        ttk.Checkbutton(row2_frame, text="区分大小写", 
                       variable=self.case_sensitive_var).pack(side=tk.LEFT, padx=20)
        
        # 第三行选项
        row3_frame = ttk.Frame(options_frame)
        row3_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(row3_frame, text="编码检测:").pack(side=tk.LEFT)
        self.encoding_var = tk.StringVar(value="自动检测")
        self.encoding_combo = ttk.Combobox(row3_frame, textvariable=self.encoding_var, 
                                         values=["自动检测", "UTF-8", "GBK", "GB2312", "GB18030", 
                                                 "Big5", "ISO-8859-1", "Windows-1252"], width=12, state="readonly")
        self.encoding_combo.pack(side=tk.LEFT, padx=5)
        
        self.include_html_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row3_frame, text="搜索HTML标签内文本", 
                       variable=self.include_html_var).pack(side=tk.LEFT, padx=20)
        
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
        
        # 绑定快捷键
        self.setup_shortcuts()
    
    def setup_shortcuts(self):
        """设置快捷键"""
        # 网址输入框的快捷键
        self.url_entry.bind('<Control-a>', self.select_all_text)
        self.url_entry.bind('<Control-c>', self.copy_text)
        self.url_entry.bind('<Control-v>', self.paste_to_url_event)
        
        # 关键词输入框的快捷键
        self.keyword_entry.bind('<Control-a>', self.select_all_text)
        self.keyword_entry.bind('<Control-c>', self.copy_text)
        self.keyword_entry.bind('<Control-v>', self.paste_to_keyword_event)
        
        # 窗口级快捷键
        self.root.bind('<Control-l>', lambda e: self.clear_url())
        self.root.bind('<Control-p>', lambda e: self.paste_to_url())
        self.root.bind('<Control-k>', lambda e: self.clear_keyword())
        self.root.bind('<Control-o>', lambda e: self.paste_to_keyword())
        self.root.bind('<F5>', lambda e: self.start_search())
        self.root.bind('<Escape>', lambda e: self.stop_search())
    
    def select_all_text(self, event):
        """全选文本"""
        event.widget.select_range(0, tk.END)
        return "break"
    
    def copy_text(self, event):
        """复制文本"""
        try:
            selected_text = event.widget.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except:
            pass
        return "break"
    
    def paste_to_url_event(self, event):
        """粘贴到网址输入框（事件处理）"""
        self.paste_to_url()
        return "break"
    
    def paste_to_keyword_event(self, event):
        """粘贴到关键词输入框（事件处理）"""
        self.paste_to_keyword()
        return "break"
    
    def clear_url(self):
        """清空网址输入框"""
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, "https://")
        self.url_entry.focus_set()
        
    def clear_keyword(self):
        """清空关键词输入框"""
        self.keyword_entry.delete(0, tk.END)
        self.keyword_entry.focus_set()
    
    def paste_to_url(self):
        """将剪贴板内容粘贴到网址输入框"""
        try:
            # 获取剪贴板内容
            clipboard_text = self.root.clipboard_get()
            if clipboard_text:
                # 清空输入框
                self.url_entry.delete(0, tk.END)
                # 插入剪贴板内容
                self.url_entry.insert(0, clipboard_text)
                self.url_entry.focus_set()
        except tk.TclError:
            # 剪贴板为空或无法访问
            pass
    
    def paste_to_keyword(self):
        """将剪贴板内容粘贴到关键词输入框"""
        try:
            # 获取剪贴板内容
            clipboard_text = self.root.clipboard_get()
            if clipboard_text:
                # 清空输入框
                self.keyword_entry.delete(0, tk.END)
                # 插入剪贴板内容
                self.keyword_entry.insert(0, clipboard_text)
                self.keyword_entry.focus_set()
        except tk.TclError:
            # 剪贴板为空或无法访问
            pass
    
    def show_mode_description(self, event=None):
        """显示搜索模式说明"""
        mode_map = {
            "0: 仅当前页面": "仅搜索当前页面，不跟踪任何链接",
            "1: 仅标题页翻页": "仅搜索论坛标题列表页，通过页码+1方式翻页",
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
            max_pages = int(self.max_pages_var.get())
            
            # 执行搜索
            results = self.search_website(start_url, keyword, mode_num, case_sensitive, delay, max_pages)
            
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
    
    def search_website(self, start_url, keyword, search_mode, case_sensitive, delay, max_pages):
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
        
        # 根据搜索模式决定搜索方式
        if search_mode == 0:
            # 仅当前页面，不跟踪任何链接
            self.update_progress("模式0: 仅搜索当前页面")
            urls_to_visit = [(start_url, 0, "page")]
            
        elif search_mode == 1:
            # 仅标题页翻页 - 使用简单页码累加
            self.update_progress("模式1: 仅搜索标题列表页（页码+1方式翻页）")
            
            # 获取起始页码
            start_page = self.extract_page_number(start_url)
            if start_page is None:
                start_page = 1
                self.log_message(f"起始URL未检测到页码，从第1页开始", "info")
            
            # 只添加起始页面，后续通过页码累加生成
            urls_to_visit = [(start_url, 0, "title_page")]
            
        elif search_mode == 2:
            # 标题页+内容页
            self.update_progress("模式2: 搜索标题列表页和帖子内容")
            urls_to_visit = [(start_url, 0, "title_page")]
            
        else:
            # 其他模式，正常搜索
            self.update_progress(f"模式{search_mode}: 深度搜索")
            urls_to_visit = [(start_url, 0, "page")]
        
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
                    
                    # 在模式1下，如果访问失败，停止翻页
                    if search_mode == 1 and page_type == "title_page":
                        current_page = self.extract_page_number(url)
                        self.log_message(f"第{current_page}页访问失败，停止翻页", "info")
                        continue
                    else:
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
                    
                    if search_mode == 1:
                        # 模式1: 通过页码+1方式翻页，不检查页面内的任何链接
                        if page_type == "title_page":
                            current_page = self.extract_page_number(url)
                            if current_page is None:
                                current_page = 1
                            
                            next_page = current_page + 1
                            
                            # 检查是否超过最大翻页数
                            if next_page > max_pages:
                                self.log_message(f"已达到最大翻页数 {max_pages}，停止翻页", "info")
                            else:
                                # 生成下一页URL
                                next_url = self.generate_next_page_url(url, current_page, next_page)
                                if next_url and next_url not in visited_urls:
                                    # 简单验证URL格式
                                    if self.is_valid_url_format(next_url):
                                        urls_to_visit.append((next_url, depth + 1, "title_page"))
                                        self.log_message(f"生成下一页: 第{next_page}页", "info")
                                    else:
                                        self.log_message(f"下一页URL格式无效，停止翻页", "info")
                    
                    elif search_mode == 2:
                        # 模式2: 收集标题页分页链接和内容链接
                        if page_type == "title_page":
                            soup = BeautifulSoup(response.text, 'html.parser')
                            
                            # 查找内容链接（进入帖子）
                            content_urls = self.find_content_links(soup, url, visited_urls)
                            for new_url in content_urls:
                                if new_url not in visited_urls:
                                    urls_to_visit.append((new_url, depth + 1, "content_page"))
                                    
                            self.log_message(f"在标题页找到 {len(content_urls)} 个内容链接", "info")
                        else:
                            # 在内容页不收集链接
                            pass
                    
                    elif search_mode >= 3:
                        # 模式3及以上: 正常收集链接
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 查找分页链接
                        pagination_urls = self.find_pagination_links(soup, url, visited_urls)
                        # 查找内容链接
                        content_urls = self.find_content_links(soup, url, visited_urls)
                        
                        # 合并链接
                        all_new_urls = list(set(pagination_urls + content_urls))
                        
                        for new_url in all_new_urls:
                            if new_url not in visited_urls:
                                # 判断链接类型
                                if new_url in pagination_urls:
                                    # 分页链接保持当前页面类型
                                    urls_to_visit.append((new_url, depth + 1, page_type))
                                else:
                                    # 内容链接
                                    if search_mode >= 3:
                                        urls_to_visit.append((new_url, depth + 1, "content_page"))
                            
            except requests.exceptions.Timeout:
                self.log_message(f"页面 {self.truncate_url(url)} 请求超时", "warning")
                if search_mode == 1 and page_type == "title_page":
                    # 在模式1下，如果超时，停止翻页
                    current_page = self.extract_page_number(url)
                    self.log_message(f"第{current_page}页请求超时，停止翻页", "info")
                continue
            except requests.exceptions.RequestException as e:
                self.log_message(f"访问 {self.truncate_url(url)} 时网络错误: {str(e)}", "warning")
                if search_mode == 1 and page_type == "title_page":
                    # 在模式1下，如果网络错误，停止翻页
                    current_page = self.extract_page_number(url)
                    self.log_message(f"第{current_page}页网络错误，停止翻页", "info")
                continue
            except Exception as e:
                self.log_message(f"处理 {self.truncate_url(url)} 时出错: {str(e)}", "error")
                continue
                
        return results
    
    def is_valid_url_format(self, url):
        """简单检查URL格式是否有效"""
        if not url.startswith(('http://', 'https://')):
            return False
        
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def extract_page_number(self, url):
        """从URL中提取页码数字"""
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        
        # 检查查询参数中的页码（常见分页参数）
        page_param_names = ['page', 'p', 'pg', 'paged', 'pn', 'PAGEN_1', 'currentpage']
        for key in page_param_names:
            if key in query and query[key]:
                try:
                    return int(query[key][0])
                except:
                    continue
        
        # 如果没有找到页码，检查URL是否有数字模式
        # 常见模式：/page/2/, /2/, -2.html 等
        patterns = [
            r'/page/(\d+)/',          # /page/2/
            r'/(\d+)/$',              # /2/
            r'[-_](\d+)\.(html|htm|php|aspx)$',  # -2.html
            r'/(\d+)$',               # /2
        ]
        
        for pattern in patterns:
            match = re.search(pattern, parsed.path)
            if match:
                try:
                    return int(match.group(1))
                except:
                    continue
        
        # 如果没有找到任何页码，返回None
        return None
    
    def generate_next_page_url(self, current_url, current_page, next_page):
        """生成下一页的URL"""
        parsed = urlparse(current_url)
        query = parse_qs(parsed.query)
        
        # 查找当前使用的分页参数
        page_param = None
        page_param_names = ['page', 'p', 'pg', 'paged', 'pn', 'PAGEN_1', 'currentpage']
        
        for key in page_param_names:
            if key in query and query[key]:
                page_param = key
                break
        
        if page_param:
            # 更新分页参数
            query[page_param] = [str(next_page)]
            
            # 重建查询字符串
            new_query = '&'.join([f"{k}={v[0]}" for k, v in query.items()])
            
            # 重建URL
            new_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
            
            return new_url
        else:
            # 如果没有分页参数，检查是否是路径分页
            path = parsed.path
            
            # 尝试替换路径中的数字分页（如/page/2/）
            new_path = re.sub(r'/page/(\d+)/', f'/page/{next_page}/', path)
            if new_path != path:
                return urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    new_path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
            
            # 尝试替换其他路径模式中的数字（如forum-1-2.html）
            new_path = re.sub(r'[-_](\d+)\.(html|htm|php|aspx)$', f'-{next_page}.html', path)
            if new_path != path:
                return urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    new_path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
            
            # 尝试替换路径末尾的数字（如/forum/2）
            new_path = re.sub(r'/(\d+)/?$', f'/{next_page}', path)
            if new_path != path:
                return urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    new_path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
            
            # 如果都不是，添加page查询参数（最简单的方法）
            if parsed.query:
                new_query = f"{parsed.query}&page={next_page}"
            else:
                new_query = f"page={next_page}"
            
            return urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
    
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
                        
                        forum_titles.append((title_text, href))
            
            # 搜索每个标题
            flags = 0 if case_sensitive else re.IGNORECASE
            
            for keyword in keywords:
                escaped_keyword = re.escape(keyword)
                try:
                    pattern = re.compile(escaped_keyword, flags)
                except re.error:
                    # 正则表达式编译失败，使用普通字符串搜索
                    for title, href in forum_titles:
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
                for title, href in forum_titles:
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
        """查找分页链接（用于模式3及以上）"""
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
                    if self.is_valid_url_format(full_url) and full_url not in visited_urls:
                        pagination_urls.append(full_url)
        
        return list(set(pagination_urls))
    
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
                    if self.is_valid_url_format(full_url) and full_url not in visited_urls:
                        content_urls.append(full_url)
        
        return list(set(content_urls))
    
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