import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import requests
from datetime import datetime, timedelta
import threading
import time
import json
import re
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed

class LOFMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LOF溢价率监控工具 - 智能数据融合优化版")
        self.root.geometry("1300x750")
        
        # 会话对象
        self.session = requests.Session()
        self._init_session_headers()
        
        # 缓存最近数据
        self.data_cache = {}
        self.cache_expiry = {
            'price': 300,  # 价格缓存5分钟
            'nav': 3600,   # 净值缓存1小时
            'full': 600    # 完整数据缓存10分钟
        }
        
        # 线程控制
        self.monitoring = False
        self.monitor_thread = None
        self.data_fetch_executor = None
        self.task_queue = queue.Queue()
        self.update_pending = False
        
        # 数据源优先级配置
        self.data_sources = {
            'price': [
                ('tencent', '腾讯财经实时价', 1),  # 最高优先级
                ('sina', '新浪财经实时价', 2),
                ('eastmoney_est', '东方财富估值', 3),
                ('cached', '缓存数据', 4)
            ],
            'nav': [
                ('eastmoney', '东方财富净值', 1),  # 最高优先级
                ('eastmoney_history', '东方财富历史净值', 2),
                ('tencent', '腾讯财经净值', 3),
                ('cached', '缓存数据', 4)
            ]
        }
        
        # 监控的LOF基金列表
        self.lof_codes = [
            "161226",  # 国投白银LOF
            "162411",  # 华宝油气LOF
            "160216",  # 国泰商品LOF
            "162719",  # 广发道琼斯石油LOF
            "501018",  # 南方原油LOF
            "501025",  # 香港银行LOF
            "168204",  # 中融钢铁LOF
            "165525",  # 基建工程LOF
            "160723",  # 嘉实原油LOF
        ]
        
        self.setup_ui()
        self.data = []
        
        # 启动任务处理线程
        self.task_processor_thread = threading.Thread(
            target=self._process_task_queue, 
            daemon=True
        )
        self.task_processor_thread.start()
        
        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _init_session_headers(self):
        """初始化会话请求头"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(headers)
    
    def _get_cached_data(self, code, data_type):
        """获取缓存数据"""
        if code in self.data_cache:
            cache_entry = self.data_cache[code]
            cache_time = cache_entry.get('timestamp', 0)
            current_time = time.time()
            
            # 检查缓存是否过期
            if data_type == 'price':
                expiry = self.cache_expiry['price']
            elif data_type == 'nav':
                expiry = self.cache_expiry['nav']
            else:
                expiry = self.cache_expiry['full']
            
            if current_time - cache_time <= expiry:
                return cache_entry.get(data_type, {})
        return None
    
    def _update_cache(self, code, data_type, data):
        """更新缓存"""
        if code not in self.data_cache:
            self.data_cache[code] = {'timestamp': time.time()}
        
        self.data_cache[code][data_type] = data
        self.data_cache[code]['timestamp'] = time.time()
    
    def _process_task_queue(self):
        """处理任务队列的独立线程"""
        while True:
            try:
                task = self.task_queue.get(timeout=0.5)
                if task[0] == 'update_table':
                    self.root.after(0, self._safe_update_table, task[1])
                elif task[0] == 'update_status':
                    self.root.after(0, self._safe_update_status, task[1])
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"任务处理错误: {e}")
    
    def _safe_update_table(self, fund_info):
        """安全更新表格（在主线程执行）"""
        try:
            # 准备表格数据 - 10列
            values = (
                fund_info['code'],  # 代码
                fund_info['name'][:15],  # 名称
                f"{fund_info['price']:.3f}" if fund_info['price'] > 0 else fund_info.get('price_status', 'N/A'),  # 实时价
                f"{fund_info['nav']:.3f}" if fund_info['nav'] > 0 else fund_info.get('nav_status', 'N/A'),  # 净值
                fund_info.get('premium_rate_str', 'N/A'),  # 溢价率
                fund_info.get('premium_amount_str', 'N/A'),  # 溢价金额
                fund_info.get('change_percent', '0.00%'),  # 涨跌幅
                f"{fund_info.get('volume', 0):.1f}" if fund_info.get('volume', 0) > 0 else "0",  # 成交量(万)
                fund_info.get('data_source', '未知'),  # 数据源
                fund_info.get('update_time', datetime.now().strftime("%H:%M:%S"))  # 更新时间
            )
            
            # 查找是否已存在该基金行
            existing_item = None
            for item in self.tree.get_children():
                if self.tree.item(item, 'values')[0] == fund_info['code']:
                    existing_item = item
                    break
            
            if existing_item:
                self.tree.item(existing_item, values=values)
            else:
                item_id = self.tree.insert("", "end", values=values)
            
            # 应用标签颜色
            tag = fund_info.get('tag', 'normal')
            if existing_item:
                self.tree.item(existing_item, tags=(tag,))
            else:
                self.tree.item(item_id, tags=(tag,))
                
        except Exception as e:
            print(f"更新表格错误: {e}")
    
    def _safe_update_status(self, message):
        """安全更新状态栏"""
        self.status_var.set(message)
    
    def setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="LOF基金溢价率监控系统（智能数据融合）", 
                                font=("微软雅黑", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))
        
        # 控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding="12")
        control_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # 按钮组
        buttons = [
            ("▶ 开始监控", self.start_monitoring),
            ("⏸ 暂停监控", self.stop_monitoring),
            ("↻ 手动刷新", self.fetch_data),
            ("💾 导出CSV", self.export_csv),
            ("➕ 添加基金", self.add_fund),
            ("📊 数据源状态", self.show_data_source_status),
        ]
        
        for i, (text, command) in enumerate(buttons):
            btn = ttk.Button(control_frame, text=text, command=command, width=12)
            btn.grid(row=0, column=i, padx=5)
        
        # 监控间隔设置
        ttk.Label(control_frame, text="刷新间隔(秒):").grid(row=0, column=len(buttons), padx=(20, 5))
        self.interval_var = tk.StringVar(value="60")
        interval_combo = ttk.Combobox(
            control_frame, 
            textvariable=self.interval_var,
            values=["30", "60", "120", "300", "600"],
            width=8,
            state="readonly"
        )
        interval_combo.grid(row=0, column=len(buttons)+1, padx=5)
        
        # 高溢价警报阈值
        ttk.Label(control_frame, text="高溢价警报>").grid(row=0, column=len(buttons)+2, padx=(20, 5))
        self.alert_var = tk.StringVar(value="5.0")
        alert_spin = ttk.Spinbox(control_frame, from_=0.1, to=100, textvariable=self.alert_var, width=6)
        alert_spin.grid(row=0, column=len(buttons)+3, padx=5)
        ttk.Label(control_frame, text="%").grid(row=0, column=len(buttons)+4, padx=(0, 10))
        
        # 数据源状态标签
        self.data_source_status = tk.StringVar(value="数据源: 智能融合")
        status_label = ttk.Label(control_frame, textvariable=self.data_source_status, foreground="blue")
        status_label.grid(row=0, column=len(buttons)+5, padx=(20, 0))
        
        # 状态栏
        self.status_var = tk.StringVar(value="🟢 就绪 - 点击'开始监控'启动")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, padding=8)
        status_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(15, 0))
        
        # 数据显示表格
        table_frame = ttk.LabelFrame(main_frame, text="实时数据监控", padding="10")
        table_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 配置表格框架的网格权重
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview（表格）- 10列定义
        columns = ("代码", "名称", "实时价", "净值", "溢价率", "溢价金额", "涨跌幅", "成交量(万)", "数据源", "更新时间")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20, selectmode="extended")
        
        # 设置列属性
        column_configs = [
            ("代码", 80, "center"),
            ("名称", 140, "center"),
            ("实时价", 90, "center"),
            ("净值", 90, "center"),
            ("溢价率", 100, "center"),
            ("溢价金额", 90, "center"),
            ("涨跌幅", 90, "center"),
            ("成交量(万)", 100, "center"),
            ("数据源", 110, "center"),
            ("更新时间", 120, "center"),
        ]
        
        for col, width, anchor in column_configs:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=anchor)
        
        # 添加滚动条
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 配置标签颜色
        self.tree.tag_configure('high_premium', foreground='#e53935', font=('宋体', 10, 'bold'))
        self.tree.tag_configure('medium_premium', foreground='#fb8c00')
        self.tree.tag_configure('normal', foreground='#333333')
        self.tree.tag_configure('discount', foreground='#43a047')
        
        # 设置主框架网格权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
    
    # =============== 数据获取函数 ===============
    
    def _get_price_from_tencent(self, code):
        """从腾讯财经获取实时价格"""
        try:
            # 确定市场前缀
            if code.startswith('16') or code.startswith('15'):
                prefix = 'sz'
            elif code.startswith('50') or code.startswith('51'):
                prefix = 'sh'
            else:
                prefix = 'sz'
            
            url = f"http://qt.gtimg.cn/q={prefix}{code}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://gu.qq.com/',
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code != 200:
                return None, "请求失败"
            
            text = response.text
            
            # 解析数据格式: v_sz161226="..."
            if '="' not in text:
                return None, "数据格式错误"
            
            data_str = text.split('="')[1].split('";')[0]
            data = data_str.split('~')
            
            if len(data) < 40:
                return None, "数据不完整"
            
            # 获取价格和相关信息
            current_price = data[3]
            change_percent = data[32] if len(data) > 32 else "0.00"
            volume = data[6] if len(data) > 6 else "0"
            name = data[1] if len(data) > 1 else f"基金{code}"
            
            # 处理价格
            try:
                price = float(current_price) if current_price else 0
            except:
                price = 0
            
            if price <= 0:
                return None, "价格无效"
            
            # 处理涨跌幅
            if change_percent and change_percent.strip():
                try:
                    if not change_percent.endswith('%'):
                        change_percent = f"{float(change_percent):.2f}%"
                except:
                    change_percent = "0.00%"
            else:
                change_percent = "0.00%"
            
            # 处理成交量
            try:
                volume_wan = float(volume) / 10000 if volume else 0
            except:
                volume_wan = 0
            
            result = {
                'price': price,
                'change_percent': change_percent,
                'volume': volume_wan,
                'name': name,
                'source': '腾讯财经',
                'timestamp': time.time()
            }
            
            return result, "成功"
                
        except requests.exceptions.RequestException:
            return None, "网络错误"
        except Exception:
            return None, "处理错误"
    
    def _get_price_from_sina(self, code):
        """从新浪财经获取实时价格（备用）"""
        try:
            # 确定市场
            if code.startswith('16') or code.startswith('15'):
                market = 'sz'
            elif code.startswith('50') or code.startswith('51'):
                market = 'sh'
            else:
                market = 'sz'
            
            url = f"http://hq.sinajs.cn/list={market}{code}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'http://finance.sina.com.cn/',
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code != 200:
                return None, "请求失败"
            
            text = response.text
            
            # 解析数据格式: var hq_str_sz161226="..."
            if '="' not in text:
                return None, "数据格式错误"
            
            data_str = text.split('="')[1].split('";')[0]
            data = data_str.split(',')
            
            if len(data) < 30:
                return None, "数据不完整"
            
            # 获取价格
            try:
                price = float(data[3]) if data[3] else 0
                prev_close = float(data[2]) if data[2] else price
            except:
                price = 0
                prev_close = 0
            
            if price <= 0:
                return None, "价格无效"
            
            # 计算涨跌幅
            if prev_close > 0:
                change_pct = (price - prev_close) / prev_close * 100
                change_percent = f"{change_pct:.2f}%"
            else:
                change_percent = "0.00%"
            
            result = {
                'price': price,
                'change_percent': change_percent,
                'volume': 0,  # 新浪不提供成交量
                'name': data[0] if data[0] else f"基金{code}",
                'source': '新浪财经',
                'timestamp': time.time()
            }
            
            return result, "成功"
                
        except requests.exceptions.RequestException:
            return None, "网络错误"
        except Exception:
            return None, "处理错误"
    
    def _get_nav_from_eastmoney(self, code):
        """从东方财富获取净值"""
        try:
            timestamp = int(time.time() * 1000)
            url = f"https://fundgz.1234567.com.cn/js/{code}.js?rt={timestamp}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://fund.eastmoney.com/',
            }
            
            response = requests.get(url, headers=headers, timeout=8)
            
            if response.status_code != 200:
                return None, "请求失败"
            
            text = response.text.strip()
            
            # 检查是否是有效的JSONP响应
            if not text.startswith('jsonpgz(') or not text.endswith(');'):
                return None, "数据格式错误"
            
            # 提取JSON部分
            json_str = text[8:-2]
            
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                json_str_clean = re.sub(r',\s*}', '}', json_str)
                json_str_clean = re.sub(r',\s*]', ']', json_str_clean)
                try:
                    data = json.loads(json_str_clean)
                except:
                    return None, "JSON解析失败"
            
            # 获取净值
            dwjz = data.get('dwjz', '0')
            name = data.get('name', f"基金{code}")
            
            try:
                nav = float(dwjz) if dwjz else 0
            except:
                nav = 0
            
            if nav <= 0:
                return None, "净值无效"
            
            result = {
                'nav': nav,
                'name': name,
                'source': '东方财富',
                'timestamp': time.time()
            }
            
            return result, "成功"
                
        except requests.exceptions.RequestException:
            return None, "网络错误"
        except Exception:
            return None, "处理错误"
    
    def _get_historical_nav_from_eastmoney(self, code):
        """从东方财富获取历史净值（备用）"""
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize=10&startDate={start_date}&endDate={end_date}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': f'https://fundf10.eastmoney.com/jjjz_{code}.html',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return None, "请求失败"
            
            data = response.json()
            
            if data.get('ErrCode') != 0 or 'Data' not in data or 'LSJZList' not in data['Data']:
                return None, "数据错误"
            
            lsjz_list = data['Data']['LSJZList']
            if not lsjz_list or len(lsjz_list) == 0:
                return None, "无历史数据"
            
            # 获取最新净值
            latest_nav = lsjz_list[0].get('DWJZ', '0')
            try:
                nav = float(latest_nav) if latest_nav else 0
            except:
                nav = 0
            
            if nav <= 0:
                return None, "净值无效"
            
            # 获取基金名称
            name = lsjz_list[0].get('FSRQ', f"基金{code}")
            
            result = {
                'nav': nav,
                'name': name,
                'source': '东方财富(历史)',
                'timestamp': time.time()
            }
            
            return result, "成功"
            
        except requests.exceptions.RequestException:
            return None, "网络错误"
        except Exception:
            return None, "处理错误"
    
    def _get_nav_from_tencent(self, code):
        """从腾讯财经获取净值（备用）"""
        try:
            # 先获取腾讯财经数据
            price_data, status = self._get_price_from_tencent(code)
            if price_data is None:
                return None, "无法获取价格数据"
            
            # 腾讯财经数据中没有净值，这里返回None
            return None, "腾讯财经无净值数据"
                
        except Exception:
            return None, "处理错误"
    
    def fetch_single_fund_data(self, code):
        """获取单个基金完整数据（智能优先级回退）"""
        fund_info = {
            'code': code,
            'name': f"基金{code}",
            'price': 0,
            'nav': 0,
            'price_status': '待获取',
            'nav_status': '待获取',
            'change_percent': "0.00%",
            'volume': 0,
            'data_source': '',
            'update_time': datetime.now().strftime("%H:%M:%S"),
            'price_source': '',
            'nav_source': '',
            'sources_used': []
        }
        
        # 尝试从缓存获取完整数据
        cached_data = self._get_cached_data(code, 'full')
        if cached_data:
            fund_info.update(cached_data)
            fund_info['data_source'] = '缓存数据'
            fund_info['sources_used'].append('缓存')
            return fund_info
        
        # ========== 获取价格数据 ==========
        price_obtained = False
        price_sources_tried = []
        
        for source_id, source_name, priority in self.data_sources['price']:
            if price_obtained:
                break
                
            price_sources_tried.append(source_name)
            
            if source_id == 'tencent':
                price_data, status = self._get_price_from_tencent(code)
                if price_data and price_data.get('price', 0) > 0:
                    fund_info['price'] = price_data['price']
                    fund_info['change_percent'] = price_data.get('change_percent', '0.00%')
                    fund_info['volume'] = price_data.get('volume', 0)
                    if 'name' in price_data and price_data['name']:
                        fund_info['name'] = price_data['name']
                    fund_info['price_source'] = source_name
                    fund_info['sources_used'].append(f"价格:{source_name}")
                    price_obtained = True
                    fund_info['price_status'] = f"{price_data['price']:.3f}"
            
            elif source_id == 'sina':
                price_data, status = self._get_price_from_sina(code)
                if price_data and price_data.get('price', 0) > 0:
                    fund_info['price'] = price_data['price']
                    fund_info['change_percent'] = price_data.get('change_percent', '0.00%')
                    if 'name' in price_data and price_data['name']:
                        fund_info['name'] = price_data['name']
                    fund_info['price_source'] = source_name
                    fund_info['sources_used'].append(f"价格:{source_name}")
                    price_obtained = True
                    fund_info['price_status'] = f"{price_data['price']:.3f}"
            
            elif source_id == 'cached':
                cached_price = self._get_cached_data(code, 'price')
                if cached_price and cached_price.get('price', 0) > 0:
                    fund_info['price'] = cached_price['price']
                    fund_info['change_percent'] = cached_price.get('change_percent', '0.00%')
                    fund_info['volume'] = cached_price.get('volume', 0)
                    fund_info['price_source'] = f"{cached_price.get('source', '缓存')}(缓存)"
                    fund_info['sources_used'].append(f"价格:{source_name}(缓存)")
                    price_obtained = True
                    fund_info['price_status'] = f"{cached_price['price']:.3f}(缓存)"
        
        if not price_obtained:
            fund_info['price_status'] = f"缺失(尝试: {', '.join(price_sources_tried)})"
        
        # ========== 获取净值数据 ==========
        nav_obtained = False
        nav_sources_tried = []
        
        for source_id, source_name, priority in self.data_sources['nav']:
            if nav_obtained:
                break
                
            nav_sources_tried.append(source_name)
            
            if source_id == 'eastmoney':
                nav_data, status = self._get_nav_from_eastmoney(code)
                if nav_data and nav_data.get('nav', 0) > 0:
                    fund_info['nav'] = nav_data['nav']
                    if 'name' in nav_data and nav_data['name']:
                        fund_info['name'] = nav_data['name']
                    fund_info['nav_source'] = source_name
                    fund_info['sources_used'].append(f"净值:{source_name}")
                    nav_obtained = True
                    fund_info['nav_status'] = f"{nav_data['nav']:.3f}"
            
            elif source_id == 'eastmoney_history':
                nav_data, status = self._get_historical_nav_from_eastmoney(code)
                if nav_data and nav_data.get('nav', 0) > 0:
                    fund_info['nav'] = nav_data['nav']
                    fund_info['nav_source'] = source_name
                    fund_info['sources_used'].append(f"净值:{source_name}")
                    nav_obtained = True
                    fund_info['nav_status'] = f"{nav_data['nav']:.3f}(历史)"
            
            elif source_id == 'tencent':
                nav_data, status = self._get_nav_from_tencent(code)
                if nav_data and nav_data.get('nav', 0) > 0:
                    fund_info['nav'] = nav_data['nav']
                    fund_info['nav_source'] = source_name
                    fund_info['sources_used'].append(f"净值:{source_name}")
                    nav_obtained = True
                    fund_info['nav_status'] = f"{nav_data['nav']:.3f}"
            
            elif source_id == 'cached':
                cached_nav = self._get_cached_data(code, 'nav')
                if cached_nav and cached_nav.get('nav', 0) > 0:
                    fund_info['nav'] = cached_nav['nav']
                    fund_info['nav_source'] = f"{cached_nav.get('source', '缓存')}(缓存)"
                    fund_info['sources_used'].append(f"净值:{source_name}(缓存)")
                    nav_obtained = True
                    fund_info['nav_status'] = f"{cached_nav['nav']:.3f}(缓存)"
        
        if not nav_obtained:
            fund_info['nav_status'] = f"缺失(尝试: {', '.join(nav_sources_tried)})"
        
        # ========== 计算溢价率和相关数据 ==========
        price = fund_info.get('price', 0)
        nav = fund_info.get('nav', 0)
        
        if price > 0 and nav > 0:
            premium_rate = (price - nav) / nav * 100
            fund_info['premium_rate'] = premium_rate
            fund_info['premium_rate_str'] = f"{premium_rate:+.2f}%"
            fund_info['premium_amount'] = price - nav
            fund_info['premium_amount_str'] = f"{price - nav:+.3f}"
            
            # 确定标签颜色
            alert_threshold = float(self.alert_var.get()) if hasattr(self, 'alert_var') else 5.0
            if premium_rate > alert_threshold:
                fund_info['tag'] = 'high_premium'
            elif premium_rate > 2:
                fund_info['tag'] = 'medium_premium'
            elif premium_rate < -1:
                fund_info['tag'] = 'discount'
            else:
                fund_info['tag'] = 'normal'
        else:
            if price == 0 and nav == 0:
                fund_info['premium_rate_str'] = "价格和净值均缺失"
            elif price == 0:
                fund_info['premium_rate_str'] = "价格缺失"
            else:
                fund_info['premium_rate_str'] = "净值缺失"
            
            fund_info['premium_amount_str'] = "N/A"
            fund_info['tag'] = 'normal'
        
        # ========== 更新缓存 ==========
        if price > 0:
            self._update_cache(code, 'price', {
                'price': price,
                'change_percent': fund_info['change_percent'],
                'volume': fund_info['volume'],
                'source': fund_info['price_source'],
                'timestamp': time.time()
            })
        
        if nav > 0:
            self._update_cache(code, 'nav', {
                'nav': nav,
                'source': fund_info['nav_source'],
                'timestamp': time.time()
            })
        
        # 缓存完整数据
        self._update_cache(code, 'full', fund_info.copy())
        
        # ========== 设置数据源显示 ==========
        if fund_info['price_source'] and fund_info['nav_source']:
            fund_info['data_source'] = f"{fund_info['price_source']}/{fund_info['nav_source']}"
        elif fund_info['price_source']:
            fund_info['data_source'] = f"{fund_info['price_source']}/净值缺失"
        elif fund_info['nav_source']:
            fund_info['data_source'] = f"价格缺失/{fund_info['nav_source']}"
        else:
            fund_info['data_source'] = "数据缺失"
        
        return fund_info
    
    def fetch_data(self):
        """获取所有基金数据"""
        if self.update_pending:
            return
        
        self.update_pending = True
        self.status_var.set("⏳ 正在从多个数据源获取数据...")
        
        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.data = []
        
        # 使用线程池获取数据
        def fetch_task():
            try:
                if self.data_fetch_executor is None:
                    self.data_fetch_executor = ThreadPoolExecutor(max_workers=10)
                
                futures = {}
                for code in self.lof_codes:
                    future = self.data_fetch_executor.submit(
                        self.fetch_single_fund_data, 
                        code
                    )
                    futures[future] = code
                
                successful = 0
                price_success = 0
                nav_success = 0
                
                # 设置超时，防止某些请求卡住
                for future in as_completed(futures, timeout=30):
                    code = futures[future]
                    try:
                        fund_info = future.result(timeout=5)
                        if fund_info:
                            self.data.append(fund_info)
                            successful += 1
                            
                            # 统计成功获取的数据
                            if fund_info.get('price', 0) > 0:
                                price_success += 1
                            if fund_info.get('nav', 0) > 0:
                                nav_success += 1
                            
                            # 通过队列发送更新任务
                            self.task_queue.put(('update_table', fund_info))
                    except Exception as e:
                        print(f"基金 {code} 数据获取失败: {e}")
                
                # 更新状态
                alert_threshold = float(self.alert_var.get())
                high_premium_count = sum(1 for fund in self.data if fund.get('premium_rate', 0) > alert_threshold)
                
                status_msg = f"✅ 数据获取完成 | 基金: {successful}/{len(self.lof_codes)}"
                status_msg += f" | 价格: {price_success}/{len(self.lof_codes)}"
                status_msg += f" | 净值: {nav_success}/{len(self.lof_codes)}"
                
                if high_premium_count > 0:
                    status_msg += f" | 高溢价(>{alert_threshold}%): {high_premium_count}个"
                
                self.task_queue.put(('update_status', status_msg))
                
                # 如果有高溢价基金，播放提示音
                if high_premium_count > 0 and self.monitoring:
                    self.root.bell()
                
            except Exception as e:
                error_msg = f"获取数据出错: {str(e)[:50]}..."
                self.task_queue.put(('update_status', error_msg))
            finally:
                self.update_pending = False
        
        # 在后台线程执行获取任务
        fetch_thread = threading.Thread(target=fetch_task, daemon=True)
        fetch_thread.start()
    
    def start_monitoring(self):
        """开始自动监控"""
        if not self.monitoring:
            self.monitoring = True
            self.status_var.set("🔄 监控已启动，正在获取数据...")
            
            def monitor_loop():
                while self.monitoring:
                    start_time = time.time()
                    self.fetch_data()
                    
                    interval = int(self.interval_var.get())
                    elapsed = time.time() - start_time
                    sleep_time = max(1, interval - elapsed)
                    
                    # 分段休眠，便于及时响应停止命令
                    for _ in range(int(sleep_time)):
                        if not self.monitoring:
                            break
                        time.sleep(1)
            
            self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
            self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        if self.monitoring:
            self.monitoring = False
            self.status_var.set("⏹️ 监控已停止")
    
    def export_csv(self):
        """导出数据到CSV文件"""
        if not self.data:
            messagebox.showwarning("警告", "没有数据可以导出，请先获取数据。")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")],
            initialfile=f"lof_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if filename:
            try:
                # 创建导出数据
                export_data = []
                for fund in self.data:
                    row = {
                        '代码': fund.get('code', ''),
                        '名称': fund.get('name', ''),
                        '实时价': fund.get('price', 0),
                        '实时价状态': fund.get('price_status', ''),
                        '净值': fund.get('nav', 0),
                        '净值状态': fund.get('nav_status', ''),
                        '溢价率': fund.get('premium_rate_str', 'N/A'),
                        '溢价金额': fund.get('premium_amount_str', 'N/A'),
                        '涨跌幅': fund.get('change_percent', '0.00%'),
                        '成交量(万)': fund.get('volume', 0),
                        '数据源': fund.get('data_source', ''),
                        '价格来源': fund.get('price_source', ''),
                        '净值来源': fund.get('nav_source', ''),
                        '更新时间': fund.get('update_time', ''),
                    }
                    export_data.append(row)
                
                export_df = pd.DataFrame(export_data)
                export_df.to_csv(filename, index=False, encoding='utf-8-sig')
                
                self.status_var.set(f"💾 数据已导出到: {filename.split('/')[-1]}")
                messagebox.showinfo("导出成功", f"已成功导出 {len(export_df)} 条记录到:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("导出错误", f"导出失败:\n{str(e)}")
    
    def add_fund(self):
        """添加新的基金代码"""
        def on_add():
            code = code_var.get().strip()
            name = name_var.get().strip()
            
            if not code.isdigit() or len(code) != 6:
                messagebox.showwarning("格式错误", "基金代码必须是6位数字")
                return
                
            if code in self.lof_codes:
                messagebox.showwarning("重复代码", "该基金代码已在监控列表中")
                return
            
            # 验证基金代码有效性
            test_data = self.fetch_single_fund_data(code)
            if test_data:
                price_ok = test_data.get('price', 0) > 0
                nav_ok = test_data.get('nav', 0) > 0
                
                if not price_ok and not nav_ok:
                    if not messagebox.askyesno("验证警告", 
                        f"基金代码 {code} 价格和净值均无法获取，是否仍然添加？"):
                        return
                elif not price_ok:
                    if not messagebox.askyesno("验证警告", 
                        f"基金代码 {code} 无法获取实时价格，是否仍然添加？"):
                        return
                elif not nav_ok:
                    if not messagebox.askyesno("验证警告", 
                        f"基金代码 {code} 无法获取净值，是否仍然添加？"):
                        return
            
            self.lof_codes.append(code)
            self.status_var.set(f"✅ 已添加基金: {name if name else code}")
            add_window.destroy()
            
            # 刷新数据显示新基金
            self.fetch_data()
        
        add_window = tk.Toplevel(self.root)
        add_window.title("添加监控基金")
        add_window.geometry("400x250")
        add_window.resizable(False, False)
        
        main_frame = ttk.Frame(add_window, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(main_frame, text="添加LOF基金到监控列表", 
                 font=("微软雅黑", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        ttk.Label(main_frame, text="基金代码 (6位):").grid(row=1, column=0, sticky=tk.W, pady=5)
        code_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=code_var, width=15).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(main_frame, text="基金名称 (可选):").grid(row=2, column=0, sticky=tk.W, pady=5)
        name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=name_var, width=25).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(main_frame, text="示例代码: 161226(白银LOF), 162411(华宝油气)", 
                 font=("宋体", 9), foreground="gray").grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="添加", command=on_add, width=10).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=add_window.destroy, width=10).pack(side=tk.LEFT, padx=10)
        
        add_window.mainloop()
    
    def show_data_source_status(self):
        """显示数据源状态"""
        cache_info = f"缓存数据: {len(self.data_cache)} 个基金"
        
        # 统计当前数据获取情况
        price_sources = [name for _, name, _ in self.data_sources['price']]
        nav_sources = [name for _, name, _ in self.data_sources['nav']]
        
        message = f"数据源优先级策略:\n\n"
        message += f"价格获取优先级:\n"
        for i, (_, name, _) in enumerate(self.data_sources['price'], 1):
            message += f"  {i}. {name}\n"
        
        message += f"\n净值获取优先级:\n"
        for i, (_, name, _) in enumerate(self.data_sources['nav'], 1):
            message += f"  {i}. {name}\n"
        
        message += f"\n缓存策略:\n"
        message += f"  • 价格缓存: {self.cache_expiry['price']}秒\n"
        message += f"  • 净值缓存: {self.cache_expiry['nav']}秒\n"
        message += f"  • 完整数据缓存: {self.cache_expiry['full']}秒\n"
        message += f"\n{cache_info}"
        
        messagebox.showinfo("数据源状态", message)
    
    def on_closing(self):
        """窗口关闭时的清理"""
        self.stop_monitoring()
        if self.data_fetch_executor:
            self.data_fetch_executor.shutdown(wait=False)
        self.root.destroy()

def main():
    """主函数"""
    root = tk.Tk()
    
    # 设置窗口居中
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    app = LOFMonitorApp(root)
    
    # 启动时自动获取一次数据
    root.after(500, app.fetch_data)
    
    root.mainloop()

if __name__ == "__main__":
    # 设置DPI感知，改善高分辨率显示
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    main()