import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
import os
import sys
from datetime import datetime, timedelta
from version import __version__
import updater
from warehouse import ALL_HERO_NAMES, WAREHOUSE_TXT_PATH
from hero_metadata import HERO_RACE, HERO_JOB, RACE_NAMES, JOB_NAMES, PUSH_COMMON_HEROES, HERO_CN_NAMES

def get_resource_path(relative_path):
    """获取资源文件的绝对路径，兼容打包后的exe"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

def get_work_path(relative_path):
    """获取工作目录下的文件路径（配置文件等）"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

CONFIG_FILE = get_work_path("game_bot_config.json")
LOG_FILE = get_work_path("game_bot.log")
_FILE_WRITE_ERROR_CALLBACK = None


def _notify_file_write_error(path):
    if _FILE_WRITE_ERROR_CALLBACK is not None:
        _FILE_WRITE_ERROR_CALLBACK(path)


class _PersistentStdout:
    """同时保留控制台输出和写入本地日志文件。"""

    def __init__(self, stream, path):
        self.stream = stream
        self.path = path
        self.lock = threading.Lock()

    def write(self, text):
        if not text:
            return 0
        try:
            self.stream.write(text)
            self.stream.flush()
        except Exception:
            # 打包后的 GUI 程序可能没有可用控制台，忽略控制台输出失败。
            pass
        try:
            with self.lock:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(text)
        except Exception:
            _notify_file_write_error(self.path)
        return len(text)

    def flush(self):
        try:
            self.stream.flush()
        except Exception:
            pass


def _enable_persistent_console_log():
    if not isinstance(sys.stdout, _PersistentStdout):
        sys.stdout = _PersistentStdout(sys.stdout, LOG_FILE)


_enable_persistent_console_log()

def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
    return {}

def save_config(config):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False

class ScriptConfig:
    def __init__(self, name, enabled=False, params=None, daily_reset=False):
        self.name = name
        self.enabled = enabled
        self.params = params or {}
        self.status = "就绪"
        self.daily_reset = daily_reset  # 是否每日重置
        self.last_run_time = None  # 最后执行时间

def _ensure_config_files():
    """首次运行时创建必要目录、从打包资源中复制配置文件到 exe 同目录"""
    # 确保 shared 目录存在
    shared_dir = get_work_path("shared")
    os.makedirs(shared_dir, exist_ok=True)

    config_files = []
    for fname in config_files:
        target = get_work_path(fname)
        if not os.path.exists(target):
            try:
                source = get_resource_path(fname)
                if os.path.exists(source):
                    import shutil
                    shutil.copy2(source, target)
            except Exception:
                pass


class GameBotGUI:
    def __init__(self, root):
        _ensure_config_files()
        self.root = root
        global _FILE_WRITE_ERROR_CALLBACK
        _FILE_WRITE_ERROR_CALLBACK = self._schedule_file_write_error
        self.root.title("梅林初号机")
        self.root.geometry("1050x700")
        
        # 全局默认字体
        style = ttk.Style()
        style.configure(".", font=("Microsoft YaHei", 9))

        self.is_running = False
        self.current_script_index = 0
        self.stop_event = threading.Event()
        
        # 创建隐藏的日志文本框用于存储日志
        self.log_text = tk.Text(self.root, height=0, width=0, state=tk.NORMAL)
        
        # 加载配置
        self.config = load_config()
        self.is_first_run = not self.config.get("first_run_completed", False)
        
        self.scripts = [
            ScriptConfig("登录", enabled=True),
            ScriptConfig("仓库管理", enabled=True),
            ScriptConfig("邮件", enabled=False, daily_reset=True),
            ScriptConfig("好友奖励", enabled=False, daily_reset=True),
            ScriptConfig("普竞", enabled=False),
            ScriptConfig("迷梦之域", enabled=False, params={"challenge_count": 5}),
            ScriptConfig("女神塔", enabled=False),
            ScriptConfig("挂机奖励", enabled=False, params={"paid_times": 0}, daily_reset=True),
            ScriptConfig("商城", enabled=False, daily_reset=True),
            ScriptConfig("日常任务", enabled=False, daily_reset=True),
            ScriptConfig("爬塔", enabled=False),
            ScriptConfig("幻灵推图", enabled=False),
            ScriptConfig("推图", enabled=False),
            ScriptConfig("循环推图", enabled=False),
            ScriptConfig("异界迷宫", enabled=False, params={
                "challenges": 1,
                "floors": "15",
                "formation_name": "",
                "shenceng_formation_name": ""
            }),
        ]
        
        # 从配置中加载脚本状态
        for script in self.scripts:
            script_config = self.config.get("scripts", {}).get(script.name, {})
            script.enabled = script_config.get("enabled", script.enabled)
            script.params = script_config.get("params", script.params)
            script.daily_reset = script_config.get("daily_reset", script.daily_reset)
            script.last_run_time = script_config.get("last_run_time", None)
        
        # 检查是否需要重置每日重置的脚本
        self.check_daily_reset()
        
        self.setup_ui()

        # 启动后自动检查更新（后台线程，不阻塞界面）
        self.root.after(1000, self._auto_check_update)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def check_daily_reset(self):
        """检查是否需要重置每日重置的脚本"""
        now = datetime.now()
        today_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
        
        for script in self.scripts:
            if script.daily_reset and script.last_run_time:
                # 解析最后执行时间
                try:
                    last_run = datetime.fromisoformat(script.last_run_time)
                    
                    # 检查最后执行时间是否在今天8点之前
                    if last_run < today_8am:
                        # 重置脚本启用状态为True
                        script.enabled = True
                        script.last_run_time = None
                        self.log(f"脚本 '{script.name}' 已重置为默认开启状态")
                except Exception as e:
                    print(f"解析最后执行时间失败: {e}")
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        self.create_control_bar(main_frame)
        self.create_dashboard(main_frame)
        self.create_script_panel(main_frame)
        
    def create_control_bar(self, parent):
        control_frame = ttk.Frame(parent, padding="10")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.master_switch_btn = ttk.Button(
            control_frame, 
            text="开始运行", 
            command=self.toggle_master_switch
        )
        self.master_switch_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            control_frame,
            text="停止运行",
            command=self.stop_all,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.view_log_btn = ttk.Button(
            control_frame,
            text="查看任务日志",
            command=self.show_log_window
        )
        self.view_log_btn.pack(side=tk.LEFT, padx=5)

        self.clear_log_btn = ttk.Button(
            control_frame,
            text="清空日志",
            command=self.clear_log_file
        )
        self.clear_log_btn.pack(side=tk.LEFT, padx=5)

        self.help_btn = ttk.Button(
            control_frame,
            text="帮助",
            command=self.show_help_window
        )
        self.help_btn.pack(side=tk.LEFT, padx=5)

        self.sponsor_btn = ttk.Button(
            control_frame,
            text="赞助",
            command=self.show_sponsor
        )
        self.sponsor_btn.pack(side=tk.LEFT, padx=5)

        self.update_btn = ttk.Button(
            control_frame,
            text="检查更新",
            command=self._check_update_clicked
        )
        self.update_btn.pack(side=tk.RIGHT, padx=5)

        self.version_label = ttk.Label(control_frame, text=__version__, foreground="gray")
        self.version_label.pack(side=tk.RIGHT, padx=5)

    def create_dashboard(self, parent):
        dashboard_frame = ttk.LabelFrame(parent, text="功能", padding="10")
        dashboard_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 添加滚动条
        canvas = tk.Canvas(dashboard_frame, width=150, height=300)
        scrollbar = ttk.Scrollbar(dashboard_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.script_buttons = []
        for i, script in enumerate(self.scripts):
            btn = ttk.Button(
                scrollable_frame,
                text=script.name,
                width=15,
                command=lambda idx=i: self.select_script(idx)
            )
            btn.pack(pady=5, fill=tk.X)
            self.script_buttons.append(btn)
            
        self.update_dashboard_buttons()
        
    def create_script_panel(self, parent):
        self.script_panel = ttk.LabelFrame(parent, text="配置", padding="10")
        self.script_panel.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.script_panel.columnconfigure(1, weight=1)
        
        self.script_name_label = ttk.Label(self.script_panel, text="", font=("Microsoft YaHei", 12, "bold"))
        self.script_name_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        self.script_enabled_var = tk.BooleanVar()
        self.script_enabled_check = ttk.Checkbutton(
            self.script_panel,
            text="开启",
            variable=self.script_enabled_var,
            command=self.on_script_enabled_changed
        )
        self.script_enabled_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        self.param_frame = ttk.Frame(self.script_panel)
        self.param_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.update_script_panel()
        
    def show_log_window(self):
        log_window = tk.Toplevel(self.root)
        log_window.title("任务日志")
        log_window.geometry("800x600")
        
        log_frame = ttk.Frame(log_window, padding="10")
        log_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        log_window.columnconfigure(0, weight=1)
        log_window.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        log_text = tk.Text(log_frame, wrap=tk.WORD)
        log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        log_text.configure(yscrollcommand=scrollbar.set)
        
        def refresh_log():
            try:
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
            except FileNotFoundError:
                content = ""
            except Exception as e:
                content = f"读取日志失败: {e}\n"
            log_text.configure(state=tk.NORMAL)
            log_text.delete("1.0", tk.END)
            log_text.insert(tk.END, content)
            log_text.see(tk.END)
            log_text.configure(state=tk.DISABLED)

        log_text.configure(state=tk.DISABLED)
        button_frame = ttk.Frame(log_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
        ttk.Button(button_frame, text="刷新", command=refresh_log).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="清空文件", command=self.clear_log_file).pack(side=tk.LEFT)
        refresh_log()

    def clear_log_file(self):
        if not messagebox.askyesno("清空日志", "确定要清空本地日志文件吗？"):
            return
        try:
            with open(LOG_FILE, "w", encoding="utf-8"):
                pass
            self.log_text.delete("1.0", tk.END)
            timestamp = time.strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] 本地日志文件已清空（此提示不会写入文件）\n")
            self.log_text.see(tk.END)
        except Exception as e:
            messagebox.showerror("清空失败", str(e))

    def show_help_window(self):
        help_window = tk.Toplevel(self.root)
        help_window.title("帮助")
        help_window.geometry("700x650")

        readme_path = get_resource_path("README.md")
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = "README.md 未找到。"

        text_frame = ttk.Frame(help_window, padding="10")
        text_frame.pack(fill=tk.BOTH, expand=True)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Microsoft YaHei", 10),
                              padx=10, pady=10, borderwidth=0)
        text_widget.insert(tk.END, content)
        text_widget.configure(state=tk.DISABLED)

        text_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=text_scrollbar.set)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def show_sponsor(self):
        qr_path = get_resource_path("sponsor_qrcode.png")
        if os.path.exists(qr_path):
            os.startfile(qr_path)
        else:
            messagebox.showinfo("赞助", "赞助二维码图片未找到。")

    def update_dashboard_buttons(self):
        for i, (btn, script) in enumerate(zip(self.script_buttons, self.scripts)):
            if i == self.current_script_index:
                btn.state(['pressed'])
            else:
                btn.state(['!pressed'])
            
            if script.enabled:
                btn.configure(text=f"✓ {script.name}")
            else:
                btn.configure(text=script.name)
                
    def update_script_panel(self):
        script = self.scripts[self.current_script_index]
        self.script_name_label.configure(text=script.name)
        self.script_enabled_var.set(script.enabled)

        # 缓存仓库面板，避免切换时重建 472 个 widget 导致卡顿
        wh_container = getattr(self, '_warehouse_container', None)
        if wh_container is not None:
            wh_container.grid_remove()

        for widget in list(self.param_frame.winfo_children()):
            if widget is wh_container:
                continue
            widget.destroy()

        if script.name == "迷梦之域":
            self.create_mimengzhiyu_params(script, 0)
        elif script.name == "挂机奖励":
            self.create_shouquguajijiangli_params(script, 0)
        elif script.name == "异界迷宫":
            self.create_yijiemigong_params(script, 0)
        elif script.name in ("幻灵推图", "推图", "循环推图"):
            self.create_push_params(0)
        elif script.name == "仓库管理":
            self.create_warehouse_params(0)
            
    def create_mimengzhiyu_params(self, script, row=0):
        ttk.Label(self.param_frame, text="挑战次数:").grid(row=row, column=0, sticky=tk.W, pady=2)
        
        challenge_count = script.params.get("challenge_count", 5)
        self.challenge_count_var = tk.IntVar(value=challenge_count)
        
        challenge_spinbox = ttk.Spinbox(
            self.param_frame,
            from_=1,
            to=100,
            textvariable=self.challenge_count_var,
            width=10
        )
        challenge_spinbox.grid(row=row, column=1, sticky=tk.W, pady=2)
        
        def on_param_change():
            script.params["challenge_count"] = self.challenge_count_var.get()
            self.save_config()
            
        challenge_spinbox.bind("<FocusOut>", lambda e: on_param_change())
        challenge_spinbox.bind("<Return>", lambda e: on_param_change())
        
    def create_pujing_params(self, script, row=0):
        ttk.Label(self.param_frame, text="暂无参数").grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        
    def create_push_params(self, row=0):
        push_settings = self.config.get("push_settings", {})

        # 跳过手动战斗
        skip_manual = push_settings.get("skip_manual", True)
        self.skip_manual_var = tk.BooleanVar(value=skip_manual)
        ttk.Checkbutton(
            self.param_frame,
            text="跳过手动战斗阵容",
            variable=self.skip_manual_var,
            command=self.on_push_param_change
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)
        row += 1

        # 失败重试次数
        ttk.Label(self.param_frame, text="失败重试次数 (1-3):").grid(row=row, column=0, sticky=tk.W, pady=2)
        retry_count = push_settings.get("retry_count", 3)
        self.retry_count_var = tk.IntVar(value=retry_count)
        ttk.Spinbox(
            self.param_frame,
            from_=1,
            to=3,
            textvariable=self.retry_count_var,
            width=5
        ).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        # Spinbox 的绑定
        for child in self.param_frame.winfo_children():
            if isinstance(child, ttk.Spinbox):
                child.bind("<FocusOut>", lambda e: self.on_push_param_change())
                child.bind("<Return>", lambda e: self.on_push_param_change())

        ttk.Label(self.param_frame, text="注: 幻灵推图、推图、循环推图共享此设置").grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=5)

    def on_push_param_change(self):
        self.config["push_settings"] = {
            "skip_manual": self.skip_manual_var.get(),
            "retry_count": self.retry_count_var.get(),
        }
        self.save_config()
        
    def create_warehouse_params(self, row=0):
        """仓库管理：种族+职业筛选，手动勾选英雄练度（首次创建后缓存，切换不重建）"""
        wh_container = getattr(self, '_warehouse_container', None)
        if wh_container is not None:
            wh_container.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
            return

        LEVELS = ["未拥有", "低", "高"]
        LEVEL_LABELS = {"未拥有": "未拥有", "低": "不到巅峰+", "高": "巅峰+及以上"}

        # 从 warehouse_heroes.txt 加载已有数据
        hero_levels = {}
        if os.path.exists(WAREHOUSE_TXT_PATH):
            with open(WAREHOUSE_TXT_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if ',' in line:
                        name, lvl = line.split(',', 1)
                        hero_levels[name.strip()] = lvl.strip()

        self._hero_levels = hero_levels

        # 外层容器，用于缓存
        container = ttk.Frame(self.param_frame)
        container.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        container.columnconfigure(0, weight=1)
        self._warehouse_container = container

        # === 筛选行 ===
        filter_frame = ttk.Frame(container)
        filter_frame.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        ttk.Label(filter_frame, text="种族:").pack(side=tk.LEFT, padx=(0, 2))
        race_values = ["全部"] + list(RACE_NAMES.values())
        self._race_filter_var = tk.StringVar(value="全部")
        race_combo = ttk.Combobox(filter_frame, textvariable=self._race_filter_var,
                                  values=race_values, state="readonly", width=8)
        race_combo.pack(side=tk.LEFT, padx=(0, 10))
        race_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_hero_filter())

        ttk.Label(filter_frame, text="职业:").pack(side=tk.LEFT, padx=(0, 2))
        job_values = ["全部"] + list(JOB_NAMES.values())
        self._job_filter_var = tk.StringVar(value="全部")
        job_combo = ttk.Combobox(filter_frame, textvariable=self._job_filter_var,
                                 values=job_values, state="readonly", width=8)
        job_combo.pack(side=tk.LEFT, padx=(0, 10))
        job_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_hero_filter())

        # 仅显示常用
        self._common_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(filter_frame, text="仅常用", variable=self._common_only_var,
                        command=self._apply_hero_filter).pack(side=tk.LEFT, padx=(0, 10))

        # 批量设置按钮
        for level in LEVELS:
            ttk.Button(filter_frame, text=f"全部→{LEVEL_LABELS[level]}",
                       command=lambda l=level: self._set_all_hero_levels(l)).pack(side=tk.LEFT, padx=2)

        # === 可滚动英雄列表 ===
        canvas = tk.Canvas(container, width=550, height=400, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        self._hero_list_frame = ttk.Frame(canvas)

        self._hero_list_frame.bind("<Configure>",
                                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._hero_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        canvas.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=1, column=2, sticky=(tk.N, tk.S))

        container.rowconfigure(1, weight=1)

        # 为每个英雄创建一行：名字 + 3 个 Radiobutton
        self._hero_vars = {}   # hero_name → tk.StringVar
        self._hero_rows = {}   # hero_name → ttk.Frame (整行)

        for i, hero_name in enumerate(ALL_HERO_NAMES):
            level = hero_levels.get(hero_name, "高")
            var = tk.StringVar(value=level)
            self._hero_vars[hero_name] = var

            row_frame = ttk.Frame(self._hero_list_frame)
            row_frame.grid(row=i, column=0, sticky=tk.W, pady=0)

            ttk.Label(row_frame, text=HERO_CN_NAMES.get(hero_name, hero_name), width=8, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))
            for lvl in LEVELS:
                ttk.Radiobutton(row_frame, text=LEVEL_LABELS[lvl], variable=var, value=lvl,
                                command=lambda n=hero_name: self._on_hero_level_change(n)
                                ).pack(side=tk.LEFT, padx=2)

            self._hero_rows[hero_name] = row_frame

        # 种族/职业查找表，供筛选用
        self._hero_race = {}
        self._hero_job = {}
        for hero_name in ALL_HERO_NAMES:
            race_key = HERO_RACE.get(hero_name, "")
            job_key = HERO_JOB.get(hero_name, "")
            self._hero_race[hero_name] = RACE_NAMES.get(race_key, "")
            self._hero_job[hero_name] = JOB_NAMES.get(job_key, "")

        self._apply_hero_filter()

    def _apply_hero_filter(self):
        """根据种族/职业/常用筛选条件显示/隐藏英雄行"""
        race_filter = self._race_filter_var.get()
        job_filter = self._job_filter_var.get()
        common_only = self._common_only_var.get()

        for hero_name, row_frame in self._hero_rows.items():
            if common_only and hero_name not in PUSH_COMMON_HEROES:
                row_frame.grid_remove()
                continue
            match_race = (race_filter == "全部" or self._hero_race.get(hero_name, "") == race_filter)
            match_job = (job_filter == "全部" or self._hero_job.get(hero_name, "") == job_filter)
            if match_race and match_job:
                row_frame.grid()
            else:
                row_frame.grid_remove()

    def _on_hero_level_change(self, hero_name):
        """Radiobutton 切换时自动写入文件"""
        self._hero_levels[hero_name] = self._hero_vars[hero_name].get()
        self._write_warehouse_txt()

    def _set_all_hero_levels(self, level):
        """批量设置所有英雄为指定练度"""
        for hero_name in ALL_HERO_NAMES:
            self._hero_levels[hero_name] = level
            if hero_name in self._hero_vars:
                self._hero_vars[hero_name].set(level)
        self._write_warehouse_txt()

    def _write_warehouse_txt(self):
        """将当前英雄练度写入 warehouse_heroes.txt"""
        hero_levels = getattr(self, '_hero_levels', {})
        try:
            with open(WAREHOUSE_TXT_PATH, 'w', encoding='utf-8') as f:
                for hero_name in ALL_HERO_NAMES:
                    level = hero_levels.get(hero_name, "高")
                    f.write(f"{hero_name},{level}\n")
        except Exception as e:
            _notify_file_write_error(WAREHOUSE_TXT_PATH)
            self.log(f"写入仓库文件失败: {str(e)}")

    def _schedule_file_write_error(self, path):
        if getattr(self, "_file_write_error_notified", False):
            return
        self._file_write_error_notified = True
        self._file_write_error_pending = True
        self.root.after(0, lambda: self._show_file_write_error(path))

    def _show_file_write_error(self, path):
        self._file_write_error_pending = False
        messagebox.showerror(
            "文件写入失败",
            f"无法写入文件：\n{path}\n\n"
            "当前文件夹可能没有写入权限，请将程序移动到其他可写文件夹后重试。",
        )
    
    def create_shouquguajijiangli_params(self, script, row=0):
        ttk.Label(self.param_frame, text="付费购买次数 (0-2):").grid(row=row, column=0, sticky=tk.W, pady=2)
        
        paid_times = script.params.get("paid_times", 0)
        self.paid_times_var = tk.IntVar(value=paid_times)
        
        paid_times_spinbox = ttk.Spinbox(
            self.param_frame,
            from_=0,
            to=2,
            textvariable=self.paid_times_var,
            width=10
        )
        paid_times_spinbox.grid(row=row, column=1, sticky=tk.W, pady=2)
        
        def on_param_change():
            script.params["paid_times"] = self.paid_times_var.get()
            self.save_config()
            
        paid_times_spinbox.bind("<FocusOut>", lambda e: on_param_change())
        paid_times_spinbox.bind("<Return>", lambda e: on_param_change())
        
        ttk.Label(self.param_frame, text="注: 免费三次默认购买掉").grid(row=row+1, column=0, columnspan=2, sticky=tk.W, pady=5)

    def create_yijiemigong_params(self, script, row=0):
        # 加载 formations.json 获取阵容列表（从 EXE 资源读取）
        formations = {}
        try:
            with open(get_resource_path("formations.json"), "r", encoding="utf-8") as f:
                formations = json.load(f)
        except Exception:
            pass
        all_forms = list(formations.keys())

        # 挑战次数
        ttk.Label(self.param_frame, text="挑战次数:").grid(row=row, column=0, sticky=tk.W, pady=2)
        challenges = script.params.get("challenges", 1)
        self.mg_challenges_var = tk.IntVar(value=challenges)
        ttk.Spinbox(self.param_frame, from_=1, to=100, textvariable=self.mg_challenges_var,
                    width=10).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        # 层数选择（互斥）
        ttk.Label(self.param_frame, text="层数:").grid(row=row, column=0, sticky=tk.W, pady=2)
        floors = script.params.get("floors", "15")
        self.mg_floors_var = tk.StringVar(value=floors)
        floor_frame = ttk.Frame(self.param_frame)
        floor_frame.grid(row=row, column=1, sticky=tk.W, pady=2)
        ttk.Radiobutton(floor_frame, text="15层", variable=self.mg_floors_var, value="15").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(floor_frame, text="20层", variable=self.mg_floors_var, value="20").pack(side=tk.LEFT, padx=5)
        row += 1

        # 初始阵容（下拉列表，不含括号）
        ttk.Label(self.param_frame, text="初始阵容:").grid(row=row, column=0, sticky=tk.W, pady=2)
        form_name = script.params.get("formation_name", "")
        self.mg_form_var = tk.StringVar(value=form_name if form_name in all_forms else "")
        form_combo = ttk.Combobox(self.param_frame, textvariable=self.mg_form_var,
                                  values=all_forms, state="readonly", width=35)
        form_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        if all_forms and not self.mg_form_var.get():
            form_combo.set(all_forms[0])
        row += 1

        # 20层boss阵容（下拉列表，含括号）
        ttk.Label(self.param_frame, text="20层boss阵容:").grid(row=row, column=0, sticky=tk.W, pady=2)
        shenceng_name = script.params.get("shenceng_formation_name", "")
        self.mg_shenceng_var = tk.StringVar(value=shenceng_name if shenceng_name in all_forms else "")
        shenceng_combo = ttk.Combobox(self.param_frame, textvariable=self.mg_shenceng_var,
                                      values=all_forms, state="readonly", width=35)
        shenceng_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        if all_forms and not self.mg_shenceng_var.get():
            shenceng_combo.set(all_forms[0])
        row += 1

        # 保存回调
        def on_param_change(*args):
            script.params["challenges"] = self.mg_challenges_var.get()
            script.params["floors"] = self.mg_floors_var.get()
            script.params["formation_name"] = self.mg_form_var.get()
            script.params["shenceng_formation_name"] = self.mg_shenceng_var.get()
            self.save_config()

        self.mg_challenges_var.trace_add("write", on_param_change)
        self.mg_floors_var.trace_add("write", on_param_change)
        self.mg_form_var.trace_add("write", on_param_change)
        self.mg_shenceng_var.trace_add("write", on_param_change)
        
    def select_script(self, index):
        self.current_script_index = index
        self.update_dashboard_buttons()
        self.update_script_panel()
        
    def on_script_enabled_changed(self):
        script = self.scripts[self.current_script_index]
        script.enabled = self.script_enabled_var.get()
        self.save_config()
        self.update_dashboard_buttons()
        
    def toggle_master_switch(self):
        if self.is_running:
            self.stop_all()
        else:
            self.start_all()
            
    def start_all(self):
        self.is_running = True
        self.stop_event.clear()
        self.master_switch_btn.configure(text="停止运行")
        self.stop_btn.configure(state=tk.NORMAL)
        
        # 检查是否有脚本启用
        enabled_scripts = [s for s in self.scripts if s.enabled]
        if not enabled_scripts:
            messagebox.showwarning("警告", "没有启用任何脚本！")
            self.stop_all()
            return
            
        self.log(f"开始运行脚本")
        
        for script in self.scripts:
            script.status = "等待中"
        self.update_script_panel()
        
        thread = threading.Thread(target=self.run_scripts_thread, args=(enabled_scripts,))
        thread.daemon = True
        thread.start()
        
    def stop_all(self):
        self.stop_event.set()
        self.is_running = False
        self.master_switch_btn.configure(text="开始运行")
        self.stop_btn.configure(state=tk.DISABLED)
        
        for script in self.scripts:
            if script.status == "运行中":
                script.status = "已停止"
        self.update_script_panel()
        
        self.log("所有脚本已停止")
        
    def on_closing(self):
        import subprocess
        if self.is_running:
            if messagebox.askokcancel("退出", "脚本正在运行中，确定要停止并退出吗？"):
                self.stop_all()
                subprocess.run(["taskkill", "/F", "/IM", "click_from_file.exe"], capture_output=True)
                self.root.destroy()
        else:
            subprocess.run(["taskkill", "/F", "/IM", "click_from_file.exe"], capture_output=True)
            self.root.destroy()
        
    def run_scripts_thread(self, scripts_to_run):
        # 先杀掉旧进程，再启动新的 click_from_file.exe（确保工作目录正确）
        import subprocess
        try:
            subprocess.run(["taskkill", "/F", "/IM", "click_from_file.exe"], capture_output=True)
            time.sleep(0.5)
        except Exception:
            pass

        self.log("运行click_from_file.exe...")
        try:
            ahk_exe_path = get_resource_path("click_from_file.exe")
            work_dir = get_work_path("")
            self.log(f"脚本路径: {ahk_exe_path}")
            self.log(f"工作目录: {work_dir}")

            if not os.path.exists(ahk_exe_path):
                self.log(f"错误: click_from_file.exe 文件不存在: {ahk_exe_path}")
            else:
                subprocess.Popen([ahk_exe_path, work_dir])
                self.log("click_from_file.exe 启动成功")
        except Exception as e:
            self.log(f"运行click_from_file.exe失败: {str(e)}")
            self.log("警告: click_from_file.exe 未启动，部分功能可能无法正常工作")
        
        time.sleep(2)
        
        # 顺序调用其他脚本
        script_order = [
            "登录", "仓库管理", "邮件", "好友奖励", "普竞", "迷梦之域", "女神塔", 
            "挂机奖励", "商城", "日常任务", "爬塔", "幻灵推图", "推图", "循环推图", "异界迷宫"
        ]
        
        for script_name in script_order:
            if self.stop_event.is_set():
                break
                
            script = next((s for s in self.scripts if s.name == script_name), None)
            if not script or not script.enabled:
                continue
                
            script.status = "运行中"
            self.root.after(0, self.update_script_panel)
            self.log(f"开始执行: {script.name}")
            
            try:
                # 检查是否需要停止
                if self.stop_event.is_set():
                    script.status = "已停止"
                    self.log(f"{script.name} 已停止")
                    result = False
                else:
                    if script.name == "登录":
                        try:
                            import start
                            start.main()
                            result = True
                        except ImportError as e:
                            self.log(f"登录模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "仓库管理":
                        try:
                            # 手动模式：直接写入 warehouse_heroes.txt
                            # 如果用户已在面板中勾选过，文件已是最新；否则生成默认文件
                            import warehouse
                            if not os.path.exists(WAREHOUSE_TXT_PATH):
                                self._write_warehouse_txt()
                            self.log("仓库英雄数据已就绪")
                            result = True
                        except ImportError as e:
                            self.log(f"仓库管理模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "邮件":
                        try:
                            import youjian
                            youjian.main()
                            result = True
                        except ImportError as e:
                            self.log(f"邮件模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "好友奖励":
                        try:
                            import haoyoujiangli
                            haoyoujiangli.main()
                            result = True
                        except ImportError as e:
                            self.log(f"好友奖励模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "普竞":
                        try:
                            import pujing
                            pujing.flow_pujing()
                            result = True
                        except ImportError as e:
                            self.log(f"普竞模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "迷梦之域":
                        try:
                            from mimengzhiyu import flow_mimengzhiyu
                            challenge_count = script.params.get("challenge_count")
                            result = flow_mimengzhiyu(challenge_count=challenge_count)
                        except ImportError as e:
                            self.log(f"迷梦之域模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "女神塔":
                        try:
                            import nvshenta
                            nvshenta.flow_nvshenta()
                            result = True
                        except ImportError as e:
                            self.log(f"女神塔模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "挂机奖励":
                        try:
                            import shouquguajijiangli
                            paid_times = script.params.get("paid_times", 0)
                            shouquguajijiangli.main(paid_times=paid_times)
                            result = True
                        except ImportError as e:
                            self.log(f"挂机奖励模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "商城":
                        try:
                            import shangcheng
                            shangcheng.main()
                            result = True
                        except ImportError as e:
                            self.log(f"商城模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "日常任务":
                        try:
                            import meirirenwulingqu
                            meirirenwulingqu.main()
                            result = True
                        except ImportError as e:
                            self.log(f"日常任务模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "爬塔":
                        try:
                            import pata
                            pata.main()
                            result = True
                        except ImportError as e:
                            self.log(f"爬塔模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "幻灵推图":
                        try:
                            import flow_push
                            ps = self.config.get("push_settings", {})
                            flow_push.main(
                                skip_manual=ps.get("skip_manual", True),
                                retry_count=ps.get("retry_count", 3)
                            )
                            result = True
                        except ImportError as e:
                            self.log(f"幻灵推图模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "推图":
                        try:
                            import push
                            ps = self.config.get("push_settings", {})
                            result = push.main(
                                skip_manual=ps.get("skip_manual", True),
                                retry_count=ps.get("retry_count", 3)
                            )
                        except ImportError as e:
                            self.log(f"推图模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "循环推图":
                        try:
                            import flow_push
                            import push
                            ps = self.config.get("push_settings", {})
                            skip_manual = ps.get("skip_manual", True)
                            retry_count = ps.get("retry_count", 3)
                            loop_count = 0
                            fast_rounds = 0
                            cycle_ok = True
                            while not self.stop_event.is_set():
                                loop_count += 1
                                round_start = time.time()
                                self.log(f"循环推图 第 {loop_count} 轮 - 幻灵推图开始")
                                try:
                                    huanling_result = flow_push.main(skip_manual=skip_manual, retry_count=retry_count)
                                    if huanling_result is False:
                                        # 单个模式结束/失败不是循环失败，按设计切换到普通推图。
                                        self.log("幻灵推图流程结束，切换到普通推图。")
                                except Exception as e:
                                    self.log(f"幻灵推图出错: {str(e)}")
                                    self.log("幻灵推图异常，继续切换到普通推图。")
                                
                                if self.stop_event.is_set():
                                    break
                                
                                self.log(f"循环推图 第 {loop_count} 轮 - 推图开始")
                                try:
                                    push_result = push.main(skip_manual=skip_manual, retry_count=retry_count)
                                    if push_result is False:
                                        # 单个模式结束/失败不是循环失败，下一轮重新进入幻灵推图。
                                        self.log("普通推图流程结束，下一轮切换到幻灵推图。")
                                except Exception as e:
                                    self.log(f"推图出错: {str(e)}")
                                    self.log("普通推图异常，下一轮继续切换到幻灵推图。")
                                
                                if self.stop_event.is_set():
                                    break

                                round_cost = time.time() - round_start
                                # 一轮正常推图至少包含一次战斗，通常需要几十秒以上；
                                # 30 秒内就结束的轮次视为异常（快速失败/空转）。
                                if round_cost < 30:
                                    fast_rounds += 1
                                    self.log(f"本轮耗时 {round_cost:.1f} 秒，异常快速结束（连续 {fast_rounds} 轮）")
                                else:
                                    fast_rounds = 0

                                if fast_rounds >= 3:
                                    self.log("循环推图连续 3 轮在 30 秒内异常结束，判定流程异常，停止循环推图。")
                                    break

                                self.log(f"循环推图 第 {loop_count} 轮完成，继续下一轮...")
                                time.sleep(2)
                            result = cycle_ok
                        except ImportError as e:
                            self.log(f"循环推图模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    elif script.name == "异界迷宫":
                        try:
                            import flow_migong
                            challenges = script.params.get("challenges", 1)
                            shouling_action = "jieshutansuo" if script.params.get("floors") == "15" else "jixutansuo"
                            formation_name = script.params.get("formation_name", "")
                            shenceng_formation_name = script.params.get("shenceng_formation_name", "")
                            flow_migong.flow_migong(
                                challenges=challenges,
                                shouling_action=shouling_action,
                                formation_name=formation_name,
                                shenceng_formation_name=shenceng_formation_name,
                            )
                            result = True
                        except ImportError as e:
                            self.log(f"异界迷宫模块导入失败: {str(e)}")
                            script.status = "错误"
                            result = False
                    else:
                        self.log(f"{script.name} 脚本暂未实现")
                        result = False
                    
                if result:
                    script.status = "完成"
                    self.log(f"{script.name} 执行完成")
                    
                    # 更新最后执行时间
                    script.last_run_time = datetime.now().isoformat()
                    
                    # 对于每日重置的脚本，执行完成后自动关闭
                    if script.daily_reset:
                        script.enabled = False
                        self.log(f"{script.name} 已自动关闭（每日重置脚本）")
                else:
                    script.status = "失败"
                    self.log(f"{script.name} 执行失败")
                    
            except Exception as e:
                script.status = "错误"
                self.log(f"{script.name} 执行出错: {str(e)}")
                
            self.root.after(0, self.update_script_panel)
            
            if self.stop_event.is_set():
                break
                
            time.sleep(2)
        
        self.root.after(0, self.stop_all)
        
    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, line)
        self.log_text.see(tk.END)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            _notify_file_write_error(LOG_FILE)
    
    def save_config(self):
        """保存配置"""
        # 收集脚本状态
        scripts_config = {}
        for script in self.scripts:
            scripts_config[script.name] = {
                "enabled": script.enabled,
                "params": script.params,
                "daily_reset": script.daily_reset,
                "last_run_time": script.last_run_time
            }
        self.config["scripts"] = scripts_config
        
        # 保存到文件
        if save_config(self.config):
            self.log("配置已保存")
        else:
            self.log("保存配置失败")

    def _auto_check_update(self):
        """启动时自动检查更新（后台线程）"""
        def _check():
            result = updater.check_update()
            if result[0] is None:
                return  # 启动时静默失败
            has_update, latest_tag, download_url, _ = result
            if has_update:
                self.root.after(0, lambda: self._show_update_dialog(latest_tag, download_url))
        threading.Thread(target=_check, daemon=True).start()

    def _check_update_clicked(self):
        """手动检查更新"""
        self.update_btn.configure(text="检查中...", state=tk.DISABLED)

        def _check():
            result = updater.check_update()
            if result[0] is None:
                _, err_msg = result
                self.root.after(0, lambda: self._update_result(f"检查失败: {err_msg}"))
            else:
                has_update, latest_tag, download_url, _ = result
                if has_update:
                    self.root.after(0, lambda: self._show_update_dialog(latest_tag, download_url))
                else:
                    self.root.after(0, lambda: self._update_result(f"已是最新版本 ({latest_tag})"))
            self.root.after(0, lambda: self.update_btn.configure(text="检查更新", state=tk.NORMAL))
        threading.Thread(target=_check, daemon=True).start()

    def _update_result(self, msg):
        self.version_label.configure(text=f"{__version__} - {msg}")
        self.log(msg)

    def _show_update_dialog(self, latest_tag, download_url):
        self.version_label.configure(text=f"{__version__} → {latest_tag} 可用", foreground="red")
        self.log(f"发现新版本: {latest_tag}")
        if not messagebox.askyesno("发现新版本",
                                   f"当前版本: {__version__}\n最新版本: {latest_tag}\n\n是否下载更新？"):
            return

        self.update_btn.configure(text="下载中...", state=tk.DISABLED)

        def _download():
            new_path = updater.download_update(download_url)
            if new_path is None:
                self.root.after(0, lambda: self._update_result("下载失败，请检查网络"))
                self.root.after(0, lambda: self.update_btn.configure(text="检查更新", state=tk.NORMAL))
                return
            self.root.after(0, lambda: self._install_and_restart(new_path))

        threading.Thread(target=_download, daemon=True).start()

    def _install_and_restart(self, new_path):
        self.update_btn.configure(text="检查更新", state=tk.NORMAL)
        if messagebox.askyesno("下载完成", "更新已下载，是否立即重启应用？"):
            updater.install_and_restart(new_path)

def main():
    root = tk.Tk()
    app = GameBotGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
