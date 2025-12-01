import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import threading
from collections import Counter

class WebSearchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("网页关键词搜索工具")
        self.root.geometry("800x600")
        
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
        self.url_entry = ttk.Entry(url_frame, width=60)
        self.url_entry.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        
        # 关键词输入区域
        keyword_frame = ttk.Frame(main_frame)
        keyword_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(keyword_frame, text="关键词:").grid(row=0, column=0, sticky=tk.W)
        self.keyword_entry = ttk.Entry(keyword_frame, width=60)
        self.keyword_entry.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        
        # 搜索选项区域
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(options_frame, text="搜索选项:").grid(row=0, column=0, sticky=tk.W)
        
        self.search_depth_var = tk.StringVar(value="1")
        depth_frame = ttk.Frame(options_frame)
        depth_frame.grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(depth_frame, text="搜索深度:").pack(side=tk.LEFT)
        self.depth_combo = ttk.Combobox(depth_frame, textvariable=self.search_depth_var, 
                                       values=["1", "2", "3", "5", "10"], width=5)
        self.depth_combo.pack(side=tk.LEFT, padx=5)
        
        self.case_sensitive_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="区分大小写", 
                       variable=self.case_sensitive_var).grid(row=0, column=2, padx=10)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.search_button = ttk.Button(button_frame, text="开始搜索", command=self.start_search)
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(button_frame, text="清空结果", command=self.clear_results)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # 进度显示
        self.progress_var = tk.StringVar(value="准备就绪")
        ttk.Label(main_frame, textvariable=self.progress_var).grid(row=4, column=0, columnspan=2, pady=5)
        
        # 结果显示区域
        result_frame = ttk.Frame(main_frame)
        result_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 创建文本框和滚动条
        self.result_text = scrolledtext.ScrolledText(result_frame, width=80, height=25)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # 统计信息
        self.stats_var = tk.StringVar(value="找到 0 个匹配")
        ttk.Label(main_frame, textvariable=self.stats_var).grid(row=6, column=0, columnspan=2, pady=5)
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
    def start_search(self):
        url = self.url_entry.get().strip()
        keyword = self.keyword_entry.get().strip()
        
        if not url:
            messagebox.showerror("错误", "请输入目标网址")
            return
            
        if not keyword:
            messagebox.showerror("错误", "请输入关键词")
            return
            
        # 禁用搜索按钮，防止重复点击
        self.search_button.config(state='disabled')
        self.clear_results()
        
        # 在新线程中执行搜索，避免界面冻结[citation:5]
        search_thread = threading.Thread(target=self.perform_search, args=(url, keyword))
        search_thread.daemon = True
        search_thread.start()
        
    def perform_search(self, start_url, keyword):
        try:
            self.update_progress("正在连接网站...")
            
            # 获取搜索参数
            max_depth = int(self.search_depth_var.get())
            case_sensitive = self.case_sensitive_var.get()
            
            # 执行搜索
            results = self.search_website(start_url, keyword, max_depth, case_sensitive)
            
            # 显示结果
            self.display_results(results, keyword)
            
            self.update_progress("搜索完成")
            
        except Exception as e:
            self.log_message(f"搜索过程中发生错误: {str(e)}")
            self.update_progress("搜索失败")
        finally:
            # 重新启用搜索按钮
            self.root.after(0, lambda: self.search_button.config(state='normal'))
            
    def search_website(self, start_url, keyword, max_depth, case_sensitive):
        """搜索网站内容[citation:7]"""
        visited_urls = set()
        results = []
        urls_to_visit = [(start_url, 0)]  # (url, depth)
        
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(keyword), flags)
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        while urls_to_visit:
            url, depth = urls_to_visit.pop(0)
            
            if url in visited_urls or depth > max_depth:
                continue
                
            try:
                self.update_progress(f"正在搜索: {url}")
                
                response = session.get(url, timeout=10)
                response.encoding = 'utf-8'
                
                if response.status_code != 200:
                    continue
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 搜索关键词[citation:5]
                text_content = soup.get_text()
                matches = list(pattern.finditer(text_content))
                
                if matches:
                    # 获取匹配的上下文
                    for match in matches[:5]:  # 只显示前5个匹配的上下文
                        start = max(0, match.start() - 50)
                        end = min(len(text_content), match.end() + 50)
                        context = text_content[start:end].replace('\n', ' ').strip()
                        results.append({
                            'url': url,
                            'context': f"...{context}...",
                            'count': len(matches)
                        })
                    # 只添加一次URL到结果中
                    self.log_message(f"在 {url} 中找到 {len(matches)} 个匹配")
                
                # 标记为已访问
                visited_urls.add(url)
                
                # 如果是第一层，查找分页链接或更多页面[citation:3]
                if depth < max_depth:
                    new_urls = self.find_pagination_links(soup, url, visited_urls)
                    # 查找普通链接
                    page_links = self.find_content_links(soup, url, visited_urls)
                    new_urls.extend(page_links)
                    
                    for new_url in new_urls:
                        if new_url not in visited_urls and new_url not in [u for u, d in urls_to_visit]:
                            urls_to_visit.append((new_url, depth + 1))
                            
            except Exception as e:
                self.log_message(f"访问 {url} 时出错: {str(e)}")
                continue
                
        return results
        
    def find_pagination_links(self, soup, base_url, visited_urls):
        """查找分页链接[citation:3]"""
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
            '.previous-page a'
        ]
        
        for selector in pagination_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self.is_same_domain(base_url, full_url) and full_url not in visited_urls:
                        pagination_urls.append(full_url)
        
        # 查找包含page、paged等参数的链接[citation:3]
        page_links = soup.find_all('a', href=re.compile(r'[?&]page[ds]?=\d+'))
        for link in page_links:
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                if self.is_same_domain(base_url, full_url) and full_url not in visited_urls:
                    pagination_urls.append(full_url)
                    
        return pagination_urls
        
    def find_content_links(self, soup, base_url, visited_urls):
        """查找内容链接"""
        content_urls = []
        
        # 查找可能是文章或内容的链接
        content_selectors = [
            'a[href*="thread"]',
            'a[href*="post"]',
            'a[href*="article"]',
            'a[href*="topic"]',
            '.title a',
            '.content a',
            '.post-title a'
        ]
        
        for selector in content_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if (self.is_same_domain(base_url, full_url) and 
                        full_url not in visited_urls and
                        not self.is_file_link(full_url)):
                        content_urls.append(full_url)
                        
        return list(set(content_urls))  # 去重
        
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
        file_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.png', '.gif', '.zip', '.rar']
        return any(url.lower().endswith(ext) for ext in file_extensions)
        
    def display_results(self, results, keyword):
        """显示搜索结果[citation:5]"""
        if not results:
            self.log_message("没有找到匹配的结果")
            self.stats_var.set("找到 0 个匹配")
            return
            
        total_matches = sum(result['count'] for result in results)
        unique_pages = len(set(result['url'] for result in results))
        
        self.log_message("=" * 60)
        self.log_message(f"搜索完成！在 {unique_pages} 个页面中找到 {total_matches} 个匹配")
        self.log_message("=" * 60)
        
        # 按匹配数量排序
        url_counts = {}
        for result in results:
            url_counts[result['url']] = url_counts.get(result['url'], 0) + result['count']
        
        for i, (url, count) in enumerate(url_counts.items(), 1):
            self.log_message(f"\n{i}. {url}")
            self.log_message(f"   匹配数量: {count}")
            
            # 显示该URL的上下文片段
            for result in results:
                if result['url'] == url:
                    self.log_message(f"   上下文: {result['context']}")
                    break
        
        self.stats_var.set(f"在 {unique_pages} 个页面中找到 {total_matches} 个匹配")
        
    def log_message(self, message):
        """在文本框中添加消息"""
        self.root.after(0, lambda: self.result_text.insert(tk.END, message + "\n"))
        self.root.after(0, lambda: self.result_text.see(tk.END))
        
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
    root.mainloop()

if __name__ == "__main__":
    main()