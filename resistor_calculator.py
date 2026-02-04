import tkinter as tk
from tkinter import ttk, messagebox
import re

class ResistorColorCodeCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("电阻色环计算器")
        self.root.geometry("800x900")
        
        # 颜色定义和对应的值
        self.color_values = {
            '黑': {'digit': 0, 'multiplier': 1, 'tolerance': None},
            '棕': {'digit': 1, 'multiplier': 10, 'tolerance': '±1%'},
            '红': {'digit': 2, 'multiplier': 100, 'tolerance': '±2%'},
            '橙': {'digit': 3, 'multiplier': 1000, 'tolerance': None},
            '黄': {'digit': 4, 'multiplier': 10000, 'tolerance': None},
            '绿': {'digit': 5, 'multiplier': 100000, 'tolerance': '±0.5%'},
            '蓝': {'digit': 6, 'multiplier': 1000000, 'tolerance': '±0.25%'},
            '紫': {'digit': 7, 'multiplier': 10000000, 'tolerance': '±0.1%'},
            '灰': {'digit': 8, 'multiplier': 100000000, 'tolerance': '±0.05%'},
            '白': {'digit': 9, 'multiplier': 1000000000, 'tolerance': None},
            '金': {'digit': None, 'multiplier': 0.1, 'tolerance': '±5%'},
            '银': {'digit': None, 'multiplier': 0.01, 'tolerance': '±10%'},
            '无': {'digit': None, 'multiplier': None, 'tolerance': '±20%'}
        }
        
        # 颜色显示映射
        self.color_display = {
            '黑': 'black', '棕': '#8B4513', '红': 'red', '橙': 'orange',
            '黄': 'yellow', '绿': 'green', '蓝': 'blue', '紫': 'purple',
            '灰': 'gray', '白': 'white', '金': '#FFD700', '银': '#C0C0C0',
            '无': '#F0F0F0'
        }
        
        # 色环类型配置
        self.ring_types = {
            '4环': {'digit_rings': 2, 'multiplier_index': 2, 'tolerance_index': 3},
            '5环': {'digit_rings': 3, 'multiplier_index': 3, 'tolerance_index': 4},
            '6环': {'digit_rings': 4, 'multiplier_index': 4, 'tolerance_index': 5}
        }
        
        self.current_ring_type = '5环'  # 默认五环
        self.ring_vars = []
        self.ring_buttons = []
        
        self.setup_ui()
    
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题
        title_label = ttk.Label(main_frame, text="电阻色环计算器", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # 色环类型选择
        self.create_ring_type_selection(main_frame)
        
        # 色环选择区域
        self.color_frame = ttk.LabelFrame(main_frame, text="选择色环颜色", padding=10)
        self.color_frame.grid(row=2, column=0, padx=5, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 创建默认的色环选择界面（五环）
        self.create_color_selection()
        
        # 结果显示区域
        self.create_result_display(main_frame)
        
        # 阻值反向计算区域
        self.create_reverse_calculation(main_frame)
        
        # 颜色说明区域（带滚动条）
        self.create_color_legend_with_scroll(main_frame)
    
    def create_ring_type_selection(self, parent):
        frame = ttk.Frame(parent)
        frame.grid(row=1, column=0, columnspan=2, pady=5)
        
        ttk.Label(frame, text="色环类型:").pack(side=tk.LEFT, padx=5)
        
        self.ring_type_var = tk.StringVar(value=self.current_ring_type)
        ring_type_combo = ttk.Combobox(frame, textvariable=self.ring_type_var, 
                                      values=list(self.ring_types.keys()),
                                      state="readonly", width=10)
        ring_type_combo.pack(side=tk.LEFT, padx=5)
        ring_type_combo.bind("<<ComboboxSelected>>", self.on_ring_type_changed)
    
    def create_color_selection(self):
        # 清除现有的色环选择部件
        for widget in self.color_frame.winfo_children():
            widget.destroy()
        
        config = self.ring_types[self.current_ring_type]
        digit_rings = config['digit_rings']
        total_rings = digit_rings + 2  # 加上乘数环和精度环
        
        # 创建色环标签和选择器
        self.ring_vars = []
        self.ring_buttons = []
        
        # 创建列标题
        for i in range(total_rings):
            if i < digit_rings:
                label_text = f"第{i+1}环(数字)"
            elif i == config['multiplier_index']:
                label_text = "乘数环"
            else:
                label_text = "精度环"
            
            label = ttk.Label(self.color_frame, text=label_text)
            label.grid(row=0, column=i, padx=5)
        
        # 创建颜色选择下拉框
        for i in range(total_rings):
            # 根据位置设置默认颜色
            if i < digit_rings:  # 数字环
                default_color = '棕' if i == 0 else '黑'
            elif i == config['multiplier_index']:  # 乘数环
                default_color = '黑'
            else:  # 精度环
                default_color = '金'
            
            var = tk.StringVar(value=default_color)
            var.trace('w', lambda *args, idx=i: self.update_ring_color(idx))
            
            combobox = ttk.Combobox(self.color_frame, textvariable=var, 
                                   values=list(self.color_values.keys()),
                                   state="readonly", width=8)
            combobox.grid(row=1, column=i, padx=5, pady=5)
            
            # 颜色显示框
            color_frame = tk.Frame(self.color_frame, width=60, height=30, 
                                  bg=self.color_display[var.get()],
                                  relief=tk.RAISED, borderwidth=2)
            color_frame.grid(row=2, column=i, padx=5, pady=5)
            color_frame.grid_propagate(False)
            
            self.ring_vars.append(var)
            self.ring_buttons.append(color_frame)
        
        # 计算按钮
        calc_button = ttk.Button(self.color_frame, text="计算阻值", command=self.calculate_from_colors)
        calc_button.grid(row=3, column=0, columnspan=total_rings, pady=10)
        
        # 随机示例按钮
        example_button = ttk.Button(self.color_frame, text="随机示例", command=self.random_example)
        example_button.grid(row=4, column=0, columnspan=total_rings, pady=5)
    
    def create_result_display(self, parent):
        frame = ttk.LabelFrame(parent, text="计算结果", padding=10)
        frame.grid(row=3, column=0, padx=5, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 阻值显示
        ttk.Label(frame, text="阻值:").grid(row=0, column=0, sticky=tk.W)
        self.resistance_label = ttk.Label(frame, text="0Ω", font=("Arial", 14, "bold"))
        self.resistance_label.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        # 精度显示
        ttk.Label(frame, text="精度:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.tolerance_label = ttk.Label(frame, text="±0%", font=("Arial", 14, "bold"))
        self.tolerance_label.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        
        # 色环类型显示
        ttk.Label(frame, text="类型:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.type_label = ttk.Label(frame, text=self.current_ring_type, font=("Arial", 12))
        self.type_label.grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)
        
        # 详细结果显示
        self.details_label = ttk.Label(frame, text="", font=("Arial", 10))
        self.details_label.grid(row=3, column=0, columnspan=2, pady=10)
    
    def create_reverse_calculation(self, parent):
        frame = ttk.LabelFrame(parent, text="阻值反向计算", padding=10)
        frame.grid(row=3, column=1, padx=5, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 输入标签
        ttk.Label(frame, text="输入阻值 (如: 1.5k, 470, 2.2M):").grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 阻值输入框
        self.reverse_entry = ttk.Entry(frame, width=20)
        self.reverse_entry.grid(row=1, column=0, columnspan=2, pady=5)
        self.reverse_entry.insert(0, "1k")
        
        # 计算按钮
        reverse_button = ttk.Button(frame, text="计算色环", command=self.calculate_from_resistance)
        reverse_button.grid(row=2, column=0, columnspan=2, pady=10)
        
        # 输入说明
        ttk.Label(frame, text="支持的单位:\nΩ (或省略), k, M\n\n示例:\n1.5k = 1500Ω\n470 = 470Ω\n2.2M = 2200000Ω", 
                 justify=tk.LEFT).grid(row=3, column=0, columnspan=2, pady=10)
    
    def create_color_legend_with_scroll(self, parent):
        # 创建外部框架
        outer_frame = ttk.LabelFrame(parent, text="颜色说明", padding=5)
        outer_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        parent.grid_rowconfigure(4, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        outer_frame.grid_rowconfigure(0, weight=1)
        outer_frame.grid_columnconfigure(0, weight=1)
        
        # 创建Canvas和滚动条
        canvas = tk.Canvas(outer_frame, height=180)
        scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
        
        # 创建可滚动的框架
        scrollable_frame = ttk.Frame(canvas)
        
        # 配置Canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 将可滚动框架添加到Canvas
        canvas_frame = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # 绑定配置事件以调整Canvas大小
        def configure_canvas(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_frame, width=event.width)
        
        scrollable_frame.bind("<Configure>", configure_canvas)
        
        # 添加颜色说明内容
        self.create_color_legend_content(scrollable_frame)
        
        # 布局Canvas和滚动条
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 配置网格权重
        outer_frame.grid_rowconfigure(0, weight=1)
        outer_frame.grid_columnconfigure(0, weight=1)
    
    def create_color_legend_content(self, parent):
        colors = ['黑', '棕', '红', '橙', '黄', '绿', '蓝', '紫', '灰', '白', '金', '银', '无']
        values = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '-', '-', '-']
        multipliers = ['×1', '×10', '×100', '×1k', '×10k', '×100k', '×1M', '×10M', '×100M', '×1G', '×0.1', '×0.01', '-']
        tolerances = ['-', '±1%', '±2%', '-', '-', '±0.5%', '±0.25%', '±0.1%', '±0.05%', '-', '±5%', '±10%', '±20%']
        
        # 标题
        headers = ['颜色', '数值', '乘数', '精度']
        for col, header in enumerate(headers):
            ttk.Label(parent, text=header, font=("Arial", 10, "bold"), 
                     width=12 if col == 0 else 10, anchor=tk.CENTER).grid(row=0, column=col, padx=2, pady=2)
        
        # 颜色行
        for i, (color, value, multiplier, tolerance) in enumerate(zip(colors, values, multipliers, tolerances), 1):
            # 颜色框
            color_canvas = tk.Canvas(parent, width=30, height=20, bg=self.color_display[color], 
                                    relief=tk.RAISED, borderwidth=1)
            color_canvas.grid(row=i, column=0, padx=2, pady=2)
            
            # 颜色名称
            ttk.Label(parent, text=color, width=8, anchor=tk.W).grid(row=i, column=0, padx=35)
            
            # 数值
            ttk.Label(parent, text=value, width=10, anchor=tk.CENTER).grid(row=i, column=1, padx=2)
            
            # 乘数
            ttk.Label(parent, text=multiplier, width=10, anchor=tk.CENTER).grid(row=i, column=2, padx=2)
            
            # 精度
            ttk.Label(parent, text=tolerance, width=10, anchor=tk.CENTER).grid(row=i, column=3, padx=2)
        
        # 添加使用说明
        ttk.Label(parent, text="使用说明:", font=("Arial", 10, "bold")).grid(row=len(colors)+1, column=0, columnspan=4, sticky=tk.W, pady=(10, 5))
        ttk.Label(parent, text="• 4环电阻: 前2环为数字，第3环为乘数，第4环为精度", 
                 wraplength=400).grid(row=len(colors)+2, column=0, columnspan=4, sticky=tk.W, padx=5)
        ttk.Label(parent, text="• 5环电阻: 前3环为数字，第4环为乘数，第5环为精度", 
                 wraplength=400).grid(row=len(colors)+3, column=0, columnspan=4, sticky=tk.W, padx=5)
        ttk.Label(parent, text="• 6环电阻: 前4环为数字，第5环为乘数，第6环为精度", 
                 wraplength=400).grid(row=len(colors)+4, column=0, columnspan=4, sticky=tk.W, padx=5)
    
    def on_ring_type_changed(self, event):
        self.current_ring_type = self.ring_type_var.get()
        self.create_color_selection()
        self.type_label.config(text=self.current_ring_type)
    
    def update_ring_color(self, index):
        if index < len(self.ring_vars):
            color = self.ring_vars[index].get()
            self.ring_buttons[index].config(bg=self.color_display[color])
    
    def calculate_from_colors(self):
        try:
            # 获取当前色环类型配置
            config = self.ring_types[self.current_ring_type]
            digit_rings = config['digit_rings']
            
            # 获取每个环的颜色
            colors = [var.get() for var in self.ring_vars]
            
            # 计算阻值
            digits = 0
            multiplier = 1
            tolerance = "±20%"
            
            # 数字环
            for i in range(digit_rings):
                digit = self.color_values[colors[i]]['digit']
                if digit is None:
                    raise ValueError(f"第{i+1}环不能用作数字环")
                digits = digits * 10 + digit
            
            # 乘数环
            multiplier_index = config['multiplier_index']
            multiplier_value = self.color_values[colors[multiplier_index]]['multiplier']
            if multiplier_value is None:
                raise ValueError(f"第{multiplier_index+1}环必须是乘数环")
            multiplier = multiplier_value
            
            # 精度环
            tolerance_index = config['tolerance_index']
            tolerance_value = self.color_values[colors[tolerance_index]]['tolerance']
            if tolerance_value:
                tolerance = tolerance_value
            
            # 计算总阻值
            resistance = digits * multiplier
            
            # 格式化显示阻值
            display_resistance = self.format_resistance(resistance)
            
            # 更新显示
            self.resistance_label.config(text=display_resistance)
            self.tolerance_label.config(text=tolerance)
            self.type_label.config(text=self.current_ring_type)
            
            # 显示详细信息
            details = f"阻值: {resistance}Ω = {digits} × {multiplier}\n"
            details += f"精度: {tolerance}\n"
            details += f"类型: {self.current_ring_type}\n"
            details += f"颜色: {'-'.join(colors)}"
            self.details_label.config(text=details)
            
        except Exception as e:
            messagebox.showerror("计算错误", f"无法计算阻值:\n{str(e)}")
    
    def calculate_from_resistance(self):
        try:
            # 获取输入值
            input_text = self.reverse_entry.get().strip()
            
            # 解析输入值
            match = re.match(r'^([\d.]+)\s*([kKM]?)\s*Ω?$', input_text, re.IGNORECASE)
            if not match:
                raise ValueError("输入格式不正确，请使用如'1.5k'、'470'、'2.2M'的格式")
            
            value_str, unit = match.groups()
            value = float(value_str)
            
            # 应用单位转换
            unit = unit.upper()
            if unit == 'K':
                value *= 1000
            elif unit == 'M':
                value *= 1000000
            
            # 找到最接近的标准阻值
            standard_resistance = self.find_nearest_standard(value)
            
            # 根据当前色环类型将阻值转换为色环
            colors = self.resistance_to_colors(standard_resistance)
            
            # 更新色环选择
            for i, color in enumerate(colors):
                if i < len(self.ring_vars):
                    self.ring_vars[i].set(color)
                    self.update_ring_color(i)
            
            # 自动计算并显示
            self.calculate_from_colors()
            
            messagebox.showinfo("计算成功", f"已找到最接近的标准阻值: {standard_resistance}Ω")
            
        except Exception as e:
            messagebox.showerror("计算错误", f"无法解析阻值:\n{str(e)}")
    
    def format_resistance(self, resistance):
        """格式化阻值显示"""
        if resistance == 0:
            return "0Ω"
        elif resistance < 1:
            return f"{resistance:.4f}Ω".rstrip('0').rstrip('.')
        elif resistance < 1000:
            return f"{resistance:.2f}Ω".rstrip('0').rstrip('.')
        elif resistance < 1000000:
            return f"{resistance/1000:.2f}kΩ".rstrip('0').rstrip('.')
        elif resistance < 1000000000:
            return f"{resistance/1000000:.2f}MΩ".rstrip('0').rstrip('.')
        else:
            return f"{resistance/1000000000:.2f}GΩ".rstrip('0').rstrip('.')
    
    def find_nearest_standard(self, resistance):
        """找到最接近的E24系列标准阻值"""
        e24_series = [
            1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
            3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1
        ]
        
        # 找到最接近的乘数
        if resistance == 0:
            return 0
        
        multiplier = 1
        while resistance / multiplier >= 10:
            multiplier *= 10
        while resistance / multiplier < 1:
            multiplier /= 10
        
        # 找到最接近的E24值
        base_value = resistance / multiplier
        nearest_base = min(e24_series, key=lambda x: abs(x - base_value))
        
        # 计算标准阻值
        standard_resistance = nearest_base * multiplier
        
        # 确保结果在合理范围内
        if standard_resistance < 0.1:
            standard_resistance = 0.1
        elif standard_resistance > 990000000:
            standard_resistance = 990000000
        
        return round(standard_resistance, 2)
    
    def resistance_to_colors(self, resistance):
        """将阻值转换为对应类型电阻的色环"""
        if resistance <= 0:
            # 零电阻特殊情况
            return ['黑', '黑', '黑', '黑', '金'] if self.current_ring_type == '5环' else ['黑', '黑', '黑', '金']
        
        config = self.ring_types[self.current_ring_type]
        digit_rings = config['digit_rings']
        
        # 将阻值转换为科学计数法表示
        digits = int(resistance)
        multiplier_power = 0
        
        while digits >= 10 ** digit_rings:
            digits //= 10
            multiplier_power += 1
        
        while digits < 10 ** (digit_rings - 1):
            digits *= 10
            multiplier_power -= 1
        
        # 确保有正确位数的有效数字
        if digits >= 10 ** digit_rings:
            digits //= 10
            multiplier_power += 1
        
        # 数字到颜色的映射
        digit_to_color = {0: '黑', 1: '棕', 2: '红', 3: '橙', 4: '黄', 
                          5: '绿', 6: '蓝', 7: '紫', 8: '灰', 9: '白'}
        
        # 乘数到颜色的映射
        multiplier_to_color = {
            0: '黑', 1: '棕', 2: '红', 3: '橙', 4: '黄',
            5: '绿', 6: '蓝', 7: '紫', 8: '灰', 9: '白',
            -1: '金', -2: '银'
        }
        
        # 获取数字环颜色
        colors = []
        for i in range(digit_rings):
            divisor = 10 ** (digit_rings - i - 1)
            digit = (digits // divisor) % 10
            colors.append(digit_to_color[digit])
        
        # 乘数环颜色
        if multiplier_power in multiplier_to_color:
            colors.append(multiplier_to_color[multiplier_power])
        else:
            colors.append('棕')  # 默认
        
        # 精度环颜色（默认使用棕色，±1%）
        colors.append('棕')
        
        return colors
    
    def random_example(self):
        """生成随机示例"""
        import random
        
        # 获取当前色环类型配置
        config = self.ring_types[self.current_ring_type]
        digit_rings = config['digit_rings']
        
        # 随机选择颜色，确保有效组合
        available_colors = list(self.color_values.keys())
        
        # 数字环使用有数字的颜色
        digit_colors = [c for c in available_colors if self.color_values[c]['digit'] is not None]
        
        # 乘数环使用有乘数的颜色
        multiplier_colors = [c for c in available_colors if self.color_values[c]['multiplier'] is not None]
        
        # 精度环使用有精度的颜色
        tolerance_colors = [c for c in available_colors if self.color_values[c]['tolerance'] is not None]
        
        # 随机选择
        colors = []
        for i in range(digit_rings):
            colors.append(random.choice(digit_colors))
        
        colors.append(random.choice(multiplier_colors))
        colors.append(random.choice(tolerance_colors))
        
        # 更新界面
        for i, color in enumerate(colors):
            if i < len(self.ring_vars):
                self.ring_vars[i].set(color)
                self.update_ring_color(i)
        
        # 自动计算
        self.calculate_from_colors()

def main():
    root = tk.Tk()
    app = ResistorColorCodeCalculator(root)
    root.mainloop()

if __name__ == "__main__":
    main()
