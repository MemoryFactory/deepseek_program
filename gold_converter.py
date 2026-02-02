import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
from datetime import datetime

class GoldPriceConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("黄金价格转换器")
        self.root.geometry("500x450")
        
        # 常量
        self.OUNCE_TO_GRAM = 31.1035  # 1金衡盎司 = 31.1035克
        
        # 汇率变量
        self.exchange_rate = tk.DoubleVar(value=7.25)  # 默认汇率
        self.rate_source = tk.StringVar(value="手动设置")
        
        # 创建界面
        self.create_widgets()
        
        # 启动时自动获取汇率
        self.root.after(1000, self.auto_fetch_rate)
    
    def create_widgets(self):
        # 标题
        title_label = tk.Label(self.root, text="国际与国内黄金价格换算器", 
                              font=("Microsoft YaHei", 16, "bold"))
        title_label.pack(pady=15)
        
        # 汇率区域
        rate_frame = tk.LabelFrame(self.root, text="汇率设置", padx=10, pady=10)
        rate_frame.pack(padx=20, pady=10, fill="x")
        
        # 汇率显示和手动输入
        tk.Label(rate_frame, text="当前汇率 (1美元):").grid(row=0, column=0, sticky="w", padx=5)
        
        rate_entry = tk.Entry(rate_frame, textvariable=self.exchange_rate, width=10)
        rate_entry.grid(row=0, column=1, padx=5)
        tk.Label(rate_frame, text="人民币").grid(row=0, column=2, padx=5)
        
        # 汇率来源显示
        tk.Label(rate_frame, text="数据来源:").grid(row=1, column=0, sticky="w", padx=5, pady=(5,0))
        tk.Label(rate_frame, textvariable=self.rate_source, fg="blue").grid(row=1, column=1, columnspan=2, 
                                                                          sticky="w", padx=5, pady=(5,0))
        
        # 汇率按钮
        btn_frame = tk.Frame(rate_frame)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        tk.Button(btn_frame, text="获取实时汇率", command=self.fetch_exchange_rate,
                 bg="#4CAF50", fg="white", padx=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="使用默认汇率", command=self.use_default_rate,
                 bg="#2196F3", fg="white", padx=15).pack(side="left", padx=5)
        
        # 转换区域
        convert_frame = tk.LabelFrame(self.root, text="价格转换", padx=10, pady=10)
        convert_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        # 国际金价输入
        tk.Label(convert_frame, text="国际金价 (美元/盎司):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.intl_entry = tk.Entry(convert_frame, width=15)
        self.intl_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(convert_frame, text="美元/盎司").grid(row=0, column=2, padx=5, pady=5)
        
        tk.Button(convert_frame, text="→ 转国内价", command=self.intl_to_domestic,
                 bg="#FF9800", fg="white").grid(row=0, column=3, padx=10, pady=5)
        
        # 国内金价输入
        tk.Label(convert_frame, text="国内基础金价 (元/克):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.domestic_entry = tk.Entry(convert_frame, width=15)
        self.domestic_entry.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(convert_frame, text="元/克").grid(row=1, column=2, padx=5, pady=5)
        
        tk.Button(convert_frame, text="→ 转国际价", command=self.domestic_to_intl,
                 bg="#FF9800", fg="white").grid(row=1, column=3, padx=10, pady=5)
        
        # 转换按钮
        tk.Button(convert_frame, text="双向同步转换", command=self.sync_convert,
                 bg="#9C27B0", fg="white", padx=20).grid(row=2, column=0, columnspan=4, pady=15)
        
        # 结果区域
        result_frame = tk.LabelFrame(self.root, text="转换结果", padx=10, pady=10)
        result_frame.pack(padx=20, pady=10, fill="x")
        
        self.result_text = tk.Text(result_frame, height=4, width=50, font=("Courier", 10))
        self.result_text.pack()
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 绑定回车键
        self.intl_entry.bind("<Return>", lambda e: self.intl_to_domestic())
        self.domestic_entry.bind("<Return>", lambda e: self.domestic_to_intl())
        rate_entry.bind("<Return>", lambda e: self.sync_convert())
    
    def fetch_exchange_rate(self):
        """从API获取实时汇率"""
        def fetch():
            self.status_var.set("正在获取实时汇率...")
            try:
                # 尝试多个汇率API源
                api_sources = [
                    "https://api.exchangerate-api.com/v4/latest/USD",
                    "https://open.er-api.com/v6/latest/USD",
                    "https://api.currencyapi.com/v3/latest?apikey=free&base_currency=USD"
                ]
                
                rate_found = False
                for api_url in api_sources:
                    try:
                        response = requests.get(api_url, timeout=5)
                        if response.status_code == 200:
                            data = response.json()
                            if 'CNY' in data.get('rates', {}):
                                rate = data['rates']['CNY']
                                self.exchange_rate.set(round(rate, 4))
                                self.rate_source.set(f"API: {api_url.split('//')[1].split('/')[0]}")
                                rate_found = True
                                
                                # 记录更新时间
                                update_time = datetime.now().strftime("%H:%M:%S")
                                self.show_result(f"✓ 汇率更新成功！\n1美元 = {rate:.4f}人民币\n更新时间: {update_time}")
                                break
                    except:
                        continue
                
                if not rate_found:
                    # 如果API都失败，使用备用方法（模拟数据）
                    self.show_result("⚠ API暂时不可用，使用模拟汇率数据")
                    self.exchange_rate.set(7.2543)
                    self.rate_source.set("模拟数据")
                
            except Exception as e:
                messagebox.showerror("错误", f"获取汇率失败: {str(e)}")
                self.status_var.set("汇率获取失败")
            finally:
                self.status_var.set("就绪")
        
        # 在新线程中获取汇率，避免界面卡顿
        thread = threading.Thread(target=fetch)
        thread.daemon = True
        thread.start()
    
    def auto_fetch_rate(self):
        """程序启动时自动获取汇率"""
        self.fetch_exchange_rate()
    
    def use_default_rate(self):
        """使用默认汇率"""
        self.exchange_rate.set(7.25)
        self.rate_source.set("手动设置")
        self.show_result("✓ 已使用默认汇率: 7.25")
    
    def intl_to_domestic(self):
        """国际转国内"""
        try:
            intl_price = float(self.intl_entry.get())
            rate = self.exchange_rate.get()
            
            # 计算: 国内金价 = 国际金价 / 31.1035 * 汇率
            domestic_price = intl_price / self.OUNCE_TO_GRAM * rate
            
            self.domestic_entry.delete(0, tk.END)
            self.domestic_entry.insert(0, f"{domestic_price:.2f}")
            
            result = (f"国际: {intl_price} 美元/盎司\n"
                     f"汇率: 1美元 = {rate} 人民币\n"
                     f"换算: {intl_price} ÷ {self.OUNCE_TO_GRAM} × {rate}\n"
                     f"国内: {domestic_price:.2f} 元/克")
            self.show_result(result)
            
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的国际金价数字")
    
    def domestic_to_intl(self):
        """国内转国际"""
        try:
            domestic_price = float(self.domestic_entry.get())
            rate = self.exchange_rate.get()
            
            # 计算: 国际金价 = 国内金价 * 31.1035 / 汇率
            intl_price = domestic_price * self.OUNCE_TO_GRAM / rate
            
            self.intl_entry.delete(0, tk.END)
            self.intl_entry.insert(0, f"{intl_price:.2f}")
            
            result = (f"国内: {domestic_price} 元/克\n"
                     f"汇率: 1美元 = {rate} 人民币\n"
                     f"换算: {domestic_price} × {self.OUNCE_TO_GRAM} ÷ {rate}\n"
                     f"国际: {intl_price:.2f} 美元/盎司")
            self.show_result(result)
            
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的国内金价数字")
    
    def sync_convert(self):
        """双向同步转换"""
        # 如果国际金价有输入，优先用它转换
        if self.intl_entry.get():
            self.intl_to_domestic()
        elif self.domestic_entry.get():
            self.domestic_to_intl()
        else:
            messagebox.showinfo("提示", "请输入国际或国内金价进行转换")
    
    def show_result(self, text):
        """在结果区域显示信息"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, text)
        
        # 更新状态栏
        self.status_var.set(f"汇率: {self.exchange_rate.get()} | 最后更新: {datetime.now().strftime('%H:%M:%S')}")

def main():
    root = tk.Tk()
    app = GoldPriceConverter(root)
    
    # 设置窗口图标和样式
    try:
        root.iconbitmap("gold.ico")  # 如果有图标文件的话
    except:
        pass
    
    # 设置样式
    style = ttk.Style()
    style.theme_use('clam')
    
    root.mainloop()

if __name__ == "__main__":
    # 确保已安装requests库
    try:
        import requests
    except ImportError:
        print("请先安装requests库: pip install requests")
        input("按Enter键退出...")
        exit(1)
    
    main()