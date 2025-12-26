import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.backend_bases import key_press_handler
from matplotlib import rcParams
import platform
from datetime import datetime, timedelta
import threading
import re
import os
import sys
import requests
from lxml import etree

# ========== 中文显示配置 ==========
if platform.system() == 'Windows':
    rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    rcParams['axes.unicode_minus'] = False
elif platform.system() == 'Darwin':
    rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC']
    rcParams['axes.unicode_minus'] = False
else:
    rcParams['font.sans-serif'] = ['DejaVu Sans']
    rcParams['axes.unicode_minus'] = False

# ========== 数据获取模块 ==========
class FutureDataFetcher:
    def __init__(self):
        self.HEADER = ["商品", "现货价格", "最近合约代码", "最近合约价格", "最近合约现期差1", 
                      "最近合约期现差百分比1", "主力合约代码", "主力合约价格", 
                      "主力合约现期差2", "主力合约现期差百分比2", "日期", "交易所"]
    
    def check_date_params(self, start_date_str, end_date_str):
        """检查日期参数格式"""
        def check_date_format(date_str):
            return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", date_str))
        
        date_list = []
        if check_date_format(start_date_str) and check_date_format(end_date_str):
            year_start, month_start, day_start = start_date_str.split("-")
            year_end, month_end, day_end = end_date_str.split("-")
            start_date = datetime(int(year_start), int(month_start), int(day_start))
            end_date = datetime(int(year_end), int(month_end), int(day_end))
            delta_days = (end_date - start_date).days
            
            if delta_days >= 0:
                for i in range(0, delta_days + 1):
                    date = start_date + timedelta(days=i)
                    date_list.append(date.strftime("%Y-%m-%d"))
                return date_list
            else:
                raise ValueError("结束日期早于开始日期")
        else:
            raise ValueError("日期格式错误，请使用YYYY-MM-DD格式")
    
    def fetch_data_for_date(self, date_str):
        """获取指定日期的期货数据"""
        url_template = "http://www.100ppi.com/sf/day-{}.html"
        url = url_template.format(date_str)
        
        try:
            resp = requests.get(url, timeout=10)
            resp.encoding = 'utf-8'
            html = etree.HTML(resp.text)
            
            # 查找数据表格
            ele_list = html.xpath('//table[@id="fdata"]//tr[@align="center"] | //table[@id="fdata"]//tr/td[@colspan="8"]')
            ret = []
            
            if len(ele_list) == 0:
                return ret
            
            exchange = ""
            for ele in ele_list:
                if ele.tag == "td":
                    exchange = ele.text.strip() if ele.text else ""
                elif ele.tag == "tr":
                    raw_vals = ele.xpath('./td/a/text()|./td/text()|.//td/font/text()')
                    vals = []
                    for val in raw_vals:
                        if isinstance(val, str) and not re.match(r'^\s+$', val):
                            # 清理特殊空白字符
                            cleaned = re.sub(r'\s+', ' ', val.strip())
                            # 处理特殊字符
                            cleaned = re.sub(r'\xa0', ' ', cleaned)
                            vals.append(cleaned)
                    
                    # 确保数据长度与表头一致
                    if len(vals) >= 10:  # 至少有商品、现货价格等基本信息
                        # 补齐缺失字段
                        while len(vals) < 10:
                            vals.append("")
                        vals.extend([date_str, exchange])
                        ret.append(vals)
            
            return ret
        except Exception as e:
            print(f"获取{date_str}数据失败: {e}")
            return []
    
    def get_future_data(self, start_date, end_date, progress_callback=None):
        """获取指定日期范围的期货数据"""
        print(f"开始获取数据，从{start_date}到{end_date}")
        
        try:
            date_list = self.check_date_params(start_date, end_date)
            all_data = []
            total_days = len(date_list)
            
            for i, date_str in enumerate(date_list):
                if progress_callback:
                    progress = (i + 1) / total_days * 100
                    progress_callback(progress, f"正在获取 {date_str} 的数据...")
                
                daily_data = self.fetch_data_for_date(date_str)
                if daily_data:
                    all_data.extend(daily_data)
            
            return pd.DataFrame(all_data, columns=self.HEADER)
        except Exception as e:
            print(f"获取数据失败: {e}")
            return None

# ========== 数据分析模块 ==========
class FutureDataAnalyzer:
    def __init__(self):
        self.data = None
        self.current_product = None
    
    def set_data(self, data):
        """设置分析数据"""
        self.data = data
        
        # 清洗和转换数据
        if self.data is not None and not self.data.empty:
            # 转换数值列
            numeric_columns = ["现货价格", "最近合约价格", "主力合约价格", 
                             "最近合约现期差1", "主力合约现期差2"]
            for col in numeric_columns:
                if col in self.data.columns:
                    self.data[col] = pd.to_numeric(self.data[col].replace('', np.nan), errors='coerce')
            
            # 转换日期列
            if "日期" in self.data.columns:
                self.data["日期"] = pd.to_datetime(self.data["日期"], errors='coerce')
    
    def get_available_products(self):
        """获取可用的商品列表"""
        if self.data is not None and "商品" in self.data.columns:
            return sorted(self.data["商品"].dropna().unique())
        return []
    
    def analyze_price_position(self, price_series):
        """
        分析当前价格在历史价格中的位置
        返回：当前价格分位数，状态描述
        """
        if len(price_series) < 2:
            return None, "数据不足"
        
        # 获取当前价格（最新价格）
        current_price = price_series.iloc[-1]
        
        # 获取历史价格（排除当前价格）
        historical_prices = price_series.iloc[:-1]
        
        # 计算当前价格在历史价格中的百分位
        try:
            from scipy import stats
            percentile = stats.percentileofscore(historical_prices, current_price, kind='weak')
        except:
            # 如果没有scipy，使用简单方法
            sorted_prices = historical_prices.sort_values()
            idx = sorted_prices.searchsorted(current_price)
            percentile = (idx / len(sorted_prices)) * 100
        
        # 根据百分位判断价格状态
        if percentile >= 99:
            status = "价格极端高估（超过99%历史价格）"
            color = "red"
        elif percentile >= 80:
            status = "价格高估（超过80%历史价格）"
            color = "orange"
        elif percentile <= 1:
            status = "价格极端低估（低于99%历史价格）"
            color = "darkgreen"
        elif percentile <= 20:
            status = "价格低估（低于80%历史价格）"
            color = "green"
        else:
            status = "价格处于合理区间"
            color = "blue"
        
        return {
            "current_price": current_price,
            "percentile": percentile,
            "status": status,
            "color": color,
            "historical_mean": historical_prices.mean(),
            "historical_std": historical_prices.std(),
            "historical_80_percentile": np.percentile(historical_prices, 80),
            "historical_20_percentile": np.percentile(historical_prices, 20),
            "historical_99_percentile": np.percentile(historical_prices, 99) if len(historical_prices) >= 100 else np.percentile(historical_prices, min(99, 100*(len(historical_prices)-1)/len(historical_prices))),
            "historical_1_percentile": np.percentile(historical_prices, 1) if len(historical_prices) >= 100 else np.percentile(historical_prices, max(1, 100/len(historical_prices))),
            "historical_min": historical_prices.min(),
            "historical_max": historical_prices.max(),
            "data_points": len(price_series)
        }
    
    def analyze_product(self, product_name):
        """分析指定商品的价格状态（根据新要求）"""
        if self.data is None or self.data.empty:
            return None, "无数据可供分析"
        
        # 过滤指定商品的数据
        product_data = self.data[self.data["商品"] == product_name].copy()
        if product_data.empty:
            return None, f"未找到商品'{product_name}'的数据"
        
        self.current_product = product_name
        
        # 按日期排序
        product_data = product_data.sort_values("日期")
        
        # 分析现货价格
        if "现货价格" in product_data.columns:
            spot_analysis = self.analyze_price_position(product_data["现货价格"].dropna())
        else:
            spot_analysis = {"status": "现货价格数据缺失"}
        
        # 分析主力合约价格
        if "主力合约价格" in product_data.columns:
            future_analysis = self.analyze_price_position(product_data["主力合约价格"].dropna())
        else:
            future_analysis = {"status": "主力合约价格数据缺失"}
        
        # 计算基差
        if "现货价格" in product_data.columns and "主力合约价格" in product_data.columns:
            product_data["基差"] = product_data["现货价格"] - product_data["主力合约价格"]
            basis_analysis = self.analyze_price_position(product_data["基差"].dropna())
        else:
            basis_analysis = {"status": "无法计算基差"}
        
        # 获取最新数据日期
        latest_date = product_data["日期"].iloc[-1] if len(product_data) > 0 else "未知"
        
        return product_data, {
            "spot": spot_analysis,
            "future": future_analysis,
            "basis": basis_analysis,
            "latest_date": latest_date,
            "product_name": product_name
        }
    
    def get_analysis_summary(self, product_name):
        """获取分析摘要"""
        product_data, analysis_dict = self.analyze_product(product_name)
        
        if product_data is None:
            return analysis_dict, None, None
        
        # 构建详细报告
        spot_info = analysis_dict.get("spot", {})
        future_info = analysis_dict.get("future", {})
        basis_info = analysis_dict.get("basis", {})
        
        # 判断整体市场状态
        overall_status = "中性"
        if "percentile" in future_info:
            if future_info["percentile"] >= 99:
                overall_status = "极度高估"
            elif future_info["percentile"] >= 80:
                overall_status = "高估"
            elif future_info["percentile"] <= 1:
                overall_status = "极度低估"
            elif future_info["percentile"] <= 20:
                overall_status = "低估"
        
        # 生成操作建议
        recommendation = self.generate_recommendation(future_info)
        
        summary = f"""
【{product_name}价格分析报告】
分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
最新数据日期: {analysis_dict['latest_date'].strftime('%Y-%m-%d') if hasattr(analysis_dict['latest_date'], 'strftime') else analysis_dict['latest_date']}
整体市场状态: {overall_status}
操作建议: {recommendation}
================================
【现货价格分析】
"""
        if "current_price" in spot_info:
            summary += f"""当前价格: {spot_info['current_price']:.2f}
历史百分位: {spot_info['percentile']:.1f}%
价格状态: {spot_info['status']}
历史价格范围: {spot_info['historical_min']:.2f} - {spot_info['historical_max']:.2f}
历史均值: {spot_info['historical_mean']:.2f}
关键分位点:
  20%分位点(低估阈值): {spot_info['historical_20_percentile']:.2f}
  80%分位点(高估阈值): {spot_info['historical_80_percentile']:.2f}
  1%分位点(极端低估): {spot_info['historical_1_percentile']:.2f}
  99%分位点(极端高估): {spot_info['historical_99_percentile']:.2f}
"""
        else:
            summary += "现货价格数据不足或缺失\n"
        
        summary += "\n================================\n【主力合约价格分析】\n"
        if "current_price" in future_info:
            summary += f"""当前价格: {future_info['current_price']:.2f}
历史百分位: {future_info['percentile']:.1f}%
价格状态: {future_info['status']}
历史价格范围: {future_info['historical_min']:.2f} - {future_info['historical_max']:.2f}
历史均值: {future_info['historical_mean']:.2f}
关键分位点:
  20%分位点(低估阈值): {future_info['historical_20_percentile']:.2f}
  80%分位点(高估阈值): {future_info['historical_80_percentile']:.2f}
  1%分位点(极端低估): {future_info['historical_1_percentile']:.2f}
  99%分位点(极端高估): {future_info['historical_99_percentile']:.2f}
"""
        else:
            summary += "主力合约价格数据不足或缺失\n"
        
        summary += "\n================================\n【基差分析】\n"
        if "current_price" in basis_info:
            summary += f"""当前基差: {basis_info['current_price']:.2f}
历史百分位: {basis_info['percentile']:.1f}%
基差状态: {basis_info['status']}
历史基差范围: {basis_info['historical_min']:.2f} - {basis_info['historical_max']:.2f}
历史均值: {basis_info['historical_mean']:.2f}
"""
        else:
            summary += "基差数据不足或缺失\n"
        
        summary += f"""
================================
【数据统计】
分析周期: {len(product_data)} 个交易日
数据覆盖: {product_data['日期'].min().strftime('%Y-%m-%d') if hasattr(product_data['日期'].min(), 'strftime') else product_data['日期'].min()} 至 
         {product_data['日期'].max().strftime('%Y-%m-%d') if hasattr(product_data['日期'].max(), 'strftime') else product_data['日期'].max()}
================================
【重要说明】
1. 价格百分位表示当前价格在历史价格中的位置
2. 超过80%历史价格 = 价格高位（高估）
3. 超过99%历史价格 = 价格极端高位（极端高估）
4. 低于80%历史价格 = 价格低位（低估）
5. 低于99%历史价格 = 价格极端低位（极端低估）
"""
        
        return summary, product_data, analysis_dict
    
    def generate_recommendation(self, future_info):
        """根据期货价格分析生成操作建议"""
        if "percentile" not in future_info:
            return "数据不足，无法提供建议"
        
        percentile = future_info["percentile"]
        
        if percentile >= 99:
            return "⚠️ 极端高估区域：建议减仓或考虑做空，注意风险控制"
        elif percentile >= 80:
            return "🔶 高估区域：谨慎操作，可考虑部分减仓或观望"
        elif percentile <= 1:
            return "✅ 极端低估区域：可能是买入机会，注意分批建仓"
        elif percentile <= 20:
            return "🟢 低估区域：可考虑逢低买入，注意仓位控制"
        else:
            return "🔵 合理区间：可持有或按原计划操作"

# ========== GUI主程序模块 ==========
class FutureAnalysisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("期货价格分析系统")
        
        # 初始化模块
        self.fetcher = FutureDataFetcher()
        self.analyzer = FutureDataAnalyzer()
        
        # 初始化变量
        self.data = None
        self.current_product = None
        self.figure = None
        self.canvas = None
        self.toolbar = None
        self.chart_frame = None
        self.canvas_frame = None
        self.hint_label = None  # 新增：用于保存提示标签的引用
        
        # 设置Tkinter中文字体
        self.set_tk_fonts()
        
        # 设置窗口大小和最小尺寸
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)  # 设置最小窗口尺寸
        
        # 创建界面
        self.setup_ui()
        
        # 设置初始日期
        self.set_default_dates()
        
        # 绑定窗口大小变化事件
        self.root.bind('<Configure>', self.on_window_resize)
    
    def set_tk_fonts(self):
        """设置Tkinter控件的中文字体"""
        if platform.system() == 'Windows':
            default_font = ('Microsoft YaHei', 9)
        elif platform.system() == 'Darwin':
            default_font = ('PingFang SC', 12)
        else:
            default_font = ('DejaVu Sans', 10)
        
        style = ttk.Style()
        style.configure('.', font=default_font)
    
    def set_default_dates(self):
        """设置默认日期"""
        today = datetime.now()
        three_months_ago = today - timedelta(days=90)
        
        self.start_date_var.set(three_months_ago.strftime("%Y-%m-%d"))
        self.end_date_var.set(today.strftime("%Y-%m-%d"))
    
    def on_window_resize(self, event):
        """窗口大小变化时调整布局"""
        if event.widget == self.root:
            # 可以在这里添加窗口大小变化时的额外处理
            pass
    
    def setup_ui(self):
        """构建用户界面"""
        # 创建主框架 - 使用pack布局管理器，更灵活
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ========== 控制面板 ==========
        control_frame = ttk.LabelFrame(main_frame, text="数据获取控制", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 日期选择
        date_frame = ttk.Frame(control_frame)
        date_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(date_frame, text="开始日期:").pack(side=tk.LEFT, padx=(0, 5))
        self.start_date_var = tk.StringVar()
        start_date_entry = ttk.Entry(date_frame, textvariable=self.start_date_var, width=15)
        start_date_entry.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(date_frame, text="结束日期:").pack(side=tk.LEFT, padx=(0, 5))
        self.end_date_var = tk.StringVar()
        end_date_entry = ttk.Entry(date_frame, textvariable=self.end_date_var, width=15)
        end_date_entry.pack(side=tk.LEFT, padx=(0, 15))
        
        # 获取数据按钮
        self.fetch_btn = ttk.Button(date_frame, text="获取期货数据", command=self.start_fetch_data)
        self.fetch_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 读取CSV数据按钮
        self.load_csv_btn = ttk.Button(date_frame, text="读取CSV数据", command=self.load_csv_data)
        self.load_csv_btn.pack(side=tk.LEFT)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(10, 0))
        
        # 进度标签
        self.progress_label = ttk.Label(control_frame, text="就绪")
        self.progress_label.pack(anchor=tk.W, pady=(2, 0))
        
        # ========== 数据分析面板 ==========
        analysis_frame = ttk.LabelFrame(main_frame, text="数据分析", padding="10")
        analysis_frame.pack(fill=tk.X, pady=(0, 10))
        
        analysis_controls_frame = ttk.Frame(analysis_frame)
        analysis_controls_frame.pack(fill=tk.X)
        
        # 商品选择
        ttk.Label(analysis_controls_frame, text="选择商品:").pack(side=tk.LEFT, padx=(0, 5))
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(analysis_controls_frame, textvariable=self.product_var, 
                                         state="readonly", width=25)
        self.product_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        # 分析按钮
        self.analyze_btn = ttk.Button(analysis_controls_frame, text="分析价格位置", 
                                     command=self.analyze_selected_product, state=tk.DISABLED)
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 保存数据按钮
        self.save_btn = ttk.Button(analysis_controls_frame, text="保存数据到CSV", 
                                  command=self.save_data, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 快速分析按钮
        self.quick_analysis_btn = ttk.Button(analysis_controls_frame, text="快速扫描全部商品", 
                                           command=self.quick_scan_all_products, state=tk.DISABLED)
        self.quick_analysis_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 清空数据按钮
        self.clear_data_btn = ttk.Button(analysis_controls_frame, text="清空数据", 
                                        command=self.clear_data, state=tk.DISABLED)
        self.clear_data_btn.pack(side=tk.LEFT)
        
        # ========== 结果显示区域 ==========
        result_frame = ttk.LabelFrame(main_frame, text="价格分析结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 10))
        
        # 设置结果区域的最小高度
        result_frame.configure(height=200)  # 固定高度，不随窗口扩展
        
        # 创建带滚动条的文本区域
        text_frame = ttk.Frame(result_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # 文本显示框
        self.result_text = tk.Text(text_frame, height=8, width=120)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 垂直滚动条
        text_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.result_text.yview)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.configure(yscrollcommand=text_scrollbar.set)
        
        # ========== 图表显示区域 ==========
        # 使用Frame包装图表区域，使其能够扩展
        chart_container_frame = ttk.Frame(main_frame)
        chart_container_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.chart_frame = ttk.LabelFrame(chart_container_frame, text="价格走势与分位分析", padding="5")
        self.chart_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建可滚动的图表区域
        self.create_scrollable_chart_area()
        
        # ========== 状态栏 ==========
        status_frame = ttk.Frame(main_frame, height=25)  # 固定高度
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)  # 阻止Frame自动调整大小
        
        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # 添加窗口大小信息标签 - 确保赋值给实例属性
        self.window_size_label = ttk.Label(status_frame, text="")
        self.window_size_label.pack(side=tk.RIGHT, padx=5)
        
        # 初始创建图表
        self.create_initial_chart()
        
        # 更新窗口大小标签
        self.update_window_size_label()
    
    def create_scrollable_chart_area(self):
        """创建可滚动的图表区域"""
        # 清除现有的图表容器内容
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # 创建主框架
        self.chart_container = ttk.Frame(self.chart_frame)
        self.chart_container.pack(fill=tk.BOTH, expand=True)
        
        # 创建滚动条框架
        scroll_frame = ttk.Frame(self.chart_container)
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Canvas和滚动条
        self.chart_canvas = tk.Canvas(scroll_frame, bg='white')
        self.chart_scrollbar_y = ttk.Scrollbar(scroll_frame, orient=tk.VERTICAL, command=self.chart_canvas.yview)
        self.chart_scrollbar_x = ttk.Scrollbar(scroll_frame, orient=tk.HORIZONTAL, command=self.chart_canvas.xview)
        
        self.chart_canvas.configure(yscrollcommand=self.chart_scrollbar_y.set, xscrollcommand=self.chart_scrollbar_x.set)
        
        # 使用grid布局管理器，更灵活
        self.chart_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.chart_scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.chart_scrollbar_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 配置网格权重
        scroll_frame.grid_rowconfigure(0, weight=1)
        scroll_frame.grid_columnconfigure(0, weight=1)
        
        # 创建内框架（用于放置图表）
        self.inner_chart_frame = ttk.Frame(self.chart_canvas)
        self.chart_canvas_window = self.chart_canvas.create_window((0, 0), window=self.inner_chart_frame, anchor=tk.NW)
        
        # 绑定事件以更新滚动区域
        self.inner_chart_frame.bind("<Configure>", self.update_chart_scrollregion)
        self.chart_canvas.bind("<Configure>", self.resize_chart_canvas_window)
        
        # 绑定鼠标滚轮事件
        self.chart_canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.chart_canvas.bind_all("<Shift-MouseWheel>", self.on_shift_mousewheel)
    
    def update_chart_scrollregion(self, event=None):
        """更新图表滚动区域"""
        # 更新Canvas的滚动区域
        self.chart_canvas.configure(scrollregion=self.chart_canvas.bbox("all"))
        # 更新窗口大小标签
        if hasattr(self, 'window_size_label'):
            self.update_window_size_label()
    
    def resize_chart_canvas_window(self, event):
        """调整Canvas窗口大小"""
        # 当Canvas大小改变时，调整内部框架的宽度
        self.chart_canvas.itemconfig(self.chart_canvas_window, width=event.width)
        # 更新窗口大小标签
        if hasattr(self, 'window_size_label'):
            self.update_window_size_label()
    
    def update_window_size_label(self):
        """更新窗口大小信息标签"""
        if hasattr(self, 'root') and hasattr(self, 'window_size_label'):
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            self.window_size_label.config(text=f"窗口: {width}x{height}")
    
    def on_mousewheel(self, event):
        """处理鼠标滚轮事件（垂直滚动）"""
        if event.delta:
            self.chart_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        else:
            if event.num == 4:  # Linux向上滚动
                self.chart_canvas.yview_scroll(-1, "units")
            elif event.num == 5:  # Linux向下滚动
                self.chart_canvas.yview_scroll(1, "units")
    
    def on_shift_mousewheel(self, event):
        """处理Shift+鼠标滚轮事件（水平滚动）"""
        if event.delta:
            self.chart_canvas.xview_scroll(int(-1*(event.delta/120)), "units")
        else:
            if event.num == 4:  # Linux向上滚动
                self.chart_canvas.xview_scroll(-1, "units")
            elif event.num == 5:  # Linux向下滚动
                self.chart_canvas.xview_scroll(1, "units")
    
    def create_initial_chart(self):
        """创建初始的空白图表"""
        # 清除inner_chart_frame中的所有组件
        for widget in self.inner_chart_frame.winfo_children():
            widget.destroy()
        
        # 清除现有图表
        if self.figure is not None:
            plt.close(self.figure)
            self.figure = None
        
        # 清除提示标签
        if self.hint_label is not None:
            self.hint_label.destroy()
            self.hint_label = None
        
        # 创建新的图表 - 使用更大的尺寸
        self.figure, self.ax = plt.subplots(figsize=(14, 8))
        self.ax.set_title("请先获取数据并选择商品进行分析", fontsize=14)
        self.ax.set_xlabel("日期")
        self.ax.set_ylabel("价格")
        self.ax.grid(True, alpha=0.3)
        
        # 添加说明文本
        self.ax.text(0.5, 0.5, 
                    "1. 输入日期范围并点击'获取期货数据'\n2. 或点击'读取CSV数据'加载已保存的数据\n3. 从下拉列表中选择商品\n4. 点击'分析价格位置'查看详细分析", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=self.ax.transAxes, fontsize=12, 
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.5))
        
        # 创建并显示空白图表
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.inner_chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加matplotlib工具栏
        self.create_matplotlib_toolbar()
        
        # 更新滚动区域
        self.update_chart_scrollregion()
    
    def create_matplotlib_toolbar(self):
        """创建matplotlib工具栏"""
        if hasattr(self, 'toolbar') and self.toolbar is not None:
            self.toolbar.destroy()
        
        # 创建matplotlib导航工具栏
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.inner_chart_frame)
        self.toolbar.update()
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # 绑定键盘事件
        self.canvas.mpl_connect("key_press_event", key_press_handler)
    
    def start_fetch_data(self):
        """开始获取数据（在新线程中）"""
        start_date = self.start_date_var.get()
        end_date = self.end_date_var.get()
        
        # 验证日期
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("错误", "日期格式错误，请使用YYYY-MM-DD格式")
            return
        
        # 禁用按钮，防止重复点击
        self.fetch_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.progress_label.config(text="开始获取数据...")
        
        # 在新线程中获取数据
        thread = threading.Thread(target=self.fetch_data_thread, args=(start_date, end_date))
        thread.daemon = True
        thread.start()
    
    def fetch_data_thread(self, start_date, end_date):
        """获取数据的线程函数"""
        def progress_callback(progress, message):
            self.root.after(0, self.update_progress, progress, message)
        
        try:
            # 获取数据
            data = self.fetcher.get_future_data(start_date, end_date, progress_callback)
            
            # 在主线程中处理结果
            self.root.after(0, self.handle_fetch_result, data)
        except Exception as e:
            self.root.after(0, self.handle_fetch_error, str(e))
    
    def update_progress(self, progress, message):
        """更新进度条"""
        self.progress_var.set(progress)
        self.progress_label.config(text=message)
    
    def handle_fetch_result(self, data):
        """处理获取数据的结果"""
        self.fetch_btn.config(state=tk.NORMAL)
        
        if data is not None and not data.empty:
            self.data = data
            self.analyzer.set_data(data)
            
            # 更新商品列表
            products = self.analyzer.get_available_products()
            self.product_combo['values'] = products
            if products:
                self.product_var.set(products[0])
            
            # 启用分析按钮
            self.analyze_btn.config(state=tk.NORMAL)
            self.save_btn.config(state=tk.NORMAL)
            self.quick_analysis_btn.config(state=tk.NORMAL)
            self.clear_data_btn.config(state=tk.NORMAL)
            
            # 显示数据摘要
            self.show_data_summary()
            
            self.status_label.config(text=f"数据获取成功，共{len(data)}条记录，{len(products)}个商品")
            messagebox.showinfo("成功", f"数据获取成功！\n共获取{len(data)}条记录，{len(products)}个商品")
        else:
            self.status_label.config(text="数据获取失败或未获取到数据")
            messagebox.showwarning("警告", "未获取到数据，请检查日期或网络连接")
    
    def handle_fetch_error(self, error_msg):
        """处理获取数据时的错误"""
        self.fetch_btn.config(state=tk.NORMAL)
        self.status_label.config(text=f"数据获取失败: {error_msg}")
        messagebox.showerror("错误", f"获取数据时发生错误:\n{error_msg}")
    
    def load_csv_data(self):
        """读取CSV文件数据"""
        file_path = filedialog.askopenfilename(
            title="选择CSV数据文件",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")],
            initialdir="."  # 初始目录为当前目录
        )
        
        if not file_path:
            return  # 用户取消了选择
        
        try:
            # 显示加载状态
            self.progress_label.config(text="正在加载CSV数据...")
            self.root.update()
            
            # 读取CSV文件
            data = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # 检查必要列是否存在
            required_columns = ["商品", "日期"]
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                messagebox.showerror("错误", f"CSV文件缺少必要列: {', '.join(missing_columns)}")
                self.progress_label.config(text="CSV文件加载失败")
                return
            
            # 处理数据
            self.data = data
            self.analyzer.set_data(data)
            
            # 更新商品列表
            products = self.analyzer.get_available_products()
            self.product_combo['values'] = products
            if products:
                self.product_var.set(products[0])
            
            # 启用分析按钮
            self.analyze_btn.config(state=tk.NORMAL)
            self.save_btn.config(state=tk.NORMAL)
            self.quick_analysis_btn.config(state=tk.NORMAL)
            self.clear_data_btn.config(state=tk.NORMAL)
            
            # 显示数据摘要
            self.show_data_summary()
            
            self.status_label.config(text=f"CSV数据加载成功，共{len(data)}条记录，{len(products)}个商品")
            messagebox.showinfo("成功", f"CSV数据加载成功！\n文件: {os.path.basename(file_path)}\n共{len(data)}条记录，{len(products)}个商品")
            
        except Exception as e:
            self.status_label.config(text=f"CSV数据加载失败: {str(e)}")
            messagebox.showerror("错误", f"加载CSV文件时发生错误:\n{str(e)}")
    
    def clear_data(self):
        """清空当前数据"""
        if messagebox.askyesno("确认", "确定要清空当前数据吗？"):
            self.data = None
            self.analyzer.set_data(None)
            
            # 清空商品列表
            self.product_combo['values'] = []
            self.product_var.set("")
            
            # 禁用分析按钮
            self.analyze_btn.config(state=tk.DISABLED)
            self.save_btn.config(state=tk.DISABLED)
            self.quick_analysis_btn.config(state=tk.DISABLED)
            self.clear_data_btn.config(state=tk.DISABLED)
            
            # 清空结果显示
            self.result_text.delete(1.0, tk.END)
            
            # 恢复初始图表
            self.create_initial_chart()
            
            self.status_label.config(text="数据已清空")
            messagebox.showinfo("提示", "数据已清空")
    
    def show_data_summary(self):
        """显示数据摘要"""
        if self.data is not None and not self.data.empty:
            # 获取数据来源信息
            data_source = "网络获取"
            if hasattr(self, 'current_csv_file'):
                data_source = f"CSV文件: {os.path.basename(self.current_csv_file)}"
            
            summary = f"""
【数据获取成功】
数据来源: {data_source}
获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
数据日期范围: {self.data['日期'].min()} 至 {self.data['日期'].max()}
总记录数: {len(self.data)}
商品数量: {len(self.analyzer.get_available_products())}
"""
            if "交易所" in self.data.columns:
                summary += f"交易所列表: {', '.join(self.data['交易所'].dropna().unique())}\n"
            
            summary += f"""
--------------------------------
数据预览（前5条）:
{self.data.head().to_string(index=False)}
"""
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(1.0, summary)
    
    def analyze_selected_product(self):
        """分析选中的商品"""
        product_name = self.product_var.get()
        if not product_name:
            messagebox.showwarning("警告", "请先选择要分析的商品")
            return
        
        # 显示分析中状态
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, f"正在分析 {product_name}...")
        self.root.update()
        
        # 执行分析
        summary, product_data, analysis_dict = self.analyzer.get_analysis_summary(product_name)
        
        # 显示分析结果
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, summary)
        
        # 更新图表
        if product_data is not None and analysis_dict is not None:
            self.update_chart(product_data, analysis_dict)
        
        # 更新状态
        self.status_label.config(text=f"完成分析: {product_name}")
    
    def quick_scan_all_products(self):
        """快速扫描所有商品"""
        if self.data is None or self.data.empty:
            messagebox.showwarning("警告", "请先获取数据")
            return
        
        products = self.analyzer.get_available_products()
        if not products:
            messagebox.showwarning("警告", "没有可分析的商品")
            return
        
        # 显示扫描中状态
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, f"正在快速扫描 {len(products)} 个商品...\n\n")
        self.root.update()
        
        results = []
        for i, product in enumerate(products):
            self.result_text.insert(tk.END, f"分析 {product}...")
            self.root.update()
            
            try:
                _, _, analysis_dict = self.analyzer.get_analysis_summary(product)
                future_info = analysis_dict.get("future", {})
                
                if "percentile" in future_info:
                    status = future_info.get("status", "未知")
                    color = future_info.get("color", "black")
                    
                    # 根据百分位添加表情符号
                    percentile = future_info["percentile"]
                    if percentile >= 99:
                        emoji = "🔴"
                    elif percentile >= 80:
                        emoji = "🟠"
                    elif percentile <= 1:
                        emoji = "🟢"
                    elif percentile <= 20:
                        emoji = "🟡"
                    else:
                        emoji = "🔵"
                    
                    results.append((product, percentile, status, emoji))
                    self.result_text.insert(tk.END, f" 完成 {emoji}\n")
                else:
                    results.append((product, None, "数据不足", "❓"))
                    self.result_text.insert(tk.END, " 数据不足\n")
            except Exception as e:
                results.append((product, None, f"错误: {str(e)}", "❌"))
                self.result_text.insert(tk.END, f" 错误\n")
            
            self.root.update()
        
        # 按百分位排序
        results_with_percentile = [(p, perc, status, emoji) for p, perc, status, emoji in results if perc is not None]
        results_without_percentile = [(p, perc, status, emoji) for p, perc, status, emoji in results if perc is None]
        
        # 按百分位降序排列（高估的在前）
        results_with_percentile.sort(key=lambda x: x[1], reverse=True)
        
        # 显示汇总结果
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, f"【快速扫描结果 - 共分析 {len(products)} 个商品】\n\n")
        self.result_text.insert(tk.END, "【高估/极端高估商品】\n")
        
        high_estimated = [r for r in results_with_percentile if r[1] >= 80]
        if high_estimated:
            for product, percentile, status, emoji in high_estimated:
                self.result_text.insert(tk.END, f"{emoji} {product}: {percentile:.1f}% - {status}\n")
        else:
            self.result_text.insert(tk.END, "暂无\n")
        
        self.result_text.insert(tk.END, "\n【低估/极端低估商品】\n")
        low_estimated = [r for r in results_with_percentile if r[1] <= 20]
        if low_estimated:
            for product, percentile, status, emoji in low_estimated:
                self.result_text.insert(tk.END, f"{emoji} {product}: {percentile:.1f}% - {status}\n")
        else:
            self.result_text.insert(tk.END, "暂无\n")
        
        self.result_text.insert(tk.END, "\n【合理区间商品】\n")
        normal_estimated = [r for r in results_with_percentile if 20 < r[1] < 80]
        if normal_estimated:
            for product, percentile, status, emoji in normal_estimated:
                self.result_text.insert(tk.END, f"{emoji} {product}: {percentile:.1f}%\n")
        else:
            self.result_text.insert(tk.END, "暂无\n")
        
        if results_without_percentile:
            self.result_text.insert(tk.END, f"\n【数据不足商品 ({len(results_without_percentile)}个)】\n")
            for product, _, status, emoji in results_without_percentile:
                self.result_text.insert(tk.END, f"{emoji} {product}: {status}\n")
        
        # 更新状态
        self.status_label.config(text=f"快速扫描完成，发现{len(high_estimated)}个高估商品，{len(low_estimated)}个低估商品")
    
    def update_chart(self, product_data, analysis_dict):
        """更新图表显示"""
        # 清除inner_chart_frame中的所有组件
        for widget in self.inner_chart_frame.winfo_children():
            widget.destroy()
        
        # 清除现有图表
        if hasattr(self, 'figure') and self.figure is not None:
            plt.close(self.figure)
            self.figure = None
        
        # 清除工具栏引用
        if hasattr(self, 'toolbar') and self.toolbar is not None:
            self.toolbar.destroy()
            self.toolbar = None
        
        # 清除提示标签引用
        if self.hint_label is not None:
            self.hint_label.destroy()
            self.hint_label = None
        
        # 获取窗口大小，动态调整图表尺寸
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # 根据窗口大小调整图表尺寸
        chart_width = max(14, window_width / 80)  # 动态宽度
        chart_height = max(8, window_height / 100)  # 动态高度
        
        # 创建新的图表 - 使用动态尺寸
        self.figure, axes = plt.subplots(2, 2, figsize=(chart_width, chart_height))
        
        # 获取分析结果
        spot_info = analysis_dict.get("spot", {})
        future_info = analysis_dict.get("future", {})
        product_name = analysis_dict.get("product_name", "未知商品")
        
        # 第一幅图：期货价格走势
        ax1 = axes[0, 0]
        if "主力合约价格" in product_data.columns:
            prices = product_data["主力合约价格"].dropna()
            dates = product_data.loc[prices.index, "日期"]
            
            ax1.plot(dates, prices, label='期货价格', color='blue', linewidth=2)
            ax1.set_xlabel('日期', fontsize=10)
            ax1.set_ylabel('期货价格', fontsize=10)
            ax1.set_title(f'{product_name} - 期货价格走势', fontsize=12, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            
            # 添加分位数线
            if "historical_80_percentile" in future_info:
                ax1.axhline(y=future_info["historical_80_percentile"], color='orange', linestyle='--', 
                           alpha=0.7, label=f'80%分位: {future_info["historical_80_percentile"]:.2f}')
            if "historical_99_percentile" in future_info:
                ax1.axhline(y=future_info["historical_99_percentile"], color='red', linestyle='--', 
                           alpha=0.7, label=f'99%分位: {future_info["historical_99_percentile"]:.2f}')
            if "historical_20_percentile" in future_info:
                ax1.axhline(y=future_info["historical_20_percentile"], color='green', linestyle='--', 
                           alpha=0.7, label=f'20%分位: {future_info["historical_20_percentile"]:.2f}')
            if "historical_1_percentile" in future_info:
                ax1.axhline(y=future_info["historical_1_percentile"], color='darkgreen', linestyle='--', 
                           alpha=0.7, label=f'1%分位: {future_info["historical_1_percentile"]:.2f}')
            
            # 标注最新价格
            if len(prices) > 0:
                latest_price = prices.iloc[-1]
                latest_date = dates.iloc[-1]
                
                # 根据价格状态选择标注颜色
                color = future_info.get("color", "black")
                ax1.scatter(latest_date, latest_price, color=color, s=100, zorder=5)
                ax1.annotate(f'当前: {latest_price:.2f}\n({future_info.get("percentile", "N/A"):.1f}%)', 
                            xy=(latest_date, latest_price), 
                            xytext=(10, 10), 
                            textcoords='offset points',
                            fontsize=9,
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8),
                            color=color)
            
            ax1.legend(loc='upper left', fontsize=8)
        
        # 第二幅图：现货价格走势
        ax2 = axes[0, 1]
        if "现货价格" in product_data.columns:
            prices = product_data["现货价格"].dropna()
            dates = product_data.loc[prices.index, "日期"]
            
            ax2.plot(dates, prices, label='现货价格', color='purple', linewidth=2)
            ax2.set_xlabel('日期', fontsize=10)
            ax2.set_ylabel('现货价格', fontsize=10)
            ax2.set_title(f'{product_name} - 现货价格走势', fontsize=12, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            
            # 添加分位数线
            if "historical_80_percentile" in spot_info:
                ax2.axhline(y=spot_info["historical_80_percentile"], color='orange', linestyle='--', 
                           alpha=0.7, label=f'80%分位: {spot_info["historical_80_percentile"]:.2f}')
            if "historical_99_percentile" in spot_info:
                ax2.axhline(y=spot_info["historical_99_percentile"], color='red', linestyle='--', 
                           alpha=0.7, label=f'99%分位: {spot_info["historical_99_percentile"]:.2f}')
            if "historical_20_percentile" in spot_info:
                ax2.axhline(y=spot_info["historical_20_percentile"], color='green', linestyle='--', 
                           alpha=0.7, label=f'20%分位: {spot_info["historical_20_percentile"]:.2f}')
            if "historical_1_percentile" in spot_info:
                ax2.axhline(y=spot_info["historical_1_percentile"], color='darkgreen', linestyle='--', 
                           alpha=0.7, label=f'1%分位: {spot_info["historical_1_percentile"]:.2f}')
            
            # 标注最新价格
            if len(prices) > 0:
                latest_price = prices.iloc[-1]
                latest_date = dates.iloc[-1]
                
                # 根据价格状态选择标注颜色
                color = spot_info.get("color", "black")
                ax2.scatter(latest_date, latest_price, color=color, s=100, zorder=5)
                ax2.annotate(f'当前: {latest_price:.2f}\n({spot_info.get("percentile", "N/A"):.1f}%)', 
                            xy=(latest_date, latest_price), 
                            xytext=(10, 10), 
                            textcoords='offset points',
                            fontsize=9,
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8),
                            color=color)
            
            ax2.legend(loc='upper left', fontsize=8)
        
        # 第三幅图：基差走势
        ax3 = axes[1, 0]
        if "基差" in product_data.columns:
            basis = product_data["基差"].dropna()
            dates = product_data.loc[basis.index, "日期"]
            
            # 根据基差正负使用不同颜色
            colors = ['green' if b >= 0 else 'red' for b in basis]
            ax3.bar(dates, basis, color=colors, alpha=0.6, width=0.8)
            ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax3.set_xlabel('日期', fontsize=10)
            ax3.set_ylabel('基差', fontsize=10)
            ax3.set_title(f'{product_name} - 基差走势', fontsize=12, fontweight='bold')
            ax3.grid(True, alpha=0.3)
            
            # 添加最新基差标注
            if len(basis) > 0:
                latest_basis = basis.iloc[-1]
                latest_date = dates.iloc[-1]
                ax3.annotate(f'当前: {latest_basis:.2f}', 
                            xy=(latest_date, latest_basis), 
                            xytext=(10, 10 if latest_basis >= 0 else -20), 
                            textcoords='offset points',
                            fontsize=9,
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8))
        
        # 第四幅图：价格分布直方图
        ax4 = axes[1, 1]
        if "主力合约价格" in product_data.columns:
            prices = product_data["主力合约价格"].dropna()
            
            # 绘制直方图
            n, bins, patches = ax4.hist(prices, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
            
            # 标记当前价格位置
            if "current_price" in future_info:
                current_price = future_info["current_price"]
                ax4.axvline(x=current_price, color='red', linewidth=2, linestyle='--', 
                           label=f'当前价格: {current_price:.2f}')
            
            # 标记关键分位数
            colors = ['green', 'lightgreen', 'orange', 'red']
            percentiles = [1, 20, 80, 99]
            percentile_values = []
            percentile_labels = []
            
            for p in percentiles:
                try:
                    value = np.percentile(prices, p)
                    percentile_values.append(value)
                    percentile_labels.append(f'{p}%')
                except:
                    pass
            
            for i, (value, label) in enumerate(zip(percentile_values, percentile_labels)):
                if i < len(colors):
                    ax4.axvline(x=value, color=colors[i], linewidth=1.5, linestyle=':', 
                               alpha=0.7, label=f'{label}分位: {value:.2f}')
            
            ax4.set_xlabel('价格', fontsize=10)
            ax4.set_ylabel('频次', fontsize=10)
            ax4.set_title(f'{product_name} - 价格分布直方图', fontsize=12, fontweight='bold')
            ax4.grid(True, alpha=0.3)
            ax4.legend(loc='upper right', fontsize=8)
        
        self.figure.suptitle(f'{product_name} - 价格位置分析 ({future_info.get("status", "未知状态")})', 
                            fontsize=14, fontweight='bold')
        self.figure.tight_layout()
        
        # 嵌入到Tkinter
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.inner_chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加matplotlib工具栏
        self.create_matplotlib_toolbar()
        
        # 创建提示标签（只创建一个）
        if self.hint_label is None:
            self.hint_label = ttk.Label(self.inner_chart_frame, 
                                      text="提示：使用鼠标滚轮可以垂直滚动，Shift+滚轮可以水平滚动。\n也可以使用右侧和底部的滚动条，或者使用上方的matplotlib工具栏进行缩放和平移。",
                                      font=('Microsoft YaHei', 8))
            self.hint_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        # 更新滚动区域
        self.update_chart_scrollregion()
        
        # 更新窗口大小标签
        if hasattr(self, 'window_size_label'):
            self.update_window_size_label()
    
    def save_data(self):
        """保存数据到CSV文件"""
        if self.data is None or self.data.empty:
            messagebox.showwarning("警告", "没有数据可保存")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")],
            initialfile="future_data.csv"
        )
        
        if file_path:
            try:
                self.data.to_csv(file_path, index=False, encoding='utf-8-sig')
                self.status_label.config(text=f"数据已保存到: {file_path}")
                messagebox.showinfo("成功", f"数据已成功保存到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件时发生错误:\n{str(e)}")

# ========== 程序入口 ==========
if __name__ == "__main__":
    root = tk.Tk()
    app = FutureAnalysisApp(root)
    root.mainloop()