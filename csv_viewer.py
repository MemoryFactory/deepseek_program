import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import os
from collections import defaultdict

class CSVViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("CSV查看器")
        self.root.geometry("1200x700")
        
        # 存储数据
        self.data = []
        self.headers = []
        self.sort_column = None
        self.sort_reverse = False
        
        # 存储列宽
        self.column_widths = defaultdict(lambda: 100)
        
        # 复选框状态变量
        self.show_grid_var = tk.BooleanVar(value=True)
        self.show_stripes_var = tk.BooleanVar(value=True)
        self.has_header_var = tk.BooleanVar(value=True)
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建主界面
        self.create_widgets()
        
        # 绑定事件
        self.bind_events()
        
        # 初始化样式
        self.init_styles()
        
    def init_styles(self):
        """初始化样式"""
        self.style = ttk.Style()
        
        # 配置奇数行和偶数行的样式
        self.style.configure("OddRow.Treeview", background="#f5f5f5")
        self.style.configure("EvenRow.Treeview", background="#ffffff")
        
        # 配置表头样式
        self.style.configure("Treeview.Heading", 
                           background="#e1e1e1", 
                           foreground="#000000",
                           relief="solid",
                           borderwidth=1)
        
        # 配置单元格样式
        self.style.map("Treeview",
                      background=[("selected", "#0078d7")],
                      foreground=[("selected", "white")])
        
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="重新加载", command=self.reload_file)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 视图菜单
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="视图", menu=view_menu)
        view_menu.add_command(label="重置列宽", command=self.reset_column_widths)
        view_menu.add_command(label="自动调整列宽", command=self.auto_resize_columns)
        
        # 绑定快捷键
        self.root.bind('<Control-o>', lambda e: self.open_file())
        
    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # 文件路径显示
        self.file_label = ttk.Label(toolbar, text="未打开文件")
        self.file_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 创建复选框框架
        checkbox_frame = ttk.Frame(toolbar)
        checkbox_frame.pack(side=tk.LEFT, padx=10)
        
        # 表格线复选框
        self.grid_check = ttk.Checkbutton(
            checkbox_frame, 
            text="表格线", 
            variable=self.show_grid_var,
            command=self.toggle_grid
        )
        self.grid_check.pack(side=tk.LEFT, padx=2)
        
        # 分行底色复选框
        self.stripes_check = ttk.Checkbutton(
            checkbox_frame, 
            text="分行底色", 
            variable=self.show_stripes_var,
            command=self.toggle_stripes
        )
        self.stripes_check.pack(side=tk.LEFT, padx=2)
        
        # 表头复选框
        self.header_check = ttk.Checkbutton(
            checkbox_frame, 
            text="表头", 
            variable=self.has_header_var,
            command=self.toggle_header
        )
        self.header_check.pack(side=tk.LEFT, padx=2)
        
        # 创建Treeview和滚动条
        self.create_treeview(main_frame)
        
        # 状态栏
        self.create_status_bar(main_frame)
        
    def create_status_bar(self, parent):
        """创建状态栏"""
        self.status_bar = ttk.Frame(parent, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        # 左侧状态信息
        self.status_left = ttk.Label(self.status_bar, text="就绪")
        self.status_left.pack(side=tk.LEFT, padx=5)
        
        # 右侧行列信息
        self.status_right = ttk.Label(self.status_bar, text="行: 0 | 列: 0 | 总行数: 0")
        self.status_right.pack(side=tk.RIGHT, padx=5)
        
    def create_treeview(self, parent):
        """创建Treeview和滚动条"""
        # 创建Treeview框架
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建垂直滚动条
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建水平滚动条
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建Treeview
        self.tree = ttk.Treeview(
            tree_frame,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            selectmode='extended',
            show='tree headings'  # 显示树状结构和表头
        )
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # 配置滚动条
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
        
        # 创建上下文菜单
        self.create_context_menu()
        
    def create_context_menu(self):
        """创建上下文菜单"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="调整列宽", command=self.adjust_column_width)
        self.context_menu.add_command(label="调整行高", command=self.adjust_row_height)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="复制单元格", command=self.copy_cell)
        self.context_menu.add_command(label="复制整行", command=self.copy_row)
        
    def bind_events(self):
        """绑定事件"""
        # Treeview列标题点击事件
        self.tree.bind('<Button-1>', self.on_header_click)
        
        # 右键菜单
        self.tree.bind('<Button-3>', self.show_context_menu)
        
        # 调整列宽
        self.tree.bind('<B1-Motion>', self.on_column_resize)
        
        # 双击单元格编辑
        self.tree.bind('<Double-Button-1>', self.edit_cell)
        
        # 更新行列信息
        self.tree.bind('<Motion>', self.update_cell_info)
        
    def toggle_grid(self):
        """切换表格线显示"""
        if self.show_grid_var.get():
            # 显示表格线
            self.style.configure("Treeview", 
                               relief="solid",
                               borderwidth=1)
            self.style.configure("Treeview.Heading",
                               relief="solid",
                               borderwidth=1)
        else:
            # 隐藏表格线
            self.style.configure("Treeview", 
                               relief="flat",
                               borderwidth=0)
            self.style.configure("Treeview.Heading",
                               relief="flat",
                               borderwidth=0)
        
        # 重新显示数据以应用样式
        if self.data:
            self.display_data()
            
    def toggle_stripes(self):
        """切换分行底色"""
        # 重新显示数据以应用分行底色
        if self.data:
            self.display_data()
            
    def toggle_header(self):
        """切换表头显示"""
        if self.data:
            self.display_data()
            
    def open_file(self):
        """打开CSV文件"""
        file_path = filedialog.askopenfilename(
            title="选择CSV文件",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        
        if file_path:
            self.load_file(file_path)
            
    def reload_file(self):
        """重新加载当前文件"""
        if hasattr(self, 'current_file') and self.current_file:
            self.load_file(self.current_file)
            
    def load_file(self, file_path):
        """加载CSV文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                
                # 读取所有数据
                self.data = list(csv_reader)
                
                if not self.data:
                    messagebox.showwarning("警告", "CSV文件为空")
                    return
                
                # 设置当前文件
                self.current_file = file_path
                self.file_label.config(text=os.path.basename(file_path))
                
                # 显示数据
                self.display_data()
                
        except Exception as e:
            messagebox.showerror("错误", f"无法读取文件: {str(e)}")
            
    def display_data(self):
        """显示数据到Treeview"""
        # 清除现有数据
        self.tree.delete(*self.tree.get_children())
        
        # 设置列
        if self.has_header_var.get() and self.data:
            # 使用第一行作为表头
            self.headers = self.data[0]
            data_rows = self.data[1:] if len(self.data) > 1 else []
        else:
            # 不使用表头，生成默认列名
            if self.data:
                num_cols = max(len(row) for row in self.data)
                self.headers = [f"列{i+1}" for i in range(num_cols)]
            else:
                self.headers = []
            data_rows = self.data
        
        # 添加行号列
        all_columns = ['行号'] + self.headers
        self.tree['columns'] = all_columns
        self.tree['show'] = 'tree headings'
        
        # 配置列
        # 配置行号列（不可排序）
        self.tree.heading('#0', text='', anchor=tk.W)
        self.tree.column('#0', width=0, stretch=tk.NO)
        
        # 配置行号列
        self.tree.heading('行号', text='行号', anchor=tk.CENTER)
        self.tree.column('行号', width=60, anchor=tk.CENTER, stretch=tk.NO)
        
        # 配置数据列
        for i, header in enumerate(self.headers):
            self.tree.heading(
                header,
                text=header,
                command=lambda h=header: self.sort_by_column(h)
            )
            
            # 设置列宽
            width = self.column_widths[header]
            self.tree.column(header, width=width, minwidth=50)
        
        # 插入数据行
        for row_index, row in enumerate(data_rows, start=1):
            # 准备行数据
            row_data = [row_index] + row
            
            # 添加行
            item_id = self.tree.insert('', tk.END, values=row_data)
            
            # 应用分行底色
            if self.show_stripes_var.get():
                if row_index % 2 == 0:
                    self.tree.item(item_id, tags=('even',))
                else:
                    self.tree.item(item_id, tags=('odd',))
            else:
                self.tree.item(item_id, tags=('normal',))
        
        # 配置标签样式
        if self.show_stripes_var.get():
            self.tree.tag_configure('odd', background='#f5f5f5')
            self.tree.tag_configure('even', background='#ffffff')
        else:
            self.tree.tag_configure('normal', background='')
        
        # 更新状态栏
        self.update_status_bar()
        
    def update_status_bar(self):
        """更新状态栏信息"""
        if not self.data:
            self.status_left.config(text="就绪")
            self.status_right.config(text="行: 0 | 列: 0 | 总行数: 0")
            return
            
        # 计算数据
        if self.has_header_var.get():
            total_rows = len(self.data) - 1
            data_rows = self.data[1:] if len(self.data) > 1 else []
        else:
            total_rows = len(self.data)
            data_rows = self.data
            
        # 获取列数
        num_cols = len(self.headers) if self.headers else 0
        
        # 获取当前可见行数
        visible_items = self.tree.get_children()
        visible_rows = len(visible_items)
        
        # 更新状态栏
        self.status_left.config(text=f"已加载: {os.path.basename(self.current_file) if hasattr(self, 'current_file') else '未打开文件'}")
        self.status_right.config(text=f"显示行: {visible_rows} | 列: {num_cols} | 总行数: {total_rows}")
        
    def on_header_click(self, event):
        """处理列标题点击"""
        region = self.tree.identify_region(event.x, event.y)
        
        if region == "heading":
            # 获取列ID
            column_id = self.tree.identify_column(event.x)
            
            # 跳过行号列（第一列）
            if column_id == '#1':
                return
                
            # 获取列名
            try:
                column_index = int(column_id.replace('#', '')) - 1
                if 0 <= column_index - 1 < len(self.headers):  # 减1是因为行号列占了一列
                    column_name = self.headers[column_index - 1]
                    self.sort_by_column(column_name)
            except (ValueError, IndexError):
                pass
                
    def sort_by_column(self, column):
        """按列排序"""
        try:
            column_index = self.headers.index(column)
            
            # 切换排序顺序
            if self.sort_column == column:
                self.sort_reverse = not self.sort_reverse
            else:
                self.sort_column = column
                self.sort_reverse = False
            
            # 获取数据行（排除表头）
            if self.has_header_var.get():
                data_to_sort = self.data[1:] if len(self.data) > 1 else []
            else:
                data_to_sort = self.data
            
            # 排序数据
            def sort_key(row):
                value = row[column_index] if column_index < len(row) else ""
                try:
                    # 尝试转换为数字
                    if value.replace('.', '', 1).isdigit():
                        return float(value) if '.' in value else int(value)
                except (ValueError, TypeError):
                    pass
                # 保持为字符串
                return str(value).lower()
            
            sorted_data = sorted(
                data_to_sort,
                key=sort_key,
                reverse=self.sort_reverse
            )
            
            # 更新数据
            if self.has_header_var.get():
                self.data = [self.data[0]] + sorted_data
            else:
                self.data = sorted_data
            
            # 重新显示
            self.display_data()
            
            # 更新状态
            order = "降序" if self.sort_reverse else "升序"
            self.status_left.config(text=f"按 '{column}' {order} 排序")
            
        except ValueError:
            pass
            
    def on_column_resize(self, event):
        """处理列宽调整"""
        region = self.tree.identify_region(event.x, event.y)
        
        if region == "separator":
            # 获取当前列宽
            for col in ['行号'] + self.headers:
                try:
                    width = self.tree.column(col, 'width')
                    if col != '行号':  # 不保存行号列的宽度
                        self.column_widths[col] = width
                except:
                    pass
            self.update_status_bar()
                
    def reset_column_widths(self):
        """重置列宽"""
        for header in self.headers:
            self.column_widths[header] = 100
            if hasattr(self, 'tree') and self.tree:
                self.tree.column(header, width=100)
        self.tree.column('行号', width=60)
        self.update_status_bar()
                
    def auto_resize_columns(self):
        """自动调整列宽"""
        if not hasattr(self, 'tree') or not self.tree:
            return
            
        for header in self.headers:
            # 获取列中所有单元格的内容长度
            max_length = len(str(header)) * 8  # 初始宽度基于标题
            
            # 获取该列的所有数据
            col_index = self.headers.index(header)
            if self.has_header_var.get():
                data_rows = self.data[1:] if len(self.data) > 1 else []
            else:
                data_rows = self.data
                
            for row in data_rows:
                if col_index < len(row):
                    cell_length = len(str(row[col_index])) * 7
                    max_length = max(max_length, cell_length)
            
            # 设置列宽，但限制最大宽度
            width = min(max_length + 20, 400)
            self.column_widths[header] = width
            self.tree.column(header, width=width)
            
        # 更新状态栏
        self.update_status_bar()
        
    def adjust_column_width(self):
        """调整选中列的宽度"""
        selected_column = None
        
        # 获取当前鼠标位置下的列
        x, y = self.root.winfo_pointerx() - self.tree.winfo_rootx(), \
               self.root.winfo_pointery() - self.tree.winfo_rooty()
        
        region = self.tree.identify_region(x, y)
        
        if region == "heading" or region == "cell":
            column_id = self.tree.identify_column(x)
            
            # 获取列名
            try:
                column_index = int(column_id.replace('#', '')) - 1
                if column_index == 0:
                    selected_column = '行号'
                elif 0 <= column_index - 1 < len(self.headers):
                    selected_column = self.headers[column_index - 1]
            except (ValueError, IndexError):
                pass
        
        if selected_column and selected_column != '行号':
            # 弹出对话框让用户输入宽度
            dialog = tk.Toplevel(self.root)
            dialog.title(f"调整列宽 - {selected_column}")
            dialog.geometry("300x150")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 当前宽度
            current_width = self.tree.column(selected_column, 'width')
            
            ttk.Label(dialog, text=f"列: {selected_column}").pack(pady=10)
            ttk.Label(dialog, text=f"当前宽度: {current_width}").pack()
            
            width_frame = ttk.Frame(dialog)
            width_frame.pack(pady=10)
            
            ttk.Label(width_frame, text="新宽度:").pack(side=tk.LEFT, padx=(0, 5))
            
            width_var = tk.StringVar(value=str(current_width))
            width_entry = ttk.Entry(width_frame, textvariable=width_var, width=10)
            width_entry.pack(side=tk.LEFT)
            width_entry.select_range(0, tk.END)
            width_entry.focus()
            
            def apply_width():
                try:
                    new_width = int(width_var.get())
                    if new_width < 50:
                        new_width = 50
                    elif new_width > 1000:
                        new_width = 1000
                        
                    self.column_widths[selected_column] = new_width
                    self.tree.column(selected_column, width=new_width)
                    self.update_status_bar()
                    dialog.destroy()
                except ValueError:
                    messagebox.showerror("错误", "请输入有效的数字")
                    
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=10)
            
            ttk.Button(button_frame, text="确定", command=apply_width).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)
            
            # 绑定回车键
            dialog.bind('<Return>', lambda e: apply_width())
            
    def adjust_row_height(self):
        """调整行高"""
        dialog = tk.Toplevel(self.root)
        dialog.title("调整行高")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="调整行高会影响所有行").pack(pady=10)
        
        height_frame = ttk.Frame(dialog)
        height_frame.pack(pady=10)
        
        ttk.Label(height_frame, text="行高:").pack(side=tk.LEFT, padx=(0, 5))
        
        height_var = tk.StringVar(value="20")
        height_entry = ttk.Entry(height_frame, textvariable=height_var, width=10)
        height_entry.pack(side=tk.LEFT)
        height_entry.select_range(0, tk.END)
        height_entry.focus()
        
        def apply_row_height():
            try:
                row_height = int(height_var.get())
                if row_height < 15:
                    row_height = 15
                elif row_height > 100:
                    row_height = 100
                    
                # 设置Treeview的行高
                self.style.configure("Treeview", rowheight=row_height)
                dialog.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
                
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="确定", command=apply_row_height).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)
        
        # 绑定回车键
        dialog.bind('<Return>', lambda e: apply_row_height())
        
    def show_context_menu(self, event):
        """显示上下文菜单"""
        self.context_menu.post(event.x_root, event.y_root)
        
    def update_cell_info(self, event):
        """更新单元格信息（可选功能）"""
        # 可以在这里添加鼠标悬停时显示单元格坐标的功能
        pass
        
    def copy_cell(self):
        """复制选中单元格内容"""
        selected = self.tree.selection()
        if selected:
            column = self.tree.identify_column(self.root.winfo_pointerx() - self.tree.winfo_rootx())
            if column:
                try:
                    item = self.tree.item(selected[0])
                    values = item['values']
                    column_index = int(column.replace('#', '')) - 1
                    if 0 <= column_index < len(values):
                        cell_value = values[column_index]
                        self.root.clipboard_clear()
                        self.root.clipboard_append(str(cell_value))
                        self.status_left.config(text=f"已复制: {cell_value}")
                except:
                    pass
                    
    def copy_row(self):
        """复制整行内容"""
        selected = self.tree.selection()
        if selected:
            try:
                item = self.tree.item(selected[0])
                values = item['values']
                # 跳过行号列
                row_data = values[1:] if len(values) > 1 else []
                row_text = '\t'.join(str(v) for v in row_data)
                self.root.clipboard_clear()
                self.root.clipboard_append(row_text)
                self.status_left.config(text="已复制整行")
            except:
                pass
                
    def edit_cell(self, event):
        """双击编辑单元格"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            # 获取选中的单元格
            item = self.tree.identify_row(event.y)
            column = self.tree.identify_column(event.x)
            
            # 跳过行号列
            if column == '#1':
                return
                
            if item and column:
                # 获取当前值
                item_data = self.tree.item(item)
                values = item_data['values']
                column_index = int(column.replace('#', '')) - 1
                
                if 0 <= column_index < len(values):
                    current_value = values[column_index]
                    
                    # 获取单元格位置
                    x, y, width, height = self.tree.bbox(item, column)
                    
                    # 创建编辑框
                    entry = ttk.Entry(self.tree)
                    entry.place(x=x, y=y, width=width, height=height)
                    entry.insert(0, str(current_value))
                    entry.select_range(0, tk.END)
                    entry.focus()
                    
                    def save_edit(event=None):
                        # 获取新值
                        new_value = entry.get()
                        
                        # 更新Treeview
                        values[column_index] = new_value
                        self.tree.item(item, values=values)
                        
                        # 更新数据
                        row_index = int(values[0]) - 1  # 行号减1得到索引
                        if self.has_header_var.get():
                            row_index += 1  # 如果有表头，数据行索引要加1
                            
                        # 获取列索引
                        col_index = column_index - 1  # 减1是因为有行号列
                        
                        if 0 <= row_index < len(self.data) and 0 <= col_index < len(self.data[row_index]):
                            self.data[row_index][col_index] = new_value
                        
                        # 销毁编辑框
                        entry.destroy()
                        self.update_status_bar()
                        
                    def cancel_edit(event=None):
                        entry.destroy()
                        
                    entry.bind('<Return>', save_edit)
                    entry.bind('<Escape>', cancel_edit)
                    entry.bind('<FocusOut>', lambda e: save_edit())


def main():
    root = tk.Tk()
    app = CSVViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()